"""
VARA-style OFDM Waterfall Display Widget for Mercury QT.

Renders a real-time scrolling waterfall (spectrogram) of the audio spectrum,
similar to the waterfall display found in VARA modem software.  The widget
shows frequency on the horizontal axis and time scrolling downward, with
colour intensity mapped to signal power.

The widget also draws:
  - A horizontal spectrum/power graph at the top (like VARA)
  - Frequency axis labels at the bottom
  - OFDM carrier band overlay markers
  - An SNR / signal level indicator bar

Colour palette follows the classic blue-black-yellow-red-white "thermal"
colour map that VARA uses.
"""

from __future__ import annotations

import numpy as np
from typing import List, Optional
from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QLinearGradient, QImage, QPen, QFont,
    QBrush, QFontMetrics, QPainterPath
)


# ---------------------------------------------------------------------------
#  Colour-map helpers
# ---------------------------------------------------------------------------

def _build_vara_colormap(n: int = 256) -> List[QColor]:
    """Build a VARA-style thermal colour map with *n* entries.

    Gradient: black → deep-blue → blue → cyan → green → yellow → red → white
    """
    # Control points: (position 0-1, R, G, B)
    stops = [
        (0.00, 0, 0, 0),         # black  (noise floor)
        (0.10, 0, 0, 40),        # very dark blue
        (0.20, 0, 0, 120),       # deep blue
        (0.30, 0, 30, 180),      # blue
        (0.40, 0, 100, 200),     # cyan-blue
        (0.50, 0, 180, 130),     # teal / green
        (0.60, 40, 220, 40),     # green
        (0.70, 200, 220, 0),     # yellow
        (0.80, 255, 160, 0),     # orange
        (0.90, 255, 60, 0),      # red
        (1.00, 255, 255, 255),   # white  (clipping)
    ]
    cmap: List[QColor] = []
    for i in range(n):
        t = i / (n - 1)
        # Find bounding stops
        for j in range(len(stops) - 1):
            if stops[j][0] <= t <= stops[j + 1][0]:
                lo = stops[j]
                hi = stops[j + 1]
                f = (t - lo[0]) / (hi[0] - lo[0]) if hi[0] != lo[0] else 0.0
                r = int(lo[1] + f * (hi[1] - lo[1]))
                g = int(lo[2] + f * (hi[2] - lo[2]))
                b = int(lo[3] + f * (hi[3] - lo[3]))
                cmap.append(QColor(r, g, b))
                break
    return cmap


# ---------------------------------------------------------------------------
#  Waterfall Widget
# ---------------------------------------------------------------------------

class WaterfallWidget(QtWidgets.QWidget):
    """VARA-style scrolling OFDM waterfall display.

    Call :meth:`push_spectrum` with a 1-D numpy array of power values (dB)
    each time a new FFT line is available.  The widget renders automatically
    at the configured refresh rate.
    """

    # Emitted when the user clicks inside the waterfall area (frequency in Hz)
    frequency_clicked = Signal(float)

    # ---- tuneable constants ----
    SPECTRUM_HEIGHT = 60          # px – height of the top spectrum graph
    FREQ_AXIS_HEIGHT = 22         # px – height of the bottom frequency labels
    SNR_BAR_HEIGHT = 18           # px – height of the SNR indicator strip
    MARKER_AREA_HEIGHT = 6        # px – thin OFDM-band marker line
    REFRESH_MS = 50               # display refresh interval (20 fps)
    DEFAULT_FFT_SIZE = 512        # default number of frequency bins
    DEFAULT_SAMPLE_RATE = 8000    # Hz – default audio sample rate
    DISPLAY_MAX_HZ = 3000.0       # Hz – clamp the visible spectrum span
    # dB range calibrated to modem_stats_get_rx_spectrum output using raw i16
    # input (FDMDV_SCALE=825 reference).  Typical signal: -10..+15 dB;
    # typical noise floor: -40..-25 dB;  full-scale i16: +26 dB.
    MIN_DB = -50.0                # colour-map floor  — noise floor
    MAX_DB = 30.0                 # colour-map ceiling — above full-scale

    # OFDM passband markers (Hz) – typical Mercury / freedv OFDM band
    OFDM_LOW_HZ = 300.0
    OFDM_HIGH_HZ = 2500.0

    def __init__(self, parent=None, *,
                 fft_size: int = DEFAULT_FFT_SIZE,
                 sample_rate: int = DEFAULT_SAMPLE_RATE,
                 history_lines: int = 300):
        super().__init__(parent)

        self._fft_size = fft_size
        self._sample_rate = sample_rate
        self._history = history_lines

        # Actual number of spectrum bins — adapts to live data on first push
        self._n_bins = fft_size // 2

        # Colour map (index 0..255)
        self._cmap = _build_vara_colormap(256)

        # Noise-floor level: 12 % into the colour range → dark blue instead of black
        _noise = self.MIN_DB + (self.MAX_DB - self.MIN_DB) * 0.12

        # Ring-buffer of spectrum lines (oldest at row 0, newest at row -1)
        self._waterfall_data = np.full((self._history, self._n_bins),
                                       _noise, dtype=np.float32)
        self._write_idx = 0
        self._lines_written = 0

        # Latest single spectrum line (for the top spectrum graph)
        self._current_spectrum = np.full(self._n_bins, _noise, dtype=np.float32)

        # Current SNR value (set externally)
        self._snr = 0.0
        self._sync = False

        # Pre-rendered waterfall QImage (updated lazily)
        self._wf_image: Optional[QImage] = None
        self._dirty = True

        # Refresh timer
        self._timer = QTimer(self)
        self._timer.setInterval(self.REFRESH_MS)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

        # Sizing
        self.setMinimumHeight(200)
        self.setMinimumWidth(280)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                           QtWidgets.QSizePolicy.Policy.Expanding)

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    @Slot(object)
    def push_spectrum(self, power_db: np.ndarray, sample_rate: int = 0):
        """Push one FFT line (power in dB).

        Automatically adapts to the incoming bin count and sample rate so
        that no external configuration is needed when the live UDP stream
        starts.  If the bin count changes (e.g. demo→live transition), the
        ring buffer is re-initialised to the noise-floor colour (dark blue)
        so the waterfall shows meaningful colour immediately.
        """
        n = len(power_db)

        # --- dynamic adaptation ---
        if sample_rate > 0 and sample_rate != self._sample_rate:
            self._sample_rate = sample_rate
            self._dirty = True

        if n != self._n_bins:
            # Bin count changed (demo→live or sample-rate change): reset buffer.
            self._n_bins = n
            _noise = self.MIN_DB + (self.MAX_DB - self.MIN_DB) * 0.12
            self._waterfall_data = np.full((self._history, n), _noise, dtype=np.float32)
            self._current_spectrum = np.full(n, _noise, dtype=np.float32)
            self._write_idx = 0
            self._lines_written = 0

        self._waterfall_data[self._write_idx] = power_db
        self._write_idx = (self._write_idx + 1) % self._history
        self._lines_written += 1
        self._current_spectrum = power_db.copy()
        self._dirty = True

    def set_snr(self, snr: float):
        self._snr = snr

    def set_sync(self, sync: bool):
        self._sync = sync

    def set_ofdm_band(self, low_hz: float, high_hz: float):
        self.OFDM_LOW_HZ = low_hz
        self.OFDM_HIGH_HZ = high_hz
        self._dirty = True

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------

    def _hz_to_x(self, hz: float, width: int) -> float:
        """Map a frequency (Hz) to an x-pixel coordinate."""
        max_hz = self._visible_max_hz()
        if max_hz <= 0:
            return 0.0
        hz = max(0.0, min(hz, max_hz))
        return (hz / max_hz) * width

    def _visible_max_hz(self) -> float:
        return min(self._sample_rate / 2.0, self.DISPLAY_MAX_HZ)

    def _visible_bin_count(self) -> int:
        max_hz = self._sample_rate / 2.0
        visible_max_hz = self._visible_max_hz()
        if max_hz <= 0 or self._n_bins <= 1:
            return max(1, self._n_bins)
        return max(
            1,
            min(
                self._n_bins,
                int(np.ceil(self._n_bins * (visible_max_hz / max_hz))),
            ),
        )

    def _x_to_bin_index(self, px: int, width: int, visible_bins: int) -> int:
        if visible_bins <= 1 or width <= 1:
            return 0
        bin_f = (px / (width - 1)) * (visible_bins - 1)
        return min(int(bin_f), visible_bins - 1)

    def _db_to_color_index(self, db: float) -> int:
        """Map dB value to 0..255 colour-map index."""
        t = (db - self.MIN_DB) / (self.MAX_DB - self.MIN_DB)
        return max(0, min(255, int(t * 255)))

    def _render_waterfall_image(self, w: int, h: int) -> QImage:
        """Render the waterfall bitmap from the ring buffer."""
        n_bins = self._visible_bin_count()
        lines = min(self._lines_written, self._history)

        img = QImage(w, h, QImage.Format.Format_RGB32)
        img.fill(QColor(0, 0, 0))

        if lines == 0:
            return img

        # Map rows: bottom of image = most-recent line
        for row_y in range(h):
            # Which history line does this pixel-row correspond to?
            line_idx_f = (row_y / h) * lines
            line_idx = int(line_idx_f)
            if line_idx >= lines:
                line_idx = lines - 1

            # Actual index in ring buffer (oldest first → newest last)
            ring_pos = (self._write_idx - lines + line_idx) % self._history
            spectrum = self._waterfall_data[ring_pos]

            for px in range(w):
                bin_i = self._x_to_bin_index(px, w, n_bins)
                ci = self._db_to_color_index(spectrum[bin_i])
                c = self._cmap[ci]
                img.setPixelColor(px, row_y, c)

        return img

    def _render_waterfall_image_fast(self, w: int, h: int) -> QImage:
        """Render waterfall via numpy for speed."""
        n_bins = self._visible_bin_count()
        lines = min(self._lines_written, self._history)

        if lines == 0:
            img = QImage(w, h, QImage.Format.Format_RGB32)
            img.fill(QColor(0, 0, 0))
            return img

        # Build ordered array (oldest → newest)
        if lines < self._history:
            ordered = self._waterfall_data[:lines]
        else:
            idx = self._write_idx
            ordered = np.roll(self._waterfall_data, -idx, axis=0)

        # Resample rows to image height
        row_indices = np.linspace(0, lines - 1, h).astype(int)
        col_indices = np.linspace(0, n_bins - 1, w).astype(int)
        sampled = ordered[np.ix_(row_indices, col_indices)]

        # Map to 0..255
        t = (sampled - self.MIN_DB) / (self.MAX_DB - self.MIN_DB)
        ci = np.clip((t * 255).astype(int), 0, 255)

        # Build RGB buffer using look-up table
        lut = np.zeros((256, 3), dtype=np.uint8)
        for i, c in enumerate(self._cmap):
            lut[i] = [c.red(), c.green(), c.blue()]

        rgb = lut[ci]  # shape (h, w, 3)

        # Build ARGB32 buffer (0xFFRRGGBB)
        argb = np.zeros((h, w), dtype=np.uint32)
        argb = (0xFF000000
                | (rgb[:, :, 0].astype(np.uint32) << 16)
                | (rgb[:, :, 1].astype(np.uint32) << 8)
                | rgb[:, :, 2].astype(np.uint32))

        img = QImage(argb.data, w, h, w * 4, QImage.Format.Format_RGB32)
        # QImage doesn't copy the data, so we must keep a reference to the
        # underlying NumPy buffer on the widget instead of on the QImage.
        self._wf_argb_ref = argb
        return img

    # ------------------------------------------------------------------
    #  Painting
    # ------------------------------------------------------------------

    def _on_tick(self):
        if self._dirty:
            self._wf_image = None  # invalidate cache
        self.update()

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        w = self.width()
        h = self.height()

        top_area = self.SPECTRUM_HEIGHT + self.SNR_BAR_HEIGHT + self.MARKER_AREA_HEIGHT
        bottom_area = self.FREQ_AXIS_HEIGHT
        wf_y = top_area
        wf_h = h - top_area - bottom_area
        if wf_h < 10:
            wf_h = 10

        # ---- Waterfall image ----
        if (
            self._wf_image is None
            or self._dirty
            or self._wf_image.width() != w
            or self._wf_image.height() != wf_h
        ):
            self._wf_image = self._render_waterfall_image_fast(w, wf_h)
            self._dirty = False
        p.drawImage(0, wf_y, self._wf_image)

        # ---- OFDM band overlay markers ----
        self._draw_ofdm_markers(p, 0, wf_y, w, wf_h)

        # ---- Spectrum graph (top) ----
        self._draw_spectrum_graph(p, 0, self.SNR_BAR_HEIGHT, w, self.SPECTRUM_HEIGHT)

        # ---- OFDM carrier marker strip ----
        self._draw_marker_strip(p, 0, self.SNR_BAR_HEIGHT + self.SPECTRUM_HEIGHT,
                                w, self.MARKER_AREA_HEIGHT)

        # ---- SNR bar (very top) ----
        self._draw_snr_bar(p, 0, 0, w, self.SNR_BAR_HEIGHT)

        # ---- Frequency axis (bottom) ----
        self._draw_freq_axis(p, 0, wf_y + wf_h, w, self.FREQ_AXIS_HEIGHT)

        p.end()

    # -- sub-painters --

    def _draw_spectrum_graph(self, p: QPainter, x0, y0, w, h):
        """Draw the top real-time power spectrum graph (VARA style)."""
        # Background
        p.fillRect(x0, y0, w, h, QColor(10, 10, 18))

        visible_bins = self._visible_bin_count()
        spec = self._current_spectrum

        # Faint grid lines
        pen_grid = QPen(QColor(40, 40, 55))
        pen_grid.setStyle(Qt.PenStyle.DotLine)
        p.setPen(pen_grid)
        for db_line in range(-80, -9, 10):
            fy = y0 + h - ((db_line - self.MIN_DB) / (self.MAX_DB - self.MIN_DB)) * h
            if y0 <= fy <= y0 + h:
                p.drawLine(int(x0), int(fy), int(x0 + w), int(fy))

        # OFDM passband shading
        lx = int(self._hz_to_x(self.OFDM_LOW_HZ, w))
        rx = int(self._hz_to_x(self.OFDM_HIGH_HZ, w))
        p.fillRect(lx, y0, rx - lx, h, QColor(25, 35, 60, 100))

        # Spectrum fill (gradient under curve)
        path = QPainterPath()
        path.moveTo(x0, y0 + h)
        for px in range(w):
            bin_i = self._x_to_bin_index(px, w, visible_bins)
            db = float(spec[bin_i])
            fy = y0 + h - ((db - self.MIN_DB) / (self.MAX_DB - self.MIN_DB)) * h
            fy = max(y0, min(y0 + h, fy))
            path.lineTo(px + x0, fy)
        path.lineTo(x0 + w, y0 + h)
        path.closeSubpath()

        grad = QLinearGradient(0, y0, 0, y0 + h)
        grad.setColorAt(0.0, QColor(0, 200, 255, 120))
        grad.setColorAt(0.5, QColor(0, 120, 200, 80))
        grad.setColorAt(1.0, QColor(0, 40, 80, 40))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path)

        # Spectrum line on top
        pen_line = QPen(QColor(0, 220, 255, 220), 1.2)
        p.setPen(pen_line)
        prev = None
        for px in range(w):
            bin_i = self._x_to_bin_index(px, w, visible_bins)
            db = float(spec[bin_i])
            fy = y0 + h - ((db - self.MIN_DB) / (self.MAX_DB - self.MIN_DB)) * h
            fy = max(y0, min(y0 + h, fy))
            if prev is not None:
                p.drawLine(QPointF(prev[0], prev[1]), QPointF(px + x0, fy))
            prev = (px + x0, fy)

    def _draw_marker_strip(self, p: QPainter, x0, y0, w, h):
        """Thin subtle strip that marks the OFDM passband edges."""
        p.fillRect(x0, y0, w, h, QColor(12, 12, 16))
        lx = int(self._hz_to_x(self.OFDM_LOW_HZ, w))
        rx = int(self._hz_to_x(self.OFDM_HIGH_HZ, w))
        # Draw a very subtle dim fill inside the band
        p.fillRect(lx, y0, rx - lx, h, QColor(0, 80, 120, 50))
        # Draw thin 1-px edge lines at band boundaries only
        pen = QPen(QColor(0, 130, 180, 90), 1)
        p.setPen(pen)
        p.drawLine(lx, y0, lx, y0 + h)
        p.drawLine(rx, y0, rx, y0 + h)

    def _draw_ofdm_markers(self, p: QPainter, x0, y0, w, h):
        """Draw faint vertical lines at OFDM band edges on the waterfall."""
        pen = QPen(QColor(0, 200, 255, 50), 1, Qt.PenStyle.DashLine)
        p.setPen(pen)
        for hz in (self.OFDM_LOW_HZ, self.OFDM_HIGH_HZ):
            fx = int(self._hz_to_x(hz, w))
            p.drawLine(fx, y0, fx, y0 + h)

    def _draw_snr_bar(self, p: QPainter, x0, y0, w, h):
        """Draw the top-most SNR / signal level bar."""
        p.fillRect(x0, y0, w, h, QColor(18, 18, 24))

        # SNR bar fill
        snr_min, snr_max = -10.0, 30.0
        frac = max(0.0, min(1.0, (self._snr - snr_min) / (snr_max - snr_min)))
        bar_w = int(frac * (w - 120))  # leave room for text

        # Colour based on SNR quality
        if self._snr < 3:
            bar_color = QColor(200, 30, 30)
        elif self._snr < 10:
            bar_color = QColor(220, 180, 0)
        else:
            bar_color = QColor(0, 200, 80)

        p.fillRect(x0 + 2, y0 + 2, bar_w, h - 4, bar_color)

        # Text labels
        font = QFont("Monospace", 8)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(220, 220, 220))
        snr_text = f"SNR: {self._snr:+.1f} dB"
        p.drawText(x0 + bar_w + 8, y0 + h - 4, snr_text)

        # Sync indicator
        sync_text = "SYNC" if self._sync else "NO SYNC"
        sync_color = QColor(0, 255, 100) if self._sync else QColor(160, 50, 50)
        p.setPen(sync_color)
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(sync_text)
        p.drawText(x0 + w - tw - 8, y0 + h - 4, sync_text)

    def _draw_freq_axis(self, p: QPainter, x0, y0, w, h):
        """Draw frequency tick marks and labels at the bottom."""
        p.fillRect(x0, y0, w, h, QColor(18, 18, 24))
        font = QFont("Monospace", 7)
        p.setFont(font)
        p.setPen(QColor(160, 160, 180))

        max_hz = self._visible_max_hz()
        # Choose nice tick spacing
        if max_hz <= 3000:
            tick_step = 500
        elif max_hz <= 8000:
            tick_step = 1000
        else:
            tick_step = 2000

        fm = QFontMetrics(font)
        tick_pen = QPen(QColor(80, 80, 100), 1)

        hz = 0
        while hz <= max_hz:
            fx = int(self._hz_to_x(hz, w)) + x0
            # Tick mark
            p.setPen(tick_pen)
            p.drawLine(fx, y0, fx, y0 + 4)
            # Label
            p.setPen(QColor(160, 160, 180))
            label = f"{hz:.0f}"
            lw = fm.horizontalAdvance(label)
            p.drawText(fx - lw // 2, y0 + h - 2, label)
            hz += tick_step

    # ------------------------------------------------------------------
    #  Mouse interaction
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            max_hz = self._visible_max_hz()
            hz = (event.position().x() / self.width()) * max_hz
            self.frequency_clicked.emit(hz)
        super().mousePressEvent(event)

"""
Waterfall Display module for the Mercury QT application.

Wraps the WaterfallWidget and SpectrumProvider into a QGroupBox.
Shows a live waterfall when a spectrum UDP port is provided, otherwise
displays a blank (black) screen.
"""

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Slot
from core.components.waterfall_widget import WaterfallWidget
from core.components.spectrum_provider import SpectrumProvider


class WaterfallDisplay(QtWidgets.QWidget):
    """Self-contained waterfall display panel."""

    def __init__(self, parent=None, spectrum_port: int | None = None):
        super().__init__(parent)

        # ---- Waterfall widget ----
        self.waterfall = WaterfallWidget(
            fft_size=512,
            sample_rate=8000,
            history_lines=350,
        )

        # ---- Spectrum data source — live UDP only, no demo ----
        self.provider = SpectrumProvider(self, udp_port=spectrum_port)
        self.provider.spectrum_ready.connect(self._on_spectrum)

        # ---- Layout inside a GroupBox ----
        self.group_box = QtWidgets.QGroupBox("Waterfall")
        inner = QtWidgets.QVBoxLayout()
        inner.setContentsMargins(4, 4, 4, 4)
        inner.setSpacing(2)
        inner.addWidget(self.waterfall, stretch=1)
        self.group_box.setLayout(inner)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.group_box)

        self._active = False

    # ------------------------------------------------------------------
    #  Slots
    # ------------------------------------------------------------------

    @Slot(object, int)
    def _on_spectrum(self, power_db, sample_rate: int):
        """Forward spectrum line (and sample rate) to the waterfall widget."""
        self.waterfall.push_spectrum(power_db, sample_rate)

    @Slot(dict)
    def handle_status(self, data: dict):
        """Update SNR and sync overlay from modem status messages."""
        snr = data.get("snr")
        if snr is not None:
            self.waterfall.set_snr(float(snr))
        sync = data.get("sync")
        if sync is not None:
            self.waterfall.set_sync(bool(sync))

    def set_active(self, enabled: bool):
        """Start or stop the spectrum UDP receiver."""
        self._active = enabled
        if enabled:
            self.provider.start()
        else:
            self.provider.stop()

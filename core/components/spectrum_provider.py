"""
Spectrum Data Provider for the Mercury QT Waterfall Display.

Provides FFT / spectrum data to the WaterfallWidget via two modes:

1. **Live mode** – Listens on a dedicated UDP port for binary FFT frames
   sent by the Mercury C backend.  Each UDP datagram carries a compact
   header followed by float32 power-spectral-density values (dB).

2. **Demo mode** – Generates a synthetic OFDM-like spectrum for UI
   development and testing when no backend is running.

The provider emits a Qt signal (`spectrum_ready`) each time a new
spectrum line is available.
"""

from __future__ import annotations

import struct
import numpy as np
from typing import Optional
from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtNetwork import QUdpSocket, QHostAddress


# ---------------------------------------------------------------------------
#  Binary protocol for spectrum datagrams (backend → UI)
# ---------------------------------------------------------------------------
#  Offset  Size   Field
#  0       4      Magic  0x4D435259  ("MCRY")
#  4       2      uint16  fft_size  (number of float32 values following)
#  6       2      uint16  sample_rate (Hz)
#  8       N*4    float32[]  power values in dB (N = fft_size)
# ---------------------------------------------------------------------------

SPECTRUM_MAGIC = 0x4D435259
SPECTRUM_HEADER = struct.Struct("<IHH")   # magic, fft_size, sample_rate
SPECTRUM_UDP_PORT = 10002                 # BASE_PORT + 2  (default spectrum port)


class SpectrumProvider(QObject):
    """Receives or generates FFT spectrum data and emits it as a signal."""

    # Emitted with (power_db: np.ndarray, sample_rate: int)
    spectrum_ready = Signal(object, int)

    def __init__(self, parent=None, *,
                 udp_port: int = SPECTRUM_UDP_PORT,
                 demo_mode: bool = True,
                 fft_size: int = 512,
                 sample_rate: int = 8000):
        super().__init__(parent)

        self._udp_port = udp_port
        self._fft_size = fft_size
        self._sample_rate = sample_rate
        self._demo_mode = demo_mode
        self._demo_timer: Optional[QTimer] = None
        self._udp_socket: Optional[QUdpSocket] = None
        self._phase = 0.0  # for demo animation

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def start(self):
        """Start receiving spectrum data (live UDP or demo generator)."""
        if self._demo_mode:
            self._start_demo()
        else:
            self._start_udp()

    def stop(self):
        if self._demo_timer and self._demo_timer.isActive():
            self._demo_timer.stop()
        if self._udp_socket:
            self._udp_socket.close()

    def set_demo_mode(self, enabled: bool):
        self.stop()
        self._demo_mode = enabled
        self.start()

    # ------------------------------------------------------------------
    #  Live UDP receiver
    # ------------------------------------------------------------------

    def _start_udp(self):
        self._udp_socket = QUdpSocket(self)
        if not self._udp_socket.bind(QHostAddress("0.0.0.0"), self._udp_port):
            print(f"[SpectrumProvider] Could not bind to port {self._udp_port}")
            # Fall back to demo mode
            self._demo_mode = True
            self._start_demo()
            return
        self._udp_socket.readyRead.connect(self._on_udp_data)
        print(f"[SpectrumProvider] Listening for spectrum on UDP port {self._udp_port}")

    @Slot()
    def _on_udp_data(self):
        while self._udp_socket and self._udp_socket.hasPendingDatagrams():
            datagram, _, _ = self._udp_socket.readDatagram(
                self._udp_socket.pendingDatagramSize()
            )
            data = bytes(datagram.data())
            if len(data) < SPECTRUM_HEADER.size:
                continue
            magic, fft_size, sr = SPECTRUM_HEADER.unpack_from(data, 0)
            if magic != SPECTRUM_MAGIC:
                continue
            expected = SPECTRUM_HEADER.size + fft_size * 4
            if len(data) < expected:
                continue
            power = np.frombuffer(data, dtype=np.float32,
                                  offset=SPECTRUM_HEADER.size, count=fft_size)
            self.spectrum_ready.emit(power, int(sr))

    # ------------------------------------------------------------------
    #  Demo / simulation generator
    # ------------------------------------------------------------------

    def _start_demo(self):
        self._demo_timer = QTimer(self)
        self._demo_timer.setInterval(50)  # ~20 lines/sec
        self._demo_timer.timeout.connect(self._generate_demo_line)
        self._demo_timer.start()
        print("[SpectrumProvider] Demo mode started")

    @Slot()
    def _generate_demo_line(self):
        """Produce a synthetic OFDM-like spectrum line."""
        n = self._fft_size // 2
        sr = self._sample_rate
        freqs = np.linspace(0, sr / 2, n)

        # Base noise floor
        noise = np.random.normal(-70, 3, n).astype(np.float32)

        # OFDM carriers inside passband (300 – 2500 Hz, like Mercury/freedv)
        ofdm_low, ofdm_high = 300.0, 2500.0
        n_carriers = 26  # typical OFDM carrier count
        carrier_freqs = np.linspace(ofdm_low + 40, ofdm_high - 40, n_carriers)
        carrier_bw = (ofdm_high - ofdm_low) / n_carriers * 0.6

        # Slowly varying "channel" – simulate fading
        self._phase += 0.02
        fade = 0.5 + 0.5 * np.sin(self._phase * 0.7)
        level = -25.0 + fade * 12.0  # carrier level (dB)

        for cf in carrier_freqs:
            gauss = np.exp(-0.5 * ((freqs - cf) / (carrier_bw / 2)) ** 2)
            # Per-carrier random variation
            carrier_level = level + np.random.uniform(-3, 3)
            noise += gauss * (carrier_level - noise.mean()) * 0.8

        # Gentle smoothing for realism
        kernel = np.array([0.1, 0.2, 0.4, 0.2, 0.1], dtype=np.float32)
        noise = np.convolve(noise, kernel, mode='same')

        # Add occasional burst/interference
        if np.random.random() < 0.03:
            burst_f = np.random.uniform(100, sr / 2 - 100)
            burst = np.exp(-0.5 * ((freqs - burst_f) / 30) ** 2) * np.random.uniform(-30, -15)
            noise += burst

        self.spectrum_ready.emit(noise, sr)

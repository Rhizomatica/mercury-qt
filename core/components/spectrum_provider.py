"""
Spectrum Data Provider for the Mercury QT Waterfall Display.

Listens on a dedicated UDP port for binary FFT frames sent by the Mercury C
backend.  Each UDP datagram carries a compact header followed by float32
power-spectral-density values (dB).

The provider emits a Qt signal (`spectrum_ready`) each time a new spectrum
line is available.
"""

from __future__ import annotations

import struct
import numpy as np
from typing import Optional
from PySide6.QtCore import QObject, Signal, Slot
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
    """Receives FFT spectrum data over UDP and emits it as a signal."""

    # Emitted with (power_db: np.ndarray, sample_rate: int)
    spectrum_ready = Signal(object, int)

    def __init__(self, parent=None, *,
                 udp_port: int = SPECTRUM_UDP_PORT):
        super().__init__(parent)
        self._udp_port = udp_port
        self._udp_socket: Optional[QUdpSocket] = None

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def start(self):
        """Bind the UDP socket and start receiving spectrum datagrams."""
        if self._udp_socket is not None:
            return  # already running
        self._udp_socket = QUdpSocket(self)
        if not self._udp_socket.bind(QHostAddress("0.0.0.0"), self._udp_port):
            print(f"[SpectrumProvider] Could not bind to port {self._udp_port}: "
                  f"{self._udp_socket.errorString()}")
            self._udp_socket.deleteLater()
            self._udp_socket = None
            return
        self._udp_socket.readyRead.connect(self._on_udp_data)
        print(f"[SpectrumProvider] Listening for spectrum on UDP port {self._udp_port}")

    def stop(self):
        """Stop receiving and release the socket."""
        if self._udp_socket is None:
            return
        self._udp_socket.readyRead.disconnect(self._on_udp_data)
        self._udp_socket.close()
        self._udp_socket.deleteLater()
        self._udp_socket = None
        print("[SpectrumProvider] Stopped.")

    # ------------------------------------------------------------------
    #  Internal
    # ------------------------------------------------------------------

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

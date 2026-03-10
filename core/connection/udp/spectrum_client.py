"""Binary UDP receiver for spectrum / waterfall data from Mercury backend.

Protocol (little-endian, sent by spectrum_sender.c):
  Offset  Size   Field
  0       4      Magic   0x4D435259  ("MCRY")
  4       2      uint16  fft_size     - number of float32 values
  6       2      uint16  sample_rate  - Hz
  8       N*4    float32[] power values in dB

Port: UI_DEFAULT_TX_PORT + 1  (default 10001)
"""

import struct
import sys

from PySide6.QtNetwork import QUdpSocket, QHostAddress
from PySide6.QtCore import QObject, Slot, Signal

SPECTRUM_MAGIC = 0x4D435259
SPECTRUM_DEFAULT_PORT = 10001    # UI_DEFAULT_TX_PORT + 1
SPECTRUM_HEADER_SIZE = 8         # magic(4) + fft_size(2) + sample_rate(2)


class SpectrumClient(QObject):
    """Listens for binary spectrum datagrams on *port* and emits :signal:`spectrum_received`.

    Attributes
    ----------
    spectrum_received : Signal(list[float], int)
        Emitted each time a valid frame arrives.
        Arguments: (power_dB_list, sample_rate_hz)
    """

    spectrum_received = Signal(list, int)

    def __init__(self, host: str = "127.0.0.1", port: int = SPECTRUM_DEFAULT_PORT, parent=None):
        super().__init__(parent)
        self._host = host
        self._port = port
        self._socket: QUdpSocket | None = None
        self._active = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> bool:
        """Bind the UDP socket and start receiving spectrum data."""
        if self._active:
            return True

        self._socket = QUdpSocket(self)
        if not self._socket.bind(QHostAddress(self._host), self._port):
            print(f"[SpectrumClient] Error: cannot bind to {self._host}:{self._port}: "
                  f"{self._socket.errorString()}")
            self._socket.deleteLater()
            self._socket = None
            return False

        self._socket.readyRead.connect(self._on_ready_read)
        self._active = True
        print(f"[SpectrumClient] Listening for spectrum data on {self._host}:{self._port}")
        return True

    def stop(self):
        """Unbind the socket and stop receiving spectrum data."""
        if not self._active:
            return

        if self._socket is not None:
            self._socket.readyRead.disconnect(self._on_ready_read)
            self._socket.close()
            self._socket.deleteLater()
            self._socket = None

        self._active = False
        print("[SpectrumClient] Stopped.")

    @property
    def active(self) -> bool:
        return self._active

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @Slot()
    def _on_ready_read(self):
        while self._socket and self._socket.hasPendingDatagrams():
            datagram, _host, _port = self._socket.readDatagram(
                self._socket.pendingDatagramSize()
            )
            self._parse_frame(datagram.data())

    def _parse_frame(self, data: bytes):
        if len(data) < SPECTRUM_HEADER_SIZE:
            print(f"[SpectrumClient] Datagram too short ({len(data)} bytes), dropping.")
            return

        magic, fft_size, sample_rate = struct.unpack_from("<IHH", data, 0)

        if magic != SPECTRUM_MAGIC:
            print(f"[SpectrumClient] Bad magic 0x{magic:08X}, expected 0x{SPECTRUM_MAGIC:08X}.")
            return

        expected_len = SPECTRUM_HEADER_SIZE + fft_size * 4
        if len(data) < expected_len:
            print(f"[SpectrumClient] Truncated payload: got {len(data)}, "
                  f"expected {expected_len} bytes.")
            return

        floats = list(struct.unpack_from(f"<{fft_size}f", data, SPECTRUM_HEADER_SIZE))
        self.spectrum_received.emit(floats, int(sample_rate))

"""
Mercury QT WebSocket Client - bidirectional connection to the Mercury C backend.

Connects to the Mercury backend's WSS server (mongoose-based) at:
    wss://<host>:<port>/websocket

Provides the same signal interface as the UDP client so the rest of the
application can be wired identically:
    - json_received(dict)          - JSON text messages from the backend
    - binary_received(bytes)       - raw binary frames (spectrum / waterfall)
    - connection_lost()            - emitted when the WebSocket closes
    - connected()                  - emitted when the WebSocket is open

Outgoing:
    - send_json(dict)              - serialise and send a JSON command
    - send_message(str)            - send a raw text frame

Configuration mirrors the C backend (gui_interface/websocket/mercury_websocket.h):
    Port     : UI_DEFAULT_PORT (10000)
    Endpoint : /websocket
    Max msg  : 8192 bytes
    SSL      : uses /etc/ssl/certs/hermes.radio.crt
"""

from __future__ import annotations

import json
import struct
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot, QTimer, QUrl
from PySide6.QtCore import QFile, QIODevice
from PySide6.QtNetwork import QSslCertificate, QSslConfiguration, QSslSocket
from PySide6.QtWebSockets import QWebSocket

import numpy as np


# ---------------------------------------------------------------------------
#  Constants - keep in sync with mercury_websocket.h
# ---------------------------------------------------------------------------
WS_DEFAULT_PORT       = 10000                         # UI_DEFAULT_PORT
WS_ENDPOINT           = "/websocket"                  # URI path the backend expects
WS_MAX_MESSAGE_SIZE   = 8192
SSL_CERT_PATH         = "/etc/ssl/certs/hermes.radio.crt"

# Reconnect / inactivity
RECONNECT_INTERVAL_MS = 3000     # retry connection every 3 s
INACTIVITY_TIMEOUT_MS = 5000     # declare connection lost after 5 s silence

# Spectrum binary protocol (same as spectrum_sender.h / spectrum_provider.py)
SPECTRUM_MAGIC   = 0x4D435259                         # "MCRY"
SPECTRUM_HEADER  = struct.Struct("<IHH")               # magic(4) + fft_size(2) + sample_rate(2)


class WebSocketClient(QObject):
    """Bidirectional QWebSocket client for the Mercury C backend."""

    # ---- Signals (same names as ClientUDP where applicable) ----
    json_received    = Signal(dict)          # decoded JSON text message
    binary_received  = Signal(bytes)         # raw binary frame
    spectrum_ready   = Signal(object, int)   # (np.ndarray power_dB, sample_rate)
    connected        = Signal()              # websocket opened
    connection_lost  = Signal()              # websocket closed / backend gone

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = WS_DEFAULT_PORT,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)

        self._host = host
        self._port = port
        self._ws: Optional[QWebSocket] = None
        self._is_connected = False

        # ---- Auto-reconnect timer ----
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setInterval(RECONNECT_INTERVAL_MS)
        self._reconnect_timer.setSingleShot(False)
        self._reconnect_timer.timeout.connect(self._try_connect)

        # ---- Inactivity watchdog ----
        self._inactivity_timer = QTimer(self)
        self._inactivity_timer.setSingleShot(True)
        self._inactivity_timer.setInterval(INACTIVITY_TIMEOUT_MS)
        self._inactivity_timer.timeout.connect(self._on_inactivity_timeout)

        # ---- SSL configuration (skip verification for now) ----
        self._ssl_config = self._build_ssl_config()

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def start(self):
        """Create the QWebSocket and initiate the first connection attempt."""
        if self._ws is not None:
            return  # already started
        self._create_socket()
        self._try_connect()

    def stop(self):
        """Gracefully close the connection and stop reconnect attempts."""
        self._reconnect_timer.stop()
        self._inactivity_timer.stop()
        if self._ws is not None:
            self._ws.close()
            self._ws.deleteLater()
            self._ws = None
        self._is_connected = False

    def send_json(self, data: dict):
        """Serialise *data* to JSON and send as a text frame."""
        if not self._is_connected:
            print("[WS] Not connected - cannot send JSON")
            return
        try:
            message = json.dumps(data)
            self.send_message(message)
        except TypeError as e:
            print(f"[WS] Error serializing data to JSON: {e}")

    def send_message(self, message: str):
        """Send a raw text frame to the backend."""
        if not self._is_connected or self._ws is None:
            print("[WS] Not connected - cannot send message")
            return
        self._ws.sendTextMessage(message)

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    # ------------------------------------------------------------------
    #  Connection helpers
    # ------------------------------------------------------------------

    def _build_ssl_config(self) -> QSslConfiguration:
        """Build SSL config for connecting to the Mercury C backend (WSS client).

        The cert/key live on the server (the radio).  As a client we only need
        to trust the server's self-signed certificate.
        """
        config = QSslConfiguration.defaultConfiguration()
        config.setPeerVerifyMode(QSslSocket.PeerVerifyMode.VerifyNone)

        # Optionally add the server cert as a trusted CA (works when the UI
        # runs on the same host as the radio or the cert has been copied over).
        cert_file = QFile(SSL_CERT_PATH)
        if cert_file.open(QIODevice.OpenModeFlag.ReadOnly):
            certs = QSslCertificate.fromDevice(cert_file)
            cert_file.close()
            if certs:
                config.setCaCertificates(config.caCertificates() + certs)

        return config

    def _build_url(self) -> QUrl:
        url = QUrl()
        url.setScheme("wss")
        url.setHost(self._host)
        url.setPort(self._port)
        url.setPath(WS_ENDPOINT)
        return url

    def _create_socket(self):
        """Instantiate a fresh QWebSocket and wire its signals."""
        if self._ws is not None:
            self._ws.deleteLater()

        self._ws = QWebSocket("mercury-qt", parent=self)

        # Apply SSL configuration
        self._ws.setSslConfiguration(self._ssl_config)

        # Qt signals → our slots
        self._ws.connected.connect(self._on_connected)
        self._ws.disconnected.connect(self._on_disconnected)
        self._ws.textMessageReceived.connect(self._on_text_message)
        self._ws.binaryMessageReceived.connect(self._on_binary_message)
        self._ws.errorOccurred.connect(self._on_error)
        self._ws.sslErrors.connect(self._on_ssl_errors)

    @Slot()
    def _try_connect(self):
        """Attempt to open the WSS connection."""
        if self._is_connected:
            return
        url = self._build_url()
        print(f"[WS] Connecting to {url.toString()} ...")
        if self._ws is None:
            self._create_socket()
        self._ws.open(url)

    # ------------------------------------------------------------------
    #  QWebSocket signal handlers
    # ------------------------------------------------------------------

    @Slot()
    def _on_connected(self):
        print(f"[WS] Connected to {self._host}:{self._port}")
        self._is_connected = True
        self._reconnect_timer.stop()
        self._inactivity_timer.start()
        self.connected.emit()

    @Slot()
    def _on_disconnected(self):
        was_connected = self._is_connected
        self._is_connected = False
        self._inactivity_timer.stop()
        if was_connected:
            print(f"[WS] Disconnected from {self._host}:{self._port}")
            self.connection_lost.emit()
        # Schedule reconnect attempts
        if not self._reconnect_timer.isActive():
            self._reconnect_timer.start()

    @Slot(str)
    def _on_text_message(self, message: str):
        """Handle incoming text (JSON) frames from the backend."""
        self._inactivity_timer.start()   # reset watchdog
        try:
            data = json.loads(message)
            self.json_received.emit(data)
        except json.JSONDecodeError as e:
            print(f"[WS] JSON decode error: {e}")
            print(f"[WS] Raw message: {message[:200]}")

    @Slot(bytes)
    def _on_binary_message(self, data: bytes):
        """Handle incoming binary frames (spectrum data) from the backend."""
        self._inactivity_timer.start()   # reset watchdog
        self.binary_received.emit(data)

        # Try to decode as spectrum frame
        if len(data) >= SPECTRUM_HEADER.size:
            magic, fft_size, sr = SPECTRUM_HEADER.unpack_from(data, 0)
            if magic == SPECTRUM_MAGIC:
                expected = SPECTRUM_HEADER.size + fft_size * 4
                if len(data) >= expected:
                    power = np.frombuffer(
                        data, dtype=np.float32,
                        offset=SPECTRUM_HEADER.size, count=fft_size
                    )
                    self.spectrum_ready.emit(power, int(sr))

    @Slot("QAbstractSocket::SocketError")
    def _on_error(self, error):
        if self._ws:
            print(f"[WS] Error: {self._ws.errorString()} (code {error})")

    @Slot(list)
    def _on_ssl_errors(self, errors):
        """Accept self-signed certificates for the Hermes radio."""
        if self._ws:
            for err in errors:
                print(f"[WS] SSL error (ignored): {err.errorString()}")
            self._ws.ignoreSslErrors()

    @Slot()
    def _on_inactivity_timeout(self):
        """No data received for INACTIVITY_TIMEOUT_MS - assume backend is gone."""
        if self._is_connected:
            print(f"[WS] Inactivity timeout - closing connection")
            self._ws.close()
            # _on_disconnected will fire and handle the rest

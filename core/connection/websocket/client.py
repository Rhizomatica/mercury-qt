"""
Mercury QT WebSocket Client - bidirectional connection to the Mercury C backend.

Connects to the Mercury backend at:
    wss://<host>:<port>/websocket   (tried first)
    ws://<host>:<port>/websocket    (tried next, and so on)

The client alternates between WSS and WS on every failed attempt until one
is accepted.  Once connected, the working scheme is kept for the lifetime of
that connection.  After a clean disconnect the cycle restarts from WSS.

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
    SSL      : self-signed cert at /etc/ssl/certs/hermes.radio.crt (WSS mode only)
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

        # Scheme negotiation: alternate wss → ws → wss → … on every failed
        # attempt until the backend accepts one.
        self._current_scheme = "wss"

        # ---- Auto-reconnect timer ----
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setInterval(RECONNECT_INTERVAL_MS)
        self._reconnect_timer.setSingleShot(True)   # fires once; rescheduled in _on_disconnected
        self._reconnect_timer.timeout.connect(self._try_connect)

        # ---- Inactivity watchdog ----
        self._inactivity_timer = QTimer(self)
        self._inactivity_timer.setSingleShot(True)
        self._inactivity_timer.setInterval(INACTIVITY_TIMEOUT_MS)
        self._inactivity_timer.timeout.connect(self._on_inactivity_timeout)

        # ---- Scheme-failure counter ----
        # Switch scheme only after this many consecutive failures on the same scheme.
        self._scheme_failures = 0
        self._max_failures_per_scheme = 2

        # ---- Connection attempt timeout ----
        # Guards against hangs where Qt never emits errorOccurred / disconnected
        # (e.g. firewall drops packets, OS TCP timeout is very long).
        self._connect_timeout = QTimer(self)
        self._connect_timeout.setSingleShot(True)
        self._connect_timeout.setInterval(5000)   # 5s to establish a connection
        self._connect_timeout.timeout.connect(self._on_connect_timeout)

        # ---- SSL configuration (skip verification - server uses self-signed cert) ----
        self._ssl_config = self._build_ssl_config()

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def start(self):
        """Initiate the first connection attempt to the backend WebSocket server."""
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
        url.setScheme(self._current_scheme)
        url.setHost(self._host)
        url.setPort(self._port)
        url.setPath(WS_ENDPOINT)
        return url

    def _create_socket(self):
        """Instantiate a fresh QWebSocket and wire its signals.

        Always called before each connection attempt to guarantee a clean
        socket state, especially when switching from wss to ws.
        """
        if self._ws is not None:
            # Disconnect all signals BEFORE aborting so that the teardown of
            # the old socket (which emits disconnected/errorOccurred) does not
            # cascade back into _on_disconnected and trigger spurious reconnects.
            # Each signal is disconnected individually so a single RuntimeError
            # does not silently skip the remaining disconnections.
            for sig, slot in [
                (self._ws.connected,             self._on_connected),
                (self._ws.disconnected,           self._on_disconnected),
                (self._ws.textMessageReceived,    self._on_text_message),
                (self._ws.binaryMessageReceived,  self._on_binary_message),
                (self._ws.errorOccurred,          self._on_error),
                (self._ws.sslErrors,              self._on_ssl_errors),
            ]:
                try:
                    sig.disconnect(slot)
                except RuntimeError:
                    pass  # already disconnected; safe to ignore
            self._ws.abort()
            self._ws.deleteLater()

        self._ws = QWebSocket("mercury-qt", parent=self)

        # Apply SSL configuration (only relevant for wss, harmless for ws)
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
        """Attempt to open the WebSocket connection using the current scheme."""
        if self._is_connected:
            return
        url = self._build_url()
        print(f"[WS] Connecting to {url.toString()} ...")
        # Always create a fresh socket to avoid stale SSL/TCP state, especially
        # when switching from wss to ws after a failed WSS attempt.
        self._create_socket()
        self._connect_timeout.start()   # watchdog: forces retry if Qt never signals
        self._ws.open(url)

    # ------------------------------------------------------------------
    #  QWebSocket signal handlers
    # ------------------------------------------------------------------

    @Slot()
    def _on_connected(self):
        print(f"[WS] Connected to {self._host}:{self._port}")
        self._is_connected = True
        self._scheme_failures = 0
        self._connect_timeout.stop()
        self._reconnect_timer.stop()
        self._inactivity_timer.start()
        self.connected.emit()

    @Slot()
    def _on_disconnected(self):
        if self.sender() is not self._ws:
            return  # stale signal from a replaced socket; ignore
        was_connected = self._is_connected
        self._is_connected = False
        self._connect_timeout.stop()
        self._inactivity_timer.stop()
        if was_connected:
            code = self._ws.closeCode() if self._ws else "N/A"
            reason = self._ws.closeReason() if self._ws else ""
            detail = f" (close code={code}" + (f", reason={reason})" if reason else ")")
            print(f"[WS] Disconnected from {self._host}:{self._port}{detail}")
            self.connection_lost.emit()
            # Keep the scheme that was working; reset failure count for reconnect.
            self._scheme_failures = 0
        # Schedule next reconnect attempt (single-shot, so safe to call unconditionally)
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
        if self.sender() is not self._ws:
            return  # stale signal from a replaced socket; ignore
        if self._ws:
            print(f"[WS] Error ({self._current_scheme}): {self._ws.errorString()} (code {error})")

        self._scheme_failures += 1
        if self._scheme_failures >= self._max_failures_per_scheme:
            next_scheme = "ws" if self._current_scheme == "wss" else "wss"
            print(
                f"[WS] {self._current_scheme.upper()} failed "
                f"{self._scheme_failures}x - switching to {next_scheme.upper()}"
            )
            self._current_scheme = next_scheme
            self._scheme_failures = 0
        else:
            print(
                f"[WS] {self._current_scheme.upper()} failed "
                f"({self._scheme_failures}/{self._max_failures_per_scheme})"
            )

    @Slot()
    def _on_connect_timeout(self):
        """Fires when a connection attempt doesn't resolve within the timeout.

        This catches hangs where Qt never emits errorOccurred or disconnected
        (e.g. the OS TCP stack is waiting for a RST/timeout that takes minutes).
        """
        if self._is_connected:
            return
        print(f"[WS] {self._current_scheme.upper()} connection attempt timed out")
        # Count as a failure and possibly switch scheme.
        self._scheme_failures += 1
        if self._scheme_failures >= self._max_failures_per_scheme:
            next_scheme = "ws" if self._current_scheme == "wss" else "wss"
            print(
                f"[WS] {self._current_scheme.upper()} failed "
                f"{self._scheme_failures}x - switching to {next_scheme.upper()}"
            )
            self._current_scheme = next_scheme
            self._scheme_failures = 0
        # Abort the stuck socket; disconnect its signals first so abort() doesn't
        # cascade into _on_disconnected and trigger a duplicate timer start.
        if self._ws is not None:
            for sig, slot in [
                (self._ws.connected,            self._on_connected),
                (self._ws.disconnected,          self._on_disconnected),
                (self._ws.textMessageReceived,   self._on_text_message),
                (self._ws.binaryMessageReceived, self._on_binary_message),
                (self._ws.errorOccurred,         self._on_error),
                (self._ws.sslErrors,             self._on_ssl_errors),
            ]:
                try:
                    sig.disconnect(slot)
                except RuntimeError:
                    pass
            self._ws.abort()
            self._ws.deleteLater()
            self._ws = None
        self._reconnect_timer.start()

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

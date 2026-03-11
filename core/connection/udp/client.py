import sys
import json
from PySide6.QtNetwork import QUdpSocket, QHostAddress
from PySide6.QtCore import QObject, Slot, QByteArray, Signal, QTimer

class ClientUDP(QObject):
    json_received = Signal(dict)
    connection_lost = Signal()   # emitted after INACTIVITY_MS with no data

    # Default ports — derived from BASE_PORT (10000):
    DEFAULT_BASE_PORT    = 10000
    DEFAULT_RECEIVE_PORT = DEFAULT_BASE_PORT      # RECEIVE_PORT = BASE_PORT      (UI listens, backend TX)
    DEFAULT_SEND_PORT    = DEFAULT_BASE_PORT + 1  # SEND_PORT    = BASE_PORT + 1  (UI sends,   backend RX)
    DEFAULT_BIND_HOST    = '0.0.0.0'   # listen on all interfaces
    DEFAULT_SERVER_HOST  = '127.0.0.1' # default destination for outgoing datagrams

    INACTIVITY_MS = 2000  # declare connection lost after 2s silence

    def __init__(self, host=None, receive_port=None, send_port=None, parent=None):
        super().__init__(parent)
        print("Create a UDP socket (IPv4, UDP)")
        # `host` may be a combined host string (legacy) or a server destination.
        # Bind always uses the wildcard address; only outgoing datagrams use host.
        self.BIND_HOST        = self.DEFAULT_BIND_HOST
        self.SERVER_HOST      = host or self.DEFAULT_SERVER_HOST
        self.RECEIVE_PORT     = receive_port or self.DEFAULT_RECEIVE_PORT
        self.SERVER_SEND_PORT = send_port or self.DEFAULT_SEND_PORT
        self.udp_socket = QUdpSocket(self)

        # Source locking: once the first Mercury process sends a packet its IP
        # is recorded here and all packets from other IPs are discarded.
        # Reset to None when the inactivity timer fires so the UI can accept
        # a fresh process after the previous one disconnects.
        self._locked_host: str | None = None

        # Inactivity watchdog
        self._inactivity_timer = QTimer(self)
        self._inactivity_timer.setSingleShot(True)
        self._inactivity_timer.setInterval(self.INACTIVITY_MS)
        self._inactivity_timer.timeout.connect(self._on_inactivity_timeout)

        # Bind the UDP socket to the client's receive port
        if not self.udp_socket.bind(QHostAddress(self.BIND_HOST), self.RECEIVE_PORT):
            print(f"Error: Could not bind UDP socket to {self.BIND_HOST}:{self.RECEIVE_PORT}")
            # TODO - toast error
            sys.exit(1)

        self.udp_socket.readyRead.connect(self.read_pending_datagrams)
        print(f"UDP Client listening on {self.BIND_HOST}:{self.RECEIVE_PORT}")

    @Slot()
    def _on_inactivity_timeout(self):
        """Inactivity watchdog fired — release source lock and signal connection lost."""
        print(f"Connection lost from {self._locked_host} (inactivity timeout)")
        self._locked_host = None
        self.connection_lost.emit()

    @Slot()
    def read_pending_datagrams(self):
        while self.udp_socket.hasPendingDatagrams():
            datagram, host, port = self.udp_socket.readDatagram(self.udp_socket.pendingDatagramSize())
            sender_ip = host.toString()

            # --- Source locking: only accept packets from the first Mercury process ---
            if self._locked_host is None:
                # First packet received — lock onto this sender
                self._locked_host = sender_ip
                # Update the outgoing destination so commands reach this Mercury instance
                self.SERVER_HOST = sender_ip
                print(f"Locked onto Mercury process at {sender_ip}:{port}")
                print(f"Commands will be sent to {self.SERVER_HOST}:{self.SERVER_SEND_PORT}")
            elif sender_ip != self._locked_host:
                # Packet from a different Mercury process — discard it
                print(f"Discarding packet from {sender_ip}:{port} (locked to {self._locked_host})")
                continue

            message = datagram.data().decode('utf-8')
            try:
                json_data = json.loads(message)
                # Reset inactivity watchdog on every received packet
                self._inactivity_timer.start()
                self.json_received.emit(json_data)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                print(f"Raw message was: {message}")
            except Exception as e:
                print(f"An unexpected error occurred while processing message: {e}")


    def start_udp_client(self):
        print(f"UDP Client sending to {self.SERVER_HOST}:{self.SERVER_SEND_PORT}")
        ping_message = "Ping Mercury UDP server..."
        self.send_message(ping_message)

    def send_json(self, data: dict):
        """Serializa o dicionário para JSON e envia como mensagem."""
        try:
            message = json.dumps(data)
            self.send_message(message)
        except TypeError as e:
            print(f"Error serializing data to JSON: {e}")
            print(f"Data was: {data}")
            
    def send_message(self, message: str):
        """Envia uma string bruta como datagrama UDP."""
        # print(f"Sending message: '{message}'")
        data = QByteArray(message.encode('utf-8'))
        
        # NOTE: A documentação do PySide6/Qt sugere que o writeDatagram deve usar
        # o QHostAddress e a porta do destinatário.
        bytes_sent = self.udp_socket.writeDatagram(data, QHostAddress(self.SERVER_HOST), self.SERVER_SEND_PORT)
        
        if bytes_sent == -1:
            print(f"Error sending message: {self.udp_socket.errorString()}")
        # else:
            # print(f"Sent {bytes_sent} bytes.")

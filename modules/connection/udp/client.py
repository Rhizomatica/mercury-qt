import sys
import json
from PySide6.QtNetwork import QUdpSocket, QHostAddress
from PySide6.QtCore import QObject, Slot, QByteArray, Signal

# Run server > ./ui_communication 127.0.0.1 10000 9999

class ClientUDP(QObject):
    json_received = Signal(dict) 

    def __init__(self, parent=None):
        super().__init__(parent)
        print("Create a UDP socket (IPv4, UDP)")
        self.HOST = '127.0.0.1'
        self.RECEIVE_PORT = 10000  # Client will listen on this port
        self.SERVER_SEND_PORT = 9999 # Server sends to this port
        self.udp_socket = QUdpSocket(self)

        # Bind the UDP socket to the client's receive port
        if not self.udp_socket.bind(QHostAddress(self.HOST), self.RECEIVE_PORT):
            print(f"Error: Could not bind UDP socket to {self.HOST}:{self.RECEIVE_PORT}")
            # TODO - toast error
            sys.exit(1)

        self.udp_socket.readyRead.connect(self.read_pending_datagrams)
        print(f"UDP Client listening on {self.HOST}:{self.RECEIVE_PORT}")

    @Slot()
    def read_pending_datagrams(self):
        while self.udp_socket.hasPendingDatagrams():
            datagram, host, port = self.udp_socket.readDatagram(self.udp_socket.pendingDatagramSize())
            message = datagram.data().decode('utf-8')
            print(f"Received from server {host.toString()}:{port}: '{message}'")
            try:
                json_data = json.loads(message)
                print(f"Parsed JSON data: {json_data}")
                self.json_received.emit(json_data)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                print(f"Raw message was: {message}")
            except Exception as e:
                print(f"An unexpected error occurred while processing message: {e}")


    def start_udp_client(self):
        print(f"UDP Client sending to {self.HOST}:{self.SERVER_SEND_PORT}")
        ping_message = "Ping Mercury UDP server..."
        self.send_message(ping_message)

    def send_message(self, message: str):
        print(f"Sending message: '{message}'")
        data = QByteArray(message.encode('utf-8'))
        bytes_sent = self.udp_socket.writeDatagram(data, QHostAddress(self.HOST), self.SERVER_SEND_PORT)
        if bytes_sent == -1:
            print(f"Error sending message: {self.udp_socket.errorString()}")
        else:
            print(f"Sent {bytes_sent} bytes.")

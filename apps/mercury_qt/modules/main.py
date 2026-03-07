from PySide6 import QtCore, QtWidgets
from .connection_info.connection_info import ConnectionInfo
from apps.mercury_qt.modules.controls.controls import Controls 

import core.connection.udp.client as Client_UDP

class Main(QtWidgets.QWidget):
    """Main application widget for Mercury QT Client."""

    def __init__(self):
        super().__init__()
        
        self.connection_info = ConnectionInfo()
        self.app_controls_view = Controls() 

        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.left_column = QtWidgets.QVBoxLayout()
        self.right_column = QtWidgets.QVBoxLayout()

        self.left_column.addWidget(self._build_radio_status_group())
        self.right_column.addWidget(self._build_controls_group())

        # --- Final layout ---
        self.main_layout.addLayout(self.left_column, 1)
        self.main_layout.addLayout(self.right_column, 1)
        
        self.start_udp_service()
        self._connect_signals()
        

    def _build_radio_status_group(self) -> QtWidgets.QGroupBox:
        return self.connection_info.handle_connection_info({"message": "Waiting for UDP data..."})
       
    def _build_controls_group(self) -> QtWidgets.QGroupBox:
        return self.app_controls_view
        
    def start_udp_service(self):
        self.client = Client_UDP.ClientUDP()
        self.client.json_received.connect(self.handle_json_data)        
        self.client.start_udp_client()
        
    @QtCore.Slot(dict)
    def handle_json_data(self, data: dict):
        """Process received JSON messages."""
        msg_type = data.get("type")
        
        handlers = {
            "soundcard_list": self.handle_soundcard_data,
            "radio_list": self.handle_radio_data,
            "status": self.connection_info.handle_connection_info,
        }

        handler = handlers.get(msg_type)
        if handler:
            handler(data)
        else:
            print(f"Unknown message type: {msg_type}")
    
    def handle_soundcard_data(self, data: dict):
        soundcards = data.get("list", [])
        self.app_controls_view.get_soundcard_control().set_options(soundcards)

    def handle_radio_data(self, data: dict):
        radios = data.get("list", [])
        self.app_controls_view.get_radio_control().set_options(radios)

    def _connect_signals(self):        
        # CONEXÃO DO SINAL CUSTOMIZADO: Conecta o sinal 'command_to_send' ao handler de envio
        self.app_controls_view.get_soundcard_control().command_to_send.connect(self._send_json_command)
        self.app_controls_view.get_radio_control().command_to_send.connect(self._send_json_command)       
        
        
    @QtCore.Slot(dict)
    def _send_json_command(self, command_dict: dict):
        """Recebe um dicionário de comando já formatado do ComboBox e o envia via UDP."""
        print(f"Sending command: {command_dict}")
        self.client.send_json(command_dict)
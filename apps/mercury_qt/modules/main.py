from PySide6 import QtCore, QtWidgets
from .connection_info.connection_info import ConnectionInfo
from .waterfall.waterfall_display import WaterfallDisplay
from apps.mercury_qt.modules.controls.controls import Controls 

import core.connection.udp.client as Client_UDP

class Main(QtWidgets.QWidget):
    """Main application widget for Mercury QT Client."""

    def __init__(self, base_port=10000):
        super().__init__()

        self.receive_port  = base_port
        self.send_port     = base_port + 1
        self.spectrum_port = base_port + 2
        self.connection_info = ConnectionInfo()
        self.app_controls_view = Controls()
        self.waterfall_display = WaterfallDisplay(spectrum_port=self.spectrum_port)
        self.waterfall_display.setVisible(False)   # shown only when backend has waterfall enabled
        self._waterfall_configured = False          # set once on first status message
        self._waterfall_on = False                  # mirrors the backend waterfall flag

        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.left_column = QtWidgets.QVBoxLayout()
        self.right_column = QtWidgets.QVBoxLayout()

        # Left: waterfall (shown only when enabled) + connection info
        self.left_column.addWidget(self.waterfall_display, stretch=3)
        self.left_column.addWidget(self._build_radio_status_group(), stretch=1)

        # Right: controls
        self.right_column.addWidget(self._build_controls_group())

        # --- Final layout ---
        self.main_layout.addLayout(self.left_column, 2)
        self.main_layout.addLayout(self.right_column, 1)
        
        self.start_udp_service()
        self._connect_signals()
        

    def _build_radio_status_group(self) -> QtWidgets.QGroupBox:
        return self.connection_info.handle_connection_info({"message": "Waiting for UDP data..."})
       
    def _build_controls_group(self) -> QtWidgets.QGroupBox:
        return self.app_controls_view
        
    def start_udp_service(self):
        self.client = Client_UDP.ClientUDP(receive_port=self.receive_port, send_port=self.send_port)
        self.client.json_received.connect(self.handle_json_data)
        self.client.connection_lost.connect(self._handle_connection_lost)
        self.client.start_udp_client()
        
    @QtCore.Slot(dict)
    def handle_json_data(self, data: dict):
        """Process received JSON messages."""
        msg_type = data.get("type")
        
        handlers = {
            "soundcard_list": self.handle_soundcard_data,
            "radio_list": self.handle_radio_data,
            "status": self._handle_status_data,
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

    def _handle_status_data(self, data: dict):
        self._last_status_data = data

        # On the very first status packet, let the backend tell us whether the
        # waterfall is enabled (-W was NOT passed).  Configure once and for all.
        if not self._waterfall_configured:
            self._waterfall_configured = True
            # json.loads returns True/False for JSON true/false; default True if absent
            self._waterfall_on = data.get("waterfall", True)
            self.waterfall_display.setVisible(self._waterfall_on)
            if self._waterfall_on:
                # Start the UDP receiver — backend is already sending spectrum data
                self.waterfall_display.set_active(True)

        # Strip the internal meta-field before passing to widgets
        status = {k: v for k, v in data.items() if k != "waterfall"}

        if self._waterfall_on:
            # SNR and sync belong to the waterfall overlay only
            self.waterfall_display.handle_status(status)
            conn_data = {k: v for k, v in status.items() if k not in ("snr", "sync")}
            self.connection_info.handle_connection_info(conn_data)
        else:
            # No waterfall — SNR and sync show in Connection Info
            self.connection_info.handle_connection_info(status)

    @QtCore.Slot()
    def _handle_connection_lost(self):
        """Called 2s after the last UDP packet — backend is gone."""
        last = getattr(self, '_last_status_data', {})
        # Build a reset dict with the same keys but cleared status values
        reset_data = {k: v for k, v in last.items()}
        reset_data['client_tcp_connected'] = False
        reset_data['user_callsign'] = ''
        reset_data['dest_callsign'] = ''
        # Strip internal meta-field
        reset_data.pop('waterfall', None)
        if self._waterfall_on:
            # Reset waterfall SNR/sync overlay
            self.waterfall_display.handle_status({'snr': 0.0, 'sync': False})
            conn_data = {k: v for k, v in reset_data.items() if k not in ('snr', 'sync')}
            self.connection_info.handle_connection_info(conn_data)
        else:
            self.connection_info.handle_connection_info(reset_data)

    def _connect_signals(self):        
        # CONEXÃO DO SINAL CUSTOMIZADO: Conecta o sinal 'command_to_send' ao handler de envio
        self.app_controls_view.get_soundcard_control().command_to_send.connect(self._send_json_command)
        self.app_controls_view.get_radio_control().command_to_send.connect(self._send_json_command)

    @QtCore.Slot(dict)
    def _send_json_command(self, command_dict: dict):
        """Recebe um dicionário de comando já formatado do ComboBox e o envia via UDP."""
        print(f"Sending command: {command_dict}")
        self.client.send_json(command_dict)
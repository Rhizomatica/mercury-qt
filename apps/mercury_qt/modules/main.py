from PySide6 import QtCore, QtWidgets
from .connection_info.connection_info import ConnectionInfo
from .waterfall.waterfall_display import WaterfallDisplay
from apps.mercury_qt.modules.controls.controls import RadioControls 

import core.connection.udp.client as Client_UDP
from core.connection.websocket.client import WebSocketClient

class Main(QtWidgets.QWidget):
    """Main application widget for Mercury QT Client."""

    def __init__(self, base_port=10000, ws_port=9999):
        super().__init__()

        self.receive_port  = base_port
        self.send_port     = base_port + 1
        self.spectrum_port = base_port + 2
        self.ws_port       = ws_port
        self.connection_info = ConnectionInfo()
        self.app_controls_view = RadioControls()
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
        self.start_ws_service()
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

    def start_ws_service(self):
        """Create and start the WebSocket client to the Mercury C backend."""
        self.ws_client = WebSocketClient(port=self.ws_port, parent=self)
        # JSON messages — same handler as UDP
        self.ws_client.json_received.connect(self.handle_json_data)
        self.ws_client.connection_lost.connect(self._handle_ws_connection_lost)
        self.ws_client.connected.connect(self._handle_ws_connected)
        # Spectrum binary data — feed directly into waterfall
        self.ws_client.spectrum_ready.connect(self._on_ws_spectrum)
        self.ws_client.start()
        
    @QtCore.Slot(dict)
    def handle_json_data(self, data: dict):
        """Process received JSON messages."""
        msg_type = data.get("type")
        
        handlers = {
            "capture_dev_list": self.handle_capture_dev_data,
            "playback_dev_list": self.handle_playback_dev_data,
            "input_channel": self.handle_input_channel_data,
            "radio_list": self.handle_radio_data,
            "status": self._handle_status_data,
        }

        handler = handlers.get(msg_type)
        if handler:
            handler(data)
        else:
            print(f"Unknown message type: {msg_type}")
    
    def handle_capture_dev_data(self, data: dict):
        devices = data.get("list", [])
        selected = data.get("selected", "")
        devices.insert(0, {"display": "Default", "id": "default"})
        ctrl = self.app_controls_view.get_capture_dev_control()
        ctrl.set_options(devices)
        if selected:
            ctrl.set_selected(selected)

    def handle_playback_dev_data(self, data: dict):
        devices = data.get("list", [])
        selected = data.get("selected", "")
        devices.insert(0, {"display": "Default", "id": "default"})
        ctrl = self.app_controls_view.get_playback_dev_control()
        ctrl.set_options(devices)
        if selected:
            ctrl.set_selected(selected)

    def handle_radio_data(self, data: dict):
        radios = data.get("list", [])
        selected = data.get("selected", "")
        device_path = data.get("device_path", "")
        ctrl = self.app_controls_view.get_radio_control()
        ctrl.set_options(radios)
        if selected:
            ctrl.set_selected(selected)
        if device_path:
            self.app_controls_view.set_device_path_text(device_path)
        # Restore user's applied selection over backend defaults
        self.app_controls_view.restore_radio_selection()

    def handle_input_channel_data(self, data: dict):
        channels = data.get("list", [])
        selected = data.get("selected", "")
        ctrl = self.app_controls_view.get_input_channel_control()
        ctrl.set_options(channels)
        if selected:
            ctrl.set_selected(selected)

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

            # Request the radio list now that we know the backend is alive
            self._send_json_command({"command": "get_radio_list"})

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

    # ------------------------------------------------------------------
    #  WebSocket event handlers
    # ------------------------------------------------------------------

    @QtCore.Slot()
    def _handle_ws_connected(self):
        """WebSocket connected — request radio list from the backend."""
        print("[Main] WebSocket connected to Mercury backend")
        self._send_json_command({"command": "get_radio_list"})

    @QtCore.Slot()
    def _handle_ws_connection_lost(self):
        """WebSocket disconnected — same reset logic as UDP connection lost."""
        print("[Main] WebSocket disconnected from Mercury backend")
        self._handle_connection_lost()

    @QtCore.Slot(object, int)
    def _on_ws_spectrum(self, power_db, sample_rate: int):
        """Forward spectrum data from WebSocket to the waterfall widget."""
        if self._waterfall_on:
            self.waterfall_display.waterfall.push_spectrum(power_db, sample_rate)

    def _connect_signals(self):        
        # CONEXÃO DO SINAL CUSTOMIZADO: Conecta o sinal 'command_to_send' ao handler de envio
        self.app_controls_view.get_capture_dev_control().command_to_send.connect(self._send_json_command)
        self.app_controls_view.get_playback_dev_control().command_to_send.connect(self._send_json_command)
        self.app_controls_view.get_input_channel_control().command_to_send.connect(self._send_json_command)
        # Radio model + device path are sent together via the combined Apply button
        self.app_controls_view.radio_config_command.connect(self._send_json_command)

    @QtCore.Slot(dict)
    def _send_json_command(self, command_dict: dict):
        """Send a JSON command to the backend via both UDP and WebSocket."""
        print(f"Sending command: {command_dict}")
        # Send via UDP (legacy)
        self.client.send_json(command_dict)
        # Send via WebSocket (new)
        self.ws_client.send_json(command_dict)
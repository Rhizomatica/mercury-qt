from PySide6 import QtCore, QtWidgets
from modules.radio.view.json_detail_view import JsonDetailView
import modules.connection.udp.client as Client_UDP


class MainWidget(QtWidgets.QWidget):
    """Main application widget for Mercury QT Client."""

    def __init__(self):
        super().__init__()

        # State
        self.soundcards: list[str] = []
        self.selected_soundcard: str = ""
        self.radios: list[str] = []
        self.selected_radio: str = ""

        # UDP Client setup
        self.client = Client_UDP.ClientUDP()
        self.client.json_received.connect(self.handle_json_data)
        self.client.json_received.connect(self.update_detail_view)
        self.client.start_udp_client()

        self._setup_ui()
        self._connect_signals()

    # -------------------------------
    # UI Setup
    # -------------------------------
    def _setup_ui(self):
        """Initialize UI layout and widgets."""
        main_layout = QtWidgets.QHBoxLayout(self)

        # --- Left column ---
        left_column = QtWidgets.QVBoxLayout()
        left_column.addWidget(self._build_status_group())
        left_column.addWidget(self._build_control_group())

        # --- Right column ---
        right_column = QtWidgets.QVBoxLayout()
        right_column.addWidget(self._build_devices_group())

        # --- Final layout ---
        main_layout.addLayout(left_column, 1)
        main_layout.addLayout(right_column, 1)

    def _build_status_group(self) -> QtWidgets.QGroupBox:
        """Create group box for connection status / JSON view."""
        group = QtWidgets.QGroupBox("Dados da Conexão")
        layout = QtWidgets.QGridLayout()

        self.json_detail_view = JsonDetailView()
        self.json_detail_view.update_json_data({"message": "Waiting for UDP data..."})
        layout.addWidget(self.json_detail_view)

        group.setLayout(layout)
        return group

    def _build_control_group(self) -> QtWidgets.QGroupBox:
        """Create radio control buttons group."""
        group = QtWidgets.QGroupBox("Controle")
        layout = QtWidgets.QVBoxLayout()

        self.btn_usb = QtWidgets.QPushButton("USB")
        self.btn_lsb = QtWidgets.QPushButton("LSB")

        layout.addWidget(self.btn_usb)
        layout.addWidget(self.btn_lsb)

        group.setLayout(layout)
        return group

    def _build_devices_group(self) -> QtWidgets.QGroupBox:
        """Create form for devices and command input."""
        group = QtWidgets.QGroupBox("Dispositivos")
        form = QtWidgets.QFormLayout()

        self.combo_soundcard = QtWidgets.QComboBox()
        self.combo_soundcard.setMinimumWidth(200)

        self.combo_radio = QtWidgets.QComboBox()
        self.combo_radio.setMinimumWidth(200)
        self.combo_radio.addItem("Waiting for radios...")
        self.combo_radio.setEnabled(False)

        self.input_command = QtWidgets.QLineEdit("SEND COMMAND")
        self.input_target = QtWidgets.QLineEdit("101")
        self.input_value = QtWidgets.QLineEdit("25.0")

        self.btn_send = QtWidgets.QPushButton("Send Command")

        form.addRow("Soundcard:", self.combo_soundcard)
        form.addRow("Radio:", self.combo_radio)
        form.addRow("Command:", self.input_command)
        form.addRow("Target ID:", self.input_target)
        form.addRow("Value:", self.input_value)
        form.addRow("", self.btn_send)

        group.setLayout(form)
        return group

    # -------------------------------
    # Signal Connections
    # -------------------------------
    def _connect_signals(self):
        """Connects UI events to logic."""
        self.btn_send.clicked.connect(self._on_send_command)
        self.btn_usb.clicked.connect(lambda: self._send_mode_command("USB"))
        self.btn_lsb.clicked.connect(lambda: self._send_mode_command("LSB"))
        self.combo_soundcard.currentTextChanged.connect(self._on_soundcard_changed)
        self.combo_radio.currentTextChanged.connect(self._on_radio_changed)

    # -------------------------------
    # Event Handlers
    # -------------------------------
    @QtCore.Slot(dict)
    def handle_json_data(self, data: dict):
        """Process received JSON messages."""
        msg_type = data.get("type")

        handlers = {
            "soundcard_list": self.handle_soundcard_data,
            "radio_list": self.handle_radio_data,
            # "status": self.handle_status_data, # for future extension
        }

        handler = handlers.get(msg_type)
        if handler:
            handler(data)
        else:
            print(f"Unknown message type: {msg_type}")

    @QtCore.Slot(dict)
    def update_detail_view(self, data: dict):
        """Update JSON details viewer."""
        self.json_detail_view.update_json_data(data)

    # -------------------------------
    # Data Handlers
    # -------------------------------
    def handle_soundcard_data(self, data: dict):
        """Update soundcard list in UI."""
        self.soundcards = data.get("list", [])
        self.selected_soundcard = data.get("selected", "")

        self.combo_soundcard.blockSignals(True)
        self.combo_soundcard.clear()
        self.combo_soundcard.addItems(self.soundcards)
        if self.selected_soundcard in self.soundcards:
            index = self.soundcards.index(self.selected_soundcard)
            self.combo_soundcard.setCurrentIndex(index)
        self.combo_soundcard.blockSignals(False)

    def handle_radio_data(self, data: dict):
        """Update radio list in UI."""
        self.radios = data.get("list", [])
        self.selected_radio = data.get("selected", "")

        self.combo_radio.blockSignals(True)
        self.combo_radio.clear()
        self.combo_radio.addItems(self.radios)
        if self.selected_radio in self.radios:
            index = self.radios.index(self.selected_radio)
            self.combo_radio.setCurrentIndex(index)
        self.combo_radio.setEnabled(bool(self.radios))
        self.combo_radio.blockSignals(False)

    # -------------------------------
    # UI Event Logic
    # -------------------------------
    def _on_send_command(self):
        """Send a command to the UDP client."""
        command = self.input_command.text()
        target = self.input_target.text()
        value = self.input_value.text()

        msg = {"command": command, "target": target, "value": value}
        print(f"Sending command: {msg}")  # replace with actual UDP send
        self.client.send_json(msg)

    def _on_soundcard_changed(self, value: str):
        self.selected_soundcard = value
        print(f"Selected soundcard: {value}")

    def _on_radio_changed(self, value: str):
        self.selected_radio = value
        print(f"Selected radio: {value}")

    def _send_mode_command(self, mode: str):
        """Example action for USB/LSB buttons."""
        msg = {"command": "set_mode", "mode": mode}
        print(f"Sending mode command: {msg}")
        self.client.send_json(msg)

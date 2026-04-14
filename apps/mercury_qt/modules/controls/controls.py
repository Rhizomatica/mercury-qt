from PySide6 import QtWidgets, QtCore, QtGui
from core.components.combobox import ComboBox

class RadioControls(QtWidgets.QWidget):
    """Componente que agrega os controles de Soundcard e Radio."""

    # Signal emitted when Apply is clicked with both radio model and device path
    radio_config_command = QtCore.Signal(dict)
    # Signal emitted when audio Apply is clicked with capture/playback/channel
    audio_config_command = QtCore.Signal(dict)
    # Signal emitted when the Connect button is clicked with valid host and port
    connect_requested = QtCore.Signal(str, int)

    def __init__(self):
        super().__init__()

        self.capture_dev_control = ComboBox("capture_dev")
        self.playback_dev_control = ComboBox("playback_dev")
        self.input_channel_control = ComboBox("input_channel")
        self.radio_control = ComboBox("radio_model")

        # Prevent audio ComboBoxes from auto-sending on selection change
        self._disable_auto_emit(self.capture_dev_control)
        self._disable_auto_emit(self.playback_dev_control)
        self._disable_auto_emit(self.input_channel_control)

        # Prevent the radio ComboBox from auto-sending on selection change
        self._disable_auto_emit(self.radio_control)

        # Plain QLineEdit for device path
        self.device_path_line_edit = QtWidgets.QLineEdit()
        self.device_path_line_edit.setMaxLength(255)
        self.device_path_line_edit.setPlaceholderText(
            "/dev/ttyUSB0 or 127.0.0.1:4532")

        # Baud Rate ComboBox (fixed options, no auto-emit needed)
        self.baud_rate_control = QtWidgets.QComboBox()
        self.baud_rate_control.addItem("Auto", "0")
        self.baud_rate_control.addItem("4800", "4800")
        self.baud_rate_control.addItem("9600", "9600")
        self.baud_rate_control.addItem("19200", "19200")
        self.baud_rate_control.addItem("38400", "38400")
        self.baud_rate_control.addItem("115200", "115200")

        # Apply button for audio config (capture/playback/channel)
        self.audio_apply_button = QtWidgets.QPushButton("Apply")
        self.audio_apply_button.clicked.connect(self._on_audio_apply)

        # Track applied audio values so backend refreshes don't lose user choices
        self._applied_capture_dev = ""
        self._applied_playback_dev = ""
        self._applied_input_channel = ""

        # Shared Apply button for HAMLIB radio model + device file path
        self.radio_apply_button = QtWidgets.QPushButton("Apply")
        self.radio_apply_button.clicked.connect(self._on_radio_apply)
        self.device_path_line_edit.returnPressed.connect(self._on_radio_apply)

        # Track applied values so backend refreshes don't lose user choices
        self._applied_radio_model = ""
        self._applied_device_path = ""
        self._applied_baud_rate = ""

        # Host / Port / Connect
        self.host_line_edit = QtWidgets.QLineEdit()
        self.host_line_edit.setMaxLength(255)
        self.host_line_edit.setPlaceholderText("127.0.0.1")

        self.port_line_edit = QtWidgets.QLineEdit()
        self.port_line_edit.setMaxLength(5)
        self.port_line_edit.setPlaceholderText("10000")
        self.port_line_edit.setValidator(QtGui.QIntValidator(1, 65535, self))

        self.connect_button = QtWidgets.QPushButton("Connect")
        self.connect_button.clicked.connect(self._on_connect_clicked)
        self.host_line_edit.returnPressed.connect(self._on_connect_clicked)
        self.port_line_edit.returnPressed.connect(self._on_connect_clicked)

        controls_layout = QtWidgets.QVBoxLayout()

        # Audio config section with shared Apply button
        audio_layout = QtWidgets.QVBoxLayout()

        # Radio Capture Device
        capture_label = QtWidgets.QLabel("Capture Device")
        audio_layout.addWidget(capture_label)
        audio_layout.addWidget(self.capture_dev_control)

        # Radio Playback Device
        playback_label = QtWidgets.QLabel("Playback Device")
        audio_layout.addWidget(playback_label)
        audio_layout.addWidget(self.playback_dev_control)

        # Capture Input Channel
        input_channel_label = QtWidgets.QLabel("Capture Input Channel")
        audio_layout.addWidget(input_channel_label)
        audio_layout.addWidget(self.input_channel_control)

        audio_layout.addWidget(self.audio_apply_button)

        audio_box = QtWidgets.QGroupBox()
        audio_box.setLayout(audio_layout)

        controls_layout.addWidget(audio_box)

        # Visually separated HAMLIB Radio Models + Device Path section
        hamlib_layout = QtWidgets.QVBoxLayout()

        radio_model_label = QtWidgets.QLabel("HAMLIB Model")
        hamlib_layout.addWidget(radio_model_label)
        hamlib_layout.addWidget(self.radio_control)

        device_path_label = QtWidgets.QLabel("Device Path")
        hamlib_layout.addWidget(device_path_label)
        hamlib_layout.addWidget(self.device_path_line_edit)

        baud_rate_label = QtWidgets.QLabel("Baud Rate")
        hamlib_layout.addWidget(baud_rate_label)
        hamlib_layout.addWidget(self.baud_rate_control)

        hamlib_layout.addWidget(self.radio_apply_button)

        hamlib_box = QtWidgets.QGroupBox() # no need title to this section
        hamlib_box.setLayout(hamlib_layout)

        controls_layout.addWidget(hamlib_box)

        # Connection section
        connection_layout = QtWidgets.QVBoxLayout()

        host_label = QtWidgets.QLabel("Host")
        connection_layout.addWidget(host_label)
        connection_layout.addWidget(self.host_line_edit)

        port_label = QtWidgets.QLabel("Port")
        connection_layout.addWidget(port_label)
        connection_layout.addWidget(self.port_line_edit)

        connection_layout.addWidget(self.connect_button)

        connection_box = QtWidgets.QGroupBox()
        connection_box.setLayout(connection_layout)

        controls_layout.addWidget(connection_box)

        controls_layout.addStretch()

        self.group_box = QtWidgets.QGroupBox("Radio Controls")
        self.group_box.setLayout(controls_layout)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.group_box)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

    # ---- Apply audio config ----

    def _on_audio_apply(self):
        """Send combined capture/playback/channel config to the backend."""
        capture_dev = self._get_selected_value(self.capture_dev_control) or "default"
        playback_dev = self._get_selected_value(self.playback_dev_control) or "default"
        input_channel = self._get_selected_value(self.input_channel_control) or "left"

        # Persist the applied values for later restoration
        self._applied_capture_dev = capture_dev
        self._applied_playback_dev = playback_dev
        self._applied_input_channel = input_channel

        command = {
            "command": "set_audio_config",
            "value": capture_dev,
            "value2": playback_dev,
            "value3": input_channel,
        }
        self.audio_config_command.emit(command)

    def _get_selected_value(self, control: ComboBox) -> str:
        """Return the currently selected value (userData) of a ComboBox."""
        idx = control.combo_box.currentIndex()
        if idx < 0:
            return ""
        val = control.combo_box.itemData(idx)
        return "" if val is None else str(val)

    # ---- Apply radio config ----

    def _on_radio_apply(self):
        """Send combined radio model + device path + baud rate to the backend."""
        model_id = self._get_selected_radio_id()
        device_path = self.device_path_line_edit.text().strip()
        baud_rate = self.baud_rate_control.currentData() or "0"

        if not model_id:
            return

        # Persist the applied values for later restoration
        self._applied_radio_model = model_id
        self._applied_device_path = device_path
        self._applied_baud_rate = baud_rate

        if model_id == "-1":
            self.device_path_line_edit.clear()

        command = {
            "command": "set_radio_config",
            "value": model_id,
            "value2": device_path,
            "value3": baud_rate,
        }
        self.radio_config_command.emit(command)

    def _get_selected_radio_id(self) -> str:
        """Return the currently selected radio model id (userData)."""
        idx = self.radio_control.combo_box.currentIndex()
        if idx < 0:
            return ""
        val = self.radio_control.combo_box.itemData(idx)
        return "" if val is None else str(val)
    
    def _disable_auto_emit(self, control: ComboBox):
        """Safely disable automatic emission on selection change for a ComboBox.
        This avoids relying on the presence of a specific internal handler or
        connection; if either is missing, it simply becomes a no-op.
        """
        handler = getattr(control, "_on_index_changed", None)
        if handler is None:
            return
        try:
            control.combo_box.currentIndexChanged.disconnect(handler)
        except (TypeError, RuntimeError):
            # If handler not connected or signal is invalid, treat as a no-op.
            pass

    # ---- Public helpers for main.py ----

    def clear_applied_state(self):
        """Discard remembered selections so the next backend push is used as-is.

        Call this when the backend restarts so stale UI choices don't override
        the fresh configuration data sent on reconnect.
        """
        self._applied_capture_dev = ""
        self._applied_playback_dev = ""
        self._applied_input_channel = ""
        self._applied_radio_model = ""
        self._applied_device_path = ""
        self._applied_baud_rate = ""

    def reset_controls(self):
        """Clear all dropdowns and text fields so no stale UI state remains."""
        for ctrl in (self.capture_dev_control, self.playback_dev_control,
                     self.input_channel_control, self.radio_control):
            ctrl.combo_box.blockSignals(True)
            ctrl.combo_box.clear()
            ctrl.combo_box.blockSignals(False)
        self.device_path_line_edit.clear()
        self.baud_rate_control.setCurrentIndex(0)

    def restore_radio_selection(self):
        """After the radio list is repopulated, restore the previously applied
        selection so it stays in sync with the backend."""
        if self._applied_radio_model:
            self.radio_control.set_selected(self._applied_radio_model)
        if self._applied_device_path:
            self.device_path_line_edit.setText(self._applied_device_path)
        if self._applied_baud_rate:
            self.set_baud_rate(self._applied_baud_rate)

    def restore_audio_selection(self):
        """After device lists are repopulated, restore the previously applied
        audio selections so they stay in sync with the backend."""
        if self._applied_capture_dev:
            self.capture_dev_control.set_selected(self._applied_capture_dev)
        if self._applied_playback_dev:
            self.playback_dev_control.set_selected(self._applied_playback_dev)
        if self._applied_input_channel:
            self.input_channel_control.set_selected(self._applied_input_channel)

    def set_device_path_text(self, text: str):
        """Set device path without triggering signals (initial sync)."""
        if not self._applied_device_path:
            self.device_path_line_edit.setText(text)

    def set_baud_rate(self, value: str):
        """Set baud rate ComboBox by value string (e.g. '0', '9600')."""
        idx = self.baud_rate_control.findData(value)
        if idx >= 0:
            self.baud_rate_control.setCurrentIndex(idx)

    def get_radio_control(self) -> ComboBox:
        return self.radio_control

    def get_capture_dev_control(self) -> ComboBox:
        return self.capture_dev_control

    def get_playback_dev_control(self) -> ComboBox:
        return self.playback_dev_control

    def get_input_channel_control(self) -> ComboBox:
        return self.input_channel_control

    def set_connection_defaults(self, host: str, port: int):
        """Populate the Host and Port fields with initial values."""
        self.host_line_edit.setText(host)
        self.port_line_edit.setText(str(port))

    def _on_connect_clicked(self):
        """Validate host and port fields, then emit connect_requested."""
        host = self.host_line_edit.text().strip()
        port_text = self.port_line_edit.text().strip()
        if not host or not port_text:
            return
        try:
            port = int(port_text)
        except ValueError:
            return
        self.connect_requested.emit(host, port)

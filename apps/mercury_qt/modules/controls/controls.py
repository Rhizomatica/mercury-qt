from PySide6 import QtWidgets, QtCore
from core.components.combobox import ComboBox

class RadioControls(QtWidgets.QWidget):
    """Componente que agrega os controles de Soundcard e Radio."""

    # Signal emitted when Apply is clicked with both radio model and device path
    radio_config_command = QtCore.Signal(dict)

    def __init__(self):
        super().__init__()

        self.capture_dev_control = ComboBox("capture_dev")
        self.playback_dev_control = ComboBox("playback_dev")
        self.input_channel_control = ComboBox("input_channel")
        self.radio_control = ComboBox("radio_model")

        # Prevent the radio ComboBox from auto-sending on selection change
        self.radio_control.combo_box.currentIndexChanged.disconnect(
            self.radio_control._on_index_changed)

        # Plain QLineEdit for device path
        self.device_path_line_edit = QtWidgets.QLineEdit()
        self.device_path_line_edit.setMaxLength(255)
        self.device_path_line_edit.setPlaceholderText(
            "/dev/ttyUSB0 or 127.0.0.1:4532")

        # Shared Apply button for HAMLIB radio model + device file path
        self.radio_apply_button = QtWidgets.QPushButton("Apply")
        self.radio_apply_button.clicked.connect(self._on_radio_apply)
        self.device_path_line_edit.returnPressed.connect(self._on_radio_apply)

        # Track applied values so backend refreshes don't lose user choices
        self._applied_radio_model = ""
        self._applied_device_path = ""

        controls_layout = QtWidgets.QVBoxLayout()

        # Radio Capture Device
        capture_label = QtWidgets.QLabel("Capture Device")
        controls_layout.addWidget(capture_label)
        controls_layout.addWidget(self.capture_dev_control)

        # Radio Playback Device
        playback_label = QtWidgets.QLabel("Playback Device")
        controls_layout.addWidget(playback_label)
        controls_layout.addWidget(self.playback_dev_control)

        # Capture Input Channel
        input_channel_label = QtWidgets.QLabel("Capture Input Channel")
        controls_layout.addWidget(input_channel_label)
        controls_layout.addWidget(self.input_channel_control)

        # Visually separated HAMLIB Radio Models + Device Path section
        hamlib_layout = QtWidgets.QVBoxLayout()

        radio_model_label = QtWidgets.QLabel("HAMLIB Model")
        hamlib_layout.addWidget(radio_model_label)
        hamlib_layout.addWidget(self.radio_control)

        device_path_label = QtWidgets.QLabel("Device Path")
        hamlib_layout.addWidget(device_path_label)
        hamlib_layout.addWidget(self.device_path_line_edit)

        hamlib_layout.addWidget(self.radio_apply_button)

        hamlib_box = QtWidgets.QGroupBox() # no need title to this section
        hamlib_box.setLayout(hamlib_layout)

        controls_layout.addWidget(hamlib_box)

        controls_layout.addStretch()

        self.group_box = QtWidgets.QGroupBox("Radio Controls")
        self.group_box.setLayout(controls_layout)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.group_box)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

    # ---- Apply radio config ----

    def _on_radio_apply(self):
        """Send combined radio model + device path to the backend."""
        model_id = self._get_selected_radio_id()
        device_path = self.device_path_line_edit.text().strip()

        if not model_id or not device_path:
            return  # both fields required

        # Persist the applied values for later restoration
        self._applied_radio_model = model_id
        self._applied_device_path = device_path

        command = {
            "command": "set_radio_config",
            "value": model_id,
            "value2": device_path,
        }
        self.radio_config_command.emit(command)

    def _get_selected_radio_id(self) -> str:
        """Return the currently selected radio model id (userData)."""
        idx = self.radio_control.combo_box.currentIndex()
        if idx < 0:
            return ""
        val = self.radio_control.combo_box.itemData(idx)
        return str(val) if val else ""

    # ---- Public helpers for main.py ----

    def restore_radio_selection(self):
        """After the radio list is repopulated, restore the previously applied
        selection so it stays in sync with the backend."""
        if self._applied_radio_model:
            self.radio_control.set_selected(self._applied_radio_model)
        if self._applied_device_path:
            self.device_path_line_edit.setText(self._applied_device_path)

    def set_device_path_text(self, text: str):
        """Set device path without triggering signals (initial sync)."""
        if not self._applied_device_path:
            self.device_path_line_edit.setText(text)

    def get_radio_control(self) -> ComboBox:
        return self.radio_control

    def get_capture_dev_control(self) -> ComboBox:
        return self.capture_dev_control

    def get_playback_dev_control(self) -> ComboBox:
        return self.playback_dev_control

    def get_input_channel_control(self) -> ComboBox:
        return self.input_channel_control

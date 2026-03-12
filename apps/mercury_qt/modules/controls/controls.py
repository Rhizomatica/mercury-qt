from PySide6 import QtWidgets, QtCore, QtGui
from core.components.combobox import ComboBox  # IMPORT ABSOLUTO

#TODO - Renomear para Controls
class Controls(QtWidgets.QWidget):
    """Componente que agrega os controles de Soundcard e Radio."""

    def __init__(self):
        super().__init__()

        self.capture_dev_control = ComboBox("capture_dev")
        self.playback_dev_control = ComboBox("playback_dev")
        self.input_channel_control = ComboBox("input_channel")
        self.radio_control = ComboBox("radio")

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

        # HAMLIB Model
        radio_model_label = QtWidgets.QLabel("HAMLIB Model")
        controls_layout.addWidget(radio_model_label)
        controls_layout.addWidget(self.radio_control)

        controls_layout.addStretch()

        self.group_box = QtWidgets.QGroupBox("Radio Controls")
        self.group_box.setLayout(controls_layout)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.group_box)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

    def get_radio_control(self) -> ComboBox:
        return self.radio_control

    def get_capture_dev_control(self) -> ComboBox:
        return self.capture_dev_control

    def get_playback_dev_control(self) -> ComboBox:
        return self.playback_dev_control

    def get_input_channel_control(self) -> ComboBox:
        return self.input_channel_control

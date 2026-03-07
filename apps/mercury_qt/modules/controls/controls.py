from PySide6 import QtWidgets, QtCore, QtGui
from core.components.combobox import ComboBox  # IMPORT ABSOLUTO

#TODO - Renomear para Controls
class Controls(QtWidgets.QWidget):
    """Componente que agrega os controles de Soundcard e Radio."""

    def __init__(self):
        super().__init__()

        self.soundcard_control = ComboBox("soundcard")
        self.radio_control = ComboBox("radio")

        controls_layout = QtWidgets.QVBoxLayout()
        controls_layout.addWidget(self.soundcard_control)
        controls_layout.addWidget(self.radio_control)
        controls_layout.addStretch()

        self.group_box = QtWidgets.QGroupBox("Controls")
        self.group_box.setLayout(controls_layout)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.group_box)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

    def get_radio_control(self) -> ComboBox:
        return self.radio_control

    def get_soundcard_control(self) -> ComboBox:
        return self.soundcard_control

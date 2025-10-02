from PySide6 import QtWidgets, QtCore

class StatusFlag(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.set_status(None) 

    @QtCore.Slot(bool)
    def set_status(self, connected: bool | None):
        if connected is True:
            self.setStyleSheet("border-radius: 10px; background-color: lightgreen;")
            self.setToolTip("Client TCP Connected: True")
        elif connected is False:
            self.setStyleSheet("border-radius: 10px; background-color: lightcoral;")
            self.setToolTip("Client TCP Connected: False")
        else: # None or other unexpected value
            self.setStyleSheet("border-radius: 10px; background-color: lightgray;")
            self.setToolTip("Client TCP Connected: N/A")
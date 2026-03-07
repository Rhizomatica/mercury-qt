from PySide6 import QtWidgets, QtCore
from core.components.json_detail_view import JsonDetailView

class ConnectionInfo(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.json_detail = JsonDetailView()
        self.connection_group = QtWidgets.QGroupBox("Connection Info.")
        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.json_detail, 0, 0)
        self.connection_group.setLayout(layout)

    @QtCore.Slot(dict)
    def handle_connection_info(self, data: dict):
        # Remove SNR and Sync from connection info — both shown in the waterfall section
        exclude = {"snr", "sync"}
        filtered_data = {k: v for k, v in data.items() if k.lower() not in exclude}
        self.json_detail.update_json_data(filtered_data)
        return self.connection_group
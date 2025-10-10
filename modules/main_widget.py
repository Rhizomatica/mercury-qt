from PySide6 import QtCore, QtWidgets, QtGui # Import QtGui for QPixmap
from modules.radio.view.json_detail_view import JsonDetailView
import sys

import modules.connection.udp.client as Client_UDP

class MockClientUDP(QtCore.QObject):
    json_received = QtCore.Signal(dict)

    def __init__(self):
        super().__init__()
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._send_mock_json)
        self._counter = 0

    def start_udp_client(self):
        print("Mock UDP client started.")
        self._timer.start(2000)

    def _send_mock_json(self):
        self._counter += 1
        mock_data = {
            "timestamp": QtCore.QDateTime.currentDateTime().toString(QtCore.Qt.ISODate),
            "sequence": self._counter,
            "sensor_data": {
                "temperature": 25.5 + (self._counter % 5),
                "humidity": 60.0 - (self._counter % 7),
                "pressure": 1012.3 + (self._counter % 3)
            },
            "status": "active" if self._counter % 2 == 0 else "idle"
        }
        self.json_received.emit(mock_data)


class MainWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mercury Qt Client")
        self.setGeometry(100, 100, 900, 600)

        self.client = Client_UDP.ClientUDP()
        # self.client = MockClientUDP()
        self.client.json_received.connect(self.handle_json_data)
        self.client.json_received.connect(self.update_detail_view)
        self.client.start_udp_client()

        main_overall_layout = QtWidgets.QVBoxLayout(self)
        columns_h_layout = QtWidgets.QHBoxLayout()
        original_content_group_box = QtWidgets.QGroupBox("UDP Data Stream")
        original_column_layout = QtWidgets.QVBoxLayout(original_content_group_box)

        self.json_detail_view = JsonDetailView()
        original_column_layout.addWidget(self.json_detail_view)
        self.json_detail_view.update_json_data({"message": "Waiting for UDP data..."})

        original_content_group_box.setLayout(original_column_layout)
        columns_h_layout.addWidget(original_content_group_box, 1)

        inputs_group_box = QtWidgets.QGroupBox("Control Inputs")

        #NEW FORM COMPONENT
        inputs_column_layout = QtWidgets.QFormLayout(inputs_group_box)
        inputs_column_layout.addRow("Command:", QtWidgets.QLineEdit("SEND COMMAND"))
        inputs_column_layout.addRow("Target ID:", QtWidgets.QLineEdit("101"))
        inputs_column_layout.addRow("Value:", QtWidgets.QLineEdit("25.0"))

        send_button = QtWidgets.QPushButton("Send Command")
        inputs_column_layout.addRow("", send_button)
        inputs_group_box.setLayout(inputs_column_layout)

        columns_h_layout.addWidget(inputs_group_box, 1)
        main_overall_layout.addLayout(columns_h_layout)


        #LOGO
        self.logo_label = QtWidgets.QLabel(self)
        logo_pixmap = QtGui.QPixmap("./assets/Rhizomatica.jpeg")
        scaled_pixmap = logo_pixmap.scaled(25, 25, 
                                           QtCore.Qt.AspectRatioMode.KeepAspectRatio, 
                                           QtCore.Qt.TransformationMode.SmoothTransformation)
        self.logo_label.setPixmap(scaled_pixmap)

        main_overall_layout.addWidget(self.logo_label, 0, 
                                      QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignRight)

        self.setLayout(main_overall_layout)


    @QtCore.Slot(dict)
    def handle_json_data(self, data: dict):
        print("\n--- Received JSON Data in MainWidget ---")
        print(data)
        print("---------------------------------------\n")

    @QtCore.Slot(dict)
    def update_detail_view(self, data: dict):
        self.json_detail_view.update_json_data(data)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    widget = MainWidget()
    widget.show()
    sys.exit(app.exec())
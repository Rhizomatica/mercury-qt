from PySide6 import QtCore, QtWidgets
import modules.connection.udp.client as Client_UDP
from modules.radio.view.json_detail_view import JsonDetailView


class MainWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.client = Client_UDP.ClientUDP()
        self.client.json_received.connect(self.handle_json_data)
        self.client.json_received.connect(self.update_detail_view)
        self.client.start_udp_client() 
        
        self.hello = "Hello from mercury qt client"
        self.layout = QtWidgets.QVBoxLayout(self)
        
        self.json_detail_view = JsonDetailView()
        self.layout.addWidget(self.json_detail_view)
        self.json_detail_view.update_json_data({"message": "Waiting for UDP data..."})

        self.setLayout(self.layout)
        

    # @QtCore.Slot()
    # def magic(self):
    #     response = self.client.send_message(self.input.text())
    #     self.text.setText(response)

    @QtCore.Slot(dict)
    def handle_json_data(self, data: dict):
        print("\n--- Received JSON Data in MainWidget ---")
        print(data)
        print("---------------------------------------\n")
        
    @QtCore.Slot(dict)
    def update_detail_view(self, data: dict):
        self.json_detail_view.update_json_data(data)
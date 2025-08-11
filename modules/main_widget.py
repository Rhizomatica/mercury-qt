from PySide6 import QtCore, QtWidgets, QtGui

import modules.udp.client as client
import modules.components.bar_chart as bar_chart


class MainWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.client = client.ClientUDP()
        self.client.start_udp_client() 
        
        self.hello = "Hello from mercury qt client"
        
        self.text = QtWidgets.QTextEdit("Type and send a message to the UDP server.", readOnly=True)
        self.text.setMaximumHeight(60)

        self.input = QtWidgets.QLineEdit()
        self.input.setMaxLength(50)
        self.button = QtWidgets.QPushButton("Send message via UDP socket")
        self.layout = QtWidgets.QVBoxLayout(self)
        self.barChart = bar_chart.BarChartWidget()
        
        self.layout.addWidget(self.barChart)
        self.layout.addWidget(self.text)
        self.layout.addWidget(self.input)
        self.layout.addWidget(self.button)

        self.button.clicked.connect(self.magic)

    @QtCore.Slot()
    def magic(self):
        response = self.client.send_message(self.input.text())
        self.text.setText(response)
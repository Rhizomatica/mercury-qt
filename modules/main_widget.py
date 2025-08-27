from PySide6 import QtCore, QtWidgets, QtGui

# import modules.connection.udp.client as client
# import modules.components.bar_chart as bar_chart
# import modules.components.scatter_chart as scatter_chart
# import modules.components.gauge_chart as gauge_chart
# import modules.fruits.model.fruits_model as Fruits_Model
# import modules.fruits.view.fruits_view as Fruits_View
import modules.radio.model.radio_model as Radio_Model
import modules.radio.view.radio_view as Radio_View


class MainWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # self.client = client.ClientUDP()
        # self.client.start_udp_client() 
        
        self.hello = "Hello from mercury qt client"
        self.layout = QtWidgets.QVBoxLayout(self)
        
        # self.text = QtWidgets.QTextEdit("Type and send a message to the UDP server.", readOnly=True)
        # self.text.setMaximumHeight(60)

        # self.input = QtWidgets.QLineEdit()
        # self.input.setMaxLength(50)
        # self.button = QtWidgets.QPushButton("Send message via UDP socket")
        # self.barChart = bar_chart.BarChartWidget()
        # self.scatterChart = scatter_chart.ScatterChartWidget()
        # self.gaugeChart = gauge_chart.GaugeChartWidget()
        
        # self.initial_fruits = ["Apple", "Banana", "Cherry"]
        # self.fruit_model = Fruits_Model.FruitModel(self.initial_fruits)
        # self.fruit_view = Fruits_View.FruitView(self.fruit_model)
        
         # Initial data as a list of dictionaries (can come from a loaded JSON file)
        initial_data = [
            {"name": "Apple", "color": "red"},
            {"name": "Banana", "color": "yellow"},
            {"name": "Blueberry", "color": "blue"},
        ]        
        self.json_model = Radio_Model.JsonListModel(initial_data)
        self.json_view = Radio_View.JsonItemView(self.json_model)
        
        # self.layout.addWidget(self.barChart)
        # self.layout.addWidget(self.scatterChart)
        # self.layout.addWidget(self.gaugeChart)
        # self.layout.addWidget(self.text)
        # self.layout.addWidget(self.input)
        # self.layout.addWidget(self.button)
        # self.layout.addWidget(self.fruit_view)
        self.layout.addWidget(self.json_view)

        self.json_view.show()
        self.setLayout(self.layout)

    #     self.button.clicked.connect(self.magic)

    # @QtCore.Slot()
    # def magic(self):
    #     response = self.client.send_message(self.input.text())
    #     self.text.setText(response)
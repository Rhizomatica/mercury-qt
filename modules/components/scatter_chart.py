import sys
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCharts import (
    QChart,
    QChartView,
    QScatterSeries,
    QValueAxis,
)
from PySide6.QtGui import QPainter

class ScatterChartWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # Create the first scatter series
        series0 = QScatterSeries()
        series0.setName("scatter1")
        series0.setMarkerShape(QScatterSeries.MarkerShape.MarkerShapeCircle)
        series0.setMarkerSize(15.0)

        # Add data to the first series
        series0.append(0, 6)
        series0.append(2, 4)
        series0.append(3, 8)
        series0.append(7, 4)
        series0.append(10, 5)

        # Create the second scatter series
        series1 = QScatterSeries()
        series1.setName("scatter2")
        series1.setMarkerShape(QScatterSeries.MarkerShape.MarkerShapeRectangle)
        series1.setMarkerSize(10.0)

        # Add data to the second series
        for i in range(10):
            series1.append(i, i)


        # Create the chart and add the series
        chart = QChart()
        chart.addSeries(series0)
        chart.addSeries(series1)
        chart.setTitle("Simple Scatter Chart")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        # Create and customize the X axis
        axis_x = QValueAxis()
        axis_x.setRange(-2, 12)
        chart.addAxis(axis_x, QtCore.Qt.AlignmentFlag.AlignBottom)
        series0.attachAxis(axis_x)
        series1.attachAxis(axis_x)

        # Create and customize the Y axis
        axis_y = QValueAxis()
        axis_y.setRange(0, 15)
        chart.addAxis(axis_y, QtCore.Qt.AlignmentFlag.AlignLeft)
        series0.attachAxis(axis_y)
        series1.attachAxis(axis_y)

        # Customize the legend
        chart.legend().setVisible(True)
        chart.legend().setAlignment(QtCore.Qt.AlignmentFlag.AlignBottom)

        # Create the chart view and set render hints
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Set the layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(chart_view)

# if __name__ == "__main__":
#     app = QtWidgets.QApplication(sys.argv)
#     widget = ScatterChartWidget()
#     widget.resize(800, 600)
#     widget.show()
#     sys.exit(app.exec())
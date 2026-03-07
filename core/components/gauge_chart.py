import sys
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCharts import (
    QChart,
    QChartView,
    QPieSeries,
)
from PySide6.QtGui import QPainter, QFont, QColor

class GaugeChartWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # --- Chart Configuration ---
        self.min_value = 0
        self.max_value = 100
        self.current_value = 60
        self.unit = " kg"

        # --- Series for the Gauge Background ---
        background_series = QPieSeries()
        background_series.setHoleSize(0.65)
        background_series.setPieSize(1.0)
        # Define the arc on the left side: from top (90) to bottom (270)
        background_series.setPieStartAngle(-90)
        background_series.setPieEndAngle(90)

        # A single slice for the background color
        background_slice = background_series.append("", self.max_value)
        background_slice.setBrush(QColor("#e0e0e0"))
        background_slice.setBorderColor(QColor("#e0e0e0"))

        # --- Series for the Gauge Value ---
        value_series = QPieSeries()
        value_series.setHoleSize(0.65)
        value_series.setPieSize(1.0)
        # Use the same arc definition
        value_series.setPieStartAngle(-90)
        value_series.setPieEndAngle(90)
        

        # --- THIS IS THE KEY CORRECTION ---
        # 1. Append the EMPTY part of the series first. This is invisible.
        #    It will occupy the space from the top (90 deg) downwards.
        remaining_slice = value_series.append("", self.max_value - self.current_value)

        remaining_slice.setBrush(QColor("#FF7B00"))
        remaining_slice.setBorderColor(QColor("#FF7B00"))

        # 2. Append the VISIBLE value part second.
        #    It will be drawn after the empty space, occupying the bottom part of the arc.
        value_slice = value_series.append("", self.current_value)
        value_slice.setBrush(QColor("#FFE5CD"))
        value_slice.setBorderColor(QColor("#000000"))


        # --- Chart Creation ---
        chart = QChart()
        chart.addSeries(background_series)
        chart.addSeries(value_series)
        chart.setTitle("Silo Contents")
        chart.legend().setVisible(False)
        chart.setBackgroundRoundness(0)
        chart.setBackgroundBrush(QtCore.Qt.BrushStyle.NoBrush)


        # --- Text Label in the Center ---
        self.label = QtWidgets.QLabel(f"{self.current_value}{self.unit}", self)
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        font = QFont("Arial", 22, QFont.Weight.Bold)
        self.label.setFont(font)
        # Adjust margin to center it in the arc
        self.label.setContentsMargins(0, 0, 70, 0)


        # --- Chart View ---
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)

        # --- Layout ---
        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(chart_view, 0, 0)
        layout.addWidget(self.label, 0, 0)
        layout.setContentsMargins(0, 0, 0, 0)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()
    gauge = BottomUpGaugeWidget()
    window.setCentralWidget(gauge)
    window.resize(350, 500)
    window.show()
    sys.exit(app.exec())
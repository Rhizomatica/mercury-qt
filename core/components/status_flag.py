from PySide6 import QtWidgets, QtCore, QtGui

class StatusFlag(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QtGui.QColor("lightgray")
        self.setFixedSize(120, 25)
        self.setToolTip("Client TCP Connected: N/A")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(14, 2, 0, 0)
        main_layout.setSpacing(5)

        self.circle_widget = CircleIndicator(self)
        self.circle_widget.setFixedSize(2 * 8, 2 * 8)
        main_layout.addWidget(self.circle_widget, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter)

        self.status_label = QtWidgets.QLabel("N/A", self)
        self.status_label.setStyleSheet("font-size: 10pt;")
        main_layout.addWidget(self.status_label, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft)

        self.setLayout(main_layout)

    @QtCore.Slot(bool)
    def set_status(self, connected: bool | None):
        if connected is True:
            self.circle_widget.set_color(QtGui.QColor("lightgreen"))
            new_tooltip = "Client TCP Connected: True"
            self.status_label.setText("On")
            self.status_label.setStyleSheet("color: lightgreen")
        elif connected is False:
            self.circle_widget.set_color(QtGui.QColor("lightcoral"))
            new_tooltip = "Client TCP Connected: False"
            self.status_label.setText("Off")
            self.status_label.setStyleSheet("color: lightcoral")
        else:
            self.circle_widget.set_color(QtGui.QColor("lightgray"))
            new_tooltip = "Client TCP Connected: N/A"
            self.status_label.setText("N/A")
            self.status_label.setStyleSheet("color: lightgray")

        self.setToolTip(new_tooltip)

class CircleIndicator(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QtGui.QColor("lightgray")
        self.radius = 8

    def set_color(self, color: QtGui.QColor):
        if self._color != color:
            self._color = color
            self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setBrush(QtGui.QBrush(self._color))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)

        x = (self.width() - self.radius * 2) / 2
        y = (self.height() - self.radius * 2) / 2
        painter.drawEllipse(x, y, self.radius * 2, self.radius * 2)
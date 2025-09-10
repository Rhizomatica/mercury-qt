from PySide6 import QtWidgets, QtCore

class JsonDetailView(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QFormLayout(self)
        self.setLayout(self.layout)
        self.labels = {}

        self.setWindowTitle("JSON Details")

        self.title_label = QtWidgets.QLabel("<b>Radio Status</b>")
        self.layout.addRow(self.title_label)
        self.layout.addRow(QtWidgets.QFrame())

    @QtCore.Slot(dict)
    def update_json_data(self, data: dict):
        current_label_keys = set(self.labels.keys())
        incoming_data_keys = set(data.keys())

        if not current_label_keys or current_label_keys != incoming_data_keys:
            self._create_fields(data)
        
        self._update_field_values(data)
        
    def _create_fields(self, data: dict):
        while self.layout.count() > 2: # Items after title and separator
            item = self.layout.takeAt(self.layout.count() - 1)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
                item.layout().deleteLater()
        
        self.labels.clear()

        for key in data.keys():
            # If we received "Waiting for UDP data..."
            if key == "message" and "type" not in data:
                continue 
                
            key_label = QtWidgets.QLabel(f"<b>{key.replace('_', ' ').capitalize().upper()}:</b>")
            value_label = QtWidgets.QLabel("N/A")
            self.layout.addRow(key_label, value_label)
            self.labels[key] = value_label # Store reference to the value label

        self.layout.update()

    def _update_field_values(self, data: dict):
        for key, value_label in self.labels.items():
            if key in data:
                value_label.setText(str(data[key]))
            else:
                value_label.setText("N/A")

        self.layout.update()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
                item.layout().deleteLater()
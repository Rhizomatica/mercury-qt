from PySide6 import QtWidgets, QtCore, QtGui
from core.components.status_flag import StatusFlag

# Keys that should be rendered together on a single row.
# Each tuple is (key_left, key_right). The combined row label is defined in PAIRED_LABELS.
PAIRED_FIELDS = [
    ("user_callsign", "dest_callsign"),
]
PAIRED_LABELS = {
    ("user_callsign", "dest_callsign"): "Callsigns",
}

class JsonDetailView(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QFormLayout(self)
        self.setLayout(self.layout)
        self.labels = {} 

        self.setWindowTitle("JSON Details")

        self.title_label = QtWidgets.QLabel("<b>Latest Status Update</b>")
        self.title_label.setStyleSheet("color: rgb(255, 136, 0)")
        
        self.layout.addRow(self.title_label)
        self.layout.addRow(QtWidgets.QFrame())

    @QtCore.Slot(dict)
    def update_json_data(self, data: dict):
        current_label_keys = set(self.labels.keys())
        incoming_data_keys = set(data.keys())

        should_recreate = False
        if not current_label_keys:
            should_recreate = True
        elif current_label_keys != incoming_data_keys:
            should_recreate = True
        else:
            for key in incoming_data_keys:
                if key == "client_tcp_connected":
                    if not isinstance(self.labels.get(key), StatusFlag):
                        should_recreate = True
                        break
                elif not isinstance(self.labels.get(key), QtWidgets.QLabel):
                    should_recreate = True
                    break


        if should_recreate:
            self._create_fields(data)
        
        self._update_field_values(data)
        
    def _create_fields(self, data: dict):
        while self.layout.count() > 2: # Items after title and separator
            item = self.layout.takeAt(self.layout.count() - 1) # Take from end for safety
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
                item.layout().deleteLater()
        
        self.labels.clear()

        # Keys already rendered as part of a paired row — skip on individual pass
        paired_rendered: set = set()

        for key in data.keys():
            if key == "message" and "type" not in data:
                continue
            if key in paired_rendered:
                continue

            # If this key is the secondary (right) part of any complete pair, skip it —
            # it will be rendered when the primary (left) key is processed.
            if any(p[1] == key and p[0] in data for p in PAIRED_FIELDS):
                paired_rendered.add(key)
                continue

            # Check if this key starts a paired group
            pair_match = next((p for p in PAIRED_FIELDS if p[0] == key and p[1] in data), None)
            if pair_match:
                key_a, key_b = pair_match
                row_label_text = PAIRED_LABELS.get(pair_match, f"{key_a} / {key_b}")
                row_label_widget = QtWidgets.QLabel(f"<b>{row_label_text}</b>")

                container = QtWidgets.QWidget()
                container.setStyleSheet("background: transparent;")
                h_layout = QtWidgets.QHBoxLayout(container)
                h_layout.setContentsMargins(0, 0, 0, 0)
                h_layout.setSpacing(6)

                label_a = QtWidgets.QLabel(str(data.get(key_a)) if data.get(key_a) is not None else "N/A")
                sep = QtWidgets.QLabel("→")
                sep.setStyleSheet("color: rgb(255, 136, 0);")
                label_b = QtWidgets.QLabel(str(data.get(key_b)) if data.get(key_b) is not None else "N/A")

                h_layout.addWidget(label_a)
                h_layout.addWidget(sep)
                h_layout.addWidget(label_b)
                h_layout.addStretch()

                self.layout.addRow(row_label_widget, container)
                self.labels[key_a] = label_a
                self.labels[key_b] = label_b
                paired_rendered.add(key_a)
                paired_rendered.add(key_b)
                continue

            key_label_widget = QtWidgets.QLabel(f"<b>{key.upper() if key.lower() == 'snr' else key.replace('_', ' ').capitalize()}</b>")
            value_widget = self._render_component(key, data.get(key))
            self.layout.addRow(key_label_widget, value_widget)
            self.labels[key] = value_widget
        
        self.layout.update()

    def _update_field_values(self, data: dict):
        for key, value_widget in self.labels.items():
            if key in data:
                self._update_component_value(key, value_widget, data.get(key))
            else:
                self._update_component_value(key, value_widget, None)
        self.layout.update()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
                item.layout().deleteLater()

    def _render_component(self, key: str, initial_value: any = None) -> QtWidgets.QWidget:
        
        if key == "client_tcp_connected":
            client_tcp_connected_status_flag = StatusFlag()
            if initial_value is not None:
                is_connected = str(initial_value).lower() == "true"
                client_tcp_connected_status_flag.set_status(is_connected)
            return client_tcp_connected_status_flag
        elif key == "sync":
            sync_status_flag = StatusFlag()
            if initial_value is not None:
                is_connected = str(initial_value).lower() == "true"
                sync_status_flag.set_status(is_connected)
            return sync_status_flag        
        else:
            # Default to QLabel for all other fields
            label = QtWidgets.QLabel(str(initial_value) if initial_value is not None else "N/A")
            return label

    def _update_component_value(self, key: str, widget: QtWidgets.QWidget, value: any):
        if key == "client_tcp_connected":
            if isinstance(widget, StatusFlag):
                is_connected = None
                if value is not None:
                    is_connected = str(value).lower() == "true"
                widget.set_status(is_connected)
           
        elif key == "sync":
            if isinstance(widget, StatusFlag):
                is_connected = None
                if value is not None:
                    is_connected = str(value).lower() == "true"
                widget.set_status(is_connected)
                
        else:
            if isinstance(widget, QtWidgets.QLabel):
                widget.setText(str(value) if value is not None else "N/A")
            else:
                print(f"Warning: Cannot update unknown widget type {type(widget)} for key '{key}'")
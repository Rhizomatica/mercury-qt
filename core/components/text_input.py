from PySide6 import QtWidgets, QtCore


class TextInput(QtWidgets.QWidget):
    """A line-edit with an Apply button that emits a command dict on Enter or click."""

    # Signal that emits the formatted command dictionary
    command_to_send = QtCore.Signal(dict)

    def __init__(self, key: str, max_length: int = 255, placeholder: str = "", parent=None):
        super().__init__(parent)

        self.key = key

        self.line_edit = QtWidgets.QLineEdit()
        self.line_edit.setMaxLength(max_length)
        if placeholder:
            self.line_edit.setPlaceholderText(placeholder)

        self.apply_button = QtWidgets.QPushButton("Apply")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.line_edit, stretch=1)
        layout.addWidget(self.apply_button)
        self.setLayout(layout)

        # Emit on Enter key or Apply button click
        self.line_edit.returnPressed.connect(self._emit_command)
        self.apply_button.clicked.connect(self._emit_command)

    def _emit_command(self):
        value = self.line_edit.text().strip()
        command = {
            "command": f"set_{self.key}",
            "value": value
        }
        self.command_to_send.emit(command)

    def set_text(self, text: str):
        """Set the line edit text without emitting a signal."""
        self.line_edit.blockSignals(True)
        self.line_edit.setText(text)
        self.line_edit.blockSignals(False)

    def text(self) -> str:
        return self.line_edit.text()

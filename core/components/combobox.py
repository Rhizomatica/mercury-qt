from PySide6 import QtWidgets, QtCore

class ComboBox(QtWidgets.QWidget):
    # Signal that emits the formatted command dictionary
    command_to_send = QtCore.Signal(dict) 

    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        
        # Key used to format the command (e.g. "capture_dev" or "radio")
        self.key = key 
        
        self.combo_box = QtWidgets.QComboBox()
        
        # Connect the native QComboBox signal to the internal slot
        self.combo_box.currentIndexChanged.connect(self._on_index_changed)
        
        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.combo_box)
        self.setLayout(layout)

    @QtCore.Slot(list)
    def set_options(self, options: list):
        """Populate the ComboBox with options.
        
        Each option can be either:
          - a dict with 'name' and 'id' keys  →  displayed as "name (id)"
          - a plain string                     →  displayed and used as-is
        """
        self.combo_box.blockSignals(True)
        self.combo_box.clear()
        for opt in options:
            if isinstance(opt, dict):
                name = opt.get("name", "")
                dev_id = opt.get("id", "")
                display_text = f"{name} ({dev_id})" if name else dev_id
                self.combo_box.addItem(display_text, userData=dev_id)
            else:
                self.combo_box.addItem(str(opt), userData=str(opt))
        self.combo_box.blockSignals(False)

    @QtCore.Slot(str)
    def set_selected(self, value: str):
        """Set the currently selected item by its id/value without emitting a command."""
        for i in range(self.combo_box.count()):
            if self.combo_box.itemData(i) == value:
                self.combo_box.blockSignals(True)
                self.combo_box.setCurrentIndex(i)
                self.combo_box.blockSignals(False)
                return
        
    @QtCore.Slot(int)
    def _on_index_changed(self, index: int):
        """Called when the selected index changes.
        Emits the command with the device id (not the display text).
        """
        if index < 0:
            return

        # Use the stored userData (the id) for the command value
        value = self.combo_box.itemData(index)
        if value is None:
            value = self.combo_box.currentText()
        
        if not value:
            return

        command = {
            "command": f"set_{self.key}",
            "value": value
        }
        
        self.command_to_send.emit(command) 

        
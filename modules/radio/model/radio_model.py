# modules/radio/model/radio_model.py
from PySide6 import QtCore, QtGui

class JsonListModel(QtCore.QAbstractListModel):
    def __init__(self, initial_data=None, parent=None):
        super().__init__(parent)
        self._data = initial_data if initial_data is not None else []

    def data(self, index, role):
        if not index.isValid():
            return None

        item = self._data[index.row()]

        if role == QtCore.Qt.DisplayRole:
            if "type" in item and item["type"] == "status":
                return item
            return str(item)

        elif role == QtCore.Qt.UserRole:
            return item
            
        elif role == QtCore.Qt.ToolTipRole:
            return str(item)

        return None

    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._data)

    def add_item(self, json_object: dict):
        # Insert a new row at the end
        self.beginInsertRows(QtCore.QModelIndex(), self.rowCount(), self.rowCount())
        self._data.append(json_object)
        self.endInsertRows()
        print(f"Model updated with new JSON: {json_object}")

    def clear_items(self):
        self.beginRemoveRows(QtCore.QModelIndex(), 0, self.rowCount() - 1)
        self._data = []
        self.endRemoveRows()
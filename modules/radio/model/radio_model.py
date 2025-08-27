from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt
import json

class JsonListModel(QAbstractListModel):
    def __init__(self, data_list=None, parent=None):
        super().__init__(parent)
        self._data = data_list if data_list is not None else []

    def rowCount(self, parent=QModelIndex()):
        # Returns the number of rows in the model.
        if parent.isValid():
            return 0 # For a simple list, there are no children for items
        return len(self._data)

    def data(self, index, role=Qt.DisplayRole):
        # Returns the data for a given index and role.
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        item = self._data[index.row()]

        if role == Qt.DisplayRole:
            # This is the primary text displayed in the view.
            return f"{item.get('name', 'N/A')} ({item.get('color', 'unknown')})"
        elif role == Qt.UserRole:
            # Qt.UserRole can be used to return the raw object
            return item
        elif role == Qt.ToolTipRole:
            # Display a tooltip with more details, maybe JSON string
            return json.dumps(item, indent=2)
        # Add other roles as needed, e.g., Qt.DecorationRole for icons, Qt.TextAlignmentRole, etc.

        return None

    def setData(self, index, value, role=Qt.EditRole):
        # Allows editing of data in the model (optional, but good for completeness).
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return False

        if role == Qt.EditRole:
            # Assuming 'value' is a dictionary for direct update or a string to update 'name'
            if isinstance(value, dict):
                self._data[index.row()] = value
            elif isinstance(value, str):
                # If editing as a string, update the 'name' field
                self._data[index.row()]['name'] = value
            else:
                return False # Cannot handle other types directly for edit
            self.dataChanged.emit(index, index, [role]) # Notify views of change
            return True
        return False

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        # Defines headers for tables or lists (less common for simple lists)
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return f"Column {section}" # For table view
        return None

    def flags(self, index):
        # Defines how items can be interacted with (e.g., selectable, editable).
        if not index.isValid():
            return Qt.NoItemFlags
        # Items are selectable and editable
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def add_item(self, item_dict):
        # Adds a new dictionary item to the model.
        row = len(self._data)
        self.beginInsertRows(QModelIndex(), row, row)
        self._data.append(item_dict)
        self.endInsertRows()

    def get_raw_data(self):
        # Returns the underlying list of dictionaries.
        return self._data
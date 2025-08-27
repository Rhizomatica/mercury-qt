from PySide6.QtCore import QStringListModel, QModelIndex, Qt

class FruitModel(QStringListModel):
    def __init__(self, fruits=None, parent=None):
        super().__init__(fruits, parent)
        if fruits is None:
            self.setStringList([])

    def add_fruit(self, fruit_name):
        row = self.rowCount()
        # For PySide6, we use QModelIndex() for the parent argument when it's a top-level item
        self.beginInsertRows(QModelIndex(), row, row)
        current_list = self.stringList()
        current_list.append(fruit_name)
        self.setStringList(current_list)
        self.endInsertRows()

    def get_fruits(self):
        return self.stringList()
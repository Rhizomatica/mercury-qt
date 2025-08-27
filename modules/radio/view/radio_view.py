import json
from PySide6.QtWidgets import QListView, QApplication, QVBoxLayout, QWidget, QLineEdit, QPushButton, QHBoxLayout, QLabel

class JsonItemView(QWidget):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("JSON Object List (PySide6)")
        self.layout = QVBoxLayout()

        self.list_view = QListView()
        self.list_view.setModel(self.model)

        # Inputs for name and color
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter item name")

        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText("Enter item color")

        # Layout for inputs and button
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Name:"))
        input_layout.addWidget(self.name_input)
        input_layout.addWidget(QLabel("Color:"))
        input_layout.addWidget(self.color_input)

        self.add_button = QPushButton("Add Item")
        self.add_button.clicked.connect(self.add_item_to_model)

        self.layout.addWidget(self.list_view)
        self.layout.addLayout(input_layout) # Add the input layout
        self.layout.addWidget(self.add_button)

        self.setLayout(self.layout)

    def add_item_to_model(self):
        name = self.name_input.text().strip()
        color = self.color_input.text().strip()

        if name:
            new_item = {"name": name, "color": color if color else "default"}
            self.model.add_item(new_item)
            self.name_input.clear()
            self.color_input.clear()

        # Demonstrate accessing raw data (e.g., for serialization)
        print("Current raw data (JSON form):", json.dumps(self.model.get_raw_data(), indent=2))
from PySide6.QtWidgets import QListView, QVBoxLayout, QWidget, QLineEdit, QPushButton

class FruitView(QWidget):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Fruit List (PySide6)")
        self.layout = QVBoxLayout()

        self.list_view = QListView()
        self.list_view.setModel(self.model)

        self.fruit_input = QLineEdit()
        self.fruit_input.setPlaceholderText("Enter new fruit")

        self.add_button = QPushButton("Add Fruit")
        self.add_button.clicked.connect(self.add_fruit_to_model)

        self.layout.addWidget(self.list_view)
        self.layout.addWidget(self.fruit_input)
        self.layout.addWidget(self.add_button)

        self.setLayout(self.layout)

    def add_fruit_to_model(self):
        fruit_name = self.fruit_input.text().strip()
        if fruit_name:
            self.model.add_fruit(fruit_name)
            self.fruit_input.clear()
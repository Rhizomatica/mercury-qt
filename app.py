import sys
from PySide6 import QtWidgets
import modules.main_widget as main_widget
import modules.test_class as test_class

def import_styles():
    try:
        with open("assets/styles/app.qss", "r") as f:
            return f.read()
    except FileNotFoundError:
        print("Error: app.qss not found. Styles will not be applied.")
        return ""

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    
    styles = import_styles()
    app.setStyleSheet(styles)

    widget = main_widget.MainWidget()
    widget.setWindowTitle("Mercury Qt - Interface")
    widget.resize(800, 600)
    widget.show()
    
    # Iniciar testes se necessário
    tests = test_class.TestClass("HERMES")
    tests.start_mercury_qt_app()

    sys.exit(app.exec())
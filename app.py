import sys
from PySide6 import QtWidgets
import modules.main_widget as main_widget
import modules.test_class as test_class
import modules.udp.client as client


def import_styles():
    # Load the stylesheet from an external file
    try:
        with open("styles/app.qss", "r") as f:
            return f.read()
    except FileNotFoundError:
        print("Error: app.qss not found. Styles will not be applied.")
        
        
if __name__ == "__main__":

    #start UDP listener
    client = client.ClientUDP()
    client.start_udp_client()
    
    #start mercury qt app
    app = QtWidgets.QApplication([])
    
    styles = import_styles()
    app.setStyleSheet(styles)

    widget = main_widget.MainWidget()
    
    widget.setWindowTitle("Mercury Qt by Rhizomatica Communications") # Set window title
    widget.resize(800, 480)
    widget.show()
    
    tests = test_class.TestClass("HERMES")
    tests.start_mercury_qt_app()

    sys.exit(app.exec())



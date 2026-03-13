import sys
import os
from PySide6 import QtWidgets
from .modules.main import Main

class MercuryQT():

    def __init__(self, base_port=10000):
        super().__init__()

        receive_port  = base_port
        send_port     = base_port + 1
        spectrum_port = base_port + 2
        ws_port       = base_port - 1     # WebSocket port (matches C backend)

        print(f"🚀👾 Starting Mercury Qt App (BASE: {base_port}, RX: {receive_port}, TX: {send_port}, SPECTRUM: {spectrum_port}, WS: {ws_port})...")

        mercury_app = QtWidgets.QApplication([])
        styles = import_styles()
        mercury_app.setStyleSheet(styles)

        widget = Main(base_port=base_port, ws_port=ws_port)
        widget.setWindowTitle("Mercury Qt - Interface")
        widget.resize(960, 640)
        widget.show()

        sys.exit(mercury_app.exec())

def import_styles():
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))  # pasta atual do script
        style_path = os.path.join(base_path, "assets", "styles", "app.qss")

        with open(style_path, "r") as f:
            return f.read()

    except FileNotFoundError:
        print(f"Error: {style_path} not found. Styles will not be applied.")
        return ""   
    

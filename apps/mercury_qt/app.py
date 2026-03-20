import sys
import os
from PySide6 import QtWidgets
from .modules.main import Main

# Default WebSocket port — matches C backend UI_DEFAULT_PORT
UI_DEFAULT_PORT = 10000


class MercuryQT():

    def __init__(self, ws_host="127.0.0.1", ws_port=UI_DEFAULT_PORT):
        super().__init__()

        print(f"=== Starting Mercury Qt App (WS host: {ws_host}  port: {ws_port}) ===")

        mercury_app = QtWidgets.QApplication([])
        styles = import_styles()
        mercury_app.setStyleSheet(styles)

        widget = Main(ws_host=ws_host, ws_port=ws_port)
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
    

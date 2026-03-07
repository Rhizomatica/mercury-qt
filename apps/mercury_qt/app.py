import sys
import os
from PySide6 import QtWidgets
from .modules.main import Main

class MercuryQT():
    
    def __init__(self):
        super().__init__()
        
        print("🚀👾 Starting Mercury Qt App...")
        
        mercury_app = QtWidgets.QApplication([])
        styles = import_styles()
        mercury_app.setStyleSheet(styles)

        widget = Main()
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
    

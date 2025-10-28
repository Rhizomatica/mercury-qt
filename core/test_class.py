import sys
import PySide6.QtCore
class TestClass:        
        def __init__(self, name: str):
            self.helloMessage = "Hello "
            self.name = name
        
        def start_mercury_qt_app(self):
            print(self.helloMessage + self.name)
            print("We are now starting the mercury-qt app ...")
            print("Python version: " + sys.version)

            # Prints PySide6 version
            print("PySide6 version: " + PySide6.__version__)
            # Prints the Qt version used to compile PySide6
            print("Qt version: " + PySide6.QtCore.__version__)


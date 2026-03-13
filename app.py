import sys
import apps.mercury_qt.app as mercury_qt
import core.test_class as test_class


if __name__ == "__main__":
    
    if len(sys.argv) > 1:
        app = sys.argv[1]
    else:
        print('Missing param app')
        sys.exit(1)

    if app == "mercury":
        UI_DEFAULT_PORT = 10000

        if len(sys.argv) > 2:
            try:
                UI_DEFAULT_PORT = int(sys.argv[2])
            except ValueError:
                print(f"Invalid port: {sys.argv[2]}. Using default {UI_DEFAULT_PORT}.")

        print(f"WebSocket port: {UI_DEFAULT_PORT}")
        mercury_qt.MercuryQT(ws_port=UI_DEFAULT_PORT)
    else:
        tests = test_class.TestClass("HERMES")
        tests.start_mercury_qt_app()

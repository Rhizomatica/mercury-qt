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
        BASE_PORT = 10000

        if len(sys.argv) > 2:
            try:
                BASE_PORT = int(sys.argv[2])
            except ValueError:
                print(f"Invalid base port: {sys.argv[2]}. Using default {BASE_PORT}.")

        RECEIVE_PORT   = BASE_PORT
        SEND_PORT      = BASE_PORT + 1
        SPECTRUM_PORT  = BASE_PORT + 2
        WS_PORT        = BASE_PORT - 1    # WebSocket port (matches C backend)

        print(f"Ports — RECEIVE: {RECEIVE_PORT}, SEND: {SEND_PORT}, SPECTRUM: {SPECTRUM_PORT}, WS: {WS_PORT}")
        mercury_qt.MercuryQT(base_port=BASE_PORT)
    else:
        tests = test_class.TestClass("HERMES")
        tests.start_mercury_qt_app()

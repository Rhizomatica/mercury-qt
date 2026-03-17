import sys
import argparse
import apps.mercury_qt.app as mercury_qt
import core.test_class as test_class


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print('Missing param app')
        sys.exit(1)

    app = sys.argv[1]

    if app == "mercury":
        parser = argparse.ArgumentParser(prog="app.py mercury")
        parser.add_argument("--host", default="127.0.0.1", help="WebSocket host (default: 127.0.0.1)")
        parser.add_argument("--port", type=int, default=10000, help="WebSocket port (default: 10000)")
        args = parser.parse_args(sys.argv[2:])

        print(f"WebSocket host: {args.host}  port: {args.port}")
        mercury_qt.MercuryQT(ws_host=args.host, ws_port=args.port)
    else:
        tests = test_class.TestClass("HERMES")
        tests.start_mercury_qt_app()

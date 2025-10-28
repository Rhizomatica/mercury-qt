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
        mercury_qt.MercuryQT()
    
    tests = test_class.TestClass("HERMES")
    tests.start_mercury_qt_app()
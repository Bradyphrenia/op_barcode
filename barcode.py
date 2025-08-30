import sys
import logging
from PyQt5 import QtWidgets as qtw

# Import MainWindow from the package to ensure reliable relative import
from mainwindow import MainWindow


def _install_global_exception_hook():
    """Ensure uncaught exceptions are logged before the app exits."""
    def _excepthook(exc_type, exc_value, exc_traceback):
        logger = logging.getLogger("uncaught")
        # Log the full stack trace
        logger.exception("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    sys.excepthook = _excepthook


def main() -> int:
    _install_global_exception_hook()

    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()

    # Support both exec() and exec_() for broader Qt compatibility
    exec_fn = getattr(app, "exec", None) or getattr(app, "exec_", None)
    return exec_fn()


if __name__ == '__main__':
    sys.exit(main())

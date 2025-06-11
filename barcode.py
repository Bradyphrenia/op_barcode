import sys
from PyQt5 import QtWidgets as qtw
from mainwindow import MainWindow

if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())

import sys
from PyQt5 import QtWidgets as qtw
from PyQt5.QtWidgets import QMainWindow
from mainwindow import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.pushButton_ok.clicked.connect(self.close)
        self.ui.pushButton_decode.clicked.connect(self.barcode_decode)

    def barcode_read(self):
        barcode = self.ui.lineEdit_barcode.text()
        return barcode

    def barcode_decode(self, barcode):
        # barcode = '01042801021324431727113010Y018'
        # barcode = barcode.decode('utf-8')

        gtin = barcode[2:16]
        expires = barcode[18:24]
        serial = barcode[26:32]
        print(gtin, expires, serial)
        return gtin, expires, serial


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())

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

    def barcode_decode(self):
        barcode = self.ui.lineEdit_barcode.text()
        gtin = barcode[2:16]
        expires = barcode[18:24]
        serial = barcode[26:32]
        expires = self.convert_date(expires)
        self.ui.lineEdit_gtin.setText(gtin)
        self.ui.lineEdit_expire.setText(expires)
        self.ui.lineEdit_serial.setText(serial)
        self.ui.lineEdit_barcode.setText('')
        return None

    def convert_date(self, date):
        yy = date[0:2]
        mm = date[2:4]
        dd = date[4:6]
        date = f'20{yy}-{mm}-{dd}'
        return date


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())

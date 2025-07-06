import sys
from PyQt5 import QtWidgets as qtw
from PyQt5.QtWidgets import QMainWindow
from mainwindow import Ui_MainWindow
import data


class BarcodeProcessor:
    @staticmethod
    def process_barcode(barcode):
        if not barcode:
            return None, None, None
        gtin = barcode[2:16] if len(barcode) > 16 else ""
        djo = barcode[4:7] == "888"  # DJO-GTIN-CODE
        print (barcode[4:7])
        if djo == False:
            expires = barcode[18:24] if len(barcode) > 24 else ""
            serial = barcode[26:] if len(barcode) > 26 else ""
        else:
            print (len(barcode))
            expires = barcode[29:35] if len(barcode) > 34 else barcode[28:34]
            print (expires)
            serial = barcode[18:27] if len(barcode) > 34 else barcode[18:26]
        expires = BarcodeProcessor.convert_date(expires) if expires else ""
        return gtin, expires, serial

    @staticmethod
    def convert_date(date):
        if len(date) != 6:
            return ""
        yy = date[0:2]
        mm = date[2:4]
        dd = date[4:6]
        return f'20{yy}-{mm}-{dd}'


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # Verbindungen einrichten
        self._setup_connections()
        # Barcode-Prozessor initialisieren
        self.barcode_processor = BarcodeProcessor()
        self.data = data.init_search('table-EP_ARTIKEL2.json')

    def _setup_connections(self):
        """Stellt alle Signal-Slot-Verbindungen her"""
        self.ui.pushButton_ok.clicked.connect(self.close)
        self.ui.pushButton_decode.clicked.connect(self.barcode_decode)
        self.ui.actionBeenden.triggered.connect(self.close)

    def barcode_decode(self):
        barcode = self.ui.lineEdit_barcode.text()
        self.ui.plainTextEdit_output.clear()
        if not barcode:
            # Zeigen Sie eine Fehlermeldung an oder geben Sie eine Warnung aus
            self.ui.plainTextEdit_output.appendPlainText(f"Kein Barcode eingegeben")
            return
        try:
            gtin, expires, serial = self.barcode_processor.process_barcode(barcode)
            # UI aktualisieren
            self.ui.lineEdit_gtin.setText(gtin)
            self.ui.lineEdit_expire.setText(expires)
            self.ui.lineEdit_serial.setText(serial)
            self.ui.lineEdit_barcode.setText('')
            self.ui.lineEdit_ref.setText(data.search_refnumber(gtin, self.data))

        except Exception as e:
            # Behandeln Sie den Fehler ordnungsgemäß
            self.ui.plainTextEdit_output.appendPlainText(f"Fehler bei der Barcode-Verarbeitung: {e}")


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())

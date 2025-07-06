import sys
import logging
from PyQt5 import QtWidgets as qtw
from PyQt5.QtWidgets import QMainWindow
from mainwindow import Ui_MainWindow
import data

# Logging-Konfiguration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('barcode_processor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class BarcodeProcessor:
    @staticmethod
    def process_barcode(barcode):
        if not barcode:
            return None, None, None
        gtin = barcode[2:16] if len(barcode) > 16 else ""
        djo = barcode[4:7] == "888"  # DJO-GTIN-CODE
        logger.debug(f"DJO-Code erkannt: {barcode[4:7]}")
        if djo == False:
            expires = barcode[18:24] if len(barcode) > 24 else ""
            serial = barcode[26:] if len(barcode) > 26 else ""
        else:
            logger.debug(f"Barcode-Länge: {len(barcode)}")
            expires = barcode[29:35] if len(barcode) > 34 else barcode[28:34]
            logger.debug(f"Ablaufdatum: {expires}")
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
        if not barcode:
            # Logging statt plainTextEdit_output
            logger.warning("Kein Barcode eingegeben")
            return
        try:
            logger.info(f"Verarbeite Barcode: {barcode}")
            gtin, expires, serial = self.barcode_processor.process_barcode(barcode)
            # UI aktualisieren
            self.ui.lineEdit_gtin.setText(gtin)
            self.ui.lineEdit_expire.setText(expires)
            self.ui.lineEdit_serial.setText(serial)
            self.ui.lineEdit_barcode.setText('')
            self.ui.lineEdit_ref.setText(data.search_refnumber(gtin, self.data))
            logger.info(f"Barcode erfolgreich verarbeitet - GTIN: {gtin}, Ablauf: {expires}, Serial: {serial}")

        except Exception as e:
            # Logging statt plainTextEdit_output
            logger.error(f"Fehler bei der Barcode-Verarbeitung: {e}", exc_info=True)


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())
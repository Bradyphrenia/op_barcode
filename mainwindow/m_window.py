import logging
import sys

from PyQt5 import QtWidgets as qtw
from PyQt5.QtWidgets import QMainWindow

import data
from mainwindow import Ui_MainWindow

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
        try:
            logger.info(f"Starte Barcode-Verarbeitung für: {barcode}")

            if not barcode:
                logger.warning("Leerer Barcode übergeben")
                return None, None, None

            if not isinstance(barcode, str):
                logger.error(f"Barcode muss ein String sein, erhalten: {type(barcode)}")
                raise TypeError(f"Barcode muss ein String sein, erhalten: {type(barcode)}")

            # Mindestlänge prüfen
            if len(barcode) < 16:
                logger.error(f"Barcode zu kurz (Länge: {len(barcode)}). Mindestlänge: 16 Zeichen")
                raise ValueError(f"Barcode zu kurz (Länge: {len(barcode)}). Mindestlänge: 16 Zeichen")

            # GTIN extrahieren
            try:
                gtin = barcode[2:16]
                logger.debug(f"GTIN extrahiert: {gtin}")
                chk = BarcodeProcessor.check_gtin(gtin)
                logger.info(f"GTIN valid: {chk}")
            except IndexError as e:
                logger.error(f"Fehler beim Extrahieren der GTIN: {e}")
                raise ValueError(f"Fehler beim Extrahieren der GTIN aus Barcode: {barcode}")

            # DJO-Code prüfen
            try:
                djo_code = barcode[4:7]
                djo = djo_code == "888"  # DJO-GTIN-CODE
                logger.debug(f"DJO-Code erkannt: {djo_code}, ist DJO: {djo}")
            except IndexError as e:
                logger.error(f"Fehler beim Prüfen des DJO-Codes: {e}")
                raise ValueError(f"Fehler beim Prüfen des DJO-Codes aus Barcode: {barcode}")

            # Ablaufdatum und Seriennummer extrahieren
            try:
                if not djo:
                    # Standard-Format
                    expires = barcode[18:24] if len(barcode) > 24 else ""
                    serial = barcode[26:] if len(barcode) > 26 else ""
                    logger.debug(f"Standard-Format: Ablauf={expires}, Serial={serial}")
                else:
                    # DJO-Format
                    logger.debug(f"DJO-Format erkannt, Barcode-Länge: {len(barcode)}")
                    expires = barcode[29:35] if len(barcode) > 34 else barcode[28:34]
                    serial = barcode[18:27] if len(barcode) > 34 else barcode[18:26]
                    logger.debug(f"DJO-Format: Ablauf={expires}, Serial={serial}")

            except IndexError as e:
                logger.error(f"Fehler beim Extrahieren von Ablaufdatum/Seriennummer: {e}")
                expires = ""
                serial = ""

            # Datum konvertieren
            try:
                expires = BarcodeProcessor.convert_date(expires) if expires else ""
                logger.debug(f"Konvertiertes Ablaufdatum: {expires}")
            except Exception as e:
                logger.error(f"Fehler bei der Datumskonvertierung: {e}")
                expires = ""

            logger.info(f"Barcode erfolgreich verarbeitet - GTIN: {gtin}, Ablauf: {expires}, Serial: {serial}")
            return gtin, expires, serial

        except (TypeError, ValueError) as e:
            logger.error(f"Validierungsfehler beim Verarbeiten des Barcodes '{barcode}': {e}")
            raise
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim Verarbeiten des Barcodes '{barcode}': {e}", exc_info=True)
            raise RuntimeError(f"Unerwarteter Fehler bei der Barcode-Verarbeitung: {e}")

    @staticmethod
    def check_gtin(gtin):
        checksum = lambda x: str(sum(int(ziffer) for ziffer in str(x)))
        number = gtin[0:13]
        check = gtin[13:14]
        logger.debug(f"GTIN: {number}, Check: {check}")
        while len(number) > 1:
            number = checksum(number)
        logger.info(f"Nummer: {number}, Prüfziffer: {check}")
        return number == check

    @staticmethod
    def convert_date(date):
        try:
            logger.debug(f"Starte Datumskonvertierung für: '{date}'")

            # Input-Validierung
            if not date:
                logger.warning("Leeres Datum übergeben")
                return ""

            if not isinstance(date, str):
                logger.error(f"Datum muss ein String sein, erhalten: {type(date)}")
                raise TypeError(f"Datum muss ein String sein, erhalten: {type(date)}")

            # Längenprüfung
            if len(date) != 6:
                logger.warning(f"Datum hat falsche Länge: {len(date)} (erwartet: 6)")
                return ""

            # Prüfung auf numerische Zeichen
            if not date.isdigit():
                logger.error(f"Datum enthält nicht-numerische Zeichen: '{date}'")
                raise ValueError(f"Datum muss nur Ziffern enthalten, erhalten: '{date}'")

            # Datum-Komponenten extrahieren
            try:
                yy = date[0:2]
                mm = date[2:4]
                dd = date[4:6]
                logger.debug(f"Extrahierte Komponenten - Jahr: {yy}, Monat: {mm}, Tag: {dd}")
            except IndexError as e:
                logger.error(f"Fehler beim Extrahieren der Datumskomponenten: {e}")
                raise ValueError(f"Fehler beim Extrahieren der Datumskomponenten aus: '{date}'")

            # Validierung der Datumskomponenten
            try:
                year_int = int(yy)
                month_int = int(mm)
                day_int = int(dd)

                # Monatsvalidierung
                if month_int < 1 or month_int > 12:
                    logger.error(f"Ungültiger Monat: {month_int}")
                    raise ValueError(f"Ungültiger Monat: {month_int} (muss zwischen 1 und 12 liegen)")

                # Tagesvalidierung (einfache Prüfung)
                if day_int < 1 or day_int > 31:
                    logger.error(f"Ungültiger Tag: {day_int}")
                    raise ValueError(f"Ungültiger Tag: {day_int} (muss zwischen 1 und 31 liegen)")

                # Erweiterte Tagesvalidierung für bestimmte Monate
                days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]  # Februar mit 29 für Schaltjahre
                if day_int > days_in_month[month_int - 1]:
                    logger.error(f"Tag {day_int} ist ungültig für Monat {month_int}")
                    raise ValueError(f"Tag {day_int} ist ungültig für Monat {month_int}")

            except ValueError as e:
                if "invalid literal" in str(e):
                    logger.error(f"Nicht-numerische Datumskomponenten: yy='{yy}', mm='{mm}', dd='{dd}'")
                    raise ValueError(f"Datumskomponenten müssen numerisch sein: '{date}'")
                else:
                    raise  # Re-raise andere ValueError

            # Formatiertes Datum erstellen
            try:
                formatted_date = f'20{yy}-{mm}-{dd}'
                logger.debug(f"Formatiertes Datum: {formatted_date}")

                # Zusätzliche Validierung mit datetime (optional)
                from datetime import datetime
                try:
                    datetime.strptime(formatted_date, '%Y-%m-%d')
                    logger.info(f"Datum erfolgreich konvertiert: '{date}' -> '{formatted_date}'")
                except ValueError as e:
                    logger.error(f"Ungültiges Datum nach Formatierung: {formatted_date}")
                    raise ValueError(f"Ungültiges Datum: {formatted_date}")

                return formatted_date

            except Exception as e:
                logger.error(f"Fehler bei der Datumsformatierung: {e}")
                raise RuntimeError(f"Fehler bei der Datumsformatierung: {e}")

        except TypeError as e:
            logger.error(f"Typfehler bei Datumskonvertierung: {e}")
            raise
        except ValueError as e:
            logger.error(f"Wertfehler bei Datumskonvertierung: {e}")
            raise
        except Exception as e:
            logger.error(f"Unerwarteter Fehler bei Datumskonvertierung für '{date}': {e}", exc_info=True)
            raise RuntimeError(f"Unerwarteter Fehler bei der Datumskonvertierung: {e}")


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # Verbindungen einrichten
        self._setup_connections()
        # Barcode-Prozessor initialisieren
        self.barcode_processor = BarcodeProcessor()
        self.data = data.init_search('table-EP_ARTIKEL2.json')

    def _setup_connections(self):
        """Stellt alle Signal-Slot-Verbindungen her"""
        self.pushButton_ok.clicked.connect(self.close)
        self.pushButton_decode.clicked.connect(self.barcode_decode)
        self.actionBeenden.triggered.connect(self.close)
        self.lineEdit_barcode.textChanged.connect(self.barcode_changed)

    def barcode_decode(self):
        self._clear_ui_fields()
        barcode = self.lineEdit_barcode.text()

        if not barcode:
            logger.warning("Kein Barcode eingegeben")
            return

        try:
            logger.info(f"Verarbeite Barcode: {barcode}")
            gtin, expires, serial = self.barcode_processor.process_barcode(barcode)
            self._update_ui_with_barcode_data(gtin, expires, serial)
            logger.info(f"Barcode erfolgreich verarbeitet - GTIN: {gtin}, Ablauf: {expires}, Serial: {serial}")
        except Exception as e:
            logger.error(f"Fehler bei der Barcode-Verarbeitung: {e}", exc_info=True)

    def _clear_ui_fields(self):
        """Löscht alle UI-Eingabefelder"""
        self.lineEdit_gtin.setText('')
        self.lineEdit_expire.setText('')
        self.lineEdit_serial.setText('')
        self.lineEdit_ref.setText('')

    def barcode_changed(self):
        if len(self.lineEdit_barcode.text()) > 0:
            self._clear_ui_fields()

    def _update_ui_with_barcode_data(self, gtin: str, expires: str, serial: str):
        """Aktualisiert die UI mit den verarbeiteten Barcode-Daten"""
        self.lineEdit_gtin.setText(gtin)
        self.lineEdit_expire.setText(expires)
        self.lineEdit_serial.setText(serial)
        self.lineEdit_barcode.setText('')
        self.lineEdit_ref.setText(data.search_refnumber(gtin, self.data))

        # Fokus auf lineEdit_barcode setzen und Cursor auf erste Position
        self.lineEdit_barcode.setFocus()
        self.lineEdit_barcode.setCursorPosition(0)


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())

import logging
import sys

import pyperclip
from PyQt5 import QtWidgets as qtw
from PyQt5.QtWidgets import QMainWindow

import data
from mainwindow import Ui_MainWindow

# Logging-Konfiguration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('barcode_processor.log'), logging.StreamHandler(sys.stdout)])


class LoggerService:
    """Zentrale Klasse für alle Logging-Funktionen"""

    def __init__(self, name):
        self.logger = logging.getLogger(name)

    def info(self, message):
        self.logger.info(message)

    def debug(self, message):
        self.logger.debug(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message, exc_info=False):
        self.logger.error(message, exc_info=exc_info)


class GtinValidator:
    """Klasse für die Validierung von GTIN-Codes"""

    def __init__(self):
        self.logger = LoggerService("GtinValidator")

    def _calculate_digit_sum(self, x):
        """Berechnet die Quersumme mit Caching für bessere Performance"""
        return str(sum(int(digit) for digit in str(x)))

    def check_gtin(self, gtin):
        number = gtin[0:13]
        check = gtin[13:14]
        self.logger.debug(f"GTIN: {number}, Check: {check}")

        while len(number) > 1:
            number = self._calculate_digit_sum(number)

        self.logger.info(f"Nummer: {number}, Prüfziffer: {check}")
        return number == check

    def validate_gtin13(self, gtin):
        """
        Validiert einen GTIN-13 Code durch Überprüfung der Prüfziffer.
        """
        # Entfernen von Leerzeichen und Bindestrichen
        gtin = gtin.replace(' ', '').replace('-', '')

        # Überprüfung der Länge
        if len(gtin) != 13:
            return False

        # Überprüfung, ob alle Zeichen Ziffern sind
        if not gtin.isdigit():
            return False

        # Berechnung der Prüfziffer
        check_digit = self.calculate_gtin13_check_digit(gtin[:12])

        # Vergleich mit der angegebenen Prüfziffer
        self.logger.info(f"Nummer: {check_digit}, Prüfziffer: {gtin[12]}")
        return int(gtin[12]) == check_digit

    def calculate_gtin13_check_digit(self, gtin_12):
        """
        Berechnet die Prüfziffer für die ersten 12 Stellen eines GTIN-13 Codes.
        """
        if len(gtin_12) != 12:
            raise ValueError("GTIN-12 muss genau 12 Stellen haben")

        # GTIN-13 Algorithmus: Abwechselnd mit 1 und 3 multiplizieren
        total = sum(int(digit) * (1 if i % 2 == 0 else 3) for i, digit in enumerate(gtin_12))

        # Prüfziffer = (10 - (Summe mod 10)) mod 10
        return (10 - (total % 10)) % 10


class DateConverter:
    """Klasse für die Konvertierung von Datumsformaten"""

    def __init__(self):
        self.logger = LoggerService("DateConverter")

    def convert_date(self, date):
        """Konvertiert ein Datum im Format YYMMDD zu YYYY-MM-DD"""
        try:
            self.logger.debug(f"Starte Datumskonvertierung für: '{date}'")

            # Input-Validierung
            if not date or not isinstance(date, str) or len(date) != 6 or not date.isdigit():
                self.logger.warning(f"Ungültiges Datumsformat: '{date}'")
                return ""

            # Datum-Komponenten extrahieren
            yy, mm, dd = date[0:2], date[2:4], date[4:6]
            self.logger.debug(f"Extrahierte Komponenten - Jahr: {yy}, Monat: {mm}, Tag: {dd}")

            # Validierung der Datumskomponenten
            month_int = int(mm)
            day_int = int(dd)

            if month_int < 1 or month_int > 12:
                self.logger.error(f"Ungültiger Monat: {month_int}")
                return ""

            # Tagesvalidierung
            days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]  # Februar mit 29 für Schaltjahre
            if day_int < 1 or day_int > days_in_month[month_int - 1]:
                self.logger.error(f"Tag {day_int} ist ungültig für Monat {month_int}")
                return ""

            # Formatiertes Datum erstellen
            formatted_date = f'20{yy}-{mm}-{dd}'

            # Zusätzliche Validierung mit datetime
            from datetime import datetime
            try:
                datetime.strptime(formatted_date, '%Y-%m-%d')
                self.logger.info(f"Datum erfolgreich konvertiert: '{date}' -> '{formatted_date}'")
                return formatted_date
            except ValueError:
                self.logger.error(f"Ungültiges Datum nach Formatierung: {formatted_date}")
                return ""

        except Exception as e:
            self.logger.error(f"Unerwarteter Fehler bei Datumskonvertierung für '{date}': {e}", exc_info=True)
            return ""


class BarcodeProcessor:
    """Hauptklasse für die Verarbeitung von Barcodes"""

    def __init__(self):
        self.logger = LoggerService("BarcodeProcessor")
        self.gtin_validator = GtinValidator()
        self.date_converter = DateConverter()

    def process_barcode(self, barcode):
        """Verarbeitet einen Barcode und extrahiert relevante Informationen"""
        try:
            self.logger.info(f"Starte Barcode-Verarbeitung für: {barcode}")

            # Grundlegende Validierung
            if not barcode:
                self.logger.warning("Leerer Barcode übergeben")
                return None, None, None, None

            if not isinstance(barcode, str):
                error_msg = f"Barcode muss ein String sein, erhalten: {type(barcode)}"
                self.logger.error(error_msg)
                raise TypeError(error_msg)

            if len(barcode) < 16:
                error_msg = f"Barcode zu kurz (Länge: {len(barcode)}). Mindestlänge: 16 Zeichen"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

            # GTIN extrahieren und validieren
            gtin, chk = self._extract_and_validate_gtin(barcode)
            if not chk:
                barcode = self._test_on_alternative_barcode(barcode)
                gtin, chk = self._extract_and_validate_gtin(barcode)

            # DJO-Code prüfen
            djo = self._check_djo_code(barcode)

            # Ablaufdatum und Seriennummer extrahieren
            expires, serial = self._extract_expiry_and_serial(barcode, djo)

            # Datum konvertieren
            expires = self.date_converter.convert_date(expires) if expires else ""

            self.logger.info(f"Barcode erfolgreich verarbeitet - GTIN: {gtin}, Ablauf: {expires}, Serial: {serial}")
            return gtin, expires, serial, chk

        except (TypeError, ValueError) as e:
            self.logger.error(f"Validierungsfehler beim Verarbeiten des Barcodes '{barcode}': {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unerwarteter Fehler beim Verarbeiten des Barcodes '{barcode}': {e}", exc_info=True)
            raise RuntimeError(f"Unerwarteter Fehler bei der Barcode-Verarbeitung: {e}")

    def _extract_and_validate_gtin(self, barcode) -> tuple[str, bool]:
        """Extrahiert und validiert die GTIN aus einem Barcode"""
        try:
            gtin = barcode[2:16]
            self.logger.debug(f"GTIN extrahiert: {gtin}")
            chk = self.gtin_validator.check_gtin(gtin)
            self.logger.info(f"GTIN valid: {chk}")
            if not chk:
                gtin_13 = barcode[3:16]
                self.logger.debug(f"GTIN-13 extrahiert: {gtin_13}")
                chk = self.gtin_validator.validate_gtin13(gtin_13)
                self.logger.info(f"GTIN-13 valid: {chk}")
            return gtin, chk
        except IndexError as e:
            self.logger.error(f"Fehler beim Extrahieren der GTIN: {e}")
            raise ValueError(f"Fehler beim Extrahieren der GTIN aus Barcode: {barcode}")

    def _test_on_alternative_barcode(self, barcode) -> str:
        self.logger.info(f"Teste auf Fehler in Barcode")
        older_barcode = barcode
        barcode = barcode[0:1] + barcode[2:]
        gtin, chk = self._extract_and_validate_gtin(barcode)
        if chk:
            self.logger.info(f"alternativer Barcode-Test erfolgreich - GTIN: {gtin}")
            return barcode
        else:
            return older_barcode

    def _check_djo_code(self, barcode):
        """Prüft, ob der Barcode ein DJO-Code ist"""
        try:
            djo_code = barcode[4:7]
            djo = djo_code == "888"  # DJO-GTIN-CODE
            self.logger.debug(f"DJO-Code erkannt: {djo_code}, ist DJO: {djo}")
            return djo
        except IndexError as e:
            self.logger.error(f"Fehler beim Prüfen des DJO-Codes: {e}")
            raise ValueError(f"Fehler beim Prüfen des DJO-Codes aus Barcode: {barcode}")

    def _extract_expiry_and_serial(self, barcode, djo):
        """Extrahiert Ablaufdatum und Seriennummer aus einem Barcode"""
        try:
            if not djo:
                # Standard-Format
                expires = barcode[18:24] if len(barcode) > 24 else ""
                serial = barcode[26:] if len(barcode) > 26 else ""
                self.logger.debug(f"Standard-Format: Ablauf={expires}, Serial={serial}")
            else:
                # DJO-Format
                self.logger.debug(f"DJO-Format erkannt, Barcode-Länge: {len(barcode)}")
                expires = barcode[29:35] if len(barcode) > 34 else barcode[28:34]
                serial = barcode[18:27] if len(barcode) > 34 else barcode[18:26]
                self.logger.debug(f"DJO-Format: Ablauf={expires}, Serial={serial}")
            return expires, serial
        except IndexError:
            self.logger.error("Fehler beim Extrahieren von Ablaufdatum/Seriennummer")
            return "", ""


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.logger = LoggerService("MainWindow")
        # Verbindungen einrichten
        self._setup_connections()
        # Barcode-Prozessor initialisieren
        self.barcode_processor = BarcodeProcessor()
        self.data = data.init_search('table-EP_ARTIKEL2.json')
        self.label_valid.setVisible(False)
        self.barcode = None
        self.radioButton_ref.setChecked(True)
        self.radioButton_gtin.setChecked(False)

    def _setup_connections(self):
        """Stellt alle Signal-Slot-Verbindungen her"""
        self.pushButton_ok.clicked.connect(self.close)
        self.pushButton_decode.clicked.connect(self.barcode_decode)
        self.actionBeenden.triggered.connect(self.close)
        self.lineEdit_barcode.textChanged.connect(self.barcode_changed)
        self.pushButton_reverse.clicked.connect(self.reverse_search)
        self.radioButton_ref.toggled.connect(self.radio_button_ref_changed)
        self.radioButton_gtin.toggled.connect(self.radio_button_gtin_changed)

    def radio_button_ref_changed(self):
        self.radioButton_gtin.setChecked(
            False) if self.radioButton_ref.isChecked() else self.radioButton_gtin.setChecked(True)

    def radio_button_gtin_changed(self):
        self.radioButton_ref.setChecked(
            False) if self.radioButton_gtin.isChecked() else self.radioButton_ref.setChecked(True)

    def reverse_search(self):
        ref = self.lineEdit_ref.text()
        if not ref:
            self.logger.warning("Keine Ref-Nr. eingegeben")
            return
        try:
            self.logger.info(f"Verarbeite Ref-Nr.: {ref}")
            gtin = data.search_gtin(ref, self.data)
            self.lineEdit_gtin.setText(gtin)
            self.logger.info(f"Ref-Nr. erfolgreich verarbeitet - Ref: {ref}")
            self._copy_to_clipboard()
            chk = self._validate_gtin_with_fallback(gtin)
            self.label_valid.setVisible(chk)
        except Exception as e:
            self.logger.error(f"Fehler bei der Ref-Nr-Verarbeitung: {e}", exc_info=True)

    def _validate_gtin_with_fallback(self, gtin: str) -> bool:
        """Validiert GTIN mit Fallback auf GTIN-13 falls notwendig"""
        chk = self.barcode_processor.gtin_validator.check_gtin(gtin)
        self.logger.info(f"GTIN valid: {chk}")

        if not chk:
            gtin_13 = gtin[1:]
            self.logger.debug(f"GTIN-13 extrahiert: {gtin_13}")
            chk = self.barcode_processor.gtin_validator.validate_gtin13(gtin_13)
            self.logger.info(f"GTIN-13 valid: {chk}")

        return chk

    def barcode_decode(self):
        self._clear_ui_fields()
        self.barcode = self.lineEdit_barcode.text()
        if not self.barcode:
            self.logger.warning("Kein Barcode eingegeben")
            return
        try:
            self.logger.info(f"Verarbeite Barcode: {self.barcode}")
            gtin, expires, serial, chk = self.barcode_processor.process_barcode(self.barcode)
            if not chk:
                self.barcode = self.barcode_processor._test_on_alternative_barcode(self.barcode)
                gtin, expires, serial, chk = self.barcode_processor.process_barcode(self.barcode)
            self._update_ui_with_barcode_data(gtin, expires, serial, chk)
            self.logger.info(f"Barcode erfolgreich verarbeitet - GTIN: {gtin}, Ablauf: {expires}, Serial: {serial}")
        except Exception as e:
            self.logger.error(f"Fehler bei der Barcode-Verarbeitung: {e}", exc_info=True)

    def _clear_ui_fields(self):
        """Löscht alle UI-Eingabefelder"""
        self.lineEdit_gtin.setText('')
        self.lineEdit_expire.setText('')
        self.lineEdit_serial.setText('')
        self.lineEdit_ref.setText('')
        self.label_valid.setVisible(False)

    def barcode_changed(self):
        if len(self.lineEdit_barcode.text()) > 0:
            self._clear_ui_fields()

    def _update_ui_with_barcode_data(self, gtin: str, expires: str, serial: str, chk: bool):
        """Aktualisiert die UI mit den verarbeiteten Barcode-Daten"""
        self.lineEdit_gtin.setText(gtin)
        self.lineEdit_expire.setText(expires)
        self.lineEdit_serial.setText(serial)
        self.lineEdit_barcode.setText('')
        self.lineEdit_ref.setText(data.search_refnumber(gtin, self.data))
        self.label_valid.setVisible(chk)
        self._copy_to_clipboard()
        # Fokus auf lineEdit_barcode setzen und Cursor auf erste Position
        self.lineEdit_barcode.setFocus()
        self.lineEdit_barcode.setCursorPosition(0)

    def _copy_to_clipboard(self):
        """Kopiert den entsprechenden Wert basierend auf dem ausgewählten Radio Button"""
        clipboard_mapping = {self.radioButton_ref: self.lineEdit_ref.text(),
                             self.radioButton_gtin: self.lineEdit_gtin.text()}
        selected_value = next((value for button, value in clipboard_mapping.items() if button.isChecked()), "")
        if selected_value:
            pyperclip.copy(selected_value)


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())

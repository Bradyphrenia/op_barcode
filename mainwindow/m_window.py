import logging
import sys
import pyperclip
from PyQt5 import QtWidgets as qtw
from PyQt5.QtWidgets import QMainWindow
import data
from find_json_file import FileOpenDialog
from info import InfoWindow
from mainwindow import Ui_MainWindow

# Konstanten
BARCODE_MIN_LENGTH = 16
GTIN_START_POS = 2
GTIN_END_POS = 16
GTIN_13_START_POS = 3
DJO_CODE_START = 4
DJO_CODE_END = 7
DJO_IDENTIFIER = "888"
STANDARD_EXPIRE_START = 18
STANDARD_EXPIRE_END = 24
STANDARD_SERIAL_START = 26
DJO_EXPIRE_START_LONG = 29
DJO_EXPIRE_END_LONG = 35
DJO_EXPIRE_START_SHORT = 28
DJO_EXPIRE_END_SHORT = 34
DJO_SERIAL_START_LONG = 18
DJO_SERIAL_END_LONG = 27
DJO_SERIAL_END_SHORT = 26
CONFIG_FILE = 'json_file.cfg'
LOG_FILE = 'barcode_processor.log'

# Logging-Konfiguration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)])

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

    def validate_gtin(self, gtin):
        """Einheitliche GTIN-Validierung mit Fallback auf GTIN-13"""
        # Zuerst standard GTIN-Validierung versuchen
        if self.check_gtin(gtin):
            return True

        # Falls fehlgeschlagen, GTIN-13 versuchen
        if len(gtin) >= 13:
            gtin_13 = gtin[1:] if len(gtin) == 14 else gtin[:13]
            return self.validate_gtin13(gtin_13)

        return False

    def check_gtin(self, gtin):
        number = gtin[0:13]
        check = gtin[13:14]
        self.logger.debug(f"GTIN: {number}, Check: {check}")
        while len(number) > 1:
            number = self._calculate_digit_sum(number)
        self.logger.info(f"Nummer: {number}, Prüfziffer: {check}")
        return number == check if number != '' else False

    def validate_gtin13(self, gtin):
        """Validiert einen GTIN-13 Code durch Überprüfung der Prüfziffer."""
        gtin = gtin.replace(' ', '').replace('-', '')
        if len(gtin) != 13 or not gtin.isdigit():
            return False
        check_digit = self.calculate_gtin13_check_digit(gtin[:12])
        self.logger.info(f"Nummer: {check_digit}, Prüfziffer: {gtin[12]}")
        return int(gtin[12]) == check_digit

    def calculate_gtin13_check_digit(self, gtin_12):
        """Berechnet die Prüfziffer für die ersten 12 Stellen eines GTIN-13 Codes."""
        if len(gtin_12) != 12:
            raise ValueError("GTIN-12 muss genau 12 Stellen haben")
        total = sum(int(digit) * (1 if i % 2 == 0 else 3) for i, digit in enumerate(gtin_12))
        return (10 - (total % 10)) % 10

class DateConverter:
    """Klasse für die Konvertierung von Datumsformaten"""
    def __init__(self):
        self.logger = LoggerService("DateConverter")

    def convert_date(self, date):
        """Konvertiert ein Datum im Format YYMMDD zu YYYY-MM-DD"""
        try:
            self.logger.debug(f"Starte Datumskonvertierung für: '{date}'")
            if not self._is_valid_date_input(date):
                return ""

            yy, mm, dd = date[0:2], date[2:4], date[4:6]
            self.logger.debug(f"Extrahierte Komponenten - Jahr: {yy}, Monat: {mm}, Tag: {dd}")

            if not self._are_valid_date_components(mm, dd):
                return ""

            formatted_date = f'20{yy}-{mm}-{dd}'
            return self._validate_formatted_date(formatted_date)

        except Exception as e:
            self.logger.error(f"Unerwarteter Fehler bei Datumskonvertierung für '{date}': {e}", exc_info=True)
            return ""

    def _is_valid_date_input(self, date):
        """Validiert die Eingabe für die Datumskonvertierung"""
        if not date or not isinstance(date, str) or len(date) != 6 or not date.isdigit():
            self.logger.warning(f"Ungültiges Datumsformat: '{date}'")
            return False
        return True

    def _are_valid_date_components(self, mm, dd):
        """Validiert Monat und Tag"""
        month_int, day_int = int(mm), int(dd)
        if month_int < 1 or month_int > 12:
            self.logger.error(f"Ungültiger Monat: {month_int}")
            return False

        days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if day_int < 1 or day_int > days_in_month[month_int - 1]:
            self.logger.error(f"Tag {day_int} ist ungültig für Monat {month_int}")
            return False
        return True

    def _validate_formatted_date(self, formatted_date):
        """Validiert das formatierte Datum"""
        from datetime import datetime
        try:
            datetime.strptime(formatted_date, '%Y-%m-%d')
            self.logger.info(f"Datum erfolgreich konvertiert: '{formatted_date}'")
            return formatted_date
        except ValueError:
            self.logger.error(f"Ungültiges Datum nach Formatierung: {formatted_date}")
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
            self._validate_barcode_input(barcode)

            gtin, chk = self._extract_and_validate_gtin(barcode)
            if not chk:
                barcode = self._test_on_alternative_barcode(barcode)
                gtin, chk = self._extract_and_validate_gtin(barcode)

            djo = self._check_djo_code(barcode)
            expires, serial = self._extract_expiry_and_serial(barcode, djo)
            expires = self.date_converter.convert_date(expires) if expires else ""

            self.logger.info(f"Barcode erfolgreich verarbeitet - GTIN: {gtin}, Ablauf: {expires}, Serial: {serial}")
            return gtin, expires, serial, chk

        except (TypeError, ValueError) as e:
            self.logger.error(f"Validierungsfehler beim Verarbeiten des Barcodes '{barcode}': {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unerwarteter Fehler beim Verarbeiten des Barcodes '{barcode}': {e}", exc_info=True)
            raise RuntimeError(f"Unerwarteter Fehler bei der Barcode-Verarbeitung: {e}")

    def _validate_barcode_input(self, barcode):
        """Validiert die Barcode-Eingabe"""
        if not barcode:
            self.logger.warning("Leerer Barcode übergeben")
            raise ValueError("Leerer Barcode")

        if not isinstance(barcode, str):
            error_msg = f"Barcode muss ein String sein, erhalten: {type(barcode)}"
            self.logger.error(error_msg)
            raise TypeError(error_msg)

        if len(barcode) < BARCODE_MIN_LENGTH:
            error_msg = f"Barcode zu kurz (Länge: {len(barcode)}). Mindestlänge: {BARCODE_MIN_LENGTH} Zeichen"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

    def _extract_and_validate_gtin(self, barcode) -> tuple[str, bool]:
        """Extrahiert und validiert die GTIN aus einem Barcode"""
        try:
            gtin = barcode[GTIN_START_POS:GTIN_END_POS]
            self.logger.debug(f"GTIN extrahiert: {gtin}")
            chk = self.gtin_validator.validate_gtin(gtin)
            self.logger.info(f"GTIN valid: {chk}")
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
            djo_code = barcode[DJO_CODE_START:DJO_CODE_END]
            djo = djo_code == DJO_IDENTIFIER
            self.logger.debug(f"DJO-Code erkannt: {djo_code}, ist DJO: {djo}")
            return djo
        except IndexError as e:
            self.logger.error(f"Fehler beim Prüfen des DJO-Codes: {e}")
            raise ValueError(f"Fehler beim Prüfen des DJO-Codes aus Barcode: {barcode}")

    def _extract_expiry_and_serial(self, barcode, djo):
        """Extrahiert Ablaufdatum und Seriennummer aus einem Barcode"""
        try:
            if not djo:
                return self._extract_standard_format_data(barcode)
            else:
                return self._extract_djo_format_data(barcode)
        except IndexError:
            self.logger.error("Fehler beim Extrahieren von Ablaufdatum/Seriennummer")
            return "", ""

    def _extract_standard_format_data(self, barcode):
        """Extrahiert Daten im Standard-Format"""
        expires = barcode[STANDARD_EXPIRE_START:STANDARD_EXPIRE_END] if len(barcode) > STANDARD_EXPIRE_END else ""
        serial = barcode[STANDARD_SERIAL_START:] if len(barcode) > STANDARD_SERIAL_START else ""
        self.logger.debug(f"Standard-Format: Ablauf={expires}, Serial={serial}")
        return expires, serial

    def _extract_djo_format_data(self, barcode):
        """Extrahiert Daten im DJO-Format"""
        self.logger.debug(f"DJO-Format erkannt, Barcode-Länge: {len(barcode)}")
        if len(barcode) > DJO_EXPIRE_END_SHORT:
            expires = barcode[DJO_EXPIRE_START_LONG:DJO_EXPIRE_END_LONG]
            serial = barcode[DJO_SERIAL_START_LONG:DJO_SERIAL_END_LONG]
        else:
            expires = barcode[DJO_EXPIRE_START_SHORT:DJO_EXPIRE_END_SHORT]
            serial = barcode[DJO_SERIAL_START_LONG:DJO_SERIAL_END_SHORT]

        self.logger.debug(f"DJO-Format: Ablauf={expires}, Serial={serial}")
        return expires, serial

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.logger = LoggerService("MainWindow")
        self._initialize_components()
        self._setup_ui_state()

    def _initialize_components(self):
        """Initialisiert alle Komponenten"""
        self._setup_connections()
        self.barcode_processor = BarcodeProcessor()
        self.data = self._init_data(self._file_path())
        self.json_search_file_dialog = FileOpenDialog()
        self.info_dialog = InfoWindow()
        self.json_search_file_dialog.file_opened.connect(self._handle_file_opened)

    def _setup_ui_state(self):
        """Setzt den initialen UI-Zustand"""
        self.label_valid.setVisible(False)
        self.barcode = None
        self.radioButton_ref.setChecked(True)
        self.radioButton_gtin.setChecked(False)

    def _init_data(self, data_file):
        return data.init_search(data_file)

    def _file_path(self):
        with open(CONFIG_FILE, 'r') as f:
            return f.read()

    def _setup_connections(self):
        """Stellt alle Signal-Slot-Verbindungen her"""
        self.pushButton_ok.clicked.connect(self.close)
        self.pushButton_decode.clicked.connect(self.barcode_decode)
        self.actionBeenden.triggered.connect(self.close)
        self.action_ber_Barcode_Leser.triggered.connect(self._handle_info_window)
        self.actionjson_Datei_ausw_hlen.triggered.connect(self.select_json_file)
        self.lineEdit_barcode.textChanged.connect(self.barcode_changed)
        self.pushButton_reverse.clicked.connect(self.reverse_search)
        self.radioButton_ref.toggled.connect(self.radio_button_ref_changed)
        self.radioButton_gtin.toggled.connect(self.radio_button_gtin_changed)

    def radio_button_ref_changed(self):
        self.radioButton_gtin.setChecked(False if self.radioButton_ref.isChecked() else True)

    def radio_button_gtin_changed(self):
        self.radioButton_ref.setChecked(False if self.radioButton_gtin.isChecked() else True)

    def reverse_search(self):
        ref = self.lineEdit_ref.text()
        self._clear_ui_fields()
        if not ref:
            self.logger.warning("Keine Ref-Nr. eingegeben")
            return

        try:
            self.logger.info(f"Verarbeite Ref-Nr.: {ref}")
            gtin = data.search_gtin(ref, self.data)
            chk = self.barcode_processor.gtin_validator.validate_gtin(gtin)

            if chk:
                self._handle_successful_reverse_search(gtin, ref)
            else:
                self._handle_failed_reverse_search(ref)

        except Exception as e:
            self.logger.error(f"Fehler bei der Ref-Nr-Verarbeitung: {e}", exc_info=True)

    def _handle_successful_reverse_search(self, gtin, ref):
        """Behandelt erfolgreiches Reverse-Search-Ergebnis"""
        self.lineEdit_gtin.setText(gtin)
        self.label_valid.setVisible(True)
        self.logger.info(f"Ref-Nr. erfolgreich verarbeitet - Ref: {ref}")
        self._copy_to_clipboard()

    def _handle_failed_reverse_search(self, ref):
        """Behandelt fehlgeschlagenes Reverse-Search-Ergebnis"""
        self.logger.info(f"Ref-Nr. nicht gefunden - Ref: {ref}")
        self.label_valid.setVisible(False)

    def barcode_decode(self):
        self._clear_ui_fields()
        self.barcode = self.lineEdit_barcode.text()
        if not self.barcode:
            self.logger.warning("Kein Barcode eingegeben")
            return

        try:
            self.logger.info(f"Verarbeite Barcode: {self.barcode}")
            gtin, expires, serial, chk = self.barcode_processor.process_barcode(self.barcode)
            self._update_ui_with_barcode_data(gtin, expires, serial, chk)
            self.logger.info(f"Barcode erfolgreich verarbeitet - GTIN: {gtin}, Ablauf: {expires}, Serial: {serial}")
        except Exception as e:
            self.logger.error(f"Fehler bei der Barcode-Verarbeitung: {e}", exc_info=True)

    def _clear_ui_fields(self):
        """Löscht alle UI-Eingabefelder"""
        fields = [self.lineEdit_gtin, self.lineEdit_expire, self.lineEdit_serial, self.lineEdit_ref]
        for field in fields:
            field.setText('')
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
        self._set_focus_to_barcode_input()

    def _set_focus_to_barcode_input(self):
        """Setzt den Fokus auf das Barcode-Eingabefeld"""
        self.lineEdit_barcode.setFocus()
        self.lineEdit_barcode.setCursorPosition(0)

    def _copy_to_clipboard(self):
        """Kopiert den entsprechenden Wert basierend auf dem ausgewählten Radio Button"""
        clipboard_mapping = {
            self.radioButton_ref: self.lineEdit_ref.text(),
            self.radioButton_gtin: self.lineEdit_gtin.text()
        }
        selected_value = next((value for button, value in clipboard_mapping.items() if button.isChecked()), "")
        if selected_value:
            pyperclip.copy(selected_value)

    def select_json_file(self):
        self.json_search_file_dialog.show()

    def _handle_file_opened(self, file_path: str) -> None:
        """Behandelt das file_opened Signal und initialisiert die Daten neu."""
        try:
            self.data = self._init_data(file_path)
            if self.data is not None:
                self.logger.info(f"Daten erfolgreich aus Datei geladen: {file_path}")
            else:
                self.logger.error(f"Fehler beim Laden der Datei {file_path}")
        except Exception as e:
            self.logger.error(f"Fehler beim Laden der Datei {file_path}: {str(e)}")
            self.logger.warning(self, "Fehler", f"Datei konnte nicht geladen werden: {str(e)}")

    def _handle_info_window(self):
        self.info_dialog.show()

if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())
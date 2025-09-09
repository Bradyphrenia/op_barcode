import logging
import sys
import pyperclip




from datetime import datetime
import psycopg2
# from datalog import datalog
import codecs







import json
import logging
import os
from collections import defaultdict
from typing import Dict, List, Any, Tuple, Union, Set

# Logging-Konfiguration hinzufügen
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(),  # Ausgabe auf der Konsole
                              logging.FileHandler('import_ep.log')  # Speichern in einer Logdatei
                              ])
logger = logging.getLogger(__name__)


def import_json_file(file_path: str) -> Dict[str, Any]:
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        logger.info(f"Reading JSON file: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            logger.debug(f"Successfully loaded JSON from {file_path}")
            return data
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in {file_path}: {str(e)}")
        raise json.JSONDecodeError(f"Invalid JSON format: {str(e)}", e.doc, e.pos)
    except Exception as e:
        logger.error(f"Error reading JSON file {file_path}: {str(e)}")
        raise Exception(f"Error reading JSON file: {str(e)}")


class OptimizedJsonSearcher:
    """Optimierte Klasse für die Suche in JSON-Datenstrukturen mit Indexierung."""

    def __init__(self, search_data: Dict[str, Any]):
        self.search_data = search_data
        self.root_elements = self._find_root_elements(search_data)

        # Performance-Optimierungen: Vorberechnete Indizes
        self._gtin_index: Dict[str, Dict[str, Any]] = {}
        self._ref_index: Dict[str, Dict[str, Any]] = {}
        self._search_term_index: Dict[str, Set[int]] = defaultdict(set)

        # Index beim Initialisieren erstellen
        self._build_indexes()

    def _build_indexes(self) -> None:
        """Erstellt Such-Indizes für bessere Performance."""
        logger.info("Erstelle Such-Indizes...")

        for idx, root_element in enumerate(self.root_elements):
            # Direkte Suche nach GTIN und Referenznummer in der Struktur
            gtin = self._extract_direct_gtin(root_element)
            ref = self._extract_direct_ref(root_element)

            if gtin:
                self._gtin_index[gtin.lower()] = root_element
                self._search_term_index[gtin.lower()].add(idx)

            if ref:
                self._ref_index[ref.lower()] = root_element
                self._search_term_index[ref.lower()].add(idx)

            # Zusätzliche Indexierung aller String-Werte für Fallback-Suche
            self._index_all_strings(root_element, idx)

        logger.info(f"Indizes erstellt: {len(self._gtin_index)} GTINs, {len(self._ref_index)} Referenzen")

    def _extract_direct_gtin(self, element: Dict[str, Any]) -> str:
        """Extrahiert GTIN direkt aus der Datenstruktur ohne JSON-String-Parsing."""
        try:
            # Suche nach UDI-Pattern in der Struktur
            for key, value in element.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if 'UDI' in str(sub_key) and 'ARI_Artikelkennzeichen' in value:
                            return str(value['ARI_Artikelkennzeichen'])
            return ''
        except (KeyError, TypeError):
            return ''

    def _extract_direct_ref(self, element: Dict[str, Any]) -> str:
        """Extrahiert Referenznummer direkt aus der Datenstruktur ohne JSON-String-Parsing."""
        try:
            # Suche nach REF-Pattern in der Struktur
            for key, value in element.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if '(REF)' in str(sub_key) and 'ARI_Artikelkennzeichen' in value:
                            return str(value['ARI_Artikelkennzeichen'])
            return ''
        except (KeyError, TypeError):
            return ''

    def _index_all_strings(self, obj: Any, element_idx: int, max_depth: int = 3, current_depth: int = 0) -> None:
        """Indexiert alle String-Werte für Fallback-Suche mit Tiefenbegrenzung."""
        if current_depth > max_depth:
            return

        if isinstance(obj, dict):
            for key, value in obj.items():
                # Indexiere Schlüssel
                key_str = str(key).lower()
                if len(key_str) > 2:  # Nur längere Strings indexieren
                    self._search_term_index[key_str].add(element_idx)

                # Rekursiv weitermachen
                self._index_all_strings(value, element_idx, max_depth, current_depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                self._index_all_strings(item, element_idx, max_depth, current_depth + 1)
        else:
            # Indexiere String-Werte
            str_value = str(obj).lower()
            if len(str_value) > 2:  # Nur längere Strings indexieren
                self._search_term_index[str_value].add(element_idx)

    def search_refnumber(self, gtin: str) -> str:
        """Optimierte Suche nach Referenznummer für eine GTIN."""
        logger.info(f"Suche nach GTIN: {gtin}")

        # Zuerst im GTIN-Index suchen
        gtin_lower = gtin.lower()
        if gtin_lower in self._gtin_index:
            root_element = self._gtin_index[gtin_lower]
            ref = self._extract_direct_ref(root_element)
            if ref:
                logger.info(f"Referenznummer gefunden (Index): {ref}")
                return ref

        # Fallback: Vollsuche falls nicht im Index
        return self._fallback_search_identifier(gtin, self._extract_refnumber_from_json, "Referenznummer")

    def search_gtin(self, ref: str) -> str:
        """Optimierte Suche nach GTIN für eine Referenznummer."""
        logger.info(f"Suche nach Ref-Nr.: {ref}")

        # Zuerst im Referenz-Index suchen
        ref_lower = ref.lower()
        if ref_lower in self._ref_index:
            root_element = self._ref_index[ref_lower]
            gtin = self._extract_direct_gtin(root_element)
            if gtin:
                logger.info(f"GTIN gefunden (Index): {gtin}")
                return gtin

        # Fallback: Vollsuche falls nicht im Index
        return self._fallback_search_identifier(ref, self._extract_gtin_from_json, "GTIN")

    def search_in_dictionary(self, search_term: str) -> List[Tuple[str, Any, Dict[str, Any]]]:
        """Optimierte Suche mit Index-basiertem Ansatz."""
        results = []
        search_term_lower = search_term.lower()

        # Zuerst im Index suchen
        matching_indices = self._search_term_index.get(search_term_lower, set())

        if matching_indices:
            for idx in matching_indices:
                if idx < len(self.root_elements):
                    root_element = self.root_elements[idx]
                    results.append((f"Root-Element {idx}: gefunden", search_term, root_element))
        else:
            # Fallback: Teilstring-Suche im Index
            for indexed_term, indices in self._search_term_index.items():
                if search_term_lower in indexed_term:
                    for idx in indices:
                        if idx < len(self.root_elements):
                            root_element = self.root_elements[idx]
                            results.append((f"Root-Element {idx}: {indexed_term}", search_term, root_element))
                    break  # Nur erste Übereinstimmung für Performance

        return results

    def _fallback_search_identifier(self, search_term: str, extractor_func, identifier_type: str) -> str:
        """Fallback-Suche wenn Index-Suche fehlschlägt."""
        gefundene_eintraege = self.search_in_dictionary(search_term)
        if not gefundene_eintraege:
            logger.warning(f"Keine Einträge gefunden für {identifier_type}-Suche: {search_term}")
            return ''

        logger.info(f"Gefunden: {len(gefundene_eintraege)} Einträge für {search_term}")
        eindeutige_root_elemente = self._get_unique_root_elements(gefundene_eintraege)

        for root_element in eindeutige_root_elemente:
            json_str = json.dumps(root_element, indent=2, ensure_ascii=False)
            result = extractor_func(json_str)
            if result:
                logger.info(f"{identifier_type} gefunden: {result}")
                return result

        logger.warning(f"Keine {identifier_type} im gefundenen Eintrag für: {search_term}")
        return ''

    def _find_root_elements(self, data: Union[Dict[str, Any], List]) -> List[Dict[str, Any]]:
        """Findet die Root-Elemente für die Suche."""
        if isinstance(data, list):
            return data
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                return value
        return [data]

    def _get_unique_root_elements(self, gefundene_eintraege: List[Tuple[str, Any, Dict[str, Any]]]) -> List[
        Dict[str, Any]]:
        """Gibt eine Liste eindeutiger Root-Elemente zurück - optimiert."""
        seen_ids = set()
        eindeutige_elemente = []

        for _, _, root_element in gefundene_eintraege:
            # Verwende id() statt JSON-Hash für bessere Performance
            element_id = id(root_element)
            if element_id not in seen_ids:
                eindeutige_elemente.append(root_element)
                seen_ids.add(element_id)

        return eindeutige_elemente

    def _extract_refnumber_from_json(self, json_str: str) -> str:
        """Extrahiert die Referenznummer aus einem JSON-String."""
        zeilen = json_str.splitlines()
        for i, zeile in enumerate(zeilen):
            if '(REF)' in zeile and i + 1 < len(zeilen):
                naechste_zeile = zeilen[i + 1].strip()
                if naechste_zeile.startswith('"ARI_Artikelkennzeichen":'):
                    return naechste_zeile.split('"')[3]
        return ''

    def _extract_gtin_from_json(self, json_str: str) -> str:
        """Extrahiert die GTIN aus einem JSON-String."""
        zeilen = json_str.splitlines()
        for i, zeile in enumerate(zeilen):
            if 'UDI' in zeile and i + 1 < len(zeilen):
                naechste_zeile = zeilen[i + 1].strip()
                if naechste_zeile.startswith('"ARI_Artikelkennzeichen":'):
                    return naechste_zeile.split('"')[3]
        return ''


def init_search(search_file: str) -> Dict[str, Any]:
    """Initialisiert Suchdaten aus einer JSON-Datei."""
    try:
        search_data = import_json_file(search_file)
        return search_data
    except FileNotFoundError as e:
        logging.error(f"Suchdatei nicht gefunden: {e}")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Ungültiges JSON-Format in Suchdatei: {e}")
        return {}
    except Exception as e:
        logging.error(f"Unerwarteter Fehler beim Laden der Suchdatei: {e}")
        return {}


# Kompatibilitätsfunktionen mit automatischem Caching
_cached_searcher = None
_cached_data_id = None


def _get_cached_searcher(data: Dict[str, Any]) -> OptimizedJsonSearcher:
    """Gibt einen gecachten JsonSearcher zurück."""
    global _cached_searcher, _cached_data_id

    data_id = id(data)
    if _cached_searcher is None or _cached_data_id != data_id:
        _cached_searcher = OptimizedJsonSearcher(data)
        _cached_data_id = data_id

    return _cached_searcher


def search_in_dictionary(data: Union[Dict[str, Any], List], search_term: str) -> List[Tuple[str, Any, Dict[str, Any]]]:
    """Kompatibilitätsfunktion für bestehenden Code."""
    searcher = _get_cached_searcher(data)
    return searcher.search_in_dictionary(search_term)


def search_refnumber(gtin: str, search_data: Dict[str, Any]) -> str:
    """Kompatibilitätsfunktion für bestehenden Code."""
    searcher = _get_cached_searcher(search_data)
    return searcher.search_refnumber(gtin)


def search_gtin(ref: str, search_data: Dict[str, Any]) -> str:
    """Kompatibilitätsfunktion für bestehenden Code."""
    searcher = _get_cached_searcher(search_data)
    return searcher.search_gtin(ref)










DEBUGGING = 0  # if 1 then debugging is on else off


def sqllog(func):
    """
    decorator function for saving SQL calls -> sql.log
    :param func: none
    :return: function
    """

    def wrapper(*args, **kwargs):
        if sys.platform == 'win32':  # Windows
            cp = 'cp1250'
        else:  # own Mac
            cp = 'utf-8'
        if DEBUGGING:
            log = codecs.open('sql.log', 'a', cp)
            log.write(f'{args[1]}\n')
            log.flush()
            log.close()
        return func(*args, **kwargs)

    return wrapper


class Database:
    """
    database class
    """

    def __init__(self, host, dbname, username, password):
        self.host = host
        self.dbname = dbname
        self.username = username
        self.password = password
        self.conn, self.cur = None, None

    def name(self):
        return self.dbname

#    @datalog
    def open_db(self):
        try:  # catch database error...
            connection_params = {
                "host": self.host,
                "dbname": self.dbname,
                "user": self.username,
                "password": self.password,
                "options": "-c client_encoding=UTF8"
            }
            connection_string = " ".join("%s='%s'" % (key, val)
                                         for key, val in connection_params.items())
            self.conn = psycopg2.connect(connection_string)
            self.cur = self.conn.cursor()
        except psycopg2.OperationalError as e:
            self.protocol(f"-- {str(e)}")
            # Avoid abrupt termination; re-raise so callers can present UI message
            raise

    def close_db(self):
        try:  # catch database error...
            if self.cur is not None:
                try:
                    self.cur.close()
                except psycopg2.Error as e:
                    self.protocol(f'-- cursor close error: {e}')
            if self.conn is not None:
                try:
                    self.conn.close()
                except psycopg2.Error as e:
                    self.protocol(f'-- connection close error: {e}')
        except Exception as e:
            self.protocol(f'-- unexpected close_db error: {e}')
        finally:
            self.cur = None
            self.conn = None
            return

    @sqllog
    def fetchall(self, sql, params=None):
        if not self.cur:
            self.protocol('-- fetchall called without open cursor')
            raise psycopg2.OperationalError('Cursor not available. Did you call open_db()?')
        try:
            if params is None:
                self.cur.execute(sql)
            else:
                self.cur.execute(sql, params)
            return self.cur.fetchall()
        except psycopg2.Error as e:
            self.protocol(f'-- fetchall error: {e}\n-- SQL: {sql[:500]}')
            raise

    @sqllog
    def fetchone(self, sql, params=None):
        if not self.cur:
            self.protocol('-- fetchone called without open cursor')
            raise psycopg2.OperationalError('Cursor not available. Did you call open_db()?')
        try:
            if params is None:
                self.cur.execute(sql)
            else:
                self.cur.execute(sql, params)
            return self.cur.fetchone()
        except psycopg2.Error as e:
            self.protocol(f'-- fetchone error: {e}\n-- SQL: {sql[:500]}')
            raise

    @sqllog
    def execute(self, sql, params=None):
        if not self.cur or not self.conn:
            self.protocol('-- execute called without open connection/cursor')
            raise psycopg2.OperationalError('Connection not available. Did you call open_db()?')
        try:
            if params is None:
                self.cur.execute(sql)
            else:
                self.cur.execute(sql, params)
            self.conn.commit()
        except psycopg2.Error as e:
            self.protocol(f'-- execute error: {e}\n-- SQL: {sql[:500]}')
            raise

    @sqllog
    def update(self, sql, params=None):
        return self.execute(sql, params)

    @sqllog
    def insert(self, sql, params=None):
        return self.execute(sql, params)

    def protocol(self, text: str) -> None:
        """Append a timestamped line to the database-specific log file.

        Uses a context manager to ensure the file is always closed and
        avoids crashing the application on logging failures.
        """
        try:
            with open(self.dbname + '.log', 'a', encoding='utf-8') as log:
                log.write(f'-- {datetime.now()}\n')
                log.write(f'{text}\n')
                log.flush()
        except Exception:
            # Swallow any logging errors to not impact main flow
            pass




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



            





if __name__ == '__main__':

    barcode_processor = BarcodeProcessor()
    data = init_search('J:/EPZ/Daten OA Troeger/table-EP_ARTIKEL.json')

    proth_list = Database('139.64.201.9', 'eprd_db2_m1', 'postgres', 'SuperUser2012')
    proth_list.open_db()
    query = ('SELECT * from artikel_ep;')
    records = proth_list.fetchall(query)
    for record in records:
        ref_nr, idnr = record[2], record[5]
        print (ref_nr,idnr)
        gtin = search_gtin(ref_nr, data)
        chk = barcode_processor.gtin_validator.validate_gtin(gtin)
        if chk:
            print (gtin)
            proth_list.execute(f'update artikel_ep set gtin = {gtin} where id = {idnr};')
        

    
    

    
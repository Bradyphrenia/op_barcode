import json
import os
from typing import Dict, List, Any, Tuple, Union
import logging

# Logging-Konfiguration hinzufügen
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Ausgabe auf der Konsole
        logging.FileHandler('import_ep.log')  # Speichern in einer Logdatei
    ]
)
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

class JsonSearcher:
    """Klasse für die Suche in JSON-Datenstrukturen."""

    def __init__(self, search_data: Dict[str, Any]):
        self.search_data = search_data

    def search_in_dictionary(self, search_term: str) -> List[Tuple[str, Any, Dict[str, Any]]]:
        """
        Durchsucht rekursiv ein Dictionary oder eine Liste nach einem Suchbegriff.
        Args:
            search_term: Der Suchbegriff
        Returns:
            Liste von Treffern als Tupel (Pfad, gefundener Wert, Root-Element)
        """
        results = []
        root_elements = self._find_root_elements(self.search_data)
        search_term_lower = str(search_term).lower()
        for idx, root_element in enumerate(root_elements):
            self._search_recursively(root_element, idx, search_term_lower, "", results, root_element)
        return results

    def search_refnumber(self, gtin: str) -> str:
        """
        Sucht nach der Referenznummer für eine gegebene GTIN in den Suchdaten.
        Args:
            gtin: Die zu suchende GTIN
        Returns:
            Die gefundene Referenznummer oder ein leerer String, wenn nichts gefunden wurde
        """
        logger.info(f"Suche nach GTIN: {gtin}")
        return self._search_identifier(gtin, self._extract_refnumber_from_json, "Referenznummer")

    def search_gtin(self, ref: str) -> str:
        """
        Sucht nach der GTIN für eine gegebene Ref-Nr. in den Suchdaten.
        Args:
            ref: Die zu suchende Ref-Nr.
        Returns:
            Die gefundene GTIN oder ein leerer String, wenn nichts gefunden wurde
        """
        logger.info(f"Suche nach Ref-Nr.: {ref}")
        return self._search_identifier(ref, self._extract_gtin_from_json, "GTIN")

    def _search_identifier(self, search_term: str, extractor_func, identifier_type: str) -> str:
        """
        Gemeinsame Suchlogik für Identifikatoren.
        Args:
            search_term: Der zu suchende Begriff
            extractor_func: Funktion zum Extrahieren des gewünschten Identifikators
            identifier_type: Typ des Identifikators für Logging
        Returns:
            Der gefundene Identifikator oder ein leerer String
        """
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
        """
        Findet die Root-Elemente für die Suche.
        Args:
            data: Das zu durchsuchende Dictionary oder die Liste
        Returns:
            Liste von Root-Elementen für die Suche
        """
        if isinstance(data, list):
            return data
        # Suche nach einer Liste von Dictionaries
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                return value
        # Fallback: Das Dictionary selbst als einziges Root-Element verwenden
        return [data]

    def _search_recursively(
            self,
            obj: Any,
            root_idx: int,
            search_term_lower: str,
            path: str,
            results: List[Tuple[str, Any, Dict[str, Any]]],
            root_element: Dict[str, Any]
    ) -> None:
        """
        Führt eine rekursive Suche in einem Objekt durch.
        Args:
            obj: Das zu durchsuchende Objekt
            root_idx: Index des Root-Elements
            search_term_lower: Der Suchbegriff in Kleinbuchstaben
            path: Der aktuelle Pfad im Objekt
            results: Liste zum Speichern der Ergebnisse
            root_element: Das Root-Element für Referenzierung in Ergebnissen
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                if search_term_lower in str(key).lower():
                    results.append((f"Root-Element {root_idx}: {new_path}", key, root_element))
                self._search_recursively(value, root_idx, search_term_lower, new_path, results, root_element)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_path = f"{path}[{i}]"
                self._search_recursively(item, root_idx, search_term_lower, new_path, results, root_element)
        else:
            if search_term_lower in str(obj).lower():
                results.append((f"Root-Element {root_idx}: {path}", obj, root_element))

    def _get_unique_root_elements(self, gefundene_eintraege: List[Tuple[str, Any, Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Gibt eine Liste eindeutiger Root-Elemente zurück."""
        eindeutige_elemente = []
        gesehene_hashes = set()
        for _, _, root_element in gefundene_eintraege:
            element_hash = hash(json.dumps(root_element, sort_keys=True))
            if element_hash not in gesehene_hashes:
                eindeutige_elemente.append(root_element)
                gesehene_hashes.add(element_hash)
        return eindeutige_elemente

    def _extract_refnumber_from_json(self, json_str: str) -> str:
        """Extrahiert die Referenznummer aus einem JSON-String, wenn vorhanden."""
        zeilen = json_str.splitlines()
        for i, zeile in enumerate(zeilen):
            if '(REF)' in zeile and i + 1 < len(zeilen):
                naechste_zeile = zeilen[i + 1].strip()
                if naechste_zeile.startswith('"ARI_Artikelkennzeichen":'):
                    return naechste_zeile.split('"')[3]
        return ''

    def _extract_gtin_from_json(self, json_str: str) -> str:
        """Extrahiert die GTIN aus einem JSON-String, wenn vorhanden."""
        zeilen = json_str.splitlines()
        for i, zeile in enumerate(zeilen):
            if 'UDI' in zeile and i + 1 < len(zeilen):
                naechste_zeile = zeilen[i + 1].strip()
                if naechste_zeile.startswith('"ARI_Artikelkennzeichen":'):
                    return naechste_zeile.split('"')[3]
        return ''

def init_search(search_file: str) -> Dict[str, Any]:
    """
    Initialisiert Suchdaten aus einer JSON-Datei.
    Args:
        search_file: Pfad zur JSON-Datei, standardmäßig "table-EP_ARTIKEL2.json"
    Returns:
        Dictionary mit Suchdaten oder leeres Dictionary bei Fehler
    """
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

# Kompatibilitätsfunktionen für bestehenden Code
def search_in_dictionary(data: Union[Dict[str, Any], List], search_term: str) -> List[Tuple[str, Any, Dict[str, Any]]]:
    """Kompatibilitätsfunktion für bestehenden Code."""
    searcher = JsonSearcher(data)
    return searcher.search_in_dictionary(search_term)

def search_refnumber(gtin: str, search_data: Dict[str, Any]) -> str:
    """Kompatibilitätsfunktion für bestehenden Code."""
    searcher = JsonSearcher(search_data)
    return searcher.search_refnumber(gtin)

def search_gtin(ref: str, search_data: Dict[str, Any]) -> str:
    """Kompatibilitätsfunktion für bestehenden Code."""
    searcher = JsonSearcher(search_data)
    return searcher.search_gtin(ref)

if __name__ == '__main__':
    data = init_search('../table-EP_ARTIKEL2.json')
    test = "07611996073546"
    print(search_refnumber(test, data))
    print(search_in_dictionary(data, 'DJO'))
    print(search_in_dictionary(data, '880-010/50'))
    print(search_gtin('880-010/50', data))
    print(search_gtin('880-010/5', data))
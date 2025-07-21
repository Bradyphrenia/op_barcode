import json
import os
from typing import Dict, Any
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


from typing import Dict, List, Any, Tuple, Union


def search_in_dictionary(data: Union[Dict, List], search_term: str) -> List[Tuple[str, Any, Dict]]:
    """
    Durchsucht rekursiv ein Dictionary oder eine Liste nach einem Suchbegriff.

    Args:
        data: Das zu durchsuchende Dictionary oder die Liste
        search_term: Der Suchbegriff

    Returns:
        Liste von Treffern als Tupel (Pfad, gefundener Wert, Root-Element)
    """
    results = []
    root_elements = _find_root_elements(data)
    search_term_lower = str(search_term).lower()

    for idx, root_element in enumerate(root_elements):
        _search_recursively(root_element, idx, search_term_lower, "", results, root_element)

    return results


def _find_root_elements(data: Union[Dict, List]) -> List[Dict]:
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
        obj: Any,
        root_idx: int,
        search_term_lower: str,
        path: str,
        results: List[Tuple[str, Any, Dict]],
        root_element: Dict
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
            _search_recursively(value, root_idx, search_term_lower, new_path, results, root_element)

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            _search_recursively(item, root_idx, search_term_lower, new_path, results, root_element)

    else:
        if search_term_lower in str(obj).lower():
            results.append((f"Root-Element {root_idx}: {path}", obj, root_element))


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


def search_refnumber(gtin: str, search_data) -> str:
    """
    Sucht nach der Referenznummer für eine gegebene GTIN in den Suchdaten.

    Args:
        gtin: Die zu suchende GTIN
        search_data: Die Daten, in denen gesucht werden soll

    Returns:
        Die gefundene Referenznummer oder ein leerer String, wenn nichts gefunden wurde
    """
    logger.info(f"Suche nach GTIN: {gtin}")

    # Suche nach Einträgen
    gefundene_eintraege = search_in_dictionary(search_data, gtin)

    if not gefundene_eintraege:
        logger.warning(f"Keine Einträge gefunden für GTIN {gtin}")
        return ''

    logger.info(f"Gefunden: {len(gefundene_eintraege)} Einträge für GTIN {gtin}")

    # Verarbeite nur eindeutige Root-Elemente
    eindeutige_root_elemente = _get_unique_root_elements(gefundene_eintraege)

    # Suche nach Referenznummer in den JSON-Daten
    for root_element in eindeutige_root_elemente:
        json_str = json.dumps(root_element, indent=2, ensure_ascii=False)
        refnummer = _extract_refnumber_from_json(json_str)

        if refnummer:
            logger.info(f"Referenznummer gefunden: {refnummer}")
            return refnummer

    logger.warning(f"Keine Referenznummer im gefundenen Eintrag für GTIN {gtin}")
    return ''


def _get_unique_root_elements(gefundene_eintraege: list) -> list:
    """Gibt eine Liste eindeutiger Root-Elemente zurück."""
    eindeutige_elemente = []
    gesehene_hashes = set()

    for _, _, root_element in gefundene_eintraege:
        element_hash = hash(json.dumps(root_element, sort_keys=True))
        if element_hash not in gesehene_hashes:
            eindeutige_elemente.append(root_element)
            gesehene_hashes.add(element_hash)

    return eindeutige_elemente


def _extract_refnumber_from_json(json_str: str) -> str:
    """Extrahiert die Referenznummer aus einem JSON-String, wenn vorhanden."""
    zeilen = json_str.splitlines()

    for i, zeile in enumerate(zeilen):
        if '(REF)' in zeile and i + 1 < len(zeilen):
            naechste_zeile = zeilen[i + 1].strip()
            if naechste_zeile.startswith('"ARI_Artikelkennzeichen":'):
                return naechste_zeile.split('"')[3]

    return ''


def _extract_gtin_from_json(json_str: str) -> str:
    """Extrahiert die GTIN aus einem JSON-String, wenn vorhanden."""
    zeilen = json_str.splitlines()

    for i, zeile in enumerate(zeilen):
        if 'UDI' in zeile and i + 1 < len(zeilen):
            naechste_zeile = zeilen[i + 1].strip()
            if naechste_zeile.startswith('"ARI_Artikelkennzeichen":'):
                return naechste_zeile.split('"')[3]

    return ''


def search_gtin(ref: str, search_data) -> str:
    """
    Sucht nach der GTIN für eine gegebene Ref-Nr. in den Suchdaten.

    Args:
        ref: Die zu suchende Ref-Nr.
        search_data: Die Daten, in denen gesucht werden soll

    Returns:
        Die gefundene GTIN oder ein leerer String, wenn nichts gefunden wurde
    """
    logger.info(f"Suche nach Ref-Nr.: {ref}")

    # Suche nach Einträgen
    gefundene_eintraege = search_in_dictionary(search_data, ref)

    if not gefundene_eintraege:
        logger.warning(f"Keine Einträge gefunden für Ref-Nr.: {ref}")
        return ''

    logger.info(f"Gefunden: {len(gefundene_eintraege)} Einträge für Ref-Nr. {ref}")

    # Verarbeite nur eindeutige Root-Elemente
    eindeutige_root_elemente = _get_unique_root_elements(gefundene_eintraege)

    # Suche nach Referenznummer in den JSON-Daten
    for root_element in eindeutige_root_elemente:
        json_str = json.dumps(root_element, indent=2, ensure_ascii=False)
        gtin = _extract_gtin_from_json(json_str)

        if gtin:
            logger.info(f"GTIN gefunden: {gtin}")
            return gtin

    logger.warning(f"Keine GTIN im gefundenen Eintrag für Ref-Nr.: {ref}")
    return ''


if __name__ == '__main__':
    data = init_search('../table-EP_ARTIKEL2.json')
    test = "07611996073546"
    print(search_refnumber(test, data))
    print(search_in_dictionary(data, 'DJO'))
    print(search_in_dictionary(data, '880-010/50'))
    print(search_gtin('880-010/50', data))

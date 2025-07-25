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


if __name__ == '__main__':
    data = init_search('../table-EP_ARTIKEL2.json')
    test = "07611996073546"
    print(search_refnumber(test, data))
    print(search_in_dictionary(data, 'DJO'))
    print(search_in_dictionary(data, '880-010/50'))
    print(search_gtin('880-010/50', data))
    print(search_gtin('880-010/5', data))

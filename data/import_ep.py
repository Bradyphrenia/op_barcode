import json
import os
from typing import Dict, Any


def import_json_file(file_path: str) -> Dict[str, Any]:
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON format: {str(e)}", e.doc, e.pos)
    except Exception as e:
        raise Exception(f"Error reading JSON file: {str(e)}")


def suche_in_dictionary(dictionary, suchbegriff):
    ergebnisse = []
    if isinstance(dictionary, list):
        root_elements = dictionary
    else:
        root_elements = None
        for key, value in dictionary.items():
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                root_elements = value
                break
        if root_elements is None:
            root_elements = [dictionary]
    for idx, root_element in enumerate(root_elements):
        treffer_gefunden = [False]

        def rekursive_suche(objekt, pfad=""):
            if isinstance(objekt, dict):
                for key, value in objekt.items():
                    neuer_pfad = f"{pfad}.{key}" if pfad else key
                    if str(suchbegriff).lower() in str(key).lower():
                        treffer_gefunden[0] = True
                        ergebnisse.append((f"Root-Element {idx}: {neuer_pfad}", key, root_element))
                    rekursive_suche(value, neuer_pfad)
            elif isinstance(objekt, list):
                for i, item in enumerate(objekt):
                    neuer_pfad = f"{pfad}[{i}]"
                    rekursive_suche(item, neuer_pfad)
            else:
                if str(suchbegriff).lower() in str(objekt).lower():
                    treffer_gefunden[0] = True
                    ergebnisse.append((f"Root-Element {idx}: {pfad}", objekt, root_element))

        rekursive_suche(root_element)
    return ergebnisse


def init_search() -> Dict[str, Any]:
    search_file = "table-EP_ARTIKEL2.json"
    try:
        search_data = import_json_file(search_file)
        return search_data
    except:
        return {}


def search_refnumber(gtin: str, search_data) -> str:
    suchbegriff = gtin
    gefundene_einträge = suche_in_dictionary(search_data, suchbegriff)
    if gefundene_einträge:
        gezeigte_root_elemente = set()
        gefunden = ''
        for pfad, wert, root_element in gefundene_einträge:
            root_hash = hash(json.dumps(root_element, sort_keys=True))
            if root_hash not in gezeigte_root_elemente:
                gefunden += json.dumps(root_element, indent=2, ensure_ascii=False)
                gezeigte_root_elemente.add(root_hash)
            gefunden_str = gefunden.splitlines()
            for i, zeile in enumerate(gefunden_str):
                if '(REF)' in zeile:
                    if gefunden_str[i + 1].strip().startswith('"ARI_Artikelkennzeichen":'):
                        return gefunden_str[i + 1].strip().split('"')[3]
            return ''
    else:
        return ''


if __name__ == '__main__':
    data = init_search()
    test = "07611996073546"
    print(search_refnumber(test, data))

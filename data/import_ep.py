import json
import os
from typing import Dict, Any, List
import psycopg2
from psycopg2.extras import Json, execute_batch


def import_json_file(file_path: str) -> Dict[str, Any]:
    """
    Import and parse JSON file from the given path

    Args:
        file_path (str): Path to the JSON file

    Returns:
        Dict[str, Any]: Parsed JSON data as dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data

    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON format: {str(e)}", e.doc, e.pos)
    except Exception as e:
        raise Exception(f"Error reading JSON file: {str(e)}")


def suche_in_dictionary(dictionary, suchbegriff):
    """
    Durchsucht ein Dictionary rekursiv nach einem Suchbegriff
    und gibt die gefundenen Pfade zurück.
    """
    ergebnisse = []

    def rekursive_suche(objekt, pfad=""):
        if isinstance(objekt, dict):
            for key, value in objekt.items():
                neuer_pfad = f"{pfad}.{key}" if pfad else key
                if str(suchbegriff).lower() in str(key).lower():
                    ergebnisse.append((neuer_pfad, key))
                rekursive_suche(value, neuer_pfad)
        elif isinstance(objekt, list):
            for i, item in enumerate(objekt):
                neuer_pfad = f"{pfad}[{i}]"
                rekursive_suche(item, neuer_pfad)
        else:
            if str(suchbegriff).lower() in str(objekt).lower():
                ergebnisse.append((pfad, objekt))

    rekursive_suche(dictionary)
    return ergebnisse


def connect_to_postgres(host: str, port: int, dbname: str, user: str, password: str):
    """
    Stellt eine Verbindung zur PostgreSQL-Datenbank her

    Args:
        host (str): Datenbank-Host
        port (int): Datenbank-Port
        dbname (str): Name der Datenbank
        user (str): Benutzername
        password (str): Passwort

    Returns:
        connection: PostgreSQL-Verbindungsobjekt
    """
    try:
        connection = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        return connection
    except Exception as e:
        raise Exception(f"Fehler bei der Datenbankverbindung: {str(e)}")


def extract_artikel_identification(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extrahiert Artikelidentifikation-Felder direkt in den Hauptdatensatz

    Args:
        records (List[Dict[str, Any]]): Liste von Datensätzen

    Returns:
        List[Dict[str, Any]]: Liste von Datensätzen mit extrahierten Artikelidentifikation-Feldern
    """
    processed_records = []

    for record in records:
        # Kopiere den Hauptdatensatz ohne artikelidentifikation
        new_record = {k: v for k, v in record.items() if k != "artikelidentifikation"}

        # Extrahiere Artikelidentifikation-Daten, falls vorhanden
        artikel_id = record.get("artikelidentifikation")
        if artikel_id and isinstance(artikel_id, dict):
            # Füge alle Felder aus artikelidentifikation direkt in den Hauptdatensatz ein
            for key, value in artikel_id.items():
                # Verwende die Originalfeldnamen ohne Präfix
                new_record[key] = value
        elif artikel_id:
            # Wenn artikelidentifikation existiert, aber kein Wörterbuch ist,
            # behalte es als eigenständiges Feld bei
            new_record["artikelidentifikation"] = artikel_id

        processed_records.append(new_record)

    return processed_records


def analyze_json_structure(records: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Analysiert die Struktur der JSON-Datensätze und bestimmt die häufigsten Datentypen
    für jedes Feld.

    Args:
        records (List[Dict[str, Any]]): Liste von Datensätzen

    Returns:
        Dict[str, str]: Zuordnung von Feldnamen zu PostgreSQL-Datentypen
    """
    if not records:
        return {}

    # Sammle alle Felder und ihre Typen
    field_types = {}
    for record in records[:100]:  # Analysiere nur die ersten 100 Datensätze
        for key, value in record.items():
            if key not in field_types:
                field_types[key] = []

            if value is None:
                continue
            elif isinstance(value, bool):
                field_types[key].append("boolean")
            elif isinstance(value, int):
                field_types[key].append("integer")
            elif isinstance(value, float):
                field_types[key].append("numeric")
            elif isinstance(value, str):
                field_types[key].append("text")
            elif isinstance(value, (dict, list)):
                field_types[key].append("jsonb")
            else:
                field_types[key].append("text")  # Fallback für unbekannte Typen

    # Bestimme den häufigsten Typ für jedes Feld
    result = {}
    for key, types in field_types.items():
        if not types:
            result[key] = "text"  # Fallback, wenn keine Typen gefunden wurden
        elif "jsonb" in types:
            result[key] = "jsonb"  # Wenn ein Feld sowohl einfache als auch komplexe Werte hat, wähle jsonb
        elif "text" in types:
            result[key] = "text"  # Text ist flexibler als numerische Typen
        elif "numeric" in types:
            result[key] = "numeric"
        elif "integer" in types:
            result[key] = "integer"
        elif "boolean" in types:
            result[key] = "boolean"
        else:
            result[key] = "text"  # Fallback

    return result


def create_structured_table(connection, table_name: str, field_types: Dict[str, str]):
    """
    Erstellt eine strukturierte Tabelle basierend auf den erkannten Feldtypen

    Args:
        connection: PostgreSQL-Verbindungsobjekt
        table_name (str): Name der zu erstellenden Tabelle
        field_types (Dict[str, str]): Zuordnung von Feldnamen zu PostgreSQL-Datentypen
    """
    try:
        cursor = connection.cursor()

        # Erstelle SQL für die Tabellendefinition
        columns = ["id SERIAL PRIMARY KEY", "import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP"]
        for field, field_type in field_types.items():
            # Sanitize field name (replace special characters)
            safe_field = field.replace(" ", "_").replace("-", "_").lower()
            columns.append(f"\"{safe_field}\" {field_type}")

        # Erstelle die Tabelle
        create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {', '.join(columns)}
            )
        """
        cursor.execute(create_table_sql)

        connection.commit()
        cursor.close()
        print(f"Strukturierte Tabelle {table_name} wurde erfolgreich erstellt oder existiert bereits.")
        return field_types
    except Exception as e:
        connection.rollback()
        raise Exception(f"Fehler beim Erstellen der strukturierten Tabelle: {str(e)}")


def import_structured_records_to_postgres(connection, table_name: str, records: List[Dict[str, Any]],
                                          field_types: Dict[str, str]):
    """
    Importiert Datensätze in die strukturierte PostgreSQL-Tabelle

    Args:
        connection: PostgreSQL-Verbindungsobjekt
        table_name (str): Name der Zieltabelle
        records (List[Dict[str, Any]]): Liste von Datensätzen
        field_types (Dict[str, str]): Zuordnung von Feldnamen zu PostgreSQL-Datentypen
    """
    try:
        cursor = connection.cursor()

        # Sanitize field names
        safe_fields = {field: field.replace(" ", "_").replace("-", "_").lower() for field in field_types.keys()}

        # Erstelle die SQL-Abfrage
        fields = [f"\"{safe_fields[field]}\"" for field in field_types.keys()]
        placeholders = ["%s"] * len(fields)

        query = f"INSERT INTO {table_name} ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"

        # Bereite die Daten für den Batch-Import vor
        template_data = []
        for record in records:
            row_data = []
            for field in field_types.keys():
                value = record.get(field)
                # Konvertiere komplexe Werte in JSON
                if isinstance(value, (dict, list)) and field_types[field] == "jsonb":
                    value = Json(value)
                row_data.append(value)
            template_data.append(tuple(row_data))

        # Batch-Ausführung mit angemessener Batch-Größe
        batch_size = min(1000, len(records))  # Maximal 1000 Datensätze pro Batch
        execute_batch(cursor, query, template_data, page_size=batch_size)

        connection.commit()
        cursor.close()
        print(f"{len(records)} Datensätze wurden erfolgreich in die strukturierte Tabelle {table_name} importiert.")
    except Exception as e:
        connection.rollback()
        raise Exception(f"Fehler beim Importieren der Datensätze in die strukturierte Tabelle: {str(e)}")


def extract_records_from_json(json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrahiert einzelne Datensätze aus der JSON-Struktur

    Args:
        json_data (Dict[str, Any]): JSON-Daten als Dictionary

    Returns:
        List[Dict[str, Any]]: Liste von Datensätzen
    """
    # Versuche, Datensätze zu finden, abhängig von der Struktur der JSON-Datei
    records = []

    # Fall 1: JSON ist bereits eine Liste von Datensätzen
    if isinstance(json_data, list):
        records = json_data
    # Fall 2: JSON enthält einen Schlüssel, der eine Liste von Datensätzen enthält
    elif isinstance(json_data, dict):
        # Suche nach Array-Eigenschaften, die wahrscheinlich Datensätze enthalten
        for key, value in json_data.items():
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                records = value
                break
        # Wenn keine Liste gefunden wurde, behandle jeden Top-Level-Schlüssel als Datensatz
        if not records:
            if all(isinstance(value, dict) for value in json_data.values()):
                records = [value for value in json_data.values()]
            # Wenn nichts anderes passt, behandle das gesamte JSON als einen Datensatz
            else:
                records = [json_data]

    return records


def import_multiple_files_to_postgres(file_configs, use_structured_tables=True, extract_artikel_id=False):
    """
    Importiert mehrere JSON-Dateien in entsprechende Tabellen

    Args:
        file_configs: Liste von Konfigurationen für die zu importierenden Dateien
                      [{"file_path": str, "table_name": str}, ...]
        use_structured_tables (bool): Wenn True, werden strukturierte Tabellen erstellt
        extract_artikel_id (bool): Wenn True, werden Artikelidentifikation-Felder extrahiert
    """
    # Datenbankverbindung herstellen
    try:
        # Konfigurieren Sie hier Ihre Datenbankverbindung
        db_config = {
            "host": "localhost",
            "port": 5432,
            "dbname": "ird_artikel",
            "user": "postgres",
            "password": "postgres"  # Ersetzen Sie dies durch Ihr tatsächliches Passwort
        }

        conn = connect_to_postgres(**db_config)

        for config in file_configs:
            file_path = config["file_path"]
            table_name = config["table_name"]

            print(f"\n=== Importiere {file_path} in Tabelle {table_name} ===")

            # JSON-Datei importieren
            try:
                json_data = import_json_file(file_path)

                # Extrahiere einzelne Datensätze aus der JSON-Struktur
                records = extract_records_from_json(json_data)

                if records:
                    # Extrahiere Artikelidentifikation-Felder
                    if extract_artikel_id:
                        print("Extrahiere Artikelidentifikation-Felder...")
                        records = extract_artikel_identification(records)

                    if use_structured_tables:
                        # Analysiere die Struktur der Datensätze
                        field_types = analyze_json_structure(records)

                        if field_types:
                            # Erstelle strukturierte Tabelle
                            create_structured_table(conn, table_name, field_types)

                            # Importiere Datensätze in die strukturierte Tabelle
                            import_structured_records_to_postgres(conn, table_name, records, field_types)
                        else:
                            print("Keine Felder für strukturierte Tabelle gefunden. Verwende Standard-JSON-Import.")
                            create_json_table(conn, table_name)
                            import_records_to_postgres(conn, table_name, records)
                    else:
                        # Verwende den Standard-JSON-Import
                        create_json_table(conn, table_name)
                        import_records_to_postgres(conn, table_name, records)

                    print(f"Es wurden {len(records)} Datensätze gefunden und importiert.")
                else:
                    # Wenn keine einzelnen Datensätze gefunden wurden, importiere das gesamte JSON
                    print("Keine einzelnen Datensätze gefunden. Importiere das gesamte JSON als einen Eintrag.")
                    create_json_table(conn, table_name)
                    import_json_to_postgres(conn, table_name, json_data)
            except Exception as e:
                print(f"Fehler beim Importieren von {file_path}: {str(e)}")
                # Weiter mit der nächsten Datei

        # Verbindung schließen
        conn.close()
        print("\nDatenbankverbindung wurde geschlossen.")

    except Exception as e:
        print(f"Fehler bei der Datenbankverbindung: {str(e)}")


def create_json_table(connection, table_name: str):
    """
    Erstellt eine Tabelle für JSON-Daten, falls sie nicht existiert

    Args:
        connection: PostgreSQL-Verbindungsobjekt
        table_name (str): Name der zu erstellenden Tabelle
    """
    try:
        cursor = connection.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                json_data JSONB,
                import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
        cursor.close()
        print(f"Tabelle {table_name} wurde erfolgreich erstellt oder existiert bereits.")
    except Exception as e:
        connection.rollback()
        raise Exception(f"Fehler beim Erstellen der Tabelle: {str(e)}")


def import_records_to_postgres(connection, table_name: str, records: List[Dict[str, Any]]):
    """
    Importiert mehrere Datensätze in die PostgreSQL-Datenbank als JSONB

    Args:
        connection: PostgreSQL-Verbindungsobjekt
        table_name (str): Name der Zieltabelle
        records (List[Dict[str, Any]]): Liste von Datensätzen
    """
    try:
        cursor = connection.cursor()

        # Vorbereiten des SQL-Statements für den Batch-Import
        query = f"INSERT INTO {table_name} (json_data) VALUES (%s)"

        # Vorbereiten der Daten für execute_batch
        template_data = [(Json(record),) for record in records]

        # Batch-Ausführung mit angemessener Batch-Größe
        batch_size = min(1000, len(records))  # Maximal 1000 Datensätze pro Batch
        execute_batch(cursor, query, template_data, page_size=batch_size)

        connection.commit()
        cursor.close()
        print(f"{len(records)} Datensätze wurden erfolgreich in die Tabelle {table_name} importiert.")
    except Exception as e:
        connection.rollback()
        raise Exception(f"Fehler beim Importieren der Datensätze: {str(e)}")


def import_json_to_postgres(connection, table_name: str, json_data: Dict[str, Any]):
    """
    Importiert das gesamte JSON-Dokument in die PostgreSQL-Datenbank

    Args:
        connection: PostgreSQL-Verbindungsobjekt
        table_name (str): Name der Zieltabelle
        json_data (Dict[str, Any]): JSON-Daten als Dictionary
    """
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"INSERT INTO {table_name} (json_data) VALUES (%s) RETURNING id",
            (Json(json_data),)
        )
        inserted_id = cursor.fetchone()[0]
        connection.commit()
        cursor.close()
        print(f"JSON-Daten wurden erfolgreich in Tabelle {table_name} mit ID {inserted_id} importiert.")
        return inserted_id
    except Exception as e:
        connection.rollback()
        raise Exception(f"Fehler beim Importieren der JSON-Daten: {str(e)}")


if __name__ == '__main__':
    # Konfiguration für die zu importierenden Dateien
    files_to_import = [
        {"file_path": "table-EP_ARTIKEL2.json", "table_name": "implantat"},
    ]

    # Import der Dateien mit strukturierten Tabellen starten und Artikelidentifikation extrahieren
    import_multiple_files_to_postgres(
        files_to_import,
        use_structured_tables=True,
        extract_artikel_id=True  # Aktiviert die Extraktion der Artikelidentifikation
    )

    # Optional: Suche in den Daten durchführen
    # Wählen Sie eine Datei für die Suche
    search_file = "table-EP_ARTIKEL2.json"
    try:
        search_data = import_json_file(search_file)
        suchbegriff = "48595"  # Ersetzen Sie dies durch Ihren Suchbegriff
        gefundene_einträge = suche_in_dictionary(search_data, suchbegriff)

        # Ergebnisse ausgeben
        if gefundene_einträge:
            print(f"\nGefunden '{suchbegriff}' in {search_file} an folgenden Stellen:")
            for pfad, wert in gefundene_einträge:
                print(f"Pfad: {pfad}, Wert: {wert}")
        else:
            print(f"\n'{suchbegriff}' wurde in {search_file} nicht gefunden.")
    except Exception as e:
        print(f"\nFehler bei der Suche: {str(e)}")

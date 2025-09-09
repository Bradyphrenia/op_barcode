import json
import psycopg2
from psycopg2.extras import Json
import os

def store_json_file_to_postgres(json_file_path, connection_params):
    """Store JSON file content directly to PostgreSQL"""

    # Read JSON file
    with open(json_file_path, 'r', encoding='utf-8') as file:
        json_data = json.load(file)

    # Connect to PostgreSQL
    conn = psycopg2.connect(**connection_params)
    cur = conn.cursor()

    try:
        # Insert JSON data
        filename = os.path.basename(json_file_path)
        cur.execute(
            "INSERT INTO json_data_storage (filename, data) VALUES (%s, %s)",
            (filename, Json(json_data))
        )

        conn.commit()
        print(f"Successfully stored {filename} to PostgreSQL")

    except Exception as e:
        conn.rollback()
        print(f"Error storing JSON data: {e}")
    finally:
        cur.close()
        conn.close()

# Usage example
connection_params = {
    'host': 'localhost',
    'database': 'your_database',
    'user': 'your_username',
    'password': 'your_password'
}

store_json_file_to_postgres('/path/to/table-EP_ARTIKEL2.json', connection_params)
#!/usr/bin/env python3
"""
import_jsonl_to_db.py

Sync messages_raw with the contents of messages.jsonl.

- Reads each line from ~/meshtastic/messages.jsonl
- Truncates messages_raw
- Inserts each JSON object into messages_raw.data (jsonb)

Run with:
    cd ~/meshtastic
    source bin/activate
    python3 import_jsonl_to_db.py
"""

import json
import pathlib
import sys
import psycopg2

# ---------- CONFIG ----------

JSONL_PATH = pathlib.Path("/home/pi/meshtastic/messages.jsonl")

DB_NAME = "meshtastic"
DB_USER = "pi"          # or "postgres", whichever user owns your tables
DB_PASSWORD = "hydro"   # remove this if you're using peer auth

TABLE_NAME = "messages_raw"
TRUNCATE_FIRST = True

# ----------------------------


def main():
    if not JSONL_PATH.exists():
        print(f"ERROR: JSONL file not found: {JSONL_PATH}")
        sys.exit(1)

    print(f"Connecting to database '{DB_NAME}' as user '{DB_USER}'...")

    # No host, no port → psycopg2 uses local UNIX socket
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    cur = conn.cursor()

    try:
        if TRUNCATE_FIRST:
            print(f"Truncating table {TABLE_NAME}...")
            cur.execute(f"TRUNCATE TABLE {TABLE_NAME};")
            conn.commit()

        count = 0
        print(f"Reading from {JSONL_PATH} ...")

        with JSONL_PATH.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"Skipping line {line_num}: invalid JSON ({e})")
                    continue

                cur.execute(
                    f"INSERT INTO {TABLE_NAME} (data) VALUES (%s::jsonb);",
                    (json.dumps(obj),),
                )
                count += 1

                if count % 100 == 0:
                    conn.commit()
                    print(f"Inserted {count} rows...")

        conn.commit()
        print(f"Done. Inserted {count} rows.")

    finally:
        cur.close()
        conn.close()
        print("Database connection closed.")


if __name__ == "__main__":
    main()

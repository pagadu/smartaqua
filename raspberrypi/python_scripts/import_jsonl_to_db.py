#!/usr/bin/env python3
"""
import_jsonl_to_db.py

Completely overwrite messages_raw with the contents of messages.jsonl.

- Reads each line from ~/meshtastic/messages.jsonl (one JSON object per line)
- TRUNCATES messages_raw
- Inserts each JSON object into messages_raw.data (jsonb)

# as user pi, no sudo
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
DB_USER = "pi"          # must match the Linux user you run this script as

TABLE_NAME = "messages_raw"   # expects a column named "data" of type jsonb
TRUNCATE_FIRST = True         # we WANT to wipe the table each run

# ----------------------------


def main():
    if not JSONL_PATH.exists():
        print(f"ERROR: JSONL file not found: {JSONL_PATH}")
        sys.exit(1)

    print(f"Connecting to database '{DB_NAME}' as user '{DB_USER}' (local peer auth)...")

    # No host, no port, no password → use local UNIX socket + peer auth
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
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

                if count and count % 100 == 0:
                    conn.commit()
                    print(f"Inserted {count} rows...")

        conn.commit()
        print(f"Done. Inserted {count} rows from {JSONL_PATH} into {TABLE_NAME}.")

    finally:
        cur.close()
        conn.close()
        print("Database connection closed.")


if __name__ == "__main__":
    main()

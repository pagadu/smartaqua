#!/usr/bin/env python3
"""
Meshtastic Message Logger
-------------------------
Listens for incoming messages from a connected Meshtastic radio
and saves them into a JSON Lines file for easy database import,
and also inserts each message into a PostgreSQL database.

Run with:
    source ~/meshtastic/bin/activate
    python3 ~/meshtastic/messageLogger.py
"""

import json
import time
import pathlib
from datetime import datetime

from pubsub import pub
from meshtastic.serial_interface import SerialInterface

# === PostgreSQL imports ===
import psycopg2
from psycopg2.extras import Json

# === Settings ===
LOG_PATH = pathlib.Path("/home/pi/meshtastic/messages.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# PostgreSQL connection settings
DB_NAME = "meshtastic"
DB_USER = "pi"          # change if you use a different user
DB_PASSWORD = None      # or set a password if needed
DB_HOST = "localhost"
DB_PORT = 5432

# Global DB connection / cursor
db_conn = None
db_cur = None


def init_db():
    """
    Try to connect to PostgreSQL and prepare a cursor.
    If it fails, we keep running but only log to file.
    """
    global db_conn, db_cur
    try:
        conn_args = {
            "dbname": DB_NAME,
            "user": DB_USER,
            "host": DB_HOST,
            "port": DB_PORT,
        }
        if DB_PASSWORD is not None:
            conn_args["password"] = DB_PASSWORD

        db_conn = psycopg2.connect(**conn_args)
        db_conn.autocommit = True
        db_cur = db_conn.cursor()
        print("Connected to PostgreSQL.")
    except Exception as e:
        print("WARNING: Could not connect to PostgreSQL:", e)
        print("         Will continue logging to file only.")
        db_conn = None
        db_cur = None


# === Helper: safely convert bytes to text ===
def b2s(value):
    """
    Convert bytes or bytearray to UTF-8 string.
    If it can't decode cleanly, return a hex string instead.
    """
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8", "replace")
        except Exception:
            return value.hex()
    return value


# === Handler: called whenever a new packet is received ===
def on_receive(packet, interface):
    """
    Extract key fields from each packet and append them to a log file
    and insert into the PostgreSQL database (if available).
    """
    decoded = packet.get("decoded") or {}
    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "from": packet.get("fromId"),
        "to": packet.get("toId"),
        "portnum": decoded.get("portnum"),       # message type ID
        "message": b2s(decoded.get("text")),     # convert if bytes
    }

    # --- 1) Append as one line of JSON to file ---
    try:
        with LOG_PATH.open("a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print("ERROR: Failed to write to log file:", e)

    # --- 2) Insert into PostgreSQL (if connected) ---
    global db_cur
    if db_cur is not None:
        try:
            db_cur.execute(
                "INSERT INTO messages_raw (data) VALUES (%s)",
                [Json(entry)],
            )
        except Exception as e:
            print("ERROR: Failed to insert into PostgreSQL:", e)

    print("Saved message:", entry["message"] or "(non-text packet)")


# === Subscribe to the Meshtastic event bus ===
pub.subscribe(on_receive, "meshtastic.receive")


# === Connect to the radio and DB ===
iface = SerialInterface()
init_db()

print("Listening for messages... (Press Ctrl+C to stop)")

# === Keep script running and responsive ===
try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nExiting cleanly...")
finally:
    try:
        iface.close()
    except Exception:
        pass
    if db_conn is not None:
        try:
            db_conn.close()
        except Exception:
            pass

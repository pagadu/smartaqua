#!/usr/bin/env python3
"""
Meshtastic Message Logger
-------------------------
Listens for incoming messages from a connected Meshtastic radio
and saves them into a JSON Lines file for easy database import.

Each message entry contains:
    - Timestamp
    - Sender node ID ("from")
    - Receiver node ID ("to")
    - Port number (message type)
    - Decoded text message

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


# === Settings ===
LOG_PATH = pathlib.Path("/home/pi/meshtastic/messages.jsonl")
# Ensure the parent directory exists
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


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
    Extract key fields from each packet and append them to a log file.
    """
    decoded = packet.get("decoded") or {}
    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "from": packet.get("fromId"),
        "to": packet.get("toId"),
        "portnum": decoded.get("portnum"),       # message type ID
        "message": b2s(decoded.get("text")),     # convert if bytes
    }

    # Append as one line of JSON
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")

    print("Saved message:", entry["message"] or "(non-text packet)")


# === Subscribe to the Meshtastic event bus ===
# pubsub is used internally by the Meshtastic Python library.
# We subscribe to the topic "meshtastic.receive" to get messages as they arrive.
pub.subscribe(on_receive, "meshtastic.receive")


# === Connect to the radio ===
# Automatically detects your USB-connected Meshtastic node.
iface = SerialInterface()

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

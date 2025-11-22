#!/usr/bin/env python3
import time
from meshtastic.serial_interface import SerialInterface
import pubsub.pub

print("Initializing Meshtastic connection...")
interface = SerialInterface(devPath="/dev/ttyUSB0")

print("Waiting for connection to stabilize...")
time.sleep(3)

def on_receive(packet, interface):
    if 'decoded' not in packet:
        return
    
    decoded = packet['decoded']
    
    # Ignore telemetry
    if decoded.get('portnum') == 'TELEMETRY_APP':
        print("📊 [Telemetry packet - ignoring]")
        return
    
    # Only process text
    if 'text' not in decoded:
        print(f"📦 [Non-text packet - type: {decoded.get('portnum', 'unknown')}]")
        return
    
    # Got text message!
    text = decoded['text']
    sender = packet.get('fromId', 'Unknown')
    
    print(f"\n{'='*70}")
    print(f"✉️  TEXT MESSAGE RECEIVED!")
    print(f"{'='*70}")
    print(f"From: {sender}")
    print(f"Message: {text}")
    print(f"{'='*70}\n")

pubsub.pub.subscribe(on_receive, "meshtastic.receive")

print("\n" + "="*70)
print("✓ Listening for TEXT messages only")
print("  (Telemetry and other packets will be ignored)")
print("="*70)
print("Send alert from dispatcher now!")
print("Press Ctrl+C to exit")
print("="*70 + "\n")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\nStopping...")
    interface.close()
    print("Closed.")
#!/usr/bin/env python3
import time
from meshtastic.serial_interface import SerialInterface
import pubsub.pub

print("Initializing Meshtastic connection...")
interface = SerialInterface(devPath="/dev/ttyUSB0")

print("Waiting for connection to stabilize...")
time.sleep(3)

def on_receive(packet, interface):
    print(f"\n{'='*70}")
    print(f"🔔 PACKET RECEIVED!")
    print(f"{'='*70}")
    print(f"Packet type: {type(packet)}")
    print(f"Packet keys: {packet.keys() if hasattr(packet, 'keys') else 'N/A'}")
    
    if 'decoded' in packet:
        print(f"✓ Decoded data present")
        if 'text' in packet['decoded']:
            print(f"✓ TEXT MESSAGE: {packet['decoded']['text']}")
        else:
            print(f"✗ No text in decoded")
            print(f"  Decoded keys: {packet['decoded'].keys()}")
    else:
        print(f"✗ No decoded data in packet")
    
    print(f"Full packet: {packet}")
    print(f"{'='*70}\n")

print("Subscribing to messages...")
pubsub.pub.subscribe(on_receive, "meshtastic.receive")

print("\n" + "="*70)
print("✓ LISTENING FOR MESSAGES")
print("="*70)
print("Send a test alert from your dispatcher NOW!")
print("Press Ctrl+C to exit")
print("="*70 + "\n")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\nStopping...")
    interface.close()
    print("Closed.")
#!/usr/bin/env python3
import time
from meshtastic.serial_interface import SerialInterface
import pubsub.pub

packet_count = 0

def on_receive(packet, interface):
    global packet_count
    packet_count += 1
    
    timestamp = time.strftime("%H:%M:%S")
    
    print(f"\n{'='*70}")
    print(f"[{timestamp}] [{packet_count}] ⚡ PACKET RECEIVED!")
    print(f"{'='*70}")
    print(f"Packet keys: {list(packet.keys())}")
    
    if 'from' in packet:
        print(f"From Node: {packet['from']}")
    
    if 'fromId' in packet:
        print(f"From ID: {packet['fromId']}")
    
    if 'decoded' in packet:
        decoded = packet['decoded']
        portnum = decoded.get('portnum', 'N/A')
        print(f"Port Type: {portnum}")
        
        if portnum == 'TELEMETRY_APP':
            print(f"  📊 TELEMETRY DATA")
            if 'telemetry' in decoded:
                telemetry = decoded['telemetry']
                if 'deviceMetrics' in telemetry:
                    metrics = telemetry['deviceMetrics']
                    print(f"    Battery: {metrics.get('batteryLevel', 'N/A')}%")
                    print(f"    Voltage: {metrics.get('voltage', 'N/A')}V")
        
        elif 'text' in decoded:
            text = decoded['text']
            print(f"  ✉️  TEXT MESSAGE!")
            print(f"    Content: {text}")
            
            # Check for LED command
            if '||LED:' in text:
                print(f"    🚨 LED COMMAND DETECTED!")
        
        else:
            print(f"  📦 Other packet type")
    else:
        print(f"  (No decoded data)")
    
    print(f"{'='*70}\n")

print("Initializing Meshtastic connection...")
interface = SerialInterface('/dev/ttyUSB0')
print("Waiting for connection to stabilize...")
time.sleep(3)

pubsub.pub.subscribe(on_receive, "meshtastic.receive")

print("\n" + "="*70)
print("✓ MONITORING ALL PACKETS")
print("="*70)
print("You should see:")
print("  📊 Telemetry packets every 30-60 seconds")
print("  ✉️  Text messages when you send alerts")
print("  📦 Other packet types occasionally")
print("\nSend alert from dispatcher and watch!")
print("Press Ctrl+C to exit")
print("="*70 + "\n")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print(f"\n\n⏹ Stopping...")
    print(f"Total packets received: {packet_count}")
    interface.close()
    print("✓ Closed.")
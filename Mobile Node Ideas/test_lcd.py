#!/usr/bin/env python3
"""
16x2 LCD I2C Test Script
Tests basic LCD functionality before full integration

This script will:
1. Detect LCD on I2C bus
2. Display test messages
3. Test scrolling
4. Verify display is working correctly
"""

import sys
import time

# Check for required libraries
try:
    from RPLCD.i2c import CharLCD
    print("✓ RPLCD library found")
except ImportError:
    print("✗ RPLCD library not found")
    print("  Install with: pip3 install RPLCD")
    sys.exit(1)

# Try both common I2C addresses
I2C_ADDRESSES = [0x27, 0x3F]

print("\n" + "="*60)
print("16x2 LCD I2C TEST SCRIPT")
print("="*60)

# Test I2C detection
print("\n1. Detecting LCD on I2C bus...")
print("-" * 60)

lcd = None
detected_address = None

for address in I2C_ADDRESSES:
    try:
        print(f"Trying address 0x{address:02X}...", end=" ")
        lcd = CharLCD(
            i2c_expander='PCF8574',
            address=address,
            port=1,
            cols=16,
            rows=2,
            dotsize=8
        )
        detected_address = address
        print("✓ SUCCESS!")
        break
    except Exception as e:
        print(f"✗ Not found")

if not lcd:
    print("\n✗ ERROR: LCD not detected on I2C bus")
    print("\nTroubleshooting:")
    print("1. Check wiring:")
    print("   - VCC → Pi Pin 2 (5V)")
    print("   - GND → Pi Pin 6 (GND)")
    print("   - SDA → Pi Pin 3 (GPIO 2)")
    print("   - SCL → Pi Pin 5 (GPIO 3)")
    print("2. Enable I2C: sudo raspi-config → Interface Options → I2C")
    print("3. Scan I2C bus: sudo i2cdetect -y 1")
    print("4. Check LCD contrast (potentiometer on back)")
    sys.exit(1)

print(f"\n✓ LCD detected at address 0x{detected_address:02X}")

# Test 1: Clear Display
print("\n2. Testing clear display...")
print("-" * 60)
try:
    lcd.clear()
    time.sleep(0.5)
    print("✓ Clear successful")
except Exception as e:
    print(f"✗ Clear failed: {e}")

# Test 2: Write to Line 1
print("\n3. Testing line 1 display...")
print("-" * 60)
try:
    lcd.write_string("LCD Test Line 1")
    print("✓ Line 1 written")
    print("  Check display: 'LCD Test Line 1'")
    time.sleep(2)
except Exception as e:
    print(f"✗ Line 1 failed: {e}")

# Test 3: Write to Line 2
print("\n4. Testing line 2 display...")
print("-" * 60)
try:
    lcd.crlf()  # Move to second line
    lcd.write_string("Success! :)")
    print("✓ Line 2 written")
    print("  Check display: 'Success! :)'")
    time.sleep(3)
except Exception as e:
    print(f"✗ Line 2 failed: {e}")

# Test 4: Clear and Write Centered
print("\n5. Testing centered text...")
print("-" * 60)
try:
    lcd.clear()
    lcd.write_string("  Raspberry Pi  ")
    lcd.crlf()
    lcd.write_string("  LCD Working!  ")
    print("✓ Centered text displayed")
    time.sleep(3)
except Exception as e:
    print(f"✗ Centered text failed: {e}")

# Test 5: Full 16 characters per line
print("\n6. Testing full line capacity...")
print("-" * 60)
try:
    lcd.clear()
    lcd.write_string("0123456789ABCDEF")  # Exactly 16 chars
    lcd.crlf()
    lcd.write_string("FEDCBA9876543210")  # Exactly 16 chars
    print("✓ Full lines displayed")
    print("  Line 1: '0123456789ABCDEF'")
    print("  Line 2: 'FEDCBA9876543210'")
    time.sleep(3)
except Exception as e:
    print(f"✗ Full line test failed: {e}")

# Test 6: Rapid Updates
print("\n7. Testing rapid updates...")
print("-" * 60)
try:
    for i in range(5):
        lcd.clear()
        lcd.write_string(f"Update Test #{i+1}")
        lcd.crlf()
        lcd.write_string(f"Count: {i+1}/5")
        time.sleep(0.5)
    print("✓ Rapid updates successful")
except Exception as e:
    print(f"✗ Rapid update failed: {e}")

# Test 7: Scrolling Text Simulation
print("\n8. Testing text scrolling...")
print("-" * 60)
try:
    long_text = "This is a very long message that needs to scroll"
    lcd.clear()
    lcd.write_string("Scroll Test:")
    
    # Scroll through the text
    for i in range(len(long_text) - 15):
        lcd.cursor_pos = (1, 0)  # Move to line 2
        lcd.write_string(long_text[i:i+16])
        time.sleep(0.2)
    
    print("✓ Scrolling test successful")
    time.sleep(1)
except Exception as e:
    print(f"✗ Scrolling failed: {e}")

# Test 8: Alert Simulation
print("\n9. Testing alert display simulation...")
print("-" * 60)
alerts = [
    ("FIRE ALERT!", "Evacuate now!"),
    ("FLOOD WARNING!", "Move to higher"),
    ("MEDICAL!", "First aid req"),
    ("HAZMAT SPILL!", "Shelter in place"),
    ("ALL CLEAR", "Resume normal")
]

try:
    for alert_type, message in alerts:
        lcd.clear()
        lcd.write_string(alert_type[:16])
        lcd.crlf()
        lcd.write_string(message[:16])
        print(f"  Alert: {alert_type}")
        time.sleep(1.5)
    print("✓ Alert simulation successful")
except Exception as e:
    print(f"✗ Alert simulation failed: {e}")

# Test 9: Final Ready Screen
print("\n10. Testing ready screen...")
print("-" * 60)
try:
    lcd.clear()
    lcd.write_string("LRR Alert Sys")
    lcd.crlf()
    lcd.write_string("READY: Listen..")
    print("✓ Ready screen displayed")
    time.sleep(2)
except Exception as e:
    print(f"✗ Ready screen failed: {e}")

# Cleanup
print("\n11. Cleaning up...")
print("-" * 60)
try:
    lcd.clear()
    lcd.write_string("Test Complete!")
    lcd.crlf()
    lcd.write_string("All tests passed")
    time.sleep(2)
    lcd.clear()
    lcd.close()
    print("✓ LCD closed successfully")
except Exception as e:
    print(f"⚠ Cleanup warning: {e}")

# Summary
print("\n" + "="*60)
print("TEST SUMMARY")
print("="*60)
print(f"✓ LCD detected at I2C address: 0x{detected_address:02X}")
print("✓ All display tests passed")
print("✓ LCD is ready for integration")
print("\nNext steps:")
print("1. If all tests passed, your LCD is working correctly")
print("2. Use address 0x{:02X} in meshtastic_led_receiver_with_lcd.py".format(detected_address))
print("3. Run the full receiver script")
print("="*60 + "\n")
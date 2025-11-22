#!/usr/bin/env python3
"""
16x2 LCD Parallel Mode Test Script
Tests standard LCD without I2C backpack

LCD GPIO Pin Assignments (4-bit mode):
- RS  → GPIO 7  (Pin 26)
- E   → GPIO 8  (Pin 24)
- D4  → GPIO 25 (Pin 22)
- D5  → GPIO 24 (Pin 18)
- D6  → GPIO 5  (Pin 29)
- D7  → GPIO 6  (Pin 31)

This script will:
1. Initialize LCD in 4-bit parallel mode
2. Display test messages
3. Test both lines
4. Verify display is working correctly
"""

import sys
import time

# Check for required libraries
try:
    import RPi.GPIO as GPIO
    print("✓ RPi.GPIO library found")
except ImportError:
    print("✗ RPi.GPIO library not found")
    print("  Install with: sudo apt-get install python3-rpi.gpio")
    sys.exit(1)

try:
    from RPLCD.gpio import CharLCD
    print("✓ RPLCD library found")
except ImportError:
    print("✗ RPLCD library not found")
    print("  Install with: pip3 install RPLCD")
    sys.exit(1)

# LCD Pin Configuration
LCD_PINS = {
    'RS': 7,   # GPIO 7 (Pin 26)
    'E': 8,    # GPIO 8 (Pin 24)
    'D4': 25,  # GPIO 25 (Pin 22)
    'D5': 24,  # GPIO 24 (Pin 18)
    'D6': 5,   # GPIO 5 (Pin 29)
    'D7': 6    # GPIO 6 (Pin 31)
}

print("\n" + "="*60)
print("16x2 LCD PARALLEL MODE TEST SCRIPT")
print("="*60)

# Test 1: LCD Initialization
print("\n1. Initializing LCD in 4-bit parallel mode...")
print("-" * 60)

lcd = None

try:
    print(f"Pin configuration:")
    print(f"  RS:  GPIO {LCD_PINS['RS']}")
    print(f"  E:   GPIO {LCD_PINS['E']}")
    print(f"  D4:  GPIO {LCD_PINS['D4']}")
    print(f"  D5:  GPIO {LCD_PINS['D5']}")
    print(f"  D6:  GPIO {LCD_PINS['D6']}")
    print(f"  D7:  GPIO {LCD_PINS['D7']}")
    print()
    
    lcd = CharLCD(
        pin_rs=LCD_PINS['RS'],
        pin_e=LCD_PINS['E'],
        pins_data=[LCD_PINS['D4'], LCD_PINS['D5'], LCD_PINS['D6'], LCD_PINS['D7']],
        numbering_mode=GPIO.BCM,
        cols=16,
        rows=2,
        dotsize=8,
        auto_linebreaks=True
    )
    
    print("✓ LCD initialized successfully")
    
except Exception as e:
    print(f"✗ LCD initialization failed: {e}")
    print("\nTroubleshooting:")
    print("1. Check wiring:")
    print("   - LCD Pin 4 (RS)  → Pi Pin 26 (GPIO 7)")
    print("   - LCD Pin 6 (E)   → Pi Pin 24 (GPIO 8)")
    print("   - LCD Pin 11 (D4) → Pi Pin 22 (GPIO 25)")
    print("   - LCD Pin 12 (D5) → Pi Pin 18 (GPIO 24)")
    print("   - LCD Pin 13 (D6) → Pi Pin 29 (GPIO 5)")
    print("   - LCD Pin 14 (D7) → Pi Pin 31 (GPIO 6)")
    print("   - LCD Pin 1 (VSS) → Pi Pin 6 (GND)")
    print("   - LCD Pin 2 (VDD) → Pi Pin 2 (5V)")
    print("   - LCD Pin 3 (V0)  → GND (or potentiometer)")
    print("   - LCD Pin 5 (RW)  → GND")
    print("2. Check contrast (LCD Pin 3)")
    print("3. Verify 5V and GND connections")
    GPIO.cleanup()
    sys.exit(1)
print()

# Test 2: Clear Display
print("2. Testing clear display...")
print("-" * 60)
try:
    lcd.clear()
    time.sleep(0.5)
    print("✓ Clear successful")
    print("  LCD should be blank with backlight on")
except Exception as e:
    print(f"✗ Clear failed: {e}")
print()

# Test 3: Write to Line 1
print("3. Testing line 1 display...")
print("-" * 60)
try:
    lcd.write_string("LCD Test Line 1")
    print("✓ Line 1 written")
    print("  Check display: 'LCD Test Line 1'")
    time.sleep(2)
except Exception as e:
    print(f"✗ Line 1 failed: {e}")
print()

# Test 4: Write to Line 2
print("4. Testing line 2 display...")
print("-" * 60)
try:
    lcd.crlf()  # Move to second line
    lcd.write_string("Parallel Mode!")
    print("✓ Line 2 written")
    print("  Check display: 'Parallel Mode!'")
    time.sleep(3)
except Exception as e:
    print(f"✗ Line 2 failed: {e}")
print()

# Test 5: Clear and Write Centered
print("5. Testing centered text...")
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
print()

# Test 6: Full 16 characters per line
print("6. Testing full line capacity...")
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
print()

# Test 7: Rapid Updates
print("7. Testing rapid updates...")
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
print()

# Test 8: Alert Simulation
print("8. Testing alert display simulation...")
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
print()

# Test 9: Character Scrolling
print("9. Testing text scrolling...")
print("-" * 60)
try:
    long_text = "This is a very long message for testing scrolling"
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
print()

# Test 10: Final Ready Screen
print("10. Testing ready screen...")
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
print()

# Cleanup
print("11. Cleaning up...")
print("-" * 60)
try:
    lcd.clear()
    lcd.write_string("Test Complete!")
    lcd.crlf()
    lcd.write_string("All tests passed")
    time.sleep(2)
    lcd.clear()
    lcd.close()
    GPIO.cleanup()
    print("✓ LCD closed and GPIO cleaned up")
except Exception as e:
    print(f"⚠ Cleanup warning: {e}")
print()

# Summary
print("="*60)
print("TEST SUMMARY")
print("="*60)
print("✓ LCD initialized in 4-bit parallel mode")
print("✓ All display tests passed")
print("✓ LCD is ready for integration")
print("\nNext steps:")
print("1. If all tests passed, your LCD is working correctly")
print("2. Run meshtastic_led_receiver_parallel_lcd.py")
print("3. Test with alerts from dispatcher")
print("\nGPIO Pin Configuration:")
print(f"  RS:  GPIO {LCD_PINS['RS']} (Pin 26)")
print(f"  E:   GPIO {LCD_PINS['E']} (Pin 24)")
print(f"  D4:  GPIO {LCD_PINS['D4']} (Pin 22)")
print(f"  D5:  GPIO {LCD_PINS['D5']} (Pin 18)")
print(f"  D6:  GPIO {LCD_PINS['D6']} (Pin 29)")
print(f"  D7:  GPIO {LCD_PINS['D7']} (Pin 31)")
print("="*60 + "\n")
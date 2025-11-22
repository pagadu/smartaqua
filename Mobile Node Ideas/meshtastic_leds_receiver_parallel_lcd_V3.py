#!/usr/bin/env python3
"""
Meshtastic LED Alert Receiver with 16x2 LCD Display (Parallel Mode)
For Lower Russian River Communities Safety Alert System

ENHANCED VERSION 3.0 Features:
- Scrolling text display for long messages
- Continuous LED blinking until ALL CLEAR received
- Push button for acknowledgment broadcasts

Hardware Requirements:
- Raspberry Pi 3B+
- Heltec LoRa ESP32 V3 (Meshtastic firmware)
- 4x LEDs (Fire, Flood, Medical, Hazmat)
- 16x2 LCD (standard parallel interface)
- 1x Push button with 10K pull-up resistor
- Appropriate resistors and wiring

LCD GPIO Pin Assignments (4-bit mode):
- RS  → GPIO 7  (Pin 26)
- E   → GPIO 8  (Pin 24)
- D4  → GPIO 25 (Pin 22)
- D5  → GPIO 24 (Pin 18)
- D6  → GPIO 5  (Pin 29)
- D7  → GPIO 6  (Pin 31)

Push Button:
- Button → GPIO 26 (Pin 37) with 10K pull-up to 3.3V
- Other side → GND

Author: Huey
Date: November 2025
Version: 3.0 (Enhanced with scrolling, continuous blink, button)
"""

import time
import logging
import sys
import threading
from meshtastic.serial_interface import SerialInterface
import pubsub

# Silence Meshtastic library logging
logging.disable(logging.CRITICAL)

# --- Configuration ---
RECEIVER_COM_PORT = "/dev/ttyUSB0"  # Change to your receiver node's port

# LCD Configuration (Parallel Mode)
LCD_ENABLED = True      # Set to False to disable LCD if not connected

# LCD GPIO Pin Assignments (4-bit mode)
LCD_PINS = {
    'RS': 7,   # Register Select - GPIO 7 (Pin 26)
    'E': 8,    # Enable - GPIO 8 (Pin 24)
    'D4': 25,  # Data bit 4 - GPIO 25 (Pin 22)
    'D5': 24,  # Data bit 5 - GPIO 24 (Pin 18)
    'D6': 5,   # Data bit 6 - GPIO 5 (Pin 29)
    'D7': 6    # Data bit 7 - GPIO 6 (Pin 31)
}

# GPIO Configuration for LEDs
LED_PINS = {
    "D1": 17,   # Fire LED - GPIO 17 (Pin 11)
    "D2": 27,   # Flood LED - GPIO 27 (Pin 13)
    "D3": 22,   # Medical LED - GPIO 22 (Pin 15)
    "D4": 23    # Hazmat LED - GPIO 23 (Pin 16)
}

# Push Button Configuration
BUTTON_PIN = 26  # GPIO 26 (Pin 37) - with external 10K pull-up
BUTTON_DEBOUNCE_TIME = 300  # milliseconds

# Alert Configuration
SCROLL_SPEED = 0.3  # seconds between scroll steps
LED_BLINK_INTERVAL = 0.5  # seconds (ON/OFF cycle)

# --- Import Libraries ---
# GPIO Library
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
    print("✓ RPi.GPIO library loaded")
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠ RPi.GPIO not available - LED & LCD control disabled")

# LCD Library (Parallel mode uses RPLCD with gpio pins)
try:
    from RPLCD.gpio import CharLCD
    LCD_LIBRARY_AVAILABLE = True
    print("✓ RPLCD library loaded")
except ImportError:
    LCD_LIBRARY_AVAILABLE = False
    LCD_ENABLED = False
    print("⚠ RPLCD not available - LCD display disabled")
    print("  Install with: pip3 install RPLCD")

# --- Global Variables ---
lcd = None  # Will be initialized in main()
meshtastic_interface = None  # Will be initialized in main()
alert_active = False  # Tracks if alert is currently active
active_leds = []  # List of LEDs currently blinking
led_blink_threads = {}  # Dictionary of LED blink threads
blink_lock = threading.Lock()  # Thread lock for LED operations
last_alert_message = ""  # Store last received alert
node_name = "Unknown"  # Will be set from Meshtastic node info

# --- LED Blink Thread Class ---
class LEDBlinker(threading.Thread):
    """Thread to continuously blink an LED until stopped"""
    
    def __init__(self, led_name, pin, interval=0.5):
        super().__init__()
        self.led_name = led_name
        self.pin = pin
        self.interval = interval
        self.running = True
        self.daemon = True  # Thread dies when main program exits
    
    def stop(self):
        """Stop the blinking"""
        self.running = False
    
    def run(self):
        """Main blink loop"""
        if not GPIO_AVAILABLE:
            return
        
        try:
            while self.running:
                GPIO.output(self.pin, GPIO.HIGH)
                time.sleep(self.interval)
                if not self.running:
                    break
                GPIO.output(self.pin, GPIO.LOW)
                time.sleep(self.interval)
        except Exception as e:
            print(f"✗ LED blink error ({self.led_name}): {e}")
        finally:
            # Ensure LED is off when stopped
            try:
                GPIO.output(self.pin, GPIO.LOW)
            except:
                pass

# --- LCD Management Class (Parallel Mode) ---
class LCDDisplay:
    """Manages 16x2 LCD in 4-bit parallel mode with scrolling support"""
    
    def __init__(self, pins, enabled=True):
        self.enabled = enabled and LCD_LIBRARY_AVAILABLE and GPIO_AVAILABLE
        self.lcd = None
        self.current_message = ""
        self.scroll_thread = None
        self.stop_scroll = False
        
        if not self.enabled:
            print("LCD display disabled")
            return
        
        try:
            # Initialize LCD in 4-bit mode
            self.lcd = CharLCD(
                pin_rs=pins['RS'],
                pin_e=pins['E'],
                pins_data=[pins['D4'], pins['D5'], pins['D6'], pins['D7']],
                numbering_mode=GPIO.BCM,  # Use BCM GPIO numbering
                cols=16,
                rows=2,
                dotsize=8,
                charmap='A00',  # Character map for proper display
                auto_linebreaks=True
            )
            
            # Clear display
            self.lcd.clear()
            time.sleep(0.1)
            
            print(f"✓ LCD initialized in 4-bit parallel mode")
            print(f"  RS: GPIO {pins['RS']}, E: GPIO {pins['E']}")
            print(f"  D4-D7: GPIO {pins['D4']}, {pins['D5']}, {pins['D6']}, {pins['D7']}")
            
        except Exception as e:
            print(f"✗ LCD initialization failed: {e}")
            print(f"  Check wiring and GPIO pins")
            self.enabled = False
    
    def clear(self):
        """Clear the LCD display"""
        if not self.enabled or not self.lcd:
            return
        try:
            self.stop_scroll = True  # Stop any scrolling
            if self.scroll_thread and self.scroll_thread.is_alive():
                self.scroll_thread.join(timeout=1)
            self.lcd.clear()
        except Exception as e:
            print(f"LCD clear error: {e}")
    
    def write(self, line1, line2=""):
        """
        Write text to LCD (2 lines)
        Automatically truncates to 16 characters per line
        """
        if not self.enabled or not self.lcd:
            return
        
        try:
            self.stop_scroll = True  # Stop any scrolling
            if self.scroll_thread and self.scroll_thread.is_alive():
                self.scroll_thread.join(timeout=1)
            
            self.lcd.clear()
            
            # Line 1 (truncate to 16 chars)
            display_line1 = line1[:16] if len(line1) > 16 else line1
            self.lcd.write_string(display_line1)
            
            # Line 2 (truncate to 16 chars)
            if line2:
                self.lcd.crlf()  # Move to second line
                display_line2 = line2[:16] if len(line2) > 16 else line2
                self.lcd.write_string(display_line2)
            
            self.current_message = f"{line1}|{line2}"
            
        except Exception as e:
            print(f"LCD write error: {e}")
    
    def write_centered(self, line1, line2=""):
        """Write centered text to LCD"""
        if not self.enabled or not self.lcd:
            return
        
        # Center the text
        centered_line1 = line1.center(16)[:16]
        centered_line2 = line2.center(16)[:16] if line2 else ""
        
        self.write(centered_line1, centered_line2)
    
    def scroll_text(self, line1, line2="", duration=10):
        """
        Scroll long text on both lines for specified duration
        This runs in a separate thread
        """
        if not self.enabled or not self.lcd:
            return
        
        self.stop_scroll = False
        
        def scroll_worker():
            try:
                start_time = time.time()
                
                # Pad text for smooth scrolling
                padded_line1 = line1 + "    " if len(line1) > 16 else line1
                padded_line2 = line2 + "    " if len(line2) > 16 else line2
                
                line1_needs_scroll = len(line1) > 16
                line2_needs_scroll = len(line2) > 16
                
                if not line1_needs_scroll and not line2_needs_scroll:
                    # No scrolling needed, just display
                    self.write(line1, line2)
                    return
                
                scroll_pos = 0
                max_scroll1 = max(0, len(padded_line1) - 16)
                max_scroll2 = max(0, len(padded_line2) - 16)
                max_scroll = max(max_scroll1, max_scroll2)
                
                while not self.stop_scroll and (time.time() - start_time) < duration:
                    self.lcd.home()
                    
                    # Display line 1
                    if line1_needs_scroll:
                        pos1 = scroll_pos % (max_scroll1 + 1) if max_scroll1 > 0 else 0
                        display1 = padded_line1[pos1:pos1+16]
                    else:
                        display1 = line1.ljust(16)[:16]
                    
                    self.lcd.write_string(display1)
                    
                    # Display line 2
                    self.lcd.crlf()
                    if line2_needs_scroll:
                        pos2 = scroll_pos % (max_scroll2 + 1) if max_scroll2 > 0 else 0
                        display2 = padded_line2[pos2:pos2+16]
                    else:
                        display2 = line2.ljust(16)[:16]
                    
                    self.lcd.write_string(display2)
                    
                    scroll_pos += 1
                    if scroll_pos > max_scroll + 4:  # Add pause at end
                        scroll_pos = 0
                    
                    time.sleep(SCROLL_SPEED)
                
            except Exception as e:
                print(f"LCD scroll error: {e}")
        
        # Stop any existing scroll thread
        self.stop_scroll = True
        if self.scroll_thread and self.scroll_thread.is_alive():
            self.scroll_thread.join(timeout=1)
        
        # Start new scroll thread
        self.scroll_thread = threading.Thread(target=scroll_worker, daemon=True)
        self.scroll_thread.start()
    
    def show_startup(self):
        """Display startup message"""
        self.write_centered("ALERT RECEIVER", "Initializing...")
    
    def show_ready(self):
        """Display ready status"""
        self.write("LRR Alert Sys", "READY: Listen..")
    
    def show_alert(self, alert_type, full_message, scroll=True):
        """
        Display alert on LCD with scrolling
        Line 1: Alert type
        Line 2: Full message (scrolls if long)
        """
        # Alert type formatting
        alert_displays = {
            "FIRE": "🔥 FIRE ALERT!",
            "FLOOD": "🌊 FLOOD WARN!",
            "MEDICAL": "⚕ MEDICAL!",
            "HAZMAT": "☢ HAZMAT!",
            "ALL CLEAR": "✓ ALL CLEAR"
        }
        
        line1 = alert_displays.get(alert_type, f"{alert_type}!")
        
        # Extract key message details for line 2
        message_preview = full_message
        if "DETAILS:" in full_message:
            try:
                details = full_message.split("DETAILS:")[1].split("|")[0].strip()
                message_preview = details
            except:
                pass
        
        if scroll and len(message_preview) > 16:
            # Start scrolling for long messages
            self.scroll_text(line1, message_preview, duration=30)
        else:
            # Static display for short messages
            self.write(line1, message_preview[:16])
    
    def show_error(self, error_msg):
        """Display error message"""
        self.write("ERROR:", error_msg[:16])
    
    def show_button_press(self):
        """Display button acknowledgment"""
        self.write("Sending ACK...", "Please wait...")
    
    def close(self):
        """Clean up LCD"""
        self.stop_scroll = True
        if self.scroll_thread and self.scroll_thread.is_alive():
            self.scroll_thread.join(timeout=1)
        
        if self.enabled and self.lcd:
            try:
                self.lcd.clear()
                self.lcd.close()
            except:
                pass

# --- GPIO Setup ---
def setup_gpio():
    """Initialize GPIO pins for LED control and button"""
    if not GPIO_AVAILABLE:
        print("⚠ Skipping GPIO initialization")
        return
    
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup LED pins
        for led_name, pin in LED_PINS.items():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
        
        print(f"✓ LED GPIO initialized: {LED_PINS}")
        
        # Setup button pin (with internal pull-up as backup)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        print(f"✓ Button GPIO initialized: Pin {BUTTON_PIN}")
        
        # Quick test flash
        for pin in LED_PINS.values():
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(0.05)
            GPIO.output(pin, GPIO.LOW)
        
        print("  ✓ LED test complete")
        
    except Exception as e:
        print(f"✗ GPIO setup error: {e}")

# --- LED Control Functions ---
def start_led_blink(led_name):
    """Start continuous blinking for a specific LED"""
    global led_blink_threads, active_leds
    
    if not GPIO_AVAILABLE:
        print(f"[SIM] {led_name} → BLINK CONTINUOUS")
        return
    
    if led_name not in LED_PINS:
        print(f"✗ Unknown LED: {led_name}")
        return
    
    with blink_lock:
        # Stop existing blink for this LED if any
        if led_name in led_blink_threads:
            led_blink_threads[led_name].stop()
            led_blink_threads[led_name].join(timeout=1)
        
        # Start new blink thread
        pin = LED_PINS[led_name]
        blinker = LEDBlinker(led_name, pin, LED_BLINK_INTERVAL)
        blinker.start()
        led_blink_threads[led_name] = blinker
        
        if led_name not in active_leds:
            active_leds.append(led_name)
        
        print(f"✓ {led_name} (GPIO {pin}): BLINKING CONTINUOUSLY")

def stop_led_blink(led_name):
    """Stop blinking for a specific LED"""
    global led_blink_threads, active_leds
    
    if not GPIO_AVAILABLE:
        print(f"[SIM] {led_name} → STOP")
        return
    
    with blink_lock:
        if led_name in led_blink_threads:
            led_blink_threads[led_name].stop()
            led_blink_threads[led_name].join(timeout=1)
            del led_blink_threads[led_name]
            
            # Turn off LED
            if led_name in LED_PINS:
                GPIO.output(LED_PINS[led_name], GPIO.LOW)
            
            if led_name in active_leds:
                active_leds.remove(led_name)
            
            print(f"✓ {led_name}: STOPPED")

def stop_all_leds():
    """Stop all LED blinking"""
    global led_blink_threads, active_leds, alert_active
    
    print("\n🔕 Stopping all LED alerts...")
    
    with blink_lock:
        # Stop all blink threads
        for led_name in list(led_blink_threads.keys()):
            led_blink_threads[led_name].stop()
            led_blink_threads[led_name].join(timeout=1)
        
        led_blink_threads.clear()
        active_leds.clear()
        alert_active = False
        
        # Turn off all LEDs
        if GPIO_AVAILABLE:
            for pin in LED_PINS.values():
                GPIO.output(pin, GPIO.LOW)
    
    print("✓ All LEDs stopped")

# --- Message Parser ---
def parse_led_command(message_text):
    """
    Extract LED command from message text
    Format: ||LED:D1:BLINK:250
    """
    if "||LED:" not in message_text:
        return None
    
    try:
        led_section = message_text.split("||LED:")[1]
        led_command = led_section.split()[0] if led_section else led_section.strip()
        parts = led_command.split(":")
        
        if len(parts) >= 2:
            led_name = parts[0].upper()
            action = parts[1].upper()
            interval = parts[2] if len(parts) > 2 else None
            return (led_name, action, interval)
            
    except Exception as e:
        print(f"✗ LED command parse error: {e}")
    
    return None

def extract_alert_info(message_text):
    """
    Extract alert type and full message for display
    
    Returns:
        tuple: (alert_type, full_message)
    """
    alert_type = "ALERT"
    
    # Try to identify alert type from message
    message_upper = message_text.upper()
    
    if "ALL CLEAR" in message_upper or "ALLCLEAR" in message_upper:
        alert_type = "ALL CLEAR"
    elif "FIRE" in message_upper:
        alert_type = "FIRE"
    elif "FLOOD" in message_upper:
        alert_type = "FLOOD"
    elif "MEDICAL" in message_upper:
        alert_type = "MEDICAL"
    elif "HAZMAT" in message_upper:
        alert_type = "HAZMAT"
    
    return (alert_type, message_text)

# --- Button Handler ---
def button_callback(channel):
    """Handle button press - send acknowledgment message"""
    global meshtastic_interface, node_name, last_alert_message
    
    timestamp = time.strftime("%H:%M:%S")
    print(f"\n{'='*70}")
    print(f"[{timestamp}] 🔘 BUTTON PRESSED!")
    print(f"{'='*70}")
    
    if lcd:
        lcd.show_button_press()
    
    try:
        if meshtastic_interface:
            # Create acknowledgment message
            if last_alert_message:
                ack_message = f"✓ ACK from {node_name}: Last message received and acknowledged"
            else:
                ack_message = f"✓ Status check from {node_name}: Everything OK here!"
            
            print(f"Broadcasting: {ack_message}")
            meshtastic_interface.sendText(ack_message, channelIndex=0)
            print("✓ Acknowledgment sent!")
            
            time.sleep(2)
            
            # Return to current display state
            if alert_active:
                alert_type, full_msg = extract_alert_info(last_alert_message)
                lcd.show_alert(alert_type, full_msg, scroll=True)
            else:
                lcd.show_ready()
        else:
            print("✗ Cannot send - Meshtastic interface not connected")
            
    except Exception as e:
        print(f"✗ Button handler error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"{'='*70}\n")

# --- Meshtastic Message Handler ---
def on_receive(packet, interface):
    """
    Callback function for received messages
    """
    global lcd, alert_active, last_alert_message
    
    try:
        # Only process text messages
        if 'decoded' not in packet:
            return
        
        decoded = packet['decoded']
        
        # Check if this is a TELEMETRY_APP packet (ignore it)
        if decoded.get('portnum') == 'TELEMETRY_APP':
            return
        
        # Check if this is a text message
        if 'text' not in decoded:
            return
        
        message_text = decoded['text']
        sender_id = packet.get('fromId', 'Unknown')
        sender_num = packet.get('from', 'Unknown')
        timestamp = time.strftime("%H:%M:%S")
        
        print(f"\n{'='*70}")
        print(f"[{timestamp}] 📨 MESSAGE RECEIVED")
        print(f"{'='*70}")
        print(f"From: {sender_id} ({sender_num})")
        print(f"Message: {message_text[:100]}{'...' if len(message_text) > 100 else ''}")
        
        # Extract alert information
        alert_type, full_message = extract_alert_info(message_text)
        
        # Check if this is an ALL CLEAR message
        if alert_type == "ALL CLEAR":
            print("\n✓ ALL CLEAR received - stopping all alerts")
            stop_all_leds()
            alert_active = False
            last_alert_message = ""
            
            # Update LCD
            lcd.show_alert(alert_type, full_message, scroll=False)
            
            # Return to ready after 5 seconds
            time.sleep(5)
            lcd.show_ready()
            
        else:
            # This is an alert - store it and activate
            last_alert_message = message_text
            alert_active = True
            
            # Update LCD with scrolling for long messages
            lcd.show_alert(alert_type, full_message, scroll=True)
            
            # Parse LED command
            led_command = parse_led_command(message_text)
            
            if led_command:
                led_name, action, interval = led_command
                print(f"\n🚨 LED COMMAND DETECTED:")
                print(f"   Target: {led_name}")
                print(f"   Action: {action}")
                if interval:
                    print(f"   Interval: {interval}ms (continuous mode)")
                
                # Start continuous blinking
                if action == "BLINK":
                    start_led_blink(led_name)
                elif action == "ON":
                    # For "ON" command, also do continuous blink
                    start_led_blink(led_name)
            else:
                print("   (No LED command in message)")
        
        print(f"{'='*70}\n")
                
    except Exception as e:
        print(f"✗ Error processing message: {e}")
        import traceback
        traceback.print_exc()

# --- Main Program ---
def main():
    """Main program entry point"""
    global lcd, meshtastic_interface, node_name
    
    print("\n" + "="*70)
    print("🚨 MESHTASTIC LED ALERT RECEIVER WITH LCD (ENHANCED) 🚨")
    print("Lower Russian River Communities Safety Alert System")
    print("="*70)
    print(f"Version: 3.0 (Scrolling, Continuous Blink, Button ACK)")
    print(f"Date: November 2025")
    print(f"Author: Huey")
    print("="*70 + "\n")
    
    # Initialize LCD
    print("🖥️  Initializing LCD display (4-bit parallel mode)...")
    lcd = LCDDisplay(pins=LCD_PINS, enabled=LCD_ENABLED)
    lcd.show_startup()
    time.sleep(2)
    
    # Setup GPIO for LEDs and button
    print("\n🔌 Initializing GPIO...")
    setup_gpio()
    
    # Setup button interrupt
    if GPIO_AVAILABLE:
        try:
            GPIO.add_event_detect(
                BUTTON_PIN, 
                GPIO.FALLING,  # Trigger on button press (HIGH to LOW)
                callback=button_callback,
                bouncetime=BUTTON_DEBOUNCE_TIME
            )
            print(f"✓ Button interrupt configured on GPIO {BUTTON_PIN}")
        except Exception as e:
            print(f"⚠ Button setup warning: {e}")
    
    # Connect to Meshtastic
    print(f"\n📡 Connecting to Meshtastic receiver node...")
    print(f"   Port: {RECEIVER_COM_PORT}")
    
    try:
        # Initialize serial connection
        meshtastic_interface = SerialInterface(devPath=RECEIVER_COM_PORT)
        print("✓ Connected successfully!")
        
        # Get node info
        time.sleep(2)
        try:
            node_info = meshtastic_interface.myInfo
            if node_info and 'user' in node_info:
                node_name = node_info['user'].get('longName', 'Unknown Node')
                print(f"✓ Node name: {node_name}")
        except:
            node_name = "LRR Receiver"
        
        lcd.write("Connected!", f"Node: {node_name[:16]}")
        
        time.sleep(2)
        print(f"✓ Node ready")
        
        # Subscribe to message events
        pubsub.pub.subscribe(on_receive, "meshtastic.receive")
        print("✓ Message handler registered")
        
        # Show ready status
        lcd.show_ready()
        
        print("\n" + "="*70)
        print("👂 LISTENING FOR EMERGENCY ALERTS...")
        print("="*70)
        print("LCD Display: ENABLED (Parallel mode)" if lcd.enabled else "LCD Display: DISABLED")
        print("LED Control: ENABLED (Continuous blink until ALL CLEAR)" if GPIO_AVAILABLE else "LED Control: DISABLED")
        print(f"Button ACK: ENABLED on GPIO {BUTTON_PIN}" if GPIO_AVAILABLE else "Button ACK: DISABLED")
        print("\nFeatures:")
        print("  • Long messages scroll automatically")
        print("  • LEDs blink continuously until ALL CLEAR")
        print("  • Press button to send acknowledgment")
        print("\nPress Ctrl+C to exit\n")
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹ Shutdown initiated by user...")
        stop_all_leds()
        lcd.write("Shutting down", "Goodbye!")
        time.sleep(1)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        lcd.show_error("Connection fail")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        
        # Stop all LEDs
        stop_all_leds()
        
        if GPIO_AVAILABLE:
            try:
                GPIO.cleanup()
                print("✓ GPIO cleaned up")
            except:
                pass
        
        if meshtastic_interface:
            try:
                meshtastic_interface.close()
                print("✓ Meshtastic interface closed")
            except:
                pass
        
        # Clear and close LCD
        if lcd:
            lcd.clear()
            lcd.close()
            print("✓ LCD display closed")
        
        print("✓ Shutdown complete")
        print("="*70 + "\n")

if __name__ == "__main__":
    main()
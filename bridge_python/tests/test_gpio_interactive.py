#!/usr/bin/env python3
"""
GPIO Interactive Test Suite - Full hardware testing
Tests LEDs, buttons, and switches with interactive diagnostics
"""

import sys
import time
from pathlib import Path
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (
    LED_ROUGES_PINS, LED_VERTES_PINS,
    LEVIERS_PINS, BOUTONS_PINS,
    RASPI_IP, print_config_summary
)


class GPIOTester:
    """Interactive GPIO testing suite"""
    
    def __init__(self, use_remote: bool = False):
        """Initialize GPIO tester
        
        Args:
            use_remote: Use remote pigpio or local GPIO
        """
        self.use_remote = use_remote
        self.gpio = None
        self.results = {
            "leds_rouges": {},
            "leds_vertes": {},
            "leviers": {},
            "boutons": {}
        }
        
        self._initialize_gpio()
    
    def _initialize_gpio(self):
        """Initialize GPIO manager"""
        try:
            from gpio_handler import GPIOHandler
            self.gpio = GPIOHandler(krpc=None, pico=None, config=None, use_remote=self.use_remote)
            if self.gpio.connected:
                print("✓ GPIO initialized")
            else:
                print("✗ GPIO not connected")
        except Exception as e:
            print(f"✗ Error initializing GPIO: {e}")
            self.gpio = None
    
    def print_header(self, title: str):
        """Print test section header"""
        print("\n" + "="*60)
        print(f"🧪 {title}")
        print("="*60)
    
    def print_result(self, status: str, message: str):
        """Print test result"""
        if status == "pass":
            print(f"  ✓ {message}")
        elif status == "fail":
            print(f"  ✗ {message}")
        elif status == "warn":
            print(f"  ⚠ {message}")
        elif status == "info":
            print(f"  ℹ {message}")
    
    def test_led_rouges(self):
        """Test red LEDs"""
        self.print_header("RED LEDs Test")
        
        if not self.gpio or not self.gpio.led_rouges:
            self.print_result("fail", "No red LEDs initialized")
            return False
        
        print(f"\nFound {len(self.gpio.led_rouges)} red LEDs: {list(self.gpio.led_rouges.keys())}")
        print("\nTesting each LED (5 seconds ON, 2 seconds OFF)...\n")
        
        success_count = 0
        for i, (pin, led) in enumerate(self.gpio.led_rouges.items()):
            try:
                # Turn ON
                led.on()
                print(f"  [{i+1}] GPIO {pin} → ON", end="")
                sys.stdout.flush()
                time.sleep(5)
                
                # Turn OFF
                led.off()
                print(f" → OFF ✓")
                self.results["leds_rouges"][pin] = "OK"
                success_count += 1
                
            except Exception as e:
                print(f" → ERROR: {e}")
                self.results["leds_rouges"][pin] = f"ERROR: {e}"
        
        print()
        result = success_count == len(self.gpio.led_rouges)
        self.print_result("pass" if result else "fail",
                         f"{success_count}/{len(self.gpio.led_rouges)} red LEDs working")
        
        return result
    
    def test_led_vertes(self):
        """Test green LEDs"""
        self.print_header("GREEN LEDs Test")
        
        if not self.gpio or not self.gpio.led_vertes:
            self.print_result("fail", "No green LEDs initialized")
            return False
        
        print(f"\nFound {len(self.gpio.led_vertes)} green LEDs: {list(self.gpio.led_vertes.keys())}")
        print("\nTesting each LED (5 seconds ON, 2 seconds OFF)...\n")
        
        success_count = 0
        for i, (pin, led) in enumerate(self.gpio.led_vertes.items()):
            try:
                # Turn ON
                led.on()
                print(f"  [{i+1}] GPIO {pin} → ON", end="")
                sys.stdout.flush()
                time.sleep(5)
                
                # Turn OFF
                led.off()
                print(f" → OFF ✓")
                self.results["leds_vertes"][pin] = "OK"
                success_count += 1
                
            except Exception as e:
                print(f" → ERROR: {e}")
                self.results["leds_vertes"][pin] = f"ERROR: {e}"
        
        print()
        result = success_count == len(self.gpio.led_vertes)
        self.print_result("pass" if result else "fail",
                         f"{success_count}/{len(self.gpio.led_vertes)} green LEDs working")
        
        return result
    
    def test_leviers(self):
        """Test lever switches"""
        self.print_header("LEVER SWITCHES Test")
        
        if not self.gpio or not self.gpio.leviers:
            self.print_result("warn", "No levier switches initialized")
            return False
        
        print(f"\nFound {len(self.gpio.leviers)} levier switches:")
        for pin, action in LEVIERS_PINS.items():
            print(f"  - GPIO {pin}: {action}")
        
        print("\n⏱ Monitoring levier states for 20 seconds...")
        print("(Move switches to test)\n")
        
        start_time = time.time()
        detected_changes = {pin: False for pin in self.gpio.leviers.keys()}
        previous_states = {pin: btn.is_pressed for pin, btn in self.gpio.leviers.items()}
        
        try:
            while time.time() - start_time < 20:
                for pin, btn in self.gpio.leviers.items():
                    current_state = btn.is_pressed
                    if current_state != previous_states[pin]:
                        action = LEVIERS_PINS.get(pin, "UNKNOWN")
                        state_text = "PRESSED" if current_state else "RELEASED"
                        print(f"  ✓ GPIO {pin} ({action}): {state_text}")
                        detected_changes[pin] = True
                        previous_states[pin] = current_state
                        self.results["leviers"][pin] = "OK"
                
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n(Test interrupted)")
        
        print()
        detected_count = sum(1 for v in detected_changes.values() if v)
        total = len(self.gpio.leviers)
        
        result = detected_count > 0  # At least one switch detected
        status = "pass" if detected_count == total else "warn" if detected_count > 0 else "fail"
        self.print_result(status, f"{detected_count}/{total} levier changes detected")
        
        return result
    
    def test_boutons(self):
        """Test momentary buttons"""
        self.print_header("MOMENTARY BUTTONS Test")
        
        if not self.gpio or not self.gpio.boutons:
            self.print_result("warn", "No buttons initialized")
            return False
        
        print(f"\nFound {len(self.gpio.boutons)} momentary buttons:")
        for pin, action in BOUTONS_PINS.items():
            print(f"  - GPIO {pin}: {action}")
        
        print("\n⏱ Monitoring button presses for 30 seconds...")
        print("(Press buttons to test)\n")
        
        start_time = time.time()
        detected_presses = {pin: 0 for pin in self.gpio.boutons.keys()}
        previous_states = {pin: btn.is_pressed for pin, btn in self.gpio.boutons.items()}
        
        try:
            while time.time() - start_time < 30:
                for pin, btn in self.gpio.boutons.items():
                    current_state = btn.is_pressed
                    
                    # Detect press (transition from released to pressed)
                    if current_state and not previous_states[pin]:
                        action = BOUTONS_PINS.get(pin, "UNKNOWN")
                        print(f"  ✓ GPIO {pin} ({action}): PRESSED")
                        detected_presses[pin] += 1
                        self.results["boutons"][pin] = "OK"
                    
                    previous_states[pin] = current_state
                
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("\n(Test interrupted)")
        
        print()
        detected_buttons = sum(1 for v in detected_presses.values() if v > 0)
        total = len(self.gpio.boutons)
        total_presses = sum(detected_presses.values())
        
        result = detected_buttons > 0
        status = "pass" if detected_buttons == total else "warn" if detected_buttons > 0 else "fail"
        self.print_result(status, f"{detected_buttons}/{total} buttons detected ({total_presses} presses total)")
        
        return result
    
    def test_all_leds_on_then_off(self):
        """Test all LEDs together"""
        self.print_header("ALL LEDs Sequence Test")
        
        if not self.gpio or not (self.gpio.led_rouges or self.gpio.led_vertes):
            self.print_result("warn", "No LEDs available")
            return
        
        print("\nTurning all LEDs ON for 3 seconds...")
        try:
            for led in self.gpio.led_rouges.values():
                led.on()
            for led in self.gpio.led_vertes.values():
                led.on()
            time.sleep(3)
            
            print("Turning all LEDs OFF...")
            for led in self.gpio.led_rouges.values():
                led.off()
            for led in self.gpio.led_vertes.values():
                led.off()
            
            self.print_result("pass", "All LEDs sequence completed")
        except Exception as e:
            self.print_result("fail", f"Error in LED sequence: {e}")
    
    def print_summary(self):
        """Print test summary"""
        self.print_header("TEST SUMMARY")
        
        total_tests = 0
        total_passed = 0
        
        # LED Results
        if self.results["leds_rouges"]:
            passed = sum(1 for v in self.results["leds_rouges"].values() if v == "OK")
            total = len(self.results["leds_rouges"])
            total_tests += total
            total_passed += passed
            status = "✓" if passed == total else "⚠"
            print(f"{status} Red LEDs: {passed}/{total} working")
        
        if self.results["leds_vertes"]:
            passed = sum(1 for v in self.results["leds_vertes"].values() if v == "OK")
            total = len(self.results["leds_vertes"])
            total_tests += total
            total_passed += passed
            status = "✓" if passed == total else "⚠"
            print(f"{status} Green LEDs: {passed}/{total} working")
        
        if self.results["leviers"]:
            passed = sum(1 for v in self.results["leviers"].values() if v == "OK")
            total = len(self.results["leviers"])
            if passed > 0:
                print(f"✓ Levier Switches: {passed}/{total} detected")
        
        if self.results["boutons"]:
            passed = sum(1 for v in self.results["boutons"].values() if v == "OK")
            total = len(self.results["boutons"])
            if passed > 0:
                print(f"✓ Buttons: {passed}/{total} detected")
        
        print("\n" + "="*60)
        if total_passed == total_tests and total_tests > 0:
            print("✅ ALL TESTS PASSED")
        elif total_passed > 0:
            print(f"⚠ PARTIAL SUCCESS: {total_passed}/{total_tests} components working")
        else:
            print("❌ NO TESTS PASSED - Check hardware connections")
        print("="*60 + "\n")
    
    def cleanup(self):
        """Cleanup GPIO"""
        if self.gpio:
            self.gpio.cleanup()
            print("✓ GPIO cleaned up")


def main():
    """Main test runner"""
    print("\n" + "="*60)
    print("🔧 GPIO INTERACTIVE TEST SUITE")
    print("="*60 + "\n")
    
    # Show configuration
    print_config_summary()
    
    # Ask about remote GPIO
    print("\nTest Configuration:")
    print("  Local GPIO: Use Raspberry Pi's built-in GPIO (if running on Raspi)")
    print("  Remote GPIO: Use pigpio for remote connection")
    
    use_remote = False
    response = input("\nUse REMOTE GPIO via pigpio? (y/N): ").strip().lower()
    if response == 'y':
        use_remote = True
        print(f"✓ Using remote GPIO on {RASPI_IP}")
    else:
        print("✓ Using LOCAL GPIO")
    
    print()
    
    # Create tester
    tester = GPIOTester(use_remote=use_remote)
    
    if not tester.gpio or not tester.gpio.connected:
        print("✗ GPIO not connected. Aborting tests.")
        return 1
    
    # Run tests
    try:
        print("\n" + "="*60)
        response = input("Press Enter to start tests...")
        print()
        
        # Red LEDs
        tester.test_led_rouges()
        time.sleep(2)
        
        # Green LEDs
        tester.test_led_vertes()
        time.sleep(2)
        
        # All LEDs sequence
        tester.test_all_leds_on_then_off()
        time.sleep(2)
        
        # Leviers
        tester.test_leviers()
        time.sleep(1)
        
        # Buttons
        tester.test_boutons()
        
        # Summary
        tester.print_summary()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠ Tests interrupted by user")
        tester.cleanup()
        return 1
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        tester.cleanup()
        return 1
    finally:
        tester.cleanup()


if __name__ == "__main__":
    sys.exit(main())

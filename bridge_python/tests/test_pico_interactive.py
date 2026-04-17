#!/usr/bin/env python3
"""
Pico ADC Interactive Test Suite
Tests Pico connection and ADC channels with live data
"""

import sys
import time
from pathlib import Path
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import PICO_PORT, THROTTLE_SMOOTHING_WINDOW, print_config_summary


class PicoTester:
    """Interactive Pico ADC testing suite"""
    
    def __init__(self):
        """Initialize Pico tester"""
        self.pico = None
        self.results = {}
        self._initialize_pico()
    
    def _initialize_pico(self):
        """Initialize Pico manager"""
        try:
            from pico_handler import PicoHandler
            self.pico = PicoHandler(port=PICO_PORT)
            if self.pico.connected:
                print("✓ Pico initialized")
            else:
                print("⚠ Pico not connected - check USB connection")
        except ImportError:
            print("✗ PicoHandler module not available")
        except Exception as e:
            print(f"✗ Error initializing Pico: {e}")
    
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
    
    def test_connection(self):
        """Test Pico connection"""
        self.print_header("PICO CONNECTION Test")
        
        if not self.pico:
            self.print_result("fail", "PicoManager not initialized")
            return False
        
        print(f"\nConnection details:")
        print(f"  Port: {self.pico.port}")
        print(f"  Connected: {self.pico.connected}")
        print(f"  Errors: {self.pico.error_count}")
        
        if self.pico.connected:
            self.print_result("pass", "Pico is connected")
            return True
        else:
            self.print_result("fail", "Pico not connected")
            print("\nTroubleshooting:")
            print("  1. Check USB cable is connected")
            print("  2. Verify Pico has picod firmware: ls /dev/ttyACM*")
            print("  3. Check permissions: sudo usermod -a -G dialout $USER")
            return False
    
    def test_adc_channels(self, duration: int = 15):
        """Test ADC channels with live data"""
        self.print_header("ADC CHANNELS Test")
        
        if not self.pico or not self.pico.connected:
            self.print_result("fail", "Pico not connected")
            return False
        
        print(f"\nReading ADC channels for {duration} seconds...")
        print("(Rotate potentiometer to see values change)\n")
        
        # Print header
        print("Time".ljust(8), end="")
        for i in range(4):
            print(f" │ CH{i}(Raw)".ljust(12), end="")
        print("\n" + "-"*60)
        
        start_time = time.time()
        min_values = {i: 4095 for i in range(4)}
        max_values = {i: 0 for i in range(4)}
        read_count = {i: 0 for i in range(4)}
        
        try:
            while time.time() - start_time < duration:
                elapsed = int(time.time() - start_time)
                print(f"{elapsed:2d}s     ", end="")
                
                for channel in range(4):
                    raw_val = self.pico.read_adc_raw(channel)
                    
                    if raw_val is not None:
                        min_values[channel] = min(min_values[channel], raw_val)
                        max_values[channel] = max(max_values[channel], raw_val)
                        read_count[channel] += 1
                        
                        # Normalize for display
                        bar_length = int((raw_val / 4095) * 10)
                        bar = "█" * bar_length + "░" * (10 - bar_length)
                        
                        print(f" │ {raw_val:4d} {bar}", end="")
                    else:
                        print(f" │ {'ERR':4s} {'?'*10}", end="")
                
                print()
                time.sleep(0.5)
        
        except KeyboardInterrupt:
            print("\n(Test interrupted)")
        
        # Print statistics
        print("-"*60)
        print("\nStatistics:")
        
        for channel in range(4):
            if read_count[channel] > 0:
                print(f"\nChannel {channel}:")
                print(f"  Reads: {read_count[channel]}")
                print(f"  Min: {min_values[channel]}")
                print(f"  Max: {max_values[channel]}")
                print(f"  Range: {max_values[channel] - min_values[channel]}")
                
                if max_values[channel] - min_values[channel] > 100:
                    self.print_result("pass", f"Channel {channel}: data is changing")
                else:
                    self.print_result("warn", f"Channel {channel}: values not changing much")
            else:
                self.print_result("fail", f"Channel {channel}: no data read")
        
        return any(read_count[i] > 0 for i in range(4))
    
    def test_smoothing(self, duration: int = 10):
        """Test ADC smoothing (moving average)"""
        self.print_header("ADC SMOOTHING Test")
        
        if not self.pico or not self.pico.connected:
            self.print_result("fail", "Pico not connected")
            return
        
        print(f"\nComparing RAW vs SMOOTHED values (Channel 0)")
        print(f"Smoothing window: {THROTTLE_SMOOTHING_WINDOW} samples\n")
        
        print("Time".ljust(8), "Raw".ljust(8), "Smoothed".ljust(12), "Difference".ljust(12))
        print("-"*50)
        
        start_time = time.time()
        previous_raw = None
        
        try:
            while time.time() - start_time < duration:
                raw = self.pico.read_adc_raw(0)
                smoothed = self.pico.read_adc_smoothed(0)
                
                if raw is not None and smoothed is not None:
                    elapsed = f"{time.time() - start_time:.1f}s"
                    diff = abs(raw - smoothed)
                    
                    # Show change indicator
                    if previous_raw is not None:
                        change = "↑" if raw > previous_raw else "↓" if raw < previous_raw else "="
                    else:
                        change = " "
                    
                    print(f"{elapsed.ljust(8)}{change}{raw:<7} {smoothed:<11.1f} {diff:<11.1f}")
                    previous_raw = raw
                
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            print("\n(Test interrupted)")
        
        self.print_result("pass", "Smoothing test completed")
    
    def test_throttle_conversion(self):
        """Test throttle conversion (0-4095 to 0.0-1.0)"""
        self.print_header("THROTTLE CONVERSION Test")
        
        if not self.pico or not self.pico.connected:
            self.print_result("fail", "Pico not connected")
            return
        
        print("\nReading throttle potentiometer...")
        print("(Channel 0 is throttle)\n")
        
        print("Raw(0-4095)".ljust(15), "Normalized(0-1)".ljust(18), "Percent(0-100%)".ljust(20))
        print("-"*55)
        
        for i in range(10):
            raw = self.pico.read_adc_raw(0)
            normalized = self.pico.read_adc_normalized(0, smoothed=False)
            percent = self.pico.read_adc_percent(0, smoothed=False)
            
            if raw is not None:
                bar_length = int((normalized or 0) * 20)
                bar = "█" * bar_length + "░" * (20 - bar_length)
                
                print(
                    f"{raw:<14} "
                    f"{normalized:<17.4f} "
                    f"{(percent or 0):<6.1f}% {bar}"
                )
            
            time.sleep(0.2)
        
        self.print_result("pass", "Throttle conversion working")
    
    def print_summary(self):
        """Print test summary"""
        self.print_header("TEST SUMMARY")
        
        if not self.pico:
            self.print_result("fail", "Pico not initialized")
            return
        
        if self.pico.connected:
            self.print_result("pass", "Pico connection successful")
            self.print_result("info", f"Port: {self.pico.port}")
            self.print_result("info", f"Errors: {self.pico.error_count}")
        else:
            self.print_result("fail", "Pico connection failed")
            self.print_result("info", "Check USB cable and permissions")
        
        print()
    
    def cleanup(self):
        """Cleanup Pico"""
        if self.pico:
            self.pico.close()
            print("✓ Pico cleaned up")


def main():
    """Main test runner"""
    print("\n" + "="*60)
    print("🔧 PICO ADC INTERACTIVE TEST SUITE")
    print("="*60 + "\n")
    
    # Show configuration
    print_config_summary()
    
    # Create tester
    tester = PicoTester()
    
    if not tester.pico:
        print("✗ Pico tester not initialized. Aborting tests.")
        return 1
    
    # Run tests
    try:
        print("\n" + "="*60)
        response = input("Press Enter to start tests...")
        print()
        
        # Connection test
        if not tester.test_connection():
            print("\n⚠ Pico not connected. Cannot continue with tests.")
            print("\nTroubleshooting:")
            print("  1. Check USB cable: ls /dev/ttyACM*")
            print("  2. Check Pico firmware: dmesg | tail -20")
            print("  3. Check permissions: sudo usermod -a -G dialout $USER")
            return 1
        
        time.sleep(1)
        
        # ADC channels test
        tester.test_adc_channels(duration=15)
        time.sleep(1)
        
        # Smoothing test
        tester.test_smoothing(duration=10)
        time.sleep(1)
        
        # Throttle conversion test
        tester.test_throttle_conversion()
        
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

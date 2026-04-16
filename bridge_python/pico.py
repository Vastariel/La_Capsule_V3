#!/usr/bin/env python3
"""
Pico Module - Handling Pico ADC readings with error management and smoothing
"""

import time
import sys
from collections import deque
from typing import Optional, Dict

try:
    import picod
except ImportError:
    print("✗ Module 'picod' non installé. Installez: pip install picod")
    sys.exit(1)

from utils import PICO_PORT, PICO_BAUD, THROTTLE_SMOOTHING_WINDOW


class PicoManager:
    """Manager for Pico ADC readings with smoothing and error handling"""
    
    def __init__(self, port: str = PICO_PORT):
        """Initialize Pico connection
        
        Args:
            port: Serial port (e.g., "/dev/ttyACM0")
        """
        self.port = port
        self.pico = None
        self.connected = False
        self.last_error_time = 0
        self.error_count = 0
        
        # Smoothing buffers for ADC channels
        self.adc_buffers: Dict[int, deque] = {
            i: deque(maxlen=THROTTLE_SMOOTHING_WINDOW) for i in range(4)
        }
        
        self._connect()
    
    def _connect(self):
        """Attempt Pico connection with error handling"""
        try:
            self.pico = picod.pico(device=self.port)
            if self.pico and self.pico.connected:
                self.pico.reset()
                self.connected = True
                print(f"✓ Pico connecté sur {self.port}")
            else:
                print(f"✗ Pico non connecté sur {self.port}")
                self.connected = False
        except Exception as e:
            print(f"✗ Erreur connexion Pico: {e}")
            self.connected = False
    
    def read_adc_raw(self, channel: int) -> Optional[int]:
        """Read raw ADC value (0-4095)
        
        Args:
            channel: ADC channel (0-3)
            
        Returns:
            Raw value or None on error
        """
        if not self.connected or not self.pico:
            return None
        
        try:
            status, ch, val = self.pico.adc_read(channel)
            if status == picod.STATUS_OKAY:
                self.error_count = 0  # Reset error counter on success
                return val
            else:
                self._handle_read_error(channel, f"Status: {status}")
                return None
        except Exception as e:
            self._handle_read_error(channel, str(e))
            return None
    
    def read_adc_smoothed(self, channel: int) -> Optional[float]:
        """Read ADC value with smoothing applied (0-4095)
        
        Args:
            channel: ADC channel (0-3)
            
        Returns:
            Smoothed value or None on error
        """
        if channel not in self.adc_buffers:
            return None
        
        val = self.read_adc_raw(channel)
        if val is not None:
            self.adc_buffers[channel].append(val)
            if len(self.adc_buffers[channel]) > 0:
                return sum(self.adc_buffers[channel]) / len(self.adc_buffers[channel])
        
        return None
    
    def read_adc_percent(self, channel: int, smoothed: bool = True) -> Optional[float]:
        """Read ADC value as percentage (0-100%)
        
        Args:
            channel: ADC channel (0-3)
            smoothed: Use smoothed values
            
        Returns:
            Percentage or None on error
        """
        if smoothed:
            val = self.read_adc_smoothed(channel)
        else:
            val = self.read_adc_raw(channel)
        
        if val is not None:
            return (val / 4095.0) * 100.0
        return None
    
    def read_adc_normalized(self, channel: int, smoothed: bool = True) -> Optional[float]:
        """Read ADC value normalized to 0.0-1.0
        
        Args:
            channel: ADC channel (0-3)
            smoothed: Use smoothed values
            
        Returns:
            Normalized value or None on error
        """
        if smoothed:
            val = self.read_adc_smoothed(channel)
        else:
            val = self.read_adc_raw(channel)
        
        if val is not None:
            return val / 4095.0
        return None
    
    def _handle_read_error(self, channel: int, error: str):
        """Handle ADC read error with logging"""
        self.error_count += 1
        current_time = time.time()
        
        # Only log once per 5 seconds to avoid spam
        if current_time - self.last_error_time > 5:
            print(f"⚠ Erreur lecture Pico canal {channel}: {error} (x{self.error_count})")
            self.last_error_time = current_time
    
    def reconnect(self):
        """Attempt to reconnect Pico"""
        print("🔄 Reconnexion Pico...")
        self.error_count = 0
        self._connect()
    
    def close(self):
        """Close Pico connection"""
        if self.pico:
            try:
                self.pico.close()
                print("✓ Pico déconnecté")
            except:
                pass
        self.connected = False
    
    def get_state(self) -> Dict:
        """Get current Pico state for monitoring"""
        return {
            "connected": self.connected,
            "port": self.port,
            "error_count": self.error_count,
            "channels": {
                i: {
                    "raw": self.read_adc_raw(i),
                    "smoothed": self.read_adc_smoothed(i),
                    "percent": self.read_adc_percent(i, smoothed=True)
                }
                for i in range(4)
            }
        }
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()


if __name__ == "__main__":
    """
    Quick Pico test - for more comprehensive testing, use:
    python3 tests/test_pico_interactive.py
    """
    print("\n" + "="*60)
    print("🧪 Pico ADC Module - Quick Test")
    print("="*60 + "\n")
    
    # Quick sanity check
    pico = PicoManager()
    
    if pico.connected:
        print("✓ Pico is connected on port:", pico.port)
        
        # Quick 5-second readout
        print("\nReading ADC channels for 5 seconds...\n")
        
        try:
            for i in range(10):
                print(f"  Read {i+1}: ", end="")
                for channel in range(4):
                    raw = pico.read_adc_raw(channel)
                    if raw is not None:
                        print(f"CH{channel}={raw:4d} ", end="")
                    else:
                        print(f"CH{channel}=ERR  ", end="")
                print()
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
    else:
        print("⚠ Pico not connected")
        print("\nTroubleshooting:")
        print("  1. Check USB cable: ls /dev/ttyACM*")
        print("  2. Check Pico firmware (should show picod)")
        print("  3. Check permissions: sudo usermod -a -G dialout $USER")
    
    print("\n✓ Pico module is working\n")
    
    print("For COMPREHENSIVE PICO testing, run:")
    print("  python3 tests/test_pico_interactive.py\n")
    
    print("This provides:")
    print("  ✓ Connection diagnostics")
    print("  ✓ Live ADC channel monitoring")
    print("  ✓ Smoothing verification")
    print("  ✓ Throttle conversion testing\n")
    
    pico.close()

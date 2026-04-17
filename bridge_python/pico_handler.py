#!/usr/bin/env python3
"""
Pico Handler - Manages RP2040 Pico ADC readings for throttle control
Provides smoothed ADC values with error handling
"""

import time
from collections import deque
from typing import Optional
import sys

try:
    import picod
except ImportError:
    print("⚠ Module 'picod' non installé. Installez: pip install picod")
    picod = None


class PicoHandler:
    """Manages Pico ADC readings with smoothing"""
    
    def __init__(self, port: str = "/dev/ttyACM0", smoothing_window: int = 10):
        """Initialize Pico connection
        
        Args:
            port: Serial port for Pico
            smoothing_window: Size of smoothing buffer
        """
        self.port = port
        self.smoothing_window = smoothing_window
        self.pico = None
        self.connected = False
        self.ser = None  # For compatibility with main.py cleanup
        self.last_error = None
        
        # Smoothing buffers
        self.adc_buffers = {
            0: deque(maxlen=smoothing_window),
            1: deque(maxlen=smoothing_window),
            2: deque(maxlen=smoothing_window),
            3: deque(maxlen=smoothing_window),
        }
        
        self.connect()
    
    def connect(self) -> bool:
        """Connect to Pico
        
        Returns:
            True if connected, False otherwise
        """
        if picod is None:
            self.last_error = "picod module not installed"
            return False
        
        try:
            print(f"[PICO] Connexion sur {self.port}...", end=" ", flush=True)
            self.pico = picod.pico(device=self.port)
            
            # Give pico a moment to initialize
            time.sleep(0.5)
            
            if self.pico:
                self.connected = True
                self.ser = self.pico  # For compatibility
                print("✓ OK", flush=True)
                return True
            else:
                print("✗ Échec (pico is None)", flush=True)
                self.connected = False
                return False
        except Exception as e:
            self.last_error = str(e)
            print(f"✗ Erreur: {e}", flush=True)
            self.connected = False
            return False
    
    def read_raw(self, channel: int) -> Optional[int]:
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
            if picod and hasattr(picod, 'STATUS_OKAY') and status == picod.STATUS_OKAY:
                return val
            elif val is not None:
                return val
            return None
        except Exception as e:
            return None
    
    def read_smoothed(self, channel: int) -> Optional[float]:
        """Read smoothed ADC value (0-4095)
        
        Args:
            channel: ADC channel (0-3)
            
        Returns:
            Smoothed value or None on error
        """
        raw = self.read_raw(channel)
        if raw is not None and channel in self.adc_buffers:
            self.adc_buffers[channel].append(raw)
            if len(self.adc_buffers[channel]) > 0:
                return sum(self.adc_buffers[channel]) / len(self.adc_buffers[channel])
        return None
    
    def read_normalized(self, channel: int, smoothed: bool = True) -> Optional[float]:
        """Read ADC value normalized to 0.0-1.0
        
        Args:
            channel: ADC channel (0-3)
            smoothed: Whether to use smoothing
            
        Returns:
            Normalized value (0.0-1.0) or None on error
        """
        if smoothed:
            val = self.read_smoothed(channel)
        else:
            val = self.read_raw(channel)
        
        if val is not None:
            return val / 4095.0
        return None
    
    def read_percent(self, channel: int, smoothed: bool = True) -> Optional[float]:
        """Read ADC value as percentage (0-100%)
        
        Args:
            channel: ADC channel (0-3)
            smoothed: Whether to use smoothing
            
        Returns:
            Percentage value (0-100) or None on error
        """
        norm = self.read_normalized(channel, smoothed)
        if norm is not None:
            return norm * 100.0
        return None
    
    def get_throttle(self) -> float:
        """Get throttle value from channel 0
        
        Returns:
            Throttle value (0.0-1.0)
        """
        val = self.read_normalized(0, smoothed=True)
        return val if val is not None else 0.0
    
    def disconnect(self) -> None:
        """Safely disconnect Pico"""
        try:
            if self.pico:
                self.pico.close()
            self.connected = False
            print("[PICO] Déconnecté")
        except:
            pass

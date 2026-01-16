#!/usr/bin/env python3
"""
Pico Monitor - Reads Pico ADC values locally on Raspberry Pi
"""

import picod
import time


class PicoMonitor:
    """Monitor Pico ADC values locally on Raspberry Pi"""
    
    def __init__(self, pico_port="/dev/ttyACM0"):
        """Initialize Pico connection"""
        self.pico_port = pico_port
        self.pico = None
        self.connected = False
        
        try:
            self.pico = picod.pico()  # Direct connection on Raspi
            if self.pico and self.pico.connected:
                self.pico.reset()
                self.connected = True
                print(f"✓ Pico initialisé sur {pico_port}")
            else:
                print(f"✗ Pico non connecté sur {pico_port}")
        except Exception as e:
            print(f"✗ Erreur connexion Pico: {e}")
    
    def read_adc(self, channel):
        """Read ADC value from Pico (0-4095)"""
        if not self.connected or not self.pico:
            return None
        
        try:
            status, ch, val = self.pico.adc_read(channel)
            if status == picod.STATUS_OKAY:
                return val
        except Exception as e:
            print(f"✗ Erreur lecture ADC canal {channel}: {e}")
        return None
    
    def read_adc_percentage(self, channel):
        """Read ADC value as percentage (0-100%)"""
        val = self.read_adc(channel)
        if val is not None:
            return (val / 4095.0) * 100.0
        return None
    
    def get_state(self):
        """Get current Pico ADC state"""
        state = {
            "connected": self.connected,
            "channels": {}
        }
        
        if not self.connected:
            return state
        
        # Read only ADC channel 0
        try:
            val = self.read_adc(0)
            percentage = self.read_adc_percentage(0)
            if val is not None:
                state["channels"]["adc_0"] = {
                    "raw": val,
                    "percentage": percentage
                }
        except:
            pass
        
        return state
    
    def close(self):
        """Close Pico connection"""
        if self.pico:
            try:
                self.pico.close()
                print("✓ Pico connection fermée")
            except:
                pass


if __name__ == "__main__":
    monitor = PicoMonitor()
    try:
        while True:
            state = monitor.get_state()
            print(state)
            time.sleep(0.5)
    except KeyboardInterrupt:
        monitor.close()

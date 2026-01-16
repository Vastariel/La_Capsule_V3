#!/usr/bin/env python3
"""
GPIO Monitor - Reads GPIO states on Raspberry Pi
"""

from gpiozero import LED, Button, Device
from gpiozero.pins.bcm import BCMFactory


class GPIOMonitor:
    """Monitor GPIO states locally on Raspberry Pi"""
    
    def __init__(self):
        """Initialize GPIO monitoring"""
        # Use local BCM pins (not remote)
        Device.pin_factory = BCMFactory()
        
        # LED PIN MAPPINGS
        self.led_rouges_pins = [24, 27, 25, 21]
        self.led_vertes_pins = [18, 12]
        
        # BUTTON PIN MAPPINGS
        # Leviers (analog switches)
        self.leviers_pins = {
            16: "SAS",
            26: "RCS",
            22: "THROTTLE_CONTROL"
        }
        
        # Boutons (momentary switches)
        self.boutons_pins = {
            6: "HEAT_SHIELD",
            13: "PARACHUTE",
            11: "LANDING_GEAR",
            5: "TOGGLE_MAP",
            20: "ENGINE_START",
            7: "FAIRING",
            23: "STAGE_BOOSTERS",
            8: "STAGE_1",
            4: "STAGE_2",
            19: "STAGE_3"
        }
        
        # Initialize LEDs
        try:
            self.led_rouges = {pin: LED(pin) for pin in self.led_rouges_pins}
            self.led_vertes = {pin: LED(pin) for pin in self.led_vertes_pins}
            print("✓ LEDs initialisées")
        except Exception as e:
            print(f"✗ Erreur initialisation LEDs: {e}")
            self.led_rouges = {}
            self.led_vertes = {}
        
        # Initialize Leviers
        try:
            self.leviers = {}
            for pin, action in self.leviers_pins.items():
                self.leviers[pin] = Button(pin, pull_up=True)
            print("✓ Leviers initialisés")
        except Exception as e:
            print(f"✗ Erreur initialisation leviers: {e}")
            self.leviers = {}
        
        # Initialize Boutons
        try:
            self.boutons = {}
            for pin, action in self.boutons_pins.items():
                self.boutons[pin] = Button(pin, pull_up=True)
            print("✓ Boutons initialisés")
        except Exception as e:
            print(f"✗ Erreur initialisation boutons: {e}")
            self.boutons = {}
        
        # Previous states for change detection
        self.etat_prec_leviers = {pin: False for pin in self.leviers_pins.keys()}
        self.etat_prec_boutons = {pin: False for pin in self.boutons_pins.keys()}
    
    def get_state(self):
        """Get current GPIO state"""
        state = {
            "leviers": {},
            "boutons": {},
            "leds_rouges": {},
            "leds_vertes": {}
        }
        
        # Leviers state
        for pin, action in self.leviers_pins.items():
            if pin in self.leviers:
                state["leviers"][action] = self.leviers[pin].is_pressed
        
        # Boutons state
        for pin, action in self.boutons_pins.items():
            if pin in self.boutons:
                state["boutons"][action] = self.boutons[pin].is_pressed
        
        # LEDs state
        for pin, led in self.led_rouges.items():
            state["leds_rouges"][f"pin_{pin}"] = led.is_lit
        
        for pin, led in self.led_vertes.items():
            state["leds_vertes"][f"pin_{pin}"] = led.is_lit
        
        return state
    
    def cleanup(self):
        """Turn off all LEDs and cleanup"""
        for led in self.led_rouges.values():
            led.off()
        for led in self.led_vertes.values():
            led.off()
        print("✓ GPIO cleanup - LEDs éteintes")


if __name__ == "__main__":
    monitor = GPIOMonitor()
    import time
    try:
        while True:
            state = monitor.get_state()
            print(state)
            time.sleep(0.5)
    except KeyboardInterrupt:
        monitor.cleanup()

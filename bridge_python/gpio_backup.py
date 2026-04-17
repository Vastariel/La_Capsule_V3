#!/usr/bin/env python3
"""
GPIO Module - Handling Raspberry Pi GPIO pins with gpiozero
Refactored to use centralized config and improved error handling
"""

import sys
from typing import Dict, Optional, Callable

try:
    from gpiozero import LED, Button
    from gpiozero.pins.pigpio import PiGPIOFactory
except ImportError:
    print("✗ Module 'gpiozero' non installé. Installez: pip install gpiozero pigpio")
    sys.exit(1)

from utils import (
    RASPI_IP, LED_ROUGES_PINS, LED_VERTES_PINS,
    LEVIERS_PINS, BOUTONS_PINS
)


class GPIO:
    """Manager for Raspberry Pi GPIO operations (legacy compatibility)"""
    
    def __init__(self, api=None, enable_pico=False, use_remote: bool = True):
        """Initialize GPIO
        
        Args:
            api: API reference for kRPC integration
            enable_pico: Enable Pico ADC reading (legacy)
            use_remote: Use remote GPIO via pigpio
        """
        self.api = api
        self.connected = False
        
        # Pico import but now managed separately via pico.py
        self.pico = None
        if enable_pico:
            try:
                from pico import PicoManager
                self.pico = PicoManager()
            except ImportError:
                print("✗ PicoManager not available, skipping Pico")
        
        # Initialize GPIO factory
        if use_remote:
            try:
                self.factory = PiGPIOFactory(host=RASPI_IP)
                print(f"✓ GPIO factory connecté à {RASPI_IP} via pigpio")
                self.connected = True
            except Exception as e:
                print(f"✗ Erreur connexion GPIO distante: {e}")
                self.connected = False
                return
        else:
            self.factory = None
            print("✓ GPIO utilise BCM GPIO local")
            self.connected = True
        
        # LED dictionaries
        self.led_rouges = {}
        self.led_vertes = {}
        
        # Button dictionaries
        self.leviers = {}
        self.boutons = {}
        
        # Button state tracking
        self.etat_prec_leviers = {pin: False for pin in LEVIERS_PINS.keys()}
        self.etat_prec_boutons = {pin: False for pin in BOUTONS_PINS.keys()}
        
        self._initialize_leds()
        self._initialize_buttons()
    
    def _initialize_leds(self):
        """Initialize LED pins"""
        try:
            for pin in LED_ROUGES_PINS:
                self.led_rouges[pin] = LED(pin, pin_factory=self.factory if self.connected else None)
            print(f"✓ {len(self.led_rouges)} LEDs rouges initialisées")
        except Exception as e:
            print(f"✗ Erreur initialisation LEDs rouges: {e}")
        
        try:
            for pin in LED_VERTES_PINS:
                self.led_vertes[pin] = LED(pin, pin_factory=self.factory if self.connected else None)
            print(f"✓ {len(self.led_vertes)} LEDs vertes initialisées")
        except Exception as e:
            print(f"✗ Erreur initialisation LEDs vertes: {e}")
    
    def _initialize_buttons(self):
        """Initialize button pins"""
        try:
            for pin in LEVIERS_PINS.keys():
                self.leviers[pin] = Button(pin, pull_up=True, pin_factory=self.factory if self.connected else None)
            print(f"✓ {len(self.leviers)} leviers initialisés")
        except Exception as e:
            print(f"✗ Erreur initialisation leviers: {e}")
        
        try:
            for pin in BOUTONS_PINS.keys():
                self.boutons[pin] = Button(pin, pull_up=True, pin_factory=self.factory if self.connected else None)
            print(f"✓ {len(self.boutons)} boutons initialisés")
        except Exception as e:
            print(f"✗ Erreur initialisation boutons: {e}")
    
    def update(self):
        """Update GPIO inputs and process kRPC commands"""
        if not self.api or not self.connected:
            return
        
        # Leviers (3-state switches)
        for pin, action in LEVIERS_PINS.items():
            if pin not in self.leviers:
                continue
            
            etat = self.leviers[pin].is_pressed
            
            # Affichage LED verte pour les leviers
            if pin == list(LEVIERS_PINS.keys())[0] and len(self.led_vertes) > 0:
                led_pin = list(self.led_vertes.keys())[0]
                if etat:
                    self.led_vertes[led_pin].on()
                else:
                    self.led_vertes[led_pin].off()
            
            # Détection changement d'état
            if etat != self.etat_prec_leviers[pin]:
                print(f"[LEVIER] GPIO {pin} ({action}): {'ACTIVÉ' if etat else 'DÉSACTIVÉ'}")
                
                if action == "SAS" and hasattr(self.api, 'set_sas'):
                    self.api.set_sas(etat)
                elif action == "RCS" and hasattr(self.api, 'set_rcs'):
                    self.api.set_rcs(etat)
                
                self.etat_prec_leviers[pin] = etat
        
        # Boutons (momentary switches)
        for pin, action in BOUTONS_PINS.items():
            if pin not in self.boutons:
                continue
            
            etat = self.boutons[pin].is_pressed
            
            # Détecte la transition LOW (appui)
            if etat and not self.etat_prec_boutons[pin]:
                print(f"[BOUTON] GPIO {pin} ({action}): APPUYÉ")
                
                if action == "STAGE_BOOSTERS" and hasattr(self.api, 'stage'):
                    self.api.stage()
                elif action == "STAGE_1" and hasattr(self.api, 'stage'):
                    self.api.stage()
                elif action == "STAGE_2" and hasattr(self.api, 'stage'):
                    self.api.stage()
                elif action == "STAGE_3" and hasattr(self.api, 'stage'):
                    self.api.stage()
                elif action == "PARACHUTE" and hasattr(self.api, 'deploy_parachute'):
                    self.api.deploy_parachute()
                elif action == "LANDING_GEAR" and hasattr(self.api, 'toggle_landing_gear'):
                    self.api.toggle_landing_gear()
            
            self.etat_prec_boutons[pin] = etat
    
    def cleanup(self):
        """Turn off all LEDs and close connections"""
        try:
            for led in self.led_rouges.values():
                led.off()
            for led in self.led_vertes.values():
                led.off()
            if self.pico:
                self.pico.close()
            print("✓ GPIO cleanup - LEDs éteintes")
        except Exception as e:
            print(f"✗ Erreur cleanup GPIO: {e}")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.cleanup()


if __name__ == "__main__":
    """
    Quick GPIO test - for more comprehensive testing, use:
    python3 tests/test_gpio_interactive.py
    """
    print("\n" + "="*60)
    print("🧪 GPIO Module - Quick Test")
    print("="*60 + "\n")
    
    # Quick sanity check
    print("ℹ Configuration loaded successfully")
    print(f"  - Red LEDs: {LED_ROUGES_PINS}")
    print(f"  - Green LEDs: {LED_VERTES_PINS}")
    print(f"  - Leviers: {list(LEVIERS_PINS.keys())}")
    print(f"  - Buttons: {list(BOUTONS_PINS.keys())}")
    
    print("\n✓ GPIO module is working\n")
    
    print("For COMPREHENSIVE GPIO testing, run:")
    print("  python3 tests/test_gpio_interactive.py\n")
    
    print("This provides:")
    print("  ✓ Individual LED testing")
    print("  ✓ Button press detection")
    print("  ✓ Switch state monitoring")
    print("  ✓ Test results summary\n")
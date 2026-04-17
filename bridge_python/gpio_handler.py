#!/usr/bin/env python3
"""
GPIO Handler - Manages Raspberry Pi GPIO for buttons/LEDs and action group triggering
Controls hardware inputs/outputs and integrates with KRPC action groups
"""

import sys
from typing import Dict, Optional

try:
    from gpiozero import LED, Button
    from gpiozero.pins.pigpio import PiGPIOFactory
except ImportError:
    print("✗ Module 'gpiozero' non installé. Installez: pip install gpiozero pigpio")
    sys.exit(1)


class GPIOHandler:
    """Manages GPIO inputs (buttons) and outputs (LEDs)"""
    
    # Default GPIO pin mappings
    DEFAULT_CONFIG = {
        "leds_rouges": [24, 27, 25, 21],    # Stage indicators
        "leds_vertes": [18, 12],             # SAS, RCS
        "leviers": {16: "SAS", 26: "RCS", 22: "THROTTLE_CONTROL"},
        "boutons": {
            20: 0,      # AG 0: Allumage booster
            23: 1,      # AG 1: Séparation booster
            8: 2,       # AG 2: Séparation stage 1
            4: 3,       # AG 3: Séparation stage 2
            19: 4,      # AG 4: Séparation stage 3
            13: 5,      # AG 5: Parachutes
            6: 6,       # AG 6: Bouclier thermique
            7: 9,       # AG 9: Coiffe
            11: "GEAR", # Landing gear (special)
            5: "MAP",   # Toggle map camera
        }
    }
    
    def __init__(self, krpc=None, pico=None, config: Optional[Dict] = None, 
                 raspi_ip: str = "192.168.1.56", use_remote: bool = True):
        """Initialize GPIO handler
        
        Args:
            krpc: KRPCHandler instance
            pico: PicoHandler instance  
            config: GPIO configuration dict
            raspi_ip: Raspberry Pi IP for remote GPIO
            use_remote: Use remote GPIO via pigpio
        """
        self.krpc = krpc
        self.pico = pico
        self.config = config or self.DEFAULT_CONFIG
        self.connected = False
        self.factory = None
        
        # Hardware objects
        self.leds_red = {}
        self.leds_green = {}
        self.buttons_leviers = {}
        self.buttons_boutons = {}
        
        # Aliases for backwards compatibility with tests
        self.led_rouges = self.leds_red
        self.led_vertes = self.leds_green
        self.leviers = self.buttons_leviers
        self.boutons = self.buttons_boutons
        
        # State tracking
        self.prev_button_states = {}
        self.throttle_last = 0.0
        self.sas_led_state = False
        self.rcs_led_state = False
        self.stage_led_states = {}
        
        # Initialize GPIO
        if use_remote:
            try:
                self.factory = PiGPIOFactory(host=raspi_ip)
                self.connected = True
                print(f"[GPIO] Connecté à {raspi_ip} via pigpio")
            except Exception as e:
                print(f"[GPIO] Erreur connexion pigpio: {e}")
                self.connected = False
                return
        else:
            self.connected = True
            print("[GPIO] Utilise GPIO local")
        
        self._initialize_pins()
    
    def _initialize_pins(self):
        """Initialize all GPIO pins"""
        if not self.connected:
            return
        
        # Initialize LEDs
        for pin in self.config.get("leds_rouges", []):
            try:
                self.leds_red[pin] = LED(pin, pin_factory=self.factory)
                self.stage_led_states[pin] = False
            except Exception as e:
                print(f"[GPIO] Erreur LED rouge {pin}: {e}")
        
        for pin in self.config.get("leds_vertes", []):
            try:
                self.leds_green[pin] = LED(pin, pin_factory=self.factory)
            except Exception as e:
                print(f"[GPIO] Erreur LED verte {pin}: {e}")
        
        # Initialize button inputs
        for pin in self.config.get("leviers", {}).keys():
            try:
                self.buttons_leviers[pin] = Button(pin, pull_up=True, pin_factory=self.factory)
                self.prev_button_states[f"levier_{pin}"] = False
            except Exception as e:
                print(f"[GPIO] Erreur levier {pin}: {e}")
        
        for pin in self.config.get("boutons", {}).keys():
            try:
                self.buttons_boutons[pin] = Button(pin, pull_up=True, pin_factory=self.factory)
                self.prev_button_states[f"bouton_{pin}"] = False
            except Exception as e:
                print(f"[GPIO] Erreur bouton {pin}: {e}")
        
        print(f"[GPIO] {len(self.leds_red)} LEDs rouges, {len(self.leds_green)} vertes")
        print(f"[GPIO] {len(self.buttons_leviers)} leviers, {len(self.buttons_boutons)} boutons")
    
    def update(self):
        """Update all GPIO states - call regularly"""
        if not self.connected or not self.krpc:
            return
        
        self._update_leviers()
        self._update_boutons()
        self._update_throttle()
        self._update_leds()
    
    def _update_leviers(self):
        """Update lever (switch) states"""
        for pin, action in self.config.get("leviers", {}).items():
            if pin not in self.buttons_leviers:
                continue
            
            pressed = self.buttons_leviers[pin].is_pressed
            prev = self.prev_button_states.get(f"levier_{pin}", False)
            
            if pressed != prev:
                self.prev_button_states[f"levier_{pin}"] = pressed
                print(f"[GPIO] Levier {action}: {'ON' if pressed else 'OFF'}")
                
                if action == "SAS":
                    self.krpc.set_sas(pressed)
                elif action == "RCS":
                    self.krpc.set_rcs(pressed)
    
    def _update_boutons(self):
        """Update button (momentary) states"""
        for pin, action in self.config.get("boutons", {}).items():
            if pin not in self.buttons_boutons:
                continue
            
            pressed = self.buttons_boutons[pin].is_pressed
            prev = self.prev_button_states.get(f"bouton_{pin}", False)
            
            # Trigger on press (transition from False to True)
            if pressed and not prev:
                self._handle_button_press(pin, action)
            
            self.prev_button_states[f"bouton_{pin}"] = pressed
    
    def _handle_button_press(self, pin: int, action):
        """Handle button press - trigger action group or special action"""
        
        # If action is an integer, it's an AG number
        if isinstance(action, int):
            self.krpc.trigger_action_group(action)
            return
        
        # Special actions
        if action == "GEAR":
            # Landing gear - access via control.brakes
            try:
                self.krpc.control.brakes = not self.krpc.control.brakes
                state = "déployé" if self.krpc.control.brakes else "rétracté"
                print(f"[KSP] Train {state}")
            except:
                pass
        
        elif action == "MAP":
            self.krpc.toggle_map_camera()
    
    def _update_throttle(self):
        """Update throttle from potentiometer if available"""
        if not self.pico:
            return
        
        # Check if throttle control lever (22) is enabled
        throttle_lever = self.buttons_leviers.get(22)
        if throttle_lever and not throttle_lever.is_pressed:
            # Lever OFF = cut throttle
            if self.throttle_last != 0.0:
                self.krpc.set_throttle(0.0)
                self.throttle_last = 0.0
            return
        
        # Read throttle from potentiometer
        throttle = self.pico.get_throttle()
        if throttle is None:
            return
        
        # Apply deadzone (2%)
        deadzone = 0.02
        if throttle < deadzone:
            throttle = 0.0
        elif throttle > (1.0 - deadzone):
            throttle = 1.0
        
        # Only update if change > 1%
        if abs(throttle - self.throttle_last) > 0.01:
            self.krpc.set_throttle(throttle)
            self.throttle_last = throttle
    
    def _update_leds(self):
        """Update LED states based on vessel state"""
        if not self.krpc.connected or not self.krpc.vessel:
            return
        
        # Update SAS/RCS indicators (green LEDs)
        self._update_green_leds()
        
        # Update stage indicators (red LEDs)
        self._update_red_leds()
    
    def _update_green_leds(self):
        """Update green LEDs (SAS=18, RCS=12) based on state"""
        # LED 18 = SAS
        if 18 in self.leds_green:
            if self.krpc.sas_state and not self.sas_led_state:
                self.leds_green[18].on()
                self.sas_led_state = True
            elif not self.krpc.sas_state and self.sas_led_state:
                self.leds_green[18].off()
                self.sas_led_state = False
        
        # LED 12 = RCS
        if 12 in self.leds_green:
            if self.krpc.rcs_state and not self.rcs_led_state:
                self.leds_green[12].on()
                self.rcs_led_state = True
            elif not self.krpc.rcs_state and self.rcs_led_state:
                self.leds_green[12].off()
                self.rcs_led_state = False
    
    def _update_red_leds(self):
        """Update red LEDs based on current stage"""
        try:
            current_stage = self.krpc.telemetry.get('current_stage', 0)
            
            # Map: LED -> associated stage number
            # Adjust based on your rocket structure:
            # 24 = Booster (stage 4-6)
            # 27 = Main stage (stage 3)
            # 25 = Upper stage (stage 2)
            # 21 = Final stage (stage 1)
            
            stage_map = {
                24: [4, 5, 6],  # Booster
                27: [3],        # Stage 1
                25: [2],        # Stage 2
                21: [1],        # Stage 3
            }
            
            for led_pin, stages in stage_map.items():
                if led_pin not in self.leds_red:
                    continue
                
                is_active = current_stage in stages
                
                if is_active and not self.stage_led_states.get(led_pin, False):
                    self.leds_red[led_pin].on()
                    self.stage_led_states[led_pin] = True
                elif not is_active and self.stage_led_states.get(led_pin, False):
                    self.leds_red[led_pin].off()
                    self.stage_led_states[led_pin] = False
        
        except Exception as e:
            pass
    
    def cleanup(self):
        """Turn off all LEDs"""
        try:
            for led in self.leds_red.values():
                led.off()
            for led in self.leds_green.values():
                led.off()
            print("[GPIO] Nettoyage: LEDs éteintes")
        except Exception as e:
            print(f"[GPIO] Erreur cleanup: {e}")
    
    def __del__(self):
        try:
            self.cleanup()
        except:
            pass

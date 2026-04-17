#!/usr/bin/env python3
"""
GPIO Module - Refactored for Action Groups
Handles Raspberry Pi GPIO pins, LEDs, and kRPC action groups
"""

import sys
import time
import json
import os
from typing import Dict, Optional

try:
    from gpiozero import LED, Button
    from gpiozero.pins.pigpio import PiGPIOFactory
except ImportError:
    print("✗ Module 'gpiozero' non installé. Installez: pip install gpiozero pigpio")
    sys.exit(1)

from utils import (
    RASPI_IP, LED_ROUGES_PINS, LED_VERTES_PINS,
    LEVIERS_PINS, BOUTONS_PINS,
    THROTTLE_DEADZONE
)


class GPIOManager:
    """
    GPIO Manager with Action Groups support
    
    Responsibilities:
    - Read GPIO inputs (buttons, switches)
    - Control GPIO outputs (LEDs)
    - Apply throttle from potentiometer
    - Trigger action groups via kRPC
    - Provide visual feedback based on vessel state
    """
    
    def __init__(self, api=None, pico=None, use_remote: bool = True):
        """Initialize GPIO
        
        Args:
            api: API reference for kRPC commands
            pico: PicoManager reference for throttle ADC
            use_remote: Use remote GPIO via pigpio
        """
        self.api = api
        self.pico = pico
        self.connected = False
        self.factory = None
        
        # Load action groups from config
        self.action_groups = {}
        self.special_actions = {}
        self._load_action_config()
        
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
        
        # LED management
        self.led_rouges_map = {}  # {pin: LED object}
        self.led_vertes_map = {}  # {pin: LED object}
        
        # Button management
        self.leviers_map = {}     # {pin: Button object}
        self.boutons_map = {}     # {pin: Button object}
        
        # State tracking
        self.button_states = {}   # Previous button states for edge detection
        self.led_states = {}      # Current LED states for feedback
        self.throttle_last = 0.0  # Last applied throttle value
        
        # Vessel state tracking
        self.sas_state = False    # Cached SAS state
        self.rcs_state = False    # Cached RCS state
        self.current_stage = 0    # Current active stage
        
        self._initialize_hardware()
    
    def _load_action_config(self):
        """Load action group configuration from config file"""
        try:
            # Load from config.json
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                "setup", "config.json"
            )
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    if 'actions' in config:
                        self.action_groups = config['actions'].get('action_groups', {})
                        self.special_actions = config['actions'].get('special_actions', {})
                        print(f"✓ Configuration d'actions chargée: {len(self.action_groups)} groupes")
        except Exception as e:
            print(f"⚠ Erreur charge config actions: {e}")
    
    def _initialize_hardware(self):
        """Initialize all GPIO pins"""
        if not self.connected:
            return
        
        # Initialize LEDs
        for pin in LED_ROUGES_PINS:
            try:
                self.led_rouges_map[pin] = LED(pin, pin_factory=self.factory)
                self.led_states[f"red_{pin}"] = False
            except Exception as e:
                print(f"✗ Erreur LED rouge {pin}: {e}")
        
        for pin in LED_VERTES_PINS:
            try:
                self.led_vertes_map[pin] = LED(pin, pin_factory=self.factory)
                self.led_states[f"green_{pin}"] = False
            except Exception as e:
                print(f"✗ Erreur LED verte {pin}: {e}")
        
        # Initialize Buttons
        for pin in LEVIERS_PINS.keys():
            try:
                self.leviers_map[pin] = Button(pin, pull_up=True, pin_factory=self.factory)
                self.button_states[f"levier_{pin}"] = False
            except Exception as e:
                print(f"✗ Erreur levier {pin}: {e}")
        
        for pin in BOUTONS_PINS.keys():
            try:
                self.boutons_map[pin] = Button(pin, pull_up=True, pin_factory=self.factory)
                self.button_states[f"button_{pin}"] = False
            except Exception as e:
                print(f"✗ Erreur bouton {pin}: {e}")
        
        print(f"✓ {len(self.led_rouges_map)} LEDs rouges initialisées")
        print(f"✓ {len(self.led_vertes_map)} LEDs vertes initialisées")
        print(f"✓ {len(self.leviers_map)} leviers initialisés")
        print(f"✓ {len(self.boutons_map)} boutons initialisés")
    
    def update(self):
        """Main update loop - called frequently from main.py"""
        if not self.api or not self.connected:
            return
        
        # 1. Process leviers (3-state switches)
        self._update_leviers()
        
        # 2. Process boutons (momentary buttons)
        self._update_boutons()
        
        # 3. Handle throttle from potentiometer
        self._update_throttle()
        
        # 4. Update LED feedback based on vessel state
        self._update_led_feedback()
    
    def _update_leviers(self):
        """Update leviers (SAS, RCS, THROTTLE_CONTROL)"""
        if not self.leviers_map:
            return
        
        for pin, action in LEVIERS_PINS.items():
            if pin not in self.leviers_map:
                continue
            
            pressed = self.leviers_map[pin].is_pressed
            prev_state = self.button_states.get(f"levier_{pin}", False)
            
            # Only on change
            if pressed != prev_state:
                self.button_states[f"levier_{pin}"] = pressed
                print(f"[LEVIER] {action} (GPIO {pin}): {'ON' if pressed else 'OFF'}")
                
                if action == "SAS":
                    self.api.set_stability_assistance(pressed)
                    self.sas_state = pressed
                elif action == "RCS":
                    self.api.set_reaction_control(pressed)
                    self.rcs_state = pressed
    
    def _update_boutons(self):
        """Update boutons (momentary buttons) - trigger action groups on press"""
        if not self.boutons_map:
            return
        
        for pin, action in BOUTONS_PINS.items():
            if pin not in self.boutons_map:
                continue
            
            pressed = self.boutons_map[pin].is_pressed
            prev_state = self.button_states.get(f"button_{pin}", False)
            
            # Trigger on press transition
            if pressed and not prev_state:
                print(f"[BOUTON] {action} (GPIO {pin}): APPUYÉ")
                self._handle_button_press(action, pin)
            
            self.button_states[f"button_{pin}"] = pressed
    
    def _handle_button_press(self, action: str, pin: int):
        """Handle button press by finding and triggering appropriate action group or action"""
        
        # First, check if this button is mapped to an action group
        for group_id, group_config in self.action_groups.items():
            if group_config.get("button") == pin:
                # Trigger this action group
                self.api.trigger_action_group(int(group_id))
                return
        
        # Then check special actions
        if action == "PARACHUTE":
            if hasattr(self.api, 'control'):
                try:
                    self.api.control.parachutes = True
                    print("[KSP] Parachute déployé")
                except:
                    pass
        
        elif action == "TOGGLE_MAP":
            if hasattr(self.api, 'toggle_map_camera'):
                self.api.toggle_map_camera()
    
    def _update_throttle(self):
        """Read potentiometer and apply throttle if lever 22 is ON"""
        if not self.pico or not self.api:
            return
        
        # Check if throttle control lever (22) is ON
        throttle_enabled = self.leviers_map.get(22, None)
        if throttle_enabled and not throttle_enabled.is_pressed:
            # Lever OFF = cut throttle
            if self.throttle_last != 0.0:
                self.api.set_throttle_level(0.0)
                self.throttle_last = 0.0
            return
        
        # Read potentiometer from Pico (channel 0)
        throttle_normalized = self.pico.read_adc_normalized(0, smoothed=True)
        
        if throttle_normalized is not None:
            # Apply deadzone
            if throttle_normalized < (THROTTLE_DEADZONE / 100.0):
                throttle_normalized = 0.0
            elif throttle_normalized > (1.0 - THROTTLE_DEADZONE / 100.0):
                throttle_normalized = 1.0
            
            # Only update if change is significant
            change = abs(throttle_normalized - self.throttle_last)
            if change > 0.01:  # 1% change threshold
                self.api.set_throttle_level(throttle_normalized)
                self.throttle_last = throttle_normalized
    
    def _update_led_feedback(self):
        """Update LED feedback based on vessel state"""
        if not self.connected or not self.api:
            return
        
        # Update green LEDs: SAS (18) and RCS (12)
        self._update_led_sas_rcs()
        
        # Update red LEDs: Stage indicators (24, 27, 25, 21)
        self._update_led_stages()
    
    def _update_led_sas_rcs(self):
        """Update green LEDs based on SAS/RCS state from API"""
        try:
            # LED 18 = SAS
            if 18 in self.led_vertes_map:
                if self.api.cached_sas_state:
                    if not self.led_states.get("green_18", False):
                        self.led_vertes_map[18].on()
                        self.led_states["green_18"] = True
                else:
                    if self.led_states.get("green_18", False):
                        self.led_vertes_map[18].off()
                        self.led_states["green_18"] = False
            
            # LED 12 = RCS  
            if 12 in self.led_vertes_map:
                if self.api.cached_rcs_state:
                    if not self.led_states.get("green_12", False):
                        self.led_vertes_map[12].on()
                        self.led_states["green_12"] = True
                else:
                    if self.led_states.get("green_12", False):
                        self.led_vertes_map[12].off()
                        self.led_states["green_12"] = False
        
        except Exception as e:
            pass  # API not ready yet
    
    def _update_led_stages(self):
        """
        Update red LEDs to show which stage is currently active
        
        Map the LEDs to stage numbers based on your rocket structure.
        Adjust these mappings in config.json as needed.
        
        By default:
        - LED 24 (pin 24) → Stages 4-6 (Booster)
        - LED 27 (pin 27) → Stage 3 (Main stage)
        - LED 25 (pin 25) → Stage 2
        - LED 21 (pin 21) → Stage 1
        """
        try:
            if self.api.current_stage is None:
                return
            
            # Map LED pins to their corresponding stage numbers
            # Feel free to adjust these based on your rocket structure
            led_to_stages = {
                24: [4, 5, 6],      # Booster stages
                27: [3],            # Stage 1 (main engine stage)
                25: [2],            # Stage 2
                21: [1],            # Stage 3
            }
            
            for led_pin, expected_stages in led_to_stages.items():
                if led_pin not in self.led_rouges_map:
                    continue
                
                # LED on if current stage is one of the expected stages for that LED
                is_current = self.api.current_stage in expected_stages
                
                if is_current:
                    self.led_rouges_map[led_pin].on()
                    self.led_states[f"red_{led_pin}"] = True
                else:
                    self.led_rouges_map[led_pin].off()
                    self.led_states[f"red_{led_pin}"] = False
        
        except Exception as e:
            pass  # API not ready yet
    
    def cleanup(self):
        """Turn off all LEDs and close connections"""
        try:
            for led in self.led_rouges_map.values():
                led.off()
            for led in self.led_vertes_map.values():
                led.off()
            print("✓ GPIO cleanup - LEDs éteintes")
        except Exception as e:
            print(f"✗ Erreur cleanup GPIO: {e}")
    
    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.cleanup()
        except:
            pass


# Keep old GPIO class name for backward compatibility
GPIO = GPIOManager
#!/usr/bin/env python3
"""
GPIO Module - Complete refactor with proper feedback and control
Handles Raspberry Pi GPIO pins, LEDs, and integrates with kRPC/Pico
"""

import sys
import time
from typing import Dict, Optional
from collections import defaultdict

try:
    from gpiozero import LED, Button
    from gpiozero.pins.pigpio import PiGPIOFactory
except ImportError:
    print("✗ Module 'gpiozero' non installé. Installez: pip install gpiozero pigpio")
    sys.exit(1)

from utils import (
    RASPI_IP, LED_ROUGES_PINS, LED_VERTES_PINS,
    LEVIERS_PINS, BOUTONS_PINS,
    THROTTLE_DEADZONE, THROTTLE_SMOOTHING_WINDOW
)


class GPIOManager:
    """
    Complete GPIO Manager with proper feedback and control
    
    Responsibilities:
    - Read GPIO inputs (buttons, switches)
    - Control GPIO outputs (LEDs)
    - Apply throttle from potentiometer
    - Track vessel state (SAS, RCS, staging)
    - Provide visual feedback
    """
    
    def __init__(self, api=None, pico=None, use_remote: bool = True):
        """Initialize GPIO
        
        Args:
            api: API reference for kRPC commands
            pico: PicoManager reference for throttle ADC
            use_remote: Use remote GPIO via pigpio
        """
        self.api = api
        self.pico = pico
        self.connected = False
        self.factory = None
        
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
        
        # LED management
        self.led_rouges_map = {}  # {pin: LED object}
        self.led_vertes_map = {}  # {pin: LED object}
        
        # Button management
        self.leviers_map = {}     # {pin: Button object}
        self.boutons_map = {}     # {pin: Button object}
        
        # State tracking
        self.button_states = {}   # Previous button states for edge detection
        self.led_states = {}      # Current LED states for feedback
        self.throttle_last = 0.0  # Last applied throttle value
        
        # Vessel state tracking
        self.vessel_masses = {}   # {stage_index: mass} for detecting separation
        self.sas_state = False    # Cached SAS state
        self.rcs_state = False    # Cached RCS state
        self.stage_detached = {}  # {stage_id: bool} for once-detached tracking
        
        self._initialize_hardware()
    
    def _initialize_hardware(self):
        """Initialize all GPIO pins"""
        if not self.connected:
            return
        
        # Initialize LEDs
        for pin in LED_ROUGES_PINS:
            try:
                self.led_rouges_map[pin] = LED(pin, pin_factory=self.factory)
                self.led_states[f"red_{pin}"] = False
            except Exception as e:
                print(f"✗ Erreur LED rouge {pin}: {e}")
        
        for pin in LED_VERTES_PINS:
            try:
                self.led_vertes_map[pin] = LED(pin, pin_factory=self.factory)
                self.led_states[f"green_{pin}"] = False
            except Exception as e:
                print(f"✗ Erreur LED verte {pin}: {e}")
        
        # Initialize Buttons
        for pin in LEVIERS_PINS.keys():
            try:
                self.leviers_map[pin] = Button(pin, pull_up=True, pin_factory=self.factory)
                self.button_states[f"levier_{pin}"] = False
            except Exception as e:
                print(f"✗ Erreur levier {pin}: {e}")
        
        for pin in BOUTONS_PINS.keys():
            try:
                self.boutons_map[pin] = Button(pin, pull_up=True, pin_factory=self.factory)
                self.button_states[f"button_{pin}"] = False
            except Exception as e:
                print(f"✗ Erreur bouton {pin}: {e}")
        
        print(f"✓ {len(self.led_rouges_map)} LEDs rouges initialisées")
        print(f"✓ {len(self.led_vertes_map)} LEDs vertes initialisées")
        print(f"✓ {len(self.leviers_map)} leviers initialisés")
        print(f"✓ {len(self.boutons_map)} boutons initialisés")
    
    def update(self):
        """Main update loop - called frequently from main.py"""
        if not self.api or not self.connected:
            return
        
        # 1. Process leviers (3-state switches) - immediate update
        self._update_leviers()
        
        # 2. Process boutons (momentary buttons) - on press
        self._update_boutons()
        
        # 3. Handle throttle from potentiometer
        self._update_throttle()
        
        # 4. Update LED feedback based on vessel state
        self._update_led_feedback()
    
    def _update_leviers(self):
        """Update leviers (SAS, RCS, THROTTLE_CONTROL)"""
        if not self.leviers_map:
            return
        
        for pin, action in LEVIERS_PINS.items():
            if pin not in self.leviers_map:
                continue
            
            pressed = self.leviers_map[pin].is_pressed
            prev_state = self.button_states.get(f"levier_{pin}", False)
            
            # Only on change
            if pressed != prev_state:
                self.button_states[f"levier_{pin}"] = pressed
                print(f"[LEVIER] {action} (GPIO {pin}): {'ON' if pressed else 'OFF'}")
                
                if action == "SAS":
                    self.api.set_stability_assistance(pressed)
                    self.sas_state = pressed
                elif action == "RCS":
                    self.api.set_reaction_control(pressed)
                    self.rcs_state = pressed
                # THROTTLE_CONTROL has no action, just affects throttle application
    
    def _update_boutons(self):
        """Update boutons (momentary buttons) - trigger on press"""
        if not self.boutons_map:
            return
        
        for pin, action in BOUTONS_PINS.items():
            if pin not in self.boutons_map:
                continue
            
            pressed = self.boutons_map[pin].is_pressed
            prev_state = self.button_states.get(f"button_{pin}", False)
            
            # Trigger on press transition
            if pressed and not prev_state:
                print(f"[BOUTON] {action} (GPIO {pin}): APPUYÉ")
                self._execute_action(action)
            
            self.button_states[f"button_{pin}"] = pressed
    
    def _execute_action(self, action: str):
        """Execute an action on kRPC"""
        try:
            if action == "ENGINE_START":
                # Just turns on engines, throttle controlled by levier 22 + potentiometer
                if hasattr(self.api, 'start_engines'):
                    self.api.start_engines()
            
            elif action == "STAGE_BOOSTERS" or action == "STAGE_1" or \
                 action == "STAGE_2" or action == "STAGE_3":
                if hasattr(self.api, 'stage'):
                    self.api.stage()
            
            elif action == "FAIRING":
                if hasattr(self.api, 'deploy_fairing'):
                    self.api.deploy_fairing()
            
            elif action == "HEAT_SHIELD":
                if hasattr(self.api, 'deploy_heat_shield'):
                    self.api.deploy_heat_shield()
            
            elif action == "PARACHUTE":
                if hasattr(self.api, 'deploy_parachute'):
                    self.api.deploy_parachute()
            
            elif action == "LANDING_GEAR":
                if hasattr(self.api, 'toggle_landing_gear'):
                    self.api.toggle_landing_gear()
            
            elif action == "TOGGLE_MAP":
                # Map toggle - no kRPC action
                print("[ACTION] Basculer carte (pas de kRPC)")
        
        except Exception as e:
            print(f"✗ Erreur action {action}: {e}")
    
    def _update_throttle(self):
        """Read potentiometer and apply throttle if lever 22 is ON"""
        if not self.pico or not self.api:
            return
        
        # Check if throttle control lever (22) is ON
        throttle_enabled = self.leviers_map.get(22, None)
        if throttle_enabled and not throttle_enabled.is_pressed:
            # Lever OFF = cut throttle
            if self.throttle_last != 0.0:
                self.api.set_throttle_level(0.0)
                self.throttle_last = 0.0
            return
        
        # Read potentiometer from Pico (channel 0)
        throttle_normalized = self.pico.read_adc_normalized(0, smoothed=True)
        
        if throttle_normalized is not None:
            # Apply deadzone
            if throttle_normalized < (THROTTLE_DEADZONE / 100.0):
                throttle_normalized = 0.0
            elif throttle_normalized > (1.0 - THROTTLE_DEADZONE / 100.0):
                throttle_normalized = 1.0
            
            # Only update if change is significant
            change = abs(throttle_normalized - self.throttle_last)
            if change > 0.01:  # 1% change threshold
                self.api.set_throttle_level(throttle_normalized)
                self.throttle_last = throttle_normalized
    
    def _update_led_feedback(self):
        """Update LED feedback based on vessel state"""
        if not self.connected:
            return
        
        # Update green LEDs: SAS (18) and RCS (12)
        self._update_led_sas_rcs()
        
        # Update red LEDs: Stage indicators (24, 27, 25, 21)
        self._update_led_stages()
    
    def _update_led_sas_rcs(self):
        """Update green LEDs based on SAS/RCS state from API"""
        try:
            # LED 18 = SAS
            if 18 in self.led_vertes_map:
                if self.api.cached_sas_state:
                    if not self.led_states.get("green_18", False):
                        self.led_vertes_map[18].on()
                        self.led_states["green_18"] = True
                else:
                    if self.led_states.get("green_18", False):
                        self.led_vertes_map[18].off()
                        self.led_states["green_18"] = False
            
            # LED 12 = RCS  
            if 12 in self.led_vertes_map:
                if self.api.cached_rcs_state:
                    if not self.led_states.get("green_12", False):
                        self.led_vertes_map[12].on()
                        self.led_states["green_12"] = True
                else:
                    if self.led_states.get("green_12", False):
                        self.led_vertes_map[12].off()
                        self.led_states["green_12"] = False
        
        except Exception as e:
            pass  # API not ready yet
    
    def _update_led_stages(self):
        """
        Update red LEDs for stage indicators
        LED on = stage present
        LED blink = stage present but fuel < 15%
        LED off = stage detached
        """
        try:
            # Map: LED pin -> stage index
            led_to_stage = {
                24: 0,  # Booster
                27: 1,  # Stage 1
                25: 2,  # Stage 2
                21: 3   # Stage 3
            }
            
            for led_pin, stage_idx in led_to_stage.items():
                if led_pin not in self.led_rouges_map:
                    continue
                
                # Check if stage still has mass (not detached)
                # For now, just turn on if API is connected
                # In future: check vessel.parts for stage presence
                
                try:
                    # Get fuel level for this LED
                    fuel_percent = self.api.liquid_fuel_percent
                    
                    if fuel_percent is not None and fuel_percent < 15.0:
                        # Blink pattern for low fuel
                        elapsed = int(time.time() * 1000) % 1000
                        if elapsed < 500:
                            self.led_rouges_map[led_pin].on()
                        else:
                            self.led_rouges_map[led_pin].off()
                    else:
                        # Normal: just on
                        self.led_rouges_map[led_pin].on()
                        self.led_states[f"red_{led_pin}"] = True
                
                except:
                    # Just turn on for now
                    self.led_rouges_map[led_pin].on()
        
        except Exception as e:
            pass  # API not ready yet
    
    def cleanup(self):
        """Turn off all LEDs and close connections"""
        try:
            for led in self.led_rouges_map.values():
                led.off()
            for led in self.led_vertes_map.values():
                led.off()
            print("✓ GPIO cleanup - LEDs éteintes")
        except Exception as e:
            print(f"✗ Erreur cleanup GPIO: {e}")
    
    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.cleanup()
        except:
            pass


# Keep old GPIO class for backward compatibility
GPIO = GPIOManager

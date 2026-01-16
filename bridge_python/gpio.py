from gpiozero import LED, Button
from gpiozero.pins.pigpio import PiGPIOFactory
from config import RASPI_IP
import picod
import time

# ==================== PICO CLASS ====================

class PICO:
    """
    PICO class for reading Pico sensors via network (socat redirection)
    Requires on Raspi: sudo apt install socat
    Command: socat TCP-LISTEN:12345,reuseaddr,fork FILE:/dev/ttyACM0,raw,echo=0
    """
    
    def __init__(self, pico_host=RASPI_IP, pico_port=12345):
        """Initialize Pico connection via network socket"""
        self.pico_host = pico_host
        self.pico_port = pico_port
        # Utiliser le lien PTY local créé par socat
        self.device_url = "/tmp/pico_remote"
        
        try:
            self.pico = picod.pico(device=self.device_url)
            if self.pico.connected:
                self.pico.reset()
                print(f"✓ Pico initialisé via {self.device_url}")
            else:
                print(f"✗ Pico non connecté sur {self.device_url}")
                self.pico = None
        except Exception as e:
            print(f"✗ Erreur connexion Pico: {e}")
            self.pico = None
    
    def read_adc(self, channel):
        """Read ADC value from Pico (0-4095)"""
        if not self.pico or not self.pico.connected:
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
    
    def close(self):
        """Close Pico connection"""
        if self.pico:
            try:
                self.pico.close()
                print("Pico connection fermée")
            except:
                pass


# ==================== GPIO CLASS ====================

class GPIO:
    """
    GPIO class for controlling KSP via Raspberry Pi pins with kRPC integration
    """
    
    def __init__(self, api=None, enable_pico=False):
        """Initialize GPIO with optional API reference for kRPC integration"""
        self.api = api
        
        # ==================== PICO SETUP ====================
        self.pico = None
        if enable_pico:
            self.pico = PICO(pico_host=RASPI_IP)
        
        # ==================== REMOTE GPIO SETUP ====================
        self.remote_factory = PiGPIOFactory(host=RASPI_IP)
        
        # ==================== LED PIN MAPPINGS ====================
        self.led_rouges_pins = [24, 27, 25, 21]
        self.led_vertes_pins = [18, 12]
        
        # ==================== BUTTON PIN MAPPINGS ====================
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
            23: "STAGE", #BOOSTERS
            8: "STAGE", #STAGE 1
            4: "STAGE", #STAGE 2
            19: "STAGE" #STAGE 3
        }
        
        # Boutons avec LED (mapping GPIO bouton -> GPIO LED)
        self.bouton_led_map = {
            23: 24,  # Boosters -> LED rouge 1
            8: 27,   # Stage 1 -> LED rouge 2
            4: 25,   # Stage 2 -> LED rouge 3
            19: 21   # Stage 3 -> LED rouge 4
        }
        
        # ==================== SETUP ====================
        # Initialisation des LEDs rouges
        self.led_rouges = {pin: LED(pin, pin_factory=self.remote_factory) for pin in self.led_rouges_pins}
        
        # Initialisation des LEDs vertes
        self.led_vertes = {pin: LED(pin, pin_factory=self.remote_factory) for pin in self.led_vertes_pins}
        
        # Initialisation des leviers (continuellement actifs)
        self.leviers = {}
        for pin, action in self.leviers_pins.items():
            self.leviers[pin] = Button(pin, pull_up=True, pin_factory=self.remote_factory)
        
        # Initialisation des boutons (momentary)
        self.boutons = {}
        for pin, action in self.boutons_pins.items():
            self.boutons[pin] = Button(pin, pull_up=True, pin_factory=self.remote_factory)
        
        # États précédents (anti-spam / détection changement)
        self.etat_prec_leviers = {pin: False for pin in self.leviers_pins.keys()}
        self.etat_prec_boutons = {pin: False for pin in self.boutons_pins.keys()}
        
        print(f"✓ GPIO initialisé - Connecté à {RASPI_IP}")
    
    def update(self):
        """Update GPIO inputs and process kRPC commands"""
        if not self.api:
            return
        
        # ---------- Boutons avec LED: Contrôle et affichage LED ----------
        for bouton, led in self.bouton_led_map.items():
            if self.boutons[bouton].is_pressed:
                self.led_rouges[led].on()
            else:
                self.led_rouges[led].off()
        
        # ---------- Leviers (continuous state) ----------
        for i, (pin, action) in enumerate(self.leviers_pins.items()):
            etat = self.leviers[pin].is_pressed
            
            # Affichage LED verte pour les leviers
            if i < len(self.led_vertes_pins):
                led_pin = self.led_vertes_pins[i]
                if etat:
                    self.led_vertes[led_pin].on()
                else:
                    self.led_vertes[led_pin].off()
            
            # Détection changement d'état pour kRPC
            if etat != self.etat_prec_leviers[pin]:
                print(f"[LEVIER] GPIO {pin} ({action}): {'ACTIVÉ' if etat else 'DÉSACTIVÉ'}")
                
                if action == "SAS":
                    self.api.set_stability_assistance(etat)
                elif action == "RCS":
                    self.api.set_reaction_control(etat)
                elif action == "THROTTLE_CONTROL":
                    # Pin 22 active le mode de contrôle du throttle
                    pass
                
                self.etat_prec_leviers[pin] = etat
        
        # ---------- Boutons sans LED (momentary press) ----------
        for pin, action in self.boutons_pins.items():
            # Ignorer les boutons avec LED (déjà traités)
            if pin in self.bouton_led_map:
                continue
            
            etat = self.boutons[pin].is_pressed
            
            # Détecte la transition LOW (appui)
            if etat and not self.etat_prec_boutons[pin]:
                print(f"[BOUTON] GPIO {pin} ({action}): APPUYÉ")
                
                if action == "HEAT_SHIELD":
                    self.api.deploy_heat_shield()
                elif action == "PARACHUTE":
                    self.api.deploy_parachute()
                elif action == "LANDING_GEAR":
                    self.api.toggle_landing_gear()
                elif action == "TOGGLE_MAP":
                    print("[MAP] Basculer affichage carte/véhicule")
                elif action == "ENGINE_START":
                    self.api.start_engines()
                elif action == "FAIRING":
                    self.api.deploy_fairing()
            
            self.etat_prec_boutons[pin] = etat
        
        # ---------- Boutons avec LED (momentary press) ----------
        for pin, action in self.bouton_led_map.items():
            etat = self.boutons[pin].is_pressed
            
            # Détecte la transition LOW (appui)
            if etat and not self.etat_prec_boutons[pin]:
                print(f"[BOUTON] GPIO {pin} ({action}): APPUYÉ")
                
                if action == "STAGE":
                    self.api.stage()
            
            self.etat_prec_boutons[pin] = etat
    
    def cleanup(self):
        """Turn off all LEDs and close connections"""
        for led in self.led_rouges.values():
            led.off()
        for led in self.led_vertes.values():
            led.off()
        if self.pico:
            self.pico.close()
        print("GPIO cleanup - LEDs éteintes")


# ==================== MAIN ====================

if __name__ == "__main__":
    print("GPIO module - use with main.py")
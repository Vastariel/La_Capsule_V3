from gpiozero import LED, Button
from gpiozero.pins.pigpio import PiGPIOFactory
import time
import threading

# ==================== REMOTE GPIO SETUP ====================

# Adresse IP du Raspberry Pi distant (à adapter)
REMOTE_IP = "192.168.1.56"
remote_factory = PiGPIOFactory(host=REMOTE_IP)

# ==================== GPIO ====================

led_rouges_pins = [24, 27, 25, 21]
led_vertes_pins = [18, 12]

# Leviers : 17 fonctionne avec pull-up interne
leviers_pins = [16, 26, 22]

boutons_pins = [23, 8, 4, 19, 6, 13, 20, 11, 7, 5]

# Boutons avec LED
bouton_led_map = {
    23: 24,
    8: 27,
    4: 25,
    19: 21
}

# Boutons sans LED (console uniquement)
boutons_console_pins = [6, 13, 20, 11, 7, 5]

# ==================== SETUP ====================

# Initialisation des LEDs
led_rouges = {pin: LED(pin, pin_factory=remote_factory) for pin in led_rouges_pins}
led_vertes = {pin: LED(pin, pin_factory=remote_factory) for pin in led_vertes_pins}

# Initialisation des boutons (pull_up=True par défaut)
boutons = {pin: Button(pin, pull_up=True, pin_factory=remote_factory) for pin in boutons_pins}
leviers = {pin: Button(pin, pull_up=True, pin_factory=remote_factory) for pin in leviers_pins}

# États précédents (anti-spam / détection changement)
etat_prec_boutons = {btn: False for btn in boutons_console_pins}
etat_prec_leviers = {lev: False for lev in leviers_pins}

# ==================== LOGIQUE ====================

def test_entrees():
    print("=== TEST BOUTONS & LEVIERS (REMOTE GPIO) ===")
    print(f"- Connecté au Raspberry Pi: {REMOTE_IP}")
    print("- Boutons : message à l'appui")
    print("- Leviers : message au changement d'état")
    print("Ctrl+C pour quitter\n")

    try:
        while True:
            # ---------- Boutons avec LED ----------
            for bouton, led in bouton_led_map.items():
                if boutons[bouton].is_pressed:
                    led_rouges[led].on()
                else:
                    led_rouges[led].off()

            # ---------- Boutons sans LED ----------
            for btn in boutons_console_pins:
                etat = boutons[btn].is_pressed
                if etat and not etat_prec_boutons[btn]:
                    print(f"[BOUTON] GPIO {btn} appuyé")
                etat_prec_boutons[btn] = etat

            # ---------- Leviers ----------
            for i, lev in enumerate(leviers_pins):
                etat = leviers[lev].is_pressed

                # LED verte associée si existante
                if i < len(led_vertes_pins):
                    led_pin = led_vertes_pins[i]
                    if etat:
                        led_vertes[led_pin].on()
                    else:
                        led_vertes[led_pin].off()

                # Détection changement d'état → console
                if etat != etat_prec_leviers[lev]:
                    if etat:
                        print(f"[LEVIER] GPIO {lev} ACTIVÉ")
                    else:
                        print(f"[LEVIER] GPIO {lev} DÉSACTIVÉ")

                etat_prec_leviers[lev] = etat

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nFin du test")

    finally:
        # Éteindre toutes les LEDs
        for led in led_rouges.values():
            led.off()
        for led in led_vertes.values():
            led.off()
        print("GPIO réinitialisées")

# ==================== MAIN ====================

if __name__ == "__main__":
    test_entrees()
import RPi.GPIO as GPIO
import time
import threading
import serial

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# ==================== GPIO ====================

led_rouges = [24, 27, 25, 21]
led_vertes = [18, 12]

# Leviers : 17 fonctionne avec pull-up interne
leviers = [16, 26, 22]

boutons = [23, 8, 4, 19, 6, 13, 20, 11, 7, 5]

# Boutons avec LED
bouton_led_map = {
    23: 24,
    8: 27,
    4: 25,
    19: 21
}

# Boutons sans LED (console uniquement)
boutons_console = [6, 13, 20, 11, 7, 5]

# ==================== PICO ====================

PICO_PORT = "/dev/ttyACM0"   # à adapter si besoin
PICO_BAUDRATE = 115200

pico_data = None
pico_running = True

# ==================== SETUP ====================

for led in led_rouges + led_vertes:
    GPIO.setup(led, GPIO.OUT)
    GPIO.output(led, GPIO.LOW)

# Pull-up interne pour boutons et leviers → évite broches flottantes
for pin in boutons + leviers:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# États précédents (anti-spam / détection changement)
etat_prec_boutons = {btn: GPIO.HIGH for btn in boutons_console}
etat_prec_leviers = {lev: GPIO.HIGH for lev in leviers}

# ==================== PICO THREAD ====================

def lire_pico():
    global pico_data, pico_running
    try:
        ser = serial.Serial(PICO_PORT, PICO_BAUDRATE, timeout=1)
        print("[PICO] Connectée")

        while pico_running:
            ligne = ser.readline().decode("utf-8", errors="ignore").strip()
            if ligne:
                pico_data = ligne
                print(f"[PICO] {ligne}")

        ser.close()

    except Exception as e:
        print(f"[PICO] ERREUR : {e}")

# ==================== LOGIQUE ====================

def test_entrees():
    print("=== TEST BOUTONS & LEVIERS ===")
    print("- Boutons : message à l'appui")
    print("- Leviers : message au changement d'état")
    print("Ctrl+C pour quitter\n")

    # Lancement lecture Pico
    thread_pico = threading.Thread(target=lire_pico, daemon=True)
    thread_pico.start()

    try:
        while True:
            # ---------- Boutons avec LED ----------
            for bouton, led in bouton_led_map.items():
                GPIO.output(led, GPIO.input(bouton) == GPIO.LOW)

            # ---------- Boutons sans LED ----------
            for btn in boutons_console:
                etat = GPIO.input(btn)
                if etat == GPIO.LOW and etat_prec_boutons[btn] == GPIO.HIGH:
                    print(f"[BOUTON] GPIO {btn} appuyé")
                etat_prec_boutons[btn] = etat

            # ---------- Leviers ----------
            for i, lev in enumerate(leviers):
                etat = GPIO.input(lev)

                # LED verte associée si existante
                if i < len(led_vertes):
                    GPIO.output(led_vertes[i], etat == GPIO.LOW)

                # Détection changement d'état → console
                if etat != etat_prec_leviers[lev]:
                    if etat == GPIO.LOW:
                        print(f"[LEVIER] GPIO {lev} ACTIVÉ")
                    else:
                        print(f"[LEVIER] GPIO {lev} DÉSACTIVÉ")

                etat_prec_leviers[lev] = etat

            # ---------- Données Pico ----------
            
            if pico_data:
                # exemple d'exploitation
                if pico_data == "ALERTE":
                    GPIO.output(led_rouges[0], GPIO.HIGH)

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nFin du test")

    finally:
        GPIO.cleanup()
        print("GPIO réinitialisées")

# ==================== MAIN ====================

if __name__ == "__main__":
    test_entrees()
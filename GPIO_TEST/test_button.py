import RPi.GPIO as GPIO
import time

LED_CHAIN_PIN = 17  # GPIO qui alimente la LED + bouton en série

GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_CHAIN_PIN, GPIO.OUT)

print("La LED sera alimentée tant que le bouton est fermé (GPIO 17 HIGH). Ctrl+C pour quitter.")

try:
    while True:
        GPIO.output(LED_CHAIN_PIN, GPIO.HIGH)  # Tente d’alimenter la LED
        time.sleep(0.1)
        # Tu peux ici ajouter une lecture par une autre broche pour savoir si la LED est réellement allumée (optionnel)
except KeyboardInterrupt:
    print("\nArrêt du programme.")

finally:
    GPIO.output(LED_CHAIN_PIN, GPIO.LOW)
    GPIO.cleanup()

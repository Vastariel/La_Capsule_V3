import serial
import RPi.GPIO as GPIO
import time

# --- Setup GPIO pour PWM sur GPIO12 (physique pin 32) ---
LED_PIN = 12
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
pwm = GPIO.PWM(LED_PIN, 1000)  # 1kHz
pwm.start(0)

# --- Connexion série avec la Pico ---
ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)

try:
    while True:
        line = ser.readline().decode().strip()
        if line.isdigit():
            val = int(line)
            # Convertir 0–65535 → 0–100 %
            duty = min(100, max(0, int(val / 65535 * 100)))
            print(f"Valeur : {val} → PWM : {duty}%")
            pwm.ChangeDutyCycle(duty)
        time.sleep(0.02)

except KeyboardInterrupt:
    print("Arrêt du programme.")
    pwm.stop()
    GPIO.cleanup()
    ser.close()

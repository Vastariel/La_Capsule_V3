import serial
import time

PICO_PORT = "/dev/ttyACM0"   # Vérifie avec `ls /dev/ttyACM*`
BAUDRATE = 115200

def main():
    try:
        with serial.Serial(PICO_PORT, BAUDRATE, timeout=1) as ser:
            print("Lecture du potentiomètre Pico... Ctrl+C pour arrêter")
            while True:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if line.startswith("POT="):
                    value = int(line.split("=")[1])
                    percent = int(value * 100 / 65535)
                    print(f"Valeur ADC : {value} ({percent}%)")
                time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nProgramme interrompu")
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    main()

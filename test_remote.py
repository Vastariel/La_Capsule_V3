from gpiozero import LED
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep

# On définit l'adresse IP du Raspberry Pi distant
remote_factory = PiGPIOFactory(host='192.168.1.42')

# On initialise le composant en lui passant la "factory" distante
led = LED(17, pin_factory=remote_factory)

print("Allumage de la LED à distance...")
while True:
    led.on()
    sleep(1)
    led.off()
    sleep(1)
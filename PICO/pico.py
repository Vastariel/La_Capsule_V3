from machine import ADC
import time
import sys

adc = ADC(26)

while True:
    value = adc.read_u16()
    print(value)  # Envoie sur le port série USB
    time.sleep(0.1)
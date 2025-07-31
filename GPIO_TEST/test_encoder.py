import RPi.GPIO as GPIO
import time

# Pins
CLK = 22
DT = 18
SW = 27

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(CLK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(DT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(SW, GPIO.IN, pull_up_down=GPIO.PUD_UP)

menu_items = ['Pause', 'Conseils', 'En savoir plus', 'Relancer la mission']
menu_index = 0
button_pressed = False
last_button_press_time = 0

def print_menu():
    print(f">>> Current screen: {menu_items[menu_index]}")

def rotary_callback(channel):
    global menu_index
    clk_state = GPIO.input(CLK)
    dt_state = GPIO.input(DT)
    
    if clk_state == 1:  # front montant
        if dt_state == 0:
            menu_index = (menu_index + 1) % len(menu_items)
        else:
            menu_index = (menu_index - 1) % len(menu_items)
        print_menu()

def button_callback(channel):
    global button_pressed, last_button_press_time
    if GPIO.input(SW) == 0:  # bouton appuyé (pull-up)
        button_pressed = True
        last_button_press_time = time.time()
        print(f"Button pressed on screen: {menu_items[menu_index]}")
        print("Waiting 1 second...")
        time.sleep(1)
        print("Returning to previous menu or waiting for next rotation.")
        button_pressed = False

# Attach event detection
GPIO.add_event_detect(CLK, GPIO.RISING, callback=rotary_callback, bouncetime=50)
GPIO.add_event_detect(SW, GPIO.FALLING, callback=button_callback, bouncetime=200)

try:
    print_menu()
    while True:
        time.sleep(0.1)  # boucle principale très simple

except KeyboardInterrupt:
    print("\nExiting program.")

finally:
    GPIO.cleanup()

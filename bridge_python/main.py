#!/usr/bin/python
#coding: utf-8
from api import API
from gpio import GPIO
from server import init_server, start_server
import time
from threading import Thread

if __name__=="__main__" : 
    api = API('Bridge vers la raspi')
    api.connect()
    api.start()
    print('✓ server KRPC connecté et en fonctionnement')
    
    # Initialize GPIO with API reference and Pico support
    gpio = GPIO(api=api, enable_pico=True)
    
    # Initialize and start WebSocket server in background
    init_server(api)
    server_thread = Thread(target=start_server, daemon=True)
    server_thread.start()
    print('✓ Serveur WebSocket démarré')
    
    try:
        while True:
            gpio.update()
            time.sleep(0.05)
    
    except KeyboardInterrupt:
        print("\nExtinction...")
    
    finally:
        # Stop API thread cleanly
        api.stop_telemetry()
        api.join()
        
        # Cleanup GPIO
        gpio.cleanup()
        
        print('disconnected')
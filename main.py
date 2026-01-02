#!/usr/bin/python
#coding: utf-8
from api import API
from gpio import GPIO
import time

if __name__=="__main__" : 
    api = API('Bridge vers la raspi')
    api.connect()
    api.start()
    print('API connected and running')
    
    # Initialize GPIO with API reference
    gpio = GPIO(api=api)
    print('GPIO connected')
    
    try:
        while True:
            gpio.update()
            time.sleep(0.05)
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    
    finally:
        # Stop API thread cleanly
        api.stop_telemetry()
        api.join()
        
        # Cleanup GPIO
        gpio.cleanup()
        
        print('disconnected')
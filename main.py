#!/usr/bin/python
#coding: utf-8
from api import API
from config import *
#from display import Display
import time


if __name__=="__main__" : 
    api = API()
    api.connect()
    api.start()
    print('API connected and running')

    # Start display in main thread (pygame must run in main thread on many platforms)
    #display = Display(api)
    # Run display until any key is pressed
    #display.run()

    # After display loop exits, stop API thread cleanly
    api.stop_telemetry()
    api.join()
    print('disconnected')
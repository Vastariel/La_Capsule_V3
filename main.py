#!/usr/bin/python
#coding: utf-8
from api import API
from config import *

if __name__=="__main__" : 
    api = API('Raspi-4')
    api.connect()
    api.start()
    print('API connected and running')

    # After display loop exits, stop API thread cleanly
    api.stop_telemetry()
    api.join()
    print('disconnected')
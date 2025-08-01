#!/usr/bin/python
#coding: utf-8
from api import API
from config import *
import time


if __name__=="__main__" : 
    api = API()
    api.connect()
    api.start()
    print('connected')
    time.sleep(3)
    api.stop_telemetry()
    api.join()
    print('deconnected')


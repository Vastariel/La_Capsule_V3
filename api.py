#!/usr/bin/python
#coding: utf-8

from threading import Thread
import time
from typing import List
from config import *

import krpc
import pygame

from config import *


# Refresh Rate Constants
REFRESH_CRITICAL  = 1   # Every frame - critical data
REFRESH_IMPORTANT = 5   # Every 5 frames - important data  
REFRESH_NORMAL    = 10  # Every 10 frames - normal data
REFRESH_MAX       = 12  # Maximum number of refresh rate slots

#The API class launch a thread that follow the status of the KSP game.
#Since calls to KRPC take lots of time, we need to desynchronise it from the pygame loop if we want to acheive 30+ fps

class API(Thread):
    """
    API Thread class for KSP telemetry data collection.
    
    This class runs in a separate thread to collect data from Kerbal Space Program
    via kRPC without blocking the main pygame loop for optimal performance.
    """  
    __slots__ = (
        # Thread control
        'is_running', 'frame_counter', 'target_fps', 'clock',
        # Data management  
        'data_sources_by_rate',
        # Telemetry values
        'altitude', 'speed', 'g_force', 'temperature',
        'apoapsis', 'apoapsis_time', 'periapsis', 'periapsis_time',
        # Control cache
        'cached_sas_state', 'cached_rcs_state', 'cached_throttle_state',
        # kRPC objects
        'con', 'vessel', 'camera', 'control', 'flight', 'orbit', 'resources'
    )
    
    def __init__(self) -> None:
        """
        Initialize the API thread with specified FPS.
        """
        #-----Thread Initialization-----#
        Thread.__init__(self)
        
        #-----Thread Control Variables-----#
        self.is_running: bool = False  # Thread execution state
        
        #-----Timing and FPS Control-----#
        self.frame_counter: int = 1                    # Current frame number (1 to fps)
        self.target_fps: int    = FPS                  # Target frames per second
        self.clock              = pygame.time.Clock()  # Pygame clock for FPS control
        
        #-----Data Management-----#
        self.data_sources_by_rate: List[List] = [[] for _ in range(REFRESH_MAX)]  # Data sources grouped by refresh rate
        
        #-----Current Telemetry Values (direct access for performance)-----#
        self.altitude: float | None       = None     # Surface altitude in meters
        self.speed: float | None          = None     # Current velocity in m/s
        self.g_force: float | None        = None     # G-force experienced
        self.temperature: float | None    = None     # Air temperature in Kelvin
        self.apoapsis: float | None       = None     # Highest orbit point in meters
        self.apoapsis_time: float | None  = None     # Time to apoapsis in seconds
        self.periapsis: float | None      = None     # Lowest orbit point in meters
        self.periapsis_time: float | None = None     # Time to periapsis in seconds
        
        #-----Control State Cache (for performance)-----#
        self.cached_sas_state: bool       = False        # SAS (Stability Augmentation System) state
        self.cached_rcs_state: bool       = True         # RCS (Reaction Control System) state  
        self.cached_throttle_state: float = 0.0    # Throttle level (0.0 to 1.0)

        
        #-----Initialize Data Sources-----#
        # Critical data - updated every frame (direct assignment for max speed)
        self.data_sources_by_rate[REFRESH_CRITICAL] = [
            (self.get_altitude, lambda v: setattr(self, 'altitude', v)),
            (self.get_speed, lambda v: setattr(self, 'speed', v))
        ]
        
        # Important data - updated every 5 frames
        self.data_sources_by_rate[REFRESH_IMPORTANT] = [
            (self.get_g_force, lambda v: setattr(self, 'g_force', v)),
            (self.get_temp, lambda v: setattr(self, 'temperature', v))
        ]
        
        # Normal data - updated every 10 frames
        self.data_sources_by_rate[REFRESH_NORMAL] = [
            (self.get_apoapsis, lambda v: setattr(self, 'apoapsis', v)),
            (self.get_apoapsis_time, lambda v: setattr(self, 'apoapsis_time', v)),
            (self.get_periapsis, lambda v: setattr(self, 'periapsis', v)),
            (self.get_periapsis_time, lambda v: setattr(self, 'periapsis_time', v))
        ]

    def connect(self, ip: str = KSP_IP) -> None:
        """Establish connection to KSP and initialize game objects"""
        self.con = krpc.connect("Raspi_4", ip, RPC_PORT)  # Main kRPC connection
        
        # Game Objects
        self.vessel = self.con.space_center.active_vessel  # Currently active vessel
        self.camera = self.con.space_center.camera         # Game camera object
        
        # Control Interfaces
        self.control    = self.vessel.control     # Vessel control interface
        self.flight     = self.vessel.flight(self.vessel.orbit.body.reference_frame)    # Flight data interface
        self.orbit      = self.vessel.orbit       # Orbital data interface
        self.resources  = self.vessel.resources   # Resource management interface
    
    def update_telemetry_data(self) -> None:
        """Update all telemetry data sources using data_sources_by_rate"""
        frame_counter = self.frame_counter
        
        # Loop through all refresh rates
        for refresh_rate, data_sources in enumerate(self.data_sources_by_rate):
            if refresh_rate != 0 and len(data_sources) > 0:  # Skip empty rates
                if frame_counter % refresh_rate == 0:  # Time to update this rate?
                    for get_method, set_method in data_sources:
                        try:
                            value = get_method()  # Call get_altitude(), get_speed(), etc.
                            set_method(value)     # Call lambda to set the attribute
                        except:
                            pass 

        # Update frame counter
        self.frame_counter = 1 if frame_counter == self.target_fps else frame_counter + 1

    def run(self) -> None:
        """Thread entry point"""
        self.is_running = True
        
        clock = self.clock
        target_fps = self.target_fps
        update_method = self.update_telemetry_data
        
        while self.is_running:
            update_method()
            clock.tick(target_fps)

    def stop_telemetry(self) -> None:
        """Stop the telemetry thread safely"""
        self.is_running = False

    #-----GET_VALUE METHODS-----#
    def get_current_fps(self) -> str:
        """Get current FPS as formatted string"""
        return str(round(self.clock.get_fps(), 1))
    
    def get_altitude(self) -> float:
        """Get current surface altitude in meters"""
        return self.flight.surface_altitude
    
    def get_speed(self) -> float:
        """Get current velocity in m/s"""
        return self.flight.speed
    
    def get_g_force(self) -> float:
        """Get current G-force experienced by the vessel"""
        return self.flight.g_force
    
    def get_temp(self) -> float:
        """Get static air temperature in Kelvin"""
        return self.flight.static_air_temperature
    
    def get_apoapsis(self) -> float:
        """Get apoapsis altitude in meters (highest point of orbit)"""
        return self.orbit.apoapsis
    
    def get_apoapsis_time(self) -> float:
        """Get time until apoapsis in seconds"""
        return self.orbit.time_to_apoapsis
    
    def get_periapsis(self) -> float:
        """Get periapsis altitude in meters (lowest point of orbit)"""
        return self.orbit.periapsis
    
    def get_periapsis_time(self) -> float:
        """Get time until periapsis in seconds"""
        return self.orbit.time_to_periapsis
    
    #-----VESSEL CONTROL METHODS-----# not finished
    
    def set_stability_assistance(self, enabled: bool) -> None:
        """Set Stability Augmentation System (SAS) state"""
        if self.cached_sas_state != enabled:
            self.control.sas = enabled
            self.cached_sas_state = enabled
    
    def set_reaction_control(self, enabled: bool) -> None:
        """Set Reaction Control System (RCS) state"""
        if self.cached_rcs_state != enabled:
            self.control.rcs = enabled
            self.cached_rcs_state = enabled
    
    def set_throttle_level(self, throttle_value: float) -> None:
        """Set throttle level (0.0 to 1.0)"""
        if self.cached_throttle_state != throttle_value:
            self.control.throttle = throttle_value
            self.cached_throttle_state = throttle_value



if __name__=="__main__" : 
    api = API()
    api.connect()
    api.start()
    try:
        while True:
            print(
                f"Altitude : {api.altitude} m | "
                f"Vitesse : {api.speed} m/s | "
                f"Force G : {api.g_force} | "
                f"Température : {api.temperature} K | "
                f"Apoapsis : {api.apoapsis} m | "
                f"Temps vers Apoapsis : {api.apoapsis_time} s | "
                f"Périapsis : {api.periapsis} m | "
                f"Temps vers Périapsis : {api.periapsis_time} s"
            )
            time.sleep(1)
    except KeyboardInterrupt:
        api.stop_telemetry()
        api.join()
        print('disconnected')
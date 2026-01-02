#!/usr/bin/python
#coding: utf-8

from threading import Thread
import time
import random
from typing import List

import krpc

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
        'is_running', 'frame_counter', 'target_fps', 'last_tick',
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
    
    def __init__(self,name) -> None:
        """
        Initialize the API thread with specified FPS.
        """
        #-----Thread Initialization-----#
        Thread.__init__(self)
        
        self.name = name
        #-----Thread Control Variables-----#
        self.is_running: bool = False  # Thread execution state
        
        #-----Timing and FPS Control-----#
        self.frame_counter: int = 1                    # Current frame number (1 to fps)
        self.target_fps: int    = FPS                  # Target frames per second
        self.last_tick: float   = time.perf_counter()  # Last tick timestamp
        
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
        self.con = krpc.connect(
            name=self.name,
            address=ip,
            rpc_port=RPC_PORT,
            stream_port=STREAM_PORT
        )  # Main kRPC connection

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
        
        target_fps = self.target_fps
        frame_duration = 1.0 / target_fps
        update_method = self.update_telemetry_data
    
        while self.is_running:
            start_time = time.perf_counter()
            update_method()
            elapsed = time.perf_counter() - start_time
            sleep_time = frame_duration - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def stop_telemetry(self) -> None:
        """Stop the telemetry thread safely"""
        self.is_running = False

    #-----GET_VALUE METHODS-----#
    def get_current_fps(self) -> str:
        """Get current FPS as string"""
        return f"{self.target_fps}"
    
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

    #========= ajout test par Camille =========#
    def deploy_heat_shield(self) -> None:
        """Deploy heat shield"""
        try:
            # Find and deploy heat shield
            for part in self.vessel.parts.all:
                if part.name == 'HeatShield' or 'heatshield' in part.name.lower():
                    part.decouple()
            print("[KSP] Bouclier thermique déployé")
        except Exception as e:
            print(f"[KSP] Erreur déploiement bouclier: {e}")
    
    def deploy_parachute(self) -> None:
        """Deploy parachute"""
        try:
            self.control.parachutes = True
            print("[KSP] Parachute déployé")
        except Exception as e:
            print(f"[KSP] Erreur déploiement parachute: {e}")
    
    def toggle_landing_gear(self) -> None:
        """Toggle landing gear"""
        try:
            self.control.gear = not self.control.gear
            state = "déployé" if self.control.gear else "rétracté"
            print(f"[KSP] Train d'atterrissage {state}")
        except Exception as e:
            print(f"[KSP] Erreur train d'atterrissage: {e}")
    
    def start_engines(self) -> None:
        """Start all engines"""
        try:
            self.control.throttle = 0.0
            print("[KSP] Moteurs démarrés")
        except Exception as e:
            print(f"[KSP] Erreur démarrage moteurs: {e}")
    
    def deploy_fairing(self) -> None:
        """Deploy fairing (coiffe)"""
        try:
            for part in self.vessel.parts.all:
                if 'fairing' in part.name.lower():
                    part.jettison()
            print("[KSP] Coiffe éjectée")
        except Exception as e:
            print(f"[KSP] Erreur éjection coiffe: {e}")
    
    def stage(self) -> None:
        """Activate next stage"""
        try:
            self.control.activate_next_stage()
            print("[KSP] Étage déclenché")
        except Exception as e:
            print(f"[KSP] Erreur déclenchement étage: {e}")



if __name__=="__main__" : 
    api = API('Raspi-4')
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
            new_throttle = random.uniform(0, 100)
            api.set_throttle_level(new_throttle / 100)
            print(f"Throttle set to: {new_throttle:.2f}%")
            time.sleep(1)
    except KeyboardInterrupt:
        api.stop_telemetry()
        api.join()
        print('disconnected')
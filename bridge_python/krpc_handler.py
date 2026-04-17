#!/usr/bin/env python3
"""
KRPC Handler - Manages Kerbal Space Program connection via kRPC
Handles connection, reconnection logic, and telemetry collection
"""

import time
import krpc
from threading import Thread
from typing import Optional, Dict


class KRPCHandler:
    """Manages kRPC connection and telemetry data collection"""
    
    def __init__(self, name: str = "La_Capsule", host: str = "192.168.1.31", 
                 rpc_port: int = 50008, stream_port: int = 50001,
                 reconnect_timeout: int = 300):
        """Initialize KRPC connection handler
        
        Args:
            name: Connection name
            host: KSP PC IP address
            rpc_port: KRPC RPC port
            stream_port: KRPC stream port
            reconnect_timeout: Reconnection timeout in seconds (300 = 5 min)
        """
        self.name = name
        self.host = host
        self.rpc_port = rpc_port
        self.stream_port = stream_port
        self.reconnect_timeout = reconnect_timeout
        
        # Connection state
        self.connection = None
        self.connected = False
        self.last_connection_attempt = 0
        self.connection_thread = None
        
        # Game objects
        self.vessel = None
        self.control = None
        self.flight = None
        self.orbit = None
        self.resources = None
        self.camera = None
        
        # Telemetry data
        self.telemetry = {
            'altitude': 0,
            'speed': 0,
            'vertical_speed': 0,
            'g_force': 0,
            'temperature': 0,
            'apoapsis': 0,
            'periapsis': 0,
            'apoapsis_time': 0,
            'periapsis_time': 0,
            'liquid_fuel_percent': 0,
            'monopropellant_percent': 0,
            'current_stage': 0,
            'engines_active': False,
        }
        
        # Control state cache
        self.sas_state = False
        self.rcs_state = False
        self.throttle_state = 0.0
    
    def connect(self) -> bool:
        """Attempt to connect to KRPC server
        
        Returns:
            True if connected, False otherwise
        """
        try:
            print(f"[KRPC] Connexion à {self.host}:{self.rpc_port}...", end=" ")
            self.connection = krpc.connect(
                name=self.name,
                address=self.host,
                rpc_port=self.rpc_port,
                stream_port=self.stream_port
            )
            
            # Get game objects
            space_center = self.connection.space_center
            self.vessel = space_center.active_vessel
            self.control = self.vessel.control
            self.flight = self.vessel.flight(self.vessel.orbit.body.reference_frame)
            self.orbit = self.vessel.orbit
            self.resources = self.vessel.resources
            self.camera = space_center.camera
            
            self.connected = True
            self.last_connection_attempt = time.time()
            print("✓ OK")
            return True
        
        except Exception as e:
            self.connected = False
            print(f"✗ Erreur: {e}")
            return False
    
    def reconnect_if_needed(self) -> bool:
        """Check if reconnection is needed and attempt it
        
        Returns:
            True if connected, False otherwise
        """
        if self.connected:
            # Verify connection is still alive
            try:
                _ = self.vessel.name
                return True
            except:
                print("[KRPC] Connexion perdue, reconnexion en cours...")
                self.connected = False
        
        # Check if it's time to retry
        elapsed = time.time() - self.last_connection_attempt
        if elapsed >= self.reconnect_timeout / 1000.0:  # Convert to seconds
            return self.connect()
        else:
            remaining = (self.reconnect_timeout - elapsed * 1000) / 1000
            if int(remaining) % 3 == 0 and int(remaining) != int(remaining + 0.1):  # Print every ~3 sec
                print(f"[KRPC] Attente connexion... (retry dans {int(remaining)}s)")
            return False
    
    def update_telemetry(self):
        """Update telemetry data from KRPC
        
        Should be called regularly to keep data current
        """
        if not self.connected:
            return
        
        try:
            self.telemetry['altitude'] = self.flight.surface_altitude
            self.telemetry['speed'] = self.flight.speed
            self.telemetry['vertical_speed'] = self.flight.vertical_speed
            self.telemetry['g_force'] = self.flight.g_force
            self.telemetry['temperature'] = self.flight.static_air_temperature
            self.telemetry['apoapsis'] = self.orbit.apoapsis
            self.telemetry['periapsis'] = self.orbit.periapsis
            self.telemetry['apoapsis_time'] = self.orbit.time_to_apoapsis
            self.telemetry['periapsis_time'] = self.orbit.time_to_periapsis
            self.telemetry['current_stage'] = self.control.current_stage
            self.telemetry['engines_active'] = self.control.throttle > 0.0
            
            # Calculate fuel percentages
            try:
                liquid = self.resources.get_resource('LiquidFuel')
                oxidizer = self.resources.get_resource('Oxidizer')
                mono = self.resources.get_resource('Monopropellant')
                
                total_fuel = 0
                max_fuel = 0
                if liquid:
                    total_fuel += liquid.amount
                    max_fuel += liquid.max
                if oxidizer:
                    total_fuel += oxidizer.amount
                    max_fuel += oxidizer.max
                
                self.telemetry['liquid_fuel_percent'] = (total_fuel / max_fuel * 100) if max_fuel > 0 else 0
                self.telemetry['monopropellant_percent'] = (mono.amount / mono.max * 100) if mono and mono.max > 0 else 0
            except:
                pass
        
        except Exception as e:
            print(f"[KRPC] Erreur update telemetry: {e}")
    
    # ===== CONTROL METHODS =====
    
    def set_throttle(self, value: float) -> None:
        """Set throttle level (0.0 to 1.0)"""
        if not self.connected:
            return
        try:
            self.control.throttle = max(0.0, min(1.0, value))
            self.throttle_state = self.control.throttle
        except Exception as e:
            print(f"[KRPC] Erreur throttle: {e}")
    
    def set_sas(self, enabled: bool) -> None:
        """Set SAS state"""
        if not self.connected:
            return
        try:
            self.control.sas = enabled
            self.sas_state = enabled
        except Exception as e:
            print(f"[KRPC] Erreur SAS: {e}")
    
    def set_rcs(self, enabled: bool) -> None:
        """Set RCS state"""
        if not self.connected:
            return
        try:
            self.control.rcs = enabled
            self.rcs_state = enabled
        except Exception as e:
            print(f"[KRPC] Erreur RCS: {e}")
    
    # ===== ACTION GROUP CONTROL =====
    
    def trigger_action_group(self, group: int) -> None:
        """Toggle action group"""
        if not self.connected:
            return
        try:
            self.control.toggle_action_group(group)
            print(f"[KSP] AG {group} déclenché")
        except Exception as e:
            print(f"[KRPC] Erreur AG {group}: {e}")
    
    def set_action_group(self, group: int, state: bool) -> None:
        """Set action group state"""
        if not self.connected:
            return
        try:
            self.control.set_action_group(group, state)
            print(f"[KSP] AG {group} = {state}")
        except Exception as e:
            print(f"[KRPC] Erreur AG {group}: {e}")
    
    def get_action_group(self, group: int) -> bool:
        """Get action group state"""
        if not self.connected:
            return False
        try:
            return self.control.get_action_group(group)
        except:
            return False
    
    # ===== CAMERA CONTROL =====
    
    def toggle_map_camera(self) -> None:
        """Toggle between map and automatic camera modes"""
        if not self.connected:
            return
        try:
            # CameraMode.map = 7, CameraMode.automatic = 0
            if self.camera.mode == 7:  # Map
                self.camera.mode = 0    # Automatic
                print("[KSP] Caméra: AUTO")
            else:
                self.camera.mode = 7    # Map
                print("[KSP] Caméra: CARTE")
        except Exception as e:
            print(f"[KRPC] Erreur caméra: {e}")
    
    def get_telemetry(self) -> Dict:
        """Get current telemetry snapshot"""
        return self.telemetry.copy()
    
    def disconnect(self) -> None:
        """Safely disconnect from KRPC"""
        try:
            if self.connection:
                self.connection.close()
            self.connected = False
            print("[KRPC] Déconnecté")
        except:
            pass

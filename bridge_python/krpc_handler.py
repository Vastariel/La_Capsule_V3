#!/usr/bin/env python3
"""
KRPC Handler - Connexion et télémétrie Kerbal Space Program via kRPC.

Gère la connexion (avec reconnexion périodique), la collecte de télémétrie,
les commandes (SAS, RCS, throttle, action groups, caméra) et le carburant
par étage.
"""

import time
from typing import Dict, List, Optional

import krpc


class KRPCHandler:
    """Connexion kRPC avec reconnexion automatique et télémétrie."""

    def __init__(
        self,
        name: str = "La_Capsule",
        host: str = "192.168.1.31",
        rpc_port: int = 50008,
        stream_port: int = 50001,
        reconnect_timeout_s: int = 5,
    ):
        self.name = name
        self.host = host
        self.rpc_port = rpc_port
        self.stream_port = stream_port
        self.reconnect_timeout_s = reconnect_timeout_s

        self.connection = None
        self.connected = False
        self.last_connection_attempt = 0.0

        self.vessel = None
        self.control = None
        self.flight = None
        self.orbit = None
        self.resources = None
        self.camera = None
        self.space_center = None

        self.telemetry: Dict = {
            "altitude": 0.0,
            "speed": 0.0,
            "vertical_speed": 0.0,
            "g_force": 0.0,
            "temperature": 0.0,
            "apoapsis": 0.0,
            "periapsis": 0.0,
            "apoapsis_time": 0.0,
            "periapsis_time": 0.0,
            "current_stage": 0,
            "engines_active": False,
            "stages": [],
        }

        self.sas_state = False
        self.rcs_state = False
        self.throttle_state = 0.0

    # ---- Connexion ---------------------------------------------------

    def connect(self) -> bool:
        self.last_connection_attempt = time.time()
        try:
            print(f"[KRPC] Connexion à {self.host}:{self.rpc_port}...", end=" ", flush=True)
            self.connection = krpc.connect(
                name=self.name,
                address=self.host,
                rpc_port=self.rpc_port,
                stream_port=self.stream_port,
            )
            self.space_center = self.connection.space_center
            self._bind_vessel()
            self.connected = True
            print("✓ OK")
            return True
        except Exception as e:
            self.connected = False
            print(f"✗ {e}")
            return False

    def _bind_vessel(self) -> None:
        self.vessel = self.space_center.active_vessel
        self.control = self.vessel.control
        self.flight = self.vessel.flight(self.vessel.orbit.body.reference_frame)
        self.orbit = self.vessel.orbit
        self.resources = self.vessel.resources
        self.camera = self.space_center.camera

    def reconnect_if_needed(self) -> bool:
        if self.connected:
            try:
                _ = self.vessel.name
                return True
            except Exception:
                print("[KRPC] Connexion perdue.")
                self.connected = False

        if time.time() - self.last_connection_attempt >= self.reconnect_timeout_s:
            return self.connect()
        return False

    def disconnect(self) -> None:
        try:
            if self.connection:
                self.connection.close()
        except Exception:
            pass
        self.connected = False

    # ---- Télémétrie --------------------------------------------------

    def update_telemetry(self) -> None:
        if not self.connected:
            return
        try:
            self.telemetry["altitude"] = self.flight.surface_altitude
            self.telemetry["speed"] = self.flight.speed
            self.telemetry["vertical_speed"] = self.flight.vertical_speed
            self.telemetry["g_force"] = self.flight.g_force
            self.telemetry["temperature"] = self.flight.static_air_temperature
            self.telemetry["apoapsis"] = self.orbit.apoapsis
            self.telemetry["periapsis"] = self.orbit.periapsis
            self.telemetry["apoapsis_time"] = self.orbit.time_to_apoapsis
            self.telemetry["periapsis_time"] = self.orbit.time_to_periapsis
            self.telemetry["current_stage"] = self.control.current_stage
            self.telemetry["engines_active"] = self.control.throttle > 0.0
            self.telemetry["stages"] = self.get_stages_fuel()
        except Exception as e:
            print(f"[KRPC] Erreur télémétrie: {e}")
            self.connected = False

    def get_stages_fuel(self, max_stages: int = 4) -> List[Dict]:
        """Carburant par étage (liste du plus récent au plus ancien).

        Chaque entrée: {stage, fuel_percent, attached}.
        attached = True si l'étage n'a pas encore été largué.
        """
        if not self.connected:
            return []
        try:
            current = self.control.current_stage
            stages: List[Dict] = []
            for stage_num in range(current, current - max_stages, -1):
                if stage_num < 0:
                    break
                try:
                    res = self.vessel.resources_in_decouple_stage(
                        stage=stage_num, cumulative=False
                    )
                    liquid = res.amount("LiquidFuel")
                    liquid_max = res.max("LiquidFuel")
                    pct = (liquid / liquid_max * 100.0) if liquid_max > 0 else 0.0
                except Exception:
                    pct = 0.0
                stages.append(
                    {
                        "stage": stage_num,
                        "fuel_percent": pct,
                        "attached": stage_num <= current,
                    }
                )
            return stages
        except Exception:
            return []

    def get_telemetry(self) -> Dict:
        return self.telemetry.copy()

    # ---- Commandes ---------------------------------------------------

    def set_throttle(self, value: float) -> None:
        if not self.connected:
            return
        try:
            v = max(0.0, min(1.0, value))
            self.control.throttle = v
            self.throttle_state = v
        except Exception as e:
            print(f"[KRPC] Erreur throttle: {e}")

    def set_sas(self, enabled: bool) -> None:
        if not self.connected:
            return
        try:
            self.control.sas = enabled
            self.sas_state = enabled
        except Exception as e:
            print(f"[KRPC] Erreur SAS: {e}")

    def set_rcs(self, enabled: bool) -> None:
        if not self.connected:
            return
        try:
            self.control.rcs = enabled
            self.rcs_state = enabled
        except Exception as e:
            print(f"[KRPC] Erreur RCS: {e}")

    def trigger_action_group(self, group: int) -> None:
        if not self.connected:
            return
        try:
            self.control.toggle_action_group(group)
            print(f"[KSP] AG {group} déclenché")
        except Exception as e:
            print(f"[KRPC] Erreur AG {group}: {e}")

    def toggle_gear_and_brakes(self) -> None:
        """Toggle simultané train d'atterrissage + freins.

        Un même bouton physique sert aux deux selon le scénario chargé
        (décollage / atterrissage).
        """
        if not self.connected:
            return
        try:
            new_state = not self.control.gear
            self.control.gear = new_state
            self.control.brakes = new_state
            print(f"[KSP] Train/Freins: {'ON' if new_state else 'OFF'}")
        except Exception as e:
            print(f"[KRPC] Erreur gear/brakes: {e}")

    def toggle_map_camera(self) -> None:
        """Bascule entre la vue carte et la vue automatique."""
        if not self.connected:
            return
        try:
            mode = self.camera.mode
            # CameraMode.map = 7, CameraMode.automatic = 0
            if mode == self.space_center.CameraMode.map:
                self.camera.mode = self.space_center.CameraMode.automatic
                print("[KSP] Caméra: AUTO")
            else:
                self.camera.mode = self.space_center.CameraMode.map
                print("[KSP] Caméra: CARTE")
        except Exception as e:
            print(f"[KRPC] Erreur caméra: {e}")

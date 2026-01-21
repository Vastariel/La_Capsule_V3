#!/usr/bin/env python3
"""
KRPC Handler - Connexion et télémétrie Kerbal Space Program via kRPC.

Gère la connexion (avec reconnexion périodique), la collecte de télémétrie
via des streams kRPC (beaucoup plus rapide qu'un appel RPC par champ),
les commandes (SAS, RCS, throttle, action groups, caméra) et le carburant
par étage.
"""

import threading
import time
from typing import Callable, Dict, List, Optional

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
            "current_stage": -1,
            "engines_active": False,
            "stages": [],
        }

        self.sas_state = False
        self.rcs_state = False
        self.throttle_state = 0.0

        self._lock = threading.RLock()
        self._streams: Dict[str, "krpc.stream.Stream"] = {}
        self._vessel_id: Optional[int] = None
        self.on_vessel_changed: Optional[Callable[[], None]] = None

    # ---- Connexion ---------------------------------------------------

    def connect(self) -> bool:
        with self._lock:
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
        self._close_streams()
        self.vessel = self.space_center.active_vessel
        self.control = self.vessel.control
        self.flight = self.vessel.flight(self.vessel.orbit.body.reference_frame)
        self.orbit = self.vessel.orbit
        self.resources = self.vessel.resources
        self.camera = self.space_center.camera
        self._vessel_id = id(self.vessel)
        self._open_streams()

    def _open_streams(self) -> None:
        """Ouvre des streams kRPC pour les champs lus en boucle."""
        c = self.connection
        try:
            self._streams = {
                "altitude": c.add_stream(getattr, self.flight, "surface_altitude"),
                "speed": c.add_stream(getattr, self.flight, "speed"),
                "vertical_speed": c.add_stream(getattr, self.flight, "vertical_speed"),
                "g_force": c.add_stream(getattr, self.flight, "g_force"),
                "temperature": c.add_stream(getattr, self.flight, "static_air_temperature"),
                "apoapsis": c.add_stream(getattr, self.orbit, "apoapsis"),
                "periapsis": c.add_stream(getattr, self.orbit, "periapsis"),
                "apoapsis_time": c.add_stream(getattr, self.orbit, "time_to_apoapsis"),
                "periapsis_time": c.add_stream(getattr, self.orbit, "time_to_periapsis"),
                "current_stage": c.add_stream(getattr, self.control, "current_stage"),
                "throttle": c.add_stream(getattr, self.control, "throttle"),
            }
            print(f"[KRPC] {len(self._streams)} streams ouverts")
        except Exception as e:
            print(f"[KRPC] Impossible d'ouvrir les streams: {e}")
            self._streams = {}

    def _close_streams(self) -> None:
        for s in self._streams.values():
            try:
                s.remove()
            except Exception:
                pass
        self._streams = {}

    def _check_vessel_changed(self, new_stage: int) -> bool:
        """Détecte un retour au lancement / switch de vaisseau.

        Signal : le stage courant augmente (pendant un vol il ne fait que
        décroître ; une hausse signifie un nouveau vaisseau).
        """
        prev_stage = self.telemetry.get("current_stage", -1)
        # Premier relevé : pas de détection, on initialise.
        if prev_stage < 0:
            return False
        if new_stage <= prev_stage:
            return False
        print(f"[KRPC] Relancement détecté (stage {prev_stage} → {new_stage})")
        try:
            self._bind_vessel()
        except Exception as e:
            print(f"[KRPC] Rebind erreur: {e}")
        if self.on_vessel_changed:
            try:
                self.on_vessel_changed()
            except Exception as e:
                print(f"[KRPC] on_vessel_changed erreur: {e}")
        return True

    def reconnect_if_needed(self) -> bool:
        with self._lock:
            if self.connected:
                try:
                    _ = self.vessel.name
                    return True
                except Exception:
                    print("[KRPC] Connexion perdue.")
                    self.connected = False
                    self._close_streams()

            if time.time() - self.last_connection_attempt >= self.reconnect_timeout_s:
                return self.connect()
            return False

    def disconnect(self) -> None:
        with self._lock:
            try:
                self._close_streams()
                if self.connection:
                    self.connection.close()
            except Exception:
                pass
            self.connected = False

    # ---- Télémétrie --------------------------------------------------

    def update_telemetry(self) -> None:
        with self._lock:
            if not self.connected:
                return
            try:
                streams = self._streams
                new_stage = self.telemetry.get("current_stage", 0)
                if streams:
                    self.telemetry["altitude"] = streams["altitude"]()
                    self.telemetry["speed"] = streams["speed"]()
                    self.telemetry["vertical_speed"] = streams["vertical_speed"]()
                    self.telemetry["g_force"] = streams["g_force"]()
                    self.telemetry["temperature"] = streams["temperature"]()
                    self.telemetry["apoapsis"] = streams["apoapsis"]()
                    self.telemetry["periapsis"] = streams["periapsis"]()
                    self.telemetry["apoapsis_time"] = streams["apoapsis_time"]()
                    self.telemetry["periapsis_time"] = streams["periapsis_time"]()
                    new_stage = streams["current_stage"]()
                    self.telemetry["engines_active"] = streams["throttle"]() > 0.0
                else:
                    # Fallback RPC direct si les streams n'ont pas pu s'ouvrir.
                    self.telemetry["altitude"] = self.flight.surface_altitude
                    self.telemetry["speed"] = self.flight.speed
                    self.telemetry["vertical_speed"] = self.flight.vertical_speed
                    self.telemetry["g_force"] = self.flight.g_force
                    self.telemetry["temperature"] = self.flight.static_air_temperature
                    self.telemetry["apoapsis"] = self.orbit.apoapsis
                    self.telemetry["periapsis"] = self.orbit.periapsis
                    self.telemetry["apoapsis_time"] = self.orbit.time_to_apoapsis
                    self.telemetry["periapsis_time"] = self.orbit.time_to_periapsis
                    new_stage = self.control.current_stage
                    self.telemetry["engines_active"] = self.control.throttle > 0.0
                self._check_vessel_changed(new_stage)
                self.telemetry["current_stage"] = new_stage
                self.telemetry["stages"] = self._get_stages_fuel_locked()
            except Exception as e:
                print(f"[KRPC] Erreur télémétrie: {e}")
                self.connected = False
                self._close_streams()

    def get_stages_fuel(self, max_stages: int = 4) -> List[Dict]:
        with self._lock:
            return self._get_stages_fuel_locked(max_stages)

    def _get_stages_fuel_locked(self, max_stages: int = 4) -> List[Dict]:
        """Carburant par étage (du plus récent au plus ancien).

        Chaque entrée: {stage, fuel_percent, attached}.
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
        with self._lock:
            return self.telemetry.copy()

    # ---- Commandes ---------------------------------------------------

    def set_throttle(self, value: float) -> None:
        with self._lock:
            if not self.connected:
                return
            try:
                v = max(0.0, min(1.0, value))
                self.control.throttle = v
                self.throttle_state = v
            except Exception as e:
                print(f"[KRPC] Erreur throttle: {e}")

    def set_sas(self, enabled: bool) -> None:
        with self._lock:
            if not self.connected:
                return
            try:
                self.control.sas = enabled
                self.sas_state = enabled
            except Exception as e:
                print(f"[KRPC] Erreur SAS: {e}")

    def set_rcs(self, enabled: bool) -> None:
        with self._lock:
            if not self.connected:
                return
            try:
                self.control.rcs = enabled
                self.rcs_state = enabled
            except Exception as e:
                print(f"[KRPC] Erreur RCS: {e}")

    def trigger_action_group(self, group: int) -> None:
        with self._lock:
            if not self.connected:
                return
            try:
                self.control.toggle_action_group(group)
                print(f"[KSP] AG {group} déclenché")
            except Exception as e:
                print(f"[KRPC] Erreur AG {group}: {e}")

    def toggle_gear_and_brakes(self) -> None:
        with self._lock:
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
        with self._lock:
            if not self.connected:
                return
            try:
                mode = self.camera.mode
                if mode == self.space_center.CameraMode.map:
                    self.camera.mode = self.space_center.CameraMode.automatic
                    print("[KSP] Caméra: AUTO")
                else:
                    self.camera.mode = self.space_center.CameraMode.map
                    print("[KSP] Caméra: CARTE")
            except Exception as e:
                print(f"[KRPC] Erreur caméra: {e}")

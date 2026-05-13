#!/usr/bin/env python3
"""
KRPC Handler - Connexion et télémétrie Kerbal Space Program via kRPC.

Gère la connexion (avec reconnexion périodique), la collecte de télémétrie
via des streams kRPC (beaucoup plus rapide qu'un appel RPC par champ) et
les commandes (SAS, RCS, throttle, action groups, caméra).
"""

import concurrent.futures
import threading
import time
from typing import Callable, Dict, Optional

import krpc


# Cadence (Hz) à laquelle KSP recalcule chaque stream côté serveur.
# Limiter ce taux libère du CPU dans KSP — c'est le levier principal pour
# réduire la latence du jeu, indépendamment de la fréquence de lecture côté
# Python (qui reste à update_hz, et lit la valeur cachée du stream).
STREAM_RATES_HZ: Dict[str, float] = {
    "altitude": 20.0,
    "speed": 20.0,
    "vertical_speed": 20.0,
    "throttle": 20.0,
    "g_force": 10.0,
    "current_stage": 5.0,
    "apoapsis": 5.0,
    "periapsis": 5.0,
    "time_to_apoapsis": 1.0,
    "time_to_periapsis": 1.0,
}


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
        self.camera = None
        self.space_center = None

        self.telemetry: Dict = {
            "altitude": 0.0,
            "speed": 0.0,
            "vertical_speed": 0.0,
            "g_force": 0.0,
            "apoapsis": 0.0,
            "periapsis": 0.0,
            "time_to_apoapsis": 0.0,
            "time_to_periapsis": 0.0,
            "heat_shield_temp": 0.0,
            "current_stage": -1,
            "engines_active": False,
        }
        self._heat_counter = 0

        self.sas_state = False
        self.rcs_state = False
        self.throttle_state = 0.0

        self._lock = threading.RLock()
        self._streams: Dict[str, "krpc.stream.Stream"] = {}
        self._vessel_id: Optional[int] = None
        self.on_vessel_changed: Optional[Callable[[], None]] = None
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="heat_poll"
        )

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
        self.camera = self.space_center.camera
        self._vessel_id = id(self.vessel)
        self._open_streams()

    def _open_streams(self) -> None:
        """Ouvre des streams kRPC pour les champs lus en boucle.

        Chaque stream a sa cadence serveur configurée via STREAM_RATES_HZ :
        KSP cesse de recalculer le stream à chaque frame et le limite au Hz
        demandé, ce qui réduit fortement la charge serveur.
        """
        c = self.connection
        try:
            streams = {
                "altitude": c.add_stream(getattr, self.flight, "surface_altitude"),
                "speed": c.add_stream(getattr, self.flight, "speed"),
                "vertical_speed": c.add_stream(getattr, self.flight, "vertical_speed"),
                "g_force": c.add_stream(getattr, self.flight, "g_force"),
                "apoapsis": c.add_stream(getattr, self.orbit, "apoapsis_altitude"),
                "periapsis": c.add_stream(getattr, self.orbit, "periapsis_altitude"),
                "time_to_apoapsis": c.add_stream(getattr, self.orbit, "time_to_apoapsis"),
                "time_to_periapsis": c.add_stream(getattr, self.orbit, "time_to_periapsis"),
                "current_stage": c.add_stream(getattr, self.control, "current_stage"),
                "throttle": c.add_stream(getattr, self.control, "throttle"),
            }
            for name, stream in streams.items():
                rate = STREAM_RATES_HZ.get(name)
                if rate is not None:
                    try:
                        stream.rate = rate
                    except Exception as e:
                        print(f"[KRPC] stream.rate({name}={rate}): {e}")
            self._streams = streams
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
        # Lock court : snapshot des références seulement.
        with self._lock:
            if not self.connected:
                return
            streams = self._streams
            flight, orbit, control = self.flight, self.orbit, self.control

        # Lectures réseau sans lock : get_telemetry() reste libre pendant ce temps.
        try:
            new_vals: Dict = {}
            if streams:
                new_vals["altitude"]          = streams["altitude"]()
                new_vals["speed"]             = streams["speed"]()
                new_vals["vertical_speed"]    = streams["vertical_speed"]()
                new_vals["g_force"]           = streams["g_force"]()
                new_vals["apoapsis"]          = streams["apoapsis"]()
                new_vals["periapsis"]         = streams["periapsis"]()
                new_vals["time_to_apoapsis"]  = streams["time_to_apoapsis"]()
                new_vals["time_to_periapsis"] = streams["time_to_periapsis"]()
                new_stage                     = streams["current_stage"]()
                new_vals["engines_active"]    = streams["throttle"]() > 0.0
            else:
                # Fallback RPC direct si les streams n'ont pas pu s'ouvrir.
                new_vals["altitude"]          = flight.surface_altitude
                new_vals["speed"]             = flight.speed
                new_vals["vertical_speed"]    = flight.vertical_speed
                new_vals["g_force"]           = flight.g_force
                new_vals["apoapsis"]          = orbit.apoapsis_altitude
                new_vals["periapsis"]         = orbit.periapsis_altitude
                new_vals["time_to_apoapsis"]  = orbit.time_to_apoapsis
                new_vals["time_to_periapsis"] = orbit.time_to_periapsis
                new_stage                     = control.current_stage
                new_vals["engines_active"]    = control.throttle > 0.0

            self._heat_counter += 1
            if self._heat_counter >= 20:
                self._heat_counter = 0
                self._executor.submit(self._async_update_heat)

            # Lock court : écriture atomique du dict partagé.
            with self._lock:
                self.telemetry.update(new_vals)
                self._check_vessel_changed(new_stage)
                self.telemetry["current_stage"] = new_stage

        except Exception as e:
            print(f"[KRPC] Erreur télémétrie: {e}")
            with self._lock:
                self.connected = False
                self._close_streams()

    def _async_update_heat(self) -> None:
        temp = self._poll_heat_shield_temp()
        with self._lock:
            self.telemetry["heat_shield_temp"] = temp

    def _poll_heat_shield_temp(self) -> float:
        try:
            return max(p.skin_temperature for p in self.vessel.parts.all)
        except Exception:
            return 0.0

    def get_telemetry(self) -> Dict:
        with self._lock:
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

#!/usr/bin/env python3
"""
KSP Control - Connexion kRPC propre au serveur admin.

Toutes les méthodes sont synchrones et protégées par un verrou : le serveur
les appelle via asyncio.to_thread(). Une méthode lève KSPError avec un
message lisible par l'animateur en cas d'échec.
"""

import socket
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

import krpc


class KSPError(Exception):
    pass


class KSPControl:
    def __init__(self, cfg: dict, ksp_cfg: dict, camera_cfg: dict):
        # Plusieurs PC KSP possibles (ce PC, celui de la capsule...) : essayés
        # dans l'ordre, le dernier qui a répondu en premier.
        hosts = cfg.get("hosts") or cfg.get("host", "127.0.0.1")
        self.hosts = [hosts] if isinstance(hosts, str) else list(hosts)
        self.host = self.hosts[0]
        self.rpc_port = cfg.get("rpc_port", 50008)
        self.stream_port = cfg.get("stream_port", 50001)
        self.ksp_dir = Path(ksp_cfg.get("dir", ""))
        self.save_game = ksp_cfg.get("save_game", "default")
        self.rotate_step = float(camera_cfg.get("rotate_step_deg", 4.0))
        self.zoom_factor = float(camera_cfg.get("zoom_factor", 1.25))

        self._lock = threading.RLock()
        self._conn = None
        self._last_attempt = 0.0

    # ---- Connexion ---------------------------------------------------

    def _find_host(self) -> Optional[str]:
        """Premier hôte dont le port RPC répond (test TCP court)."""
        for host in [self.host] + [h for h in self.hosts if h != self.host]:
            try:
                with socket.create_connection((host, self.rpc_port), timeout=1.0):
                    return host
            except OSError:
                continue
        return None

    def _sc(self):
        """SpaceCenter connecté, avec reconnexion (au plus toutes les 3 s)."""
        if self._conn is not None:
            try:
                _ = self._conn.krpc.get_status()
                return self._conn.space_center
            except Exception:
                self._close()
        if time.time() - self._last_attempt < 3.0:
            raise KSPError("KSP injoignable (kRPC)")
        self._last_attempt = time.time()
        if len(self.hosts) > 1:
            host = self._find_host()
            if host is None:
                print(f"[KRPC] Aucun KSP joignable ({', '.join(self.hosts)})")
                raise KSPError("KSP injoignable (kRPC)")
            self.host = host
        try:
            self._conn = krpc.connect(
                name="La Capsule - admin",
                address=self.host,
                rpc_port=self.rpc_port,
                stream_port=self.stream_port,
            )
            print(f"[KRPC] Connecté à {self.host}:{self.rpc_port}")
            return self._conn.space_center
        except Exception as e:
            self._conn = None
            print(f"[KRPC] Connexion impossible : {e}")
            raise KSPError("KSP injoignable (kRPC)")

    def _close(self) -> None:
        try:
            if self._conn:
                self._conn.close()
        except Exception:
            pass
        self._conn = None

    def _vessel(self):
        try:
            return self._sc().active_vessel
        except KSPError:
            raise
        except Exception:
            raise KSPError("pas de vaisseau actif (KSP hors scène de vol ?)")

    # ---- État --------------------------------------------------------

    def status(self) -> Dict:
        with self._lock:
            try:
                sc = self._sc()
            except KSPError as e:
                return {"krpc": False, "error": str(e)}
            state = {"krpc": True, "vessel": None}
            try:
                vessel = sc.active_vessel
                state["vessel"] = vessel.name
                state["camera_map"] = sc.camera.mode == sc.CameraMode.map
                state["can_revert"] = sc.can_revert_to_launch()
                state["parachutes"] = [
                    {"index": i, "title": p.part.title, "deployed": p.deployed,
                     "state": str(p.state).split(".")[-1]}
                    for i, p in enumerate(vessel.parts.parachutes)
                ]
            except Exception:
                pass  # hors scène de vol : seul "krpc" est pertinent
            return state

    # ---- Caméra ------------------------------------------------------

    def camera_toggle_map(self) -> bool:
        with self._lock:
            sc = self._sc()
            cam = sc.camera
            to_map = cam.mode != sc.CameraMode.map
            cam.mode = sc.CameraMode.map if to_map else sc.CameraMode.automatic
            return to_map

    def camera_move(self, dx: float, dy: float) -> None:
        """dx, dy dans [-1, 1] : droite/gauche et haut/bas du joystick."""
        dx = max(-1.0, min(1.0, float(dx)))
        dy = max(-1.0, min(1.0, float(dy)))
        with self._lock:
            cam = self._sc().camera
            if dx:
                cam.heading = (cam.heading + dx * self.rotate_step) % 360.0
            if dy:
                pitch = cam.pitch + dy * self.rotate_step
                cam.pitch = max(cam.min_pitch, min(cam.max_pitch, pitch))

    def camera_zoom(self, direction: int) -> None:
        """direction > 0 : rapprocher, < 0 : éloigner."""
        with self._lock:
            cam = self._sc().camera
            factor = 1.0 / self.zoom_factor if direction > 0 else self.zoom_factor
            dist = cam.distance * factor
            cam.distance = max(cam.min_distance, min(cam.max_distance, dist))

    def camera_reset(self) -> None:
        with self._lock:
            cam = self._sc().camera
            cam.distance = cam.default_distance
            cam.pitch = max(cam.min_pitch, min(cam.max_pitch, 15.0))
            cam.heading = 0.0

    # ---- Science -----------------------------------------------------

    def run_all_experiments(self) -> Dict:
        with self._lock:
            experiments = self._vessel().parts.experiments
            ran, skipped = [], []
            for exp in experiments:
                title = exp.part.title
                try:
                    if exp.inoperable or exp.has_data or not exp.available:
                        skipped.append(title)
                        continue
                    exp.run()
                    ran.append(title)
                except Exception:
                    skipped.append(title)
            return {"ran": ran, "skipped": skipped, "total": len(experiments)}

    # ---- Pannes ------------------------------------------------------

    def cut_parachutes(self, index: Optional[int]) -> List[str]:
        """Coupe le parachute `index` (ordre de status()), ou tous si None."""
        with self._lock:
            chutes = self._vessel().parts.parachutes
            if index is not None:
                if not 0 <= index < len(chutes):
                    raise KSPError("parachute introuvable (fusée modifiée ?)")
                chutes = [chutes[index]]
            cut = []
            for chute in chutes:
                chute.cut()
                cut.append(chute.part.title)
            return cut

    # ---- Mission -----------------------------------------------------

    def revert_to_launch(self) -> None:
        with self._lock:
            sc = self._sc()
            if not sc.can_revert_to_launch():
                raise KSPError("retour au lancement impossible dans l'état actuel")
            sc.revert_to_launch()

    def list_saves(self) -> List[str]:
        folder = self.ksp_dir / "saves" / self.save_game
        if not folder.is_dir():
            return []
        files = sorted(folder.glob("*.sfs"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [f.stem for f in files]

    def load_save(self, name: str) -> None:
        if name not in self.list_saves():
            raise KSPError(f"sauvegarde inconnue : {name}")
        with self._lock:
            self._sc().load(name)

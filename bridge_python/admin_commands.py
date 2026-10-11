#!/usr/bin/env python3
"""
Admin Commands - Commandes reçues de l'interface animateur (serveur admin du PC).

Le serveur admin a sa propre connexion kRPC pour tout ce qui touche KSP.
Il ne passe par le bridge que pour ce qui n'existe que sur la Raspi :
- la calibration du throttle (le Pico est branché sur la Raspi) ;
- les pannes d'instruments (l'écran Godot est alimenté par ce bridge).

Chaque message doit porter le jeton partagé `admin.token` de config.json.
"""

import json
import threading
from pathlib import Path
from typing import Dict, Optional


# Pannes d'instruments connues (clé = élément affiché par Godot).
INSTRUMENTS = ("navball",)


class AdminCommands:
    def __init__(self, pico, config_path: Path, token: Optional[str]):
        self.pico = pico
        self.config_path = config_path
        self.token = token or None
        self._lock = threading.Lock()
        self.failures: Dict[str, bool] = {name: False for name in INSTRUMENTS}

    def get_failures(self) -> Dict[str, bool]:
        with self._lock:
            return dict(self.failures)

    def handle(self, msg: dict) -> dict:
        """Traite une commande et renvoie la réponse (sans l'id de requête)."""
        if self.token is None:
            return {"ok": False, "error": "admin.token absent de config.json"}
        if msg.get("token") != self.token:
            return {"ok": False, "error": "jeton invalide"}

        cmd = msg.get("cmd")
        try:
            if cmd == "status":
                return {"ok": True, "failures": self.get_failures(),
                        "pico": bool(self.pico and self.pico.connected)}
            if cmd == "failure_set":
                return self._failure_set(msg.get("name"), bool(msg.get("active")))
            if cmd == "calib_sample":
                return self._calib_sample()
            if cmd == "calib_save":
                return self._calib_save(msg.get("points"))
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
        return {"ok": False, "error": f"commande inconnue : {cmd}"}

    # ---- Pannes d'instruments -----------------------------------------

    def _failure_set(self, name, active: bool) -> dict:
        if name not in INSTRUMENTS:
            return {"ok": False, "error": f"instrument inconnu : {name}"}
        with self._lock:
            self.failures[name] = active
        print(f"[ADMIN] Panne {name} : {'ACTIVE' if active else 'réparée'}")
        return {"ok": True, "failures": self.get_failures()}

    # ---- Calibration throttle -----------------------------------------

    def _calib_sample(self) -> dict:
        if not self.pico or not self.pico.connected:
            return {"ok": False, "error": "Pico non connecté"}
        raw = self.pico.recent_raw()
        if raw is None:
            return {"ok": False, "error": "aucune lecture ADC récente"}
        return {"ok": True, **raw}

    def _calib_save(self, points) -> dict:
        """points = [[fraction, raw], ...] ; même format que calibrate_throttle.py."""
        try:
            pts = [[float(f), int(r)] for f, r in points]
        except (TypeError, ValueError):
            return {"ok": False, "error": "points invalides"}
        if len(pts) < 2:
            return {"ok": False, "error": "il faut au moins 2 points"}
        raws = [r for _, r in pts]
        monotonic = (all(a < b for a, b in zip(raws, raws[1:]))
                     or all(a > b for a, b in zip(raws, raws[1:])))
        if not monotonic:
            return {"ok": False, "error": f"valeurs non monotones : {raws}"}

        if not self.pico.set_calibration(pts):
            return {"ok": False, "error": "table refusée par le Pico handler"}

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        config.setdefault("throttle", {})["calibration"] = pts
        tmp = self.config_path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            f.write("\n")
        tmp.replace(self.config_path)
        print(f"[ADMIN] Calibration enregistrée : {pts}")
        return {"ok": True, "points": pts}

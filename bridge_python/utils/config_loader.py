#!/usr/bin/env python3
"""
Config Loader - chargement de config.json.

Expose `get_config()` et `print_config_summary()`. Source unique de
vérité : le fichier config.json à la racine du projet (ou chemin absolu
de production).
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict


_SEARCH_PATHS = [
    Path("/home/capsule/Desktop/La_Capsule_V3/config.json"),
    Path(__file__).resolve().parent.parent.parent / "config.json",
]


def _load() -> Dict[str, Any]:
    for path in _SEARCH_PATHS:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                print(f"✓ Config chargée: {path}")
                return json.load(f)
    print("✗ config.json introuvable. Cherché dans:")
    for p in _SEARCH_PATHS:
        print(f"  - {p}")
    sys.exit(1)


CONFIG: Dict[str, Any] = _load()


def get_config() -> Dict[str, Any]:
    return CONFIG


def print_config_summary() -> None:
    k = CONFIG.get("krpc", {})
    w = CONFIG.get("websocket", {})
    g = CONFIG.get("hardware", {}).get("gpio", {})
    p = CONFIG.get("hardware", {}).get("pico", {})
    print("=" * 60)
    print("CONFIGURATION")
    print("=" * 60)
    print(f"KSP:       {k.get('host')}:{k.get('rpc_port')} (stream {k.get('stream_port')})")
    print(f"Raspi:     {g.get('raspi_ip')} (remote={g.get('use_remote')})")
    print(f"WebSocket: ws://{w.get('host')}:{w.get('port')}  {w.get('update_hz')} Hz")
    print(f"Pico:      {p.get('port')} ch={p.get('adc_channel_throttle')}")
    print(
        f"GPIO:      {len(g.get('leds_rouges', {}))} LED rouges, "
        f"{len(g.get('leds_vertes', {}))} vertes, "
        f"{len(g.get('leviers', {}))} leviers, "
        f"{len(g.get('boutons', {}))} boutons"
    )
    print("=" * 60)


if __name__ == "__main__":
    print_config_summary()

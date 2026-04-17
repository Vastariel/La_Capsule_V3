#!/usr/bin/env python3
"""
La Capsule V3 - Point d'entrée.

Orchestre KRPC, Pico (ADC throttle), GPIO (Raspberry) et le serveur
WebSocket qui alimente l'UI Godot.
"""

import json
import sys
import threading
import time
from pathlib import Path

from krpc_handler import KRPCHandler
from pico_handler import PicoHandler
from gpio_handler import GPIOHandler
from websocket_server import WebSocketServer


CONFIG_SEARCH_PATHS = [
    Path("/home/capsule/Desktop/La_Capsule_V3/config.json"),
    Path(__file__).resolve().parent.parent / "config.json",
]


def load_config() -> dict:
    for path in CONFIG_SEARCH_PATHS:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            print(f"[CONFIG] Chargé: {path}")
            return cfg
    print("✗ config.json introuvable. Chemins testés:")
    for p in CONFIG_SEARCH_PATHS:
        print(f"  - {p}")
    sys.exit(1)


def main() -> None:
    print("=" * 60)
    print("La Capsule V3 - KSP Hardware Control")
    print("=" * 60)

    config = load_config()

    # ---- KRPC -------------------------------------------------------
    kcfg = config.get("krpc", {})
    krpc = KRPCHandler(
        host=kcfg.get("host", "127.0.0.1"),
        rpc_port=kcfg.get("rpc_port", 50008),
        stream_port=kcfg.get("stream_port", 50001),
        reconnect_timeout_s=kcfg.get("reconnect_timeout_s", 5),
    )
    krpc.connect()

    # ---- Pico (ADC) -------------------------------------------------
    pcfg = config.get("hardware", {}).get("pico", {})
    tcfg = config.get("throttle", {})
    pico = PicoHandler(
        port=pcfg.get("port", "/dev/ttyACM0"),
        adc_channel=pcfg.get("adc_channel_throttle", 0),
        alpha=tcfg.get("smoothing_alpha", 0.25),
        deadzone=tcfg.get("deadzone_percent", 3.0) / 100.0,
        output_deadband=tcfg.get("output_deadband_percent", 1.0) / 100.0,
    )

    # ---- GPIO -------------------------------------------------------
    gpio_cfg = config.get("hardware", {}).get("gpio")
    gpio = GPIOHandler(krpc=krpc, pico=pico, config=gpio_cfg)

    # ---- WebSocket --------------------------------------------------
    wcfg = config.get("websocket", {})
    ws = WebSocketServer(
        krpc=krpc,
        host=wcfg.get("host", "0.0.0.0"),
        port=wcfg.get("port", 8080),
        update_hz=wcfg.get("update_hz", 10),
    )
    threading.Thread(target=ws.start, daemon=True).start()

    # ---- Boucle principale ------------------------------------------
    print("=" * 60)
    print("Boucle principale (Ctrl-C pour arrêter)")
    print("=" * 60)

    loop = 0
    try:
        while True:
            try:
                if krpc.connected:
                    krpc.update_telemetry()
                else:
                    krpc.reconnect_if_needed()
            except Exception:
                pass

            try:
                gpio.update()
            except Exception as e:
                print(f"[GPIO] Erreur: {e}")

            loop += 1
            if loop % 30 == 0:
                print(
                    f"[LOOP] {loop:6d} "
                    f"KRPC:{'✓' if krpc.connected else '✗'} "
                    f"WS:{len(ws.clients)}"
                )
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[MAIN] Ctrl-C")
    finally:
        gpio.cleanup()
        pico.disconnect()
        krpc.disconnect()
        print("[MAIN] Arrêt")


if __name__ == "__main__":
    main()

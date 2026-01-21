#!/usr/bin/env python3
"""
La Capsule V3 - Point d'entrée.

Orchestre KRPC, Pico (ADC throttle), GPIO (Raspberry) et le serveur
WebSocket qui alimente l'UI Godot.

Architecture multi-thread :
- Thread télémétrie kRPC (update_hz, défaut 20Hz)
- Thread GPIO (throttle + LEDs, 20Hz)
- Thread WebSocket (asyncio, diffusion à update_hz)
- Boutons/leviers : event-driven via callbacks gpiozero (thread pigpio)
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


def telemetry_loop(krpc: KRPCHandler, hz: int, stop_event: threading.Event) -> None:
    """Lit la télémétrie kRPC à la cadence demandée et gère la reconnexion."""
    interval = 1.0 / max(1, hz)
    while not stop_event.is_set():
        try:
            if krpc.connected:
                krpc.update_telemetry()
            else:
                krpc.reconnect_if_needed()
        except Exception as e:
            print(f"[TELEM] Erreur: {e}")
        stop_event.wait(interval)


def gpio_loop(gpio: GPIOHandler, hz: int, stop_event: threading.Event) -> None:
    """Rafraîchit throttle (lecture Pico) + LEDs à cadence fixe."""
    interval = 1.0 / max(1, hz)
    while not stop_event.is_set():
        try:
            gpio.update()
        except Exception as e:
            print(f"[GPIO] Erreur: {e}")
        stop_event.wait(interval)


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

    # Retour au lancement : on ré-aligne LEDs et leviers sur le nouveau vaisseau.
    krpc.on_vessel_changed = gpio.resync_vessel_state
    if krpc.connected:
        gpio.resync_vessel_state()

    # ---- WebSocket --------------------------------------------------
    wcfg = config.get("websocket", {})
    ws_hz = int(wcfg.get("update_hz", 20))
    ws = WebSocketServer(
        krpc=krpc,
        host=wcfg.get("host", "0.0.0.0"),
        port=wcfg.get("port", 8080),
        update_hz=ws_hz,
    )
    threading.Thread(target=ws.start, daemon=True).start()

    # ---- Threads télémétrie + GPIO ----------------------------------
    stop_event = threading.Event()
    telem_hz = int(config.get("telemetry", {}).get("update_hz", 20))
    gpio_hz = 20

    telem_thread = threading.Thread(
        target=telemetry_loop, args=(krpc, telem_hz, stop_event), daemon=True
    )
    gpio_thread = threading.Thread(
        target=gpio_loop, args=(gpio, gpio_hz, stop_event), daemon=True
    )
    telem_thread.start()
    gpio_thread.start()

    print("=" * 60)
    print(f"Threads lancés : télémétrie {telem_hz}Hz, GPIO {gpio_hz}Hz, WS {ws_hz}Hz")
    print("Boutons/leviers : event-driven (gpiozero callbacks)")
    print("Ctrl-C pour arrêter")
    print("=" * 60)

    # ---- Boucle principale (monitoring léger) -----------------------
    loop = 0
    try:
        while True:
            time.sleep(1.0)
            loop += 1
            if loop % 10 == 0:
                print(
                    f"[LOOP] {loop:6d}s "
                    f"KRPC:{'✓' if krpc.connected else '✗'} "
                    f"WS:{len(ws.clients)}"
                )
    except KeyboardInterrupt:
        print("\n[MAIN] Ctrl-C")
    finally:
        stop_event.set()
        telem_thread.join(timeout=2.0)
        gpio_thread.join(timeout=2.0)
        gpio.cleanup()
        pico.disconnect()
        krpc.disconnect()
        print("[MAIN] Arrêt")


if __name__ == "__main__":
    main()

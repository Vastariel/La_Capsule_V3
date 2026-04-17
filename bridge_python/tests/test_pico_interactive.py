#!/usr/bin/env python3
"""Test Pico ADC interactif (hardware requis).

Usage:
    python test_pico_interactive.py         # durée normale
    python test_pico_interactive.py --quick # durée réduite
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import get_config
from pico_handler import PicoHandler


def bar(value: float, width: int = 40) -> str:
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    cfg = get_config()
    tcfg = cfg.get("throttle", {})
    pcfg = cfg.get("hardware", {}).get("pico", {})

    pico = PicoHandler(
        port=pcfg.get("port", "/dev/ttyACM0"),
        adc_channel=pcfg.get("adc_channel_throttle", 0),
        alpha=tcfg.get("smoothing_alpha", 0.25),
        deadzone=tcfg.get("deadzone_percent", 3.0) / 100.0,
        output_deadband=tcfg.get("output_deadband_percent", 1.0) / 100.0,
    )
    if not pico.connected:
        print(f"✗ Pico non connecté: {pico.last_error}")
        return 1

    duration = 3.0 if args.quick else 10.0
    print(f"\nLecture throttle pendant {duration}s (tournez le potentiomètre)...")
    print("raw = valeur brute 0-4095, th = throttle 0-1 après EMA + deadzone\n")

    end = time.time() + duration
    while time.time() < end:
        raw = pico.read_raw()
        th = pico.get_throttle()
        if raw is not None:
            print(f"  raw={raw:4d} | th={th:.3f} |{bar(th)}|", end="\r", flush=True)
        time.sleep(0.05)
    print()

    print("\n[Deadband] Valeurs renvoyées par get_throttle_if_changed() :")
    emitted = 0
    end = time.time() + (2.0 if args.quick else 5.0)
    while time.time() < end:
        v = pico.get_throttle_if_changed()
        if v is not None:
            print(f"  → {v:.3f}")
            emitted += 1
        time.sleep(0.05)
    print(f"[Deadband] {emitted} valeurs émises")

    pico.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())

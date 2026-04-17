#!/usr/bin/env python3
"""Test GPIO interactif (hardware requis).

Usage:
    python test_gpio_interactive.py         # délais normaux
    python test_gpio_interactive.py --quick # délais réduits (~30s total)
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import get_config, print_config_summary
from gpio_handler import GPIOHandler


def test_leds(gpio: GPIOHandler, per_led_seconds: float) -> None:
    all_leds = {**gpio.leds_red, **gpio.leds_green}
    print(f"\n[LEDs] {len(all_leds)} LEDs à tester ({per_led_seconds}s chacune)")
    for pin, led in all_leds.items():
        role = gpio.leds_rouges_cfg.get(pin) or gpio.leds_vertes_cfg.get(pin)
        print(f"  GPIO {pin} ({role}) → ON", end="", flush=True)
        led.on()
        time.sleep(per_led_seconds)
        led.off()
        print(" → OFF ✓")


def test_inputs(gpio: GPIOHandler, monitor_seconds: float) -> None:
    print(f"\n[Inputs] Monitoring {monitor_seconds}s — actionnez leviers/boutons")
    print("  Leviers:", {p: a for p, a in gpio.leviers_cfg.items()})
    print("  Boutons:", {p: a.get("name", a.get("type")) for p, a in gpio.boutons_cfg.items()})

    prev_lev = {p: b.is_pressed for p, b in gpio.leviers.items()}
    prev_btn = {p: b.is_pressed for p, b in gpio.boutons.items()}
    detected = set()

    end = time.time() + monitor_seconds
    while time.time() < end:
        for p, b in gpio.leviers.items():
            cur = b.is_pressed
            if cur != prev_lev[p]:
                print(f"  Levier {p} ({gpio.leviers_cfg[p]}): {'ON' if cur else 'OFF'}")
                prev_lev[p] = cur
                detected.add(("levier", p))
        for p, b in gpio.boutons.items():
            cur = b.is_pressed
            if cur and not prev_btn[p]:
                name = gpio.boutons_cfg[p].get("name", gpio.boutons_cfg[p].get("type"))
                print(f"  Bouton {p} ({name}): PRESS")
                detected.add(("bouton", p))
            prev_btn[p] = cur
        time.sleep(0.05)

    total = len(gpio.leviers) + len(gpio.boutons)
    print(f"\n[Inputs] {len(detected)}/{total} entrées vues")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Délais réduits")
    args = parser.parse_args()

    print_config_summary()

    led_time = 0.3 if args.quick else 1.0
    input_time = 5.0 if args.quick else 15.0

    cfg = get_config()["hardware"]["gpio"]
    gpio = GPIOHandler(krpc=None, pico=None, config=cfg)
    if not gpio.connected:
        print("✗ GPIO non connecté")
        return 1

    try:
        test_leds(gpio, led_time)
        test_inputs(gpio, input_time)
    finally:
        gpio.cleanup()
    return 0


if __name__ == "__main__":
    sys.exit(main())

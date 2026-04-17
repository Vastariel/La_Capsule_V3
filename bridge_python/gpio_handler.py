#!/usr/bin/env python3
"""
GPIO Handler - Entrées/sorties Raspberry Pi.

Lit boutons et leviers, pilote les LEDs, déclenche les actions kRPC.
Toute la config vient de config.json (section hardware.gpio).
"""

import sys
from typing import Dict, Optional

try:
    from gpiozero import LED, Button
    from gpiozero.pins.pigpio import PiGPIOFactory
except ImportError:
    print("✗ Module 'gpiozero' requis: pip install gpiozero pigpio")
    sys.exit(1)


def _coerce_int_keys(d: Dict) -> Dict:
    """Les clés JSON sont des strings, on les convertit en int."""
    return {int(k): v for k, v in d.items()}


class GPIOHandler:
    """Gère les GPIO de la Raspberry Pi et les actions associées."""

    def __init__(self, krpc=None, pico=None, config: Optional[Dict] = None):
        if config is None:
            raise ValueError("GPIOHandler: config manquant (hardware.gpio)")

        self.krpc = krpc
        self.pico = pico
        self.config = config

        self.raspi_ip = config.get("raspi_ip", "127.0.0.1")
        self.use_remote = config.get("use_remote", True)

        self.leds_rouges_cfg = _coerce_int_keys(config.get("leds_rouges", {}))
        self.leds_vertes_cfg = _coerce_int_keys(config.get("leds_vertes", {}))
        self.leviers_cfg = _coerce_int_keys(config.get("leviers", {}))
        self.boutons_cfg = _coerce_int_keys(config.get("boutons", {}))

        self.factory = None
        self.connected = False

        self.leds_red: Dict[int, LED] = {}
        self.leds_green: Dict[int, LED] = {}
        self.leviers: Dict[int, Button] = {}
        self.boutons: Dict[int, Button] = {}

        self._prev_leviers: Dict[int, bool] = {}
        self._prev_boutons: Dict[int, bool] = {}
        self._stage_led_states: Dict[int, bool] = {}
        self._sas_led = False
        self._rcs_led = False

        self._connect_factory()
        if self.connected:
            self._initialize_pins()

    # ---- Initialisation ----------------------------------------------

    def _connect_factory(self) -> None:
        if self.use_remote:
            try:
                self.factory = PiGPIOFactory(host=self.raspi_ip)
                self.connected = True
                print(f"[GPIO] Connecté pigpio → {self.raspi_ip}")
            except Exception as e:
                print(f"[GPIO] Erreur pigpio ({self.raspi_ip}): {e}")
                self.connected = False
        else:
            self.connected = True
            print("[GPIO] Mode GPIO local")

    def _initialize_pins(self) -> None:
        for pin in self.leds_rouges_cfg:
            try:
                self.leds_red[pin] = LED(pin, pin_factory=self.factory)
                self._stage_led_states[pin] = False
            except Exception as e:
                print(f"[GPIO] LED rouge {pin}: {e}")

        for pin in self.leds_vertes_cfg:
            try:
                self.leds_green[pin] = LED(pin, pin_factory=self.factory)
            except Exception as e:
                print(f"[GPIO] LED verte {pin}: {e}")

        for pin in self.leviers_cfg:
            try:
                self.leviers[pin] = Button(pin, pull_up=True, pin_factory=self.factory)
                self._prev_leviers[pin] = False
            except Exception as e:
                print(f"[GPIO] Levier {pin}: {e}")

        for pin in self.boutons_cfg:
            try:
                self.boutons[pin] = Button(pin, pull_up=True, pin_factory=self.factory)
                self._prev_boutons[pin] = False
            except Exception as e:
                print(f"[GPIO] Bouton {pin}: {e}")

        print(
            f"[GPIO] {len(self.leds_red)} LED rouges, {len(self.leds_green)} vertes, "
            f"{len(self.leviers)} leviers, {len(self.boutons)} boutons"
        )

    # ---- Boucle ------------------------------------------------------

    def update(self) -> None:
        if not self.connected:
            return
        self._update_leviers()
        self._update_boutons()
        self._update_throttle()
        self._update_leds()

    def _update_leviers(self) -> None:
        for pin, action in self.leviers_cfg.items():
            btn = self.leviers.get(pin)
            if btn is None:
                continue
            pressed = btn.is_pressed
            if pressed == self._prev_leviers[pin]:
                continue
            self._prev_leviers[pin] = pressed
            print(f"[GPIO] Levier {action}: {'ON' if pressed else 'OFF'}")
            if action == "SAS" and self.krpc:
                self.krpc.set_sas(pressed)
            elif action == "RCS" and self.krpc:
                self.krpc.set_rcs(pressed)
            # THROTTLE_CONTROL : géré dans _update_throttle

    def _update_boutons(self) -> None:
        for pin, action in self.boutons_cfg.items():
            btn = self.boutons.get(pin)
            if btn is None:
                continue
            pressed = btn.is_pressed
            was = self._prev_boutons[pin]
            if pressed and not was:
                self._dispatch_button(pin, action)
            self._prev_boutons[pin] = pressed

    def _dispatch_button(self, pin: int, action: Dict) -> None:
        if not self.krpc:
            return
        atype = action.get("type")
        if atype == "ag":
            self.krpc.trigger_action_group(int(action["value"]))
        elif atype == "gear_brakes":
            self.krpc.toggle_gear_and_brakes()
        elif atype == "map_toggle":
            self.krpc.toggle_map_camera()
        else:
            print(f"[GPIO] Action inconnue sur pin {pin}: {action}")

    def _update_throttle(self) -> None:
        if not self.pico or not self.krpc:
            return
        # Lever THROTTLE_CONTROL (par défaut pin 22 dans leviers_cfg)
        throttle_pin = next(
            (p for p, a in self.leviers_cfg.items() if a == "THROTTLE_CONTROL"), None
        )
        if throttle_pin is not None:
            lever = self.leviers.get(throttle_pin)
            if lever is not None and not lever.is_pressed:
                # Sécurité : lever OFF → coupe le throttle
                if self.krpc.throttle_state != 0.0:
                    self.krpc.set_throttle(0.0)
                return

        new_value = self.pico.get_throttle_if_changed()
        if new_value is not None:
            self.krpc.set_throttle(new_value)

    def _update_leds(self) -> None:
        if not self.krpc or not self.krpc.connected or not self.krpc.vessel:
            return

        # LEDs vertes : SAS / RCS
        for pin, role in self.leds_vertes_cfg.items():
            led = self.leds_green.get(pin)
            if led is None:
                continue
            if role == "SAS":
                self._toggle_led(led, self.krpc.sas_state, "_sas_led")
            elif role == "RCS":
                self._toggle_led(led, self.krpc.rcs_state, "_rcs_led")

        # LEDs rouges : stage courant
        current_stage = self.krpc.telemetry.get("current_stage", 0)
        for pin, stages in self.leds_rouges_cfg.items():
            led = self.leds_red.get(pin)
            if led is None:
                continue
            active = current_stage in stages
            if active != self._stage_led_states.get(pin, False):
                (led.on if active else led.off)()
                self._stage_led_states[pin] = active

    def _toggle_led(self, led: LED, wanted: bool, attr: str) -> None:
        current = getattr(self, attr)
        if wanted == current:
            return
        (led.on if wanted else led.off)()
        setattr(self, attr, wanted)

    # ---- Cleanup -----------------------------------------------------

    def cleanup(self) -> None:
        try:
            for led in self.leds_red.values():
                led.off()
            for led in self.leds_green.values():
                led.off()
            print("[GPIO] LEDs éteintes")
        except Exception as e:
            print(f"[GPIO] Erreur cleanup: {e}")

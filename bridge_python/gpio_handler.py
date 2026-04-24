#!/usr/bin/env python3
"""
GPIO Handler - Entrées/sorties Raspberry Pi.

Lit boutons et leviers (event-driven via gpiozero callbacks), pilote les
LEDs (PWM pour la luminosité), déclenche les actions kRPC.
Toute la config vient de config.json (section hardware.gpio).
"""

import sys
from typing import Dict, Optional

try:
    from gpiozero import PWMLED, Button
    from gpiozero.pins.pigpio import PiGPIOFactory
except ImportError:
    print("✗ Module 'gpiozero' requis: pip install gpiozero pigpio")
    sys.exit(1)


def _coerce_int_keys(d: Dict) -> Dict:
    """Les clés JSON sont des strings, on les convertit en int."""
    return {int(k): v for k, v in d.items()}


def _parse_leviers(raw: Dict) -> (Dict[int, str], Dict[int, bool]):
    """Accepte deux formes pour chaque levier :
      - "22": "THROTTLE_CONTROL"                         (ancienne forme)
      - "22": { "name": "THROTTLE_CONTROL", "inverted": true }

    Retourne (names_by_pin, inverted_by_pin).
    """
    names: Dict[int, str] = {}
    inverted: Dict[int, bool] = {}
    for pin_str, value in raw.items():
        pin = int(pin_str)
        if isinstance(value, dict):
            names[pin] = str(value.get("name", ""))
            inverted[pin] = bool(value.get("inverted", False))
        else:
            names[pin] = str(value)
            inverted[pin] = False
    return names, inverted


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

        rouges_raw = config.get("leds_rouges", {})
        self.red_brightness = float(rouges_raw.get("brightness", 0.5))
        self.red_active_high = bool(rouges_raw.get("active_high", True))
        # "pins" si présent sinon on accepte le mapping à plat (rétro-compat).
        red_pins = rouges_raw.get("pins", {k: v for k, v in rouges_raw.items() if k.isdigit()})
        self.leds_rouges_cfg = _coerce_int_keys(red_pins)

        vertes_raw = config.get("leds_vertes", {})
        self.green_brightness = float(vertes_raw.get("brightness", self.red_brightness))
        self.green_active_high = bool(vertes_raw.get("active_high", True))
        green_pins = vertes_raw.get("pins", {k: v for k, v in vertes_raw.items() if k.isdigit()})
        self.leds_vertes_cfg = _coerce_int_keys(green_pins)

        self.leviers_cfg, self._lever_inverted = _parse_leviers(config.get("leviers", {}))
        self.boutons_cfg = _coerce_int_keys(config.get("boutons", {}))

        self.factory = None
        self.connected = False

        self.leds_red: Dict[int, PWMLED] = {}
        self.leds_green: Dict[int, PWMLED] = {}
        self.leviers: Dict[int, Button] = {}
        self.boutons: Dict[int, Button] = {}

        # LED rouge par nom d'action (ex: "STAGE_BOOSTERS" → pin 24).
        self._red_led_by_name: Dict[str, int] = {}
        # État "allumée" (True) / "éteinte" (False) pour chaque LED rouge.
        self._red_on: Dict[int, bool] = {}
        self._sas_on = False
        self._rcs_on = False
        self._throttle_lever_prev: Optional[bool] = None

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
        for pin, action_name in self.leds_rouges_cfg.items():
            try:
                led = PWMLED(pin, pin_factory=self.factory, active_high=self.red_active_high)
                self.leds_red[pin] = led
                self._red_on[pin] = True
                led.value = self.red_brightness
                if isinstance(action_name, str):
                    self._red_led_by_name[action_name] = pin
            except Exception as e:
                print(f"[GPIO] LED rouge {pin}: {e}")

        for pin, role in self.leds_vertes_cfg.items():
            try:
                led = PWMLED(pin, pin_factory=self.factory, active_high=self.green_active_high)
                led.value = 0.0
                self.leds_green[pin] = led
            except Exception as e:
                print(f"[GPIO] LED verte {pin}: {e}")

        for pin, action in self.leviers_cfg.items():
            try:
                btn = Button(pin, pull_up=True, pin_factory=self.factory, bounce_time=0.02)
                btn.when_pressed = self._make_lever_callback(pin, action, True)
                btn.when_released = self._make_lever_callback(pin, action, False)
                self.leviers[pin] = btn
            except Exception as e:
                print(f"[GPIO] Levier {pin}: {e}")

        for pin, action in self.boutons_cfg.items():
            try:
                btn = Button(pin, pull_up=True, pin_factory=self.factory, bounce_time=0.02)
                btn.when_pressed = self._make_button_callback(pin, action)
                self.boutons[pin] = btn
            except Exception as e:
                print(f"[GPIO] Bouton {pin}: {e}")

        print(
            f"[GPIO] {len(self.leds_red)} LED rouges (PWM dim {self.red_brightness:.2f}), "
            f"{len(self.leds_green)} vertes (dim {self.green_brightness:.2f}), "
            f"{len(self.leviers)} leviers, {len(self.boutons)} boutons"
        )
        # Trace d'orientation : permet de vérifier la correspondance entre la
        # position physique ON voulue et is_pressed (câblage pull-up/GND).
        for pin, name in self.leviers_cfg.items():
            btn = self.leviers.get(pin)
            if btn is None:
                continue
            inv = self._lever_inverted.get(pin, False)
            print(
                f"[GPIO] Levier {name} (pin {pin}) état initial : "
                f"is_pressed={btn.is_pressed} inverted={inv} → ON={self._lever_is_on(pin)}"
            )

    # ---- Callbacks event-driven --------------------------------------

    def _make_button_callback(self, pin: int, action: Dict):
        def _cb():
            self._dispatch_button(pin, action)
        return _cb

    def _make_lever_callback(self, pin: int, action: str, pressed_raw: bool):
        def _cb():
            inverted = self._lever_inverted.get(pin, False)
            on = (not pressed_raw) if inverted else pressed_raw
            print(f"[GPIO] Levier {action}: {'ON' if on else 'OFF'}")
            if action == "SAS" and self.krpc:
                self.krpc.set_sas(on)
            elif action == "RCS" and self.krpc:
                self.krpc.set_rcs(on)
            # THROTTLE_CONTROL : la boucle _update_throttle (20 Hz) détecte
            # la transition via _throttle_lever_prev et pousse la bonne valeur.
        return _cb

    def _dispatch_button(self, pin: int, action: Dict) -> None:
        if not self.krpc:
            return
        atype = action.get("type")
        name = action.get("name", "")
        if atype == "ag":
            value = int(action["value"])
            self.krpc.trigger_action_group(value % 10)
            # Si ce bouton correspond à une LED rouge, on l'éteint (PWM → 0).
            self._turn_off_red_led(name)
        elif atype == "gear_brakes":
            self.krpc.toggle_gear_and_brakes()
        elif atype == "map_toggle":
            self.krpc.toggle_map_camera()
        else:
            print(f"[GPIO] Action inconnue sur pin {pin}: {action}")

    def _turn_off_red_led(self, action_name: str) -> None:
        pin = self._red_led_by_name.get(action_name)
        if pin is None:
            return
        led = self.leds_red.get(pin)
        if led is None or not self._red_on.get(pin, False):
            return
        led.value = 0.0
        self._red_on[pin] = False
        print(f"[GPIO] LED rouge {action_name} (pin {pin}) éteinte")

    # ---- Sync état : leviers, throttle, retour au lancement ---------

    def resync_vessel_state(self) -> None:
        """Au changement de vaisseau (retour au lancement) : rallume toutes
        les LEDs rouges, pousse l'état des leviers vers kRPC.
        """
        print("[GPIO] Resync vaisseau : LEDs rouges rallumées, leviers poussés")
        for pin, led in self.leds_red.items():
            led.value = self.red_brightness
            self._red_on[pin] = True
        self._push_lever_states()

    def _push_lever_states(self) -> None:
        """Aligne KSP sur la position actuelle des leviers (SAS/RCS/throttle).

        N'accède pas au Pico : la lecture ADC est réservée au thread gpio_loop
        (contrainte threading.local de picod). On reset _throttle_lever_prev
        pour que le prochain tick de _update_throttle pousse la bonne valeur.
        """
        if not self.krpc:
            return
        for pin, action in self.leviers_cfg.items():
            if self.leviers.get(pin) is None:
                continue
            on = self._lever_is_on(pin)
            if action == "SAS":
                self.krpc.set_sas(on)
            elif action == "RCS":
                self.krpc.set_rcs(on)
            elif action == "THROTTLE_CONTROL" and not on:
                self.krpc.set_throttle(0.0)
        self._throttle_lever_prev = None

    # ---- Boucle (throttle + LEDs vertes) ----------------------------

    def update(self) -> None:
        if not self.connected:
            return
        self._update_throttle()
        self._update_green_leds()

    def _lever_is_on(self, pin: int) -> bool:
        """État logique du levier : applique l'inversion si configurée."""
        lever = self.leviers.get(pin)
        if lever is None:
            return False
        raw = lever.is_pressed
        return (not raw) if self._lever_inverted.get(pin, False) else raw

    def _throttle_lever_active(self) -> bool:
        throttle_pin = next(
            (p for p, a in self.leviers_cfg.items() if a == "THROTTLE_CONTROL"), None
        )
        if throttle_pin is None:
            return True
        return self._lever_is_on(throttle_pin)

    def _update_throttle(self) -> None:
        if not self.pico or not self.krpc:
            return

        active = self._throttle_lever_active()

        # Levier OFF : on force 0 et on reset le tracking Pico pour que
        # la prochaine transition OFF→ON reparte proprement.
        if not active:
            if self.krpc.throttle_state != 0.0:
                self.krpc.set_throttle(0.0)
            if self._throttle_lever_prev is not False:
                self.pico.reset_emit()
                self._throttle_lever_prev = False
            return

        # Transition OFF→ON (ou premier tick avec levier ON) : on pousse
        # immédiatement la valeur courante du pot, sans attendre un mouvement.
        if self._throttle_lever_prev is not True:
            value = self.pico.get_throttle()
            self.krpc.set_throttle(value)
            self.pico.sync_emit(value)
            self._throttle_lever_prev = True
            return

        # Régime établi : on ne pousse que sur changement au-delà du deadband.
        new_value = self.pico.get_throttle_if_changed()
        if new_value is not None:
            self.krpc.set_throttle(new_value)

    def _update_green_leds(self) -> None:
        if not self.krpc or not self.krpc.connected:
            return
        for pin, role in self.leds_vertes_cfg.items():
            led = self.leds_green.get(pin)
            if led is None:
                continue
            if role == "SAS":
                self._set_green(led, self.krpc.sas_state, "_sas_on")
            elif role == "RCS":
                self._set_green(led, self.krpc.rcs_state, "_rcs_on")

    def _set_green(self, led: PWMLED, wanted: bool, attr: str) -> None:
        current = getattr(self, attr)
        if wanted == current:
            return
        led.value = self.green_brightness if wanted else 0.0
        setattr(self, attr, wanted)

    # ---- Cleanup -----------------------------------------------------

    def cleanup(self) -> None:
        try:
            for led in self.leds_red.values():
                led.value = 0.0
            for led in self.leds_green.values():
                led.value = 0.0
            print("[GPIO] LEDs éteintes")
        except Exception as e:
            print(f"[GPIO] Erreur cleanup: {e}")

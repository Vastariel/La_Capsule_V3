#!/usr/bin/env python3
"""
Pico Handler - Lecture ADC du Pico RP2040 pour le throttle.

Lissage EMA (filtre exponentiel) + deadzone aux extrémités +
deadband de sortie pour éviter de spammer kRPC avec du bruit.
"""

import time
from typing import Optional

try:
    import picod
except ImportError:
    print("⚠ Module 'picod' non installé. Installez: pip install picod")
    picod = None


class PicoHandler:
    """Gère la lecture ADC du Pico avec lissage EMA."""

    def __init__(
        self,
        port: str = "/dev/ttyACM0",
        adc_channel: int = 0,
        alpha: float = 0.25,
        deadzone: float = 0.03,
        output_deadband: float = 0.01,
    ):
        self.port = port
        self.adc_channel = adc_channel
        self.alpha = alpha
        self.deadzone = deadzone
        self.output_deadband = output_deadband

        self.pico = None
        self.connected = False
        self.last_error: Optional[str] = None

        # État EMA : None tant qu'aucune valeur n'a été lue
        self._ema: Optional[float] = None
        self._last_emitted: float = 0.0

        self.connect()

    # ---- Connexion ---------------------------------------------------

    def connect(self) -> bool:
        if picod is None:
            self.last_error = "picod module not installed"
            return False

        try:
            print(f"[PICO] Connexion sur {self.port}...", end=" ", flush=True)
            self.pico = picod.pico(device=self.port)
            time.sleep(0.3)
            self.connected = self.pico is not None
            print("✓ OK" if self.connected else "✗ Échec")
            return self.connected
        except Exception as e:
            self.last_error = str(e)
            print(f"✗ Erreur: {e}", flush=True)
            self.connected = False
            return False

    def disconnect(self) -> None:
        try:
            if self.pico:
                self.pico.close()
        except Exception:
            pass
        self.connected = False

    # ---- Lecture ----------------------------------------------------

    def read_raw(self, channel: Optional[int] = None) -> Optional[int]:
        """Lit la valeur brute ADC (0-4095) ou None en cas d'erreur."""
        if not self.connected or not self.pico:
            return None
        ch = self.adc_channel if channel is None else channel
        try:
            _status, _ch, val = self.pico.adc_read(ch)
            return val
        except Exception:
            return None

    def read_throttle_raw(self) -> Optional[float]:
        """Valeur normalisée 0..1 lissée (EMA), sans deadzone ni deadband."""
        raw = self.read_raw(self.adc_channel)
        if raw is None:
            return None

        norm = max(0.0, min(1.0, raw / 4095.0))
        if self._ema is None:
            self._ema = norm
        else:
            self._ema = self.alpha * norm + (1.0 - self.alpha) * self._ema
        return self._ema

    def get_throttle(self) -> float:
        """Throttle lissé avec deadzone aux bords (0 et 1).

        Retourne toujours une valeur : si l'ADC est indisponible, renvoie
        la dernière valeur émise pour éviter les sauts.
        """
        ema = self.read_throttle_raw()
        if ema is None:
            return self._last_emitted

        if ema < self.deadzone:
            return 0.0
        if ema > 1.0 - self.deadzone:
            return 1.0
        return ema

    def get_throttle_if_changed(self) -> Optional[float]:
        """Renvoie la nouvelle valeur throttle uniquement si elle a bougé
        au-delà du deadband de sortie. Sinon None.
        """
        value = self.get_throttle()
        if abs(value - self._last_emitted) >= self.output_deadband or (
            value in (0.0, 1.0) and self._last_emitted != value
        ):
            self._last_emitted = value
            return value
        return None

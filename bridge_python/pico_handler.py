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
        calibration: Optional[list] = None,
    ):
        self.port = port
        self.adc_channel = adc_channel
        self.alpha = alpha
        self.deadzone = deadzone
        self.output_deadband = output_deadband

        # Table d'étalonnage : corrige la non-linéarité du potentiomètre.
        # Format en config : [[fraction, raw_adc], ...] (fraction 0..1).
        # Stockée triée par valeur brute croissante : (raw, fraction).
        self._calib = self._build_calibration(calibration)

        self.pico = None
        self.connected = False
        self.last_error: Optional[str] = None

        # État EMA : None tant qu'aucune valeur n'a été lue
        self._ema: Optional[float] = None
        self._last_emitted: float = 0.0

        # Pas de self.connect() ici : picod stocke son état dans un
        # threading.local() — la connexion doit être faite depuis le thread
        # qui fera ensuite les adc_read(). L'appelant (gpio_loop) s'en charge.

    # ---- Étalonnage --------------------------------------------------

    @staticmethod
    def _build_calibration(calibration: Optional[list]) -> list:
        """Transforme [[fraction, raw], ...] en liste (raw, fraction) triée
        par valeur brute croissante. Retourne [] si pas d'étalonnage valide.
        """
        if not calibration:
            return []
        pts = []
        for item in calibration:
            try:
                frac, raw = float(item[0]), float(item[1])
            except (TypeError, ValueError, IndexError):
                continue
            pts.append((raw, max(0.0, min(1.0, frac))))
        if len(pts) < 2:
            return []
        # Tri par raw croissant ; en cas de doublon de raw, on garde le 1er.
        pts.sort(key=lambda p: p[0])
        dedup = []
        for raw, frac in pts:
            if not dedup or raw > dedup[-1][0]:
                dedup.append((raw, frac))
        return dedup if len(dedup) >= 2 else []

    def _apply_calibration(self, raw: float) -> float:
        """Convertit une valeur brute ADC en fraction 0..1 corrigée via
        l'interpolation linéaire par morceaux de la table d'étalonnage.

        Sans table, retombe sur la normalisation linéaire raw/4095.
        """
        pts = self._calib
        if not pts:
            return max(0.0, min(1.0, raw / 4095.0))
        if raw <= pts[0][0]:
            return pts[0][1]
        if raw >= pts[-1][0]:
            return pts[-1][1]
        for i in range(len(pts) - 1):
            r0, f0 = pts[i]
            r1, f1 = pts[i + 1]
            if r0 <= raw <= r1:
                t = (raw - r0) / (r1 - r0)
                return f0 + t * (f1 - f0)
        return max(0.0, min(1.0, raw / 4095.0))

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

        norm = self._apply_calibration(raw)
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

    def sync_emit(self, value: Optional[float] = None) -> float:
        """Aligne le tracking d'émission sur `value` (ou la valeur courante).

        À appeler quand un consommateur pousse une valeur sans passer par
        `get_throttle_if_changed()`, pour que celle-ci ne réémette que sur
        un vrai changement ultérieur.
        """
        if value is None:
            value = self.get_throttle()
        self._last_emitted = value
        return value

    def reset_emit(self) -> None:
        """Reset l'EMA et le tracking d'émission : le prochain appel à
        `get_throttle_if_changed()` traitera la valeur courante comme neuve.
        """
        self._ema = None
        self._last_emitted = 0.0

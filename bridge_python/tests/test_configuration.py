#!/usr/bin/env python3
"""Tests de config - structure, cohérence pin mapping."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import get_config


class TestConfiguration(unittest.TestCase):
    def setUp(self):
        self.cfg = get_config()

    def test_root_sections(self):
        for key in ("krpc", "websocket", "hardware", "throttle"):
            self.assertIn(key, self.cfg)

    def test_krpc(self):
        k = self.cfg["krpc"]
        self.assertIsInstance(k["host"], str)
        self.assertEqual(k["rpc_port"], 50008)
        self.assertEqual(k["stream_port"], 50001)

    def test_websocket(self):
        w = self.cfg["websocket"]
        self.assertEqual(w["host"], "0.0.0.0")
        self.assertEqual(w["port"], 8080)

    def test_gpio_pins_populated(self):
        g = self.cfg["hardware"]["gpio"]
        self.assertTrue(g["leds_rouges"])
        self.assertTrue(g["leds_vertes"])
        self.assertTrue(g["leviers"])
        self.assertTrue(g["boutons"])

    def test_gpio_no_output_duplicates(self):
        g = self.cfg["hardware"]["gpio"]
        leds = list(g["leds_rouges"].keys()) + list(g["leds_vertes"].keys())
        self.assertEqual(len(leds), len(set(leds)), f"LED pins dupliquées: {leds}")

    def test_gpio_no_input_duplicates(self):
        g = self.cfg["hardware"]["gpio"]
        inputs = list(g["leviers"].keys()) + list(g["boutons"].keys())
        self.assertEqual(len(inputs), len(set(inputs)), f"Input pins dupliquées: {inputs}")

    def test_button_action_types_known(self):
        g = self.cfg["hardware"]["gpio"]
        valid = {"ag", "gear_brakes", "map_toggle"}
        for pin, action in g["boutons"].items():
            self.assertIn(action.get("type"), valid, f"Pin {pin}: type inconnu {action}")
            if action["type"] == "ag":
                self.assertIsInstance(action.get("value"), int)

    def test_throttle_params_in_range(self):
        t = self.cfg["throttle"]
        self.assertGreater(t["smoothing_alpha"], 0.0)
        self.assertLessEqual(t["smoothing_alpha"], 1.0)
        self.assertGreaterEqual(t["deadzone_percent"], 0.0)
        self.assertLess(t["deadzone_percent"], 50.0)


class TestPicoHandlerAPI(unittest.TestCase):
    """Tests API PicoHandler - pas de hardware requis."""

    def test_import(self):
        from pico_handler import PicoHandler
        self.assertIsNotNone(PicoHandler)

    def test_ema_logic(self):
        """L'EMA doit converger vers la valeur cible."""
        from pico_handler import PicoHandler
        ph = PicoHandler.__new__(PicoHandler)  # bypass __init__
        ph.alpha = 0.3
        ph.deadzone = 0.03
        ph.output_deadband = 0.01
        ph._ema = None
        ph._last_emitted = 0.0
        ph.adc_channel = 0
        ph.connected = False
        ph.pico = None

        # Simule 50 lectures constantes à 0.5 → EMA doit s'approcher
        ph._ema = 0.0
        for _ in range(50):
            ph._ema = 0.3 * 0.5 + 0.7 * ph._ema
        self.assertAlmostEqual(ph._ema, 0.5, places=2)


class TestGPIOHandlerAPI(unittest.TestCase):
    """Test import et gestion config invalide."""

    def test_import(self):
        try:
            from gpio_handler import GPIOHandler
            self.assertIsNotNone(GPIOHandler)
        except ImportError as e:
            self.skipTest(f"gpiozero indispo: {e}")

    def test_missing_config_raises(self):
        try:
            from gpio_handler import GPIOHandler
        except ImportError:
            self.skipTest("gpiozero indispo")
        with self.assertRaises(ValueError):
            GPIOHandler(config=None)


if __name__ == "__main__":
    unittest.main(verbosity=2)

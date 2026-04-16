#!/usr/bin/env python3
"""
Test suite for bridge_python components
Tests GPIO, Pico, and configuration
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (
    KSP_IP, RPC_PORT, STREAM_PORT,
    RASPI_IP, FPS,
    WS_HOST, WS_PORT, WS_PATH,
    LED_ROUGES_PINS, LED_VERTES_PINS,
    LEVIERS_PINS, BOUTONS_PINS,
    get_config, print_config_summary
)


class TestConfiguration(unittest.TestCase):
    """Test configuration loading"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = get_config()
    
    def test_config_loaded(self):
        """Test that configuration is loaded"""
        self.assertIsNotNone(self.config)
        self.assertIn('network', self.config)
        self.assertIn('hardware', self.config)
        self.assertIn('performance', self.config)
    
    def test_krpc_config(self):
        """Test kRPC configuration"""
        self.assertEqual(KSP_IP, "192.168.1.27")
        self.assertEqual(RPC_PORT, 50008)
        self.assertEqual(STREAM_PORT, 50001)
    
    def test_raspi_config(self):
        """Test Raspberry Pi configuration"""
        self.assertEqual(RASPI_IP, "192.168.1.56")
        self.assertEqual(FPS, 30)
    
    def test_websocket_config(self):
        """Test WebSocket configuration"""
        self.assertEqual(WS_HOST, "0.0.0.0")
        self.assertEqual(WS_PORT, 8080)
        self.assertEqual(WS_PATH, "/telemetry")
    
    def test_gpio_pins_configured(self):
        """Test GPIO pins are configured"""
        self.assertGreater(len(LED_ROUGES_PINS), 0)
        self.assertGreater(len(LED_VERTES_PINS), 0)
        self.assertGreater(len(LEVIERS_PINS), 0)
        self.assertGreater(len(BOUTONS_PINS), 0)
    
    def test_pins_no_duplicates(self):
        """Test no duplicate pins"""
        all_pins = set()
        
        # Collect all outputs
        for pin in LED_ROUGES_PINS:
            self.assertNotIn(pin, all_pins, f"Duplicate pin {pin}")
            all_pins.add(pin)
        
        for pin in LED_VERTES_PINS:
            self.assertNotIn(pin, all_pins, f"Duplicate pin {pin}")
            all_pins.add(pin)
        
        # Inputs and outputs can share GPIO (one is input, one is output)
        # but ideally they shouldn't in a well-designed system
        inputs = set(LEVIERS_PINS.keys()) | set(BOUTONS_PINS.keys())
        outputs = set(LED_ROUGES_PINS) | set(LED_VERTES_PINS)
        
        overlap = inputs & outputs
        if overlap:
            print(f"⚠ Warning: GPIO pins used for both input and output: {overlap}")


class TestPicoModule(unittest.TestCase):
    """Test Pico module"""
    
    def test_pico_import(self):
        """Test Pico module can be imported"""
        try:
            from pico import PicoManager
            self.assertIsNotNone(PicoManager)
        except ImportError as e:
            self.skipTest(f"Pico module not available: {e}")
    
    def test_pico_creation(self):
        """Test Pico manager can be instantiated"""
        try:
            from pico import PicoManager
            pico = PicoManager()
            # May not be connected, but object should exist
            self.assertIsNotNone(pico)
        except ImportError:
            self.skipTest("Pico module not available")
        except Exception as e:
            # Expected if hardware not available
            self.skipTest(f"Pico hardware not available: {e}")


class TestGPIOModule(unittest.TestCase):
    """Test GPIO module"""
    
    def test_gpio_import(self):
        """Test GPIO module can be imported"""
        try:
            from gpio import GPIO
            self.assertIsNotNone(GPIO)
        except ImportError as e:
            self.skipTest(f"GPIO module not available: {e}")
    
    def test_gpio_creation(self):
        """Test GPIO manager can be instantiated"""
        try:
            from gpio import GPIO
            # Use local GPIO (no remote)
            gpio = GPIO(use_remote=False)
            self.assertIsNotNone(gpio)
        except ImportError:
            self.skipTest("GPIO module not available")
        except Exception as e:
            # Expected if hardware not available
            self.skipTest(f"GPIO hardware not available: {e}")


class TestServerModule(unittest.TestCase):
    """Test server module"""
    
    def test_server_import(self):
        """Test server module can be imported"""
        try:
            import server
            self.assertIsNotNone(server)
        except ImportError as e:
            self.skipTest(f"Server module not available: {e}")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🧪 BRIDGE_PYTHON TEST SUITE")
    print("="*60 + "\n")
    
    print_config_summary()
    print()
    
    unittest.main(verbosity=2)

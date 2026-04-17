#!/usr/bin/env python3
"""
Config Loader - Loads centralized configuration from config.json
This module provides a single point of configuration for the entire system.
Searches for config.json in multiple locations for backwards compatibility.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Find the project root and config file
def _find_config_file() -> Path:
    """Find config.json - searches in multiple locations"""
    current = Path(__file__).resolve()
    
    # Go up until we find config.json
    search_depth = 0
    while current != current.parent and search_depth < 10:
        # Try current directory (and parents) for config.json
        config_paths = [
            current.parent.parent / "config.json",              # New location: root/config.json
            current.parent.parent / "setup" / "config.json",   # Old location: setup/config.json
            current / "config.json",                            # Current dir
            Path("/home/capsule/Desktop/La_Capsule_V3/config.json"),  # Absolute path
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                return config_path
        
        current = current.parent
        search_depth += 1
    
    raise FileNotFoundError(
        "Cannot find config.json. Searched in:\n"
        "  1. /config.json (root)\n"
        "  2. setup/config.json (legacy)\n"
        "  3. Current directory"
    )

def _load_config() -> Dict[str, Any]:
    """Load configuration from config.json"""
    try:
        config_path = _find_config_file()
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"✓ Configuration chargée depuis {config_path}")
        return config
    except FileNotFoundError as e:
        print(f"✗ Erreur: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ Erreur JSON dans config.json: {e}")
        sys.exit(1)


# Load config globally on import
CONFIG = _load_config()

# ===== KRPC Configuration =====
KSP_IP = CONFIG.get("network", {}).get("ksp_pc", {}).get("ip", "192.168.1.31")
RPC_PORT = CONFIG.get("network", {}).get("ksp_pc", {}).get("krpc_rpc_port", 50008)
STREAM_PORT = CONFIG.get("network", {}).get("ksp_pc", {}).get("krpc_stream_port", 50001)

# ===== Raspi Configuration =====
RASPI_IP = CONFIG.get("network", {}).get("raspi", {}).get("ip", "192.168.1.56")
FPS = CONFIG.get("performance", {}).get("fps", 30)

# ===== WebSocket Configuration =====
WS_HOST = CONFIG.get("network", {}).get("bridge_websocket", {}).get("host", "0.0.0.0")
WS_PORT = CONFIG.get("network", {}).get("bridge_websocket", {}).get("port", 8080)
WS_PATH = CONFIG.get("network", {}).get("bridge_websocket", {}).get("path", "/telemetry")

# ===== Hardware Configuration =====
PICO_PORT = CONFIG.get("hardware", {}).get("pico", {}).get("port", "/dev/ttyACM0")
PICO_BAUD = CONFIG.get("hardware", {}).get("pico", {}).get("baud_rate", 115200)
PICO_ADC_CHANNELS = CONFIG.get("hardware", {}).get("pico", {}).get("adc_channels", {})

LED_ROUGES_PINS = CONFIG.get("hardware", {}).get("gpio_raspi", {}).get("leds_rouges", [24, 27, 25, 21])
LED_VERTES_PINS = CONFIG.get("hardware", {}).get("gpio_raspi", {}).get("leds_vertes", [18, 12])
LEVIERS_PINS = {int(k): v for k, v in CONFIG.get("hardware", {}).get("gpio_raspi", {}).get("leviers", {}).items()}
BOUTONS_PINS = {int(k): v for k, v in CONFIG.get("hardware", {}).get("gpio_raspi", {}).get("boutons", {}).items()}

# ===== Performance Configuration =====
THROTTLE_SMOOTHING_WINDOW = CONFIG.get("performance", {}).get("throttle_smoothing_window", 10)
THROTTLE_DEADZONE = CONFIG.get("performance", {}).get("throttle_deadzone_percent", 2.0) / 100.0
THROTTLE_CHANGE_THRESHOLD = CONFIG.get("performance", {}).get("throttle_change_threshold_percent", 1.0) / 100.0

# ===== Telemetry Configuration =====
REFRESH_CRITICAL = CONFIG.get("telemetry", {}).get("refresh_rates", {}).get("critical", 1)
REFRESH_IMPORTANT = CONFIG.get("telemetry", {}).get("refresh_rates", {}).get("important", 5)
REFRESH_NORMAL = CONFIG.get("telemetry", {}).get("refresh_rates", {}).get("normal", 10)

# ===== Logging Configuration =====
LOG_LEVEL = CONFIG.get("logging", {}).get("level", "INFO")
LOG_FILE = CONFIG.get("logging", {}).get("file", "/tmp/bridge.log")
LOG_TO_CONSOLE = CONFIG.get("logging", {}).get("console", True)


def get_config() -> Dict[str, Any]:
    """Get the full configuration dictionary"""
    return CONFIG


def print_config_summary():
    """Print a summary of the configuration"""
    print("=" * 60)
    print("🔧 CONFIGURATION SUMMARY")
    print("=" * 60)
    print(f"KSP PC: {KSP_IP}:{RPC_PORT} (Stream: {STREAM_PORT})")
    print(f"Raspi: {RASPI_IP}")
    print(f"WebSocket: ws://{WS_HOST}:{WS_PORT}{WS_PATH}")
    print(f"Pico: {PICO_PORT} @ {PICO_BAUD} baud")
    print(f"GPIO LEDs: {len(LED_ROUGES_PINS)} red, {len(LED_VERTES_PINS)} green")
    print(f"GPIO Inputs: {len(LEVIERS_PINS)} leviers, {len(BOUTONS_PINS)} buttons")
    print(f"Performance: {FPS} FPS")
    print("=" * 60)


if __name__ == "__main__":
    print_config_summary()

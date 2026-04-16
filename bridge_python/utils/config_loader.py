#!/usr/bin/env python3
"""
Config Loader - Loads centralized configuration from setup/config.json
This module provides a single point of configuration for the entire system.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Find the project root (where setup/config.json is located)
def _find_project_root() -> Path:
    """Find the project root by looking for setup/config.json"""
    current = Path(__file__).resolve()
    
    # Go up until we find setup/config.json
    while current != current.parent:
        config_path = current.parent.parent / "setup" / "config.json"
        if config_path.exists():
            return current.parent.parent
        current = current.parent
    
    raise FileNotFoundError(
        "Cannot find project root. Make sure setup/config.json exists."
    )

def _load_config() -> Dict[str, Any]:
    """Load configuration from setup/config.json"""
    try:
        project_root = _find_project_root()
        config_path = project_root / "setup" / "config.json"
        
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
KSP_IP = CONFIG["network"]["ksp_pc"]["ip"]
RPC_PORT = CONFIG["network"]["ksp_pc"]["krpc_rpc_port"]
STREAM_PORT = CONFIG["network"]["ksp_pc"]["krpc_stream_port"]

# ===== Raspi Configuration =====
RASPI_IP = CONFIG["network"]["raspi"]["ip"]
FPS = CONFIG["performance"]["fps"]

# ===== WebSocket Configuration =====
WS_HOST = CONFIG["network"]["bridge_websocket"]["host"]
WS_PORT = CONFIG["network"]["bridge_websocket"]["port"]
WS_PATH = CONFIG["network"]["bridge_websocket"]["path"]

# ===== Hardware Configuration =====
PICO_PORT = CONFIG["hardware"]["pico"]["port"]
PICO_BAUD = CONFIG["hardware"]["pico"]["baud_rate"]
PICO_ADC_CHANNELS = CONFIG["hardware"]["pico"]["adc_channels"]

LED_ROUGES_PINS = CONFIG["hardware"]["gpio_raspi"]["leds_rouges"]
LED_VERTES_PINS = CONFIG["hardware"]["gpio_raspi"]["leds_vertes"]
LEVIERS_PINS = {int(k): v for k, v in CONFIG["hardware"]["gpio_raspi"]["leviers"].items()}
BOUTONS_PINS = {int(k): v for k, v in CONFIG["hardware"]["gpio_raspi"]["boutons"].items()}

# ===== Performance Configuration =====
THROTTLE_SMOOTHING_WINDOW = CONFIG["performance"]["throttle_smoothing_window"]
THROTTLE_DEADZONE = CONFIG["performance"]["throttle_deadzone_percent"] / 100.0
THROTTLE_CHANGE_THRESHOLD = CONFIG["performance"]["throttle_change_threshold_percent"] / 100.0

# ===== Telemetry Configuration =====
REFRESH_CRITICAL = CONFIG["telemetry"]["refresh_rates"]["critical"]
REFRESH_IMPORTANT = CONFIG["telemetry"]["refresh_rates"]["important"]
REFRESH_NORMAL = CONFIG["telemetry"]["refresh_rates"]["normal"]

# ===== Logging Configuration =====
LOG_LEVEL = CONFIG["logging"]["level"]
LOG_FILE = CONFIG["logging"]["file"]
LOG_TO_CONSOLE = CONFIG["logging"]["console"]


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

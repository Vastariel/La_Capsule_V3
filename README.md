# La Capsule V3 - KSP Hardware Control System

A complete system for controlling **Kerbal Space Program** (KSP) with physical hardware (buttons, switches, LEDs) connected via Raspberry Pi, and displaying telemetry in Godot.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  PC: Kerbal Space Program (KSP) + kRPC Server                   │
│  Listens on: 192.168.1.25:50008 (RPC), :50001 (Stream)         │
└─────────────────────────┬───────────────────────────────────────┘
                          │ kRPC Protocol
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│  RASPBERRY PI 4 (192.168.1.56)                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ bridge_python (Main Controller)                             ││
│  │  ├─ api.py         → kRPC telemetry collection             ││
│  │  ├─ gpio.py        → GPIO control (buttons, LEDs)          ││
│  │  ├─ pico.py        → ADC readings (potentiomètres)         ││
│  │  └─ server.py      → WebSocket server (ws://0.0.0.0:8080)  ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  USB ┌──────────────────────────────────────────────────────┐  │
│  ├──▶│ Pico (RP2040) Microcontroller                        │  │
│  │   │ • ADC Channel 0: Throttle Potentiometer              │  │
│  │   └──────────────────────────────────────────────────────┘  │
│  │                                                              │
│  GPIO┌──────────────────────────────────────────────────────┐  │
│  ├──▶│ GPIO Inputs (Buttons & Switches)                     │  │
│  │   │ • 3 Leviers (SAS, RCS, Throttle control)            │  │
│  │   │ • 10 Boutons (Stage, Parachute, Landing gear, etc.) │  │
│  │   └──────────────────────────────────────────────────────┘  │
│  │                                                              │
│  GPIO┌──────────────────────────────────────────────────────┐  │
│  └──▶│ GPIO Outputs (LEDs)                                 │  │
│      │ • 4 Red LEDs (Stage indicators)                     │  │
│      │ • 2 Green LEDs (Levier state indicators)            │  │
│      └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          │ WebSocket
                          │ ws://192.168.1.56:8080/telemetry
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│  CLIENT PC: Godot UI                                            │
│  • Receives telemetry data from bridge_python                  │
│  • Displays real-time KSP status                               │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
La_Capsule_V3/
├── bridge_python/              # Main controller on Raspberry Pi
│   ├── utils/
│   │   ├── config_loader.py   # Centralized config loading
│   │   └── __init__.py
│   ├── tests/
│   │   ├── test_configuration.py
│   │   ├── __init__.py
│   │   └── README.md
│   ├── api.py                 # kRPC telemetry collection
│   ├── config.py              # Legacy config (loads from config_loader)
│   ├── gpio.py                # GPIO operations (buttons, LEDs)
│   ├── pico.py                # Pico ADC management
│   ├── server.py              # WebSocket server for Godot
│   ├── main.py                # Main entry point
│   └── requirements.txt        # Python dependencies
│
├── raspi_controller/          # Alternative controller (optional)
│   ├── gpio_monitor.py
│   ├── pico_monitor.py
│   ├── websocket_client.py
│   ├── main.py
│   └── requirements.txt
│
├── godot_ui/                  # Godot project
│   ├── Assets/
│   ├── Fonts/
│   ├── Scenes/
│   ├── Scripts/
│   ├── project.godot
│   └── export_presets.cfg
│
├── setup/
│   ├── config.json            # ⭐ CENTRALIZED CONFIGURATION
│   └── install_pi.sh          # Installation script for Raspberry Pi
│
└── README.md
```

## ⚙️ Configuration

**All configuration is centralized in `setup/config.json`**. This file contains:

- **Network**: IP addresses and ports for KSP PC, Raspberry Pi, WebSocket
- **Hardware**: GPIO pins, Pico ADC channels, LED mappings
- **Performance**: FPS, update intervals, throttle smoothing
- **Telemetry**: Refresh rates for different data types
- **Logging**: Log level, file path, console output

### Example Config

```json
{
  "network": {
    "ksp_pc": {
      "ip": "192.168.1.25",
      "krpc_rpc_port": 50008,
      "krpc_stream_port": 50001
    },
    "raspi": {
      "ip": "192.168.1.56"
    },
    "bridge_websocket": {
      "host": "0.0.0.0",
      "port": 8080,
      "path": "/telemetry"
    }
  },
  "hardware": {
    "pico": {
      "port": "/dev/ttyACM0",
      "adc_channels": {
        "0": "Throttle potentiometer"
      }
    },
    "gpio_raspi": {
      "leds_rouges": [24, 27, 25, 21],
      "leviers": {"16": "SAS", "26": "RCS", "22": "THROTTLE_CONTROL"},
      "boutons": {"6": "HEAT_SHIELD", ...}
    }
  }
}
```

## 🚀 Installation

### 1. Install dependencies on Raspberry Pi

```bash
sudo apt update
sudo apt install python3-pip python3-venv pigpio

cd ~/La_Capsule_V3/bridge_python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Setup kRPC on PC

Install kRPC server mod in KSP. Configure to listen on the correct IP/port.

### 3. Run bridge_python on Raspberry Pi

```bash
cd ~/La_Capsule_V3/bridge_python
source venv/bin/activate
python3 main.py
```

### 4. Run Godot client

```bash
cd ~/La_Capsule_V3/godot_ui
godot
```

## 🧪 Testing

```bash
cd bridge_python
python3 -m pytest tests/ -v

# Run specific test
python3 -m pytest tests/test_configuration.py::TestConfiguration::test_krpc_config -v

# Test GPIO manually (local)
python3 gpio.py

# Test Pico manually
python3 pico.py

# Test configuration
python3 -m utils.config_loader
```

## 📊 Modules

### api.py
Handles kRPC connection and telemetry:
- Connects to KSP on PC
- Collects vessel data (altitude, speed, apoapsis, periapsis, etc.)
- Updates throttle from Pico ADC
- Manages control (SAS, RCS, staging)

### gpio.py
Manages Raspberry Pi GPIO:
- Controls LEDs (red for staging, green for levier state)
- Reads buttons (momentary and continuous)
- Reads switches (leviers)
- Triggers kRPC actions when buttons pressed

### pico.py
Manages Pico ADC readings:
- Reads throttle potentiometer
- Applies smoothing (10-sample moving average)
- Handles disconnections gracefully
- Provides raw, smoothed, percentage, and normalized outputs

### server.py
WebSocket server for Godot:
- Broadcasts telemetry every 100ms
- Listens on `0.0.0.0:8080/telemetry`
- Clients connect from a network

## 🔧 Customization

### Change Network Configuration

Edit `setup/config.json`:

```json
"network": {
  "ksp_pc": {"ip": "YOUR_PC_IP"},
  "raspi": {"ip": "YOUR_RASPI_IP"},
  "bridge_websocket": {"host": "0.0.0.0", "port": YOUR_PORT}
}
```

### Reconfigure GPIO Pins

Edit GPIO pins in `setup/config.json`:

```json
"gpio_raspi": {
  "leds_rouges": [24, 27, 25, 21],
  "boutons": {"6": "HEAT_SHIELD", "13": "PARACHUTE", ...}
}
```

### Adjust Throttle Smoothing

Edit `setup/config.json`:

```json
"performance": {
  "throttle_smoothing_window": 10,
  "throttle_deadzone_percent": 2.0,
  "throttle_change_threshold_percent": 1.0
}
```

## 🐛 Troubleshooting

### "Cannot connect to KSP"
- Ensure KSP is running with kRPC server active
- Check IP address and ports in `config.json`
- Verify network connectivity: `ping 192.168.1.25`

### "GPIO pins not responding"
- Verify pins in `config.json` match your wiring
- Check for duplicate pins (input and output)
- Test with: `python3 gpio.py`

### "Pico not detected"
- Check USB connection: `ls /dev/ttyACM0`
- Verify Pico is flashed with correct firmware
- Run: `python3 pico.py`

### "WebSocket not connecting"
- Check firewall allows port 8080
- Verify Godot connects to correct IP: `ws://192.168.1.56:8080/telemetry`
- Check server is running: `netstat -an | grep 8080`

## 📝 License

[Your License Here]

## 👥 Contributors

[List Contributors Here]
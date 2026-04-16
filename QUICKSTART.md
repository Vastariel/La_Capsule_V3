# Quick Start Guide

## Prerequisites

- **PC with KSP**: Kerbal Space Program with kRPC mod installed
- **Raspberry Pi 4**: Running Raspberry Pi OS with Python 3.9+
- **Pico RP2040**: Connected via USB to Raspberry Pi
- **Network**: All devices on same network (or configured with correct IPs)
- **GPIO Hardware**: Buttons, switches, LEDs wired to Raspberry Pi GPIO pins

## Step 1: Configure the System

Edit `setup/config.json` with your network setup:

```json
{
  "network": {
    "ksp_pc": {
      "ip": "YOUR_PC_IP_ADDRESS",
      "krpc_rpc_port": 50008,
      "krpc_stream_port": 50001
    },
    "raspi": {
      "ip": "YOUR_RASPI_IP_ADDRESS"
    },
    "bridge_websocket": {
      "host": "0.0.0.0",
      "port": 8080
    }
  },
  "hardware": {
    "pico": {
      "port": "/dev/ttyACM0"
    },
    "gpio_raspi": {
      "leds_rouges": [24, 27, 25, 21],
      "leds_vertes": [18, 12],
      "leviers": {
        "16": "SAS",
        "26": "RCS",
        "22": "THROTTLE_CONTROL"
      },
      "boutons": {
        "6": "HEAT_SHIELD",
        "13": "PARACHUTE",
        "11": "LANDING_GEAR",
        "5": "TOGGLE_MAP",
        "20": "ENGINE_START",
        "7": "FAIRING",
        "23": "STAGE_BOOSTERS",
        "8": "STAGE_1",
        "4": "STAGE_2",
        "19": "STAGE_3"
      }
    }
  }
}
```

**Find your IPs**:
```bash
# On PC
ipconfig getifaddr en0  # macOS
hostname -I             # Linux

# On Raspberry Pi
hostname -I
```

## Step 2: Verify Your Raspberry Pi

Find your Raspberry Pi's IP:
```bash
ssh pi@raspberrypi.local
hostname -I
# Returns something like: 192.168.1.56
```

## Step 3: Test Configuration

On Raspberry Pi:
```bash
cd ~/La_Capsule_V3/bridge_python
python3 utils/config_loader.py
```

Expected output:
```
✓ Configuration chargée depuis .../setup/config.json
============================================================
🔧 CONFIGURATION SUMMARY
============================================================
KSP PC: 192.168.1.25:50008 (Stream: 50001)
Raspi: 192.168.1.56
WebSocket: ws://0.0.0.0:8080/telemetry
...
```

## Step 4: Test Hardware Components

### Test GPIO
```bash
cd ~/La_Capsule_V3/bridge_python
python3 gpio.py
```

This will:
- Turn on red LEDs one by one (5 seconds each)
- Wait for button presses and print their status
- (Press Ctrl+C to exit)

### Test Pico ADC
```bash
python3 pico.py
```

This will:
- Connect to Pico on /dev/ttyACM0
- Read throttle potentiometer every 0.5 seconds
- Show raw, smoothed, and percentage values

### Test Configuration
```bash
python3 -m pytest tests/test_configuration.py -v
```

## Step 5: Install Dependencies

On Raspberry Pi:
```bash
cd ~/La_Capsule_V3/bridge_python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

On PC (for running server locally during development):
```bash
cd La_Capsule_V3/bridge_python
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Step 6: Start KSP Server

1. Launch Kerbal Space Program
2. Start a flight (or load existing save)
3. Ensure kRPC server is running:
   - In-game: Alt+F2 (or check kRPC console)
   - Should show: "Server running on 0.0.0.0:50008"

## Step 7: Run the Bridge

On Raspberry Pi:
```bash
cd ~/La_Capsule_V3/bridge_python
source venv/bin/activate
python3 main.py
```

Expected output:
```
============================================================
🔧 CONFIGURATION SUMMARY
============================================================
KSP PC: 192.168.1.25:50008 (Stream: 50001)
...
✓ server KRPC connecté et en fonctionnement
✓ Serveur WebSocket démarré
✓ GPIO initialisé - Connecté à 192.168.1.56
✓ Pico connecté sur /dev/ttyACM0
```

## Step 8: Connect Godot Client

1. Open Godot project: `godot_ui/project.godot`
2. Look for WebSocket connection setup in scripts
3. Edit connection URL to: `ws://192.168.1.56:8080/telemetry`
4. Hit "Play" (F5)

You should see telemetry data flowing in real-time!

## Step 9: Test Control Loop

1. **From Physical Hardware**:
   - Press buttons → LEDs light up
   - Move switches → Godot shows state change
   - Turn throttle potentiometer → Vessel throttle changes in KSP

2. **From KSP**:
   - Activate SAS in-game → Green LED lights
   - Stage rocket → Red LED pulses

3. **From Godot** (if UI buttons implemented):
   - Click UI button → GPIO LED responds

## Troubleshooting

### "Connection refused" (KSP)
```bash
# On PC, check kRPC is listening
netstat -an | grep 50008

# Or test connection from Raspi
python3 -c "import krpc; conn = krpc.connect(address='PC_IP', rpc_port=50008)"
```

### "GPIO permission denied"
```bash
# pigpio daemon must be running
sudo systemctl start pigpiod
# Or manually:
sudo pigpiod
```

### "Pico not found"
```bash
# Check USB connection
ls /dev/tty*
# Should show /dev/ttyACM0 or similar

# Test connection manually
python3 pico.py
```

### "WebSocket connection timeout"
```bash
# Check port is open
netstat -an | grep 8080

# Check firewall
sudo iptables -L  # On Raspberry Pi

# Test from PC
python3 -c "import websockets, asyncio; asyncio.run(websockets.connect('ws://RASPI_IP:8080/telemetry'))"
```

### "No telemetry data"
1. Verify KSP is running with active flight
2. Check kRPC server console in-game
3. Run `python3 main.py` and look for connection messages
4. Check logs: `tail -f /tmp/bridge.log`

## Next Steps

1. ✅ Basic system working?
2. ⚙️ Customize GPIO pins in `config.json`
3. 🎨 Extend Godot UI for more telemetry displays
4. 📊 Add data logging for post-flight analysis
5. 📱 Create mobile client
6. 🛡️ Add failsafe mechanisms

## Architecture Diagrams

See [ARCHITECTURE.md](ARCHITECTURE.md) for:
- System architecture overview
- Data flow diagrams
- Module descriptions
- Future enhancement ideas

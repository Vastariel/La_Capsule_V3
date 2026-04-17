# Quick Start Guide

**Status:** Refactored to new modular architecture (Nov 2024)

## Prerequisites

- **PC with KSP**: Kerbal Space Program with kRPC mod installed
- **Raspberry Pi 4**: Running Raspberry Pi OS with Python 3.9+
- **Pico RP2040**: Connected via USB to Raspberry Pi
- **Network**: All devices on same network (or configured with correct IPs)
- **GPIO Hardware**: Buttons, switches, LEDs wired to Raspberry Pi GPIO pins

## Quick Start (5 Minutes)

### 1. Install Dependencies
```bash
cd ~/Desktop/La_Capsule_V3/bridge_python
pip3 install -r requirements.txt
```

### 2. Run the Bridge
```bash
python3 main.py
```

That's it! The system will:
- Connect to kRPC on `192.168.1.31:50000`
- Initialize Pico ADC if available
- Start GPIO control
- Listen for Godot on `ws://0.0.0.0:8080`

Expected output:
```
[✓] KRPC connecté
[✓] Pico connecté
[✓] GPIO initialisé
[✓] WebSocket serveur démarré
[LOOP] Status updates...
```

### 3. Connect Godot Client
```gdscript
# In your Godot telemetry UI script
var ws = WebSocketClient.new()
ws.connect_to_url("ws://raspberrypi.local:8080")
```

---

## Detailed Configuration

```json
{
  "krpc": {
    "host": "192.168.1.31",
    "port": 50000
  },
  "hardware": {
    "gpio_raspi": {
      "leds_rouges": [24, 27, 25, 21],
      "leds_vertes": [18, 12],
      "leviers": {
        "16": "SAS",
        "26": "RCS",
        "22": "THROTTLE_CONTROL"
      },
      "boutons": {
        "20": "ENGINE_START",
        "23": "STAGE_BOOSTERS",
        "8": "STAGE_1",
        "4": "STAGE_2",
        "19": "STAGE_3",
        "13": "PARACHUTE",
        "6": "HEAT_SHIELD",
        "7": "FAIRING",
        "11": "LANDING_GEAR",
        "5": "TOGGLE_MAP"
      }
    }
  }
}
```

---

## System Architecture

The new modular system has 5 components:

```
┌─────────────────────────────────────────────────┐
│                   main.py                       │
│  (Orchestrates everything)                      │
└─────────────────────────────────────────────────┘
               │               │               │
    ┌──────────┴────┬──────────┴────┬──────────┴──────┐
    │               │                │                 │
    │               │                │                 │
┌───┴────┐    ┌─────┴──┐    ┌────────┴──┐    ┌──────┴────────┐
│  KRPC   │    │  Pico  │    │   GPIO    │    │  WebSocket   │
│Handler  │    │Handler │    │  Handler  │    │   Server     │
└────┬────┘    └─────┬──┘    └────┬──────┘    └──────┬────────┘
     │               │            │                    │
     │               │            │                    │
  KSP PC         /dev/        Raspberry            Godot Clients
  50000          ttyACM0       Pi GPIO              (ws://...)
```

**How it works:**
- **main.py**: Central orchestrator - loads config, initializes all 4 handlers
- **krpc_handler.py**: Manages KSP connection with auto-reconnect
- **pico_handler.py**: Reads throttle potentiometer from Pico
- **gpio_handler.py**: Handles buttons, switches, LEDs
- **websocket_server.py**: Broadcasts telemetry to Godot every 100ms

---

## Control Flow

### Button Press → Action

```
User presses Button 20
    ↓
gpio_handler detects edge
    ↓
Maps Button 20 → AG 0 (Engine Start)
    ↓
krpc_handler.trigger_action_group(0)
    ↓
KSP Engine ignites
    ↓
LED feedback updated
    ↓
Godot UI shows state change via WebSocket
```

### Telemetry Flow

```
Every 100ms:
krpc_handler.update_telemetry()
    ↓
Collects: speed, altitude, vertical_speed, 
          g_force, fuel%, current_stage, etc.
    ↓
websocket_server.broadcast(data)
    ↓
Godot clients receive JSON:
{
  "speed": 250.5,
  "altitude": 50000,
  "vertical_speed": 10.5,
  "ascending": true,
  "fuel_percent": 75.3,
  "current_stage": 2
}
```

---

## Test Scenarios

### 1. Basic Connectivity ✓
```bash
python3 main.py
# Should show:
# [✓] KRPC connecté
# [✓] Pico connecté
# [✓] GPIO initialisé
# [✓] WebSocket serveur démarré
```

### 2. Button Control ✓
```
Press physical button 20
→ Check KSP: Should see engine light
→ Check LED 24, 27, 25, 21: Should reflect stage status
```

### 3. Throttle Control ✓
```
Move lever 22 (THROTTLE_CONTROL) to ON
Move potentiometer
→ Check KSP: Vessel throttle should change smoothly
→ Check Godot: Throttle slider should match
```

### 4. Godot Telemetry ✓
```
In Godot, connect to ws://raspberrypi.local:8080
→ Should receive speed, altitude updates
→ Values should update every 100ms
```

---

## Troubleshooting

### KRPC Connection Issues

**Problem:** `[!] KRPC non disponible`

**Causes & Solutions:**
```bash
# 1. KSP not running
# → Start KSP and flight

# 2. kRPC mod not loaded
# → Launch KSP from launcher (mod auto-loads)

# 3. Wrong IP/port
# → Edit config.json, verify IP

# 4. Firewall blocking
# → Check: telnet 192.168.1.31 50000
# → If fails, add firewall exception
```

### Pico Connection Issues

**Problem:** `[!] Pico non disponible`

```bash
# 1. Check USB connection
ls /dev/ttyACM*

# 2. Check permissions
# → Make sure user can access /dev/ttyACM0

# 3. Wrong port or baud rate
# → Edit config.json: hardware.pico.port
```

### GPIO Permission Issues

**Problem:** `GPIO permission denied`

```bash
# Enable pigpio daemon (runs as root)
sudo systemctl start pigpiod

# Or run script as root
sudo python3 main.py

# Or add user to gpio group
sudo usermod -aG gpio pi
```

### WebSocket Connection Issues

**Problem:** Godot can't connect to `ws://...`

```bash
# 1. Check port is open
netstat -tuln | grep 8080

# 2. Try alternative hostnames
ws://raspberrypi.local:8080     # mDNS
ws://192.168.1.56:8080          # IP address

# 3. Check firewall on Pi
sudo ufw allow 8080

# 4. Test from PC
python3 -c "
import asyncio, websockets
async def test():
    async with websockets.connect('ws://192.168.1.56:8080'):
        msg = await ws.recv()
        print(msg)
asyncio.run(test())
"
```

---

## Performance Notes

- **Main loop:** 10 Hz (100ms)
- **Telemetry updates:** 10/sec (100ms intervals)
- **LED updates:** Real-time (< 50ms latency)
- **Button response:** < 100ms from press to KSP

---

## File Structure

```
La_Capsule_V3/
├── config.json                   ← Main config
├── main.py                       ← Entry point
├── QUICKSTART.md                 ← This file
├── REFACTOR_COMPLETE.md          ← What changed
├── bridge_python/
│   ├── krpc_handler.py          ← KSP communication
│   ├── pico_handler.py          ← Throttle ADC
│   ├── gpio_handler.py          ← Button/LED control
│   ├── websocket_server.py      ← Godot telemetry
│   ├── main.py                  ← OLD (kept for reference)
│   ├── requirements.txt         ← Dependencies
│   └── tests/                   ← Unit tests
├── godot_ui/                    ← Godot client
└── setup/                       ← Installation scripts
```

---

## Next Steps

1. ✅ Run `python3 main.py`
2. ✅ Connect Godot to `ws://raspberrypi.local:8080`
3. ✅ Test buttons, switches, throttle
4. ⏭️ Clean up old files (when ready)
5. ⏭️ Update documentation
6. ⏭️ Deploy as systemd service (optional)

---

See [ARCHITECTURE.md](ARCHITECTURE.md) and [REFACTOR_COMPLETE.md](REFACTOR_COMPLETE.md) for more details.
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

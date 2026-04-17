# Deployment Guide

Complete guide to deploy La Capsule V3 from scratch.

## Prerequisites

- **Hardware**:
  - PC running Windows/Mac/Linux with Kerbal Space Program
  - Raspberry Pi 4 with Raspberry Pi OS (32 or 64-bit)
  - Pico RP2040 microcontroller with picod firmware
  - GPIO hardware (buttons, switches, LEDs)
  - USB cable for Pico connection to Raspberry Pi

- **Software**:
  - KSP with kRPC mod installed and configured
  - Python 3.9+ on Raspberry Pi
  - Godot 4.x or compatible (for UI client)

- **Network**:  
  - All devices on same network (or static IPs if using VPN)
  - No firewall blocking ports 50008, 50001, 8080

## Phase 1: Hardware Setup

### 1.1 Wire Raspberry Pi GPIO

Connect your hardware to Raspberry Pi GPIO pins according to `setup/config.json`:

```
LED Rouges (Outputs):
  GPIO 24 → LED 1
  GPIO 27 → LED 2
  GPIO 25 → LED 3
  GPIO 21 → LED 4

LED Vertes (Outputs):
  GPIO 18 → LED 5
  GPIO 12 → LED 6

Leviers (Inputs, Pull-up):
  GPIO 16 → SAS Switch
  GPIO 26 → RCS Switch
  GPIO 22 → Throttle Control

Boutons (Inputs, Pull-up):
  GPIO 6  → Heat Shield
  GPIO 13 → Parachute
  GPIO 11 → Landing Gear
  GPIO 5  → Toggle Map
  GPIO 20 → Engine Start
  GPIO 7  → Fairing
  GPIO 23 → Stage Boosters
  GPIO 8  → Stage 1
  GPIO 4  → Stage 2
  GPIO 19 → Stage 3
```

**Wiring Tips**:
- Use 3.3V pullup resistors for inputs (gpiozero handles pull-up internally)
- Add current-limiting resistors for LEDs (220-330Ω recommended)
- Use ground connections appropriately

### 1.2 Connect Pico

Connect Pico RP2040 via USB to Raspberry Pi.

Verify connection:
```bash
ls /dev/ttyACM0
# Should exist if Pico is connected
```

## Phase 2: Software Installation

### 2.1 Update Raspberry Pi

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv pigpio git -y

# Start pigpio daemon (required for remote GPIO)
sudo pigpiod
# Or enable as service: sudo systemctl enable pigpiod
```

### 2.2 Clone/Download Project

```bash
cd ~
git clone https://github.com/Vastariel/La_Capsule_V3.git
# Or: download zip and extract
cd La_Capsule_V3
```

### 2.3 Setup Python Environment

```bash
cd bridge_python
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.4 Configure Network

Edit `setup/config.json`:

```bash
nano ../setup/config.json
```

Update with your actual IPs:
- Find Raspberry Pi IP: `hostname -I`
- Find PC IP: On Windows: `ipconfig`, On Mac/Linux: `hostname -I`

```json
{
  "network": {
    "ksp_pc": {
      "ip": "192.168.1.10",  ← Your PC IP
      "krpc_rpc_port": 50008,
      "krpc_stream_port": 50001
    },
    "raspi": {
      "ip": "192.168.1.56"   ← Your Raspi IP
    }
  }
}
```

## Phase 3: Verify Each Component

### 3.1 Test Configuration

```bash
cd ~/La_Capsule_V3/bridge_python
python3 -m utils.config_loader
```

Expected:
```
✓ Configuration chargée
🔧 CONFIGURATION SUMMARY
KSP PC: 192.168.1.10:50008...
```

### 3.2 Test GPIO (Local)

```bash
python3 gpio.py
```

Expected:
- LEDs light up one by one (test takes ~20 seconds)
- Input monitoring active (press buttons to see output)
- (Ctrl+C to exit)

### 3.3 Test Pico

```bash
python3 pico.py
```

Expected:
```
✓ Pico connecté sur /dev/ttyACM0
--- Lecture 1 ---
  Canal 0: raw=500, smoothed=501.5, percent=12.2%
  ...
```

### 3.4 Test Configuration Tests

```bash
python3 -m pytest tests/ -v
```

Expected:
- All configuration tests pass
- Some hardware tests may be skipped (expected)

## Phase 4: KSP Server Setup

### 4.1 Install kRPC Mod

1. Download kRPC from https://krpc.github.io/
2. Install to KSP GameData folder
3. Restart KSP

### 4.2 Configure kRPC Server

1. Start KSP
2. Load or create flight scene
3. Check kRPC console (Alt+F2)
4. Should show: "Server listening on 0.0.0.0:50008"

### 4.3 Test Connection

From Raspberry Pi:
```bash
python3 -c "
import krpc
try:
    conn = krpc.connect(address='192.168.1.10', rpc_port=50008)
    vessel = conn.space_center.active_vessel
    print(f'✓ Connected! Vessel: {vessel.name}')
    print(f'  Altitude: {vessel.flight().mean_altitude:.0f}m')
    conn.close()
except Exception as e:
    print(f'✗ Error: {e}')
"
```

Expected: Should print vessel name and altitude

## Phase 5: Deployment

### 5.1 Start bridge_python

On Raspberry Pi:
```bash
cd ~/La_Capsule_V3/bridge_python
source venv/bin/activate
python3 main.py
```

Expected output:
```
🔧 CONFIGURATION SUMMARY
...
✓ server KRPC connecté et en fonctionnement
✓ Serveur WebSocket démarré
✓ GPIO initialisé
✓ Pico connecté
```

**Keep this running** (don't close terminal or it stops)

### 5.2 Start Godot Client

On your PC:
```bash
cd La_Capsule_V3/godot_ui
godot
```

1. Open project
2. Press F5 to play
3. Wait for connection dialog or auto-connection

Expected:
- Telemetry updates in real-time
- Speed, altitude, apoapsis displayed
- LEDs respond to GPIO changes

### 5.3 Test Full System

1. **Verify telemetry** streams from KSP to Godot
2. **Test GPIO inputs**: Press buttons, verify Godot responds
3. **Test LED outputs**: Verify LEDs light up during tests
4. **Test throttle**: Turn potentiometer, watch throttle change in KSP

## Phase 6: Production Deployment

### 6.1 Systemd Service (Optional)

Create auto-start service:

```bash
sudo nano /etc/systemd/system/la-capsule.service
```

Add:
```ini
[Unit]
Description=La Capsule V3 Bridge
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/La_Capsule_V3/bridge_python
ExecStart=/home/pi/La_Capsule_V3/bridge_python/venv/bin/python3 main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable la-capsule
sudo systemctl start la-capsule
```

Check status:
```bash
sudo systemctl status la-capsule
```

### 6.2 Logs

View logs:
```bash
sudo journalctl -u la-capsule -f
# Or check file logs
tail -f /tmp/bridge.log
```

### 6.3 Firewall Configuration (if needed)

Allow ports:
```bash
sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
# Make persistent:
sudo iptables-save | sudo tee /etc/iptables.rules
```

## Phase 7: Troubleshooting

### "kRPC Not Connecting"
```bash
# On PC, check kRPC in game console (Alt+F2)
# On Raspi, verify IP/ports
python3 -c "import krpc; krpc.connect(address='YOUR_PC_IP')"
```

###  "GPIO Permission Denied"
```bash
# Ensure pigpiod is running
sudo pigpiod

# Or add user to group
sudo usermod -a -G gpio pi
sudo usermod -a -G spi pi
sudo usermod -a -G i2c pi
```

### "Pico Not Found"
```bash
ls /dev/ttyACM*
# Should show /dev/ttyACM0
# If not, check USB connection and Pico firmware
```

### "WebSocket Not Connecting from Godot"
```bash
# Test WebSocket locally:
python3 -c "
import asyncio, websockets
async def test():
    async with websockets.connect('ws://RASPI_IP:8080/telemetry') as ws:
        msg = await ws.recv()
        print(f'Received: {msg}')
asyncio.run(test())
"
```

## Phase 8: Maintenance

### Regular Checks

```bash
# Check system health
free -h              # Memory usage
df -h                # Disk usage
top                  # CPU usage

# Check services
sudo systemctl status la-capsule
sudo systemctl status pigpiod

# Check logs
tail -20 /tmp/bridge.log
```

### Updates

When pulling new code:
```bash
cd ~/La_Capsule_V3
git pull
cd bridge_python
# Might need to reinstall requirements if dependencies changed
pip install -r requirements.txt
```

## Rollback Plan

If something breaks:

1. **Check logs**: `tail -f /tmp/bridge.log`
2. **Stop service**: `sudo systemctl stop la-capsule`
3. **Restart bridge**: `python3 main.py` (debug mode)
4. **Git rollback**: `git revert` to previous commit

## Monitoring and Alerts

Future enhancements:
- Email alerts if connection lost
- Automated restart on failure
- Data logging for post-flight analysis
- Health dashboard

---

For detailed architecture, see [ARCHITECTURE.md](ARCHITECTURE.md)
For quick start, see [QUICKSTART.md](QUICKSTART.md)

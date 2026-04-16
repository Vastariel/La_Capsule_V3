# 🚀 Actions For You - Next Steps

## Immediate Actions (Required)

### 1. Review the Restructuring  (5 min)
- [ ] Read [SUMMARY.md](SUMMARY.md) - Overview of changes
- [ ] Review [README.md](README.md) - Full system documentation

### 2. Configure the System  (10 min)
- [ ] Open `setup/config.json` in a text editor
- [ ] Update network IPs:
  - Find your **PC IP**: `ipconfig` (Windows) or `hostname -I` (Mac/Linux)
  - Find your **Raspberry Pi IP**: `ssh pi@raspberrypi.local` then `hostname -I`
  - Update these IPs in `config.json`
- [ ] Verify GPIO pins match your hardware wiring
- [ ] Verify Pico is on `/dev/ttyACM0` (or update if different)

**Example config update**:
```json
{
  "network": {
    "ksp_pc": {"ip": "YOUR_PC_IP_HERE"},
    "raspi": {"ip": "YOUR_RASPI_IP_HERE"}
  }
}
```

### 3. Understand the Architecture  (10 min)
- [ ] Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand:
  - How data flows between components
  - Why each file exists
  - Design decisions made

### 4. Verify Setup  (5 min)
```bash
cd ~/La_Capsule_V3
chmod +x verify.sh
bash verify.sh
```

Expected output: ✓ All checks passed

---

## Testing Phase (Before Running Full System)

### 5. Test Configuration  (5 min)
On Raspberry Pi:
```bash
cd bridge_python
python3 utils/config_loader.py
```

Should show:
```
✓ Configuration chargée
KSP PC: [YOUR_IP]:50008
Raspi: [YOUR_IP]
...
```

### 6. Quick Module Tests  (10 min each)

**Quick GPIO test:**
```bash
python3 gpio.py
```
Expected: Shows GPIO info and directs to interactive test

**Quick Pico test:**
```bash
python3 pico.py
```
Expected: Shows Pico info and directs to interactive test

**Configuration validation:**
```bash
python3 -m pytest tests/test_configuration.py -v
```

### 7. FULL Interactive Hardware Tests  (45 min total)

#### GPIO Interactive Test (20-25 min)
```bash
python3 tests/test_gpio_interactive.py
```

**What happens:**
1. Choose LOCAL or REMOTE GPIO
2. Red LEDs light up one by one (5 sec each)
   → **ACTION**: Watch for light, verify connections
3. Green LEDs light up one by one (5 sec each)
   → **ACTION**: Watch for light, verify connections
4. All LEDs sequence on/off together
5. Wait for levier switch inputs (20 sec)
   → **ACTION**: Move SAS/RCS/Throttle switches
6. Wait for button inputs (30 sec)
   → **ACTION**: Press all buttons
7. Get test results summary

**Expected results:**
- ✓ All LEDs respond
- ✓ All switch changes detected
- ✓ All button presses detected
- ✓ Good summary report

#### Pico ADC Interactive Test (15-20 min)
```bash
python3 tests/test_pico_interactive.py
```

**What happens:**
1. Connection test (1 min)
   → Verifies Pico USB is connected
2. ADC channels monitoring (15 sec)
   → **ACTION**: Rotate throttle potentiometer
   → See raw ADC values change
3. Smoothing verification (10 sec)
   → Compare raw vs smoothed values
4. Throttle conversion test (10 sec)
   → See 0-4095 → 0.0-1.0 conversion
5. Statistics summary

**Expected results:**
- ✓ Pico detected on /dev/ttyACM0
- ✓ Channel 0 values change when potentiometer rotated
- ✓ Smoothing reduces noise
- ✓ Throttle conversions correct

### 8. Test KSP Connection  (10 min)
On Raspberry Pi:
```bash
python3 -c "
import krpc
conn = krpc.connect(address='YOUR_PC_IP', rpc_port=50008)
vessel = conn.space_center.active_vessel
print(f'✓ Connected to {vessel.name}')
print(f'  Altitude: {vessel.flight().mean_altitude:.0f}m')
conn.close()
"
```
Expected: Should print vessel info

---

## Running the Full System

### 8. Start bridge_python on Raspberry Pi
```bash
cd ~/La_Capsule_V3/bridge_python
source venv/bin/activate
python3 main.py
```

**Keep this terminal open** (don't close or system stops)

Expected output:
```
✓ server KRPC connecté
✓ Serveur WebSocket démarré
✓ GPIO initialisé
✓ Pico connecté
```

### 9. Run Godot Client
On your PC:
```bash
cd ~/La_Capsule_V3/godot_ui
godot
```

- Open project
- Press F5 to play
- Watch telemetry update in real-time

---

## Questions to Answer Before Testing

Before running hardware tests, **clarify these**:

1. **GPIO Pins**: Have you verified the pin numbers in `config.json` match your physical wiring?
   - Are the red LEDs connected to GPIO 24, 27, 25, 21?
   - Are the buttons connected to the correct pins?
   - Answer: [ ] Yes / [ ] No / [ ] Need to check

2. **Pico Connection**: Is the Pico USB connected to the Raspberry Pi?
   - Check: `ls /dev/ttyACM0` (should exist)
   - Answer: [ ] Yes / [ ] No / [ ] Need to check

3. **Network**: Do you know your IPs?
   - PC IP: ________________
   - Raspi IP: ________________
   - Updated in config.json: [ ] Yes / [ ] No

4. **KSP Server**: Is kRPC mod installed?
   - Installed on KSP: [ ] Yes / [ ] No
   - Tested locally: [ ] Yes [ ] No  
   - Working: [ ] Yes / [ ] No / [ ] Haven't tested

---

## Common Issues & Quick Fixes

### "Cannot find project root in config_loader"
→ Ensure `setup/config.json` exists in the project root

### "GPIO permission denied"
→ Run `sudo pigpiod` on Raspberry Pi first

### "ModuleNotFoundError: No module named 'krpc'"
→ Run `pip install -r requirements.txt` in venv

### "Connection refused" (KSP)
→ Verify KSP is running with kRPC server active (Alt+F2 in game)

---

## Documentation References

- **Quick Start**: [QUICKSTART.md](QUICKSTART.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Production Deployment**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Godot Setup**: [godot_ui/SETUP.md](godot_ui/SETUP.md)
- **raspi_controller**: [raspi_controller/README.md](raspi_controller/README.md)

---

## Optional Enhancements (Later)

Once the basic system works:

- [ ] Set up systemd service for auto-start
- [ ] Add data logging for post-flight analysis
- [ ] Implement bidirectional Godot control (buttons sending commands)
- [ ] Create mobile client
- [ ] Add more sensors (IMU, etc.)

---

## Success Checklist

When everything is working, you should be able to:

- [x] Edit config.json to change IPs
- [x] Run bridge_python without errors
- [x] Connect Godot client to bridge
- [x] See live telemetry data in Godot
- [x] Press buttons and see GPIO responses
- [x] Turn throttle potentiometer and see KSP throttle change
- [x] Activate SAS in KSP and see LED light up

---

## Support & Questions

If something isn't working:

1. Check the **Troubleshooting** section in [QUICKSTART.md](QUICKSTART.md)
2. Check **logs**: `tail -f /tmp/bridge.log`
3. Run **tests**: `pytest tests/ -v`
4. Consult **DEPLOYMENT.md** for detailed troubleshooting by layer

---

## Final Checklist

- [ ] Read SUMMARY.md
- [ ] Update setup/config.json with your IPs
- [ ] Run verify.sh and fix any errors
- [ ] Test individual components (GPIO, Pico, Config)
- [ ] Install dependencies on Raspberry Pi
- [ ] Start bridge_python
- [ ] Open Godot and verify telemetry
- [ ] Test full system (buttons, throttle, LEDs)

**Everything working? You're done! 🎉**

---

Questions? See [QUICKSTART.md](QUICKSTART.md) → Troubleshooting

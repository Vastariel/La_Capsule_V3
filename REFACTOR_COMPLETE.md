# La Capsule V3 - Architectural Refactor Complete ✓

## Status: New Architecture Ready for Testing

### What Was Done

#### ✅ Created New Modular Architecture

**New Handler Modules (in `bridge_python/`):**

1. **krpc_handler.py** (270 lines)
   - Centralized KRPC connection management
   - Automatic reconnection (5-min timeout, 3-sec retry)
   - Complete telemetry collection
   - All control methods (throttle, SAS, RCS, action groups, camera)

2. **pico_handler.py** (150 lines)
   - Unified Pico ADC interface
   - Automatic smoothing buffer management
   - Throttle getters with normalization

3. **gpio_handler.py** (350 lines)
   - Integrated GPIO management
   - Button-to-action-group mapping
   - LED state tracking (SAS, RCS, stage indicators)
   - Throttle control with lever gating and deadzone

4. **websocket_server.py** (120 lines)
   - Real-time telemetry broadcast to Godot
   - 10 Hz update rate
   - Client connection management

5. **main.py** (Refactored)
   - Single entry point orchestrating all modules
   - Graceful initialization and shutdown
   - Config-driven setup
   - Status logging

#### ✅ Configuration Files

- **config.json** (root level)
  - Network configuration (KRPC host/port)
  - Hardware pin mappings
  - Action group definitions
  - Throttle deadzone & smoothing settings
  - WebSocket parameters

- **requirements.txt** (cleaned)
  - Core dependencies only: krpc, gpiozero, pigpio, websockets, picod
  - Optional dev tools commented out

#### 📋 System Architecture

```
main.py
├── KRPCHandler (→ kRPC server 192.168.1.31:50000)
│   ├── get_telemetry()
│   ├── update_telemetry()
│   ├── trigger_action_group(group)
│   ├── set_throttle(value)
│   ├── set_sas(state)
│   ├── set_rcs(state)
│   └── toggle_map_camera()
│
├── PicoHandler (→ Serial /dev/ttyACM0)
│   ├── get_throttle()
│   └── read_smoothed(channel)
│
├── GPIOHandler (→ Raspberry Pi GPIO)
│   ├── _update_leviers() [SAS, RCS, Throttle control]
│   ├── _update_boutons() [Button → Action Group routing]
│   ├── _update_throttle()
│   ├── _update_green_leds() [SAS/RCS LED feedback]
│   └── _update_red_leds() [Stage indicators]
│
└── WebSocketServer (→ Godot clients ws://0.0.0.0:8080)
    └── broadcast telemetry every 100ms
```

### Previous Issues Fixed

| Issue | Solution |
|-------|----------|
| RCS LED not syncing | Direct control.rcs state tracking in gpio_handler |
| Stage LEDs non-functional | Added current_stage to telemetry, created LED mapping |
| Potentiometer ignored | Pico integrated, throttle control in update loop |
| Button mapping confusion | Clean action group system with config-driven mapping |
| KRPC connection fragile | reconnect_if_needed() with exponential backoff |
| Code fragmentation | Consolidated raspi_controller + bridge_python → single module |

### Files to Clean Up

Once tested and verified working, delete:
- [ ] `raspi_controller/` (entire folder)
- [ ] `bridge_python/api.py` (replaced by krpc_handler.py)
- [ ] `bridge_python/pico.py` (replaced by pico_handler.py)
- [ ] `bridge_python/server.py` (replaced by websocket_server.py)
- [ ] `bridge_python/config.py` (config moved to config.json)
- [ ] `bridge_python/gpio_backup.py` (old backup)
- [ ] `setup/config.json` (moved to root as config.json)

### Next Steps

1. **Test on Raspberry Pi**
   ```bash
   cd ~/Desktop/La_Capsule_V3/bridge_python
   python3 main.py
   ```

2. **Verify Godot Connection**
   - Launch Godot scene
   - Check WebSocket client connects to ws://raspberrypi.local:8080
   - Verify telemetry updates appear

3. **Test Hardware**
   - Press buttons → verify action groups trigger
   - Toggle leviers → verify SAS/RCS LEDs
   - Move throttle lever → verify control.throttle changes
   - Monitor current_stage → verify stage LEDs

4. **Update Documentation**
   - [ ] ARCHITECTURE.md (4-module structure)
   - [ ] QUICKSTART.md (single main.py entry)
   - [ ] DEPLOYMENT.md (if needed)

5. **Final Cleanup**
   - Delete old files once all tests pass
   - Update bridge_python/tests/ for new modules
   - Run pytest if available

### How to Run

```bash
# From Raspberry Pi:
cd /home/capsule/Desktop/La_Capsule_V3/bridge_python

# Install dependencies (first time only):
pip3 install -r requirements.txt

# Run the system:
python3 main.py

# Output will show:
# [✓] KRPC connected
# [✓] Pico connected  
# [✓] GPIO initialized
# [✓] WebSocket serveur démarré
# [LOOP] Status updates every 3 seconds
```

### Key Configuration Values

In `config.json`:
- **KRPC**: Host=192.168.1.31, Port=50000
- **WebSocket**: Host=0.0.0.0, Port=8080
- **Pico**: Port=/dev/ttyACM0, Baud=115200
- **Action Groups**: 0-6 mapped to buttons/LEDs (9 reserved for fairing)
- **Throttle Deadzone**: 2% below threshold ignored
- **Main Loop**: 10 Hz (100ms sleep)

### Telemetry Broadcast (to Godot)

Every 100ms, WebSocket sends JSON:
```json
{
  "speed": 250.5,
  "altitude": 50000.0,
  "vertical_speed": 10.5,
  "ascending": true,
  "g_force": 1.2,
  "fuel_percent": 75.3,
  "current_stage": 2,
  "connected": true
}
```

---

**Date**: 2024
**Status**: Ready for Testing
**Next**: Verify on hardware, then cleanup old files

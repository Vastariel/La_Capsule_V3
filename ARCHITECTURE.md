# Architecture Documentation

## System Overview

The La Capsule V3 system is a **client-server architecture** with three main components:

### 1. **KSP Server (PC)**
- Runs Kerbal Space Program with kRPC extension
- Exposes telemetry via kRPC protocol (`192.168.1.25:50008` RPC, `:50001` Stream)
- Receives control commands (SAS, RCS, Throttle, Staging)

### 2. **Raspberry Pi 4 Bridge (Central Controller)**
- Runs `bridge_python` module
- **Collects data from**:
  - kRPC (telemetry from PC)
  - GPIO inputs (buttons, switches)
  - Pico ADC (potentiometer)
- **Sends data to**:
  - WebSocket clients (Godot UI)
  - kRPC (control commands)
  - GPIO outputs (LEDs)
- **Single point of truth** for all hardware state

### 3. **Godot Client (Display)**
- Connects to Raspberry Pi via WebSocket
- **Receives**: Telemetry streams every 100ms
- **Sends**: (Currently display-only, can be extended for user input)
- Displays real-time KSP status, flight instruments

## Why This Architecture?

### ✅ Advantages

1. **Centralized Control**: All GPIO, Pico, and KSP logic in one place (Raspberry Pi)
2. **Real-time Response**: Direct GPIO control without network latency
3. **Scalability**: Multiple Godot clients can connect simultaneously
4. **Maintainability**: Single configuration file for all IP addresses and pins
5. **Hardware Safety**: Raspberry Pi validates all commands before sending to KSP
6. **Graceful Degradation**: System works even if Godot client disconnects

### ⚠️ Design Decisions Explained

#### Why bridge_python runs on Raspberry Pi, not PC?

The **Pico microcontroller is connected via USB to the Raspberry Pi**, making it impossible for the PC to access it directly unless:
- PC and Raspberry Pi are networked (adds complexity, latency, points of failure)
- Pico is networked separately (overcomplicated for this use case)

Therefore: **bridge_python MUST run on Raspberry Pi**

If you ever want to run bridge_python on PC in the future:
- Pico would need to be networked or daisy-chained
- GPIO could be accessed remotely via pigpio
- Benefits would likely not outweigh complexity

#### Why raspi_controller exists (and is optional)?

`raspi_controller/` is an **alternative lightweight controller** that:
- Contains only GPIO monitoring and WebSocket communication
- Could theoretically run independently to send GPIO state to bridge_python or Godot
- **Currently: NOT RECOMMENDED** - use bridge_python instead for full functionality

**Decision**: Keep raspi_controller as an optional component but document that bridge_python is the primary implementation.

#### Why separate modules (pico.py, gpio.py)?

**Modularity and Testability**:
- `pico.py`: ADC with smoothing, error handling, reconnection logic
- `gpio.py`: GPIO control with callbacks and state tracking
- `api.py`: kRPC telemetry collection
- `server.py`: WebSocket server for clients

Each module can be tested independently without full hardware.

## Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│ KSP Server (PC): 192.168.1.25:50008                         │
└───────────────────┬──────────────────────────────────────────┘
                    │ kRPC Protocol
                    │
        ┌───────────▼────────────────────────┐
        │ Raspberry Pi: 192.168.1.56         │
        │                                    │
        │ ┌─ api.py                         │
        │ │ (Collects telemetry)           │
        │ │ Reads: altitude, speed, etc.   │
        │ │ Sends: throttle, control       │
        │ │                                  │
        │ ├─ gpio.py                        │
        │ │ (Hardware control)             │
        │ │ Reads: buttons, switches       │
        │ │ Writes: red/green LEDs         │
        │ │                                  │
        │ ├─ pico.py                        │
        │ │ (Sensor readings)              │
        │ │ Reads: throttle potentiometer  │
        │ │                                  │
        │ └─ server.py                      │
        │   (WebSocket server)             │
        │   Broadcasts: telemetry + state │
        │   Every 100ms                    │
        └──────────┬───────────────────────┘
                   │ WebSocket ws://0.0.0.0:8080
                   │
        ┌──────────▼────────────────────┐
        │ Godot Client (Any PC/Device)  │
        │                                │
        │ Displays telemetry             │
        │ (Read-only mode currently)     │
        └────────────────────────────────┘
```

## Data Types and Refresh Rates

### Critical Data (Every frame = 30Hz)
- Altitude
- Speed

### Important Data (Every 5 frames = 6Hz)
- G-force
- Temperature

### Normal Data (Every 10 frames = 3Hz)
- Apoapsis / Periapsis
- Time to Apoapsis / Periapsis

### Hardware State (Continuous)
- GPIO button states
- LED states
- Pico ADC values

## Configuration Management

All configuration is in **`setup/config.json`**:

```json
{
  "network": {
    "ksp_pc": {"ip": "192.168.1.25", "krpc_rpc_port": 50008},
    "raspi": {"ip": "192.168.1.56"},
    "bridge_websocket": {"host": "0.0.0.0", "port": 8080}
  },
  "hardware": {
    "gpio_raspi": {
      "leds_rouges": [24, 27, 25, 21],
      "leviers": {"16": "SAS", "26": "RCS", ...}
    }
  }
}
```

**Single modification point**: Change IPs here, and the entire system adapts.

## Future Enhancements

1. **Bidirectional Godot Control**
   - Currently: Display-only
   - Enhancement: Allow Godot UI buttons to send commands back to bridge

2. **Multiple Pico Support**
   - Currently: 1 Pico (4 ADC channels)
   - Enhancement: Support multiple Picos for more sensors

3. **Data Logging**
   - Add CSV/database logging of flight data
   - Post-flight analysis

4. **Mobile Support**
   - Mobile client connecting to WebSocket
   - Wireless throttle control, staging buttons

5. **Failsafe Mechanisms**
   - Watchdog timer for lost communication
   - Automatic throttle to 0 if connection lost
   - LED patterns for error states

## Testing Strategy

### Level 1: Configuration Testing
```bash
python3 -m utils.config_loader
pytest tests/test_configuration.py
```

### Level 2: Hardware Testing (Local)
```bash
# Test GPIO (no remote connection, no hardware required for imports)
python3 gpio.py

# Test Pico (if hardware connected)
python3 pico.py
```

### Level 3: Integration Testing
```bash
# Full system with all components
python3 main.py
```

### Level 4: System Testing
1. Godot client connects to WebSocket
2. Verify telemetry stream
3. Test KSP commands (staging, SAS, RCS, throttle)
4. Monitor GPIO responses (LEDs, button detection)

## Troubleshooting by Layer

### Network Layer
- Check IP addresses: `hostname -I`
- Test connectivity: `ping 192.168.1.25`
- Check ports: `netstat -an | grep 8080`

### Hardware Layer
- Test GPIO: See `bridge_python/gpio.py`
- Test Pico: See `bridge_python/pico.py`
- Check pin conflicts in `config.json`

### Software Layer
- Check logs: `tail -f /tmp/bridge.log`
- Test config: `python3 -m utils.config_loader`
- Run tests: `pytest -v`

### Integration Layer
- Verify WebSocket broadcast
- Check Godot client connection
- Monitor KSP telemetry stream

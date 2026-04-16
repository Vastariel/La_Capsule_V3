# raspi_controller - Alternative Controller

## Purpose

`raspi_controller/` is an **alternative lightweight implementation** that:
- Monitors GPIO and Pico locally on Raspberry Pi
- Sends data to bridge_python via WebSocket
- Could theoretically run independently

## Current Status

**⚠️ Currently experimental and optional.** 

**Recommended approach**: Use `bridge_python` instead, which integrates all components.

## When raspi_controller is Useful

1. **Distributed Architecture**: Run GPIO monitoring separately from API/WebSocket server
2. **Testing**: Verify GPIO/Pico work independently
3. **Scalability**: Multiple raspi_controllers → single bridge server (future)

## Components

### gpio_monitor.py
- Monitors GPIO states locally
- Tracks buttons, switches, LEDs
- No remote pigpio needed

### pico_monitor.py
- Reads Pico ADC values
- Direct USB connection
- No socat redirection needed

### websocket_client.py
- Sends monitored data to bridge
- Handles reconnection
- Async streaming

### main.py
- Coordinates all modules
- Runs in background

## Usage (Optional)

```bash
# Install dependencies
python3 -m pip install -r requirements.txt

# Run
python3 main.py

# Or run daemon
nohup python3 main.py &
```

## Configuration

Edit `main.py` to set bridge connection:
```python
controller = RaspiController(
    bridge_host="192.168.1.25",  # Where bridge_python runs
    bridge_port=8081
)
```

## Why bridge_python is Better

✅ **bridge_python** (Recommended):
- Runs on Raspi, controls everything
- Single source of truth for hardware state
- Direct GPIO control without extra WebSocket hop
- Better real-time performance
- Easier to debug

❌ **raspi_controller** (Alternative):
- Extra network hop (Raspi → Raspi)
- More complex architecture
- Potential timing issues
- Monitoring only (no control in current implementation)

## Architecture Comparison

### Option 1: Using bridge_python (RECOMMENDED)
```
KSP → bridge_python [GPIO + Pico] → Godot
       ↓
      WebSocket
```

### Option 2: Using raspi_controller (NOT RECOMMENDED)
```
KSP → bridge_python [GPIO + Pico] → Godot
              ↑
        raspi_controller (extra component)
              ↓
           WebSocket
```

## Migration Path

If you're using raspi_controller:

1. **Switch to bridge_python**:
   ```bash
   cd bridge_python
   python3 main.py
   ```

2. **raspi_controller becomes optional**:
   - Keep it for reference
   - Use if distributed architecture needed later

## Future Enhancement

If distributed monitoring becomes necessary:

```
Device 1: GPIO Monitor → Local API
Device 2: Pico Monitor → Local API
Device 3: Bridge → Aggregates both, talks to KSP & Godot
```

Currently: All on one device (Raspi) with bridge_python.

## Recommendation

**Use bridge_python (bridge_python/main.py) as your primary controller.**

raspi_controller is available if you need it, but adds unnecessary complexity in the current setup.

---

See [ARCHITECTURE.md](../ARCHITECTURE.md) for system design details.
  },
  "pico": {
    "connected": true,
    "channels": {
      "adc_0": {"raw": 2048, "percentage": 50.0},
      "adc_1": {"raw": 1024, "percentage": 25.0},
      "adc_2": {"raw": 3072, "percentage": 75.0}
    }
  }
}
```

## Configuration

Modifier les adresses IP et ports dans `main.py` :
- `bridge_host` : Adresse IP du PC (bridge_krpc)
- `bridge_port` : Port du serveur WebSocket du bridge

# Godot UI - Telemetry Data Schema

## Overview

The Godot UI receives real-time telemetry data from the bridge_python server via WebSocket connection at `ws://[RASPI_IP]:8080/telemetry`.

**Update Interval**: 100ms (10 Hz refresh rate)

---

## WebSocket Connection

### Configuration (in `Scripts/main.gd`)

```gdscript
@export var ws_host: String = "192.168.1.56"      # Raspberry Pi IP
@export var ws_port: int = 8080                    # WebSocket port
@export var ws_path: String = "/telemetry"         # WebSocket path
@export var auto_connect: bool = true              # Auto-connect on startup
```

### Connection URL Format
```
ws://192.168.1.56:8080/telemetry
```

---

## Telemetry Data Schema

Every 100ms, the server sends a JSON message with the following structure:

```json
{
  "speed": 150.5,
  "altitude": 5000.0,
  "vertical_speed": 25.3,
  "ascending": true,
  "apoapsis": 100000.0,
  "periapsis": 50000.0,
  "apoapsis_time": 120.5,
  "periapsis_time": 300.0,
  "g_force": 1.5,
  "max_g_force": 3.2,
  "temperature": 400.0,
  "liquid_fuel_percent": 85.5,
  "monopropellant_percent": 92.0,
  "engines_active": true,
  "current_stage": 3
}
```

---

## Field Descriptions

### Movement & Position

| Field | Type | Unit | Range | Description |
|-------|------|------|-------|-------------|
| `speed` | float | m/s | ≥ 0 | Current velocity magnitude |
| `altitude` | float | m | ≥ 0 | Height above sea level |
| `vertical_speed` | float | m/s | -∞ to +∞ | Rate of altitude change (+ = ascending, - = descending) |
| `ascending` | bool | - | true/false | **Easy flag**: True if vessel is going up, False if going down |

### Orbital Data

| Field | Type | Unit | Range | Description |
|-------|------|------|-------|-------------|
| `apoapsis` | float | m | ≥ 0 | Altitude of highest orbit point |
| `periapsis` | float | m | ≥ 0 | Altitude of lowest orbit point |
| `apoapsis_time` | float | s | ≥ 0 | Seconds until reaching apoapsis (-1 if not in orbit) |
| `periapsis_time` | float | s | ≥ 0 | Seconds until reaching periapsis (-1 if not in orbit) |

### Forces & Physics

| Field | Type | Unit | Range | Description |
|-------|------|------|-------|-------------|
| `g_force` | float | g | -∞ to +∞ | Current G-force experienced by vessel |
| `max_g_force` | float | g | ≥ 0 | Peak G-force reached during current flight |
| `temperature` | float | K | 0 to ∞ | External air temperature (0 K in space) |

### Resources

| Field | Type | Unit | Range | Description |
|-------|------|------|-------|-------------|
| `liquid_fuel_percent` | float | % | 0-100 | LiquidFuel + Oxidizer combined percentage |
| `monopropellant_percent` | float | % | 0-100 | Monopropellant (RCS fuel) percentage |

### Engine State

| Field | Type | Unit | Range | Description |
|-------|------|------|-------|-------------|
| `engines_active` | bool | - | true/false | True if throttle > 0%, False otherwise |
| `current_stage` | int | - | 0-∞ | Current active stage number from KSP (0 = final stage) |

---

## Usage Examples

### Displaying Climbing/Descending Indicator

```gdscript
func _on_telemetry_received(data: Dictionary):
    var ascending = data["ascending"]
    
    if ascending:
        indicator_label.text = "⬆️ ASCENDING"
        indicator_label.modulate = Color.GREEN
    else:
        indicator_label.text = "⬇️ DESCENDING"
        indicator_label.modulate = Color.RED
```

### Fuel Low Warning

```gdscript
func _on_telemetry_received(data: Dictionary):
    var fuel_percent = data["liquid_fuel_percent"]
    var rcs_percent = data["monopropellant_percent"]
    
    if fuel_percent < 15.0:
        show_fuel_warning("CRITICAL FUEL LOW: " + str(int(fuel_percent)) + "%")
    
    if rcs_percent < 10.0:
        show_rcs_warning("RCS FUEL CRITICAL: " + str(int(rcs_percent)) + "%")
```

### G-Force Display

```gdscript
func _on_telemetry_received(data: Dictionary):
    var current_g = data["g_force"]
    var max_g = data["max_g_force"]
    
    g_force_label.text = "G: %.1f (Peak: %.1f)" % [current_g, max_g]
    
    # Color code based on G warning
    if current_g > 3.0:
        g_force_label.modulate = Color.RED
    elif current_g > 2.0:
        g_force_label.modulate = Color.YELLOW
    else:
        g_force_label.modulate = Color.WHITE
```

### Vertical Speed Display

```gdscript
func _on_telemetry_received(data: Dictionary):
    var v_speed = data["vertical_speed"]
    
    if abs(v_speed) < 0.5:
        status = "HOVERING"
    elif v_speed > 5.0:
        status = "CLIMBING FAST"
    elif v_speed > 1.0:
        status = "CLIMBING"
    elif v_speed < -5.0:
        status = "FALLING FAST"
    elif v_speed < -1.0:
        status = "DESCENDING"
    else:
        status = "LEVELING"
```

---

## Data Update Frequencies

The bridge_python collects data at different refresh rates for optimization:

### Critical Data (Every frame = 30 Hz)
- `speed`
- `altitude`
- `vertical_speed`

### Important Data (Every 5 frames = 6 Hz)
- `g_force`
- `max_g_force`
- `temperature`
- `liquid_fuel_percent`
- `monopropellant_percent`
- `engines_active`

### Normal Data (Every 10 frames = 3 Hz)
- `apoapsis`
- `periapsis`
- `apoapsis_time`
- `periapsis_time`

**Note**: All data is sent every 100ms to Godot, but the bridge updates at different rates internally.

---

## Connection Status

### Handle Connection Success

```gdscript
func _on_websocket_connected():
    print("✓ Connected to bridge_python server")
    connection_status.text = "CONNECTED"
    connection_status.modulate = Color.GREEN
```

### Handle Connection Failure

```gdscript
func _on_websocket_closed():
    print("✗ Disconnected from server")
    connection_status.text = "DISCONNECTED"
    connection_status.modulate = Color.RED
```

### Handle Invalid Data

```gdscript
func _on_telemetry_received(raw_data: String):
    var data = JSON.parse_string(raw_data)
    
    if data == null:
        print("✗ Invalid JSON received")
        return
    
    # Process valid data...
```

---

## Troubleshooting

### No data received?

1. **Check network connection**: Can you ping 192.168.1.56?
2. **Check bridge is running**: `ps aux | grep bridge_python`
3. **Check WebSocket port**: `sudo netstat -tlnp | grep 8080`
4. **Check firewall**: Allow connections on port 8080

### Values stuck at 0?

1. **KSP not running?** Start Kerbal Space Program first
2. **kRPC not responding?** Check KSP console for errors
3. **Raspberry Pi not connected to KSP PC?** Check network cable

### Gauge scaling/display issues?

Use these ranges for UI scaling:

```gdscript
# Speed gauge (0-300 m/s typical cruising altitude)
speed_gauge.value = clamp(data["speed"], 0, 300)

# Altitude gauge (0-100km typical)
altitude_gauge.value = clamp(data["altitude"], 0, 100000)

# Fuel gauge (0-100%)
fuel_gauge.value = clamp(data["liquid_fuel_percent"], 0, 100)

# G-Force gauge (0-5g typical)
g_force_gauge.value = clamp(data["g_force"], 0, 5)
```

---

## Next Steps

1. Update `main.gd` to parse this telemetry data
2. Create display elements for each gauge/indicator
3. Implement color coding for warnings (red = dangerous)
4. Test connection with bridge_python running locally

For implementation examples, see the Godot Scripts folder.

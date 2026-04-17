# Godot UI Configuration Guide

## Current Architecture

Godot communicates with the bridge_python server via **WebSocket** to receive telemetry data in real-time.

### Data Flow

```
bridge_python (ws://0.0.0.0:8080/telemetry)
              ↓ WebSocket
           Godot Client
              ↓
        Display telemetry
```

## Configuration

The Godot client has hardcoded WebSocket settings. Update them:

### Option 1: Edit in main.gd (Recommended)

File: `godot_ui/Scripts/main.gd`

```gdscript
@export var ws_host: String = "192.168.1.56"  # ← Change to your Raspberry Pi IP
@export var ws_port: int = 8080
@export var ws_path: String = "/telemetry"
@export var auto_connect: bool = true
```

### Option 2: Configure via Godot Editor

1. Open `godot_ui/project.godot` in Godot
2. Select the "Main" node in the scene tree
3. In the Inspector (right panel), find:
   - **Ws Host**: Set to `192.168.1.56` (your Raspberry Pi IP)
   - **Ws Port**: Leave as `8080`
   - **Ws Path**: Leave as `/telemetry`
   - **Auto Connect**: Check to auto-connect on startup

### Option 3: Connection Dialog

Users can connect manually via the connection dialog:
- IP input field in the "Connection" window
- Click "Connect" button
- Godot connects to `ws://[INPUT_IP]:8080/telemetry`

## Testing the Connection

### 1. Start bridge_python on Raspberry Pi
```bash
cd ~/La_Capsule_V3/bridge_python
python3 main.py
```

Expected:
```
✓ Serveur WebSocket démarré
```

### 2. Open Godot Editor
```bash
cd ~/La_Capsule_V3/godot_ui
godot
```

### 3. Open Project and Run
- File → Open Project → Select project.godot
- Press F5 (or Play button)

### 4. Verify Connection
- Check Godot console: Should show "Connected to WebSocket"
- Check console labels update with telemetry
- Press Ctrl+C to stop

## Godot Script Structure

### main.gd
- **Purpose**: Main telemetry UI manager
- **Connects to**: WebSocket server
- **Updates**: Speed, altitude, apoapsis, periapsis, fuel bars
- **Features**: Auto-reconnect on disconnect

### Scripts Overview

```
main.gd                    # Main telemetry connector
├─ _ready()              # Initialize WebSocket
├─ _process()            # Handle connection/disconnection
├─ _on_ws_connected()    # When WebSocket connects
├─ _on_ws_message()      # When telemetry data received
└─ _update_ui()          # Update UI labels

connection_window.gd      # Connection dialog (optional)
├─ _ready()              # Initialize input fields
└─ _on_connect_pressed() # Emit signal with IP address
```

## Data Structure

The WebSocket receives telemetry in JSON format every 100ms:

```json
{
  "speed": 450.5,
  "altitude": 85000.0,
  "apoapsis": 120000.0,
  "periapsis": 50000.0,
  "g_force": 2.5,
  "temperature": 350.0
}
```

Godot parses this and updates UI labels accordingly.

## Extending Godot UI

### Add a New Telemetry Display

1. **Add UI element** in Scene editor (e.g., Label, ProgressBar)
2. **Give it a unique name** (e.g., "YawValue")
3. **Update main.gd** to find and update it:

```gdscript
var yaw_label: Label

func _ready():
	# ... existing code ...
	yaw_label = get_node_or_null("GameScreen/Content/Yaw/YawValue")

func _update_ui(data: Dictionary):
	# ... existing code ...
	if yaw_label and data.has("yaw"):
		yaw_label.text = "%.1f°" % data["yaw"]
```

### Add Control Buttons (Future Enhancement)

Currently Godot is **display-only**. To add commands:

1. **Add buttons** to the scene
2. **Create callback functions**:

```gdscript
func _on_stage_button_pressed():
	var cmd = {"action": "stage"}
	ws.send_text(JSON.stringify(cmd))

func _on_sas_button_pressed():
	var cmd = {"action": "sas", "state": true}
	ws.send_text(JSON.stringify(cmd))
```

3. **Update bridge_python** to receive and process commands

## Troubleshooting

### "Cannot connect to WebSocket"
- Check Raspberry Pi IP is correct: `hostname -I` on Raspi
- Verify port 8080 is not blocked by firewall
- Check bridge_python is running: `netstat -an | grep 8080`
- Try: `python3 -c "import websockets, asyncio; asyncio.run(websockets.connect('ws://[RASPI_IP]:8080/telemetry'))"`

### "Connection keeps disconnecting"
- Check network stability (ping Raspberry Pi)
- Look at bridge_python logs for errors
- Check system resources on Raspberry Pi (CPU, RAM, disk)

### "Telemetry data not updating"
- Verify KSP is running with active flight
- Check kRPC server is connected: `python3 main.py` should show connection message
- Check firewall between PC and Raspberry Pi

### "Script errors in Godot console"
- Check for typos in node paths (main.gd line ~25)
- Verify scene structure matches expected paths
- Use "find_child()" fallback for more robust node finding

## Scene Structure

Expected Godot scene hierarchy:

```
Main (main.gd attached)
├─ GameScreen
│  └─ Content
│     ├─ Speed
│     │  └─ SpeedValue (Label) ← Updated with speed
│     ├─ CenterContainer
│     │  └─ Values
│     │     ├─ Altitude
│     │     │  └─ AltitudeValue (Label)
│     │     ├─ Apoastre
│     │     │  └─ ApoapsisValue (Label)
│     │     └─ Périastre
│     │        └─ PeriapsisValue (Label)
│     └─ Bottom
│        └─ FuelBar (ProgressBar)
└─ ConnectionWindow (optional, for manual IP input)
```

## Future Enhancements

1. **Bidirectional Communication**
   - Add buttons to Godot UI for control commands
   - Modify bridge_python server to receive commands

2. **Mobile Client**
   - Create Godot export for Android/iOS
   - Same WebSocket connection

3. **Enhanced Displays**
   - Real-time graphs (altitude vs time)
   - G-force indicator
   - Fuel consumption rate
   - Orbital display

4. **Settings Panel**
   - Persistent IP/port configuration
   - Update intervals
   - UI theme selection

---

For system architecture details, see [ARCHITECTURE.md](../ARCHITECTURE.md)

extends Node
# Telemetry UI manager: connects to a WebSocket server and updates UI labels.
# Exports allow configuring host/port/path from the editor.

@export var ws_host: String = "192.168.1.21"
@export var ws_port: int = 8080
@export var ws_path: String = "/"
@export var auto_connect: bool = true
@export var reconnect_delay: float = 2.0 # seconds

signal telemetry_updated(data)

var ws: WebSocketPeer
var connected := false
var _reconnect_time := 0.0

var speed_label: Label
var apoapsis_label: Label
var altitude_label: Label
var periapsis_label: Label
var fuel_bar: ProgressBar
var liquid_fuel_label: Label
var oxidizer_label: Label
var solid_fuel_label: Label
var rocket: Control  # Reference to the rocket visualization

func _ready():
	ws = WebSocketPeer.new()
	# cache UI nodes inside the instanced Telemetry scene (node name "GameScreen")
	# main.tscn contains an instance named GameScreen which is the root of Telemetry.tscn
	var gs = "GameScreen"
	# Use get_node_or_null to avoid hard crashes if scene changes; log helpful errors
	speed_label = get_node_or_null("%s/Content/Speed/VBoxContainer/SpeedValue" % gs)
	apoapsis_label = get_node_or_null("%s/Content/CenterContainer/Values/Apoastre/ApoapsisValue" % gs)
	altitude_label = get_node_or_null("%s/Content/CenterContainer/Values/Altitude/AltitudeValue" % gs)
	periapsis_label = get_node_or_null("%s/Content/CenterContainer/Values/Périastre/PeriapsisValue" % gs)
	fuel_bar = get_node_or_null("%s/Content/Bottom/CenterContainer/VBoxContainer/HBoxContainer/Booster1/FuelBar" % gs)

	# If any lookup failed, try a name-based search as a fallback (more resilient to scene changes)
	if speed_label == null:
		# try to find by node name anywhere under Main
		speed_label = find_child("SpeedValue", true, false)
		if speed_label:
			print("Found SpeedValue via find_child() fallback")
		else:
			push_error("Node not found: %s/Content/Speed/VBoxContainer/SpeedValue (and fallback failed)" % gs)

	if apoapsis_label == null:
		apoapsis_label = find_child("ApoapsisValue", true, false)
		if apoapsis_label:
			print("Found ApoapsisValue via find_child() fallback")
		else:
			push_error("Node not found: %s/Content/CenterContainer/Values/Apoastre/ApoapsisValue (and fallback failed)" % gs)

	if altitude_label == null:
		altitude_label = find_child("AltitudeValue", true, false)
		if altitude_label:
			print("Found AltitudeValue via find_child() fallback")
		else:
			push_error("Node not found: %s/Content/CenterContainer/Values/Altitude/AltitudeValue (and fallback failed)" % gs)

	if periapsis_label == null:
		periapsis_label = find_child("PeriapsisValue", true, false)
		if periapsis_label:
			print("Found PeriapsisValue via find_child() fallback")
		else:
			push_error("Node not found: %s/Content/CenterContainer/Values/Périastre/PeriapsisValue (and fallback failed)" % gs)

	# The ProgressBar in the scene is named "ProgressBar4" under Booster4; try that path first
	if fuel_bar == null:
		fuel_bar = get_node_or_null("%s/Content/Bottom/CenterContainer/VBoxContainer/HBoxContainer/Booster4/ProgressBar4" % gs)
		if fuel_bar:
			print("Found fuel ProgressBar via corrected path")
		else:
			# try a name-based fallback
			fuel_bar = find_child("ProgressBar4", true, false)
			if fuel_bar:
				print("Found ProgressBar4 via find_child() fallback")
			else:
				push_error("Fuel ProgressBar not found under expected paths (and fallback failed)")

	# Try to find fuel-related labels (can be null if not in UI)
	liquid_fuel_label = find_child("LiquidFuelValue", true, false)
	oxidizer_label = find_child("OxidizerValue", true, false)
	solid_fuel_label = find_child("SolidFuelValue", true, false)
	
	# Get reference to rocket visualization
	rocket = get_node_or_null("GameScreen/Rocket")
	if rocket == null:
		# Try to find it if it has a different path
		rocket = find_child("Rocket", true, false)
		if rocket:
			print("Found Rocket node via find_child()")
		else:
			print("Warning: Rocket node not found - stage fuel gauges won't display")

	if auto_connect:
		_connect()

func _process(delta):
	# tentative de reconnexion si déconnecté
	if not connected and _reconnect_time > 0.0:
		_reconnect_time -= delta
		if _reconnect_time <= 0.0:
			_connect()

	# Poll WebSocket pour traiter les événements
	if ws.get_ready_state() != WebSocketPeer.STATE_CLOSED:
		ws.poll()

	# vérifier l'état
	match ws.get_ready_state():
		WebSocketPeer.STATE_OPEN:
			if not connected:
				_on_ws_connected()
			_check_incoming()
		WebSocketPeer.STATE_CLOSING:
			pass # en cours de fermeture
		WebSocketPeer.STATE_CLOSED:
			if connected:
				_on_ws_closed()

func _connect():
	var url = "ws://%s:%d%s" % [ws_host, ws_port, ws_path]
	var err = ws.connect_to_url(url)
	if err == OK:
		print("Attempting WebSocket connect to ", url)
	else:
		print("WebSocket connect_to_url error: ", err)
		_reconnect_time = reconnect_delay
		# Show connection window so user can retry / change IP
		var cw = get_node_or_null("ConnectionWindow")
		if cw:
			cw.show()

func _on_ws_connected():
	connected = true
	print("WebSocket connected!")
	# Hide the connection window when connection is established
	var cw = get_node_or_null("ConnectionWindow")
	if cw:
		cw.hide()

func _on_ws_closed():
	connected = false
	print("WebSocket closed")
	_reconnect_time = reconnect_delay
	# Show the connection window so user can re-enter IP
	var cw = get_node_or_null("ConnectionWindow")
	if cw:
		cw.show()

func _check_incoming():
	while ws.get_available_packet_count() > 0:
		var packet = ws.get_packet()
		if ws.was_string_packet():
			_process_message(packet.get_string_from_utf8())
		else:
			print("Received non-text packet, ignoring.")

func _process_message(text: String) -> void:
	# Expect JSON like {"speed": 123.4, "altitude": 1000, "apoapsis": 5000, "periapsis": 400, "liquid_fuel": 100, "oxidizer": 150, "solid_fuel": 200}
	var result = JSON.parse_string(text)
	if typeof(result) != TYPE_DICTIONARY:
		print("Received non-JSON or parse error:", text)
		return
	var data: Dictionary = result

	# Accept both French and English keys
	var speed = data.get("speed", data.get("vitesse", null))
	var altitude = data.get("altitude", data.get("altitude_m", data.get("alt", null)))
	var apo = data.get("apoapsis", data.get("apoastre", data.get("apo", null)))
	var peri = data.get("periapsis", data.get("periastre", data.get("peri", null)))
	var fuel = data.get("fuel", data.get("carburant", data.get("reserve", null)))
	var liquid_fuel = data.get("liquid_fuel", data.get("carburant_liquide", null))
	var oxidizer = data.get("oxidizer", data.get("oxidant", null))
	var solid_fuel = data.get("solid_fuel", data.get("carburant_solide", null))

	if speed != null:
		speed_label.text = _format_speed(speed)
	if altitude != null:
		altitude_label.text = _format_big_number(altitude)
	if apo != null:
		apoapsis_label.text = _format_big_number(apo)
	if peri != null:
		periapsis_label.text = _format_big_number(peri)
	if fuel != null:
		# Fuel expected 0-100
		if typeof(fuel) in [TYPE_FLOAT, TYPE_INT]:
			fuel_bar.value = clamp(float(fuel), 0.0, fuel_bar.max_value)
		elif typeof(fuel) == TYPE_STRING:
			var fv = float(fuel)
			fuel_bar.value = clamp(fv, 0.0, fuel_bar.max_value)
	
	# Update fuel labels if they exist
	if liquid_fuel != null and liquid_fuel_label:
		liquid_fuel_label.text = _format_big_number(float(liquid_fuel))
	if oxidizer != null and oxidizer_label:
		oxidizer_label.text = _format_big_number(float(oxidizer))
	if solid_fuel != null and solid_fuel_label:
		solid_fuel_label.text = _format_big_number(float(solid_fuel))
	
	# Update rocket stage fuel gauges if rocket exists
	if rocket and rocket.has_method("update_from_telemetry"):
		rocket.update_from_telemetry(data)

	emit_signal("telemetry_updated", data)

func _format_speed(s) -> String:
	# Show with 3 decimals and unit km/s
	var f = float(s)
	return "%06.3f km/s" % f

func _format_big_number(n) -> String:
	# Format with thousand separators
	var val = int(n)
	var s = str(val)
	var parts = []
	while s.length() > 3:
		parts.insert(0, s.substr(s.length()-3, 3))
		s = s.substr(0, s.length()-3)
	parts.insert(0, s)
	return String(".").join(parts)


func _on_connection_window_connect_requested(ip: String) -> void:
	ws_host = ip
	# Try connecting immediately when user requests connection
	_reconnect_time = 0.0
	_connect()

extends Node
# La Capsule V3 - UI télémétrie.
# Se connecte en WebSocket au bridge Python (par défaut localhost),
# affiche les valeurs et l'état de chaque étage.

@export var ws_host: String = "127.0.0.1"
@export var ws_port: int = 8080
@export var ws_path: String = "/"
@export var auto_connect: bool = true
@export var reconnect_delay: float = 2.0 # secondes avant retry
@export var fallback_delay: float = 5.0  # secondes avant d'afficher ConnectionWindow
@export var kerbin_radius_m: float = 600000.0 # soustrait aux apo/péri

signal telemetry_updated(data)

var ws: WebSocketPeer
var connected := false
var _reconnect_time := 0.0
var _first_attempt_time := 0.0
var _fallback_shown := false

# Nœuds UI mis en cache
var speed_label: Label
var apoapsis_label: Label
var altitude_label: Label
var periapsis_label: Label
var fuel_bars: Array = [] # [stage1, stage2, stage3, stage4] → noeuds ProgressBar

const DETACHED_COLOR := Color(0.3, 0.3, 0.3, 1.0)
const ATTACHED_COLOR := Color(1, 1, 1, 1)

func _ready():
	ws = WebSocketPeer.new()
	_cache_ui_nodes()

	if auto_connect:
		_first_attempt_time = Time.get_ticks_msec() / 1000.0
		_connect()

func _cache_ui_nodes():
	speed_label = find_child("SpeedValue", true, false)
	apoapsis_label = find_child("ApoapsisValue", true, false)
	altitude_label = find_child("AltitudeValue", true, false)
	periapsis_label = find_child("PeriapsisValue", true, false)

	# 4 stages : Booster1/FuelBar = stage 1, ProgressBar2..4 = stages 2..4
	var stage1 = find_child("FuelBar", true, false)
	var stage2 = find_child("ProgressBar2", true, false)
	var stage3 = find_child("ProgressBar3", true, false)
	var stage4 = find_child("ProgressBar4", true, false)
	fuel_bars = [stage1, stage2, stage3, stage4]

	for i in fuel_bars.size():
		if fuel_bars[i] == null:
			push_warning("Fuel bar stage %d introuvable" % (i + 1))

func _process(delta):
	if not connected and _reconnect_time > 0.0:
		_reconnect_time -= delta
		if _reconnect_time <= 0.0:
			_connect()

	ws.poll()
	match ws.get_ready_state():
		WebSocketPeer.STATE_OPEN:
			if not connected:
				_on_ws_connected()
			_check_incoming()
		WebSocketPeer.STATE_CLOSED:
			if connected:
				_on_ws_closed()
			else:
				_maybe_show_fallback()

func _connect():
	var url = "ws://%s:%d%s" % [ws_host, ws_port, ws_path]
	var err = ws.connect_to_url(url)
	if err == OK:
		print("[WS] Tentative de connexion: ", url)
	else:
		print("[WS] Erreur connect_to_url: ", err)
		_reconnect_time = reconnect_delay

func _on_ws_connected():
	connected = true
	_fallback_shown = false
	print("[WS] Connecté")
	var cw = get_node_or_null("ConnectionWindow")
	if cw:
		cw.hide()

func _on_ws_closed():
	connected = false
	print("[WS] Déconnecté")
	_reconnect_time = reconnect_delay

func _maybe_show_fallback():
	if _fallback_shown:
		return
	var now = Time.get_ticks_msec() / 1000.0
	if now - _first_attempt_time < fallback_delay:
		return
	_fallback_shown = true
	var cw = get_node_or_null("ConnectionWindow")
	if cw:
		cw.show()

func _check_incoming():
	while ws.get_available_packet_count() > 0:
		var packet = ws.get_packet()
		if ws.was_string_packet():
			_process_message(packet.get_string_from_utf8())

func _process_message(text: String) -> void:
	var result = JSON.parse_string(text)
	if typeof(result) != TYPE_DICTIONARY:
		return
	var data: Dictionary = result

	var speed = data.get("speed")
	var altitude = data.get("altitude")
	var apo = data.get("apoapsis")
	var peri = data.get("periapsis")

	if speed != null and speed_label:
		speed_label.text = _format_speed(speed)
	if altitude != null and altitude_label:
		altitude_label.text = _format_big_number(altitude)
	if apo != null and apoapsis_label:
		apoapsis_label.text = _format_big_number(float(apo) - kerbin_radius_m)
	if peri != null and periapsis_label:
		periapsis_label.text = _format_big_number(float(peri) - kerbin_radius_m)

	var stages = data.get("stages", [])
	if stages is Array:
		_update_stages(stages)

	emit_signal("telemetry_updated", data)

func _update_stages(stages: Array):
	# stages : liste d'objets {stage, fuel_percent, attached}
	# fuel_bars[0] = stage 1 (FuelBar), fuel_bars[1] = stage 2, etc.
	# On mappe du plus récent (courant) au plus ancien en parcourant fuel_bars.
	for i in fuel_bars.size():
		var bar = fuel_bars[i]
		if bar == null:
			continue
		if i < stages.size():
			var s = stages[i]
			var pct = float(s.get("fuel_percent", 0.0))
			var attached = bool(s.get("attached", true))
			bar.value = clamp(pct, 0.0, bar.max_value)
			bar.modulate = ATTACHED_COLOR if attached else DETACHED_COLOR
		else:
			bar.value = 0.0
			bar.modulate = DETACHED_COLOR

func _format_speed(s) -> String:
	return "%06.3f km/s" % float(s)

func _format_big_number(n) -> String:
	var val = int(n)
	var neg = val < 0
	if neg:
		val = -val
	var s = str(val)
	var parts = []
	while s.length() > 3:
		parts.insert(0, s.substr(s.length() - 3, 3))
		s = s.substr(0, s.length() - 3)
	parts.insert(0, s)
	var joined = String(".").join(parts)
	return "-" + joined if neg else joined

func _on_connection_window_connect_requested(ip: String) -> void:
	ws_host = ip
	_reconnect_time = 0.0
	_connect()

extends Node
# La Capsule V3 - UI télémétrie.
# Se connecte en WebSocket au bridge Python (par défaut localhost),
# affiche les valeurs et l'état de chaque étage.

@export var ws_host: String = "127.0.0.1"
@export var ws_port: int = 8080
@export var ws_path: String = "/"
@export var auto_connect: bool = true
@export var reconnect_delay: float = 2.0
@export var fallback_delay: float = 5.0

signal telemetry_updated(data)

var ws: WebSocketPeer
var connected := false
var _reconnect_time := 0.0
var _first_attempt_time := 0.0
var _fallback_shown := false

var speed_label: Label
var apoapsis_label: Label
var altitude_label: Label
var periapsis_label: Label
var apo_time_label: Label
var peri_time_label: Label
var vspeed_value: Label
var vspeed_arrow: Label
var gforce_label: Label
var heat_temp_label: Label
var rocket: Node = null


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
	apo_time_label = find_child("ApoTimeValue", true, false)
	peri_time_label = find_child("PeriTimeValue", true, false)
	vspeed_value = find_child("VSpeedValue", true, false)
	vspeed_arrow = find_child("VSpeedArrow", true, false)
	gforce_label = find_child("GForceValue", true, false)
	heat_temp_label = find_child("HeatTempValue", true, false)

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
	var vspeed = data.get("vertical_speed")
	var gforce = data.get("g_force")
	var mission  = data.get("mission_time")

	if speed != null and speed_label:
		speed_label.text = _format_speed(speed)
	if altitude != null and altitude_label:
		altitude_label.text = _format_big_number(altitude)
	if apo != null and apoapsis_label:
		apoapsis_label.text = _format_big_number(float(apo))
	if peri != null and periapsis_label:
		periapsis_label.text = _format_big_number(float(peri))
	if vspeed != null and vspeed_arrow and vspeed_value:
		vspeed_value.text = "%+.1f m/s" % float(vspeed)
		vspeed_arrow.text = "▲" if float(vspeed) > 0.0 else "▼"

	var apo_time = data.get("time_to_apoapsis")
	var peri_time = data.get("time_to_periapsis")
	if apo_time != null and apo_time_label:
		apo_time_label.text = _format_time(float(apo_time))
	if peri_time != null and peri_time_label:
		peri_time_label.text = _format_time(float(peri_time))

	var heat_temp = data.get("heat_shield_temp")
	if heat_temp != null and heat_temp_label:
		heat_temp_label.text = "%d" % int(float(heat_temp) - 273.15)
	if gforce != null and gforce_label:
		gforce_label.text = "%.2f" % float(gforce)


	emit_signal("telemetry_updated", data)

func _format_speed(s) -> String:
	return "%.0f" % (float(s))

func _format_time(t: float) -> String:
	if is_nan(t) or is_inf(t) or abs(t) > 86400.0:
		return "--:--"
	var prefix := "-" if t < 0.0 else ""
	var sec := int(abs(t))
	var m := sec / 60
	sec = sec % 60
	if m >= 60:
		var h := m / 60
		m = m % 60
		return prefix + "%d:%02d:%02d" % [h, m, sec]
	return prefix + "%02d:%02d" % [m, sec]

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

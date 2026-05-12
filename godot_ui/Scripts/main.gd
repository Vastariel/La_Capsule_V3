extends Node
# La Capsule V3 — UI télémétrie V2 HUD.
# Se connecte en WebSocket au bridge Python (par défaut localhost).

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
var _mission_start_time: float = -1.0   # UTC seconds when T=0 received
var _mission_elapsed: float = 0.0

# V2 palette
const AMBER  := Color(0.941176, 0.690196, 0.282353, 1.0)
const CYAN   := Color(0.384314, 0.784314, 0.878431, 1.0)
const RED    := Color(0.909804, 0.333333, 0.184314, 1.0)
const DIM    := Color(1.0, 1.0, 1.0, 0.18)

# UI node refs — top strip
var mission_time_label: Label
var phase_label: Label
var stage_value_label: Label

# Speed circle
var speed_circle_node: Control
var speed_label: Label
var altitude_label: Label
var vario_arrow: Label
var vspeed_label: Label

# Arc gauges
var gforce_arc: Control
var gforce_value: Label
var heat_arc: Control
var heat_temp_label: Label

# Apo / Peri
var apoapsis_label: Label
var periapsis_label: Label
var apo_time_label: Label
var peri_time_label: Label

# Stage bars  [ProgressBar4(boosters), FuelBar(E1), ProgressBar2(E2), ProgressBar3(E3)]
var fuel_bars: Array = []
# Matching label nodes for percents
var stage_pct_labels: Array = []
# Stage name labels for dimming when detached
var stage_name_labels: Array = []


func _ready() -> void:
	ws = WebSocketPeer.new()
	_cache_ui_nodes()
	_init_bar_styles()

	if auto_connect:
		_first_attempt_time = Time.get_ticks_msec() / 1000.0
		_connect()


func _cache_ui_nodes() -> void:
	mission_time_label = find_child("MissionTimeValue", true, false)
	phase_label        = find_child("PhaseValue",       true, false)
	stage_value_label  = find_child("StageValue",       true, false)

	speed_circle_node  = find_child("SpeedCircle",  true, false)
	speed_label        = find_child("SpeedValue",   true, false)
	altitude_label     = find_child("AltitudeValue",true, false)
	vario_arrow        = find_child("VarioArrow",   true, false)
	vspeed_label       = find_child("VSpeedValue",  true, false)

	gforce_arc         = find_child("GForceArc",    true, false)
	gforce_value       = find_child("GForceValue",  true, false)
	heat_arc           = find_child("HeatArc",      true, false)
	heat_temp_label    = find_child("HeatTempValue",true, false)

	apoapsis_label     = find_child("ApoapsisValue", true, false)
	periapsis_label    = find_child("PeriapsisValue",true, false)
	apo_time_label     = find_child("ApoTimeValue",  true, false)
	peri_time_label    = find_child("PeriTimeValue", true, false)

	# Stage bars: BOOSTERS, ÉTAGE 1, ÉTAGE 2, ÉTAGE 3
	fuel_bars = [
		find_child("ProgressBar4", true, false),  # boosters  → stages[3]
		find_child("FuelBar",      true, false),  # étage 1   → stages[0]
		find_child("ProgressBar2", true, false),  # étage 2   → stages[1]
		find_child("ProgressBar3", true, false),  # étage 3   → stages[2]
	]
	stage_pct_labels = [
		find_child("StagePct0", true, false),
		find_child("StagePct1", true, false),
		find_child("StagePct2", true, false),
		find_child("StagePct3", true, false),
	]
	stage_name_labels = [
		find_child("StageLabel0", true, false),
		find_child("StageLabel1", true, false),
		find_child("StageLabel2", true, false),
		find_child("StageLabel3", true, false),
	]


func _init_bar_styles() -> void:
	var cyan_fill := StyleBoxFlat.new()
	cyan_fill.bg_color = CYAN
	for bar: ProgressBar in fuel_bars:
		if bar == null:
			continue
		bar.add_theme_stylebox_override("fill", cyan_fill.duplicate())


func _process(delta: float) -> void:
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


func _connect() -> void:
	var url := "ws://%s:%d%s" % [ws_host, ws_port, ws_path]
	var err := ws.connect_to_url(url)
	if err == OK:
		print("[WS] Tentative de connexion: ", url)
	else:
		print("[WS] Erreur connect_to_url: ", err)
		_reconnect_time = reconnect_delay


func _on_ws_connected() -> void:
	connected = true
	_fallback_shown = false
	print("[WS] Connecté")
	var cw := get_node_or_null("ConnectionWindow")
	if cw:
		cw.hide()


func _on_ws_closed() -> void:
	connected = false
	print("[WS] Déconnecté")
	_reconnect_time = reconnect_delay


func _maybe_show_fallback() -> void:
	if _fallback_shown:
		return
	var now := Time.get_ticks_msec() / 1000.0
	if now - _first_attempt_time < fallback_delay:
		return
	_fallback_shown = true
	var cw := get_node_or_null("ConnectionWindow")
	if cw:
		cw.show()


func _check_incoming() -> void:
	while ws.get_available_packet_count() > 0:
		var packet := ws.get_packet()
		if ws.was_string_packet():
			_process_message(packet.get_string_from_utf8())


func _process_message(text: String) -> void:
	var result := JSON.parse_string(text)
	if typeof(result) != TYPE_DICTIONARY:
		return
	var data: Dictionary = result

	var speed    = data.get("speed")
	var altitude = data.get("altitude")
	var apo      = data.get("apoapsis")
	var peri     = data.get("periapsis")
	var vspeed   = data.get("vertical_speed")
	var gforce   = data.get("g_force")
	var mission  = data.get("mission_time")
	var stage    = data.get("current_stage")

	# Speed (m/s)
	if speed != null:
		var spd := float(speed)
		if speed_label:
			speed_label.text = _format_speed_ms(spd)
		if speed_circle_node and speed_circle_node.has_method("set_speed"):
			speed_circle_node.call("set_speed", spd)

	# Altitude SOL (m → km.m)
	if altitude != null and altitude_label:
		altitude_label.text = _format_big_number(float(altitude))

	# Vertical speed + vario arrow
	if vspeed != null:
		var vs := float(vspeed)
		var going_up := vs >= 0.0
		if vario_arrow:
			vario_arrow.text = "▲" if going_up else "▼"
			vario_arrow.add_theme_color_override("font_color", CYAN if going_up else AMBER)
		if vspeed_label:
			vspeed_label.text = "%+.1f m/s" % vs
			vspeed_label.add_theme_color_override("font_color", CYAN if going_up else AMBER)

	# G-Force arc gauge
	if gforce != null:
		var gf := float(gforce)
		var g_color := RED if gf > 4.0 else AMBER
		if gforce_arc and gforce_arc.has_method("set_arc_value"):
			gforce_arc.call("set_arc_value", gf, g_color)
		if gforce_value:
			gforce_value.text = "%4.2f" % gf
			gforce_value.add_theme_color_override("font_color", g_color)
			var unit := find_child("GForceUnit", true, false) as Label
			if unit:
				unit.add_theme_color_override("font_color", g_color)

	# Heat shield temperature
	var heat_temp = data.get("heat_shield_temp")
	if heat_temp != null:
		var ht := float(heat_temp)
		var t_color := _temp_color(ht)
		if heat_arc and heat_arc.has_method("set_arc_value"):
			heat_arc.call("set_arc_value", minf(ht, 2000.0), t_color)
			heat_arc.max_value = 2000.0
		if heat_temp_label:
			heat_temp_label.text = "%04.1f" % ht if ht < 10000.0 else "%d" % int(ht)
			heat_temp_label.add_theme_color_override("font_color", t_color)

	# Apoapsis / Periapsis
	if apo != null and apoapsis_label:
		apoapsis_label.text = _format_big_number(float(apo))
	if peri != null and periapsis_label:
		periapsis_label.text = _format_big_number(float(peri))

	var apo_time  = data.get("time_to_apoapsis")
	var peri_time = data.get("time_to_periapsis")
	if apo_time  != null and apo_time_label:
		apo_time_label.text  = _format_time(float(apo_time))
	if peri_time != null and peri_time_label:
		peri_time_label.text = _format_time(float(peri_time))

	# Mission clock
	if mission != null and mission_time_label:
		_mission_elapsed = float(mission)
		mission_time_label.text = _format_time_full(float(mission))

	# Phase (derived from data)
	if phase_label:
		phase_label.text = _phase_from_data(data).to_upper()

	# Current stage
	if stage != null and stage_value_label:
		stage_value_label.text = str(int(stage))

	# Stage fuel bars
	var stages = data.get("stages", [])
	if stages is Array:
		_update_stages(stages)

	emit_signal("telemetry_updated", data)


func _update_stages(stages: Array) -> void:
	# Display order: BOOSTERS (stages[3]), ÉTAGE1 (stages[0]), ÉTAGE2 (stages[1]), ÉTAGE3 (stages[2])
	var stage_idx := [3, 0, 1, 2]

	for row in 4:
		var bar   := fuel_bars[row]         as ProgressBar
		var pct_l := stage_pct_labels[row]  as Label
		var name_l:= stage_name_labels[row] as Label
		var si    := stage_idx[row]

		if bar == null:
			continue

		if si < stages.size():
			var s        := stages[si]
			var pct      := float(s.get("fuel_percent", 0.0))
			var attached := bool(s.get("attached", true))

			bar.value = clampf(pct, 0.0, 100.0)

			var bar_color: Color
			if not attached:
				bar_color = DIM
			elif pct < 15.0:
				bar_color = RED
			elif pct < 30.0:
				bar_color = AMBER
			else:
				bar_color = CYAN

			var fill_style := StyleBoxFlat.new()
			fill_style.bg_color = bar_color
			bar.add_theme_stylebox_override("fill", fill_style)

			var text_color := AMBER if attached else DIM
			if pct_l:
				pct_l.text = "%d%%" % int(pct) if attached else "—"
				pct_l.add_theme_color_override("font_color", text_color)
			if name_l:
				name_l.add_theme_color_override("font_color", text_color)
		else:
			bar.value = 0.0
			var fill_style := StyleBoxFlat.new()
			fill_style.bg_color = DIM
			bar.add_theme_stylebox_override("fill", fill_style)
			if pct_l:
				pct_l.text = "—"
				pct_l.add_theme_color_override("font_color", DIM)
			if name_l:
				name_l.add_theme_color_override("font_color", DIM)


func _phase_from_data(d: Dictionary) -> String:
	var alt := float(d.get("altitude", 0.0))
	var vs  := float(d.get("vertical_speed", 0.0))
	if alt < 100.0 and absf(vs) < 2.0:
		return "Pré-vol"
	if alt < 80000.0 and vs > 5.0:
		return "Ascension"
	if alt > 70000.0 and absf(vs) < 30.0:
		return "Orbite"
	if vs < -50.0 and alt > 1000.0:
		return "Rentrée"
	if alt < 1000.0 and vs < 0.0:
		return "Descente"
	return "—"


func _temp_color(t: float) -> Color:
	if t > 1500.0:
		return RED
	if t > 800.0:
		return AMBER
	return CYAN


func _format_speed_ms(s: float) -> String:
	# Show m/s with one decimal, grouped by thousands
	var i := int(s)
	var frac := int((s - i) * 10.0)
	return "%s.%d" % [_group_thousands(i), frac]


func _format_time(t: float) -> String:
	if t < 0.0:
		return "--:--"
	var sec := int(t)
	var m   := sec / 60
	sec = sec % 60
	if m >= 60:
		var h := m / 60
		m = m % 60
		return "%d:%02d:%02d" % [h, m, sec]
	return "%02d:%02d" % [m, sec]


func _format_time_full(t: float) -> String:
	var sec := int(absf(t))
	var h   := sec / 3600
	sec = sec % 3600
	var m   := sec / 60
	sec = sec % 60
	return "%02d:%02d:%02d" % [h, m, sec]


func _format_big_number(n: float) -> String:
	var val := int(n)
	var neg := val < 0
	if neg:
		val = -val
	var s := "%09d" % val          # zero-pad to 9 digits
	# Insert dots every 3 digits: 000.000.000
	var result := s.substr(0, 3) + "." + s.substr(3, 3) + "." + s.substr(6, 3)
	return "-" + result if neg else result


func _group_thousands(n: int) -> String:
	var s := str(n)
	var parts: Array = []
	while s.length() > 3:
		parts.insert(0, s.substr(s.length() - 3, 3))
		s = s.substr(0, s.length() - 3)
	parts.insert(0, s)
	return ".".join(parts)


func _on_connection_window_connect_requested(ip: String) -> void:
	ws_host = ip
	_reconnect_time = 0.0
	_connect()

extends Node
## Client kRPC minimal (protocole protobuf sur TCP, serveur RPC uniquement).
##
## Se connecte au serveur kRPC lancé dans KSP, récupère le vaisseau actif et
## interroge en boucle son cap, son tangage et son roulis (repère surface).
## Se reconnecte automatiquement si KSP est fermé, si on quitte la scène de vol
## ou si le vaisseau actif change.
##
## Format des messages : chaque message protobuf est précédé de sa taille (varint).
## Les valeurs d'arguments/résultats sont encodées sans tag :
##   objet (handle) -> varint uint64, float -> 4 octets little-endian.

signal attitude_received(heading: float, pitch: float, roll: float)
signal status_changed(text: String)

@export var host := "192.168.1.61"
@export var rpc_port := 50008         # port RPC du serveur kRPC (voir GameData/kRPC/PluginData/settings.cfg)
@export var client_name := "Godot Navball"
@export var poll_interval := 0.0       # secondes entre deux lectures (0 = chaque frame)
@export var reconnect_delay := 2.0     # secondes avant une nouvelle tentative de connexion
@export var retry_delay := 1.0         # secondes avant de redemander le vaisseau actif

const CONNECT_TIMEOUT := 5.0
const HANDSHAKE_TIMEOUT := 30.0        # laisse le temps d'accepter le client dans KSP
const RESPONSE_TIMEOUT := 5.0

enum State { DISCONNECTED, CONNECTING, HANDSHAKE, READY }
enum Pending { NONE, VESSEL, FLIGHT, ATTITUDE }

## Vrai tant que les dernières données reçues de KSP sont valides.
var has_attitude := false
var status := ""

var _tcp := StreamPeerTCP.new()
var _state := State.DISCONNECTED
var _pending := Pending.NONE
var _waiting := false
var _timer := 0.0
var _buf := PackedByteArray()
var _vessel := 0
var _flight := 0


func _process(delta: float) -> void:
	_timer -= delta

	if _state == State.DISCONNECTED:
		if _timer <= 0.0:
			_connect()
		return

	_tcp.poll()
	var tcp_status := _tcp.get_status()

	if _state == State.CONNECTING:
		if tcp_status == StreamPeerTCP.STATUS_CONNECTED:
			_send_handshake()
		elif tcp_status == StreamPeerTCP.STATUS_ERROR or _timer <= 0.0:
			_disconnect("Serveur kRPC injoignable (%s:%d)" % [host, rpc_port])
		return

	if tcp_status != StreamPeerTCP.STATUS_CONNECTED:
		_disconnect("Connexion kRPC perdue")
		return

	_receive()
	var msg: Variant = _pop_message()
	if msg != null:
		_waiting = false
		if _state == State.HANDSHAKE:
			_on_handshake(msg)
		else:
			_on_response(msg)
	elif _waiting and _timer <= 0.0:
		_disconnect("Pas de réponse du serveur kRPC")
		return

	if _state == State.READY and not _waiting and _timer <= 0.0:
		_send_next_request()


# --- Connexion -----------------------------------------------------------------

func _connect() -> void:
	_tcp = StreamPeerTCP.new()
	_buf.clear()
	if _tcp.connect_to_host(host, rpc_port) != OK:
		_disconnect("Adresse kRPC invalide : %s" % host)
		return
	_state = State.CONNECTING
	_timer = CONNECT_TIMEOUT
	_set_status("Connexion à %s:%d…" % [host, rpc_port])


func _disconnect(reason: String) -> void:
	_tcp.disconnect_from_host()
	_state = State.DISCONNECTED
	_waiting = false
	_reset_vessel()
	_timer = reconnect_delay
	_set_status(reason)


func _send_handshake() -> void:
	# ConnectionRequest { type = RPC (0) ; client_name }
	var req := _field_varint(1, 0)
	req.append_array(_field_bytes(2, client_name.to_utf8_buffer()))
	_send(req)
	_state = State.HANDSHAKE
	_waiting = true
	_timer = HANDSHAKE_TIMEOUT
	_set_status("En attente d'acceptation dans KSP…")


func _on_handshake(msg: PackedByteArray) -> void:
	# ConnectionResponse { status (0 = OK) ; message ; client_identifier }
	var resp := _parse(msg)
	var code: int = resp.get(1, [0])[0]
	if code != 0:
		var text: String = resp.get(2, [PackedByteArray()])[0].get_string_from_utf8()
		_disconnect("Connexion refusée par kRPC : %s" % text)
		return
	_state = State.READY
	_timer = 0.0
	_set_status("Connecté à kRPC")


# --- Requêtes ------------------------------------------------------------------

func _send_next_request() -> void:
	var calls: Array[PackedByteArray] = []
	if _vessel == 0:
		_pending = Pending.VESSEL
		calls.append(_call("SpaceCenter", "get_ActiveVessel"))
	elif _flight == 0:
		# Sans référentiel explicite, kRPC utilise vessel.surface_reference_frame.
		_pending = Pending.FLIGHT
		calls.append(_call("SpaceCenter", "Vessel_Flight", [_varint(_vessel)]))
	else:
		_pending = Pending.ATTITUDE
		var flight := _varint(_flight)
		calls.append(_call("SpaceCenter", "Flight_get_Heading", [flight]))
		calls.append(_call("SpaceCenter", "Flight_get_Pitch", [flight]))
		calls.append(_call("SpaceCenter", "Flight_get_Roll", [flight]))
		# Pour détecter un changement de vaisseau actif.
		calls.append(_call("SpaceCenter", "get_ActiveVessel"))

	# Request { repeated ProcedureCall calls = 1 }
	var req := PackedByteArray()
	for c in calls:
		req.append_array(_field_bytes(1, c))
	_send(req)
	_waiting = true
	_timer = RESPONSE_TIMEOUT


func _on_response(msg: PackedByteArray) -> void:
	# Response { Error error = 1 ; repeated ProcedureResult results = 2 }
	var resp := _parse(msg)
	if resp.has(1):
		_on_call_error(_error_text(resp[1][0]))
		return

	var values: Array[PackedByteArray] = []
	for raw in resp.get(2, []):
		# ProcedureResult { Error error = 1 ; bytes value = 2 }
		var result := _parse(raw)
		if result.has(1):
			_on_call_error(_error_text(result[1][0]))
			return
		var value: PackedByteArray = result.get(2, [PackedByteArray()])[0]
		values.append(value)

	if values.is_empty():
		_on_call_error("réponse vide")
		return

	match _pending:
		Pending.VESSEL:
			_vessel = _decode_handle(values[0])
			if _vessel == 0:
				_on_call_error("Aucun vaisseau actif")
				return
			_timer = 0.0
		Pending.FLIGHT:
			_flight = _decode_handle(values[0])
			_timer = 0.0
		Pending.ATTITUDE:
			if values.size() < 4 or _decode_handle(values[3]) != _vessel:
				_reset_vessel()
				_timer = 0.0
				return
			has_attitude = true
			_set_status("Connecté à kRPC — vol en cours")
			attitude_received.emit(_decode_float(values[0]), _decode_float(values[1]), _decode_float(values[2]))
			_timer = poll_interval
	_pending = Pending.NONE


func _on_call_error(text: String) -> void:
	# Typiquement : pas dans la scène de vol, vaisseau détruit…
	_reset_vessel()
	_pending = Pending.NONE
	_timer = retry_delay
	_set_status("kRPC : %s" % text)


func _reset_vessel() -> void:
	_vessel = 0
	_flight = 0
	has_attitude = false


func _set_status(text: String) -> void:
	if text != status:
		status = text
		status_changed.emit(text)


# --- Transport -----------------------------------------------------------------

func _send(msg: PackedByteArray) -> void:
	var data := _varint(msg.size())
	data.append_array(msg)
	_tcp.put_data(data)


func _receive() -> void:
	var n := _tcp.get_available_bytes()
	if n <= 0:
		return
	var r := _tcp.get_data(n)
	if r[0] == OK:
		_buf.append_array(r[1])


## Extrait un message complet du tampon, ou renvoie null s'il est incomplet.
func _pop_message() -> Variant:
	var head := _read_varint(_buf, 0)
	if head[1] < 0:
		return null
	var start: int = head[1]
	var end: int = start + head[0]
	if _buf.size() < end:
		return null
	var msg := _buf.slice(start, end)
	_buf = _buf.slice(end)
	return msg


# --- Encodage protobuf ---------------------------------------------------------

## ProcedureCall { service = 1 ; procedure = 2 ; repeated Argument arguments = 3 }
## Argument { position = 1 ; value = 2 }
static func _call(service: String, procedure: String, args: Array[PackedByteArray] = []) -> PackedByteArray:
	var msg := _field_bytes(1, service.to_utf8_buffer())
	msg.append_array(_field_bytes(2, procedure.to_utf8_buffer()))
	for i in args.size():
		var arg := _field_varint(1, i)
		arg.append_array(_field_bytes(2, args[i]))
		msg.append_array(_field_bytes(3, arg))
	return msg


static func _varint(value: int) -> PackedByteArray:
	var out := PackedByteArray()
	while true:
		var b := value & 0x7F
		value = (value >> 7) & 0x01FFFFFFFFFFFFFF  # décalage non signé
		if value == 0:
			out.push_back(b)
			break
		out.push_back(b | 0x80)
	return out


static func _field_varint(field: int, value: int) -> PackedByteArray:
	var out := _varint(field << 3)
	out.append_array(_varint(value))
	return out


static func _field_bytes(field: int, data: PackedByteArray) -> PackedByteArray:
	var out := _varint((field << 3) | 2)
	out.append_array(_varint(data.size()))
	out.append_array(data)
	return out


# --- Décodage protobuf ---------------------------------------------------------

## Renvoie [valeur, position suivante], ou [0, -1] si les données sont tronquées.
static func _read_varint(data: PackedByteArray, pos: int) -> Array:
	var result := 0
	var shift := 0
	while pos < data.size():
		var b := data[pos]
		pos += 1
		result |= (b & 0x7F) << shift
		if (b & 0x80) == 0:
			return [result, pos]
		shift += 7
	return [0, -1]


## Décode un message en { numéro_de_champ: [valeurs] }.
## Varint -> int ; longueur délimitée / fixed32 / fixed64 -> PackedByteArray.
static func _parse(data: PackedByteArray) -> Dictionary:
	var fields := {}
	var pos := 0
	while pos < data.size():
		var key_r := _read_varint(data, pos)
		if key_r[1] < 0:
			break
		var key: int = key_r[0]
		pos = key_r[1]
		var value: Variant
		match key & 7:
			0:
				var r := _read_varint(data, pos)
				value = r[0]
				pos = r[1]
			1:
				value = data.slice(pos, pos + 8)
				pos += 8
			2:
				var r := _read_varint(data, pos)
				var length: int = r[0]
				pos = r[1]
				value = data.slice(pos, pos + length)
				pos += length
			5:
				value = data.slice(pos, pos + 4)
				pos += 4
			_:
				break
		if pos < 0:
			break
		if not fields.has(key >> 3):
			fields[key >> 3] = []
		fields[key >> 3].append(value)
	return fields


static func _decode_handle(value: PackedByteArray) -> int:
	return _read_varint(value, 0)[0]


static func _decode_float(value: PackedByteArray) -> float:
	return value.decode_float(0) if value.size() >= 4 else 0.0


## Error { service = 1 ; name = 2 ; description = 3 ; stack_trace = 4 }
static func _error_text(raw: PackedByteArray) -> String:
	var err := _parse(raw)
	var text: String = err.get(3, [PackedByteArray()])[0].get_string_from_utf8()
	if text.is_empty():
		text = err.get(2, [PackedByteArray()])[0].get_string_from_utf8()
	return text if not text.is_empty() else "erreur inconnue"

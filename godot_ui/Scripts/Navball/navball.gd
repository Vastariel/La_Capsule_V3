extends Control
## Navball façon KSP, alimentée par la télémétrie du bridge Python
## (heading / pitch / roll reçus via WebSocket, voir main.gd → set_attitude).
##
## keyboard_fallback = true permet de tester la scène seule, sans KSP :
##   Flèches gauche/droite : cap (heading)
##   Flèches haut/bas      : tangage (pitch)
##   Q / E                 : roulis (roll)
##   Shift                 : mouvement lent (précision)
##   R                     : remise à zéro

const SPEED := 60.0        # degrés par seconde
const SLOW_FACTOR := 0.15
const ROLL_SIGN := 1.0     # mettre -1.0 si le roulis kRPC est inversé par rapport à KSP

## Désactivé par défaut : les flèches pilotent déjà le menu de la capsule.
@export var keyboard_fallback := false
## Lissage entre deux échantillons de télémétrie (20 Hz) : plus grand = plus
## réactif, plus petit = plus doux. 0 = pas de lissage.
@export var smoothing := 15.0

var heading := 0.0   # 0..360, 0 = Nord, sens horaire vu de dessus
var pitch := 0.0     # -90..90, positif = nez vers le haut
var roll := 0.0      # -180..180, positif = aile droite vers le bas
var has_attitude := false
# Direction prograde (repère monde : Nord = -Z, Est = +X, Haut = +Y), ou null.
var _prograde_dir: Variant = null

# Le rendu 3D de la boule ne se fait que quand son orientation change
# (UPDATE_ONCE) : une navball immobile ne coûte rien au GPU.
var _current := Quaternion.IDENTITY
var _dirty := true

@onready var ball: MeshInstance3D = $BallView/SubViewport/Ball
@onready var viewport: SubViewport = $BallView/SubViewport
@onready var overlay: Control = $Overlay


func _notification(what: int) -> void:
	if what == NOTIFICATION_RESIZED:
		_dirty = true


func _process(delta: float) -> void:
	if keyboard_fallback and not has_attitude:
		_process_keyboard(delta)
	_update_ball(delta)
	_update_markers()


func set_attitude(h: float, p: float, r: float) -> void:
	has_attitude = true
	heading = fposmod(h, 360.0)
	pitch = clampf(p, -90.0, 90.0)
	roll = wrapf(r * ROLL_SIGN, -180.0, 180.0)


## Direction du vecteur vitesse (cap / tangage en degrés). null = masquer.
func set_prograde(data: Variant) -> void:
	if typeof(data) != TYPE_DICTIONARY:
		_prograde_dir = null
		return
	var h := deg_to_rad(float(data.get("heading", 0.0)))
	var p := deg_to_rad(float(data.get("pitch", 0.0)))
	_prograde_dir = Vector3(cos(p) * sin(h), sin(p), -cos(p) * cos(h))


func _process_keyboard(delta: float) -> void:
	var speed := SPEED * (SLOW_FACTOR if Input.is_key_pressed(KEY_SHIFT) else 1.0)

	heading += Input.get_axis("ui_left", "ui_right") * speed * delta
	pitch += Input.get_axis("ui_down", "ui_up") * speed * delta
	var r := 0.0
	if Input.is_physical_key_pressed(KEY_E):
		r += 1.0
	if Input.is_physical_key_pressed(KEY_Q):
		r -= 1.0
	roll += r * speed * delta

	if Input.is_physical_key_pressed(KEY_R):
		heading = 0.0
		pitch = 0.0
		roll = 0.0

	heading = fposmod(heading, 360.0)
	pitch = clampf(pitch, -90.0, 90.0)
	roll = wrapf(roll, -180.0, 180.0)


func _update_ball(delta: float) -> void:
	# Orientation du vaisseau dans le repère monde (Nord = -Z, Est = +X, Haut = +Y).
	# Ordre : cap, puis tangage, puis roulis (axes locaux).
	var ship := Basis(Vector3.UP, -deg_to_rad(heading)) \
		* Basis(Vector3.RIGHT, deg_to_rad(pitch)) \
		* Basis(Vector3.BACK, -deg_to_rad(roll))

	# Le maillage est déjà stocké "en miroir" (z inversé) pour que la boule soit
	# vue de l'extérieur avec la texture dans le bon sens. On applique donc la
	# rotation inverse du vaisseau, conjuguée par ce miroir.
	var mirror := Basis.from_scale(Vector3(1, 1, -1))
	var target := (mirror * ship.inverse() * mirror).get_rotation_quaternion()

	if smoothing > 0.0:
		var next := _current.slerp(target, 1.0 - exp(-smoothing * delta))
		# Écart résiduel négligeable : on se cale sur la cible pour arrêter de rendre.
		if next.angle_to(target) < 0.0005:
			next = target
		_set_orientation(next)
	else:
		_set_orientation(target)

	if _dirty:
		_dirty = false
		viewport.render_target_update_mode = SubViewport.UPDATE_ONCE


func _set_orientation(q: Quaternion) -> void:
	if q.is_equal_approx(_current):
		return
	_current = q
	ball.quaternion = q
	_dirty = true


# Position écran d'une direction du ciel sur la boule, telle que rendue :
# sommet du maillage = miroir(direction), puis rotation courante de la boule.
# Renvoie Vector3(x, y, profondeur) en unités de rayon (x à droite, y en bas) ;
# profondeur > 0 = face visible.
func _project(dir: Vector3) -> Vector3:
	var r := Basis(_current) * Vector3(dir.x, dir.y, -dir.z)
	return Vector3(r.x, -r.y, r.z)


func _update_markers() -> void:
	if _prograde_dir == null:
		overlay.set_markers(null, null)
	else:
		overlay.set_markers(_project(_prograde_dir), _project(-_prograde_dir))

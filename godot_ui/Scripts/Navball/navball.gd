extends Control
## Navball façon KSP.
## Si un serveur kRPC tourne dans KSP (voir le nœud KRPC), la navball suit
## l'attitude du vaisseau actif. Sinon, contrôles clavier :
##   Flèches gauche/droite : cap (heading)
##   Flèches haut/bas      : tangage (pitch)
##   Q / E                 : roulis (roll)
##   Shift                 : mouvement lent (précision)
##   R                     : remise à zéro

const SPEED := 60.0        # degrés par seconde
const SLOW_FACTOR := 0.15
const ROLL_SIGN := 1.0     # mettre -1.0 si le roulis kRPC est inversé par rapport à KSP

var heading := 0.0   # 0..360, 0 = Nord, sens horaire vu de dessus
var pitch := 0.0     # -90..90, positif = nez vers le haut
var roll := 0.0      # -180..180, positif = aile droite vers le bas

@onready var ball: MeshInstance3D = $BallView/SubViewport/Ball
@onready var info: Label = $Info
@onready var krpc: Node = $KRPC


func _process(delta: float) -> void:
	if not krpc.has_attitude:
		_process_keyboard(delta)
	_update_ball()


func _on_krpc_attitude(h: float, p: float, r: float) -> void:
	heading = fposmod(h, 360.0)
	pitch = clampf(p, -90.0, 90.0)
	roll = wrapf(r * ROLL_SIGN, -180.0, 180.0)


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


func _update_ball() -> void:
	# Orientation du vaisseau dans le repère monde (Nord = -Z, Est = +X, Haut = +Y).
	# Ordre : cap, puis tangage, puis roulis (axes locaux).
	var ship := Basis(Vector3.UP, -deg_to_rad(heading)) \
		* Basis(Vector3.RIGHT, deg_to_rad(pitch)) \
		* Basis(Vector3.BACK, -deg_to_rad(roll))

	# Le maillage est déjà stocké "en miroir" (z inversé) pour que la boule soit
	# vue de l'extérieur avec la texture dans le bon sens. On applique donc la
	# rotation inverse du vaisseau, conjuguée par ce miroir.
	var mirror := Basis.from_scale(Vector3(1, 1, -1))
	ball.basis = mirror * ship.inverse() * mirror

	info.text = "Cap      : %6.1f°\nTangage  : %6.1f°\nRoulis   : %6.1f°\n\n" % [heading, pitch, roll] \
		+ krpc.status + "\n\n" \
		+ ("Source : KSP (kRPC)" if krpc.has_attitude \
			else "Source : clavier\n←/→ : cap\n↑/↓ : tangage\nQ/E : roulis\nShift : précision\nR : reset")

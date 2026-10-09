extends Control
## Overlay 2D de la navball : anneau extérieur + symbole fixe du vaisseau.
## Dessiné à l'échelle de la taille du nœud (référence : 500 px).

## Doit correspondre à la taille de la caméra orthogonale (boule de rayon 1).
@export var cam_size := 2.1
## Couleur des marqueurs prograde / rétrograde (vert-jaune façon KSP).
@export var marker_color := Color(0.85, 0.95, 0.1)

# Positions projetées (x, y en rayons de boule, z = profondeur) ou null.
var _prograde: Variant = null
var _retrograde: Variant = null


func set_markers(prograde: Variant, retrograde: Variant) -> void:
	if prograde == _prograde and retrograde == _retrograde:
		return
	_prograde = prograde
	_retrograde = retrograde
	queue_redraw()


func _notification(what: int) -> void:
	if what == NOTIFICATION_RESIZED:
		queue_redraw()


func _draw() -> void:
	var c := size / 2.0
	var k := minf(size.x, size.y) / 500.0
	# 1 unité 3D = size.x / cam_size pixels, et la boule a un rayon de 1
	var ring_r := minf(size.x, size.y) / cam_size
	# Anneau extérieur
	draw_arc(c, ring_r + 3.0 * k, 0.0, TAU, 128, Color(0.75, 0.75, 0.78), maxf(6.0 * k, 1.5), true)
	draw_arc(c, ring_r + 8.0 * k, 0.0, TAU, 128, Color(0.25, 0.26, 0.3), maxf(4.0 * k, 1.0), true)

	# Marqueurs de vitesse, sous le symbole du vaisseau
	_draw_marker(_prograde, false, c, ring_r)
	_draw_marker(_retrograde, true, c, ring_r)

	# Symbole fixe du vaisseau (orange)
	var col := Color(1.0, 0.65, 0.05)
	var shadow := Color(0, 0, 0, 0.7)
	for pass_i in range(2):
		var color := col if pass_i == 1 else shadow
		var w := maxf((4.0 if pass_i == 1 else 7.0) * k, 1.5 if pass_i == 1 else 2.5)
		draw_arc(c, 9.0 * k, 0.0, TAU, 32, color, w, true)
		draw_line(c + Vector2(-70, 0) * k, c + Vector2(-20, 0) * k, color, w, true)
		draw_line(c + Vector2(20, 0) * k, c + Vector2(70, 0) * k, color, w, true)
		draw_line(c + Vector2(-20, 0) * k, c + Vector2(-20, 12) * k, color, w, true)
		draw_line(c + Vector2(20, 0) * k, c + Vector2(20, 12) * k, color, w, true)
		draw_line(c + Vector2(0, -9) * k, c + Vector2(0, -22) * k, color, w, true)



# Prograde : cercle + point central + 3 branches (haut, gauche, droite).
# Rétrograde : cercle barré d'une croix + 3 branches (haut, bas-gauche, bas-droite).
# Masqué sur la face cachée, estompé à l'approche du bord.
func _draw_marker(m: Variant, retro: bool, c: Vector2, ring_r: float) -> void:
	if m == null or m.z <= 0.0:
		return
	var col := marker_color
	col.a = clampf(m.z * 4.0, 0.0, 1.0)
	var shadow := Color(0, 0, 0, 0.6 * col.a)
	var p := c + Vector2(m.x, m.y) * ring_r
	var r := maxf(ring_r * 0.13, 6.0)
	var tick := r * 0.8
	var dirs := [Vector2.UP, Vector2(-1, 1).normalized(), Vector2(1, 1).normalized()] if retro \
		else [Vector2.UP, Vector2.LEFT, Vector2.RIGHT]
	for pass_i in range(2):
		var k := col if pass_i == 1 else shadow
		var w := maxf(r * 0.22, 1.5) + (0.0 if pass_i == 1 else 1.5)
		draw_arc(p, r, 0.0, TAU, 24, k, w, true)
		for d in dirs:
			draw_line(p + d * r, p + d * (r + tick), k, w, true)
		if retro:
			var x := r * 0.6
			draw_line(p + Vector2(-x, -x), p + Vector2(x, x), k, w, true)
			draw_line(p + Vector2(-x, x), p + Vector2(x, -x), k, w, true)
		else:
			draw_circle(p, w * 0.8, k)

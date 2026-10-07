extends Control
## Overlay 2D de la navball : anneau extérieur + symbole fixe du vaisseau.
## Dessiné à l'échelle de la taille du nœud (référence : 500 px).

## Doit correspondre à la taille de la caméra orthogonale (boule de rayon 1).
@export var cam_size := 2.1


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

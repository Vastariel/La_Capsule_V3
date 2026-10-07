extends Control
## Overlay 2D de la navball : anneau extérieur + symbole fixe du vaisseau.

## Doit correspondre à la taille de la caméra orthogonale (boule de rayon 1).
@export var cam_size := 2.1


func _draw() -> void:
	var c := size / 2.0
	# 1 unité 3D = size.x / cam_size pixels, et la boule a un rayon de 1
	var ring_r := size.x / cam_size
	# Anneau extérieur
	draw_arc(c, ring_r + 3.0, 0.0, TAU, 128, Color(0.75, 0.75, 0.78), 6.0, true)
	draw_arc(c, ring_r + 8.0, 0.0, TAU, 128, Color(0.25, 0.26, 0.3), 4.0, true)

	# Symbole fixe du vaisseau (orange)
	var col := Color(1.0, 0.65, 0.05)
	var shadow := Color(0, 0, 0, 0.7)
	for pass_i in range(2):
		var k := col if pass_i == 1 else shadow
		var w := 4.0 if pass_i == 1 else 7.0
		draw_arc(c, 9.0, 0.0, TAU, 32, k, w, true)
		draw_line(c + Vector2(-70, 0), c + Vector2(-20, 0), k, w, true)
		draw_line(c + Vector2(20, 0), c + Vector2(70, 0), k, w, true)
		draw_line(c + Vector2(-20, 0), c + Vector2(-20, 12), k, w, true)
		draw_line(c + Vector2(20, 0), c + Vector2(20, 12), k, w, true)
		draw_line(c + Vector2(0, -9), c + Vector2(0, -22), k, w, true)

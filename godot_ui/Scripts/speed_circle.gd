extends Control

const AMBER      = Color(0.941176, 0.690196, 0.282353, 1.0)
const AMBER_RING = Color(0.941176, 0.690196, 0.282353, 0.42)
const AMBER_TICK = Color(0.941176, 0.690196, 0.282353, 0.55)
const TRACK      = Color(1.0, 1.0, 1.0, 0.08)
const CYAN       = Color(0.384314, 0.784314, 0.878431, 1.0)
const BG_COLOR   = Color(0.023529, 0.035294, 0.058824, 1.0)
const SPEED_MAX  = 3200.0

var current_speed: float = 0.0

func set_speed(v: float) -> void:
	current_speed = maxf(0.0, v)
	queue_redraw()

func _draw() -> void:
	var cx := size.x / 2.0
	var cy := size.y / 2.0
	var r  := minf(cx, cy) * 0.96
	var r_inner := r * (330.0 / 464.0)

	# Outer track
	draw_arc(Vector2(cx, cy), r, 0.0, TAU, 128, TRACK, 3.5, true)

	# Speed progress arc — clockwise from 12 o'clock (-PI/2)
	var pct := clampf(current_speed / SPEED_MAX, 0.0, 1.0)
	if pct > 0.001:
		var end_a := -PI / 2.0 + TAU * pct
		draw_arc(Vector2(cx, cy), r, -PI / 2.0, end_a, maxi(8, int(128 * pct)), AMBER, 8.0, true)

	# Inner ring
	draw_arc(Vector2(cx, cy), r_inner, 0.0, TAU, 128, AMBER_RING, 3.5, true)

	# 12 tick marks every 30°
	for i in 12:
		var a := (i * 30.0 - 90.0) * PI / 180.0
		var p1 := Vector2(cx + cos(a) * r, cy + sin(a) * r)
		var p2 := Vector2(cx + cos(a) * (r - 18.0), cy + sin(a) * (r - 18.0))
		draw_line(p1, p2, AMBER_TICK, 3.5, true)

	# Leading-edge marker (cyan circle on ring at current speed angle)
	var ma := -PI / 2.0 + TAU * clampf(current_speed / SPEED_MAX, 0.0, 1.0)
	var mp := Vector2(cx + cos(ma) * r, cy + sin(ma) * r)
	draw_circle(mp, 18.0, BG_COLOR)
	draw_arc(mp, 18.0, 0.0, TAU, 32, CYAN, 4.0, true)
	draw_circle(mp, 7.0, CYAN)

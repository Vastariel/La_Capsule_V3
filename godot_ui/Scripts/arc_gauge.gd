extends Control

# Semicircle arc gauge opening upward.
# Circle center is placed near the bottom of the control so the arc
# sweeps upward into the visible area (like the JSX startA=180→360).

const AMBER       = Color(0.941176, 0.690196, 0.282353, 1.0)
const AMBER_TRACK = Color(0.941176, 0.690196, 0.282353, 0.10)
const RED         = Color(0.909804, 0.333333, 0.184314, 1.0)

var current_value: float = 0.0
var max_value: float = 6.0
var arc_color: Color = AMBER

func set_arc_value(v: float, color: Color = AMBER) -> void:
	current_value = clampf(v, 0.0, max_value)
	arc_color = color
	queue_redraw()

func _draw() -> void:
	var w   := size.x
	var h   := size.y
	var cx  := w / 2.0
	# Center near bottom so the arc opens upward into the control area
	var cy  := h * 0.94
	var r   := minf(w * 0.42, h * 0.80)
	var thk := maxf(r * 0.14, 14.0)

	# Track arc: PI (left) → TAU=2π (right) going through 3π/2 (top in screen)
	# This sweeps the upper semicircle — opening faces DOWN, arc bulges UP ✓
	draw_arc(Vector2(cx, cy), r, PI, TAU, 64, AMBER_TRACK, thk, true)

	# Value fill
	var pct := clampf(current_value / max_value, 0.0, 1.0)
	if pct > 0.001:
		draw_arc(Vector2(cx, cy), r, PI, PI + PI * pct, maxi(4, int(64 * pct)), arc_color, thk, true)

	# Tick marks (11 marks across 180°)
	for i in 11:
		var a     := PI + PI * float(i) / 10.0
		var inner := r - thk * 0.7
		var outer := r + thk * 0.35
		var major := (i % 5 == 0)
		var p1    := Vector2(cx + cos(a) * inner, cy + sin(a) * inner)
		var p2    := Vector2(cx + cos(a) * outer,  cy + sin(a) * outer)
		draw_line(p1, p2,
			arc_color if major else Color(1.0, 1.0, 1.0, 0.4),
			3.0 if major else 1.5, true)

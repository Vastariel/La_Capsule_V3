extends PanelContainer

@export var blink_interval := 0.6

var _timer := 0.0
var _lit := true
var _style: StyleBoxFlat

func _ready() -> void:
	_style = get_theme_stylebox("panel").duplicate()
	add_theme_stylebox_override("panel", _style)

func _process(delta: float) -> void:
	_timer += delta
	if _timer >= blink_interval:
		_timer = fmod(_timer, blink_interval)
		_lit = !_lit
		_style.bg_color.a = 1.0 if _lit else 0.0

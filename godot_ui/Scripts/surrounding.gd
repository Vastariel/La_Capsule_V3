extends TextureRect

@export var rotation_speed := 10 # degrés / seconde

func _ready():
	# centre le pivot au milieu de la texture
	pivot_offset = size / 2
	# active la rotation autour du pivot
	set_anchors_preset(Control.PRESET_CENTER)

func _process(delta):
	rotation_degrees += rotation_speed * delta

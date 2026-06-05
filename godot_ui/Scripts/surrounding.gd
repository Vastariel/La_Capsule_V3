extends TextureRect

@export var rotation_speed := 10 # degrés / seconde

func _ready():
	pivot_offset = size / 2

func _notification(what):
	if what == NOTIFICATION_RESIZED:
		pivot_offset = size / 2

func _process(delta):
	rotation_degrees += rotation_speed * delta

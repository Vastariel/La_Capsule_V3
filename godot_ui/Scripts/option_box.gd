extends Control

signal activated
signal deactivated

@onready var background = $Background
@onready var label = $Label

var is_selected: bool = false
var is_active: bool = false

func set_selected(selected: bool):
	is_selected = selected
	_update_visuals()

func toggle_active():
	is_active = !is_active
	_update_visuals()
	if is_active:
		activated.emit()
	else:
		deactivated.emit()

func reset_active():
	if is_active:
		is_active = false
		deactivated.emit()
	_update_visuals()

func _update_visuals():
	if is_active:
		background.color = Color(1, 1, 1, 1)   # Boîte blanche opaque
		label.add_theme_color_override("font_color", Color.html("#0a0f1c"))
	elif is_selected:
		background.color = Color(1, 1, 1, 0.3) # Boîte blanche transparente
		label.add_theme_color_override("font_color", Color.html("#0a0f1c"))
	else:
		background.color = Color(1, 1, 1, 0)   # Invisible
		label.add_theme_color_override("font_color", Color.WHITE) # Texte blanc par défaut

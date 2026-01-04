extends VBoxContainer

var current_index := 0
var options := []
var option_names := ["Pause", "Conseils", "En savoir plus", "Relancer la mission"]

func _ready():
	options = get_children()

	for i in range(options.size()):
		options[i].label.text = option_names[i]
		options[i].activated.connect(_on_option_activated.bind(i))
		options[i].deactivated.connect(_on_option_deactivated.bind(i))

	_update_selection()

func _unhandled_input(event):
	if event.is_action_pressed("ui_down"):
		current_index = (current_index + 1) % options.size()
		_reset_all_active()
		_update_selection()
	elif event.is_action_pressed("ui_up"):
		current_index = (current_index - 1 + options.size()) % options.size()
		_reset_all_active()
		_update_selection()
	elif event.is_action_pressed("ui_accept"):
		options[current_index].toggle_active()

func _update_selection():
	for i in range(options.size()):
		options[i].set_selected(i == current_index)

func _reset_all_active():
	for opt in options:
		opt.reset_active()

# 🚀 Commandes différentes selon activation/désactivation
func _on_option_activated(index):
	match index:
		0: print("Pause activée")
		1: print("Conseils affichés")
		2: print("Infos supplémentaires affichées")
		3: print("Mission relancée")

func _on_option_deactivated(index):
	match index:
		0: print("Pause quittée")
		1: print("Conseils fermés")
		2: print("Infos supplémentaires fermées")
		3: print("Mission annulée")

extends Window

@onready var ip_input: LineEdit = $VBoxContainer/LineEdit
@onready var connect_button: Button = $VBoxContainer/Button

@export var default_ip := "192.168.1.21"

signal connect_requested(ip: String)

func _ready():
	ip_input.text = default_ip
	title = "Connexion au serveur"
	connect_button.text = "Connect →"
	connect_button.pressed.connect(_on_connect_pressed)

func _on_connect_pressed():
	emit_signal("connect_requested", ip_input.text.strip_edges())
	# Do not hide here; let the main controller hide it on successful connection

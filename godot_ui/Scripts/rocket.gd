extends Control
# Jauges de carburant par étage, pilotées par le tableau "stages" du bridge.
# Le bridge envoie (du plus récent au plus ancien) : stages[0..3].
# Mapping vers la fusée (bas → haut) : booster, etage1, etage2, etage3, coiffe.

@onready var coiffe_gauge: ColorRect = $Coiffe_2/ColorRect
@onready var etage3_gauge: ColorRect = $Etage3_2/ColorRect2
@onready var etage2_gauge: ColorRect = $Etage2_2/ColorRect3
@onready var etage1_gauge: ColorRect = $Etage1_2/ColorRect4
@onready var booster1_gauge: ColorRect = $Booster_2/ColorRect5
@onready var booster2_gauge: ColorRect = $Booster2_2/ColorRect6

const DETACHED_MOD := Color(0.3, 0.3, 0.3, 1.0)
const ATTACHED_MOD := Color(1.0, 1.0, 1.0, 1.0)


func _ready() -> void:
	# Affichage initial : tout plein, tout attaché.
	for g in [coiffe_gauge, etage3_gauge, etage2_gauge, etage1_gauge, booster1_gauge, booster2_gauge]:
		_set_gauge(g, 100.0, true)


func update_from_stages(stages: Array) -> void:
	# stages[0] = étage courant (le plus bas encore attaché), stages[3] = plus ancien.
	# Mapping visuel, du bas vers le haut :
	#   stages[0] → etage1 + boosters (stage actif au décollage)
	#   stages[1] → etage2
	#   stages[2] → etage3
	#   stages[3] → coiffe
	var s0 = _stage_at(stages, 0)
	var s1 = _stage_at(stages, 1)
	var s2 = _stage_at(stages, 2)
	var s3 = _stage_at(stages, 3)

	_apply(etage1_gauge, s0)
	_apply(booster1_gauge, s0)
	_apply(booster2_gauge, s0)
	_apply(etage2_gauge, s1)
	_apply(etage3_gauge, s2)
	_apply(coiffe_gauge, s3)


func _stage_at(stages: Array, idx: int) -> Dictionary:
	if idx < stages.size() and stages[idx] is Dictionary:
		return stages[idx]
	return {"fuel_percent": 0.0, "attached": false}


func _apply(gauge: ColorRect, stage: Dictionary) -> void:
	var pct := float(stage.get("fuel_percent", 0.0))
	var attached := bool(stage.get("attached", false))
	_set_gauge(gauge, pct, attached)


func _set_gauge(gauge: ColorRect, fuel_percent: float, attached: bool) -> void:
	if gauge == null:
		return
	fuel_percent = clamp(fuel_percent, 0.0, 100.0)
	gauge.anchor_top = 1.0 - (fuel_percent / 100.0)
	gauge.modulate = ATTACHED_MOD if attached else DETACHED_MOD

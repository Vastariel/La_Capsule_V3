extends Control
# Rocket telemetry visualization script
# Displays fuel levels for each stage and boosters with dynamic gauges

# Stage color rects (the clipping masks that show fuel level)
@onready var coiffe_gauge = $Coiffe_2/ColorRect
@onready var etage3_gauge = $Etage3_2/ColorRect2
@onready var etage2_gauge = $Etage2_2/ColorRect3
@onready var etage1_gauge = $Etage1_2/ColorRect4
@onready var booster1_gauge = $Booster_2/ColorRect5
@onready var booster2_gauge = $Booster2_2/ColorRect6

# Stage fuel tracking
var stage_data = {
	"coiffe": {"fuel_percent": 0.0, "is_detached": false},
	"etage3": {"fuel_percent": 0.0, "is_detached": false},
	"etage2": {"fuel_percent": 0.0, "is_detached": false},
	"etage1": {"fuel_percent": 100.0, "is_detached": false},
	"booster": {"fuel_percent": 100.0, "is_detached": false}
}

func _ready():
	# Initialize all gauges to 100%
	update_stage_fuel("etage1", 100.0)
	update_stage_fuel("etage2", 0.0)
	update_stage_fuel("etage3", 0.0)
	update_stage_fuel("booster", 100.0)


func update_stage_fuel(stage_name: String, fuel_percent: float, is_detached: bool = false) -> void:
	"""
	Update fuel level for a specific stage
	fuel_percent: 0-100 representing tank fill level
	is_detached: whether the stage has been decoupled
	"""
	if stage_name not in stage_data:
		push_error("Unknown stage: " + stage_name)
		return
	
	# Clamp fuel to 0-100%
	fuel_percent = clamp(fuel_percent, 0, 100)
	
	# Update tracking data
	stage_data[stage_name]["fuel_percent"] = fuel_percent
	stage_data[stage_name]["is_detached"] = is_detached
	
	# Get the corresponding gauge and update it
	var gauge = _get_gauge_for_stage(stage_name)
	if gauge:
		_update_gauge_visual(gauge, fuel_percent, is_detached)


func _get_gauge_for_stage(stage_name: String) -> ColorRect:
	"""Return the ColorRect gauge node for the given stage"""
	match stage_name:
		"coiffe":
			return coiffe_gauge
		"etage3":
			return etage3_gauge
		"etage2":
			return etage2_gauge
		"etage1":
			return etage1_gauge
		"booster":
			# Return booster1 as primary; both update together
			return booster1_gauge
		_:
			return null


func _update_gauge_visual(gauge: ColorRect, fuel_percent: float, is_detached: bool) -> void:
	"""
	Visually update the gauge ColorRect
	- Adjust anchor_top to show fuel level (0.0 = full, 1.0 = empty)
	- Darken the gauge if stage is detached
	"""
	# Adjust height based on fuel percentage
	# anchor_top moves from bottom (1.0) to top (0.0) as fuel increases
	gauge.anchor_top = 1.0 - (fuel_percent / 100.0)
	
	# If detached, darken the gauge
	if is_detached:
		gauge.modulate = Color(0.3, 0.3, 0.3, 1.0)  # Dimmed
	else:
		gauge.modulate = Color(1.0, 1.0, 1.0, 1.0)  # Normal


func update_from_telemetry(telemetry_data: Dictionary) -> void:
	"""
	Update all stage fuel levels based on telemetry data from server
	Expected keys: liquid_fuel, oxidizer, solid_fuel
	"""
	# Extract fuel values from telemetry
	var liquid_fuel = float(telemetry_data.get("liquid_fuel", 0))
	var oxidizer = float(telemetry_data.get("oxidizer", 0))
	var solid_fuel = float(telemetry_data.get("solid_fuel", 0))
	
	# Calculate fuel percentages (assuming max capacities - adjust as needed)
	# These values should match your KSP rocket configuration
	var max_liquid_fuel = 2880.0  # Adjust to your rocket's max capacity
	var max_oxidizer = 3520.0     # Adjust to your rocket's max capacity
	var max_solid_fuel = 7500.0   # Adjust to your rocket's max capacity
	
	# Calculate percentages
	var liquid_percent = (liquid_fuel / max_liquid_fuel) * 100.0 if max_liquid_fuel > 0 else 0
	var oxidizer_percent = (oxidizer / max_oxidizer) * 100.0 if max_oxidizer > 0 else 0
	var solid_percent = (solid_fuel / max_solid_fuel) * 100.0 if max_solid_fuel > 0 else 0
	
	# Distribute fuel across stages based on real mission profile
	# This is a simplified distribution - adjust based on your actual rocket design
	
	# Stage 1: Main engines (liquid fuel + oxidizer) - active stage
	var stage1_fuel = min(liquid_percent, oxidizer_percent)
	update_stage_fuel("etage1", stage1_fuel, false)
	
	# Stage 2: Upper stage (uses some liquid fuel)
	var stage2_fuel = max(0, liquid_percent - 30.0)
	update_stage_fuel("etage2", stage2_fuel, false)
	
	# Stage 3: Final stage (minimal fuel)
	var stage3_fuel = max(0, liquid_percent - 60.0)
	update_stage_fuel("etage3", stage3_fuel, false)
	
	# Boosters: Use solid fuel
	update_stage_fuel("booster", solid_percent, false)


func get_stage_fuel_percent(stage_name: String) -> float:
	"""Get current fuel percentage for a stage"""
	if stage_name in stage_data:
		return stage_data[stage_name]["fuel_percent"]
	return 0.0


func is_stage_detached(stage_name: String) -> bool:
	"""Check if a stage has been detached"""
	if stage_name in stage_data:
		return stage_data[stage_name]["is_detached"]
	return false


func detach_stage(stage_name: String) -> void:
	"""Mark a stage as detached and update visuals"""
	if stage_name in stage_data:
		stage_data[stage_name]["is_detached"] = true
		var gauge = _get_gauge_for_stage(stage_name)
		if gauge:
			_update_gauge_visual(gauge, 0.0, true)  # Empty and darkened
		print("Stage %s detached" % stage_name)


func get_all_stages_status() -> Dictionary:
	"""Return complete status of all stages"""
	return stage_data.duplicate(true)

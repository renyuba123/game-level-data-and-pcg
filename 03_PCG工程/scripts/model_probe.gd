extends SceneTree

const Model = preload("res://scripts/pcg_model.gd")

func _initialize() -> void:
	var source: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/source_profile.json"))
	var model = Model.new()
	var failures: Array = []
	var variants := {}
	for seed in range(1, 101):
		var level: Dictionary = model.generate_level(seed, source)
		if not level["validation"]["ok"]:
			failures.append({"seed": seed, "issues": level["validation"]["issues"]})
		var key := ""
		for room in level["rooms"]:
			key += str(room["polygon"])
		variants[key] = true
	var summary := {"failures": failures, "variant_count": variants.size(), "tested": 100}
	var first: Dictionary = model.generate_level(42, source)
	var repeated: Dictionary = model.generate_level(42, source)
	var first_signature := ""
	var repeated_signature := ""
	for room in first["rooms"]: first_signature += str(room["polygon"])
	for room in repeated["rooms"]: repeated_signature += str(room["polygon"])
	summary["same_seed_reproduced"] = first_signature == repeated_signature
	if not summary["same_seed_reproduced"]: failures.append({"seed": 42, "issues": ["not deterministic"]})
	var output = FileAccess.open("res://reports/model_001_100.json", FileAccess.WRITE)
	output.store_string(JSON.stringify(summary, "\t"))
	output.close()
	print(JSON.stringify(summary))
	quit(0 if failures.is_empty() else 1)

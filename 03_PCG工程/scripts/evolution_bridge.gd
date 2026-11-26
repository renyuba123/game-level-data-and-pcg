extends SceneTree
const Model = preload("res://scripts/pcg_model.gd")

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2:
		push_error("Expected input.json output.json")
		quit(2)
		return
	var requests = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var source = JSON.parse_string(FileAccess.get_file_as_string("res://data/source_profile.json"))
	if not requests is Array or not source is Dictionary:
		quit(2)
		return
	var model = Model.new()
	var results: Array = []
	for request in requests:
		var level: Dictionary = model.generate_level(int(request.get("seed", 42)), source, request.get("genes", {}))
		if level["validation"]["ok"]:
			level["walls_initial"] = model.wall_segments(level)
			var ids: Array = []
			for edge in level["edges"]: ids.append(edge["id"])
			level["walls_all_open"] = model.wall_segments(level, ids)
			level["wall_thickness_m"] = 0.18
		results.append(encode(level))
	var output := FileAccess.open(args[1], FileAccess.WRITE)
	if output == null:
		quit(3)
		return
	output.store_string(JSON.stringify(results))
	output.close()
	quit()

func encode(value: Variant) -> Variant:
	if value is Vector2: return [value.x, value.y]
	if value is Vector3: return [value.x, value.y, value.z]
	if value is Array or value is PackedVector2Array:
		var result: Array = []
		for item in value: result.append(encode(item))
		return result
	if value is Dictionary:
		var result := {}
		for key in value: result[key] = encode(value[key])
		return result
	return value

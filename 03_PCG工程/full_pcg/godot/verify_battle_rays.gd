extends SceneTree

const Decoder = preload("res://full_pcg/godot/layout_decoder.gd")


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var case_path := OS.get_environment("RATKING_BATTLE_RAYS")
	var spec = JSON.parse_string(FileAccess.get_file_as_string(case_path))
	if not spec is Dictionary:
		quit(2)
		return
	var level = Decoder.new()
	root.add_child(level)
	if not level.load_package(spec.package):
		quit(2)
		return
	var results: Array = []
	for state in ["initial", "all_open"]:
		if state == "all_open":
			for gate in level.data.gates:
				level.set_open(gate.id, true)
		for i in range(3):
			await physics_frame
		for probe in spec.probes:
			if probe.state != state:
				continue
			var start: Vector3 = level.point(probe.start, float(probe.height))
			var end: Vector3 = level.point(probe.end, float(probe.height))
			var ray := PhysicsRayQueryParameters3D.create(start, end, 1 | 64)
			var hit := level.get_world_3d().direct_space_state.intersect_ray(ray)
			results.append({"id": probe.id, "clear": hit.is_empty()})
	var out := FileAccess.open(spec.output, FileAccess.WRITE)
	if out == null:
		quit(2)
		return
	out.store_string(JSON.stringify({"package_hash": level.data.package_hash, "results": results}, "  "))
	out.close()
	quit(0)

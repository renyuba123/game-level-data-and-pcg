extends SceneTree

const AutoLevel = preload("res://full_pcg/godot/auto_combat_level.gd")


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var spec = JSON.parse_string(FileAccess.get_file_as_string(OS.get_environment("RATKING_COMBAT_BATCH")))
	if not spec is Dictionary or spec.get("schema") != "combat-batch/godot-1":
		push_error("Invalid combat batch")
		quit(2)
		return
	# Use the project's game clock. Python never implements a second physics clock.
	var hz := Engine.physics_ticks_per_second
	var delta := 1.0 / hz
	for case in spec.cases:
		var level = AutoLevel.new()
		level.protocol_override = spec.combat
		level.package_path = spec.package
		level.layout_scale = float(spec.get("layout_scale", 1.0))
		root.add_child(level)
		level.set_physics_process(false)
		if level.data.get("package_hash") != spec.package_hash:
			push_error("Wrong layout package")
			quit(2)
			return
		for rid in level.maps.values():
			NavigationServer3D.map_set_use_async_iterations(rid, false)
			NavigationServer3D.map_force_update(rid)
		level.setup(case)
		level.score_telemetry = true
		await physics_frame
		await physics_frame
		var frames: Array = []
		var inputs: Array = []
		var limit := ceili(float(level.combat.simulation.time_limit_s) * hz) + 2
		for step in range(limit):
			await physics_frame
			level.command = level.control(delta)
			level._physics_process(delta)
			frames.append(level.sample())
			if spec.capture_controls:
				inputs.append(level.command)
			if level.result != "":
				break
		if level.result == "":
			push_error("Combat did not terminate within its configured time")
			quit(2)
			return
		var out := FileAccess.open(case.output, FileAccess.WRITE)
		if out == null:
			push_error("Cannot write combat episode")
			quit(2)
			return
		var episode := {"schema":"combat-batch/godot-1","case_id":case.id,
			"package_hash":level.data.package_hash,"layout_hash":level.data.layout.layout_hash,
			"physics_hz":hz,"layout_scale":level.layout_scale,"result":level.result,"duration_s":frames.size()*delta,"phase":level.phase,
			"controls_version":"direction-aim/2","combat":level.combat,"events":level.event_log,"frames":frames,"inputs":inputs,"telemetry":"godot-score/1","ability":case.ability}
		if not level.tactical_decisions.is_empty():
			episode["policy_decisions"] = level.tactical_decisions
		out.store_string(JSON.stringify(episode, "", true, true))
		out.close()
		level.free()
	quit(0)

extends SceneTree

const ReplayLevel = preload("res://full_pcg/godot/replay_combat_level.gd")


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var spec = JSON.parse_string(FileAccess.get_file_as_string(OS.get_environment("RATKING_REPLAY_CASE")))
	if not spec is Dictionary or spec.get("schema") != "combat-replay/1":
		push_error("A combat-replay/1 case is required")
		quit(2)
		return
	Engine.physics_ticks_per_second = roundi(1.0 / float(spec.dt))
	var delta := 1.0 / Engine.physics_ticks_per_second
	var level = ReplayLevel.new()
	level.protocol_override = spec.get("combat",{})
	level.package_path = spec.package
	level.layout_scale = float(spec.get("layout_scale", 1.0))
	root.add_child(level)
	level.set_physics_process(false)
	if level.data.get("package_hash") != spec.package_hash:
		push_error("Wrong replay layout package")
		quit(2)
		return
	for rid in level.maps.values():
		NavigationServer3D.map_set_use_async_iterations(rid, false)
		NavigationServer3D.map_force_update(rid)
	level.native_boss = spec.native_boss
	level.score_telemetry = spec.get("score_telemetry",false)
	level.reaction_scale = spec.get("reaction_scale",1.0)
	var actor_collision: bool = spec.get("actor_collision", true)
	if not actor_collision:
		# Isolate player/Boss contact while retaining all wall and portal shapes.
		level.player_body.set_collision_mask_value(4, false)
		level.boss_body.set_collision_mask_value(5, false)
	level.player_body.position = level.point(spec.start_player, level.player_body.position.y)
	level.boss_body.position = level.point(spec.start_boss, level.boss_body.position.y)
	# A tick already scheduled before changing Engine's rate may still use 60 Hz.
	# Wait until the fixed physics rate applies before feeding the first command.
	await physics_frame
	await physics_frame
	var frames: Array = []
	for input in spec.inputs:
		await physics_frame
		level.command = input
		level._physics_process(delta)
		frames.append(level.sample())
		if level.result != "":
			break
	var out := FileAccess.open(spec.output, FileAccess.WRITE)
	if out == null:
		push_error("Cannot save replay")
		quit(2)
		return
	out.store_string(JSON.stringify({"package_hash": level.data.package_hash, "native_boss": level.native_boss,
		"result": level.result if level.result != "" else "INPUT_ENDED", "events": level.event_log,
		"frames": frames, "actor_collision": actor_collision, "physics_hz": Engine.physics_ticks_per_second}, "", true, true))
	out.close()
	quit(0)

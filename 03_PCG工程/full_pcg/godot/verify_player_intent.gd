extends SceneTree

const Manual = preload("res://full_pcg/godot/combat_level.gd")
const Automatic = preload("res://full_pcg/godot/auto_combat_level.gd")


func _initialize() -> void:
	call_deferred("_check")


func _trace(automatic: bool) -> Array:
	var level = Automatic.new() if automatic else Manual.new()
	level.package_path = OS.get_environment("RATKING_VERIFY_PACKAGE")
	root.add_child(level)
	level.set_physics_process(false)
	await physics_frame
	await physics_frame
	var samples: Array = []
	for tick in range(12):
		var aiming := tick >= 4 and tick < 8
		if automatic:
			level.command = {"move_direction":[0,1],"aim":aiming,"fire":aiming}
		else:
			var key := InputEventKey.new()
			key.keycode = KEY_S
			key.pressed = true
			Input.parse_input_event(key)
			var mouse := InputEventMouseButton.new()
			mouse.button_index = MOUSE_BUTTON_LEFT
			mouse.pressed = aiming
			Input.parse_input_event(mouse)
			Input.flush_buffered_events()
		await physics_frame
		var before: Vector3 = level.player_body.position
		level._player_move(1.0 / Engine.physics_ticks_per_second)
		var distance: float = level.player_body.position.z - before.z
		var speed := float(level.combat.player.aim_speed_mps if aiming else level.combat.player.speed_mps)
		samples.append([distance, speed / Engine.physics_ticks_per_second])
	level.free()
	await physics_frame
	return samples


func _check() -> void:
	var manual := await _trace(false)
	var automatic := await _trace(true)
	for i in range(manual.size()):
		if not is_equal_approx(manual[i][0],automatic[i][0]) or absf(manual[i][0]-manual[i][1]) > 0.00001:
			push_error("Movement mismatch at tick %d: %s / %s" % [i,manual[i],automatic[i]])
			quit(1)
			return
	print("PASS manual and automatic forward displacement at 60 Hz: ", manual)
	quit(0)

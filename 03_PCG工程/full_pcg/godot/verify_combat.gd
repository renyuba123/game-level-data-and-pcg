extends SceneTree

const CombatScene = preload("res://scenes/CombatFullPCG.tscn")


func _initialize() -> void:
	call_deferred("_run")


func _ray(from: Vector3, to: Vector3, mask: int, level: Node3D) -> Dictionary:
	var query := PhysicsRayQueryParameters3D.create(from, to)
	query.collision_mask = mask
	return level.get_world_3d().direct_space_state.intersect_ray(query)


func _run() -> void:
	var level = CombatScene.instantiate()
	if OS.has_environment("RATKING_VERIFY_PACKAGE"): level.package_path=OS.get_environment("RATKING_VERIFY_PACKAGE")
	get_root().add_child(level)
	for rid in level.maps.values():
		NavigationServer3D.map_set_use_async_iterations(rid,false)
		NavigationServer3D.map_force_update(rid)
	for frame in range(12): await physics_frame
	level.set_physics_process(false)
	var issues: Array[String] = []
	if level.data.is_empty(): issues.append("package_not_loaded")
	if level.data.layout.spawn.room != level.data.layout.boss.room:
		issues.append("not_same_room")
	if level.player_body.position.distance_to(level.boss_body.position) < 1.5:
		issues.append("opening_gap_too_small")
	var boss_origin: Vector3 = level.point(level.data.layout.boss.position, level.boss_body.position.y)
	if level.boss_body.position.distance_to(boss_origin) < 0.05:
		issues.append("boss_did_not_chase")
	var initial_hp: float = level.boss_hp
	level._fire_at(level.boss_body.position)
	if level.boss_hp >= initial_hp:
		issues.append("muzzle_ray_failed_to_hit_visible_boss")
	if level.loaded != 7:
		issues.append("shot_did_not_consume_ammo")
	var portal_checks := 0
	for gate in level.data.gates:
		if gate.kind != "through": continue
		var portal: Dictionary = {}
		for item in level.data.layout.portals:
			if item.id == gate.id: portal = item; break
		var c: Vector3 = level.point(portal.center, 1.2)
		var n := Vector3(float(portal.normal[0]), 0, float(portal.normal[1]))
		var from: Vector3 = c - n * 0.7
		var to: Vector3 = c + n * 0.7
		var before := _ray(from, to, 1 | 2, level)
		level.allow_squeeze(gate.id, true)
		var player_open := _ray(from, to, 1 | 2, level)
		var boss_blocked := _ray(from, to, 1 | 4, level)
		level.allow_squeeze(gate.id, false)
		level.set_open(gate.id, true)
		var all_open := _ray(from, to, 1 | 2 | 4, level)
		if before.is_empty() or not player_open.is_empty() or boss_blocked.is_empty() or not all_open.is_empty():
			issues.append("through_collision_state:" + gate.id)
		portal_checks += 1
		break
	if portal_checks == 0:
		issues.append("no_through_to_test")
	var break_checks := 0
	var old_boss_position: Vector3 = level.boss_body.position
	for gate in level.data.gates:
		if gate.kind != "break": continue
		var portal: Dictionary = {}
		for item in level.data.layout.portals:
			if item.id == gate.id: portal = item; break
		var c: Vector3 = level.point(portal.center, 1.2)
		var n := Vector3(float(portal.normal[0]), 0, float(portal.normal[1]))
		var before := _ray(c - n * .7, c + n * .7, 1 | 2 | 4, level)
		# Begin this isolated smash probe idle; the preceding chase can already
		# have started a different gate timer.
		level.smash_id = ""
		level.smash_s = 0
		var boss_gate_link: NavigationLink3D = level.links["boss:" + gate.id]
		level.boss_body.position = Vector3(boss_gate_link.start_position.x,
			level.boss_body.position.y,boss_gate_link.start_position.z)
		level._boss_smash(.01)
		if level.smash_id != gate.id:
			issues.append("boss_did_not_start_smash:" + gate.id)
		level._boss_smash(2.0)
		await physics_frame
		var after := _ray(c - n * .7, c + n * .7, 1 | 2 | 4, level)
		if before.is_empty() or not after.is_empty() or not level.gates[gate.id].opened:
			issues.append("break_collision_state:" + gate.id)
		break_checks += 1
		break
	if break_checks == 0:
		issues.append("no_break_to_test")
	level.boss_body.position = old_boss_position
	var old_player_position: Vector3 = level.player_body.position
	var supply: Dictionary = level.data.layout.supplies[0]
	level.player_body.position = level.point(supply.position, level.player_body.position.y)
	var reserve_before: int = level.reserve
	if not level.collect_supply(supply.id) or level.collect_supply(supply.id):
		issues.append("supply_pickup_repeat_or_blocked")
	if level.reserve != reserve_before + int(level.combat.supplies.rounds_per_pack):
		issues.append("supply_budget_wrong")
	level.player_body.position = old_player_position
	level.loaded = 0
	level.reload_s = 0.01
	level._reload(0.02)
	if level.loaded != int(level.combat.weapon.magazine):
		issues.append("reload_failed")
	level._apply_boss_hit(1000.0)
	if level.phase != 2 or level.boss_hp != 500.0 or level.result != "":
		issues.append("first_phase_skipped_or_hp_not_clamped")
	if not is_instance_valid(level.stalker_body):
		issues.append("stalker_not_spawned_after_split")
	level._apply_boss_hit(500.0)
	if level.result != "":
		issues.append("same_tick_kill_was_allowed")
	level.tick += 1
	level.elapsed_s += 0.05
	level._apply_boss_hit(500.0)
	if level.result != "victory" or level.boss_hp != 0.0:
		issues.append("second_phase_kill_failed")
	var kinds: Array[String] = []
	for event in level.event_log: kinds.append(event.kind)
	if kinds.count("split") != 1 or kinds[-1] != "victory":
		issues.append("event_order_or_terminal_log")
	var record_path := ProjectSettings.globalize_path("user://combat_episode.json")
	var result := {"passed": issues.is_empty(), "issues": issues, "events": kinds,
		"boss_hp": level.boss_hp, "phase": level.phase, "episode_path": record_path}
	var output := OS.get_environment("RATKING_COMBAT_RESULT")
	if output.is_empty(): output="res://full_pcg_output/combat_godot/godot_combat_check.json"
	var file := FileAccess.open(output,FileAccess.WRITE)
	file.store_string(JSON.stringify(result, "  "))
	file.close()
	print(JSON.stringify({"passed": issues.is_empty(), "issues": issues, "events": kinds}))
	level.queue_free()
	quit(0 if issues.is_empty() else 1)

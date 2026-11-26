extends SceneTree

const MainScene = preload("res://scenes/Main.tscn")


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var main = MainScene.instantiate()
	main.boss_speed = 0.0
	main.player_speed = 6.25
	main.player_aim_speed = 2.75
	main.boss_hp = 1200.0
	main.boss_attack_warning = 1.1
	main.stalker_speed = 6.4
	main.stalker_damage = 17.0
	main.weapon_damage = 55.0
	main.player_squeeze_seconds = 0.8
	main.boss_through_seconds = 2.25
	main.boss_break_seconds = 2.75
	main.map_size = 1.5
	main.through_interaction_range = 1.75
	main.supply_pickup_seconds = 0.35
	main.supply_pickup_range = 1.4
	var protocol: Dictionary = main._combat_protocol()
	var checks := [
		is_equal_approx(protocol.boss.speed_mps, 0.0),
		is_equal_approx(protocol.player.speed_mps, 6.25),
		is_equal_approx(protocol.player.aim_speed_mps, 2.75),
		is_equal_approx(protocol.boss.hp, 1200.0),
		is_equal_approx(protocol.boss.attack_warning_s, 1.1),
		is_equal_approx(protocol.stalker.speed_mps, 6.4),
		is_equal_approx(protocol.stalker.damage, 17.0),
		is_equal_approx(protocol.weapon.damage, 55.0),
		is_equal_approx(protocol.supplies.pickup_s, 0.35),
		is_equal_approx(protocol.supplies.pickup_radius_m, 1.4),
		is_equal_approx(protocol.portals.through_player_squeeze_s, 0.8),
		is_equal_approx(protocol.portals.through_player_interaction_range_m, 1.75),
		is_equal_approx(protocol.portals.through_boss_smash_s, 2.25),
		is_equal_approx(protocol.portals.break_boss_smash_s, 2.75),
		protocol.protocol_id == "combat_v3_inspector_playtest",
	]
	if checks.has(false):
		push_error("Inspector values did not reach the combat protocol: %s" % protocol)
		quit(1)
		return
	var package := OS.get_environment("RATKING_VERIFY_PACKAGE")
	if package.is_empty():
		push_error("RATKING_VERIFY_PACKAGE is required")
		quit(1)
		return
	var level = preload("res://full_pcg/godot/replay_combat_level.gd").new()
	level.package_path = package
	level.layout_scale = main.map_size
	level.protocol_override = protocol
	level.native_boss = true
	root.add_child(level)
	level.set_physics_process(false)
	for navigation_map in level.maps.values():
		NavigationServer3D.map_set_use_async_iterations(navigation_map, false)
		NavigationServer3D.map_force_update(navigation_map)
	await physics_frame
	await physics_frame
	var raw_spawn: Array = level.data.layout.spawn.position
	var expected_spawn := Vector3(raw_spawn[0] * main.map_size,level.player_body.position.y,raw_spawn[1] * main.map_size)
	if level.player_body.position.distance_to(expected_spawn) > 0.00001:
		push_error("Map Size did not scale layout and spawn coordinates together")
		quit(1)
		return
	var raw_vertex: Array = level.data.obstacle_faces[0]
	var raw_point := Vector2(raw_vertex[0],raw_vertex[2])
	var obstacle = level.data.layout.obstacles[0]
	var nearest := raw_point.distance_squared_to(Vector2(obstacle.position[0],obstacle.position[1]))
	for candidate in level.data.layout.obstacles.slice(1):
		var distance := raw_point.distance_squared_to(Vector2(candidate.position[0],candidate.position[1]))
		if distance < nearest:
			obstacle = candidate
			nearest = distance
	var scaled_obstacle_vertex := level.scaled_vertex(raw_vertex,true)
	var raw_offset := raw_point - Vector2(obstacle.position[0],obstacle.position[1])
	var scaled_center: Vector2 = Vector2(obstacle.position[0],obstacle.position[1]) * main.map_size
	var scaled_offset: Vector2 = Vector2(scaled_obstacle_vertex.x,scaled_obstacle_vertex.z) - scaled_center
	if raw_offset.distance_to(scaled_offset) > 0.00001:
		push_error("Map Size changed block dimensions")
		quit(1)
		return
	var player_shape: CapsuleShape3D = level.player_body.get_children().filter(
		func(child): return child is CollisionShape3D
	)[0].shape
	var boss_shape: CapsuleShape3D = level.boss_body.get_children().filter(
		func(child): return child is CollisionShape3D
	)[0].shape
	if not is_equal_approx(player_shape.radius,protocol.player.radius_m) or not is_equal_approx(
		boss_shape.radius,protocol.boss.radius_m
	):
		push_error("Map Size changed player or Boss collision dimensions")
		quit(1)
		return
	var supply = level.data.layout.supplies[0]
	var supply_center := level.point(supply.position,level.player_body.position.y)
	var supply_marker: MeshInstance3D = level.supply_markers[supply.id]
	var expected_marker := level.point(supply.position,0.35)
	if supply_marker.position.distance_to(expected_marker) > 0.00001:
		push_error("Map Size did not keep the ammo marker on its interaction point")
		quit(1)
		return
	level.player_body.position = supply_center + Vector3(main.supply_pickup_range - .05,0,0)
	var reserve_before: int = level.reserve
	level.command = {"interact":true,"fire":false,"reload":false,"move_direction":[0,0],"aim":false,"heading":0.0,"bearing":0.0}
	level._interact(1.0 / 60.0)
	if level.pickup_id != supply.id:
		push_error("Expanded supply range did not start pickup")
		quit(1)
		return
	level.command.interact = false
	for tick in range(ceili(main.supply_pickup_seconds * 60.0) + 1):
		level._interact(1.0 / 60.0)
	if not level.collected.has(supply.id) or level.reserve != reserve_before + int(protocol.supplies.rounds_per_pack):
		push_error("A single E press did not collect ammunition")
		quit(1)
		return
	var through = level.data.layout.portals.filter(func(portal): return portal.kind == "through")[0]
	var through_center := level.point(through.center,level.player_body.position.y)
	level.player_body.position = through_center + Vector3(main.through_interaction_range - .05,0,0)
	level.command = {"interact":true,"fire":false,"reload":false,"move_direction":[0,0],"aim":false,"heading":0.0,"bearing":0.0}
	level._interact(1.0 / 60.0)
	if level.squeeze_id != through.id:
		push_error("Expanded through interaction range did not start squeezing")
		quit(1)
		return
	level.command.interact = false
	for tick in range(ceili(main.player_squeeze_seconds * 60.0) + 1):
		level._interact(1.0 / 60.0)
	if level.squeeze_open_id != through.id or not level.event_log.any(
		func(event): return event.kind == "squeeze_end" and event.data.id == through.id
	):
		push_error("A single E press did not complete the through squeeze")
		quit(1)
		return
	var boss_gate_link: NavigationLink3D = level.links["boss:" + through.id]
	level.boss_body.position = Vector3(boss_gate_link.start_position.x,
		level.boss_body.position.y,boss_gate_link.start_position.z)
	level.smash_id = ""
	level.smash_s = 0
	level._boss_smash(1.0 / 60.0)
	if level.smash_id != through.id:
		push_error("Boss did not start smashing from the scaled gate approach point")
		quit(1)
		return
	level._boss_smash(float(protocol.portals.through_boss_smash_s) + 0.01)
	if not level.gates[through.id].opened:
		push_error("Boss did not open the scaled gate after its smash duration")
		quit(1)
		return
	for gate_spec in level.data.gates:
		if gate_spec.kind not in ["through","break"]:
			continue
		var portal_spec: Dictionary = level.next_portal(gate_spec.id)
		var gate_link: NavigationLink3D = level.links["boss:" + gate_spec.id]
		level.boss_body.position = Vector3(gate_link.start_position.x,
			level.boss_body.position.y,gate_link.start_position.z)
		if not level._boss_at_gate_approach(gate_spec.id,portal_spec):
			push_error("Scaled Boss approach was not detected for " + gate_spec.id)
			quit(1)
			return
	level.combat.boss.speed_mps = 4.2
	for normal_portal in level.data.layout.portals:
		if normal_portal.kind != "normal":
			continue
		var normal_link: NavigationLink3D = level.links["boss:" + normal_portal.id]
		var link_start := Vector3(normal_link.start_position.x,0,normal_link.start_position.z)
		var link_end := Vector3(normal_link.end_position.x,0,normal_link.end_position.z)
		var link_direction: Vector3 = (link_end-link_start).normalized()
		var approach: Vector3 = NavigationServer3D.map_get_closest_point(
			level.maps.boss,link_start-link_direction*1.5
		)
		var finish: Vector3 = NavigationServer3D.map_get_closest_point(
			level.maps.boss,link_end+link_direction*2.5
		)
		level.boss_body.position = Vector3(approach.x,level.boss_body.position.y,approach.z)
		level.player_body.position = Vector3(finish.x,level.player_body.position.y,finish.z)
		await physics_frame
		var midpoint := (link_start+link_end)*.5
		var initial_side: float = (level.boss_body.position-midpoint).dot(link_direction)
		var crossed_normal := false
		for frame in range(120):
			level._boss_move(1.0/60.0)
			var current_side: float = (level.boss_body.position-midpoint).dot(link_direction)
			if initial_side*current_side < 0:
				crossed_normal = true
				break
			await physics_frame
		if not crossed_normal:
			push_error("Boss did not physically cross normal portal " + normal_portal.id)
			quit(1)
			return
	level.combat.boss.speed_mps = 0.0
	# The split spawn candidate is derived from an already-scaled live Boss
	# position. It must stay close to the Boss instead of being scaled twice.
	level.player_body.position = level.point(level.data.layout.spawn.position,level.player_body.position.y)
	level.boss_body.position = level.point(level.data.layout.boss.position,level.boss_body.position.y)
	level._spawn_stalker()
	if not is_instance_valid(level.stalker_body):
		push_error("Stalker could not spawn on the scaled layout")
		quit(1)
		return
	var stalker_xz := Vector2(level.stalker_body.position.x,level.stalker_body.position.z)
	var boss_xz := Vector2(level.boss_body.position.x,level.boss_body.position.z)
	if stalker_xz.distance_to(boss_xz) > 1.11:
		push_error("Stalker spawn was scaled twice or moved away from the Boss")
		quit(1)
		return
	level.stalker_retreat_s = 0
	level.player_body.position = level.stalker_body.position + Vector3(3.0,0,0)
	level._stalker_step(1.0 / 60.0)
	if not is_equal_approx(level.stalker_body.velocity.length(),main.stalker_speed):
		push_error("Inspector Stalker Speed did not reach the live Stalker")
		quit(1)
		return
	level.stalker_retreat_s = 0
	level.stalker_warning_s = 0
	level.player_body.position = level.stalker_body.position + Vector3(0.7,0,0)
	await physics_frame
	var hp_before: float = level.player_hp
	level._stalker_step(float(protocol.stalker.warning_s) + 0.01)
	if not is_equal_approx(level.player_hp,hp_before-main.stalker_damage):
		push_error("Inspector Stalker Damage did not reduce player health")
		quit(1)
		return
	level.player_hp = main.stalker_damage
	level.stalker_retreat_s = 0
	level.stalker_warning_s = 0
	level._stalker_step(float(protocol.stalker.warning_s) + 0.01)
	if level.result != "death":
		push_error("Lethal Stalker damage did not end the combat")
		quit(1)
		return
	var stopped_at: Vector3 = level.boss_body.position
	for tick in range(10):
		level._boss_move(1.0 / 60.0)
	if level.boss_body.velocity.length() > 0.00001:
		push_error("Boss retained velocity with Inspector Boss Speed set to zero")
		quit(1)
		return
	stopped_at = level.boss_body.position
	level.combat.boss.speed_mps = 4.2
	for tick in range(10):
		level._boss_move(1.0 / 60.0)
	if level.boss_body.velocity.length() < 4.19 or level.boss_body.position.distance_to(stopped_at) < 0.1:
		push_error("Non-zero Inspector Boss Speed did not move the Boss")
		quit(1)
		return
	print("PASS scaled resource and Stalker positions plus Inspector combat values control CombatLevel")
	level.free()
	main.free()
	quit(0)

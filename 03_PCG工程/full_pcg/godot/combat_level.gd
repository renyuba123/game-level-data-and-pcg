extends "res://full_pcg/godot/layout_decoder.gd"
## Minimal playable combat whitebox. Python Layout supplies every wall and portal.

@export_file("*.json") var package_path := "res://full_pcg_output/combat_godot/seed_0001.json"

var combat: Dictionary = {}
var player_body: CharacterBody3D
var boss_body: CharacterBody3D
var stalker_body: CharacterBody3D
var view_camera: Camera3D
var hud: Label
var elapsed_s := 0.0
var tick := 0
var result := ""
var phase := 1
var boss_hp := 0.0
var player_hp := 0.0
var split_tick := -1
var split_t := -1.0
var loaded := 0
var reserve := 0
var cooldown_s := 0.0
var aim_s := 0.0
var reload_s := 0.0
var attack_s := 0.0
var squeeze_s := 0.0
var squeeze_open_s := 0.0
var squeeze_id := ""
var squeeze_open_id := ""
var interact_latched := false
var vault_id := ""
var vault_start := Vector3.ZERO
var vault_end := Vector3.ZERO
var vault_time := 0.0
var vault_returning := false
var smash_s := 0.0
var smash_id := ""
var pickup_s := 0.0
var pickup_id := ""
var collected: Dictionary = {}
var supply_markers: Dictionary = {}
var stalker_control_s := 0.0
var stalker_warning_s := 0.0
var stalker_retreat_s := 0.0
var event_log: Array = []
var protocol_override: Dictionary = {}


func _ready() -> void:
	var parsed = JSON.parse_string(FileAccess.get_file_as_string("res://combat_pcg/combat_config.json"))
	if not parsed is Dictionary:
		push_error("Missing combat protocol")
		set_physics_process(false)
		return
	combat = parsed if protocol_override.is_empty() else protocol_override.duplicate(true)
	if not load_package(package_path):
		push_error("Missing combat Layout package: " + package_path)
		set_physics_process(false)
		return
	# Historical v5 packages predate embedded window parameters.
	if data.layout.get("schema_version")==5 and not data.has("window"):
		data.window = {"duration_s":.65,"arc_height_m":.70,"interaction_range_m":.42}
	var layout: Dictionary = data.layout
	player_body = _actor("Player", layout.spawn.position, combat.player, 16, 1 | 2 | 8 | 32, Color("54b56d"))
	boss_body = _actor("LargeBoss", layout.boss.position, combat.boss, 8, 1 | 4 | 16, Color("bf4b4b"))
	boss_hp = float(combat.boss.hp)
	player_hp = float(combat.player.hp)
	loaded = mini(int(combat.weapon.magazine), int(combat.supplies.initial_rounds_including_magazine))
	reserve = int(combat.supplies.initial_rounds_including_magazine) - loaded
	for item in layout.supplies:
		var marker := MeshInstance3D.new()
		marker.name = item.id
		var mesh := SphereMesh.new()
		mesh.radius = 0.24
		mesh.height = 0.48
		marker.mesh = mesh
		marker.material_override = material(Color("e2bd59"))
		# Layout positions use the same Map Size transform as their interaction
		# point. The marker's local radius and height remain unchanged.
		marker.position = point(item.position, 0.35)
		add_child(marker)
		supply_markers[item.id] = marker
	_create_view()
	_log("spawn", {"room_id": layout.spawn.room, "boss_room_id": layout.boss.room,
		"player": [player_body.position.x,player_body.position.z],
		"boss": [boss_body.position.x,boss_body.position.z]})


func _actor(label: String, coords: Array, spec: Dictionary, layer: int, mask: int,
		color: Color, world_coordinates := false) -> CharacterBody3D:
	var body := CharacterBody3D.new()
	body.name = label
	body.motion_mode = CharacterBody3D.MOTION_MODE_FLOATING
	body.collision_layer = layer
	body.collision_mask = mask
	if world_coordinates:
		body.position = Vector3(float(coords[0]), float(spec.height_m) / 2.0, float(coords[1]))
	else:
		body.position = point(coords,float(spec.height_m) / 2.0)
	var capsule := CapsuleShape3D.new()
	capsule.radius = float(spec.radius_m)
	capsule.height = float(spec.height_m)
	var collision := CollisionShape3D.new()
	collision.shape = capsule
	body.add_child(collision)
	var appearance := MeshInstance3D.new()
	var mesh := CapsuleMesh.new()
	mesh.radius = capsule.radius
	mesh.height = capsule.height
	appearance.mesh = mesh
	appearance.material_override = material(color)
	body.add_child(appearance)
	add_child(body)
	return body


func _create_view() -> void:
	var bounds: Array = data.layout.bounds
	var center := Vector3((float(bounds[0]) + float(bounds[2])) * layout_scale / 2.0, 35,
		(float(bounds[1]) + float(bounds[3])) * layout_scale / 2.0)
	view_camera = Camera3D.new()
	view_camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	view_camera.size = maxf(float(bounds[2]) - float(bounds[0]), float(bounds[3]) - float(bounds[1])) * layout_scale * 1.35
	view_camera.position = center
	view_camera.rotation_degrees = Vector3(-90, 0, 0)
	view_camera.current = true
	add_child(view_camera)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-65, -20, 0)
	add_child(light)
	var canvas := CanvasLayer.new()
	hud = Label.new()
	hud.position = Vector2(16, 16)
	canvas.add_child(hud)
	add_child(canvas)
	_update_hud()


func _log(kind: String, details: Dictionary = {}) -> void:
	event_log.append({"id": "event_%05d" % event_log.size(), "t": elapsed_s,
		"step": tick, "sequence": event_log.size(), "kind": kind, "data": details})


func _update_hud() -> void:
	if is_instance_valid(hud):
		var interaction := _interaction_hint()
		hud.text = "Phase %d | Player HP %.0f | Boss HP %.0f | Ammo %d+%d | %.1fs\nWASD move  Mouse hold aim/fire  R reload  E interact\n%s%s" % [
			phase, player_hp, boss_hp, loaded, reserve, elapsed_s, interaction, result]


func _through_range() -> float:
	return float(combat.portals.get("through_player_interaction_range_m", 1.6))

func _pickup_range() -> float:
	return float(combat.supplies.pickup_radius_m)


func _interaction_hint() -> String:
	if squeeze_id != "":
		var progress := 100.0 * squeeze_s / maxf(0.01,float(combat.portals.through_player_squeeze_s))
		return "Squeezing through %s | %.0f%%\n" % [squeeze_id,minf(100.0,progress)]
	if pickup_id != "":
		var progress := 100.0 * pickup_s / maxf(0.01,float(combat.supplies.pickup_s))
		return "Picking up ammo %s | %.0f%%\n" % [pickup_id,minf(100.0,progress)]
	for item in data.layout.supplies:
		if collected.has(item.id):
			continue
		var center := point(item.position,player_body.position.y)
		if player_body.position.distance_to(center) <= _pickup_range():
			return "Press E to pick up ammo %s\n" % item.id
	for portal in data.layout.portals:
		if portal.kind != "through" or gates[portal.id].opened or squeeze_open_id == portal.id:
			continue
		var center := point(portal.center, player_body.position.y)
		if player_body.position.distance_to(center) <= _through_range():
			return "Press E to squeeze through %s\n" % portal.id
	return ""


func _terminal(kind: String) -> void:
	if result != "":
		return
	result = kind
	_log(kind)
	_update_hud()
	_save_episode()


func _save_episode() -> void:
	var second_duration := maxf(0, elapsed_s - split_t) if split_t >= 0 else 0.0
	var record := {"schema_version": combat.schema_version, "layout_schema_version":data.layout.get("schema_version"), "layout_scale":layout_scale, "window_config_hash":data.get("window_config_hash"), "package_hash":data.get("package_hash"), "episode_id": "godot_%s_%d" % [str(data.layout.seed), int(Time.get_unix_time_from_system())],
		"individual_id": "layout_" + str(data.layout.layout_hash).substr(0, 12), "policy": "human_or_replay",
		"scenario_seed": int(data.layout.seed), "layout_hash": data.layout.layout_hash,
		"combat_config_hash": JSON.stringify(combat).sha256_text(),
		"outcome": result, "duration_s": elapsed_s,
		"final_player_hp": player_hp,
		"phase2_reached": phase == 2,
		"phase_durations_s": {"phase1": elapsed_s - second_duration, "phase2": second_duration},
		"events": event_log}
	var file := FileAccess.open("user://combat_episode.json", FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(record, "  "))
		file.close()


func _physics_process(delta: float) -> void:
	if result != "" or not is_instance_valid(player_body) or not is_instance_valid(boss_body):
		return
	tick += 1
	elapsed_s += delta
	cooldown_s = maxf(0, cooldown_s - delta)
	stalker_control_s = maxf(0, stalker_control_s - delta)
	# A valid grab wins a tie with a shot at the same logical step.
	_player_move(delta)
	_boss_move(delta)
	_boss_attack(delta)
	if result != "": return
	_stalker_step(delta)
	if result != "": return
	_boss_smash(delta)
	_reload(delta)
	_interact(delta)
	_shoot(delta)
	if result == "" and elapsed_s >= float(combat.simulation.time_limit_s):
		_terminal("timeout")
	_update_hud()


func _move_direction() -> Vector3:
	var direction := Vector3.ZERO
	if Input.is_key_pressed(KEY_W): direction.z -= 1
	if Input.is_key_pressed(KEY_S): direction.z += 1
	if Input.is_key_pressed(KEY_A): direction.x -= 1
	if Input.is_key_pressed(KEY_D): direction.x += 1
	return direction


func _aim_held() -> bool:
	return _fire_held()


func _player_move(delta: float) -> void:
	if vault_id != "":
		_step_vault(delta)
		return
	var speed := float(combat.player.aim_speed_mps if _aim_held() else combat.player.speed_mps)
	player_body.velocity = _move_direction().normalized() * speed if stalker_control_s <= 0 else Vector3.ZERO
	player_body.move_and_slide()


func _clear_ray(from: Vector3, to: Vector3, actor: CollisionObject3D, target: CollisionObject3D, contact := false) -> bool:
	var query := PhysicsRayQueryParameters3D.create(from, to)
	query.collision_mask = 1 | 8 | 16 | 32 | 64
	if contact or data.layout.get("schema_version") != 5: query.collision_mask |= 2 | 4
	query.exclude = [actor.get_rid()]
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	return not hit.is_empty() and hit.collider == target


func _boss_move(delta: float) -> void:
	var start := Vector3(boss_body.position.x, 0, boss_body.position.z)
	var finish := Vector3(player_body.position.x, 0, player_body.position.z)
	var path := nav_path("boss", start, finish)
	# Navigation can return a partial path to the last reachable point.
	if path.is_empty() or path[-1].distance_to(finish) > float(combat.boss.grab_range_m):
		var gate_target := _nearest_closed_gate(start)
		if gate_target != start:
			path = nav_path("boss", start, gate_target)
	var target := _boss_waypoint(start, path)
	var direction := target - start
	var speed := minf(float(combat.boss.speed_mps),direction.length() / delta)
	boss_body.velocity = direction.normalized() * speed
	boss_body.move_and_slide()


func _boss_waypoint(start: Vector3, path: PackedVector3Array) -> Vector3:
	# Prefer the furthest point in path order that the complete capsule can
	# sweep to locally. Re-selecting by a distance cutoff alone can alternate
	# between the projected origin and the next point every physics tick.
	# The navigation-link span grows with Map Size, so the lookahead must use
	# the same scale or a normal doorway link can become longer than the fixed
	# cutoff and make the Boss oscillate at its entrance.
	var lookahead := 2.0 * layout_scale
	for i in range(path.size()-1,-1,-1):
		var displacement := path[i] - start
		if displacement.length() <= .01 or displacement.length() > lookahead:
			continue
		if not boss_body.test_move(boss_body.transform, displacement):
			return path[i]
	# Allow contact-limited movement so the boss still closes to grab range.
	for waypoint in path:
		if waypoint.distance_to(start) > .05:
			return waypoint
	return start


func _nearest_closed_gate(start: Vector3) -> Vector3:
	var target := start
	var best := INF
	for gate in data.gates:
		if gate.kind == "window" or gates[gate.id].opened: continue
		for coords in data.links:
			if coords.portal != gate.id or coords.role != "boss": continue
			for end in coords.points:
				var candidate := point(end)
				var path := nav_path("boss", start, candidate)
				if path.is_empty() or path[-1].distance_to(candidate) > .35: continue
				var distance := start.distance_to(path[0])
				for i in range(1,path.size()):
					distance += path[i-1].distance_to(path[i])
				if distance < best:
					best = distance
					target = candidate
	return target


func _boss_attack(delta: float) -> void:
	var close := boss_body.position.distance_to(player_body.position) <= float(combat.boss.grab_range_m)
	var visible := _clear_ray(boss_body.position + Vector3(0, .25, 0),
		player_body.position + Vector3(0, .25, 0), boss_body, player_body, true)
	if not close or not visible:
		attack_s = 0
		return
	if attack_s == 0: _log("attack_warning", {"by": "large_boss"})
	attack_s += delta
	if attack_s >= float(combat.boss.attack_warning_s):
		_log("grab", {"by": "large_boss"})
		_terminal("death")


func _boss_smash(delta: float) -> void:
	if smash_id != "":
		smash_s -= delta
		if smash_s <= 0:
			set_open(smash_id, true)
			_log("portal_open", {"id": smash_id, "by": "boss"})
			smash_id = ""
		return
	for gate in data.gates:
		if gate.kind == "window" or gates[gate.id].opened: continue
		var portal: Dictionary = {}
		for item in data.layout.portals:
			if item.id == gate.id: portal = item; break
		if portal.is_empty(): continue
		if _boss_at_gate_approach(gate.id,portal):
			smash_id = gate.id
			smash_s = float(combat.portals.through_boss_smash_s if gate.kind == "through" else combat.portals.break_boss_smash_s)
			_log("smash_start", {"id": gate.id, "kind": gate.kind})
			break


func _boss_at_gate_approach(id: String, portal: Dictionary) -> bool:
	# Closed-gate navigation leads the Boss to one of the link endpoints.
	# Those endpoints scale with Map Size, while the old fixed 1 m radius from
	# the portal centre did not. Test the actual approach anchors so every map
	# scale starts the same interaction at the place the Boss can reach.
	var key := "boss:" + id
	if links.has(key):
		var link: NavigationLink3D = links[key]
		var boss_xz := Vector2(boss_body.position.x,boss_body.position.z)
		var start_xz := Vector2(link.start_position.x,link.start_position.z)
		var end_xz := Vector2(link.end_position.x,link.end_position.z)
		var tolerance := float(combat.boss.radius_m) + 0.15
		return minf(boss_xz.distance_to(start_xz),boss_xz.distance_to(end_xz)) <= tolerance
	# Compatibility fallback for an old package without a Boss link.
	var center := point(portal.center,boss_body.position.y)
	return center.distance_to(boss_body.position) <= 1.0


func _reload_held() -> bool:
	return Input.is_key_pressed(KEY_R)


func _interaction_held() -> bool:
	return Input.is_key_pressed(KEY_E) or Input.is_joy_button_pressed(0, JOY_BUTTON_A)


func _fire_held() -> bool:
	return Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT)


func _reload(delta: float) -> void:
	if reload_s > 0:
		reload_s -= delta
		if reload_s <= 0:
			var amount := mini(int(combat.weapon.magazine) - loaded, reserve)
			loaded += amount
			reserve -= amount
			_log("reload_end", {"loaded": loaded, "reserve": reserve})
		return
	if _reload_held() and reserve > 0 and loaded < int(combat.weapon.magazine):
		reload_s = float(combat.weapon.reload_s)
		_log("reload_start")


func _interact(delta: float) -> void:
	if squeeze_open_s > 0:
		squeeze_open_s -= delta
		if squeeze_open_s <= 0 and squeeze_open_id != "":
			allow_squeeze(squeeze_open_id, false)
			squeeze_open_id = ""
	var held := _interaction_held()
	var pressed := held and not interact_latched
	interact_latched = held
	if vault_id != "": return
	if squeeze_id != "":
		var active_portal = next_portal(squeeze_id)
		if active_portal.is_empty():
			squeeze_id = ""
			squeeze_s = 0
		else:
			var active_center := point(active_portal.center,player_body.position.y)
			if player_body.position.distance_to(active_center) > _through_range() + .35:
				squeeze_id = ""
				squeeze_s = 0
			else:
				squeeze_s += delta
				if squeeze_s >= float(combat.portals.through_player_squeeze_s):
					allow_squeeze(squeeze_id,true)
					squeeze_open_s = 1.5
					_log("squeeze_end",{"id":squeeze_id})
					squeeze_open_id = squeeze_id
					squeeze_id = ""
					squeeze_s = 0
				return
	if pickup_id != "":
		var active_supply = next_supply(pickup_id)
		if active_supply.is_empty() or collected.has(pickup_id):
			pickup_id = ""
			pickup_s = 0
		else:
			var active_center := point(active_supply.position,player_body.position.y)
			if player_body.position.distance_to(active_center) > _pickup_range():
				pickup_id = ""
				pickup_s = 0
			else:
				pickup_s += delta
				if pickup_s >= float(combat.supplies.pickup_s):
					collect_supply(pickup_id)
					pickup_id = ""
					pickup_s = 0
				return
	if not held:
		squeeze_s = 0
		return
	for item in data.layout.supplies:
		if collected.has(item.id): continue
		var center := point(item.position, player_body.position.y)
		if player_body.position.distance_to(center) <= _pickup_range():
			if pickup_id != item.id:
				pickup_id = item.id
				pickup_s = 0
				_log("pickup_start", {"id": item.id})
			return
	for portal in data.layout.portals:
		if portal.kind == "window":
			if pressed:
				if _start_vault(portal.id): return
			continue
		if portal.kind != "through" or gates[portal.id].opened or squeeze_open_id == portal.id: continue
		var center := point(portal.center, player_body.position.y)
		if player_body.position.distance_to(center) <= _through_range():
			if squeeze_id != portal.id:
				squeeze_id = portal.id
				squeeze_s = 0
				_log("squeeze_start", {"id": portal.id})
			return


func next_portal(id: String) -> Dictionary:
	for portal in data.layout.portals:
		if portal.id == id:
			return portal
	return {}


func next_supply(id: String) -> Dictionary:
	for item in data.layout.supplies:
		if item.id == id:
			return item
	return {}


func _start_vault(id: String) -> bool:
	if vault_id != "" or not gates.has(id) or gates[id].kind != "window": return false
	var link: NavigationLink3D = links["player:" + id]
	var a := link.start_position
	var b := link.end_position
	a.y = player_body.position.y
	b.y = a.y
	var entry := a if player_body.position.distance_to(a) < player_body.position.distance_to(b) else b
	if player_body.position.distance_to(entry) > float(data.window.interaction_range_m): return false
	vault_start = player_body.position
	vault_end = b if entry == a else a
	vault_time = 0
	vault_returning = false
	allow_vault(id, true)
	if player_body.test_move(player_body.transform, vault_end-vault_start):
		allow_vault(id, false)
		return false
	vault_id = id
	_log("vault_start", {"id":id})
	return true


func _step_vault(delta: float) -> void:
	var duration := float(data.window.duration_s)
	var next := clampf(vault_time + (-delta if vault_returning else delta),0.0,duration)
	var t := next/duration
	var target := vault_start.lerp(vault_end,t)
	target.y += float(data.window.arc_height_m)*sin(PI*t)
	var hit := player_body.move_and_collide(target-player_body.position)
	if hit != null:
		vault_returning = true
		return
	vault_time = next
	if (vault_returning and next<=0) or (not vault_returning and next>=duration):
		allow_vault(vault_id, false)
		_log("vault_blocked" if vault_returning else "vault_end", {"id":vault_id})
		vault_id = ""


func collect_supply(id: String) -> bool:
	if collected.has(id) or result != "": return false
	for item in data.layout.supplies:
		if item.id != id: continue
		var center := point(item.position, player_body.position.y)
		if player_body.position.distance_to(center) > _pickup_range(): return false
		collected[id] = true
		reserve += int(combat.supplies.rounds_per_pack)
		supply_markers[id].visible = false
		_log("pickup_end", {"id": id, "reserve": reserve})
		return true
	return false


func _mouse_target() -> Vector3:
	var mouse := get_viewport().get_mouse_position()
	var origin := view_camera.project_ray_origin(mouse)
	var direction := view_camera.project_ray_normal(mouse)
	if absf(direction.y) < 0.001: return boss_body.position
	return origin + direction * ((player_body.position.y - origin.y) / direction.y)


func _shoot(delta: float) -> void:
	if vault_id != "" or reload_s > 0 or loaded <= 0 or cooldown_s > 0 or not _fire_held():
		aim_s = 0
		return
	aim_s += delta
	if aim_s < float(combat.weapon.aim_s): return
	_fire_at(_mouse_target())


func _fire_at(target: Vector3) -> void:
	if loaded <= 0 or cooldown_s > 0 or result != "": return
	loaded -= 1
	cooldown_s = float(combat.weapon.fire_interval_s)
	var muzzle := player_body.position + Vector3(0, .25, 0)
	var aim := (target - muzzle).normalized()
	var endpoint := muzzle + aim * float(combat.weapon.range_m)
	var query := PhysicsRayQueryParameters3D.create(muzzle, endpoint)
	query.exclude = [player_body.get_rid()]
	query.collision_mask = (1 | 64 | 8 | 32) if data.layout.get("schema_version") == 5 else (1 | 2 | 4 | 8 | 32)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	_log("shot", {"loaded": loaded, "from": [muzzle.x, muzzle.z], "toward": [endpoint.x, endpoint.z]})
	if hit.is_empty(): return
	if hit.collider == boss_body:
		_apply_boss_hit(float(combat.weapon.damage))
	elif is_instance_valid(stalker_body) and hit.collider == stalker_body:
		stalker_retreat_s = 3.0
		_log("hit", {"target": "stalker", "response": "interrupt_and_retreat"})


func _apply_boss_hit(damage: float) -> void:
	if result != "" or damage <= 0: return
	if phase == 1:
		var threshold := float(combat.boss.hp) * float(combat.stalker.split_hp_fraction)
		boss_hp = maxf(threshold, boss_hp - damage)
		_log("hit", {"target": "large_boss", "hp": boss_hp, "phase": 1})
		if boss_hp <= threshold:
			phase = 2
			split_tick = tick
			split_t = elapsed_s
			_spawn_stalker()
			_log("split", {"hp": boss_hp})
	else:
		if tick <= split_tick:
			return
		boss_hp = maxf(0, boss_hp - damage)
		_log("hit", {"target": "large_boss", "hp": boss_hp, "phase": 2})
		if boss_hp <= 0:
			_terminal("victory")


func _spawn_stalker() -> void:
	var away := boss_body.position - player_body.position
	away.y = 0
	if away.length() < .01: away = Vector3.RIGHT
	away = away.normalized()
	var offsets := [away, -away, Vector3(away.z, 0, -away.x), Vector3(-away.z, 0, away.x)]
	for offset in offsets:
		var candidate: Vector3 = boss_body.position + offset * 1.1
		var down := PhysicsRayQueryParameters3D.create(candidate + Vector3(0, 2, 0), candidate - Vector3(0, 2, 0))
		down.collision_mask = 1
		var floor_hit := get_world_3d().direct_space_state.intersect_ray(down)
		if floor_hit.is_empty() or floor_hit.collider.name != "Floor": continue
		var capsule := CapsuleShape3D.new()
		capsule.radius = float(combat.stalker.radius_m)
		capsule.height = 1.6
		var query := PhysicsShapeQueryParameters3D.new()
		query.shape = capsule
		query.transform = Transform3D(Basis(), Vector3(candidate.x, 0.9, candidate.z))
		query.collision_mask = 1 | 2 | 4 | 8 | 16
		if not get_world_3d().direct_space_state.intersect_shape(query).is_empty(): continue
		var spec: Dictionary = {"radius_m": combat.stalker.radius_m, "height_m": 1.6}
		# candidate is already in scaled world space because it is derived from
		# the live Boss position. Do not apply layout_scale a second time.
		stalker_body = _actor("Stalker", [candidate.x, candidate.z], spec, 32, 1 | 16,
			Color("c98d58"), true)
		stalker_retreat_s = .5
		return
	push_warning("No collision-valid stalker spawn near Boss")


func _stalker_step(delta: float) -> void:
	if not is_instance_valid(stalker_body): return
	if stalker_retreat_s > 0:
		stalker_retreat_s -= delta
		return
	var direction := player_body.position - stalker_body.position
	direction.y = 0
	if direction.length() > .9:
		stalker_body.velocity = direction.normalized() * float(combat.stalker.speed_mps)
		stalker_body.move_and_slide()
		stalker_warning_s = 0
	elif _clear_ray(stalker_body.position + Vector3(0, .2, 0),
		player_body.position + Vector3(0, .2, 0), stalker_body, player_body, true):
		if stalker_warning_s == 0: _log("attack_warning", {"by": "stalker"})
		stalker_warning_s += delta
		if stalker_warning_s >= float(combat.stalker.warning_s):
			player_hp = maxf(0.0, player_hp - float(combat.stalker.damage))
			stalker_control_s = float(combat.stalker.control_s)
			stalker_retreat_s = float(combat.stalker.cooldown_s)
			stalker_warning_s = 0
			_log("grab", {"by": "stalker", "effect": "damage_and_temporary_control",
				"damage": float(combat.stalker.damage), "player_hp": player_hp})
			if player_hp <= 0:
				_terminal("death")

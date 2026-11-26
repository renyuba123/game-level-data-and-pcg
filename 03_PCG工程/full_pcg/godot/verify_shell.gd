extends SceneTree

const Decoder = preload("res://full_pcg/godot/layout_decoder.gd")


func _initialize() -> void:
	call_deferred("_run")


func _point(coords: Array) -> Vector3:
	return Vector3(float(coords[0]), 0.0, float(coords[1]))


func _run() -> void:
	var folder := OS.get_environment("RATKING_VERIFY_DIR")
	if folder.is_empty(): folder = "res://full_pcg_output/shell_checks"
	var manifest_path := folder.path_join("manifest.json")
	var manifest = JSON.parse_string(FileAccess.get_file_as_string(manifest_path))
	if not manifest is Dictionary:
		push_error("Missing combat Godot package manifest")
		quit(2)
		return
	var rows: Array = []
	for entry in manifest.packages:
		var decoder = Decoder.new()
		get_root().add_child(decoder)
		var issues: Array[String] = []
		if not decoder.load_package(entry.path):
			issues.append("package_load_failed")
		else:
			# The headless spatial checks require a completed navigation snapshot.
			for rid in decoder.maps.values():
				NavigationServer3D.map_set_use_async_iterations(rid,false)
				NavigationServer3D.map_force_update(rid)
			for step in range(12):
				await physics_frame
			var layout: Dictionary = decoder.data.layout
			if layout.layout_hash != entry.layout_hash:
				issues.append("layout_hash_mismatch")
			for gate in decoder.data.gates:
				var player_link: NavigationLink3D = decoder.links["player:" + gate.id]
				var boss_link: NavigationLink3D = decoder.links["boss:" + gate.id]
				if gate.kind == "through":
					if not player_link.enabled or boss_link.enabled:
						issues.append("through_initial_link_state:" + gate.id)
					if not decoder.allow_squeeze(gate.id, true):
						issues.append("squeeze_unavailable:" + gate.id)
					decoder.allow_squeeze(gate.id, false)
				elif gate.kind == "break":
					if player_link.enabled or boss_link.enabled:
						issues.append("break_initial_link_state:" + gate.id)
			for gate in decoder.data.gates:
				for role in ["player","boss"]:
					if crossing(decoder,gate,role): issues.append("closed crossing "+gate.id+" "+role)
				if gate.kind in ["window","through"]:
					var pass_center := ray_passes(decoder,gate.id,0,1.15)
					if pass_center != (gate.kind=="window"): issues.append("centre_ballistics:"+gate.id)
					if gate.kind=="through" and not ray_passes(decoder,gate.id,.35,1.15): issues.append("no_door_slit:"+gate.id)
				if gate.kind=="window":
					if ray_passes(decoder,gate.id,0,.30): issues.append("missing_window_sill:"+gate.id)
					decoder.allow_vault(gate.id,true)
					if not crossing(decoder,gate,"player"): issues.append("blocked_vault:"+gate.id)
					if crossing(decoder,gate,"boss"): issues.append("boss_window_cross:"+gate.id)
					decoder.allow_vault(gate.id,false)
					decoder.set_open(gate.id,true)
					if decoder.gates[gate.id].opened or decoder.links["boss:"+gate.id].enabled or crossing(decoder,gate,"boss"):
						issues.append("boss_broke_window:"+gate.id)
					continue
				if gate.kind=="through":
					decoder.allow_squeeze(gate.id,true)
					if not crossing(decoder,gate,"player"): issues.append("blocked squeeze "+gate.id)
					if crossing(decoder,gate,"boss"): issues.append("boss squeeze "+gate.id)
					decoder.allow_squeeze(gate.id,false)
				decoder.set_open(gate.id,true)
				for role in ["player","boss"]:
					if not crossing(decoder,gate,role): issues.append("open collision "+gate.id+" "+role)
				if not decoder.links["player:" + gate.id].enabled or not decoder.links["boss:" + gate.id].enabled:
					issues.append("gate_still_closed_after_smash:" + gate.id)
			for step in range(12):
				await physics_frame
			for rid in decoder.maps.values():
				NavigationServer3D.map_force_update(rid)
			for role in ["player", "boss"]:
				var actor: Dictionary = layout.spawn if role == "player" else layout.boss
				var start := _point(actor.position)
				for room in layout.rooms:
					var finish := _point(room.center)
					var path: PackedVector3Array = decoder.nav_path(role, start, finish)
					if path.is_empty() or path[path.size() - 1].distance_to(finish) > 0.25:
						issues.append(role + "_missing_room_" + room.id)
		var map_state := {}
		for role in ["player", "boss"]:
			if decoder.maps.has(role):
				var actor: Dictionary = decoder.data.layout.spawn if role == "player" else decoder.data.layout.boss
				var start := _point(actor.position)
				var closest := NavigationServer3D.map_get_closest_point(decoder.maps[role], start)
				map_state[role] = {"iterations": NavigationServer3D.map_get_iteration_id(decoder.maps[role]),
					"regions": NavigationServer3D.map_get_regions(decoder.maps[role]).size(),
					"links": NavigationServer3D.map_get_links(decoder.maps[role]).size(),
					"closest_distance": closest.distance_to(start),
					"self_path_points": decoder.nav_path(role, start, start).size()}
		decoder.clear_layout()
		# Exercise the playable interaction and damage path on the same saved package.
		var level = preload("res://full_pcg/godot/combat_level.gd").new()
		level.package_path = entry.path
		get_root().add_child(level)
		level.set_physics_process(false)
		for step in range(3): await physics_frame
		for gate in level.data.gates:
			if gate.kind != "window": continue
			var link: NavigationLink3D = level.links["player:"+gate.id]
			var from := link.start_position
			var to := link.end_position
			level.player_body.position = from + Vector3.UP * (float(level.combat.player.height_m)/2+.035)
			var direction := (to-from).normalized()
			level.boss_body.position = to + direction*.35 + Vector3.UP * float(level.combat.boss.height_m)/2
			await physics_frame
			if not level._clear_ray(level.player_body.position+Vector3.UP*.25,level.boss_body.position,level.player_body,level.boss_body):
				issues.append("live_window_visibility:"+gate.id)
			if level._clear_ray(level.player_body.position+Vector3.UP*.25,level.boss_body.position,level.player_body,level.boss_body,true):
				issues.append("live_window_contact:"+gate.id)
			var before: float = level.boss_hp
			level._fire_at(level.boss_body.position)
			if level.boss_hp >= before: issues.append("live_window_shot:"+gate.id)
			level._boss_smash(.1)
			if level.smash_id == gate.id: issues.append("live_smash_target_window:"+gate.id)
			level.boss_body.position = Vector3(-50,2,-50)
			await physics_frame
			if not level._start_vault(gate.id): issues.append("live_vault_start:"+gate.id)
			else:
				var apex := 0.0
				for step in range(48):
					level._step_vault(1./60.)
					apex = maxf(apex,level.player_body.position.y-level.vault_start.y)
					if level.vault_id == "": break
				if apex < .62: issues.append("live_vault_height:"+gate.id)
				if Vector2(level.player_body.position.x,level.player_body.position.z).distance_to(Vector2(to.x,to.z))>.03:
					issues.append("live_vault_landing:"+gate.id)
			break
		level.queue_free()
		rows.append({"seed": entry.seed, "rooms": entry.rooms, "map_state": map_state,
			"layout_hash": entry.layout_hash, "issues": issues, "ok": issues.is_empty()})
		decoder.queue_free()
		await process_frame
	var passed := true
	for row in rows:
		if not row.ok:
			passed = false
	var result := {"passed": passed, "count": rows.size(), "rows": rows,
		"scope": "Package load, role capsule crossings before and after opening, and all-open navigation"}
	var output := FileAccess.open(folder.path_join("godot_navigation.json"), FileAccess.WRITE)
	output.store_string(JSON.stringify(result, "  "))
	output.close()
	print(JSON.stringify({"passed": passed, "count": rows.size(), "failures": rows.filter(func(row): return not row.ok)}))
	quit(0 if passed else 1)

func crossing(decoder,gate,role) -> bool:
	var link = decoder.links[role+":"+gate.id]
	var body := CharacterBody3D.new()
	var col := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = decoder.data.role_radii[role]
	capsule.height = 1.8 if role=="player" else 2.2
	col.shape=capsule
	body.add_child(col)
	body.collision_layer=0
	body.collision_mask=3 if role=="player" else 5
	decoder.add_child(body)
	var start: Vector3=link.start_position
	var finish: Vector3=link.end_position
	body.position=start+Vector3.UP*(capsule.height/2+.035)
	var destination := body.position+(finish-start)
	body.move_and_collide(finish-start)
	var done := body.position.distance_to(destination)<.02
	body.free()
	return done

func ray_passes(decoder,id,offset,height) -> bool:
	for portal in decoder.data.layout.portals:
		if portal.id != id: continue
		var center: Vector3 = decoder.point(portal.center,height) + decoder.point(portal.tangent)*offset
		var normal: Vector3 = decoder.point(portal.normal)*.35
		var q := PhysicsRayQueryParameters3D.create(center-normal,center+normal,1|64)
		return decoder.get_world_3d().direct_space_state.intersect_ray(q).is_empty()
	return false

extends SceneTree

const Decoder = preload("res://full_pcg/godot/layout_decoder.gd")


func _initialize() -> void:
	call_deferred("_run")


func _point(coords: Array) -> Vector3:
	return Vector3(float(coords[0]), 0.0, float(coords[1]))


func _run() -> void:
	var manifest_path := "res://full_pcg_output/combat_godot/manifest.json"
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
				decoder.set_open(gate.id, true)
				if not decoder.links["player:" + gate.id].enabled or not decoder.links["boss:" + gate.id].enabled:
					issues.append("gate_still_closed_after_smash:" + gate.id)
			for step in range(12):
				await physics_frame
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
		rows.append({"seed": entry.seed, "rooms": entry.rooms, "map_state": map_state,
			"layout_hash": entry.layout_hash, "issues": issues, "ok": issues.is_empty()})
		decoder.queue_free()
		await process_frame
	var passed := true
	for row in rows:
		if not row.ok:
			passed = false
	var result := {"passed": passed, "count": rows.size(), "rows": rows,
		"scope": "Godot headless package load and all-open navigation; combat physics pending"}
	var output := FileAccess.open("res://full_pcg_output/combat_godot/godot_navigation.json", FileAccess.WRITE)
	output.store_string(JSON.stringify(result, "  "))
	output.close()
	print(JSON.stringify({"passed": passed, "count": rows.size(), "failures": rows.filter(func(row): return not row.ok)}))
	quit(0 if passed else 1)

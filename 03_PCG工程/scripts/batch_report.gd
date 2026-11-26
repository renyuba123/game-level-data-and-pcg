extends SceneTree

const Main = preload("res://scripts/main.gd")

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var main = Main.new()
	get_root().add_child(main)
	await physics_frame
	var issues := []
	var min_nav_polygons := 999999
	var min_door_width := INF
	var all_open_checks := 0
	for seed in range(1, 101):
		main._regenerate(seed)
		await physics_frame
		await physics_frame
		var level: Dictionary = main.level
		if not level["validation"]["ok"]:
			issues.append("seed %d geometry: %s" % [seed, level["validation"]["issues"]])
		for child in main.world.get_children():
			if child is NavigationRegion3D:
				var count: int = child.navigation_mesh.get_polygon_count()
				min_nav_polygons = mini(min_nav_polygons, count)
				if count == 0: issues.append("seed %d empty navigation %s" % [seed, child.name])
		for edge in level["edges"]:
			min_door_width = minf(min_door_width, edge["door_width_m"])
			if edge["kind"] == "normal":
				if not edge["player_nav_link"].enabled or not edge["boss_nav_link"].enabled:
					issues.append("seed %d normal link disabled" % seed)
			else:
				if edge["player_nav_link"].enabled or edge["boss_nav_link"].enabled:
					issues.append("seed %d special link enabled" % seed)
				main._open_for_boss(edge)
		if seed % 10 == 0:
			await create_timer(0.2).timeout
			for room in level["rooms"]:
				var start: Vector3 = main.model.room_center(level, room["id"]) + Vector3(0, 0.1, 0)
				var finish: Vector3 = main.exit_marker.position
				finish.y = 0.1
				for role in ["player", "boss"]:
					var nav_map: RID = main.player_nav_map if role == "player" else main.boss_nav_map
					var nav_layer: int = 1 if role == "player" else 2
					for block in level["blocks"]:
						if block["room"] == room["id"]:
							for edge in level["edges"]:
								if edge["a"] == room["id"] or edge["b"] == room["id"]:
									var link: NavigationLink3D = edge["%s_nav_link" % role]
									start = link.get_global_start_position() if edge["a"] == room["id"] else link.get_global_end_position()
									break
					var path: PackedVector3Array = NavigationServer3D.map_get_path(nav_map, start, finish, true, nav_layer)
					all_open_checks += 1
					if path.is_empty() or path[-1].distance_to(finish) > 1.0:
						issues.append("seed %d %s cannot reach exit from %s" %
							[seed, role, room["source_id"]])
	var report := {"tested": 100, "issues": issues, "min_nav_polygons": min_nav_polygons,
		"min_door_width_m": min_door_width, "all_open_path_checks": all_open_checks}
	var output = FileAccess.open("res://reports/batch_001_100.json", FileAccess.WRITE)
	output.store_string(JSON.stringify(report, "  "))
	output.close()
	print("BATCH_PROBE issues=%d checks=%d" % [issues.size(), all_open_checks])
	quit(0 if issues.is_empty() else 1)

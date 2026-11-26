extends SceneTree

const Main = preload("res://scripts/main.gd")

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var main = Main.new()
	get_root().add_child(main)
	await create_timer(0.2).timeout
	var results := []
	var issues := []
	for kind in ["through", "break"]:
		main._regenerate(42 if kind == "through" else 43)
		await create_timer(0.2).timeout
		var edge: Dictionary = {}
		for item in main.level["edges"]:
			if item["kind"] == kind:
				edge = item
				break
		var segment: PackedVector2Array = edge["shared_segment"]
		var tangent := (segment[1] - segment[0]).normalized()
		var normal := Vector2(-tangent.y, tangent.x)
		var a: Vector2 = main.level["rooms"][edge["a"]]["center"]
		var b: Vector2 = main.level["rooms"][edge["b"]]["center"]
		if normal.dot(b - a) < 0: normal = -normal
		var center: Vector3 = edge["position"]
		main.boss.position = center + Vector3(-normal.x * 1.1, 1.15, -normal.y * 1.1)
		main.player.position = center + Vector3(normal.x * 1.7, 1.0, normal.y * 1.7)
		main.boss_crossing_points.clear()
		main.boss.velocity = Vector3.ZERO
		var start: Vector3 = main.boss.position
		await create_timer(8.0).timeout
		var boss_room: int = main.model.closest_room(main.level, main.boss.position)
		var result := {"kind": kind, "opened": edge["boss_open"], "player_open": edge["player_open"],
			"boss_room": boss_room, "expected_room": edge["b"],
			"travel_m": start.distance_to(main.boss.position),
			"boss_position": str(main.boss.position),
			"player_position": str(main.player.position),
			"collisions": main.boss.get_slide_collision_count()}
		results.append(result)
		if not edge["boss_open"] or not edge["player_open"]:
			issues.append("%s was not opened" % kind)
		if boss_room != edge["b"]:
			issues.append("%s boss did not cross" % kind)
	var output = FileAccess.open("res://reports/chase.json", FileAccess.WRITE)
	output.store_string(JSON.stringify({"issues": issues, "results": results}, "  "))
	output.close()
	print(JSON.stringify({"issues": issues, "results": results}))
	quit(0 if issues.is_empty() else 1)

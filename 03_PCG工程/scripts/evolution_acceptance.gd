extends SceneTree
const Main = preload("res://scripts/main.gd")

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var results: Array = []
	var checked: Array = []
	var failures: Array = []
	for label in ["balanced", "exploration", "pressure"]:
		var path := "res://data/evolution/%s.json" % label
		if not FileAccess.file_exists(path):
			failures.append("Missing " + path)
			continue
		var candidate = JSON.parse_string(FileAccess.get_file_as_string(path))
		var key: String = candidate["evaluation"]["key"]
		if checked.has(key): continue
		checked.append(key)
		var main = Main.new()
		main.candidate_file = path
		get_root().add_child(main)
		main.set_physics_process(false)
		main.set_process(false)
		await create_timer(0.3).timeout
		var ids: Array = []
		for edge in main.level["edges"]:
			if edge["kind"] != "normal": ids.append(edge["id"])
		for id in ids:
			main._regenerate(42)
			await create_timer(0.3).timeout
			var edge: Dictionary = {}
			for e in main.level["edges"]:
				if e["id"] == id: edge = e
			var segment: PackedVector2Array = edge["shared_segment"]
			var tangent := (segment[1]-segment[0]).normalized()
			var normal := Vector2(-tangent.y,tangent.x)
			var a: Vector2 = main.level["rooms"][edge["a"]]["center"]
			var b: Vector2 = main.level["rooms"][edge["b"]]["center"]
			if normal.dot(b-a)<0: normal = -normal
			var center: Vector3 = edge["position"]
			main.boss.position = center + Vector3(-normal.x*0.72,1.15,-normal.y*0.72)
			main.player.position = center + Vector3(normal.x*0.85,1.0,normal.y*0.85)
			main.boss.velocity = Vector3.ZERO
			main.game_finished = false
			await physics_frame
			var blocked_before: bool = main.boss.test_move(main.boss.global_transform,Vector3(normal.x*2.2,0,normal.y*2.2))
			var player_blocked: bool = main.player.test_move(main.player.global_transform,Vector3(-normal.x*3.0,0,-normal.y*3.0))
			# Exercise real AI/collisions without ending this gate-only test on combat capture.
			for step in range(480):
				await physics_frame
				main._update_boss(1.0/60.0)
			var offset: Vector3 = main.boss.position-center
			var crossed: bool = Vector2(offset.x,offset.z).dot(normal)>0.25
			var passed: bool = blocked_before and player_blocked and edge["boss_open"] and edge["player_open"] and crossed
			var row := {"candidate":key,"preset":label,"edge":id,"kind":edge["kind"],
				"boss_blocked_initially":blocked_before,"player_blocked_without_interaction":player_blocked,
				"boss_open":edge["boss_open"],"player_open":edge["player_open"],"boss_crossed":crossed,"passed":passed}
			results.append(row)
			print(JSON.stringify(row))
			if not passed: failures.append("%s %s failed actual gate test" % [label,id])
		main.queue_free()
		await process_frame
	var output = FileAccess.open("res://evolution/acceptance.json",FileAccess.WRITE)
	output.store_string(JSON.stringify({"results":results,"failures":failures,"unique_candidates":checked.size()},"  "))
	output.close()
	quit(0 if failures.is_empty() else 1)

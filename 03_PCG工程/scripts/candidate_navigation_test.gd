extends SceneTree
const Main = preload("res://scripts/main.gd")

func _initialize() -> void:
	call_deferred("_run")

func _reachable(main: Node3D, map: RID, layers: int, start_room: int) -> Dictionary:
	var start: Vector3 = NavigationServer3D.map_get_closest_point(map, main.model.room_center(main.level,start_room))
	var reached: Array = []
	var missing: Array = []
	for room in main.level["rooms"]:
		var target: Vector3 = NavigationServer3D.map_get_closest_point(map,main.model.room_center(main.level,room["id"]))
		var path := NavigationServer3D.map_get_path(map,start,target,true,layers)
		var ok := not path.is_empty()
		if ok: ok = path[path.size()-1].distance_to(target)<0.15
		if ok: reached.append(room["source_id"])
		else: missing.append(room["source_id"])
	return {"reached":reached,"missing":missing}

func _run() -> void:
	var rows: Array = []
	var checked: Array = []
	var all_ok := true
	for label in ["balanced","exploration","pressure"]:
		var file := "res://data/evolution/%s.json" % label
		var candidate = JSON.parse_string(FileAccess.get_file_as_string(file))
		if not candidate is Dictionary:
			all_ok = false
			continue
		var key: String = candidate["evaluation"]["key"]
		if checked.has(key): continue
		checked.append(key)
		var main = Main.new()
		main.candidate_file = file
		get_root().add_child(main)
		main.set_physics_process(false)
		main.set_process(false)
		await create_timer(0.3).timeout
		var row := {"candidate":key,"label":label,
			"player_initial_without_squeeze_actions":_reachable(main,main.player_nav_map,1,main.level["spawn_room"]),
			"boss_initial":_reachable(main,main.boss_nav_map,2,main.level["boss_room"])}
		for edge in main.level["edges"]: main._open_for_boss(edge)
		await create_timer(0.3).timeout
		row["player_all_open"] = _reachable(main,main.player_nav_map,1,main.level["spawn_room"])
		row["boss_all_open"] = _reachable(main,main.boss_nav_map,2,main.level["boss_room"])
		row["passed"] = row["player_all_open"]["missing"].is_empty() and row["boss_all_open"]["missing"].is_empty()
		all_ok = all_ok and row["passed"]
		rows.append(row)
		main.queue_free()
		await process_frame
	var output = FileAccess.open("res://evolution/candidate_navigation.json",FileAccess.WRITE)
	output.store_string(JSON.stringify({"passed":all_ok,"results":rows,
		"note":"Initial player navigation excludes explicit squeeze actions; all-open reachability must cover every room."},"  "))
	output.close()
	print(JSON.stringify({"passed":all_ok,"results":rows}))
	quit(0 if all_ok else 1)

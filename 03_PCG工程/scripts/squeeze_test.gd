extends SceneTree
const Main = preload("res://scripts/main.gd")
func _initialize() -> void:
	call_deferred("_run")
func _run() -> void:
	var main = Main.new()
	main.candidate_file = "res://data/evolution/balanced.json"
	get_root().add_child(main)
	main.set_physics_process(false)
	main.set_process(false)
	await create_timer(0.2).timeout
	var result := {"passed":false}
	for edge in main.level["edges"]:
		if edge["kind"] != "through": continue
		var span: PackedVector2Array = edge["shared_segment"]
		var tangent := (span[1]-span[0]).normalized()
		var normal := Vector3(-tangent.y,0,tangent.x)
		var center: Vector3 = edge["position"]+Vector3(0,1,0)
		main.player.position = center+normal*0.72
		await physics_frame
		main._try_squeeze()
		if main.active_squeeze.is_empty(): continue
		if main.active_squeeze["id"] != edge["id"]:
			main.active_squeeze = {}
			continue
		main._process(0.7)
		await physics_frame
		var crossed: bool = normal.dot(main.player.position-center)<-0.5
		var blocked_back: bool = main.player.test_move(main.player.global_transform,normal*1.4)
		result = {"edge":edge["id"],"crossed_with_interaction":crossed,"blocked_without_second_interaction":blocked_back,
			"boss_open":edge["boss_open"],"player_open":edge["player_open"],
			"passed":crossed and blocked_back and not edge["boss_open"] and not edge["player_open"]}
		break
	var file = FileAccess.open("res://evolution/squeeze_test.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(result,"  "))
	file.close()
	print(JSON.stringify(result))
	quit(0 if result["passed"] else 1)

extends SceneTree
## Opens an archived Layout directly in the shared playable combat scene.

const LEVEL = preload("res://scenes/CombatFullPCG.tscn")

func _initialize() -> void:
	call_deferred("_open_candidate")

func _open_candidate() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() < 2 or args.size() > 3 or (args.size() == 3 and args[2] != "--verify"):
		push_error("Expected package.json config_snapshot.json [--verify]")
		quit(2)
		return
	var config = JSON.parse_string(FileAccess.get_file_as_string(args[1]))
	if not config is Dictionary or not config.get("combat") is Dictionary or float(config.get("layout_scale", 0)) <= 0:
		push_error("Invalid archived combat configuration")
		quit(2)
		return
	var level = LEVEL.instantiate()
	level.package_path = args[0]
	level.layout_scale = float(config.layout_scale)
	level.protocol_override = config.combat
	root.add_child(level)
	if level.data.is_empty() or not is_instance_valid(level.player_body) or not is_instance_valid(level.boss_body):
		push_error("Candidate did not load")
		quit(3)
		return
	current_scene = level
	get_root().title = "Evolution Viewer | Seed %s | %s" % [
		str(level.data.layout.seed), str(level.data.layout_hash).left(10)]
	if args.size() == 3:
		level.set_physics_process(false)
		await physics_frame
		var origin: Array = level.data.layout.spawn.position
		var observed := Vector2(level.player_body.position.x, level.player_body.position.z)
		if not observed.is_equal_approx(Vector2(origin[0], origin[1]) * level.layout_scale) or level.combat != config.combat:
			push_error("Candidate did not use the archived scale or combat protocol")
			quit(4)
			return
		print("VIEWER_READY ", level.data.layout_hash, " scale=", level.layout_scale,
			" rooms=", level.data.layout.rooms.size(), " portals=", level.data.layout.portals.size())
		quit()

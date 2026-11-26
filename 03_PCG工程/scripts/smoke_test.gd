extends SceneTree

const Main = preload("res://scripts/main.gd")

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var main = Main.new()
	get_root().add_child(main)
	for frame in range(10):
		await physics_frame
	var floors := 0
	var walls := 0
	var nav_regions := 0
	for child in main.world.get_children():
		if child.name.begins_with("Floor_"): floors += 1
		if child.name.begins_with("Wall_"): walls += 1
		if child.name.begins_with("Nav_"): nav_regions += 1
	var report := {"validation": main.level["validation"], "floors": floors,
		"walls": walls, "nav_regions": nav_regions,
		"player_position": main.player.position, "boss_position": main.boss.position}
	var output = FileAccess.open("res://reports/smoke.json", FileAccess.WRITE)
	output.store_string(JSON.stringify(report, "  "))
	output.close()
	print(JSON.stringify(report))
	quit(0 if floors == 11 and nav_regions == 22 else 1)

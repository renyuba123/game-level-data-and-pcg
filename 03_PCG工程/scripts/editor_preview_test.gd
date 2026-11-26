extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var scene: PackedScene = load("res://scenes/Main.tscn")
	var main: Node3D = scene.instantiate()
	main.candidate_file = ""
	main.map_seed = 42
	get_root().add_child(main)
	await process_frame
	var first := main.get_node_or_null("EditorLayoutPreview_42")
	var initial_preview: bool = is_instance_valid(first)
	var first_count := first.get_child_count() if first else 0
	main.map_seed = 43
	await process_frame
	await process_frame
	var second := main.get_node_or_null("EditorLayoutPreview_43")
	var report := {"editor_hint": Engine.is_editor_hint(), "initial_preview": initial_preview,
		"initial_children": first_count, "seed_change_preview": second != null,
		"updated_children": second.get_child_count() if second else 0}
	var file = FileAccess.open("res://reports/editor_preview_test.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "  "))
	file.close()
	print(JSON.stringify(report))
	quit(0 if report["editor_hint"] and report["initial_preview"] and report["seed_change_preview"] else 1)

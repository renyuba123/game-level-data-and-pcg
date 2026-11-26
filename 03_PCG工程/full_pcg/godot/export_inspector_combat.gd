extends SceneTree
## Resolve exported defaults and saved overrides through the same code as Main.


func _initialize() -> void:
	var main = preload("res://scenes/Main.tscn").instantiate()
	var combat: Dictionary = main._combat_protocol()
	var path := OS.get_environment("RATKING_INSPECTOR_SNAPSHOT")
	var output := FileAccess.open(path, FileAccess.WRITE)
	if output == null or combat.is_empty():
		main.free()
		quit(2)
		return
	output.store_string(JSON.stringify({"seed": main.map_seed, "layout_scale": main.map_size,
		"combat": combat}, "  ", true, true))
	output.close()
	main.free()
	quit(0)

extends SceneTree
## Four-panel vector comparison: source DXF walls and three generated seeds.

const Model = preload("res://scripts/pcg_model.gd")

func _initialize() -> void: call_deferred("_run")

func _run() -> void:
	var source: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/source_profile.json"))
	var model = Model.new()
	var selected := []
	var seen := {}
	for seed in range(1, 101):
		var candidate: Dictionary = model.generate_level(seed, source)
		var key := str(candidate["branch_order"])
		if not seen.has(key):
			seen[key] = true
			selected.append(seed)
		if selected.size() == 3: break
	var svg := '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="460" viewBox="0 0 1600 460">'
	svg += '<rect width="1600" height="460" fill="#17202c"/>'
	for panel in range(4):
		var min_x := INF
		var min_y := INF
		var max_x := -INF
		var max_y := -INF
		var points := []
		var level: Dictionary = {}
		if panel == 0:
			for wall in source["wall_segments"]:
				points.append(Vector2(wall["start_m"][0], wall["start_m"][1]))
				points.append(Vector2(wall["end_m"][0], wall["end_m"][1]))
		else:
			level = model.generate_level(selected[panel - 1], source)
			for room in level["rooms"]:
				for p in room["polygon"]: points.append(p)
		for p in points:
			min_x = minf(min_x, p.x)
			max_x = maxf(max_x, p.x)
			min_y = minf(min_y, p.y)
			max_y = maxf(max_y, p.y)
		var scale: float = minf(350.0 / (max_x - min_x), 350.0 / (max_y - min_y))
		var left := panel * 400.0 + 25.0
		var top := 65.0
		svg += '<rect x="%d" y="15" width="380" height="430" rx="8" fill="#243146" stroke="#52677e"/>' % (panel * 400 + 10)
		svg += '<text x="%d" y="44" fill="#f5f7fa" font-family="Arial" font-size="19">%s</text>' % [
			panel * 400 + 25, "DXF 原始墙线" if panel == 0 else "生成 Seed %d" % selected[panel - 1]]
		if panel == 0:
			for wall in source["wall_segments"]:
				var a := Vector2(wall["start_m"][0], wall["start_m"][1])
				var b := Vector2(wall["end_m"][0], wall["end_m"][1])
				svg += '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#e5edf6" stroke-width="1.5"/>' % [
					left + (a.x - min_x) * scale, top + (max_y - a.y) * scale,
					left + (b.x - min_x) * scale, top + (max_y - b.y) * scale]
		else:
			for room in level["rooms"]:
				var coords := ""
				for p in room["polygon"]:
					coords += "%.2f,%.2f " % [left + (p.x - min_x) * scale, top + (max_y - p.y) * scale]
				svg += '<polygon points="%s" fill="#527187" stroke="#dce8f2" stroke-width="2"/>' % coords
				var c: Vector2 = room["center"]
				svg += '<text x="%.2f" y="%.2f" text-anchor="middle" fill="#ffffff" font-family="Arial" font-size="12">%s</text>' % [
					left + (c.x - min_x) * scale, top + (max_y - c.y) * scale, room["source_id"]]
			for block in level["blocks"]:
				var c: Vector2 = block["position"]
				svg += '<circle cx="%.2f" cy="%.2f" r="%.2f" fill="#b69356" stroke="#f6d383"/>' % [
					left + (c.x - min_x) * scale, top + (max_y - c.y) * scale,
					block["radius"] * scale]
	svg += '</svg>'
	var file = FileAccess.open("res://reports/layout_comparison.svg", FileAccess.WRITE)
	file.store_string(svg)
	file.close()
	print("wrote layout_comparison.svg")
	quit()

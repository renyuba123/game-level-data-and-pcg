@tool
extends RefCounted
## Rat King inspired, source-proportioned room grammar. Coordinates are metres in X/Z.

const ROOM_IDS := ["R05", "R03", "R01", "R02", "R04", "R06", "R07", "R08", "R10", "R09", "R11"]
const ROOM_KINDS := ["hub", "obstacle_arena", "lower_chamber", "branch_connector",
	"small_side_room", "small_side_room", "long_corridor", "side_chamber",
	"compact_side_room", "vertical_connector", "chamfered_terminal"]
const PAIRS := [[0, 1], [0, 6], [0, 4], [0, 5], [0, 3],
	[1, 2], [2, 3], [4, 5], [1, 4], [6, 7],
	[7, 8], [6, 9], [9, 10], [9, 7], [9, 8]]
const BREAK_CANDIDATES := [6, 7, 8, 13, 14]
const THROUGH_COUNT := 6
const BREAK_COUNT := 3
const PLAYER_RADIUS := 0.35
const BOSS_RADIUS := 0.58

var rng := RandomNumberGenerator.new()


func generate_level(map_seed: int, source: Dictionary, genes: Dictionary = {}) -> Dictionary:
	rng.seed = map_seed
	var reference := _source_sizes(source)
	var hw: float = maxf(6.0, _dimension(reference["R05"].x, "R05_width", genes))
	var hh: float = maxf(3.2, _dimension(reference["R05"].y, "R05_height", genes))
	var aw: float = _dimension(reference["R03"].x, "R03_width", genes)
	var ah: float = maxf(_dimension(reference["R03"].y, "R03_height", genes), hh + 1.35)
	var arena_bottom: float = hh - 0.5
	var lower_w: float = _dimension(reference["R01"].x, "R01_width", genes)
	var lower_h: float = maxf(2.4, _dimension(reference["R01"].y, "R01_height", genes))
	var branch_w: float = minf(_dimension(reference["R02"].x, "R02_width", genes), hw - 2.4)
	var branch_h: float = _dimension(reference["R02"].y, "R02_height", genes)
	var upper1_w: float = maxf(1.85, _dimension(reference["R04"].x, "R04_width", genes))
	var upper1_h: float = maxf(2.0, _dimension(reference["R04"].y, "R04_height", genes))
	var upper2_w: float = _dimension(reference["R06"].x, "R06_width", genes)
	var upper2_h: float = _dimension(reference["R06"].y, "R06_height", genes)
	var spine_w: float = clampf(_dimension(reference["R07"].y, "R07_height", genes), 1.45, hh * 0.52)
	var side1_w: float = _dimension(reference["R08"].x, "R08_width", genes)
	var side1_h: float = _dimension(reference["R08"].y, "R08_height", genes)
	var side2_w: float = _dimension(reference["R10"].x, "R10_width", genes)
	var side2_h: float = maxf(1.7, _dimension(reference["R10"].y, "R10_height", genes))
	var spine_l: float = maxf(_dimension(reference["R07"].x, "R07_width", genes), maxf(side1_w, side2_w) + 0.9)
	var connector_w: float = maxf(1.85, _dimension(reference["R09"].x, "R09_width", genes))
	var connector_h: float = maxf(_dimension(reference["R09"].y, "R09_height", genes), spine_w + side1_h + 1.7)
	var terminal_w: float = _dimension(reference["R11"].x, "R11_width", genes)
	var terminal_h: float = minf(_dimension(reference["R11"].y, "R11_height", genes), connector_h - 0.6)
	var spine_end := hw + spine_l
	var side1_end := spine_w + side1_h
	var terminal_z := (connector_h - terminal_h) / 2.0
	var slope_cut: float = genes.get("slope_cut", rng.randf_range(1.25, 2.0))
	var bevel: float = genes.get("bevel", rng.randf_range(0.35, 0.65))
	var swap_upper: bool = genes.get("swap_upper", rng.randi_range(0, 1) == 1)
	var swap_side: bool = genes.get("swap_side", rng.randi_range(0, 1) == 1)
	var upper4: PackedVector2Array
	var upper5: PackedVector2Array
	if swap_upper:
		upper5 = _rect(0, -upper2_h, upper2_w, 0)
		upper4 = _rect(upper2_w, -upper1_h, upper2_w + upper1_w, 0)
	else:
		upper4 = _rect(0, -upper1_h, upper1_w, 0)
		upper5 = _rect(upper1_w, -upper2_h, upper1_w + upper2_w, 0)
	var side7: PackedVector2Array
	var side8: PackedVector2Array
	if swap_side:
		side8 = _rect(spine_end - side2_w, spine_w, spine_end, spine_w + side2_h)
		side7 = _rect(spine_end - side1_w, spine_w + side2_h,
			spine_end, spine_w + side2_h + side1_h)
	else:
		side7 = _rect(spine_end - side1_w, spine_w, spine_end, side1_end)
		side8 = _rect(spine_end - side2_w, side1_end, spine_end, side1_end + side2_h)
	var raw_polygons: Array = [
		PackedVector2Array([Vector2(0, 0), Vector2(hw, 0),
			Vector2(hw, spine_w + 0.25), Vector2(hw - slope_cut, hh), Vector2(0, hh)]),
		_rect(-aw, arena_bottom - ah, 0, arena_bottom),
		_rect(-lower_w, arena_bottom, 0, arena_bottom + lower_h),
		_rect(0, hh, branch_w, hh + branch_h),
		upper4,
		upper5,
		_rect(hw, 0, spine_end, spine_w),
		side7,
		side8,
		_rect(spine_end, 0, spine_end + connector_w, connector_h),
		PackedVector2Array([Vector2(spine_end + connector_w, terminal_z),
			Vector2(spine_end + connector_w + terminal_w - bevel, terminal_z),
			Vector2(spine_end + connector_w + terminal_w, terminal_z + bevel),
			Vector2(spine_end + connector_w + terminal_w, terminal_z + terminal_h - bevel),
			Vector2(spine_end + connector_w + terminal_w - bevel, terminal_z + terminal_h),
			Vector2(spine_end + connector_w, terminal_z + terminal_h)])
	]
	var mirror_x: bool = rng.randi_range(0, 1) == 1
	var mirror_z: bool = rng.randi_range(0, 1) == 1
	var quarter_turn: int = rng.randi_range(0, 3)
	var rooms: Array = []
	for i in range(raw_polygons.size()):
		var polygon := PackedVector2Array()
		for point in raw_polygons[i]:
			polygon.append(_transform_point(point, mirror_x, mirror_z, quarter_turn))
		rooms.append({"id": i, "source_id": ROOM_IDS[i], "kind": ROOM_KINDS[i],
			"polygon": polygon, "center": _polygon_centroid(polygon),
			"source_choice": _source_choice(source, ROOM_IDS[i])})
	var pairs: Array = PAIRS.duplicate(true)
	for pair in pairs:
		for j in range(2):
			if swap_upper:
				if pair[j] == 4: pair[j] = 5
				elif pair[j] == 5: pair[j] = 4
			if swap_side:
				if pair[j] == 7: pair[j] = 8
				elif pair[j] == 8: pair[j] = 7
	var break_indices: Array = []
	var candidates: Array = BREAK_CANDIDATES.duplicate()
	_shuffle(candidates)
	if not genes.is_empty():
		candidates.sort_custom(func(a, b): return float(genes.get("priority_%d" % a, a)) < float(genes.get("priority_%d" % b, b)))
	for index in candidates:
		if break_indices.size() == BREAK_COUNT: break
		var proposed := break_indices.duplicate()
		proposed.append(index)
		if _connected_without(pairs, proposed): break_indices.append(index)
	assert(break_indices.size() == BREAK_COUNT)
	var available: Array = range(pairs.size())
	for index in break_indices: available.erase(index)
	_shuffle(available)
	if not genes.is_empty():
		available.sort_custom(func(a, b): return float(genes.get("priority_%d" % a, a)) < float(genes.get("priority_%d" % b, b)))
	var through_indices: Array = available.slice(0, THROUGH_COUNT)
	var removed: int = int(genes.get("remove_normal", -1))
	var excluded: Array = break_indices.duplicate()
	excluded.append(removed)
	if through_indices.has(removed) or break_indices.has(removed) or not _connected_without(pairs, excluded):
		removed = -1
	var edges: Array = []
	for i in range(pairs.size()):
		if i == removed: continue
		var pair: Array = pairs[i]
		var shared: PackedVector2Array = _shared_segment(rooms[pair[0]]["polygon"], rooms[pair[1]]["polygon"])
		var length: float = shared[0].distance_to(shared[1]) if shared.size() == 2 else 0.0
		var kind := "normal"
		if break_indices.has(i): kind = "break"
		elif through_indices.has(i): kind = "through"
		var width: float = minf(2.4, length - 0.12)
		width = maxf(1.35, width * float(genes.get("door_width_%d" % i, 1.0)))
		var fraction: float = float(genes.get("door_offset_%d" % i, 0.5))
		var margin: float = (width / 2.0 + 0.06) / maxf(length, 0.001)
		fraction = clampf(fraction, margin, 1.0 - margin)
		var anchor := shared[0].lerp(shared[1], fraction) if shared.size() == 2 else Vector2.ZERO
		edges.append({"id": "E%02d" % (i + 1), "a": pair[0], "b": pair[1],
			"kind": kind, "shared_segment": shared,
			"door_width_m": width, "door_anchor": anchor, "squeeze_width_m": 0.9,
			"boss_open": kind == "normal", "player_open": kind == "normal"})
	var blocks: Array = []
	var block_refs: Array = source.get("blocks", [])
	for index in range(mini(2, block_refs.size())):
		var room_id := 1 if index == 0 else 10
		var center: Vector2 = rooms[room_id]["center"]
		var radius: float = clampf(float(block_refs[index].get("radius_m", 0.5)), 0.3, 0.8)
		var offset := Vector2(rng.randf_range(-0.35, 0.35), rng.randf_range(-0.35, 0.35))
		if index == 1:
			var poly: PackedVector2Array = rooms[room_id]["polygon"]
			offset = (poly[poly.size() - 1] - poly[0]).normalized() * 1.35
		if not genes.is_empty():
			if index == 0:
				offset = Vector2(float(genes.get("block_x", 0.0)), float(genes.get("block_y", 0.0)))
			else:
				offset = offset.normalized() * float(genes.get("block_terminal_offset", 1.35))
		blocks.append({"id": index, "room": room_id,
			"position": center + offset,
			"radius": radius})
	var result := {"schema_version": 2, "seed": map_seed, "rooms": rooms, "edges": edges,
		"branch_order": {"upper_swapped": swap_upper, "side_swapped": swap_side},
		"blocks": blocks, "genes": genes.duplicate(true), "spawn_room": int(genes.get("spawn_room", 2)), "boss_room": int(genes.get("boss_room", 9)), "exit_room": 10,
		"source_dxf_sha256": source.get("source_dxf_sha256", ""),
		"source_graph_sha256": source.get("source_graph_sha256", ""),
		"source_connection_counts": {"through": 6, "break": 3, "block": 2}}
	result["validation"] = validate_level(result)
	return result


func validate_level(level: Dictionary) -> Dictionary:
	var rooms: Array = level["rooms"]
	var edges: Array = level["edges"]
	var issues: Array = []
	var areas: Array = []
	var long_spaces := 0
	var irregular_spaces := 0
	for room in rooms:
		var poly: PackedVector2Array = room["polygon"]
		var area: float = absf(_area(poly))
		areas.append(area)
		if area < 2.0: issues.append("room %s has too little area" % room["source_id"])
		var bounds := _bounds(poly)
		if maxf(bounds.size.x, bounds.size.y) / maxf(0.01, minf(bounds.size.x, bounds.size.y)) > 2.8:
			long_spaces += 1
		if poly.size() > 4: irregular_spaces += 1
	for i in range(rooms.size()):
		for j in range(i + 1, rooms.size()):
			for intersection in Geometry2D.intersect_polygons(rooms[i]["polygon"], rooms[j]["polygon"]):
				if absf(_area(intersection)) > 0.001:
					issues.append("room overlap %d/%d" % [i, j])
	var kinds := {"normal": 0, "through": 0, "break": 0}
	for edge in edges:
		kinds[edge["kind"]] += 1
		if edge["shared_segment"].size() != 2 or edge["door_width_m"] < 1.35:
			issues.append("door %s has no usable shared wall" % edge["id"])
		elif edge["door_width_m"] > edge["shared_segment"][0].distance_to(edge["shared_segment"][1]) - 0.119:
			issues.append("door %s exceeds shared wall" % edge["id"])
	if level["spawn_room"] == level["boss_room"] or room_center(level, level["spawn_room"]).distance_to(room_center(level, level["boss_room"])) < 4.0:
		issues.append("unsafe starting separation")
	if not _connected_without(_edge_pairs(edges), _break_indices(edges)):
		issues.append("initial player graph disconnected")
	if long_spaces < 2: issues.append("missing long connectors")
	if irregular_spaces < 2: issues.append("missing sloped or chamfered spaces")
	if kinds["through"] != THROUGH_COUNT or kinds["break"] != BREAK_COUNT:
		issues.append("wrong semantic connection counts")
	var distinct_areas := {}
	for area in areas: distinct_areas[roundi(area)] = true
	if distinct_areas.size() < 5: issues.append("insufficient room size variety")
	return {"ok": issues.is_empty(), "issues": issues, "room_count": rooms.size(),
		"edge_count": edges.size(), "connection_counts": kinds,
		"initial_player_loops": edges.size() - BREAK_COUNT - rooms.size() + 1,
		"all_open_loops": edges.size() - rooms.size() + 1,
		"long_space_count": long_spaces, "irregular_space_count": irregular_spaces,
		"area_min_m2": areas.min(), "area_max_m2": areas.max()}


func room_center(level: Dictionary, id: int) -> Vector3:
	var p: Vector2 = level["rooms"][id]["center"]
	return Vector3(p.x, 0, p.y)


func door_center(edge: Dictionary) -> Vector3:
	var segment: PackedVector2Array = edge["shared_segment"]
	var p: Vector2 = edge.get("door_anchor", (segment[0] + segment[1]) / 2.0)
	return Vector3(p.x, 0, p.y)


func closest_room(level: Dictionary, position: Vector3) -> int:
	var point := Vector2(position.x, position.z)
	for room in level["rooms"]:
		if Geometry2D.is_point_in_polygon(point, room["polygon"]): return room["id"]
	var nearest := 0
	var distance := INF
	for room in level["rooms"]:
		var d: float = point.distance_squared_to(room["center"])
		if d < distance:
			distance = d
			nearest = room["id"]
	return nearest


func next_edge_toward(level: Dictionary, from_room: int, to_room: int) -> Dictionary:
	if from_room == to_room: return {}
	var queue: Array = [from_room]
	var previous := {from_room: -1}
	var previous_edge := {}
	while not queue.is_empty():
		var current: int = queue.pop_front()
		if current == to_room: break
		for edge in level["edges"]:
			var other := -1
			if edge["a"] == current: other = edge["b"]
			elif edge["b"] == current: other = edge["a"]
			if other >= 0 and not previous.has(other):
				previous[other] = current
				previous_edge[other] = edge
				queue.append(other)
	if not previous.has(to_room): return {}
	var step := to_room
	while previous[step] != from_room: step = previous[step]
	return previous_edge[step]


func _source_sizes(source: Dictionary) -> Dictionary:
	var sizes := {}
	for room in source.get("convex_rooms", []):
		var min_x := INF
		var min_y := INF
		var max_x := -INF
		var max_y := -INF
		for pair in room["polygon_m"]:
			min_x = minf(min_x, float(pair[0]))
			max_x = maxf(max_x, float(pair[0]))
			min_y = minf(min_y, float(pair[1]))
			max_y = maxf(max_y, float(pair[1]))
		sizes[room["room_id"]] = Vector2(max_x - min_x, max_y - min_y)
	return sizes


func _source_choice(source: Dictionary, ref_id: String) -> float:
	for room in source.get("convex_rooms", []):
		if room["room_id"] == ref_id: return float(room["choice"])
	return 0.0


func _scaled(value: float) -> float:
	return value * rng.randf_range(0.88, 1.12)


func _rect(x0: float, y0: float, x1: float, y1: float) -> PackedVector2Array:
	return PackedVector2Array([Vector2(x0, y0), Vector2(x1, y0),
		Vector2(x1, y1), Vector2(x0, y1)])


func _transform_point(point: Vector2, mirror_x: bool, mirror_z: bool, turns: int) -> Vector2:
	var result := point
	if mirror_x: result.x = -result.x
	if mirror_z: result.y = -result.y
	for _i in range(turns): result = Vector2(-result.y, result.x)
	return Vector2(snappedf(result.x, 0.001), snappedf(result.y, 0.001))


func _polygon_centroid(poly: PackedVector2Array) -> Vector2:
	var sum := Vector2.ZERO
	for point in poly: sum += point
	return sum / poly.size()


func _bounds(poly: PackedVector2Array) -> Rect2:
	var rect := Rect2(poly[0], Vector2.ZERO)
	for point in poly: rect = rect.expand(point)
	return rect


func _area(poly: PackedVector2Array) -> float:
	var value := 0.0
	for i in range(poly.size()): value += poly[i].cross(poly[(i + 1) % poly.size()])
	return value / 2.0


func _shared_segment(a: PackedVector2Array, b: PackedVector2Array) -> PackedVector2Array:
	var best := PackedVector2Array()
	var best_length := 0.0
	for i in range(a.size()):
		var start: Vector2 = a[i]
		var end: Vector2 = a[(i + 1) % a.size()]
		var delta := end - start
		var length := delta.length()
		if length < 0.001: continue
		var direction := delta / length
		for j in range(b.size()):
			var c: Vector2 = b[j]
			var d: Vector2 = b[(j + 1) % b.size()]
			if absf(direction.cross(c - start)) > 0.01 or absf(direction.cross(d - start)) > 0.01:
				continue
			var low: float = maxf(0.0, minf((c - start).dot(direction), (d - start).dot(direction)))
			var high: float = minf(length, maxf((c - start).dot(direction), (d - start).dot(direction)))
			if high - low > best_length:
				best_length = high - low
				best = PackedVector2Array([start + direction * low, start + direction * high])
	return best


func _edge_pairs(edges: Array) -> Array:
	var result: Array = []
	for edge in edges: result.append([edge["a"], edge["b"]])
	return result


func _break_indices(edges: Array) -> Array:
	var result: Array = []
	for i in range(edges.size()):
		if edges[i]["kind"] == "break": result.append(i)
	return result


func _connected_without(pairs: Array, removed: Array) -> bool:
	var seen: Array = [0]
	var queue: Array = [0]
	while not queue.is_empty():
		var room: int = queue.pop_front()
		for i in range(pairs.size()):
			if removed.has(i): continue
			var other := -1
			if pairs[i][0] == room: other = pairs[i][1]
			elif pairs[i][1] == room: other = pairs[i][0]
			if other >= 0 and not seen.has(other):
				seen.append(other)
				queue.append(other)
	return seen.size() == ROOM_IDS.size()


func _shuffle(items: Array) -> void:
	for index in range(items.size() - 1, 0, -1):
		var swap := rng.randi_range(0, index)
		var temp = items[index]
		items[index] = items[swap]
		items[swap] = temp


func _dimension(value: float, key: String, genes: Dictionary) -> float:
	return value * float(genes[key]) if genes.has(key) else _scaled(value)


func room_wall_segments(level: Dictionary, room: Dictionary) -> Array:
	var segments: Array = []
	var polygon: PackedVector2Array = room["polygon"]
	for side in range(polygon.size()):
		var a: Vector2 = polygon[side]
		var b: Vector2 = polygon[(side + 1) % polygon.size()]
		var length := a.distance_to(b)
		var direction := (b - a) / length
		var openings: Array = []
		for edge in level["edges"]:
			if edge["a"] != room["id"] and edge["b"] != room["id"]: continue
			var door := door_center(edge)
			var mid := Vector2(door.x, door.z)
			if absf(direction.cross(mid - a)) > 0.015: continue
			var along: float = (mid - a).dot(direction)
			if along < -0.01 or along > length + 0.01: continue
			var half_width: float = edge["door_width_m"] / 2.0
			openings.append([maxf(0.0, along - half_width), minf(length, along + half_width)])
		openings.sort_custom(func(first, second): return first[0] < second[0])
		var cursor := 0.0
		for gap in openings:
			if gap[0] > cursor + 0.01: segments.append([a + direction * cursor, a + direction * gap[0]])
			cursor = maxf(cursor, gap[1])
		if cursor < length - 0.01: segments.append([a + direction * cursor, b])
	return segments


func wall_segments(level: Dictionary, opened: Array = []) -> Array:
	var segments: Array = []
	for room in level["rooms"]: segments.append_array(room_wall_segments(level, room))
	for edge in level["edges"]:
		if edge["kind"] == "normal" or opened.has(edge["id"]): continue
		var shared: PackedVector2Array = edge["shared_segment"]
		var tangent: Vector2 = (shared[1] - shared[0]).normalized()
		var d := door_center(edge)
		var center := Vector2(d.x, d.z)
		var width: float = edge["door_width_m"]
		if edge["kind"] == "break":
			segments.append([center - tangent * width / 2, center + tangent * width / 2])
		else:
			var narrow: float = edge.get("squeeze_width_m", 0.9)
			segments.append([center - tangent * width / 2, center - tangent * narrow / 2])
			segments.append([center + tangent * narrow / 2, center + tangent * width / 2])
	return segments


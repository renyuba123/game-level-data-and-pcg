@tool
extends Node3D
## DXF-proportioned polygon blockout. WASD move; E/gamepad A squeeze; R/T seeds.

const Model = preload("res://scripts/pcg_model.gd")
const WORLD_LAYER := 4
const PLAYER_GATE_LAYER := 1
const BOSS_GATE_LAYER := 2

@export var map_seed := 42:
	set(value):
		map_seed = value
		if Engine.is_editor_hint() and is_inside_tree() and not source.is_empty():
			call_deferred("_rebuild_editor_preview")
@export_file("*.json") var candidate_file := "":
	set(value):
		candidate_file = value
		if Engine.is_editor_hint() and is_inside_tree() and not source.is_empty():
			call_deferred("_rebuild_editor_preview")
@export var player_speed := 5.0
@export var boss_speed := 3.25
@export var player_squeeze_seconds := 0.65
@export var boss_through_seconds := 2.0
@export var boss_break_seconds := 3.0

@export_group("Evolution")
@export_enum("Seed layout", "Balanced", "Exploration", "Pressure") var evolution_preset := 0:
	set(value):
		evolution_preset = value
		if value == 0: candidate_file = ""
		else:
			var names := ["", "balanced", "exploration", "pressure"]
			var path := "res://data/evolution/%s.json" % names[value]
			if FileAccess.file_exists(path): candidate_file = path
			else: push_warning("Candidate not yet available: " + path)
@export_multiline var evolution_status := "No search started"
@export_multiline var candidate_summary := "Seed-generated layout"
@export_tool_button("Run 16-candidate pilot") var evolution_pilot_button = _start_evolution_pilot
@export_tool_button("Run / resume full search") var evolution_search_button = _start_evolution_search
@export_tool_button("Refresh candidate preview") var evolution_refresh_button = _refresh_evolution
var evolution_poll_seconds := 0.0
var boss_crossing_points: Array[Vector3] = []

var model = Model.new()
var source: Dictionary
var level: Dictionary
var world: Node3D
var player: CharacterBody3D
var boss: CharacterBody3D
var exit_marker: MeshInstance3D
var camera: Camera3D
var hud: Label
var player_nav_map: RID
var boss_nav_map: RID
var active_squeeze: Dictionary = {}
var squeeze_remaining := 0.0
var game_finished := false
var result_text := ""


func _ready() -> void:
	var parsed = JSON.parse_string(FileAccess.get_file_as_string("res://data/source_profile.json"))
	if not parsed is Dictionary:
		push_error("Missing or invalid source_profile.json")
		return
	source = parsed
	if Engine.is_editor_hint():
		_rebuild_editor_preview()
		return
	_register_inputs()
	player_nav_map = NavigationServer3D.map_create()
	boss_nav_map = NavigationServer3D.map_create()
	NavigationServer3D.map_set_cell_size(player_nav_map, 0.05)
	NavigationServer3D.map_set_cell_size(boss_nav_map, 0.05)
	NavigationServer3D.map_set_active(player_nav_map, true)
	NavigationServer3D.map_set_active(boss_nav_map, true)
	_create_camera_and_light()
	_create_hud()
	_regenerate(map_seed)


func _rebuild_editor_preview() -> void:
	if not Engine.is_editor_hint() or not is_inside_tree() or source.is_empty():
		return
	if is_instance_valid(world):
		world.free()
	world = Node3D.new()
	world.name = "EditorLayoutPreview_%d" % map_seed
	add_child(world)
	level = _candidate_level(map_seed)
	if not level["validation"]["ok"]:
		push_error("Invalid editor preview: %s" % str(level["validation"]["issues"]))
		return
	_build_geometry()
	_add_evolution_label()


func _exit_tree() -> void:
	if player_nav_map.is_valid(): NavigationServer3D.free_rid(player_nav_map)
	if boss_nav_map.is_valid(): NavigationServer3D.free_rid(boss_nav_map)


func _register_inputs() -> void:
	for action in ["pcg_interact", "pcg_regenerate", "pcg_repeat"]:
		if not InputMap.has_action(action): InputMap.add_action(action)
	var interact := InputEventKey.new()
	interact.physical_keycode = KEY_E
	InputMap.action_add_event("pcg_interact", interact)
	var joy := InputEventJoypadButton.new()
	joy.button_index = JOY_BUTTON_A
	InputMap.action_add_event("pcg_interact", joy)
	var regenerate := InputEventKey.new()
	regenerate.physical_keycode = KEY_R
	InputMap.action_add_event("pcg_regenerate", regenerate)
	var repeat := InputEventKey.new()
	repeat.physical_keycode = KEY_T
	InputMap.action_add_event("pcg_repeat", repeat)


func _create_camera_and_light() -> void:
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	add_child(camera)
	camera.current = true
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-65, -25, 0)
	light.light_energy = 1.4
	add_child(light)
	var ambient := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("18202b")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("d8e2ef")
	env.ambient_light_energy = 0.6
	ambient.environment = env
	add_child(ambient)


func _create_hud() -> void:
	var canvas := CanvasLayer.new()
	add_child(canvas)
	hud = Label.new()
	hud.position = Vector2(18, 16)
	hud.add_theme_font_size_override("font_size", 18)
	hud.add_theme_color_override("font_color", Color.WHITE)
	hud.add_theme_color_override("font_shadow_color", Color.BLACK)
	hud.add_theme_constant_override("shadow_offset_x", 1)
	hud.add_theme_constant_override("shadow_offset_y", 1)
	canvas.add_child(hud)


func _regenerate(new_seed: int) -> void:
	boss_crossing_points.clear()
	if is_instance_valid(world):
		world.free()
	world = Node3D.new()
	world.name = "Generated_%d" % new_seed
	add_child(world)
	map_seed = new_seed
	level = _candidate_level(new_seed)
	if not level["validation"]["ok"]:
		push_error("Invalid level: %s" % str(level["validation"]["issues"]))
		return
	_fit_camera()
	_build_geometry()
	_build_navigation()
	_create_actors()
	active_squeeze = {}
	squeeze_remaining = 0.0
	game_finished = false
	result_text = ""
	_save_report()
	_update_hud()


func _fit_camera() -> void:
	var min_x := INF
	var min_z := INF
	var max_x := -INF
	var max_z := -INF
	for room in level["rooms"]:
		for p in room["polygon"]:
			min_x = minf(min_x, p.x)
			max_x = maxf(max_x, p.x)
			min_z = minf(min_z, p.y)
			max_z = maxf(max_z, p.y)
	var center := Vector3((min_x + max_x) / 2.0, 0, (min_z + max_z) / 2.0)
	camera.position = center + Vector3(0, 65, 0.01)
	camera.look_at(center)
	var viewport_size: Vector2 = get_viewport().get_visible_rect().size
	var aspect: float = maxf(1.0, viewport_size.x / maxf(1.0, viewport_size.y))
	camera.size = maxf(max_z - min_z + 4.0, (max_x - min_x + 4.0) / aspect)


func _save_report() -> void:
	var report := {"schema_version": 2, "seed": level["seed"], "genes": level.get("genes", {}), "candidate_file": candidate_file,
		"validation": level["validation"], "source_dxf_sha256": level["source_dxf_sha256"],
		"source_graph_sha256": level["source_graph_sha256"], "rooms": [], "edges": []}
	for room in level["rooms"]:
		var points := []
		for p in room["polygon"]: points.append([p.x, p.y])
		report["rooms"].append({"source_id": room["source_id"], "kind": room["kind"],
			"polygon_m": points})
	for edge in level["edges"]:
		report["edges"].append({"id": edge["id"], "a": edge["a"], "b": edge["b"],
			"kind": edge["kind"], "door_width_m": edge["door_width_m"]})
	var file := FileAccess.open("user://last_generation.json", FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify(report, "  "))
		file.close()


func _build_geometry() -> void:
	var wall_mat := _material(Color("738091"))
	var floor_mat := _material(Color("48556a"))
	var through_mat := _material(Color("4dbddd", 0.75))
	var break_mat := _material(Color("d68063"))
	for room in level["rooms"]:
		_build_floor(room, floor_mat)
		_build_room_walls(room, wall_mat)
	for edge in level["edges"]:
		edge["position"] = model.door_center(edge)
		edge["smash_elapsed"] = 0.0
		edge["barriers"] = []
		var segment: PackedVector2Array = edge["shared_segment"]
		var tangent: Vector2 = (segment[1] - segment[0]).normalized()
		var width: float = edge["door_width_m"]
		if edge["kind"] == "through":
			var narrow: float = edge.get("squeeze_width_m",0.9)
			var shoulder: float = (width-narrow)/2.0
			for sign_value in [-1.0,1.0]:
				var offset: Vector2 = tangent*sign_value*(narrow+shoulder)/2.0
				edge["barriers"].append(_wall_piece("ThroughShoulder_%s" % edge["id"],
					edge["position"]+Vector3(offset.x,1.5,offset.y),tangent,shoulder,wall_mat,WORLD_LAYER))
			width = narrow
			edge["player_gate"] = _wall_piece("Squeeze_%s" % edge["id"],
				edge["position"], tangent, width, through_mat, PLAYER_GATE_LAYER)
			edge["boss_gate"] = _wall_piece("BossSmash_%s" % edge["id"],
				edge["position"], tangent, width, through_mat, BOSS_GATE_LAYER)
		elif edge["kind"] == "break":
			edge["barriers"].append(_wall_piece("Break_%s" % edge["id"],
				edge["position"], tangent, width, break_mat, WORLD_LAYER))
	for block in level["blocks"]:
		var p: Vector2 = block["position"]
		_cylinder("Block_%d" % block["id"], Vector3(p.x, 0.8, p.y),
			float(block["radius"]), 1.6, _material(Color("917249")))


func _build_floor(room: Dictionary, material: Material) -> void:
	var polygon: PackedVector2Array = room["polygon"]
	var triangles: PackedInt32Array = Geometry2D.triangulate_polygon(polygon)
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var faces := PackedVector3Array()
	for index in triangles:
		var p: Vector2 = polygon[index]
		vertices.append(Vector3(p.x, 0, p.y))
		normals.append(Vector3.UP)
	for index in range(0, triangles.size(), 3):
		for j in range(3): faces.append(vertices[index + j])
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var visual := MeshInstance3D.new()
	visual.name = "Floor_%s" % room["source_id"]
	visual.mesh = mesh
	visual.material_override = material
	world.add_child(visual)
	var body := StaticBody3D.new()
	body.name = "FloorCollision_%s" % room["source_id"]
	body.collision_layer = WORLD_LAYER
	var collider := CollisionShape3D.new()
	var shape := ConcavePolygonShape3D.new()
	shape.data = faces
	shape.backface_collision = true
	collider.shape = shape
	body.add_child(collider)
	world.add_child(body)


func _build_room_walls(room: Dictionary, material: Material) -> void:
	for segment in model.room_wall_segments(level,room):
		var a: Vector2 = segment[0]
		var b: Vector2 = segment[1]
		var mid := (a+b)*0.5
		_wall_piece("Wall_%s" % room["source_id"], Vector3(mid.x,1.5,mid.y),
			(b-a).normalized(),a.distance_to(b),material,WORLD_LAYER)


func _wall_interval(label: String, origin: Vector2, direction: Vector2,
		start: float, finish: float, material: Material) -> void:
	var mid := origin + direction * ((start + finish) / 2.0)
	_wall_piece("Wall_%s" % label, Vector3(mid.x, 1.5, mid.y),
		direction, finish - start, material, WORLD_LAYER)


func _wall_piece(label: String, position: Vector3, tangent: Vector2, length: float,
		material: Material, layer: int) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.name = label
	body.position = position
	body.rotation.y = -atan2(tangent.y, tangent.x)
	body.collision_layer = layer
	body.collision_mask = 0
	var size := Vector3(length, 3.0, 0.18)
	var visual := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	visual.mesh = mesh
	visual.material_override = material
	body.add_child(visual)
	var collider := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	collider.shape = shape
	body.add_child(collider)
	world.add_child(body)
	return body


func _cylinder(label: String, position: Vector3, radius: float, height: float,
		material: Material) -> void:
	var body := StaticBody3D.new()
	body.name = label
	body.position = position
	body.collision_layer = WORLD_LAYER
	var visual := MeshInstance3D.new()
	var mesh := CylinderMesh.new()
	mesh.top_radius = radius
	mesh.bottom_radius = radius
	mesh.height = height
	visual.mesh = mesh
	visual.material_override = material
	body.add_child(visual)
	var collider := CollisionShape3D.new()
	var shape := CylinderShape3D.new()
	shape.radius = radius
	shape.height = height
	collider.shape = shape
	body.add_child(collider)
	world.add_child(body)


func _material(color: Color) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 0.9
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	if color.a < 1.0: material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	return material


func _build_navigation() -> void:
	for room in level["rooms"]:
		for role in ["player", "boss"]:
			var clearance := Model.PLAYER_RADIUS if role == "player" else Model.BOSS_RADIUS
			var region := NavigationRegion3D.new()
			region.name = "Nav_%s_%s" % [role, room["source_id"]]
			region.navigation_layers = 1 if role == "player" else 2
			region.use_edge_connections = false
			region.navigation_mesh = _room_navmesh(room, clearance)
			world.add_child(region)
			region.set_navigation_map(player_nav_map if role == "player" else boss_nav_map)
	for edge in level["edges"]:
		var a: Vector2 = level["rooms"][edge["a"]]["center"]
		var b: Vector2 = level["rooms"][edge["b"]]["center"]
		var segment: PackedVector2Array = edge["shared_segment"]
		var tangent: Vector2 = (segment[1] - segment[0]).normalized()
		var normal := Vector2(-tangent.y, tangent.x)
		if normal.dot(b - a) < 0: normal = -normal
		var center: Vector3 = edge["position"]
		for role in ["player", "boss"]:
			var link := NavigationLink3D.new()
			link.name = "Link_%s_%s" % [role, edge["id"]]
			link.navigation_layers = 1 if role == "player" else 2
			var anchor := 0.78 if role == "player" else 0.88
			link.start_position = center + Vector3(-normal.x * anchor, 0.1, -normal.y * anchor)
			link.end_position = center + Vector3(normal.x * anchor, 0.1, normal.y * anchor)
			link.enabled = edge["kind"] == "normal"
			world.add_child(link)
			link.set_navigation_map(player_nav_map if role == "player" else boss_nav_map)
			edge["%s_nav_link" % role] = link


func _room_navmesh(room: Dictionary, clearance: float) -> NavigationMesh:
	var mesh := NavigationMesh.new()
	mesh.cell_size = 0.05
	var vertices := PackedVector3Array()
	var polygons := []
	var lookup := {}
	var insets: Array[PackedVector2Array] = Geometry2D.offset_polygon(
		room["polygon"], -(clearance + 0.08))
	if _room_has_block(room["id"]):
		_add_nav_around_block(room["id"], room["polygon"], clearance, vertices, polygons, lookup)
	else:
		for inset in insets:
			_append_nav_polygon(inset, vertices, polygons, lookup)
	mesh.vertices = vertices
	for polygon in polygons: mesh.add_polygon(polygon)
	return mesh


func _room_has_block(room_id: int) -> bool:
	for block in level["blocks"]:
		if block["room"] == room_id: return true
	return false


func _add_nav_around_block(room_id: int, polygon: PackedVector2Array, clearance: float,
		vertices: PackedVector3Array, polygons: Array, lookup: Dictionary) -> void:
	var rect := Rect2(polygon[0], Vector2.ZERO)
	for point in polygon: rect = rect.expand(point)
	var margin := clearance + 0.08
	var x0: float = rect.position.x + margin
	var x1: float = rect.end.x - margin
	var z0: float = rect.position.y + margin
	var z1: float = rect.end.y - margin
	# The navigation rectangle must respect clearance from chamfers as well.
	var safe_polygons := Geometry2D.offset_polygon(polygon,-margin)
	if safe_polygons.is_empty(): return
	var safe_polygon: PackedVector2Array = safe_polygons[0]
	for attempt in range(20):
		var all_inside := true
		for p in [Vector2(x0, z0), Vector2(x1, z0), Vector2(x1, z1), Vector2(x0, z1)]:
			if not Geometry2D.is_point_in_polygon(p, safe_polygon):
				all_inside = false
				break
		if all_inside: break
		x0 += 0.025
		x1 -= 0.025
		z0 += 0.025
		z1 -= 0.025
	var obstacle: Dictionary = {}
	for item in level["blocks"]:
		if item["room"] == room_id:
			obstacle = item
			break
	var center: Vector2 = obstacle["position"]
	var radius: float = obstacle["radius"] + clearance + 0.08
	var left: float = clampf(center.x - radius, x0, x1)
	var right: float = clampf(center.x + radius, x0, x1)
	var top: float = clampf(center.y - radius, z0, z1)
	var bottom: float = clampf(center.y + radius, z0, z1)
	# Split every strip at the same coordinates. Partial shared edges (T junctions)
	# are not connected inside one NavigationMesh, even when their surfaces touch.
	var xs := [x0,left,right,x1]
	var zs := [z0,top,bottom,z1]
	var strips: Array = []
	for ix in range(3):
		for iz in range(3):
			if ix == 1 and iz == 1: continue
			strips.append([xs[ix],zs[iz],xs[ix+1],zs[iz+1]])
	for strip in strips:
		if strip[2] - strip[0] < 0.03 or strip[3] - strip[1] < 0.03: continue
		var box := PackedVector2Array([Vector2(strip[0], strip[1]),
			Vector2(strip[2], strip[1]), Vector2(strip[2], strip[3]),
			Vector2(strip[0], strip[3])])
		_append_nav_polygon(box, vertices, polygons, lookup)


func _append_nav_polygon(polygon: PackedVector2Array, vertices: PackedVector3Array,
		polygons: Array, lookup: Dictionary) -> void:
	var triangles := Geometry2D.triangulate_polygon(polygon)
	for i in range(0, triangles.size(), 3):
		var indices := PackedInt32Array()
		for j in range(3):
			var p: Vector2 = polygon[triangles[i + j]]
			var key := "%d,%d" % [roundi(p.x * 1000), roundi(p.y * 1000)]
			if not lookup.has(key):
				lookup[key] = vertices.size()
				vertices.append(Vector3(p.x, 0.1, p.y))
			indices.append(lookup[key])
		polygons.append(indices)


func _create_actors() -> void:
	player = _actor("Player", model.room_center(level, level["spawn_room"]) + Vector3(0, 1, 0),
		Model.PLAYER_RADIUS, 1.8, Color("69d47a"), PLAYER_GATE_LAYER | WORLD_LAYER)
	boss = _actor("Boss", model.room_center(level, level["boss_room"]) + Vector3(0, 1.15, 0),
		Model.BOSS_RADIUS, 2.2, Color("e25d63"), BOSS_GATE_LAYER | WORLD_LAYER)
	exit_marker = MeshInstance3D.new()
	exit_marker.name = "Exit"
	var mesh := SphereMesh.new()
	mesh.radius = 0.85
	mesh.height = 1.7
	exit_marker.mesh = mesh
	exit_marker.material_override = _material(Color("e4d15a"))
	var exit_room_center: Vector3 = model.room_center(level, level["exit_room"])
	var entrance: Vector3 = exit_room_center
	for edge in level["edges"]:
		if edge["a"] == level["exit_room"] or edge["b"] == level["exit_room"]:
			entrance = edge["position"]
			break
	var inward := exit_room_center - entrance
	inward.y = 0
	exit_marker.position = entrance + inward.normalized() * 1.1 + Vector3(0, 0.9, 0)
	world.add_child(exit_marker)


func _actor(label: String, position: Vector3, radius: float, height: float,
		color: Color, mask: int) -> CharacterBody3D:
	var body := CharacterBody3D.new()
	body.name = label
	body.position = position
	body.collision_layer = 8 if label == "Player" else 16
	body.collision_mask = mask
	var collider := CollisionShape3D.new()
	var shape := CapsuleShape3D.new()
	shape.radius = radius
	shape.height = height
	collider.shape = shape
	body.add_child(collider)
	var visual := MeshInstance3D.new()
	var mesh := CapsuleMesh.new()
	mesh.radius = radius
	mesh.height = height
	visual.mesh = mesh
	visual.material_override = _material(color)
	body.add_child(visual)
	world.add_child(body)
	return body


func _process(delta: float) -> void:
	if Engine.is_editor_hint():
		evolution_poll_seconds += delta
		if evolution_poll_seconds > 2.0:
			evolution_poll_seconds = 0.0
			_read_evolution_status()
		return
	if Input.is_action_just_pressed("pcg_regenerate"):
		_regenerate(map_seed + 1)
		return
	if Input.is_action_just_pressed("pcg_repeat"):
		_regenerate(map_seed)
		return
	if game_finished: return
	if Input.is_action_just_pressed("pcg_interact"): _try_squeeze()
	if not active_squeeze.is_empty():
		squeeze_remaining -= delta
		if squeeze_remaining <= 0:
			# Each squeeze crosses the intact gap once; Boss destruction opens it permanently.
			player.position = active_squeeze["squeeze_destination"]
			player.velocity = Vector3.ZERO
			active_squeeze = {}
	_update_hud()


func _physics_process(delta: float) -> void:
	if Engine.is_editor_hint(): return
	if game_finished or not is_instance_valid(player): return
	var input_direction := Vector3.ZERO
	if Input.is_key_pressed(KEY_W): input_direction.z -= 1
	if Input.is_key_pressed(KEY_S): input_direction.z += 1
	if Input.is_key_pressed(KEY_A): input_direction.x -= 1
	if Input.is_key_pressed(KEY_D): input_direction.x += 1
	player.velocity = input_direction.normalized() * player_speed if active_squeeze.is_empty() else Vector3.ZERO
	player.move_and_slide()
	_update_boss(delta)
	if player.global_position.distance_to(exit_marker.global_position) < 1.25:
		game_finished = true
		result_text = "到达出口！按 R 换一张地图。"
	elif player.global_position.distance_to(boss.global_position) < 1.15:
		game_finished = true
		result_text = "被 Boss 追上。按 T 重试本地图。"


func _try_squeeze() -> void:
	if not active_squeeze.is_empty(): return
	var nearest: Dictionary = {}
	var best := 1.8
	for edge in level["edges"]:
		if edge["kind"] != "through" or edge["player_open"]: continue
		var distance: float = player.position.distance_to(edge["position"] + Vector3(0, 1, 0))
		if distance < best:
			best = distance
			nearest = edge
	if not nearest.is_empty():
		var span: PackedVector2Array = nearest["shared_segment"]
		var tangent := (span[1]-span[0]).normalized()
		var normal := Vector3(-tangent.y,0,tangent.x)
		var center: Vector3 = nearest["position"]+Vector3(0,player.position.y,0)
		var side := 1.0 if normal.dot(player.position-center)>=0 else -1.0
		var approach := center+normal*side*0.62
		if player.test_move(player.global_transform,approach-player.position): return
		nearest["squeeze_destination"] = center-normal*side*0.62
		active_squeeze = nearest
		squeeze_remaining = player_squeeze_seconds


func _update_boss(delta: float) -> void:
	if not boss_crossing_points.is_empty():
		var crossing_target: Vector3 = boss_crossing_points[0]
		if boss.position.distance_to(crossing_target)<0.08:
			boss_crossing_points.pop_front()
			if boss_crossing_points.is_empty(): return
			crossing_target = boss_crossing_points[0]
		var crossing_direction := crossing_target-boss.position
		if boss_crossing_points.size()>1:
			var approach_path := NavigationServer3D.map_get_path(boss_nav_map,boss.position,crossing_target,true,2)
			if approach_path.size()>=2:
				var approach_index := 1
				while approach_index<approach_path.size()-1 and boss.position.distance_to(approach_path[approach_index])<0.2:
					approach_index+=1
				crossing_direction = approach_path[approach_index]-boss.position
		crossing_direction.y=0
		boss.velocity=crossing_direction.normalized()*minf(boss_speed,crossing_direction.length()/maxf(delta,0.001))
		boss.move_and_slide()
		return
	var boss_room: int = model.closest_room(level, boss.position)
	var player_room: int = model.closest_room(level, player.position)
	var target := player.position
	var crossing_open_door := false
	if boss_room != player_room:
		var edge: Dictionary = model.next_edge_toward(level, boss_room, player_room)
		if not edge.is_empty():
			if not edge["boss_open"]:
				target = edge["position"] + Vector3(0, boss.position.y, 0)
				if boss.position.distance_to(target) < 1.25:
					boss.velocity = Vector3.ZERO
					edge["smash_elapsed"] += delta
					var duration: float = boss_through_seconds if edge["kind"] == "through" else boss_break_seconds
					if edge["smash_elapsed"] >= duration: _open_for_boss(edge)
					return
			else:
				var span: PackedVector2Array = edge["shared_segment"]
				var tangent := (span[1]-span[0]).normalized()
				var normal := Vector2(-tangent.y,tangent.x)
				var next_room: int = edge["b"] if edge["a"]==boss_room else edge["a"]
				var toward: Vector3 = model.room_center(level,next_room)-model.room_center(level,boss_room)
				if normal.dot(Vector2(toward.x,toward.z))<0: normal=-normal
				var portal: Vector3 = edge["position"]+Vector3(0,boss.position.y,0)
				var step := Vector3(normal.x*0.72,0,normal.y*0.72)
				boss_crossing_points.assign([portal-step,portal+step])
				return
	var direction: Vector3 = target - boss.position
	if not crossing_open_door:
		var path := NavigationServer3D.map_get_path(boss_nav_map,
			boss.global_position, target, true, 2)
		if path.size() >= 2:
			var index := 1
			while index < path.size() - 1 and boss.global_position.distance_to(path[index]) < 0.35:
				index += 1
			direction = path[index] - boss.position
	direction.y = 0
	boss.velocity = direction.normalized() * boss_speed if direction.length() > 0.05 else Vector3.ZERO
	boss.move_and_slide()


func _open_for_boss(edge: Dictionary) -> void:
	for barrier in edge["barriers"]:
		if is_instance_valid(barrier): barrier.queue_free()
	if edge.has("player_gate") and is_instance_valid(edge["player_gate"]):
		edge["player_gate"].queue_free()
	if edge.has("boss_gate") and is_instance_valid(edge["boss_gate"]):
		edge["boss_gate"].queue_free()
	edge["boss_open"] = true
	edge["player_open"] = true
	edge["boss_nav_link"].enabled = true
	edge["player_nav_link"].enabled = true


func _update_hud() -> void:
	if not is_instance_valid(hud) or not is_instance_valid(player): return
	var validation: Dictionary = level["validation"]
	var prompt := ""
	if not active_squeeze.is_empty():
		prompt = "挤身通过中：%.1fs" % maxf(0, squeeze_remaining)
	else:
		for edge in level["edges"]:
			if edge["kind"] == "through" and not edge["player_open"]:
				if player.position.distance_to(edge["position"] + Vector3(0, 1, 0)) < 1.8:
					prompt = "按 E / 手柄 A 挤身通过蓝色 through"
					break
	hud.text = ("鼠王关 PCG 白模 | Seed %d | 房型 %d | through %d | break %d | 初始环路 %d\n" %
		[level["seed"], validation["room_count"], validation["connection_counts"]["through"],
		validation["connection_counts"]["break"], validation["initial_player_loops"]]) + \
		"WASD 移动 · E/手柄 A 互动 · R 新地图 · T 重试 · 绿=玩家 红=Boss 黄=出口\n" + prompt + result_text


func _candidate_level(seed_value: int) -> Dictionary:
	if not candidate_file.is_empty():
		var candidate = JSON.parse_string(FileAccess.get_file_as_string(candidate_file))
		if candidate is Dictionary and candidate.has("genes"):
			var generated: Dictionary = model.generate_level(int(candidate.get("seed",42)),source,candidate["genes"])
			generated["evolution"] = candidate.get("evaluation",{})
			generated["generation"] = candidate.get("generation",0)
			return generated
		push_error("Invalid evolution candidate: "+candidate_file)
	return model.generate_level(seed_value,source)

func _start_evolution_pilot() -> void:
	_start_evolution("pilot")

func _start_evolution_search() -> void:
	_start_evolution("search")

func _start_evolution(mode: String) -> void:
	if FileAccess.file_exists("res://evolution/process.json"):
		var previous = JSON.parse_string(FileAccess.get_file_as_string("res://evolution/process.json"))
		if previous is Dictionary and OS.is_process_running(int(previous.get("pid",-1))):
			push_warning("Evolution already running. See evolution/status.json")
			return
	var python := ProjectSettings.globalize_path("res://evolution/.venv/Scripts/pythonw.exe")
	var script := ProjectSettings.globalize_path("res://evolution/launch.py")
	var pid := OS.create_process(python,PackedStringArray([script,mode]),false)
	evolution_status = "Started %s, PID %d" % [mode,pid]

func _read_evolution_status() -> void:
	if FileAccess.file_exists("res://evolution/status.json"):
		evolution_status = FileAccess.get_file_as_string("res://evolution/status.json")

func _refresh_evolution() -> void:
	_read_evolution_status()
	if Engine.is_editor_hint(): _rebuild_editor_preview()

func _add_evolution_label() -> void:
	if not level.has("evolution"): return
	var data: Dictionary = level["evolution"]
	var display: Dictionary = data.get("fine_review",data)
	var scores: Array = display.get("objectives",[0.0,0.0,0.0,0.0])
	var label := Label3D.new()
	label.name = "EvolutionScores"
	label.text = "Generation %d | grid %s\nS %.3f  F %.3f\nP %.3f  D %.3f" % [level.get("generation",0),str(display.get("grid","?")),scores[0],scores[1],scores[2],-float(scores[3])]
	candidate_summary = label.text+"\n"+str(data.get("status",""))
	label.position = Vector3(0,4.0,0)
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.font_size = 32
	label.pixel_size = 0.02
	label.no_depth_test = true
	world.add_child(label)

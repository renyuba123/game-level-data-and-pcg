extends Node3D
## Reads Python's authoritative mesh and navigation polygons. No random generation.
var data: Dictionary = {}
var gates: Dictionary = {}
var links: Dictionary = {}
var maps: Dictionary = {}
var generated: Node3D
var layout_scale := 1.0

func point(value, height: float = 0.0) -> Vector3:
	return Vector3(float(value[0]) * layout_scale, height, float(value[1]) * layout_scale)

func scaled_vertex(value, preserve_local_size := false) -> Vector3:
	if not preserve_local_size or data.is_empty() or data.layout.obstacles.is_empty():
		return Vector3(float(value[0]) * layout_scale,float(value[1]),float(value[2]) * layout_scale)
	var raw := Vector2(float(value[0]),float(value[2]))
	var center := Vector2(data.layout.obstacles[0].position[0],data.layout.obstacles[0].position[1])
	var nearest := raw.distance_squared_to(center)
	for obstacle in data.layout.obstacles.slice(1):
		var candidate := Vector2(obstacle.position[0],obstacle.position[1])
		var distance := raw.distance_squared_to(candidate)
		if distance < nearest:
			center = candidate
			nearest = distance
	var transformed := center * layout_scale + (raw - center)
	return Vector3(transformed.x,float(value[1]),transformed.y)

func material(color: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	return m

func solid(faces: Array, label: String, color: Color, layer: int = 1,
		preserve_local_size := false) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.name = label
	body.collision_layer = layer
	body.collision_mask = 0
	generated.add_child(body)
	if faces.is_empty(): return body
	var vertices := PackedVector3Array()
	for v in faces: vertices.append(scaled_vertex(v,preserve_local_size))
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	for v in vertices: surface.add_vertex(v)
	surface.generate_normals()
	var mesh := MeshInstance3D.new()
	mesh.mesh = surface.commit()
	mesh.material_override = material(color)
	body.add_child(mesh)
	var collision := CollisionShape3D.new()
	var shape := ConcavePolygonShape3D.new()
	shape.set_faces(vertices)
	shape.backface_collision = true
	collision.shape = shape
	body.add_child(collision)
	return body

func load_package(path: String) -> bool:
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary: return false
	clear_layout()
	data = parsed
	generated = Node3D.new()
	generated.name = "GeneratedFullPCG"
	add_child(generated)
	solid(data.floor_faces, "Floor", Color("aab4bd"))
	solid(data.wall_faces, "Walls", Color("dae0e6"))
	solid(data.obstacle_faces, "Obstacles", Color("626c78"),1,true)
	for gate in data.gates:
		var bodies: Array = []
		var color: Color = {"through":Color("559fb0"), "break":Color("cb825a"), "window":Color("a33b9f")}[gate.kind]
		bodies.append(solid(gate.faces, gate.id, color))
		var player_block: StaticBody3D = null
		if gate.kind in ["through", "window"]:
			player_block = solid(gate.middle_faces, gate.id + "_player", color, 2)
			bodies.append(player_block)
			var boss_block := solid(gate.middle_faces, gate.id + "_boss", color, 4)
			bodies.append(boss_block)
			if not gate.get("ballistic_faces", []).is_empty():
				player_block.get_child(0).hide()
				boss_block.get_child(0).hide()
				bodies.append(solid(gate.ballistic_faces, gate.id + "_frame", color, 64))
		gates[gate.id] = {"bodies": bodies, "player_block": player_block, "opened": false, "kind": gate.kind}
	for role in ["player", "boss"]:
		var map: RID = NavigationServer3D.map_create()
		maps[role] = map
		NavigationServer3D.map_set_up(map, Vector3.UP)
		NavigationServer3D.map_set_cell_size(map, 0.001)
		NavigationServer3D.map_set_cell_height(map, 0.001)
		NavigationServer3D.map_set_edge_connection_margin(map, 0.002)
		NavigationServer3D.map_set_link_connection_radius(map, 0.05)
		NavigationServer3D.map_set_active(map, true)
		var nav := NavigationMesh.new()
		nav.cell_size = 0.001
		nav.cell_height = 0.001
		var vertices := PackedVector3Array()
		var polygons: Array[PackedInt32Array] = []
		var unique: Dictionary = {}
		for tri in data.navigation[role]:
			var indices := PackedInt32Array()
			for xy in tri:
				var v := point(xy)
				var key := "%.9f,%.9f" % [v.x, v.z]
				if not unique.has(key):
					unique[key] = vertices.size()
					vertices.append(v)
				indices.append(unique[key])
			polygons.append(indices)
		nav.vertices = vertices
		for polygon in polygons: nav.add_polygon(polygon)
		var region := NavigationRegion3D.new()
		region.name = role + "_navigation"
		region.navigation_mesh = nav
		generated.add_child(region)
		region.set_navigation_map(map)
	for entry in data.links:
		var link := NavigationLink3D.new()
		link.name = entry.role + "_" + entry.portal
		link.start_position = point(entry.points[0])
		link.end_position = point(entry.points[1])
		link.enabled = entry.kind == "normal" or (entry.role == "player" and entry.kind in ["through", "window"])
		link.enter_cost = 3.25 if entry.kind in ["through", "window"] and entry.role == "player" else 0.0
		generated.add_child(link)
		link.set_navigation_map(maps[entry.role])
		links[entry.role + ":" + entry.portal] = link
	return true

func clear_layout() -> void:
	if is_instance_valid(generated):
		remove_child(generated)
		generated.free()
	for map in maps.values(): NavigationServer3D.free_rid(map)
	maps.clear()
	links.clear()
	gates.clear()

func _exit_tree() -> void:
	clear_layout()

func set_open(id: String, value: bool) -> void:
	if not gates.has(id) or gates[id].kind == "window": return
	var gate: Dictionary = gates[id]
	gate.opened = value
	for body in gate.bodies:
		body.visible = not value
		for child in body.get_children():
			if child is CollisionShape3D: child.disabled = value
	for role in ["player", "boss"]:
		var link: NavigationLink3D = links[role + ":" + id]
		link.enabled = value or (role == "player" and gate.kind == "through")
		link.enter_cost = 3.25 if not value and gate.kind == "through" and role == "player" else 0.0

func allow_squeeze(id: String, enabled: bool) -> bool:
	if not gates.has(id) or gates[id].kind != "through": return false
	return _player_passage(id, enabled)

func allow_vault(id: String, enabled: bool) -> bool:
	if not gates.has(id) or gates[id].kind != "window": return false
	return _player_passage(id, enabled)

func _player_passage(id: String, enabled: bool) -> bool:
	var body: StaticBody3D = gates[id].player_block
	for child in body.get_children():
		if child is CollisionShape3D: child.disabled = enabled
	return true

func nav_path(role: String, start: Vector3, finish: Vector3) -> PackedVector3Array:
	return NavigationServer3D.map_get_path(maps[role], start, finish, true)

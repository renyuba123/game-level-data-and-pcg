@tool
extends Node3D
## Live DXF-shell subdivision and the interactive combat tuning surface.

@export_group("Layout")
@export var map_seed := 42
@export_range(0.5, 3.0, 0.05, "or_greater") var map_size := 1.0
@export var show_dxf_reference := false
@export var color_partitions := true

@export_group("Player")
@export_range(0.0, 20.0, 0.05, "or_greater") var player_speed := 5.0
@export_range(0.0, 20.0, 0.05, "or_greater") var player_aim_speed := 2.0

@export_group("Boss")
@export_range(0.0, 20.0, 0.05, "or_greater") var boss_speed := 4.2
@export_range(1.0, 10000.0, 1.0, "or_greater") var boss_hp := 1000.0
@export_range(0.0, 10.0, 0.05, "or_greater") var boss_grab_range := 1.2
@export_range(0.0, 10.0, 0.05, "or_greater") var boss_attack_warning := 0.6

@export_group("Stalker")
@export_range(0.0, 20.0, 0.05, "or_greater") var stalker_speed := 4.8
@export_range(0.0, 1000.0, 1.0, "or_greater") var stalker_damage := 20.0

@export_group("Weapon")
@export_range(1.0, 1000.0, 1.0, "or_greater") var weapon_damage := 40.0
@export_range(0.01, 10.0, 0.01, "or_greater") var weapon_fire_interval := 0.3
@export_range(0.0, 10.0, 0.05, "or_greater") var weapon_aim_seconds := 0.35
@export_range(0.0, 20.0, 0.05, "or_greater") var weapon_reload_seconds := 2.0

@export_group("Supplies")
@export_range(0.0, 5.0, 0.05, "or_greater") var supply_pickup_seconds := 0.4
@export_range(0.5, 4.0, 0.05, "or_greater") var supply_pickup_range := 1.25

@export_group("Portals")
@export_range(0.0, 10.0, 0.05, "or_greater") var player_squeeze_seconds := 0.65
@export_range(0.5, 4.0, 0.05, "or_greater") var through_interaction_range := 1.6
@export_range(0.0, 20.0, 0.05, "or_greater") var boss_through_seconds := 1.5
@export_range(0.0, 20.0, 0.05, "or_greater") var boss_break_seconds := 1.8
var requested_seed: Variant = null
var pending_pid := -1
var packet_path := ""
var preview_root: Node3D
var status_label: Label3D
var packet: Dictionary = {}
var appearance_key := ""
var serial := 0
var live_combat: Node3D

func _ready() -> void:
	_request_seed()

func _physics_process(_delta: float) -> void:
	pass

func _process(_delta: float) -> void:
	if requested_seed != map_seed:
		_request_seed()
	if pending_pid > 0 and not OS.is_process_running(pending_pid):
		pending_pid = -1
		if not FileAccess.file_exists(packet_path):
			_status("Generation failed | seed %d" % map_seed)
			return
		var result = JSON.parse_string(FileAccess.get_file_as_string(packet_path))
		if not result is Dictionary or result.get("seed") != map_seed:
			_status("Invalid package | seed %d" % map_seed)
			return
		if not result.get("ok", false):
			_status("Seed %d | %s" % [map_seed,result.get("reason","invalid")])
			return
		packet = result
		_status("Seed %d | %s" % [map_seed,str(packet.layout_hash).left(12)])
		if not Engine.is_editor_hint():
			live_combat = preload("res://scenes/CombatFullPCG.tscn").instantiate()
			live_combat.set("package_path",packet_path)
			live_combat.set("layout_scale",map_size)
			live_combat.set("protocol_override",_combat_protocol())
			add_child(live_combat)
	var key := str(show_dxf_reference) + str(color_partitions) + str(map_size)
	if Engine.is_editor_hint() and not packet.is_empty() and key != appearance_key:
		appearance_key = key
		_draw_preview()

func _request_seed() -> void:
	requested_seed = map_seed
	serial += 1
	packet = {}
	appearance_key = ""
	if is_instance_valid(live_combat):
		remove_child(live_combat)
		live_combat.queue_free()
	if is_instance_valid(preview_root):
		remove_child(preview_root)
		preview_root.queue_free()
	_status("Generating seed %d…" % map_seed)
	var folder := ProjectSettings.globalize_path("user://shell_preview")
	DirAccess.make_dir_recursive_absolute(folder)
	packet_path = folder.path_join("%d_%d_%d_%d.json" % [OS.get_process_id(),get_instance_id(),serial,map_seed])
	var python := ProjectSettings.globalize_path(str(ProjectSettings.get_setting("ratking/python", "res://evolution/.venv/Scripts/python.exe")))
	if OS.has_environment("RATKING_PYTHON"): python = OS.get_environment("RATKING_PYTHON")
	var worker := ProjectSettings.globalize_path("res://full_pcg/shell_layout.py")
	pending_pid = OS.create_process(python,["-B",worker,str(map_seed),packet_path],false)
	if pending_pid <= 0: _status("Python launch failed | seed %d" % map_seed)

func _combat_protocol() -> Dictionary:
	var parsed = JSON.parse_string(FileAccess.get_file_as_string("res://combat_pcg/combat_config.json"))
	if not parsed is Dictionary:
		push_error("Missing combat protocol")
		return {}
	var protocol: Dictionary = parsed.duplicate(true)
	protocol.player.speed_mps = player_speed
	protocol.player.aim_speed_mps = player_aim_speed
	protocol.boss.speed_mps = boss_speed
	protocol.boss.hp = boss_hp
	protocol.boss.grab_range_m = boss_grab_range
	protocol.boss.attack_warning_s = boss_attack_warning
	protocol.stalker.speed_mps = stalker_speed
	protocol.stalker.damage = stalker_damage
	protocol.weapon.damage = weapon_damage
	protocol.weapon.fire_interval_s = weapon_fire_interval
	protocol.weapon.aim_s = weapon_aim_seconds
	protocol.weapon.reload_s = weapon_reload_seconds
	protocol.supplies.pickup_s = supply_pickup_seconds
	var pickup_range: Variant = get("supply_pickup_range")
	if pickup_range is float or pickup_range is int:
		protocol.supplies.pickup_radius_m = float(pickup_range)
	protocol.portals.through_player_squeeze_s = player_squeeze_seconds
	protocol.portals.through_player_interaction_range_m = through_interaction_range
	protocol.portals.through_boss_smash_s = boss_through_seconds
	protocol.portals.break_boss_smash_s = boss_break_seconds
	protocol.protocol_id = "combat_v3_inspector_playtest"
	return protocol

func _status(message: String) -> void:
	if not is_instance_valid(status_label):
		status_label = Label3D.new()
		status_label.position = Vector3(8,3,-5)
		status_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		status_label.font_size = 44
		add_child(status_label)
	status_label.text = message

func _preview_vertex(value, preserve_local_size := false) -> Vector3:
	if not preserve_local_size or packet.layout.obstacles.is_empty():
		return Vector3(value[0] * map_size,value[1],value[2] * map_size)
	var raw := Vector2(value[0],value[2])
	var center := Vector2(packet.layout.obstacles[0].position[0],packet.layout.obstacles[0].position[1])
	var nearest := raw.distance_squared_to(center)
	for obstacle in packet.layout.obstacles.slice(1):
		var candidate := Vector2(obstacle.position[0],obstacle.position[1])
		var distance := raw.distance_squared_to(candidate)
		if distance < nearest:
			center = candidate
			nearest = distance
	var transformed := center * map_size + (raw-center)
	return Vector3(transformed.x,value[1],transformed.y)

func _mesh(faces: Array, color: Color, preserve_local_size := false) -> void:
	if faces.is_empty(): return
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	for v in faces: surface.add_vertex(_preview_vertex(v,preserve_local_size))
	surface.generate_normals()
	var item := MeshInstance3D.new()
	item.mesh = surface.commit()
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	item.material_override = mat
	preview_root.add_child(item)

func _marker(pos, color: Color, size: float) -> void:
	var item := MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = size
	sphere.height = 2*size
	item.mesh = sphere
	item.position = Vector3(pos[0] * map_size,size+.04,pos[1] * map_size)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	item.material_override = mat
	preview_root.add_child(item)

func _draw_preview() -> void:
	if is_instance_valid(preview_root):
		remove_child(preview_root)
		preview_root.queue_free()
	preview_root = Node3D.new()
	preview_root.name = "ShellSeed_%d" % map_seed
	add_child(preview_root)
	_mesh(packet.floor_faces,Color("c5c6bd"))
	_mesh(packet.wall_faces,Color("ddd9cf"))
	_mesh(packet.obstacle_faces,Color("6c6055"),true)
	if color_partitions:
		for zone in packet.zones:
			var faces := []
			for tri in packet.zones[zone]:
				for v in tri: faces.append([v[0],.025,v[1]])
			var tint := Color("a8cdb5")
			if str(zone).begins_with("east"): tint = Color("aec9df")
			if zone in ["hall","foyer"]: tint = Color("e7c686")
			_mesh(faces,tint)
	for gate in packet.gates:
		var color: Color = {"through":Color("559fb0"),"window":Color("a33b9f"),"break":Color("cb825a")}[gate.kind]
		_mesh(gate.faces,color)
		_mesh(gate.get("ballistic_faces",[]),color)
	for p in packet.layout.portals:
		if p.kind == "normal": _marker(p.center,Color("f5f3ed"),.09)
	for s in packet.layout.supplies: _marker(s.position,Color("d2a538"),.18)
	_marker(packet.layout.spawn.position,Color("2b9559"),.35)
	_marker(packet.layout.boss.position,Color("b54942"),.55)
	if show_dxf_reference:
		var profile = JSON.parse_string(FileAccess.get_file_as_string("res://data/shell_source_v2.json"))
		var lines := ImmediateMesh.new()
		var mat := StandardMaterial3D.new()
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		mat.albedo_color = Color("e5419c")
		lines.surface_begin(Mesh.PRIMITIVE_LINES,mat)
		for wall in profile.wall_segments:
			for pt in [wall.start_m,wall.end_m]:
				lines.surface_add_vertex(Vector3(pt[0] * map_size,2.52,pt[1] * map_size))
		lines.surface_end()
		var item := MeshInstance3D.new()
		item.mesh = lines
		preview_root.add_child(item)


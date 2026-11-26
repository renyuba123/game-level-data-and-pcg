extends "res://full_pcg/godot/replay_combat_level.gd"
## The policy chooses controls. CombatLevel applies them to the actual scene.

var policy: String
var decision_variant := "reference"
var crossing_gate := ""
var avoid_gate_until := 0.0
var avoid_gate_direction := Vector3.ZERO
var crossing_deadline := 0.0
var crossing_exit := Vector3.ZERO
var error_scale := 1.0
var decisions := RandomNumberGenerator.new()
var aiming := RandomNumberGenerator.new()
var heading := 0.0
var last_seen := Vector3.ZERO
var seen_at := -100.0
var aim_on_target_s := 0.0
var known_supplies: Dictionary = {}
var goal := Vector3.ZERO
var path := PackedVector3Array()
var path_index := 0
var next_plan := 0.0
var moving_to_supply := false
var aim_error := 0.0
var mobile_course := Vector3.ZERO
var mobile_until := 0.0

# Opt-in development variants. These decisions are kept out of engine events
# so the same captured controls can still be replayed without the policy.
var tactical_decisions: Array[Dictionary] = []
var tactic := {}
var visited_rooms := {}
var collected_count := 0
var tactic_next_plan := 0.0


func setup(case: Dictionary) -> void:
	native_boss = true
	policy = case.policy
	decision_variant = case.get("decision_variant","reference")
	reaction_scale = case.ability.get("reaction_scale", 1.0)
	error_scale = case.ability.get("error_scale", 1.0)
	decisions.seed = int(case.seed)
	aiming.seed = int(case.seed) + 2147483647
	heading = float(data.layout.spawn.heading_rad) + decisions.randf_range(-.2,.2)
	aim_error = aiming.randfn(0.0, deg_to_rad(float(combat.weapon.angular_error_sd_deg)) * error_scale)
	goal = _flat(player_body.position)


func _flat(pos: Vector3) -> Vector3:
	return Vector3(pos.x, 0, pos.z)


func _visible_from(origin: Vector3, target: Vector3) -> bool:
	if origin.distance_to(target) > float(combat.player.vision_range_m):
		return false
	var ray := PhysicsRayQueryParameters3D.create(origin, target)
	ray.collision_mask = 1 | 64
	return get_world_3d().direct_space_state.intersect_ray(ray).is_empty()


func _see(pos: Vector3) -> bool:
	var eye := player_body.position + Vector3.UP * .25
	var offset := _flat(pos - eye).normalized()
	if offset.dot(Vector3(cos(heading), 0, sin(heading))) < cos(deg_to_rad(float(combat.player.fov_deg) / 2.0)):
		return false
	return _visible_from(eye,pos)


func _find_goal(pos: Vector3, seen: bool) -> void:
	var recent := elapsed_s - seen_at < 1.5
	var gap := pos.distance_to(last_seen)
	var retreat_range := 5.5 if policy == "occlusion" else 5.0
	var retreat: bool = recent and gap < retreat_range
	moving_to_supply = false
	if not retreat and loaded + reserve < (16 if policy == "supply" else 10):
		var nearest := INF
		for id in known_supplies:
			if collected.has(id):
				continue
			var candidate: Vector3 = known_supplies[id]
			var route := nav_path("player", pos, candidate)
			if route.is_empty() or route[-1].distance_to(candidate) > .55:
				continue
			var cost := pos.distance_to(route[0])
			for i in range(1,route.size()):
				cost += route[i-1].distance_to(route[i])
			if cost < nearest:
				nearest = cost
				goal = candidate
				path = route
				path_index = 0
				moving_to_supply = true
		if moving_to_supply:
			return
	if not retreat and seen and loaded > 0:
		path.clear()
		return
	if not retreat and path_index < path.size() and goal.distance_to(pos) > .50:
		return
	var best := -INF
	path.clear()
	for room in data.layout.rooms:
		var candidate := point(room.center)
		if candidate.distance_to(pos) < 1.0:
			continue
		var route := nav_path("player", pos, candidate)
		if route.is_empty() or route[-1].distance_to(candidate) > .7:
			continue
		var score := decisions.randf()
		if retreat:
			var nearest_gap := INF
			for waypoint in route:
				nearest_gap = minf(nearest_gap, waypoint.distance_to(last_seen))
			score = minf(candidate.distance_to(last_seen), 10.0) + 2.0 * nearest_gap - .4 * candidate.distance_to(pos)
			var cover := not _visible_from(candidate + Vector3.UP * 1.15, last_seen + Vector3.UP * 1.15)
			score += (3.0 if policy == "occlusion" else 1.0) if cover else 0.0
		if score > best:
			best = score
			goal = candidate
			path = route
			path_index = 0


func _portal_to_use(pos: Vector3, target: Vector3) -> bool:
	for portal in data.layout.portals:
		if portal.kind not in ["window", "through"] or gates[portal.id].opened:
			continue
		var link: NavigationLink3D = links["player:" + portal.id]
		var entry := link.start_position
		var exit := link.end_position
		if pos.distance_to(exit) < pos.distance_to(entry):
			entry = link.end_position
			exit = link.start_position
		var radius := float(data.window.interaction_range_m) if portal.kind == "window" else _through_range()
		if pos.distance_to(entry) <= radius and (target - pos).dot(exit - entry) > 0.0:
			if portal.kind == "through" and decision_variant in ["crossing","combined"]:
				var hold := float(combat.portals.through_player_squeeze_s)
				var warning := float(combat.boss.attack_warning_s)
				var arrival := maxf(0,pos.distance_to(last_seen)-float(combat.boss.grab_range_m))/float(combat.boss.speed_mps)
				var clear_s := pos.distance_to(exit)/float(combat.player.speed_mps)
				var remaining_warning := maxf(0,warning-attack_s) if is_equal_approx(seen_at,elapsed_s) else warning
				if elapsed_s - seen_at < 1.0 and arrival + remaining_warning < hold + clear_s + .15:
					avoid_gate_until = elapsed_s + hold
					avoid_gate_direction = (pos-last_seen).normalized()
					return false
				crossing_gate = portal.id
				crossing_deadline = elapsed_s + hold + 1.5
				crossing_exit = exit
			return portal.kind != "window" or not interact_latched
	return false


func _steer(pos: Vector3, direction: Vector3, interact: bool) -> Vector3:
	# A navmesh point can require a portal action or be on the other side of
	# a corner. Look for a short physically open direction before committing.
	if direction == Vector3.ZERO or interact or vault_id != "":
		return direction
	var recent := elapsed_s - seen_at <= 1.5 and pos.distance_to(last_seen) < 5.5
	if not recent and not player_body.test_move(player_body.transform,direction * .35):
		return direction
	var away := (pos - last_seen).normalized() if recent else Vector3.ZERO
	var best := Vector3.ZERO
	var best_score := -INF
	for spread in [0.0, .4, -.4, .8, -.8, 1.2, -1.2, PI / 2.0, -PI / 2.0, 2.4, -2.4, PI]:
		var candidate := direction.rotated(Vector3.UP,spread)
		if player_body.test_move(player_body.transform,candidate * .38):
			continue
		var value := candidate.dot(direction) + 2.0 * candidate.dot(away)
		if value > best_score:
			best_score = value
			best = candidate
	return best


# Choose a locally clear arc using the last observed position and known supplies.
func _mobile_direction(pos: Vector3, heading_goal: Vector3, recent: bool) -> Vector3:
	var wish := heading_goal
	var urgent_pack := false
	if loaded + reserve <= 8:
		var nearest := INF
		for id in known_supplies:
			if collected.has(id): continue
			var offset: Vector3 = known_supplies[id] - pos
			if offset.length() < nearest and not player_body.test_move(player_body.transform,offset):
				nearest = offset.length()
				wish = offset.normalized()
				urgent_pack = true
	var best := -INF
	var chosen := wish
	for i in range(24):
		var direction := Vector3(cos(i*TAU/24),0,sin(i*TAU/24))
		var travel := 0.0
		for reach in [.45,1.0,1.8,2.8]:
			if player_body.test_move(player_body.transform,direction*reach): break
			travel = reach
		if travel == 0: continue
		var end := pos + direction*travel
		var value := travel + direction.dot(wish)*(4.0 if urgent_pack else 1.0)
		if recent:
			value += clampf(end.distance_to(last_seen)-pos.distance_to(last_seen),-2,2)*1.6
			var tangent := Vector3.UP.cross(pos-last_seen).normalized()
			value += direction.dot(tangent)*.7
		if value > best:
			best = value
			chosen = direction
	return chosen


# Use the room polygon in model coordinates. No candidate depends on fixed room or gate IDs.
func _room_at(pos: Vector3) -> String:
	var point_2d := Vector2(pos.x, pos.z) / layout_scale
	for room in data.layout.rooms:
		var polygon := PackedVector2Array()
		for vertex in room.polygon:
			polygon.append(Vector2(float(vertex[0]), float(vertex[1])))
		if Geometry2D.is_point_in_polygon(point_2d, polygon):
			return room.id
	return ""


func _route_length(route: PackedVector3Array, from: Vector3, to: Vector3) -> float:
	if route.is_empty() or route[0].distance_to(from) > .65 or route[-1].distance_to(to) > .55:
		return INF
	var distance := from.distance_to(route[0]) + route[-1].distance_to(to)
	for i in range(1, route.size()):
		distance += route[i - 1].distance_to(route[i])
	return distance


func _boss_earliest_arrival(target: Vector3) -> float:
	var speed := float(combat.boss.speed_mps)
	var distance := maxf(0, last_seen.distance_to(target) - float(combat.boss.grab_range_m))
	var age := elapsed_s - seen_at
	return maxf(0, distance / maxf(speed, .01) - age) if age <= 2.5 else INF


func _start_tactic(kind: String, id: String, destination: Vector3, route: PackedVector3Array,
		travel_s: float, deadline_s: float) -> void:
	tactic = {"kind":kind, "id":id, "until":elapsed_s + deadline_s}
	goal = destination
	path = route
	path_index = 0
	tactical_decisions.append({"t":elapsed_s, "step":tick, "kind":kind, "id":id,
		"travel_s":travel_s, "ammo":loaded + reserve})


func _plan_open_door(pos: Vector3, room: String, leaving: bool) -> bool:
	var best_score := -INF
	var best := {}
	for portal in data.layout.portals:
		if room not in [portal.a, portal.b] or (portal.kind != "normal" and not gates[portal.id].opened):
			continue
		var neighbor: String = portal.b if portal.a == room else portal.a
		if not leaving and visited_rooms.has(neighbor):
			continue
		var link: NavigationLink3D = links["player:" + portal.id]
		var across := point(portal.normal).normalized()
		if portal.b == room:
			across = -across
		var center := point(portal.center)
		var destination := link.end_position if (link.end_position - center).dot(across) > 0.0 else link.start_position
		var route := nav_path("player", pos, destination)
		var travel_s := _route_length(route, pos, destination) / float(combat.player.speed_mps)
		var slack := _boss_earliest_arrival(center) - travel_s
		if travel_s > (2.0 if leaving else 1.6) or slack < .25:
			continue
		var value := minf(slack, 4.0) - travel_s
		if value > best_score:
			best_score = value
			best = {"id":portal.id, "to":destination, "route":route, "time":travel_s}
	if best.is_empty():
		return false
	var destination: Vector3 = best.to
	var route: PackedVector3Array = best.route
	var travel_s: float = best.time
	if leaving:
		# Clear the far side before the mobile steering can turn back through
		# the doorway. Prefer a sweep-clear lateral run inside the new room.
		var portal := next_portal(best.id)
		var tangent := point(portal.tangent).normalized()
		var destination_room := _room_at(destination)
		var body_at_exit := player_body.global_transform
		body_at_exit.origin = destination + Vector3.UP * player_body.position.y
		var best_clearance := 0.0
		var escape := destination
		for signed_distance in [-4.0, 4.0, -2.0, 2.0]:
			var offset := tangent * float(signed_distance)
			var candidate := destination + offset
			if _room_at(candidate) != destination_room or player_body.test_move(body_at_exit, offset):
				continue
			var clearance := offset.length() + .35 * candidate.distance_to(last_seen)
			if clearance > best_clearance:
				best_clearance = clearance
				escape = candidate
		if escape != destination:
			route.append(escape)
			travel_s += destination.distance_to(escape) / float(combat.player.speed_mps)
			destination = escape
	_start_tactic("leave_after_pickup" if leaving else "look_for_ammo", best.id,
		destination, route, travel_s, travel_s + 1.0)
	return true


func _plan_ammo(pos: Vector3) -> bool:
	var best := {}
	var best_time := INF
	for id in known_supplies:
		if collected.has(id):
			continue
		var destination: Vector3 = known_supplies[id]
		var route := nav_path("player", pos, destination)
		var travel := _route_length(route, pos, destination) / float(combat.player.speed_mps)
		var finish := travel + float(combat.supplies.pickup_s)
		if finish >= minf(best_time, 3.0) or _boss_earliest_arrival(destination) < finish + .25:
			continue
		# Check the route as well as the pickup so we don't cross the remembered threat.
		var safe := true
		var distance := 0.0
		var previous := pos
		for waypoint in route:
			distance += previous.distance_to(waypoint)
			if _boss_earliest_arrival(waypoint) < distance / float(combat.player.speed_mps):
				safe = false
				break
			previous = waypoint
		if safe:
			best_time = finish
			best = {"id":id, "to":destination, "route":route, "time":travel}
	if best.is_empty():
		return false
	_start_tactic("collect_ammo", best.id, best.to, best.route, best.time, best_time + 1.0)
	return true


func _update_tactic(pos: Vector3) -> void:
	var finished_pickup := collected.size() > collected_count
	collected_count = collected.size()
	if not tactic.is_empty():
		var done := collected.has(tactic.id) if tactic.kind == "collect_ammo" else pos.distance_to(goal) <= .28
		if done or elapsed_s >= float(tactic.until):
			tactic.clear()
			moving_to_supply = false
			path.clear()
			path_index = 0
			next_plan = elapsed_s
		else:
			return
	var low_ammo := decision_variant != "paced_exit_v1" and loaded + reserve <= 4
	if not finished_pickup and not low_ammo:
		return
	var room := _room_at(pos)
	if not room.is_empty():
		visited_rooms[room] = true
	if finished_pickup and decision_variant != "paced_supply_v1" and elapsed_s - seen_at <= 2.5:
		var open_exits := 0
		for portal in data.layout.portals:
			if room in [portal.a, portal.b] and (portal.kind == "normal" or gates[portal.id].opened):
				open_exits += 1
		if open_exits == 1 and _plan_open_door(pos, room, true):
			return
	if low_ammo and reload_s <= 0 and elapsed_s >= tactic_next_plan:
		tactic_next_plan = elapsed_s + .4
		if not _plan_ammo(pos) and not room.is_empty():
			_plan_open_door(pos, room, false)


func control(delta: float) -> Dictionary:
	var pos := _flat(player_body.position)
	var seen := _see(boss_body.position)
	if seen:
		last_seen = _flat(boss_body.position)
		seen_at = elapsed_s
	for pack in data.layout.supplies:
		if not known_supplies.has(pack.id) and _see(point(pack.position, .35)):
			known_supplies[pack.id] = point(pack.position)
	var paced := decision_variant.begins_with("paced")
	if decision_variant in ["paced_supply_v1", "paced_exit_v1", "paced_tactics_v1"]:
		_update_tactic(pos)
	var tactical := not tactic.is_empty()
	if not tactical and elapsed_s + 1e-8 >= next_plan:
		_find_goal(pos, seen)
		next_plan = elapsed_s + .4

	while path_index < path.size() and path[path_index].distance_to(pos) <= .23:
		path_index += 1
	var target := path[path_index] if path_index < path.size() else pos
	var direction := (target - pos).normalized()
	var collect_ready := false
	var collecting: bool = tactic.kind == "collect_ammo" if tactical else moving_to_supply
	if collecting and goal.distance_to(pos) <= float(combat.supplies.pickup_radius_m) * .85:
		collect_ready = true
		direction = Vector3.ZERO
	if crossing_gate != "" and (pos.distance_to(crossing_exit) <= .22 or gates[crossing_gate].opened or elapsed_s >= crossing_deadline):
		crossing_gate = ""
	var avoiding := elapsed_s < avoid_gate_until
	var interact := collect_ready or crossing_gate != "" or (not avoiding and _portal_to_use(pos, target))
	if elapsed_s < avoid_gate_until:
		direction = avoid_gate_direction
	if crossing_gate != "":
		direction = (crossing_exit-pos).normalized()
	if not tactical or (not interact and player_body.test_move(player_body.transform, direction * .15)):
		direction = _steer(pos, direction, interact)
	if (decision_variant == "mobile" or paced) and not interact and not tactical:
		if elapsed_s >= mobile_until:
			mobile_course = _mobile_direction(pos,direction,elapsed_s-seen_at < 1.5)
			mobile_until = elapsed_s+.15
		direction = mobile_course
		for id in known_supplies:
			if not collected.has(id) and pos.distance_to(known_supplies[id]) < float(combat.supplies.pickup_radius_m)*.9:
				interact = true
				direction = Vector3.ZERO
				break
	var aim_point := last_seen if not tactical and loaded + reserve > 0 and elapsed_s - seen_at < 1.0 else target
	var look := aim_point - pos
	if look.length_squared() > .001:
		heading = rotate_toward(heading, atan2(look.z, look.x), deg_to_rad(float(combat.player.turn_deg_per_s)) * delta)
	else:
		heading += deg_to_rad(float(combat.player.turn_deg_per_s)) * delta
	var aligned := absf(angle_difference(heading, atan2(look.z,look.x))) <= deg_to_rad(float(combat.player.aim_fov_deg)) / 2.0
	var shooting_gap := pos.distance_to(last_seen) > 3.0
	if seen and (decision_variant in ["reengage","combined","mobile"] or paced):
		var contact := _clear_ray(player_body.position+Vector3.UP*.25,boss_body.position+Vector3.UP*.25,player_body,boss_body,true)
		var escape_margin := maxf(0,pos.distance_to(last_seen)-float(combat.boss.grab_range_m))/float(combat.boss.speed_mps)
		shooting_gap = not contact or escape_margin + float(combat.boss.attack_warning_s) > float(combat.weapon.aim_s) + float(combat.player.reaction_s)*reaction_scale + .25
		if paced:
			# Sprint during cooldown. Leave enough time to finish aiming and get clear of a grab.
			shooting_gap = cooldown_s <= 0.0 and (not contact or pos.distance_to(last_seen) > 2.5)
	var can_aim := loaded > 0 and seen and aligned and shooting_gap and not interact and not tactical
	aim_on_target_s = aim_on_target_s + delta if can_aim else 0.0
	var shoot := can_aim and aim_on_target_s + 1e-8 >= float(combat.player.reaction_s) * reaction_scale
	# Draw a new aiming error after each fired shot; this stream is independent of route choices.
	if cooldown_s > 0.0 and cooldown_s + 1e-8 >= float(combat.weapon.fire_interval_s):
		aim_error = aiming.randfn(0.0, deg_to_rad(float(combat.weapon.angular_error_sd_deg)) * error_scale)
	return {"move_direction":[direction.x,direction.z], "aim":shoot, "boss_velocity":[0,0],
		"heading":heading, "bearing":heading + aim_error, "fire":shoot,
		"reload":loaded == 0 or (loaded <= 3 and elapsed_s - seen_at >= 1.5),
		"interact":interact}

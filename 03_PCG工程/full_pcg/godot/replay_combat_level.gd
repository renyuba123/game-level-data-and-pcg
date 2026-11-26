extends "res://full_pcg/godot/combat_level.gd"

var command: Dictionary
var native_boss := false
var score_telemetry := false
var reaction_scale := 1.0


func _move_direction() -> Vector3:
	return Vector3(float(command.move_direction[0]), 0, float(command.move_direction[1]))


func _aim_held() -> bool:
	return command.aim


func _player_move(delta: float) -> void:
	if command.has("move_direction"):
		super._player_move(delta)
		return
	# Historical inputs record absolute velocity, including reconstructed Python traces.
	if vault_id != "":
		_step_vault(delta)
		return
	var velocity_xz: Array = command.player_velocity
	player_body.velocity = Vector3(float(velocity_xz[0]), 0, float(velocity_xz[1])) if stalker_control_s <= 0 else Vector3.ZERO
	player_body.move_and_slide()


func _boss_move(delta: float) -> void:
	if native_boss:
		super._boss_move(delta)
		return
	var velocity_xz: Array = command.boss_velocity
	boss_body.velocity = Vector3(float(velocity_xz[0]), 0, float(velocity_xz[1]))
	boss_body.move_and_slide()


func _reload_held() -> bool:
	return command.reload


func _interaction_held() -> bool:
	return command.interact


func _fire_held() -> bool:
	return command.fire


func _mouse_target() -> Vector3:
	var bearing := float(command.bearing)
	return player_body.position + Vector3.UP * .25 + Vector3(cos(bearing), 0, sin(bearing)) * 10


func _save_episode() -> void:
	# The SceneTree writes all replay results to the configured evidence directory.
	pass


func sample() -> Dictionary:
	var p := player_body.position
	var b := boss_body.position
	var heading := Vector3(cos(command.heading), 0, sin(command.heading))
	var offset := b - p
	offset.y = 0
	var in_vision := offset.length() <= float(combat.player.vision_range_m) \
		and offset.normalized().dot(heading) >= cos(deg_to_rad(float(combat.player.fov_deg) / 2.0))
	var visible := in_vision and _clear_ray(p + Vector3.UP * .25, b, player_body, boss_body)
	var opened: Array = []
	for id in gates:
		if gates[id].opened:
			opened.append(id)
	opened.sort()
	var snapshot := {"p": [p.x, p.z], "b": [b.x, b.z], "gap": offset.length(), "hp": boss_hp,
		"player_hp": player_hp,
		"loaded": loaded, "reserve": reserve, "phase": phase, "visible": visible,
		"pickup": pickup_id, "reload_left": maxf(0, reload_s), "vault": vault_id, "opened": opened}


	if score_telemetry:
		snapshot.merge(_score_observation(heading,visible))
	return snapshot


func _route_time(actor: CharacterBody3D, reach: float, speed: float, warning: float, remaining: float, budget: float) -> Variant:
	var source := actor.position
	var destination := player_body.position
	var contact := _clear_ray(source + Vector3.UP * .25, destination + Vector3.UP * .25,actor,player_body,true)
	var gap := source.distance_to(destination)
	if contact and gap <= reach:
		return maxf(0.0,warning - remaining)
	if gap > reach + speed * budget:
		return null
	if actor == stalker_body:
		if not contact:
			return null
		var travel := destination - source
		travel.y = 0
		var step := travel.normalized() * maxf(0.0,travel.length() - reach)
		if actor.test_move(actor.transform,step):
			return null
		return step.length()/speed + warning
	source.y = 0
	destination.y = 0
	var path := nav_path("boss",source,destination)
	if path.is_empty() or path[-1].distance_to(destination) > reach:
		return null
	var length := source.distance_to(path[0])
	for index in range(1,path.size()):
		length += path[index-1].distance_to(path[index])
	return maxf(0.0,length - (reach - path[-1].distance_to(destination)))/speed + warning


func _score_observation(heading: Vector3, boss_visible: bool) -> Dictionary:
	var player := player_body.position
	var stalker_visible := false
	var reaction := float(combat.player.reaction_s) * reaction_scale
	# Limit the path query to the maximum distance reachable in the scoring horizon.
	var budget := reaction + float(combat.weapon.aim_s) + float(combat.weapon.fire_interval_s) + float(combat.score_sampling.threat_margin_s)
	var boss_eta = _route_time(boss_body, float(combat.boss.grab_range_m), float(combat.boss.speed_mps), float(combat.boss.attack_warning_s),attack_s,budget)
	var stalker_eta = null
	if is_instance_valid(stalker_body):
		var look := stalker_body.position - player
		look.y = 0
		stalker_visible = look.length() <= float(combat.player.vision_range_m) and look.normalized().dot(heading) >= cos(deg_to_rad(float(combat.player.fov_deg))/2.0) and _clear_ray(player+Vector3.UP*.25,stalker_body.position,player_body,stalker_body)
		if stalker_retreat_s <= 0:
			stalker_eta = _route_time(stalker_body,.9,float(combat.stalker.speed_mps),float(combat.stalker.warning_s),stalker_warning_s,budget)
	var escape = null
	var away := player - boss_body.position
	away.y = 0
	if vault_id == "" and stalker_control_s <= 0:
		var clearance := 2.0 * float(combat.player.radius_m)
		for i in range(8):
			var motion := away.normalized().rotated(Vector3.UP,i*TAU/8.0) * clearance
			if motion.dot(away) <= 0.0 or player_body.test_move(player_body.transform,motion):
				continue
			if is_instance_valid(stalker_body) and (player+motion).distance_to(stalker_body.position)<player.distance_to(stalker_body.position):
				continue
			escape = clearance/float(combat.player.speed_mps)
			break
	var aim := boss_body.position - player
	aim.y = 0
	var muzzle_clear := aim.length() <= float(combat.weapon.range_m) and _clear_ray(player + Vector3.UP * .25,boss_body.position,player_body,boss_body)
	var aligned := aim.normalized().dot(heading) >= cos(deg_to_rad(float(combat.player.aim_fov_deg))/2.0)
	return {"stalker_visible":stalker_visible,"boss_visible":boss_visible,"boss_eta_s":boss_eta,"stalker_eta_s":stalker_eta,
		"escape_s":escape,"reaction_s":reaction,"threat_horizon_s":budget,"muzzle_clear":muzzle_clear,
		"ready":boss_visible and muzzle_clear and aligned and loaded > 0 and reload_s <= 0 and vault_id == "" and stalker_control_s <= 0 and pickup_s <= 0,
		"action_risk":reload_s > 0 or pickup_s > 0}

"""Adapt the existing variable-topology geometry to the two-stage Boss protocol.

The Full-PCG generator remains the sole source of polygons and portals. This
module only chooses combat positions and validates their meaning.
"""
import copy
import math

import networkx as nx
from shapely.geometry import Point, Polygon, shape

from full_pcg.common import digest
from full_pcg.geometry import generate as generate_geometry
from full_pcg.geometric_graph import reconstruct
from full_pcg.topology import graph, sample
from full_pcg.validation import validate as validate_geometry

from .contracts import SCHEMA, validate_genome
from .protocol import default_combat, validate_combat


def prepare_topology(seed, geometry_config):
    """Choose a real high-degree core without changing the sampled graph."""
    genome = copy.deepcopy(sample(seed, geometry_config))
    net = graph(genome)
    usable = nx.Graph()
    usable.add_nodes_from(net)
    usable.add_edges_from((e["a"], e["b"]) for e in genome["edges"] if e["kind"] != "break")
    eligible = [r for r in genome["rooms"] if net.degree[r["id"]] >= 3 and usable.degree[r["id"]] >= 2]
    if not eligible:
        return genome, {"ok": False, "issues": ["no_connected_core_with_two_initial_exits"]}
    core = max(eligible, key=lambda r: (net.degree[r["id"]], usable.degree[r["id"]], r["id"]))
    core_id = core["id"]
    core.update(role="hub", width=4.25, height=4.0, shape="chamfer", rotation=0)
    for room in genome["rooms"]:
        if room["id"] != core_id and room["role"] == "hub":
            room["role"] = "side"
    # A core pillar can completely control the opening fight. Preserve the
    # fixed obstacle count while moving any sampled core obstacle to a side room.
    used = {o["room"] for o in genome["obstacles"]}
    for obstacle in genome["obstacles"]:
        if obstacle["room"] != core_id:
            continue
        replacements = sorted((r for r in genome["rooms"] if r["id"] not in used and r["id"] != core_id),
                              key=lambda r: (-net.degree[r["id"]], r["id"]))
        if not replacements:
            return genome, {"ok": False, "issues": ["no_room_for_core_obstacle"]}
        replacement = replacements[0]
        replacement.update(width=4.0, height=3.6, shape="chamfer", rotation=(replacement["rotation"] // 90) * 90)
        used.remove(core_id)
        used.add(replacement["id"])
        obstacle["room"] = replacement["id"]
    genome["spawn"] = core_id
    genome["boss"] = core_id
    genome["operations"] = [*genome["operations"], {"op": "choose_combat_core", "room_id": core_id,
                                                  "all_open_degree": net.degree[core_id],
                                                  "initial_player_exits": usable.degree[core_id]}]
    return genome, {"ok": True, "issues": [], "core_room_id": core_id}


def _candidates(poly, free, radius):
    safe = poly.buffer(-(radius + .06)).intersection(free)
    minx, miny, maxx, maxy = poly.bounds
    pts = []
    x = minx
    while x <= maxx:
        y = miny
        while y <= maxy:
            if safe.covers(Point(x, y)):
                pts.append((round(x, 4), round(y, 4)))
            y += .35
        x += .35
    return pts


def _choose_spawns(layout, core_id, combat, config):
    room = next(r for r in layout["rooms"] if r["id"] == core_id)
    poly = shape({"type": "Polygon", "coordinates": [room["polygon"]]})
    floor = shape(layout["floor"])
    base = shape(layout["base_obstacles"])
    player_free = floor.difference(base.buffer(config["player_radius"] + .025))
    boss_free = floor.difference(base.buffer(config["boss_radius"] + .025))
    players = _candidates(poly, player_free, config["player_radius"])
    bosses = _candidates(poly, boss_free, config["boss_radius"])
    if not players or not bosses:
        raise ValueError("core_has_no_clear_spawn_pair")
    # Bound the opening gap: it should permit a reaction but retain contact.
    pair = max(((a, b) for a in players for b in bosses if math.dist(a, b) <= 4.6),
               key=lambda ab: (math.dist(*ab), ab[0], ab[1]), default=None)
    if pair is None or math.dist(*pair) < combat["boss"]["grab_range_m"] + .8:
        raise ValueError("core_opening_gap_too_small")
    a, b = pair
    pa = math.atan2(b[1] - a[1], b[0] - a[0])
    pb = math.atan2(a[1] - b[1], a[0] - b[0])
    margin = (math.dist(a, b) - combat["boss"]["grab_range_m"]) / combat["boss"]["speed_mps"]
    margin += combat["boss"]["attack_warning_s"] - combat["player"]["reaction_s"]
    return ({"room": core_id, "position": list(a), "heading_rad": pa},
            {"room": core_id, "position": list(b), "heading_rad": pb}, margin)


def _place_supplies(layout, genome, combat):
    count = combat["supplies"]["pack_count"]
    core = layout["spawn"]["room"]
    net = graph(genome)
    # Disperse fixed-count packs, with positions rather than amounts as genes.
    candidates = [r for r in layout["rooms"] if r["id"] != core]
    candidates.sort(key=lambda r: (-nx.shortest_path_length(net, core, r["id"]), r["id"]))
    if len(candidates) < count:
        raise ValueError("insufficient_distinct_supply_rooms")
    return [{"id": f"supply_{i:03d}", "room_id": r["id"], "position": r["center"]}
            for i, r in enumerate(candidates[:count])]


def contract_genome(genome, layout):
    """Versioned portable projection; source genes remain in `source_genome`."""
    rooms = []
    for r in layout["rooms"]:
        actual = Polygon(r["polygon"])
        position = [actual.centroid.x, actual.centroid.y]
        outline = [[x - position[0], y - position[1]] for x, y in list(actual.exterior.coords)[:-1]]
        rooms.append({"id": r["id"], "position": position, "rotation_deg": 0,
                      "outline_local": outline, "role": r["role"]})
    projected = {"schema_version": SCHEMA, "units": "model_m", "seed": genome["seed"], "rooms": rooms,
                 "connections": [{"id": e["id"], "a": e["a"], "b": e["b"], "kind": e["kind"]} for e in (layout["portals"] if layout.get("schema_version")==5 else genome["edges"])],
                 "spawn": {role: {"room_id": layout[field]["room"], "position": layout[field]["position"],
                                  "heading_rad": layout[field]["heading_rad"]}
                           for role, field in (("player", "spawn"), ("boss", "boss"))},
                 "obstacles": [{"id": o["id"], "room_id": o["room"], "position": o["position"]}
                               for o in layout["obstacles"]],
                 "supplies": layout["supplies"]}
    if layout.get("schema_version")==5:
        projected["schema_version"]="combat-shell-genome/1"
        projected["connections"]=[copy.deepcopy(p) for p in layout["portals"]]
        projected["obstacles"]=[dict(o,room_id=o["room"]) for o in layout["obstacles"]]
    validate_genome(projected)
    return projected


def validate_layout(layout, genome, geometry_config, combat):
    issues = []
    net = graph(genome)
    core = layout["spawn"]["room"]
    assert core == layout["boss"]["room"]
    sorted_areas = sorted((r["area"] for r in layout["rooms"]), reverse=True)
    area_floor = sorted_areas[max(0, math.ceil(len(sorted_areas) * .25) - 1)]
    room = next(r for r in layout["rooms"] if r["id"] == core)
    if room["area"] + 1e-6 < area_floor:
        issues.append("core_not_top_area_quartile")
    if net.degree[core] < 3:
        issues.append("core_degree_below_three")
    initial = net.copy()
    initial.remove_edges_from((e["a"], e["b"]) for e in genome["edges"] if e["kind"] == "break")
    if initial.degree[core] < 2:
        issues.append("core_has_fewer_than_two_initial_player_exits")
    if not nx.is_connected(initial):
        issues.append("initial_player_graph_disconnected")
    if len(layout["supplies"]) != combat["supplies"]["pack_count"]:
        issues.append("supply_pack_count_mismatch")
    floor = shape(layout["floor"])
    base = shape(layout["base_obstacles"])
    player_free = floor.difference(base.buffer(geometry_config["player_radius"] + .025))
    boss_free = floor.difference(base.buffer(geometry_config["boss_radius"] + .025))
    for actor, free in (("spawn", player_free), ("boss", boss_free)):
        if not free.covers(Point(layout[actor]["position"])):
            issues.append(actor + "_collision")
    for item in layout["supplies"]:
        if not player_free.covers(Point(item["position"])):
            issues.append("supply_collision:" + item["id"])
        if item["room_id"] not in initial:
            issues.append("supply_unknown_room:" + item["id"])
    if layout["opening_reaction_margin_s"] <= 0:
        issues.append("no_opening_reaction_margin")
    geometric = reconstruct(layout, geometry_config)
    issues.extend(geometric["issues"])
    prior = validate_geometry(layout, geometry_config)
    # The old exit target is an after-combat marker. Its time/detour criteria
    # cannot invalidate a fight. Retain the old report for diagnostics.
    old_exit_issues = {"escape_too_short", "escape_detour_excessive", "exit_endpoint_disconnected"}
    issues.extend(issue for issue in prior["issues"] if issue not in old_exit_issues)
    return {"ok": not issues, "issues": sorted(set(issues)), "geometry": geometric,
            "legacy_physical_diagnostics": prior,
            "combat_evidence": "topology_and_clearance_only; firing/real Boss navigation not yet verified"}


def generate(seed, geometry_config, combat=None):
    combat = default_combat() if combat is None else combat
    validate_combat(combat)
    genome, prepared = prepare_topology(seed, geometry_config)
    if not prepared["ok"]:
        return {"source_genome": genome}, prepared
    layout, report = generate_geometry(genome, geometry_config)
    if not report["ok"]:
        return {"source_genome": genome, "partial_layout": layout}, report
    try:
        player, boss, margin = _choose_spawns(layout, prepared["core_room_id"], combat, geometry_config)
        layout["spawn"] = player
        layout["boss"] = boss
        layout["opening_reaction_margin_s"] = margin
        layout["supplies"] = _place_supplies(layout, genome, combat)
        layout["combat_protocol_id"] = combat["protocol_id"]
        layout["exit"]["victory_condition"] = False
        layout.pop("layout_hash", None)
        layout["layout_hash"] = digest(layout)
        projected = contract_genome(genome, layout)
        qa = validate_layout(layout, genome, geometry_config, combat)
        return {"source_genome": genome, "combat_genome": projected, "layout": layout}, qa
    except ValueError as exc:
        return {"source_genome": genome, "partial_layout": layout}, {"ok": False, "issues": [str(exc)]}

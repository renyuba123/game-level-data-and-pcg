"""Deterministic 2D clearance/navigation pursuit proxy; final acceptance uses Godot physics."""
from __future__ import annotations
import math
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union
from metrics import candidate_geometry

class Navigation:
    def __init__(self, floor, obstacles, radius, cell=.35, anchors=()):
        free = floor.difference(obstacles.buffer(radius + .025)).buffer(-.01)
        x0, y0, x1, y1 = floor.bounds
        points, indices = [], {}
        for ix, x in enumerate(np.arange(x0, x1 + cell, cell)):
            for iy, y in enumerate(np.arange(y0, y1 + cell, cell)):
                if free.covers(Point(x, y)):
                    indices[ix, iy] = len(points)
                    points.append((x, y))
        for point in anchors:
            if free.covers(Point(point)): points.append(tuple(point))
        points = list(dict.fromkeys(tuple(round(float(v), 9) for v in p) for p in points))
        if not points: raise ValueError("empty clearance navigation")
        self.points = np.array(points)
        rows, cols, data = [], [], []
        for a, b in cKDTree(self.points).query_pairs(cell * 1.45):
                if free.covers(LineString([points[a], points[b]])):
                    rows.extend((a, b)); cols.extend((b, a))
                    distance = float(np.linalg.norm(self.points[a] - self.points[b]))
                    data.extend((distance, distance))
        self.graph = csr_matrix((data, (rows, cols)), shape=(len(points), len(points)))
        self.tree = cKDTree(self.points)
        self.fields = {}
        self.free = free

    def nearest(self, point):
        return int(self.tree.query(point)[1])

    def route(self, start, end):
        a, b = self.nearest(start), self.nearest(end)
        if not self.free.covers(LineString([start, self.points[a]])): return []
        if b not in self.fields:
            self.fields[b] = dijkstra(self.graph, directed=False, indices=b, return_predecessors=True)
        distance, previous = self.fields[b]
        if not np.isfinite(distance[a]): return []
        path = [self.points[a]]
        while a != b:
            a = int(previous[a])
            if a < 0: return []
            path.append(self.points[a])
        return path

def move(point, path, budget):
    result = np.array(point, dtype=float)
    trace = [result.copy()]
    for target in path:
        delta = target - result
        length = float(np.linalg.norm(delta))
        if length < 1e-6: continue
        if length <= budget:
            result = np.array(target)
            trace.append(result.copy())
            budget -= length
        else:
            result = result + delta / length * budget
            trace.append(result.copy())
            break
    return result, LineString(trace if len(trace) > 1 else trace * 2)

def door_anchors(layout):
    points = []
    # Preserve narrow corridor medial paths even when the regular lattice misses them.
    for room in layout["rooms"]:
        polygon = np.array(room["polygon"])
        center = np.array(room["center"])
        span = float(np.max(np.linalg.norm(polygon-center, axis=1)))
        for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
            direction = (b-a)/np.linalg.norm(b-a)
            points.extend(center + direction*t for t in np.arange(-span, span+.05, .15))
    for e in layout["edges"]:
        a, b = np.array(e["shared_segment"])
        tangent = (b-a) / np.linalg.norm(b-a)
        normal = np.array([-tangent[1], tangent[0]])
        points.extend(np.array(e["door_anchor"]) + normal*t for t in np.arange(-1., 1.01, .1))
    return points

def clearance_check(layout):
    anchors = door_anchors(layout)
    report = {}
    for role, state, radius in [("player_initial", "initial", .35), ("boss_initial", "initial", .58),
                                 ("player_open", "all_open", .35), ("boss_open", "all_open", .58)]:
        obstacles, floor = candidate_geometry(layout, state)
        nav = Navigation(floor, obstacles, radius, anchors=anchors)
        centers = []
        for room in layout["rooms"]:
            safe = Polygon(room["polygon"]).intersection(nav.free)
            if safe.is_empty: raise ValueError(f"{role}: room lacks clearance")
            p = safe.representative_point()
            centers.append([p.x, p.y])
        origin = centers[layout["boss_room"] if role.startswith("boss") else layout["spawn_room"]]
        reachable = sum(bool(nav.route(origin, center)) for center in centers)
        if role != "boss_initial" and reachable != len(centers): raise ValueError(f"{role}: disconnected room")
        report[role] = {"reachable_rooms": reachable, "total_rooms": len(centers), "nodes": len(nav.points)}
    return report

def run(layout, heldout=False):
    base, floor = candidate_geometry(layout, "all_open")
    centers = [np.array(room["center"]) for room in layout["rooms"]]
    polygons = [Polygon(room["polygon"]) for room in layout["rooms"]]
    anchors = door_anchors(layout)
    boss_nav = Navigation(floor, base, .58, anchors=anchors)
    room_areas = [Polygon(r["polygon"]).area for r in layout["rooms"]]
    portals = {}
    for edge in layout["edges"]:
        a, b = np.array(edge["shared_segment"])
        tangent = (b-a) / np.linalg.norm(b-a)
        center = np.array(edge["door_anchor"])
        width = edge["door_width_m"]
        full = LineString([center-tangent*width/2, center+tangent*width/2])
        if edge["kind"] == "through":
            shoulder = unary_union([
                LineString([center-tangent*width/2, center-tangent*.45]),
                LineString([center+tangent*.45, center+tangent*width/2])]).buffer(.09, cap_style="flat")
        else:
            shoulder = full.buffer(.09, cap_style="flat")
        portals[edge["id"]] = {"edge": edge, "full": full, "obstacle": shoulder}
    nav_cache = {}
    def state(opened):
        key = tuple(sorted(opened))
        if key not in nav_cache:
            obstacles = unary_union([base, *[p["obstacle"] for key_, p in portals.items()
                if p["edge"]["kind"] != "normal" and key_ not in opened]])
            nav_cache[key] = (Navigation(floor, obstacles, .35, anchors=anchors), obstacles)
        return nav_cache[key]
    episodes = []
    seed_values = [104729, 130363] if heldout else [11, 29]
    for policy in ["exit", "distance", "occlusion"]:
        for seed in seed_values:
            rng = np.random.default_rng(seed)
            opened, squeezed = set(), set()
            nav, obstacles = state(opened)
            player = centers[layout["spawn_room"]] + rng.uniform(-.15, .15, 2)
            boss = centers[layout["boss_room"]] + rng.uniform(-.15, .15, 2)
            player = nav.points[nav.nearest(player)].copy()
            boss = boss_nav.points[boss_nav.nearest(boss)].copy()
            exit_point = centers[layout["exit_room"]]
            exit_point = nav.points[nav.nearest(exit_point)]
            target = exit_point
            smash, squeeze = {}, {}
            visible_ticks = near_ticks = stuck_ticks = 0
            visited = []
            outcome = "timeout"
            for tick in range(200):
                dt = .2
                nav, obstacles = state(opened)
                if tick % 3 == 0:
                    if policy == "exit" or tick > 130:
                        target = exit_point
                    else:
                        scores = []
                        for center in centers:
                            reachable = nav.route(player, center)
                            if not reachable:
                                scores.append(-1e6)
                                continue
                            distance = float(np.linalg.norm(center-boss))
                            visible = not obstacles.intersects(LineString([center, boss]))
                            scores.append(distance + (4.0 * (not visible) if policy == "occlusion" else 0) -
                                          .2 * float(np.linalg.norm(center-player)))
                        target = centers[int(np.argmax(scores))]
                path = nav.route(player, target)
                if not path: stuck_ticks += 1
                proposed, moving = move(player, path, 5.0*dt)
                for key in list(squeezed):
                    if portals[key]["full"].distance(Point(player)) > 1.0:
                        squeezed.remove(key)
                        squeeze.pop(key, None)
                for key, portal in portals.items():
                    if portal["edge"]["kind"] != "through" or key in opened or key in squeezed: continue
                    if moving.intersects(portal["full"].buffer(.2)):
                        squeeze[key] = squeeze.get(key, 0) + dt
                        if squeeze[key] < .65: proposed = player.copy()
                        else: squeezed.add(key)
                        break
                player = proposed
                boss_path = boss_nav.route(boss, player)
                proposed, motion = move(boss, boss_path, 3.25*dt)
                for key, portal in portals.items():
                    kind = portal["edge"]["kind"]
                    if kind == "normal" or key in opened: continue
                    if motion.intersects(portal["obstacle"].buffer(.58 + .02)):
                        smash[key] = smash.get(key, 0) + dt
                        proposed = boss.copy()
                        if smash[key] >= (2.0 if kind == "through" else 3.0):
                            opened.add(key)
                        break
                boss = proposed
                distance = float(np.linalg.norm(player-boss))
                visible = not obstacles.intersects(LineString([player,boss]))
                visible_ticks += int(visible)
                near_ticks += int(distance < 5 and visible)
                room_id = next((i for i,p in enumerate(polygons) if p.covers(Point(player))), -1)
                if room_id >= 0: visited.append(room_id)
                if distance < .93 and visible:
                    outcome = "caught"; break
                if np.linalg.norm(player-exit_point) < .8:
                    outcome = "escaped"; break
            duration = (tick+1)*.2
            episodes.append({"policy": policy, "seed": seed, "outcome": outcome,
                "duration": duration, "visibility_fraction": visible_ticks/(tick+1),
                "near_fraction": near_ticks/(tick+1), "stuck_fraction": stuck_ticks/(tick+1),
                "visited_rooms": len(set(visited)), "opened": sorted(opened),
                "route": [r for i,r in enumerate(visited) if i==0 or r!=visited[i-1]]})
    n = len(episodes)
    escaped = sum(e["outcome"] == "escaped" for e in episodes)/n
    early = sum(e["outcome"] == "caught" and e["duration"] < 3 for e in episodes)/n
    timeout = sum(e["outcome"] == "timeout" for e in episodes)/n
    near = float(np.mean([e["near_fraction"] for e in episodes]))
    stuck = float(np.mean([e["stuck_fraction"] for e in episodes]))
    coverage = float(np.mean([e["visited_rooms"] for e in episodes]))/len(centers)
    routes = [set(zip(e["route"], e["route"][1:])) for e in episodes]
    differences = [1-len(a&b)/len(a|b) for i,a in enumerate(routes) for b in routes[i+1:] if a|b]
    diversity = .5*coverage + .5*float(np.mean(differences or [0]))
    fairness = early + stuck + max(0., .5-escaped) + .5*timeout
    pressure = abs(near-.4) + max(0., .1-near)
    return {"method": "2D clearance-grid pursuit proxy; fixed speeds and action times",
            "heldout": heldout, "episodes": episodes, "fairness_loss": fairness,
            "pressure_loss": pressure, "route_diversity": diversity,
            "escape_fraction": escaped, "early_catch_fraction": early,
            "timeout_fraction": timeout, "near_fraction": near, "stuck_fraction": stuck}

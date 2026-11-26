from __future__ import annotations
import csv
from contextlib import nullcontext
import time
from pathlib import Path
import numpy as np
import ezdxf
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from common import CLI, METRICS, QUANTILES, ROOT, SOURCE_MAPS, WORK, command, digest, read_json, write_json

ROLE = {"R05": "hub", "R03": "arena", "R07": "corridor", "R09": "corridor", "R11": "terminal"}

def table(path):
    with Path(path).open(encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))

def make_profile(rows, rooms):
    result = {"count": len(rows), "metrics": {}, "roles": {}}
    points = np.array([[float(r["x"]) / 1000, float(r["y"]) / 1000] for r in rows])
    groups = {}
    for room in rooms:
        role = ROLE.get(room.get("source_id", room.get("room_id")), "side")
        polygon = Polygon(room.get("polygon", room.get("polygon_m")))
        groups.setdefault(role, np.zeros(len(points), dtype=bool))
        groups[role] |= np.array([polygon.covers(Point(x, y)) for x, y in points])
    for name in METRICS:
        values = np.array([float(r[name]) for r in rows])
        valid = np.isfinite(values) & (values >= 0)
        if valid.sum() != len(values):
            raise ValueError(f"invalid metric values: {name}")
        q = np.quantile(values, QUANTILES)
        scale = max(float(q[-1] - q[0]), abs(float(q[2])) * .01, 1e-9)
        result["metrics"][name] = {"quantiles": q.tolist(), "scale": scale,
            "min": float(values.min()), "max": float(values.max()), "mean": float(values.mean())}
        threshold = np.quantile(values, .9)
        for role, mask in groups.items():
            if mask.sum() == 0: continue
            result["roles"].setdefault(role, {})[name] = {
                "quantiles": np.quantile(values[mask], QUANTILES).tolist(),
                "top_decile_fraction": float(np.mean(values[mask] >= threshold)),
                "sample_count": int(mask.sum())}
    return result

def distance(candidate, reference):
    errors = {}
    for name in METRICS:
        base = reference["metrics"][name]
        scale = base["scale"]
        global_error = float(np.mean(np.abs(np.array(candidate["metrics"][name]["quantiles"]) -
                                                np.array(base["quantiles"]))) / scale)
        regional = []
        for role, fields in reference["roles"].items():
            other = candidate["roles"].get(role, {}).get(name)
            if not other:
                regional.append(2.)
            else:
                regional.append(float(np.mean(np.abs(np.array(other["quantiles"]) -
                    np.array(fields[name]["quantiles"]))) / scale) +
                    abs(other["top_decile_fraction"] - fields[name]["top_decile_fraction"]))
        errors[name] = .5 * global_error + .5 * float(np.mean(regional or [0.]))
    return float(np.mean(list(errors.values()))), errors

def candidate_geometry(layout, state="initial"):
    key = "walls_all_open" if state == "all_open" else "walls_initial"
    walls = unary_union([LineString(segment).buffer(.09, cap_style="flat", join_style="mitre")
                         for segment in layout[key] if LineString(segment).length > .01])
    blocks = [Point(item["position"]).buffer(item["radius"], quad_segs=16) for item in layout["blocks"]]
    obstacles = unary_union([walls, *blocks])
    floor = unary_union([Polygon(room["polygon"]) for room in layout["rooms"]])
    return obstacles, floor

def write_candidate_dxf(layout, state, path):
    obstacles, floor = candidate_geometry(layout, state)
    doc = ezdxf.new("R2010")
    doc.units = 4
    space = doc.modelspace()
    shapes = list(obstacles.geoms) if hasattr(obstacles, "geoms") else [obstacles]
    for shape in shapes:
        for ring in [shape.exterior, *shape.interiors]:
            coords = list(ring.coords)
            for a, b in zip(coords, coords[1:]):
                space.add_line((a[0] * 1000, a[1] * 1000), (b[0] * 1000, b[1] * 1000))
    doc.saveas(path)
    fills = []
    for room in layout["rooms"]:
        free = Polygon(room["polygon"]).difference(obstacles)
        if free.is_empty: raise ValueError("room has no free floor")
        p = free.representative_point()
        fills.append((p.x * 1000, p.y * 1000))
    return fills

def analyze(dxf, fills, directory, grid=400, *, cli=CLI, trace=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    # DXF GUID/timestamp metadata changes on save; cache the actual line geometry.
    lines = []
    for entity in ezdxf.readfile(dxf).modelspace():
        if entity.dxftype() != "LINE": raise ValueError("analysis DXF must contain explicit LINE geometry")
        ends = sorted([tuple(round(float(v), 6) for v in entity.dxf.start), tuple(round(float(v), 6) for v in entity.dxf.end)])
        lines.append(ends)
    recipe = {"engine_sha256": digest(cli), "grid": grid, "radius": "n",
              "geometry_sha256": digest(sorted(lines)), "fills": fills, "metrics": METRICS}
    key = digest(recipe)
    manifest = directory / "complete.json"
    if manifest.exists() and read_json(manifest).get("key") == key:
        return table(directory / "metrics.csv"), {**read_json(manifest), "cache_hit": True}
    points = directory / "fill.tsv"
    points.write_text("X\tY\n" + "".join(f"{x}\t{y}\n" for x, y in fills), encoding="utf-8")
    imported, prepared = directory / "import.graph", directory / "prepared.graph"
    visible, metric = directory / "visibility.graph", directory / "metric.graph"
    times = {}
    operations = [
        ("import", ["-f", dxf, "-o", imported, "-m", "IMPORT"]),
        ("prepare", ["-f", imported, "-o", prepared, "-m", "VISPREP", "-pg", grid, "-pf", points, "-pm"]),
        ("visibility", ["-f", prepared, "-o", visible, "-m", "VGA", "-vm", "visibility", "-vg", "-vr", "n"]),
        ("metric", ["-f", visible, "-o", metric, "-m", "VGA", "-vm", "metric", "-vr", "n"]),
        ("export", ["-f", metric, "-o", directory / "metrics.csv", "-m", "EXPORT", "-em", "pointmap-data-csv"]),
    ]
    for name, args in operations:
        log = directory / f"{name}.log"
        with trace("depthmap", operation=name, log=str(log)) if trace else nullcontext():
            times[name] = command([cli, *args], log, 600)
    rows = table(directory / "metrics.csv")
    if not rows: raise ValueError("Depthmap returned zero points")
    result = {"key": key, "recipe": recipe, "timing_seconds": times, "point_count": len(rows)}
    write_json(manifest, result)
    return rows, {**result, "cache_hit": False}

def baseline_dxf(profile, state, path):
    doc = ezdxf.new("R2010")
    doc.units = 4
    space = doc.modelspace()
    for wall in profile["wall_segments"]:
        a, b = wall["start_m"], wall["end_m"]
        space.add_line((a[0] * 1000, a[1] * 1000), (b[0] * 1000, b[1] * 1000))
    for block in profile["blocks"]:
        x, y = block["center_m"]
        radius = block["radius_m"]
        angles = np.linspace(0, 2*np.pi, 65)
        vertices = [(1000*(x+radius*np.cos(a)), 1000*(y+radius*np.sin(a))) for a in angles]
        for a, b in zip(vertices, vertices[1:]): space.add_line(a, b)
    # Source connection symbols are not wall boundaries. Break closures are explicit only.
    if state == "initial":
        for conn in profile["connections"]:
            if conn["kind"] == "break":
                a, b = conn["start_m"], conn["end_m"]
                space.add_line((a[0]*1000, a[1]*1000), (b[0]*1000, b[1]*1000))
    doc.saveas(path)
    fills = []
    blocked = unary_union([*[Point(b["center_m"]).buffer(b["radius_m"]) for b in profile["blocks"]],
        *[LineString([wall["start_m"],wall["end_m"]]) for wall in profile["wall_segments"]]])
    # Convex centroids can land inside the terminal square pillar, which is drawn
    # as wall lines rather than a block-layer circle. Seed only known free VGA cells.
    original_points = [Point(float(r["x"])/1000,float(r["y"])/1000) for r in table(SOURCE_MAPS / "vga.csv")]
    for room in profile["convex_rooms"]:
        region = Polygon(room["polygon_m"])
        candidates = [p for p in original_points if region.covers(p)]
        if not candidates: raise ValueError("No verified free VGA cell in source convex region")
        p = max(candidates,key=lambda p:min(p.distance(blocked),p.distance(region.boundary)))
        fills.append((p.x*1000, p.y*1000))
    return fills

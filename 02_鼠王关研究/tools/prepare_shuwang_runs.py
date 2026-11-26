"""Prepare one shared source/depthmap/shuwang.graph map and five source-specific run records."""
import csv
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "maps/ratking/shuwang"
GRAPH = ROOT / "source/depthmap/shuwang.graph"
DXF = ROOT / "source/cad/鼠王关.dxf"
SOURCES = ["source/illustrator/鼠王关玩家路线图001.ai", "source/illustrator/002.ai", "source/illustrator/003_.ai", "source/illustrator/004.ai", "source/illustrator/005_.ai"]
GRAPH_HASH = hashlib.sha256(GRAPH.read_bytes()).hexdigest()
DXF_HASH = hashlib.sha256(DXF.read_bytes()).hexdigest()
old_transform = json.loads((ROOT / "maps/ratking/map_transform.json").read_text(encoding="utf-8"))["transform"]


def ai(x, y):
    a, b, c = old_transform["x_ai"]
    d, e, f = old_transform["y_ai"]
    return [round(a * x + b * y + c, 3), round(d * x + e * y + f, 3)]


def read_dxf_entities():
    text = DXF.read_text(errors="replace").splitlines()
    pairs = [(text[i].strip(), text[i + 1].strip()) for i in range(0, len(text) - 1, 2)]
    lines, circles, polylines, entity = [], [], [], None
    for key, value in pairs + [("0", "END")]:
        if key == "0":
            if entity:
                kind, attrs = entity
                one = lambda code: next((v for k, v in attrs if k == code), None)
                if kind == "LINE" and all(one(k) is not None for k in ("10", "20", "11", "21")):
                    p = ai(float(one("10")), float(one("20")))
                    q = ai(float(one("11")), float(one("21")))
                    lines.append([one("8") or "0", *p, *q])
                elif kind == "CIRCLE":
                    x, y, radius = float(one("10")), float(one("20")), float(one("40"))
                    points = [ai(x + radius * math.cos(2 * math.pi * i / 64),
                                 y + radius * math.sin(2 * math.pi * i / 64)) for i in range(64)]
                    circles.append([one("8") or "0", points])
                elif kind == "LWPOLYLINE":
                    xs = [float(v) for k, v in attrs if k == "10"]
                    ys = [float(v) for k, v in attrs if k == "20"]
                    assert len(xs) == len(ys) == int(one("90"))
                    polylines.append([one("8") or "0", [ai(x, y) for x, y in zip(xs, ys)],
                                      bool(int(one("70") or 0) & 1)])
            entity = (value, [])
        elif entity is not None:
            entity[1].append((key, value))
    assert (len(lines), len(circles), len(polylines)) == (129, 2, 1)
    return lines, circles, polylines


def read_convex():
    rows = list(csv.DictReader((MAP / "convex.csv").open(encoding="utf-8-sig")))
    mif = (MAP / "convex_geom.mif").read_text(encoding="latin1")
    sections = re.split(r"(?=^REGION\s+1\s*$)", mif.split("Data", 1)[1], flags=re.M)
    polygons = []
    for section in sections:
        if not section.lstrip().startswith("REGION"):
            continue
        ls = [line.strip() for line in section.splitlines() if line.strip()]
        n = int(ls[1])
        polygons.append([ai(*map(float, line.split())) for line in ls[2:2 + n - 1]])
    assert len(rows) == len(polygons) == 11, (len(rows), len(polygons))
    return [[f"R{i+1:02d}", int(row["Ref"]), float(row["Choice"]),
             float(row["Connectivity"]), polygon]
            for i, (row, polygon) in enumerate(zip(rows, polygons))]


def palette(values):
    low, high = min(values), max(values)
    colors = ["#3333DD", "#3388DD", "#22CCDD", "#22CCBB", "#22DD88",
              "#88DD22", "#BBCC22", "#DDCC22", "#DD8833", "#DD3333"]
    return {"min": low, "max": high, "colors": colors,
            "method": "ten_equal_numeric_intervals_from_exported_range",
            "bounds": [low + (high - low) * i / 10 for i in range(11)]}


vga = list(csv.DictReader((MAP / "vga.csv").open(encoding="utf-8-sig")))
assert len(vga) == 3468
metric_columns = ["Visual Integration [HH]", "Gate Counts", "Metric Mean Shortest-Path Distance"]
points = []
for row in vga:
    points.append([*ai(float(row["x"]), float(row["y"])),
                   *[float(row[key]) for key in metric_columns]])
palettes = {key: palette([float(row[key]) for row in vga]) for key in metric_columns}
walls, circles, polylines = read_dxf_entities()
convex = read_convex()
map_data = {"graph_sha256": GRAPH_HASH, "dxf_sha256": DXF_HASH,
            "source_graph": "source/depthmap/shuwang.graph", "source_dxf": "source/cad/鼠王关.dxf",
            "registration": "DXF and graph share world XY; graph-to-AI affine from prior eight-control registration",
            "transform": old_transform, "walls": walls, "circles": circles,
            "polylines": polylines, "convex": convex,
            "vga": points, "palettes": palettes, "metric_columns": metric_columns}
(MAP / "render_data.json").write_text(json.dumps(map_data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

native = list(csv.DictReader((ROOT / "outputs/native_runs_001_005.tsv").open(encoding="utf-8-sig"), delimiter="\t"))
source_001 = list(csv.DictReader((ROOT / "runs/ratking_run-001/source_current.tsv").open(encoding="utf-8-sig"), delimiter="\t"))
source_001_by_geometry = {}
for source_item in source_001:
    geometry_key = (source_item["type"], source_item["layer"],
                    round(float(source_item["x1"]), 3), round(float(source_item["y1"]), 3))
    source_001_by_geometry.setdefault(geometry_key, []).append(source_item["uuid"])


def nearest_route_order(segments, spawn):
    unused = segments[:]
    current = spawn
    output = []
    while unused:
        candidates = []
        for segment in unused:
            a, b = segment["a"], segment["b"]
            candidates.append((math.dist(current, a), segment["uuid"], segment, a, b))
            candidates.append((math.dist(current, b), segment["uuid"], segment, b, a))
        gap, _, segment, start, end = min(candidates, key=lambda x: (x[0], x[1]))
        output.append({"uuid": segment["uuid"], "a": start, "b": end, "gap": round(gap, 3)})
        unused.remove(segment)
        current = end
    return output


def projection(point, ordered):
    distance = 0.0
    best = (float("inf"), float("inf"))
    for segment in ordered:
        a, b = segment["a"], segment["b"]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length2 = dx * dx + dy * dy
        t = max(0, min(1, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length2)) if length2 else 0
        q = (a[0] + t * dx, a[1] + t * dy)
        best = min(best, (math.dist(point, q), distance + t * math.sqrt(length2)))
        distance += math.sqrt(length2)
    return best


for run_number, source in enumerate(SOURCES, 1):
    rid = f"ratking_run-{run_number:03d}"
    run_dir = ROOT / "runs" / rid
    run_dir.mkdir(parents=True, exist_ok=True)
    items = [row.copy() for row in native if int(row["run"]) == run_number]
    if run_number == 1:
        for item in items:
            geometry_key = (item["type"], item["layer"],
                            round(float(item["x1"]), 3), round(float(item["y1"]), 3))
            matches = source_001_by_geometry.get(geometry_key, [])
            assert matches, ("Source 001 native object not found", geometry_key)
            item["edited_uuid"] = item["uuid"]
            item["uuid"] = matches.pop(0)
    segments = [{"uuid": row["uuid"], "a": [float(row["x1"]), float(row["y1"])],
                 "b": [float(row["x2"]), float(row["y2"])]}
                for row in items if row["type"] == "route"]
    events = [{"uuid": row["uuid"], "layer": row["layer"],
               "xy": [float(row["x1"]), float(row["y1"])]}
              for row in items if row["type"] == "event"]
    spawn = next(row["xy"] for row in events if row["layer"] == "Spawn")
    ordered = nearest_route_order(segments, spawn)
    for event in events:
        event["offset"], event["route_distance"] = projection(event["xy"], ordered)
    events.sort(key=lambda row: (row["layer"] != "Spawn", row["route_distance"], row["uuid"]))
    for i, event in enumerate(events, 1):
        event["event_id"] = f"E{i:03d}"
    source_hash = hashlib.sha256((ROOT / source).read_bytes()).hexdigest()
    data = {"run_id": rid, "source_ai": source, "source_ai_sha256": source_hash,
            "graph_sha256": GRAPH_HASH, "route_order_status": "geometry_candidate_not_video_verified",
            "segments": ordered, "events": events, "end": ordered[-1]["b"]}
    (run_dir / "render_data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    with (run_dir / "route_points.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        w = csv.writer(stream); w.writerow(["run_id", "candidate_order", "source_object_id", "start_x_ai", "start_y_ai", "end_x_ai", "end_y_ai", "gap_ai_pt", "sequence_index", "timestamp_s"])
        for i, seg in enumerate(ordered, 1):
            w.writerow([rid, i, seg["uuid"], *seg["a"], *seg["b"], seg["gap"], "", ""])
    with (run_dir / "events.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        w = csv.writer(stream); w.writerow(["run_id", "event_id", "source_layer", "source_object_id", "x_ai", "y_ai", "route_distance_ai_pt", "route_offset_ai_pt", "timestamp_s", "order_status"])
        for event in events:
            w.writerow([rid, event["event_id"], event["layer"], event["uuid"], *event["xy"], round(event["route_distance"], 3), round(event["offset"], 3), "", "candidate_geometry"])
    print(rid, "segments", len(ordered), "events", len(events), "max gap", round(max(s["gap"] for s in ordered), 2))
print("graph", GRAPH_HASH, "DXF", len(walls), "lines", len(circles), "circles", len(polylines), "polyline", "convex", len(convex), "VGA", len(points))

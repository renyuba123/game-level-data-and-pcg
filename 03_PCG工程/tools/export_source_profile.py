"""Export the current Rat King DXF semantics for the Godot prototype.

Only ENTITIES are exported. BLOCKS contains reusable through/break definitions,
which are not extra doors in the map. No original project file is modified.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COURSE_ROOT = PROJECT_ROOT.parent
SOURCE_ROOT = Path(os.environ.get("RATKING_SOURCE_ROOT", COURSE_ROOT / "02_鼠王关研究"))
OUT = PROJECT_ROOT / "data" / "source_profile.json"
DXF = SOURCE_ROOT / "source" / "cad" / "鼠王关.dxf"
GRAPH = SOURCE_ROOT / "source" / "depthmap" / "shuwang.graph"
ROOMS = SOURCE_ROOT / "maps" / "ratking" / "shuwang" / "rooms.json"
SUMMARY = SOURCE_ROOT / "maps" / "ratking" / "shuwang" / "summary.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dxf_entities(path: Path):
    lines = path.read_text(errors="replace").splitlines()
    pairs = [(lines[i].strip(), lines[i + 1].strip()) for i in range(0, len(lines) - 1, 2)]
    section = ""
    kind = None
    attrs: list[tuple[str, str]] = []
    for code, value in pairs + [("0", "EOF")]:
        if code == "0":
            if kind in {"LINE", "CIRCLE", "LWPOLYLINE"} and section == "ENTITIES":
                data: dict[str, list[str]] = {}
                for key, item in attrs:
                    data.setdefault(key, []).append(item)
                yield kind, data.get("8", ["0"])[0].lower(), data
            kind, attrs = value, []
        else:
            attrs.append((code, value))
            if kind == "SECTION" and code == "2":
                section = value
            elif kind == "ENDSEC":
                section = ""


def xz(x: float, y: float) -> list[float]:
    return [round(x / 1000, 5), round(y / 1000, 5)]


def inverse_ai(point: list[float], transform: dict) -> list[float]:
    a, b, c = transform["x_ai"]
    d, e, f = transform["y_ai"]
    determinant = a * e - b * d
    px, py = point[0] - c, point[1] - f
    return xz((e * px - b * py) / determinant, (-d * px + a * py) / determinant)


def main() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert summary["graph_sha256"] == sha256(GRAPH), "shuwang.graph changed"
    assert summary["dxf_sha256"] == sha256(DXF), "DXF changed"
    transform = summary["graph_to_ai_transform"]
    raw_rooms = json.loads(ROOMS.read_text(encoding="utf-8"))
    rooms = [{"room_id": room["room_id"],
              "polygon_m": [inverse_ai(pt, transform) for pt in room["polygon_ai"]],
              "choice": room["Choice"],
              "convex_connectivity": room["Convex_Connectivity"]}
             for room in raw_rooms]
    walls = []
    links = []
    obstacles = []
    counts = Counter()
    for kind, layer, data in dxf_entities(DXF):
        counts[(layer, kind)] += 1
        if kind == "LINE":
            start = xz(float(data["10"][0]), float(data["20"][0]))
            end = xz(float(data["11"][0]), float(data["21"][0]))
            item = {"start_m": start, "end_m": end,
                    "length_m": round(math.dist(start, end), 5)}
            if layer in {"through", "break"}:
                item.update({"id": f"{layer.upper()}-{1 + sum(x['kind'] == layer for x in links):02d}",
                             "kind": layer})
                links.append(item)
            elif layer == "wall":
                walls.append(item)
        elif kind == "CIRCLE" and layer == "block":
            obstacles.append({"id": f"BLOCK-{len(obstacles) + 1:02d}",
                              "center_m": xz(float(data["10"][0]), float(data["20"][0])),
                              "radius_m": round(float(data["40"][0]) / 1000, 5)})
        elif kind == "LWPOLYLINE" and layer == "wall":
            vertices = [xz(float(x), float(y)) for x, y in zip(data["10"], data["20"]) ]
            closed = bool(int(data.get("70", ["0"])[0]) & 1)
            for i in range(len(vertices) if closed else len(vertices) - 1):
                walls.append({"start_m": vertices[i], "end_m": vertices[(i + 1) % len(vertices)],
                              "length_m": round(math.dist(vertices[i], vertices[(i + 1) % len(vertices)]), 5)})
    assert counts[("through", "LINE")] == 6
    assert counts[("break", "LINE")] == 3
    assert counts[("block", "CIRCLE")] == 2
    profile = {
        "schema_version": 1,
        "source_dxf": DXF.name,
        "source_dxf_sha256": sha256(DXF),
        "source_graph": GRAPH.name,
        "source_graph_sha256": sha256(GRAPH),
        "dxf_insunits": 4,
        "units": "meters converted from DXF millimeters; game-world scale unverified",
        "wall_segments": walls,
        "connections": links,
        "blocks": obstacles,
        "convex_rooms": rooms,
        "source_metrics": {"convex_choice_min": 0, "convex_choice_max": 62,
                           "vga_point_count": summary["vga_points"]},
        "notes": ["Connection segments are DXF symbols, not a verified room-pair edge list.",
                  "BLOCKS definitions were intentionally excluded.",
                  "Generated level topology is a design prototype, not a tracing of the original map."],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}: {len(rooms)} rooms, {len(links)} connections, "
          f"{len(obstacles)} blocks, {len(walls)} wall segments")


if __name__ == "__main__":
    main()


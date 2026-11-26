"""Embed first-run source IDs and calibrated Gate Counts cells in JSX."""
import csv
import hashlib
import json
import math
import struct
from pathlib import Path

root = Path(__file__).resolve().parents[1]
run = root / "runs/ratking_run-001"
maps = root / "maps/ratking"

with (run / "events.csv").open(encoding="utf-8-sig", newline="") as stream:
    events = list(csv.DictReader(stream))
assert len(events) == 24
assert events[0]["source_layer"] == "Spawn" and events[0]["event_id"] == "E001"

occupied = []
markers = [(float(e["x_ai_pdf"]), float(e["y_ai_pdf"])) for e in events]
offsets = [(14, 15), (-43, 15), (14, -19), (-43, -19),
           (14, 35), (-43, 35), (27, 2), (-54, 2)]
event_data = []
for event, (x, y) in zip(events, markers):
    choices = []
    for rank, (dx, dy) in enumerate(offsets):
        lx, ly = x + dx, y + dy
        box = (lx - 3, ly - 5, lx + 44, ly + 20)
        score = rank * 0.5
        if box[0] < 60 or box[2] > 1465 or box[1] < 320 or box[3] > 1060:
            score += 1000
        for old in occupied:
            overlap = max(0, min(box[2], old[2]) - max(box[0], old[0])) * \
                      max(0, min(box[3], old[3]) - max(box[1], old[1]))
            score += overlap * 2
        for mx, my in markers:
            if box[0] - 4 < mx < box[2] + 4 and box[1] - 4 < my < box[3] + 4:
                score += 10 if math.dist((mx, my), (x, y)) < 1 else 35
        choices.append((score, rank, lx, ly, box))
    _, _, lx, ly, box = min(choices)
    occupied.append(box)
    event_data.append([event["event_id"], event["source_layer"],
                       event["source_object_id"].removeprefix("AI-uuid-"),
                       round(x, 3), round(y, 3), round(lx, 3), round(ly, 3)])

with (maps / "vga_points.csv").open(encoding="utf-8-sig", newline="") as stream:
    points = list(csv.DictReader(stream))
assert len(points) == 3462
gate_values = [int(float(p["Gate_Counts"])) for p in points]
summary = json.loads((maps / "vga_summary.json").read_text(encoding="utf-8"))
assert min(gate_values) == 4 and max(gate_values) == 7230
assert summary["metrics"]["Gate Counts"]["count"] == len(points)
gate_image = maps / "gate_counts_depthmap_original.png"
image_bytes = gate_image.read_bytes()
assert image_bytes[:8] == b"\x89PNG\r\n\x1a\n"
image_size = struct.unpack(">II", image_bytes[16:24])
palette = json.loads((maps / "gate_counts_palette.json").read_text(encoding="utf-8"))
assert palette["source_image_sha256"] == hashlib.sha256(image_bytes).hexdigest()
assert len(palette["colors"]) == 10
assert palette["lower_bounds_inclusive"][0] == min(gate_values)
assert palette["upper_bounds_inclusive"][-1] == max(gate_values)
assert all(palette["upper_bounds_inclusive"][i] + 1 == palette["lower_bounds_inclusive"][i+1]
           for i in range(9))
gate_points = [[round(float(p["x_ai"]), 3), round(float(p["y_ai"]), 3),
                int(float(p["Gate_Counts"]))] for p in points]

data = {"events": event_data, "gate_image_size": image_size,
        "gate_image_sha256": hashlib.sha256(image_bytes).hexdigest(),
        "gate_point_count": len(points), "gate_min": 4, "gate_max": 7230,
        "gate_points": gate_points, "gate_palette": palette}
template = (root / "tools/ratking_figure_template.jsx").read_text(encoding="utf-8")
jsx = template.replace("/*DATA_LITERAL*/null",
                       json.dumps(data, ensure_ascii=True, separators=(",", ":")))
assert jsx != template
(root / "tools/render_ratking.jsx").write_text(jsx, encoding="utf-8")
print("JSX bytes", len(jsx.encode("utf-8")), "events", len(events),
      "gate points", len(points), "calibration image", image_size)

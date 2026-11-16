#!/usr/bin/env python3
"""Basic, read-only validation for a single gameplay run directory.

Usage: python validate_run.py /path/to/runs/<run_id>
No nonstandard packages required; does not edit input files.
"""
import csv
import hashlib
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REQUIRED_POINTS = {
    "run_id", "attempt_id", "point_id", "sequence_index", "timestamp_s",
    "x_map", "y_map", "room_id", "source_object_id", "order_status",
    "confidence", "notes", "candidate_order", "sequence_evidence", "x_ai", "y_ai"
}
REQUIRED_EVENTS = {
    "run_id", "attempt_id", "event_id", "event_type", "source_layer",
    "source_object_id", "timestamp_s", "x_map", "y_map", "room_id",
    "route_point_id", "verification_status", "notes", "original_event_id",
    "route_distance_ai_pt", "route_offset_ai_pt", "candidate_route_segment",
    "event_order_status"
}
REQUIRED_MANIFEST = {"map_id", "run_id", "coordinate_system", "route_order_verified"}


def read_table(path, required, errors):
    if not path.exists():
        errors.append(f"Missing {path.name}")
        return []
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            missing = required - set(reader.fieldnames or [])
            if missing:
                errors.append(f"{path.name} lacks columns: {', '.join(sorted(missing))}")
            return list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        errors.append(f"Could not read {path.name}: {exc}")
        return []


def numeric_or_blank(value, label, rownum, errors):
    if value in (None, ""):
        return
    try:
        float(value)
    except ValueError:
        errors.append(f"Row {rownum}: {label} must be a number or blank")


def main(folder):
    errors, warnings = [], []
    path = Path(folder)
    if not path.is_dir():
        print(f"ERROR: directory not found: {path}")
        return 2
    manifest_path = path / "run_manifest.json"
    manifest = {}
    try:
        with manifest_path.open(encoding="utf-8") as f:
            manifest = json.load(f)
        if not isinstance(manifest, dict):
            errors.append("run_manifest.json must be an object")
            manifest = {}
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"Cannot read run_manifest.json: {exc}")
    missing = REQUIRED_MANIFEST - set(manifest)
    if missing:
        errors.append("Manifest missing fields: " + ", ".join(sorted(missing)))
    run_id = manifest.get("run_id", "")
    if not run_id:
        errors.append("Manifest run_id cannot be empty")
    if manifest.get("route_order_verified") not in (True, False):
        errors.append("route_order_verified must be true or false")
    workspace = path.parent.parent
    for field, relative in (("source_sha256", (manifest.get("source_files") or [None])[0]),
                            ("edited_ai_sha256", manifest.get("edited_ai"))):
        expected = manifest.get(field)
        if expected and relative:
            target = workspace / relative
            if not target.is_file():
                errors.append(f"{field}: file not found: {relative}")
            elif hashlib.sha256(target.read_bytes()).hexdigest().lower() != expected.lower():
                errors.append(f"{field}: hash mismatch: {relative}")
    if manifest.get("edited_ai") and len(list(workspace.rglob("*.ai"))) != 2:
        errors.append("This Rat King workspace must contain exactly the original and edited AI files")
    map_dir = workspace / "maps" / str(manifest.get("map_id", ""))
    for field, relative in (("depthmap_graph_sha256", workspace / "shuwangguan.graph"),
                            ("convex_export_sha256", map_dir / "convex_export.mif"),
                            ("vga_export_sha256", map_dir / "vga_export.txt"),
                            ("map_transform_sha256", map_dir / "map_transform.json")):
        expected = manifest.get(field)
        if expected:
            if not relative.is_file():
                errors.append(f"{field}: file not found: {relative}")
            elif hashlib.sha256(relative.read_bytes()).hexdigest().lower() != expected.lower():
                errors.append(f"{field}: hash mismatch")
    for filename, expected in manifest.get("figure_sha256", {}).items():
        target = workspace / "outputs" / run_id / filename
        if not target.is_file():
            errors.append(f"figure missing: {filename}")
        elif hashlib.sha256(target.read_bytes()).hexdigest().lower() != expected.lower():
            errors.append(f"figure hash mismatch: {filename}")
    transform = None
    transform_path = map_dir / "map_transform.json"
    if transform_path.is_file():
        try:
            registration = json.loads(transform_path.read_text(encoding="utf-8"))
            transform = registration["transform"]
            assert registration["status"] == "registered"
            assert len(registration["controls"]) >= 3
            assert registration["max_residual_pdf_pt"] < registration["acceptance_tolerance_pdf_pt"]
        except (KeyError, ValueError, AssertionError, OSError) as exc:
            errors.append(f"Invalid registered map transform: {exc}")
            transform = None
    native_ids = set()
    native_file = path / "native_items.tsv"
    if native_file.is_file():
        with native_file.open(encoding="utf-8-sig", newline="") as f:
            native_ids = {"AI-uuid-" + r["uuid"] for r in csv.DictReader(f, delimiter="\t")}
    rooms_path = workspace / "maps" / str(manifest.get("map_id", "")) / "rooms.json"
    room_ids = set()
    if rooms_path.is_file():
        try:
            room_ids = {r["room_id"] for r in json.loads(rooms_path.read_text(encoding="utf-8"))["rooms"]}
        except (KeyError, TypeError, ValueError, OSError) as exc:
            errors.append(f"Cannot read room IDs: {exc}")

    points = read_table(path / "route_points.csv", REQUIRED_POINTS, errors)
    events = read_table(path / "events.csv", REQUIRED_EVENTS, errors)
    point_ids, event_ids = set(), set()
    sequence_by_attempt = {}
    candidate_by_attempt = {}
    candidate_points = []
    for i, row in enumerate(points, 2):
        p = row.get("point_id", "")
        if not p:
            errors.append(f"route_points.csv row {i}: point_id empty")
        if p in point_ids:
            errors.append(f"route_points.csv row {i}: duplicate point_id {p}")
        point_ids.add(p)
        if row.get("run_id") != run_id:
            errors.append(f"route_points.csv row {i}: run_id mismatch")
        status = row.get("order_status", "")
        if status not in ("verified", "unverified"):
            errors.append(f"route_points.csv row {i}: order_status invalid")
        if row.get("confidence") not in ("high", "medium", "low"):
            errors.append(f"route_points.csv row {i}: confidence invalid")
        for col in ("timestamp_s", "x_map", "y_map", "x_ai", "y_ai"):
            numeric_or_blank(row.get(col), col, i, errors)
        if row.get("room_id") and row["room_id"] not in room_ids:
            errors.append(f"route_points.csv row {i}: unknown room_id {row['room_id']}")
        if row.get("source_object_id", "").startswith("AI-uuid-") and native_ids and row["source_object_id"] not in native_ids:
            errors.append(f"route_points.csv row {i}: native object ID is absent")
        if transform and all(row.get(k) for k in ("x_map", "y_map", "x_ai", "y_ai")):
            gx, gy = float(row["x_map"]), float(row["y_map"])
            a, b, c = transform["x_ai"]
            d, e, f = transform["y_ai"]
            if math.dist((a*gx+b*gy+c, d*gx+e*gy+f), (float(row["x_ai"]),float(row["y_ai"]))) > .05:
                errors.append(f"route_points.csv row {i}: graph to AI coordinate mismatch")
        seq = row.get("sequence_index", "")
        if status == "unverified" and seq:
            errors.append(f"route_points.csv row {i}: formal sequence needs verified order")
        candidate = row.get("candidate_order", "")
        if candidate:
            if not candidate.isdigit() or int(candidate) < 1:
                errors.append(f"route_points.csv row {i}: candidate_order must be positive integer")
            else:
                ckey = (row.get("attempt_id", ""), int(candidate))
                if ckey in candidate_by_attempt:
                    errors.append(f"route_points.csv row {i}: duplicate candidate_order {candidate}")
                candidate_by_attempt[ckey] = p
                candidate_points.append(row)
        if seq:
            if not seq.isdigit() or int(seq) < 1:
                errors.append(f"route_points.csv row {i}: sequence_index must be positive integer")
            else:
                attempt = row.get("attempt_id", "")
                key = (attempt, int(seq))
                if key in sequence_by_attempt:
                    errors.append(f"route_points.csv row {i}: duplicate sequence_index {seq} within attempt {attempt}")
                sequence_by_attempt[key] = p
        if bool(row.get("x_map")) != bool(row.get("y_map")):
            errors.append(f"route_points.csv row {i}: x_map and y_map must both be set or blank")
        if bool(row.get("x_ai")) != bool(row.get("y_ai")):
            errors.append(f"route_points.csv row {i}: x_ai and y_ai must both be set or blank")
    if manifest.get("route_order_verified") and any(row.get("order_status") != "verified" for row in points):
        errors.append("Manifest says route_order_verified but some point order_status is not verified")
    candidate_points.sort(key=lambda row: int(row["candidate_order"]))
    for a, b in zip(candidate_points[1::2], candidate_points[2::2]):
        if a.get("attempt_id") != b.get("attempt_id") or not all(a.get(k) and b.get(k) for k in ("x_ai", "y_ai")):
            continue
        gap = math.dist((float(a["x_ai"]), float(a["y_ai"])),
                        (float(b["x_ai"]), float(b["y_ai"])))
        if gap > 3:
            warnings.append(f"Candidate route gap {a['point_id']} -> {b['point_id']}: {gap:.2f} AI points")

    for i, row in enumerate(events, 2):
        e = row.get("event_id", "")
        if not e:
            errors.append(f"events.csv row {i}: event_id empty")
        if e in event_ids:
            errors.append(f"events.csv row {i}: duplicate event_id {e}")
        event_ids.add(e)
        if row.get("run_id") != run_id:
            errors.append(f"events.csv row {i}: run_id mismatch")
        if row.get("room_id") and row["room_id"] not in room_ids:
            errors.append(f"events.csv row {i}: unknown room_id {row['room_id']}")
        if row.get("source_object_id", "").startswith("AI-uuid-") and native_ids and row["source_object_id"] not in native_ids:
            errors.append(f"events.csv row {i}: native object ID is absent")
        if transform and all(row.get(k) for k in ("x_map", "y_map", "x_ai_pdf", "y_ai_pdf")):
            gx, gy = float(row["x_map"]), float(row["y_map"])
            a, b, c = transform["x_ai"]
            d, e, f = transform["y_ai"]
            if math.dist((a*gx+b*gy+c, d*gx+e*gy+f), (float(row["x_ai_pdf"]),float(row["y_ai_pdf"]))) > .05:
                errors.append(f"events.csv row {i}: graph to AI coordinate mismatch")
        if not row.get("event_type"):
            errors.append(f"events.csv row {i}: event_type empty; use 'unknown' if uncertain")
        for col in ("timestamp_s", "x_map", "y_map"):
            numeric_or_blank(row.get(col), col, i, errors)
        ref = row.get("route_point_id", "")
        if ref and ref not in point_ids:
            errors.append(f"events.csv row {i}: route_point_id {ref} is absent from route_points.csv")
        if bool(row.get("x_map")) != bool(row.get("y_map")):
            errors.append(f"events.csv row {i}: x_map and y_map must both be set or blank")
    if not points:
        warnings.append("route_points.csv has zero data rows; cannot compute route behaviour")
    if not events:
        warnings.append("events.csv has zero data rows; no event distribution can be computed")
    elif any(not row.get("room_id") for row in events):
        warnings.append("Some event markers fall outside the registered convex polygons")

    if run_id == "ratking_run-001" and events:
        expected_ids = [f"E{i:03d}" for i in range(1, len(events) + 1)]
        if [row["event_id"] for row in events] != expected_ids:
            errors.append("Event IDs must be consecutive in candidate route order")
        if len(events) != 24 or events[0]["source_layer"] != "Spawn":
            errors.append("Expected 24 native marks with Spawn as E001")
        if len({row["source_object_id"] for row in events}) != len(events):
            errors.append("Event source Illustrator UUIDs must be unique")
        if any(row.get("event_order_status") != "spatial_candidate_unverified_time"
               or row.get("timestamp_s") for row in events):
            errors.append("Candidate event IDs must not imply verified event times")
        distances = [float(row["route_distance_ai_pt"]) for row in events]
        if distances[1:] != sorted(distances[1:]):
            errors.append("Event IDs are not ordered by candidate route distance")
        if manifest.get("spawn_event_id") != "E001" or manifest.get("end_event_id") is not None:
            errors.append("Spawn must be E001 and End must have no event ID")
        audit_path = workspace / "outputs" / run_id / "icon_audit.tsv"
        if audit_path.is_file():
            with audit_path.open(encoding="utf-8-sig", newline="") as stream:
                audit = list(csv.DictReader(stream, delimiter="\t"))
            audit_by_id = {row["event_id"]: row for row in audit}
            if len(audit_by_id) != len(events):
                errors.append("Edited AI icon audit does not cover all events")
            if len({row["edited_ai_uuid"] for row in audit}) != len(events):
                errors.append("Edited AI icon UUIDs must be unique")
            for row in events:
                match = audit_by_id.get(row["event_id"])
                if not match or match["source_original_ai_uuid"] != row["source_object_id"].removeprefix("AI-uuid-"):
                    errors.append(f"Icon audit source mismatch: {row['event_id']}")
                elif float(match["centroid_offset_ai_pt"]) > 40:
                    errors.append(f"Icon audit geometry mismatch: {row['event_id']}")
            expected_hash = manifest.get("icon_audit_sha256")
            if expected_hash and hashlib.sha256(audit_path.read_bytes()).hexdigest() != expected_hash:
                errors.append("Icon audit hash mismatch")
        else:
            errors.append("Missing edited AI icon audit")
        vga_path = map_dir / "vga_points.csv"
        summary_path = map_dir / "vga_summary.json"
        if vga_path.is_file() and summary_path.is_file():
            with vga_path.open(encoding="utf-8-sig", newline="") as stream:
                vga = list(csv.DictReader(stream))
            gate = [float(row["Gate_Counts"]) for row in vga]
            summary = json.loads(summary_path.read_text(encoding="utf-8"))["metrics"]["Gate Counts"]
            if len(vga) != 3462 or min(gate) != 4 or max(gate) != 7230:
                errors.append("Gate Counts point count or range differs from source export")
            if summary.get("count") != len(vga):
                errors.append("Gate Counts summary point count mismatch")
        else:
            errors.append("Missing Gate Counts point table or summary")
        image_path = map_dir / "gate_counts_depthmap_original.png"
        if not image_path.is_file():
            errors.append("Missing original Depthmap Gate Counts image")
        else:
            raw_image = image_path.read_bytes()
            if not raw_image.startswith(b"\x89PNG\r\n\x1a\n"):
                errors.append("Original Gate Counts image is not PNG")
            if hashlib.sha256(raw_image).hexdigest() != manifest.get("gate_counts_original_image_sha256"):
                errors.append("Original Gate Counts image hash mismatch")
        palette_path = map_dir / "gate_counts_palette.json"
        if not palette_path.is_file():
            errors.append("Missing Gate Counts image-calibrated palette")
        else:
            palette = json.loads(palette_path.read_text(encoding="utf-8"))
            if palette.get("source_image_sha256") != manifest.get("gate_counts_original_image_sha256"):
                errors.append("Gate Counts calibration image hash mismatch")
            if palette.get("lower_bounds_inclusive") != manifest.get("gate_counts_palette_thresholds"):
                errors.append("Gate Counts calibrated thresholds mismatch")
            if hashlib.sha256(palette_path.read_bytes()).hexdigest() != manifest.get("gate_counts_palette_sha256"):
                errors.append("Gate Counts palette file hash mismatch")
            if len(palette.get("colors", [])) != 10:
                errors.append("Gate Counts palette must contain ten bands")
            lows = palette.get("lower_bounds_inclusive", [])
            highs = palette.get("upper_bounds_inclusive", [])
            if len(lows) != 10 or len(highs) != 10 or lows[0] != 4 or highs[-1] != 7230 or any(highs[i] + 1 != lows[i + 1] for i in range(9)):
                errors.append("Gate Counts palette bands do not cover the raw value range continuously")
        if manifest.get("gate_counts_render_method") != "derived_image_matched_value_bands":
            errors.append("Gate Counts figure must use documented image-matched value bands")
        gate_svg = workspace / "outputs" / run_id / "gate_counts_from_edited_ai.svg"
        if gate_svg.is_file():
            svg = gate_svg.read_bytes()
            if b"<image" in svg or b"data:image" in svg or b"Downloads" in svg:
                errors.append("Gate Counts SVG must contain vector cells without an embedded screenshot")
            svg_root = ET.fromstring(svg)
            gate_layer = next((item for item in svg_root.iter() if item.get("id") == "F-Gate-Counts"), None)
            cell_count = sum(item.tag.endswith("}rect") or item.tag == "rect" for item in gate_layer.iter()) if gate_layer is not None else 0
            if cell_count != 3462:
                errors.append(f"Gate Counts SVG has {cell_count} vector cells, expected 3462")

    print(f"Run: {run_id or '(unknown)'} | points: {len(points)} | events: {len(events)}")
    for warn in warnings:
        print("WARNING:", warn)
    for error in errors:
        print("ERROR:", error)
    print("Result:", "PASS" if not errors else "FAIL")
    return 1 if errors else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_run.py /path/to/runs/<run_id>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))

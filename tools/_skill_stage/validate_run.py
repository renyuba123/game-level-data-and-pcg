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
from pathlib import Path

REQUIRED_POINTS = {
    "run_id", "attempt_id", "point_id", "sequence_index", "timestamp_s",
    "x_map", "y_map", "room_id", "source_object_id", "order_status",
    "confidence", "notes", "candidate_order", "sequence_evidence", "x_ai", "y_ai"
}
REQUIRED_EVENTS = {
    "run_id", "attempt_id", "event_id", "event_type", "source_layer",
    "source_object_id", "timestamp_s", "x_map", "y_map", "room_id",
    "route_point_id", "verification_status", "notes"
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
        if a.get("attempt_id") != b.get("attempt_id") or not all(a.get(k) and b.get(k) for k in ("x_map", "y_map")):
            continue
        gap = math.dist((float(a["x_map"]), float(a["y_map"])),
                        (float(b["x_map"]), float(b["y_map"])))
        if gap > 3:
            warnings.append(f"Candidate route gap {a['point_id']} -> {b['point_id']}: {gap:.2f} map units")

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

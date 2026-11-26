"""Assign candidate event IDs by distance along the drawn first-run route.

The IDs describe spatial order on the current drawing, not verified event time.
Native Illustrator UUIDs remain the stable reference for each marker.
"""
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/ratking_run-001"


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_rows(path, data):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def projection(x, y, segments, starts):
    matches = []
    for index, ((ax, ay), (bx, by)) in enumerate(segments):
        dx, dy = bx - ax, by - ay
        length2 = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / length2))
        px, py = ax + t * dx, ay + t * dy
        distance = math.hypot(x - px, y - py)
        arc = starts[index] + math.sqrt(length2) * t
        matches.append((distance, arc, index + 1))
    # Nearest piece of route; when it revisits a point, use the first visit.
    return min(matches)


def main():
    points = rows(RUN / "route_points.csv")
    assert len(points) == 88
    segments = [((float(a["x_ai"]), float(a["y_ai"])),
                 (float(b["x_ai"]), float(b["y_ai"])))
                for a, b in zip(points[::2], points[1::2])]
    starts, distance = [], 0.0
    for a, b in segments:
        starts.append(distance)
        distance += math.dist(a, b)

    events = rows(RUN / "events.csv")
    assert len(events) == 24
    assert len({event["source_object_id"] for event in events}) == 24
    spawn = [event for event in events if event["source_layer"] == "Spawn"]
    assert len(spawn) == 1
    for event in events:
        near, arc, piece = projection(float(event["x_ai_pdf"]),
                                      float(event["y_ai_pdf"]), segments, starts)
        event["route_distance_ai_pt"] = f"{arc:.3f}"
        event["route_offset_ai_pt"] = f"{near:.3f}"
        event["candidate_route_segment"] = str(piece)
        event["event_order_status"] = "spatial_candidate_unverified_time"
        if not event.get("original_event_id"):
            event["original_event_id"] = event["event_id"]
    events.sort(key=lambda event: (
        0 if event["source_layer"] == "Spawn" else 1,
        float(event["route_distance_ai_pt"]),
        float(event["route_offset_ai_pt"]),
        event["source_object_id"],
    ))
    old_to_new = {}
    for number, event in enumerate(events, 1):
        new_id = f"E{number:03d}"
        old_to_new[event["original_event_id"]] = new_id
        event["event_id"] = new_id
    assert events[0]["source_layer"] == "Spawn"
    write_rows(RUN / "events.csv", events)

    qa_path = RUN / "review_needed.csv"
    qa = rows(qa_path)
    for item in qa:
        if item["review_id"] == "Q010":
            ids = [event["event_id"] for event in events
                   if event["source_layer"] == "Transform"]
            item["question"] = ("Which Transform mark (" + " or ".join(ids) +
                                ") relates to the user-described endpoint? "
                                "End itself is a separate route label.")
        elif item["review_id"] == "Q012":
            marker = next(event for event in events
                          if event["source_object_id"] == "AI-uuid-736")
            item["location"] = (f"{marker['event_id']} / AI-uuid-736 "
                                "AI (1129.352,779.968)")
    write_rows(qa_path, qa)

    manifest_path = RUN / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["spawn_event_id"] = "E001"
    manifest["event_order_status"] = "spatial_candidate_along_drawn_route"
    manifest["event_order_is_timestamp"] = False
    manifest["end_event_id"] = None
    manifest["end_is_separate_route_label"] = True
    manifest["event_count"] = len(events)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    print("event IDs:", [(event["event_id"], event["source_layer"],
                          event["source_object_id"]) for event in events])
    print("old to new:", old_to_new)


if __name__ == "__main__":
    main()

"""Package saved authoritative Layouts for the existing Godot decoder."""
import argparse
import hashlib

from full_pcg.common import ROOT, read, write
from full_pcg.godot_export import package


def export(audit_dir, output_dir, limit=12):
    config = read(ROOT / "configs/full_pcg_v2.json")
    rows = [read(path) for path in sorted(audit_dir.glob("seed_*.json"))]
    pending = [row for row in rows if row["validation"]["ok"]]
    counts, paths, failures = set(), [], []
    while pending and len(paths) < limit:
        index = next((i for i, row in enumerate(pending)
                      if len(row["data"]["source_genome"]["rooms"]) not in counts), 0)
        row = pending.pop(index)
        layout = row["data"]["layout"]
        target = output_dir / f"seed_{layout['seed']:04d}.json"
        try:
            packed = package(layout, config)
        except ValueError as exc:
            failures.append({"seed": layout["seed"], "reason": str(exc)})
            continue
        write(target, packed)
        counts.add(len(layout["rooms"]))
        paths.append({"seed": layout["seed"], "rooms": len(layout["rooms"]),
                      "layout_hash": layout["layout_hash"], "path": str(target)})
    manifest = {"count": len(paths), "attempted": len(paths) + len(failures),
                "package_failures": failures, "room_counts": sorted(counts), "packages": paths,
                "source_summary_sha256": hashlib.sha256((audit_dir / "summary.json").read_bytes()).hexdigest(),
                "notice": "Python Layout is authoritative; Godot must not regenerate geometry."}
    write(output_dir / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", default="full_pcg_output/combat_phase2_audit_v1")
    parser.add_argument("--output", default="full_pcg_output/combat_godot")
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()
    result = export(ROOT / args.audit, ROOT / args.output, args.limit)
    print({"count": result["count"], "seeds": [p["seed"] for p in result["packages"]],
           "package_failures": result["package_failures"]})


if __name__ == "__main__":
    main()

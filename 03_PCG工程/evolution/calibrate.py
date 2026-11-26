from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
from common import CLI, METRICS, ROOT, SOURCE_DXF, SOURCE_GRAPH, SOURCE_MAPS, WORK, command, digest, read_json, write_json
from metrics import analyze, baseline_dxf, make_profile, table

def run(grid=400):
    folder = WORK / "baseline"
    folder.mkdir(parents=True, exist_ok=True)
    original = table(SOURCE_MAPS / "vga.csv")
    original_by_ref = {row["Ref"]: row for row in original}
    report = {"source_graph_sha256": digest(SOURCE_GRAPH),
        "source_vga_csv_sha256": digest(SOURCE_MAPS / "vga.csv"),
        "source_dxf_sha256": digest(SOURCE_DXF), "cli_sha256": digest(CLI),
        "reference_point_count": len(original), "unit": "DXF drawing units (millimetres); physical scale unverified",
        "excluded_metrics": {"Gate Counts": "original generating procedure and parameters unverified",
                            "Convex Choice": "convex graph recomputation parity not established"},
        "recomputation": {}, "states": {}}
    for suffix, fields, args in [
        ("visibility", METRICS[:2], ["-vm", "visibility", "-vg", "-vr", "n"]),
        ("metric", METRICS[2:], ["-vm", "metric", "-vr", "n"]),
    ]:
        graph = folder / f"recomputed_{suffix}.graph"
        output = folder / f"recomputed_{suffix}.csv"
        if not graph.exists():
            command([CLI, "-f", SOURCE_GRAPH, "-o", graph, "-m", "VGA", *args],
                    folder / f"recompute_{suffix}.log", 900)
        command([CLI, "-f", graph, "-o", output, "-m", "EXPORT", "-em", "pointmap-data-csv"],
                folder / f"export_{suffix}.log")
        rows = table(output)
        if {r["Ref"] for r in rows} != set(original_by_ref):
            raise RuntimeError("recomputation changed point references")
        for name in fields:
            difference = np.array([abs(float(r[name]) - float(original_by_ref[r["Ref"]][name])) for r in rows])
            span = max(float(r[name]) for r in original) - min(float(r[name]) for r in original)
            report["recomputation"][name] = {"max_abs_error": float(difference.max()),
                "mean_abs_error": float(difference.mean()), "max_error_over_original_range": float(difference.max()/max(span, 1e-9))}
    profile = read_json(ROOT / "data/source_profile.json")
    if profile["source_graph_sha256"] != report["source_graph_sha256"] or profile["source_dxf_sha256"] != report["source_dxf_sha256"]:
        raise RuntimeError("source profile is stale")
    for state in ["initial", "all_open"]:
        directory = folder / f"grid_{grid}" / state
        directory.mkdir(parents=True, exist_ok=True)
        dxf = directory / "baseline.dxf"
        fills = baseline_dxf(profile, state, dxf)
        rows, provenance = analyze(dxf, fills, directory, grid)
        target = make_profile(rows, profile["convex_rooms"])
        write_json(directory / "profile.json", target)
        report["states"][state] = provenance
        if grid == 200:
            old = {(float(r["x"]),float(r["y"])):r for r in original}
            new = {(float(r["x"]),float(r["y"])):r for r in rows}
            shared = set(old)&set(new)
            report.setdefault("geometry_reanalysis",{})[state] = {
                "point_count":len(rows), "shared_coordinates":len(shared),
                "new_coordinates":len(set(new)-set(old)), "missing_coordinates":len(set(old)-set(new)),
                "metric_max_abs_difference_on_shared_cells":{m:max(abs(float(new[p][m])-float(old[p][m])) for p in shared) for m in METRICS},
                "note":"State-specific DXF reanalysis; original graph opening state is not independently documented."}
    write_json(folder / f"calibration_{grid}.json", report)
    print(f"baseline calibrated at grid {grid}")
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", type=int, default=400)
    run(parser.parse_args().grid)

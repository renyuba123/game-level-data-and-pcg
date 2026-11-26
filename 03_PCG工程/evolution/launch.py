"""Editor entry point. Work runs outside Godot; all output stays in the project."""
import os
import subprocess
import sys
from common import WORK, ROOT, GODOT, read_json, write_json

mode = sys.argv[1] if len(sys.argv)>1 else "pilot"
if mode not in ("pilot", "search"): raise ValueError(mode)
write_json(WORK/"process.json", {"pid": os.getpid(), "mode": mode})
python = WORK/".venv/Scripts/python.exe"
with (WORK/f"{mode}_console.log").open("w", encoding="utf-8") as output:
    result = subprocess.run([str(python), str(WORK/f"{mode}.py")], stdout=output, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode == 0 and mode == "search" and not (WORK/"runs/search_v1/STOP").exists():
        steps = [("report", [python, WORK/"report.py", "search_v1"]),
                 ("fine_baseline", [python, WORK/"calibrate.py", "--grid", "200"]),
                 ("fine_candidates", [python, WORK/"refine.py", "search_v1"]),
                 ("actual_gate_tests", [GODOT, "--headless", "--path", ROOT, "--script", "res://scripts/evolution_acceptance.gd"])]
        for phase, command in steps:
            write_json(WORK/"status.json", {"state": "finalizing", "phase": phase, "run": "search_v1"})
            result = subprocess.run([str(a) for a in command], stdout=output, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode: break
        if result.returncode == 0:
            review = {}
            for label in ("balanced", "exploration", "pressure"):
                path = ROOT/f"data/evolution/{label}.json"
                candidate = read_json(path)
                evaluation = candidate["evaluation"]
                fine = evaluation["fine_review"]
                heldout = evaluation["heldout"]
                ok = fine["valid"] and fine["constraint"] <= 0 and heldout["early_catch_fraction"] == 0 and heldout["escape_fraction"] > 0
                review[label] = ok
                evaluation["status"] = "200-unit and actual gate tests complete; " + ("heldout proxy passed" if ok else "review failed; provisional candidate")
                write_json(path, candidate)
            write_json(WORK/"status.json", {"state": "complete" if all(review.values()) else "complete_with_review_failures", "run":"search_v1", "review":review})
    elif result.returncode == 0 and mode == "pilot":
        write_json(WORK/"status.json", {"state":"pilot_complete","summary":read_json(WORK/"pilot/summary.json")})
    if result.returncode:
        write_json(WORK/"status.json", {"state": "failed", "mode": mode, "log": str(WORK/f"{mode}_console.log"), "exit_code": result.returncode})

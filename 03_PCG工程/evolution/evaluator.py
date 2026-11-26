from __future__ import annotations
import time
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from pathlib import Path
import numpy as np
from common import ROOT, SOURCE_DXF, SOURCE_GRAPH, WORK, CLI, digest, read_json, write_json, decode
from metrics import write_candidate_dxf, analyze, make_profile, distance
from simulation import clearance_check, run
from genome import native

class Evaluator:
    def __init__(self, grid=400):
        self.grid = grid
        self.reference = {state: read_json(WORK/f"baseline/grid_{grid}/{state}/profile.json") for state in ("initial", "all_open")}
        calibration = read_json(WORK/f"baseline/calibration_{grid}.json")
        if digest(SOURCE_GRAPH) != calibration["source_graph_sha256"] or digest(SOURCE_DXF) != calibration["source_dxf_sha256"]:
            raise RuntimeError("Source files changed; rerun calibration before optimization")
        self.recipe = {"grid": grid, "baseline": digest({"profiles": self.reference,
            "graph": calibration["source_graph_sha256"], "dxf": calibration["source_dxf_sha256"]}), "cli": digest(CLI),
            "model": digest(ROOT/"scripts/pcg_model.gd"),
            "source_profile": digest(ROOT/"data/source_profile.json"),
            "implementation": {name: digest(WORK/name) for name in ("metrics.py", "simulation.py", "evaluator.py", "common.py", "genome.py")}}
        self.source_hashes = {str(SOURCE_GRAPH): calibration["source_graph_sha256"],
                             str(SOURCE_DXF): calibration["source_dxf_sha256"]}

    def batch(self, genomes, directory, generation=0):
        self.assert_unchanged()
        requests = [{"seed": 42, "genes": native(g)} for g in genomes]
        layouts = decode(requests, directory)
        records = [None]*len(requests)
        workers = min(4, max(1, int(os.environ.get("RATKING_WORKERS", "4"))))
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self.one, request, layout): i for i,(request,layout) in enumerate(zip(requests,layouts))}
            for completed, future in enumerate(as_completed(futures), 1):
                i = futures[future]
                record = {**future.result(), "generation": generation}
                records[i] = record
                write_json(Path(directory)/"progress.json", {"completed": completed, "total": len(requests), "workers": workers, "last": record})
                print(f"candidate {completed}/{len(requests)} valid={record['valid']} seconds={record.get('seconds',0):.1f}", flush=True)
        write_json(Path(directory)/"evaluations.json", records)
        self.assert_unchanged()
        return records

    def assert_unchanged(self):
        files = {**self.source_hashes, str(ROOT/"scripts/pcg_model.gd"):self.recipe["model"],
                 str(ROOT/"data/source_profile.json"):self.recipe["source_profile"], str(CLI):self.recipe["cli"],
                 **{str(WORK/name):sha for name,sha in self.recipe["implementation"].items()}}
        for path, sha in files.items():
            if digest(Path(path)) != sha: raise RuntimeError(f"Source or implementation changed during search: {path}")

    def one(self, request, layout):
        key = digest({"request": request, "recipe": self.recipe})
        folder = WORK / "cache" / key
        cache = folder/"evaluation.json"
        with file_lock(folder/"evaluation.lock"):
            if cache.exists():
                record = read_json(cache)
            else:
                record = {**request, "key": key, "grid": self.grid, "recipe": self.recipe,
                          "valid": False, "objectives": [1e6]*4, "constraint": 1., "states": {}}
                start = time.perf_counter()
                try:
                    if not layout["validation"]["ok"]: raise ValueError(str(layout["validation"]["issues"]))
                    record["clearance"] = clearance_check(layout)
                    write_json(folder/"layout.json", layout)
                    errors = []
                    for state in ("initial", "all_open"):
                        geometry_key = digest({"state": state, "walls": layout["walls_initial" if state=="initial" else "walls_all_open"],
                            "blocks": layout["blocks"], "rooms": layout["rooms"], "grid": self.grid,
                            "cli": self.recipe["cli"], "exporter": self.recipe["implementation"]["metrics.py"]})
                        state_dir = WORK/"analysis_cache"/geometry_key
                        state_dir.mkdir(parents=True, exist_ok=True)
                        with file_lock(state_dir/"geometry.lock"):
                            dxf = state_dir/"layout.dxf"
                            if not (state_dir/"fills.json").exists():
                                fills = write_candidate_dxf(layout, state, dxf)
                                write_json(state_dir/"fills.json", fills)
                            else: fills = read_json(state_dir/"fills.json")
                            rows, provenance = analyze(dxf, fills, state_dir, self.grid)
                            profile = make_profile(rows, layout["rooms"])
                            error, fields = distance(profile, self.reference[state])
                            errors.append(error)
                            write_json(state_dir/"profile.json", profile)
                            record["states"][state] = {"distance": error, "metrics": fields, "analysis": provenance, "directory": str(state_dir)}
                    simulation = run(layout)
                    guardrail = simulation["early_catch_fraction"] + simulation["stuck_fraction"] + max(0., 1/6-simulation["escape_fraction"])
                    record.update(valid=True, constraint=guardrail, simulation=simulation,
                        objectives=[float(np.mean(errors)), simulation["fairness_loss"],
                                    simulation["pressure_loss"], -simulation["route_diversity"]])
                except (ValueError, RuntimeError) as exc:
                    record["error"] = str(exc)
                record["seconds"] = time.perf_counter()-start
                write_json(cache, record)
        return record

@contextmanager
def file_lock(path):
    """Local Windows process lock; automatically released after a crashed worker."""
    import msvcrt
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if stream.tell()==0:
            stream.write(b"0"); stream.flush()
        deadline=time.monotonic()+1800
        while True:
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
                break
            except OSError:
                if time.monotonic()>deadline: raise TimeoutError(f"Cache lock timeout: {path}")
                time.sleep(.1)
        try: yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)

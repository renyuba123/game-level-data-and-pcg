import argparse
import time
import numpy as np
from pymoo.core.mixed import MixedVariableSampling
from pymoo.core.problem import Problem
from common import WORK, write_json
from evaluator import Evaluator
from genome import variables

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=16)
    args = parser.parse_args()
    problem = Problem(vars=variables())
    pop = MixedVariableSampling().do(problem, args.count, random_state=np.random.default_rng(20261118))
    start = time.perf_counter()
    records = Evaluator().batch(pop.get("X"), WORK/"pilot/evaluated")
    elapsed = time.perf_counter()-start
    write_json(WORK/"pilot/summary.json", {"requested": args.count, "valid": sum(r["valid"] for r in records),
        "seconds": elapsed, "mean_seconds": elapsed/args.count,
        "estimated_hours_at_observed_cache_mix": elapsed/args.count*32*20*3*2/3600,
        "depthmap_cache_hits": sum(bool(s["analysis"].get("cache_hit")) for r in records for s in r["states"].values()),
        "timing_note": "Includes cache reuse; new geometries may take longer. Four worker processes by default.",
        "errors": [r.get("error") for r in records if not r["valid"]]})
    print(f"Pilot completed in {elapsed:.1f}s", flush=True)

if __name__ == "__main__": main()

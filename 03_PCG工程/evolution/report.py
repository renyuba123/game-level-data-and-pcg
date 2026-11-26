"""Export inspected candidate presets and matched-budget progress figures."""
from __future__ import annotations
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
from common import WORK, ROOT, read_json, write_json
from simulation import run

def main(name):
    directory = WORK/"runs"/name
    history = read_json(directory/"history.json")
    keys = list(dict.fromkeys(k for h in history if h["method"]=="evolution" for k in h["keys"]))
    records = [read_json(WORK/"cache"/k/"evaluation.json") for k in keys]
    records = [r for r in records if r["valid"]]
    if not records: raise RuntimeError("No valid candidates to export")
    feasible = [r for r in records if r["constraint"] <= 0]
    if not feasible: raise RuntimeError("No candidates passed fairness guardrails; no playable presets published")
    objectives = np.array([r["objectives"] for r in feasible])
    front = NonDominatedSorting().do(objectives, only_non_dominated_front=True)
    pool = [feasible[i] for i in front]
    values = objectives[front]
    scaled = (values-values.min(axis=0))/np.maximum(np.ptp(values, axis=0), 1e-9)
    # Screen a bounded shortlist on held-out episodes before publishing presets.
    # The already-running search/fitness is unchanged; this is an export acceptance gate.
    shortlist = sorted(set(np.argsort(scaled.mean(axis=1))[:5].tolist() +
                           np.argsort(values[:,3])[:5].tolist() + np.argsort(values[:,2])[:5].tolist()))
    accepted, review_rows = [], []
    for index in shortlist:
        record = pool[index]
        heldout_file = WORK/"cache"/record["key"]/"heldout.json"
        if not heldout_file.exists():
            write_json(heldout_file, run(read_json(WORK/"cache"/record["key"]/"layout.json"), heldout=True))
        result = read_json(heldout_file)
        ok = result["fairness_loss"] <= 0
        review_rows.append({"key":record["key"],"accepted":ok,"heldout":result})
        if ok: accepted.append(index)
    write_json(directory/"heldout_export_review.json", {"rule":"heldout fairness_loss <= 0; no early catch/stuck/timeout and at least half escape",
        "scope":"Post-search acceptance; introduced after interim diagnostic review, not a change to fitness", "candidates":review_rows})
    if not accepted:
        raise RuntimeError("No shortlisted candidate passed held-out fairness review; existing previews retained, no new recommended presets published")
    pool = [pool[i] for i in accepted]
    values = values[accepted]
    scaled = (values-values.min(axis=0))/np.maximum(np.ptp(values, axis=0), 1e-9)
    # Scaling here selects a preview from the Pareto set; it never changes fitness/reference normalization.
    choices = {"balanced": int(np.argmin(scaled.mean(axis=1))),
               "exploration": int(np.argmin(values[:,3])), "pressure": int(np.argmin(values[:,2]))}
    presets = {}
    for label, index in choices.items():
        record = pool[index]
        heldout_file = WORK/"cache"/record["key"]/"heldout.json"
        if heldout_file.exists(): heldout = read_json(heldout_file)
        else:
            heldout = run(read_json(WORK/"cache"/record["key"]/"layout.json"), heldout=True)
            write_json(heldout_file, heldout)
        generation = next(h["generation"] for h in history if record["key"] in h["keys"])
        candidate = {"seed": record["seed"], "genes": record["genes"], "generation": generation,
            "evaluation": {"objectives": record["objectives"], "grid": record["grid"], "key": record["key"],
                "status": "coarse-grid candidate; final physics and 200-unit review required", "heldout": heldout,
                "excluded": ["Gate Counts", "Convex Choice"]}}
        write_json(ROOT/f"data/evolution/{label}.json", candidate)
        presets[label] = candidate
    write_json(directory/"pareto.json", pool)
    fig, axes = plt.subplots(1, 2, figsize=(12,4.5), constrained_layout=True)
    for method in ("evolution", "random"):
        for seed in sorted({h["seed"] for h in history}):
            hs = sorted((h for h in history if h["method"]==method and h["seed"]==seed), key=lambda h:h["generation"])
            xs, ys, counts, best, total, valid_count = [], [], [], float("inf"), 0, 0
            for h in hs:
                total += h["evaluations"]; valid_count += h["valid"]
                if h["minimum_objectives"]: best = min(best, h["minimum_objectives"][0])
                xs.append(total); ys.append(best); counts.append(valid_count/total)
            axes[0].plot(xs,ys,label=f"{method} seed {seed}")
            axes[1].plot(xs,counts,label=f"{method} seed {seed}")
    axes[0].set(title="Best structural distance (lower is better)", xlabel="Evaluations per method", ylabel="Fixed-baseline distance")
    axes[1].set(title="Geometry/analysis valid fraction", xlabel="Evaluations per method", ylabel="Fraction")
    for ax in axes: ax.grid(alpha=.2); ax.legend(fontsize=7)
    fig.savefig(directory/"comparison.png", dpi=180)
    plt.close(fig)
    summary = {"run": name, "valid_evolution_candidates": len(records), "fairness_feasible": len(feasible),
        "pareto_count": len(pool), "presets": {k:v["evaluation"]["key"] for k,v in presets.items()},
        "completed_batches": len(history), "note": "Proxy evaluation only. No claim of better player experience or global optimum."}
    write_json(directory/"summary.json", summary)
    print(summary)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("name"); main(parser.parse_args().name)

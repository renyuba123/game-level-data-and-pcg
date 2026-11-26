"""Run and verify a separately registered Generation 0–2 breeding pilot."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import random
from shutil import copyfile

import networkx as nx

from combat_pcg.contracts import require
from combat_pcg.godot_batch import file_hash
from combat_pcg.shell_depthmap import analyze
from full_pcg.breeding.operators import breed, parent_pair
from full_pcg.common import ROOT, digest, read, write
from full_pcg.pilot_contract import register
from full_pcg.shell_genome import graph
from full_pcg.shell_pilot import eligible, evaluate_packet, fronts, load_packet, pareto, select


def prepare(config, source, output, godot, depthmap):
    new = read(config)
    require(new["schema"] == "shell-breeding-pilot/2" and new["run_id"] == "shell_breeding_v2",
            "wrong breeding configuration version")
    require(source != output and not output.is_relative_to(source), "use a separate archive")
    require(new["base_config"] == "configs/shell_pilot_v1.json" and
            0 <= new["crossover_probability"] <= 1 and new["mutations"] == [1, 3],
            "invalid pilot operator configuration")
    require((source/"registration.json").is_file(), "registered v1 source run required")
    require(Path(analyze.__globals__["CLI"]).resolve() == depthmap, "Depthmap executable mismatch")
    base, baseline = register(ROOT/new["base_config"], source, godot, depthmap)
    source_history = source/"genetic"/"generation_00.json"
    spec = base | new
    registration = {
        "run_id": spec["run_id"], "config_sha256": file_hash(config),
        "base_registration_hash": digest(baseline), "base_generation_sha256": file_hash(source_history),
        "tools": baseline["tools"], "total_requests": 24, "maximum_episodes": 288,
        "official_requests": 0, "formal_preflight": baseline["formal_preflight"],
        "implementation": {p.name: file_hash(p) for p in sorted(Path(__file__).parent.glob("*.py"))}
    }
    for name, payload in (("registration.json", registration), ("config_snapshot.json", spec)):
        path = output/name
        if path.exists():
            require(read(path) == payload, f"run identity differs: {path}")
        else:
            write(path, payload)
    return spec, read(source_history)["requests"]


def certificate(root, row):
    return root/"evaluation"/str(row["seed"])/row["layout_hash"]/"certificate.json"


def inherit_evidence(source, output, row):
    original = certificate(source, row)
    target = certificate(output, row)
    if target.exists():
        return
    proof = read(original)
    for name, sha256 in proof["files"].items():
        source_file = (source/name).resolve()
        local_file = (output/name).resolve()
        require(source_file.is_relative_to(source) and local_file.is_relative_to(output),
                "unsafe inherited evidence path")
        require(file_hash(source_file) == sha256, f"invalid original evidence: {name}")
        local_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = local_file.with_suffix(local_file.suffix+".inherit")
        copyfile(source_file, temporary)
        temporary.replace(local_file)
    write(target, proof)


def requests(spec, generation, initial, population, packets, source):
    if generation == 0:
        for row in initial:
            yield dict(row, crossover="initial", operations=[], attempted_parents=None, mutation_count=0,
                       evidence_origin="v1_verified_cache"), load_packet(source, row["layout_hash"])
        return
    pool = [row for row in population if eligible(row)] or population
    require(pool, "no admissible breeding parents")
    for slot in range(spec["population"]):
        rng = random.Random(f'{spec["optimizer_seed"]}:breeding-v2:{generation}:{slot}')
        p1, p2 = parent_pair(pool, rng)
        row, packet = breed(p1, p2, packets, rng, spec["crossover_probability"], spec["max_repairs"],
                            spec["mutations"])
        row.update(id=f"genetic-{generation}-{slot:02}", seed=p1["seed"],
                   layout_hash=packet["layout"]["layout_hash"] if packet else None,
                   topology_changed=not nx.is_isomorphic(graph(packets[p1["layout_hash"]]["layout"]),
                                                         graph(packet["layout"])) if packet else None,
                   fallback_parent=not eligible(p1))
        yield row, packet


def choose(combined, count):
    survivors = select(combined, count)
    kept = {r["id"] for r in survivors}
    ranks = {r["id"]: rank for rank, front in enumerate(fronts(combined), 1) for r in front}
    hashes = {r["layout_hash"] for r in survivors}
    decisions = {}
    for row in combined:
        key = row["id"]
        if key in kept:
            reason = "retained_scored" if eligible(row) else "retained_evidence_fallback"
        elif row["status"] == "INVALID":
            reason = "invalid"
        elif not eligible(row):
            reason = "insufficient_evidence"
        elif row["layout_hash"] in hashes:
            reason = "duplicate_layout"
        else:
            reason = "pareto_rank_or_crowding"
        decisions[key] = {"retained": key in kept, "reason": reason, "rank": ranks.get(key)}
    return survivors, decisions


def run(config, source, output, godot, depthmap, workers, through, verify):
    require(1 <= workers <= 8 and 0 <= through <= 2, "runner limits exceeded")
    spec, initial = prepare(config, source, output, godot, depthmap)
    records, packets, summaries, population = {}, {}, {}, []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for generation in range(through+1):
            path = output/"genetic"/f"generation_{generation:02}.json"
            saved = read(path) if path.exists() else None
            if verify:
                require(saved is not None, f"missing committed generation: {path}")
            if saved is not None and not verify:
                for row in saved["requests"]:
                    key = row["layout_hash"]
                    if key and key not in packets:
                        packets[key] = load_packet(output, key)
                        summaries[key] = evaluate_packet(output, godot, packets[key], spec)
                current = saved
            else:
                cohort, jobs = [], {}
                for row, packet in requests(spec, generation, initial, population, packets, source):
                    key = row["layout_hash"]
                    merged = key is not None and (key in summaries or key in jobs)
                    row["shared_evaluation"] = merged or generation == 0
                    row.setdefault("evidence_origin", "same_run_cache" if merged else "v2_evaluation")
                    if key is not None and not merged:
                        if verify:
                            require(certificate(output, row).is_file(), f"missing certified evaluation: {key}")
                        if generation == 0 and not verify:
                            inherit_evidence(source, output, row)
                        packets[key] = packet
                        jobs[key] = pool.submit(evaluate_packet, output, godot, packet, spec)
                    cohort.append(row)
                    print("proposal", generation, row["id"], row["crossover"], row["mutation_count"],
                          row["layout_hash"], flush=True)
                for key, job in jobs.items():
                    summaries[key] = job.result()
                for row in cohort:
                    evidence = summaries.get(row["layout_hash"])
                    if evidence is None:
                        row["status"] = "INVALID"
                        continue
                    row.update({k: evidence[k] for k in ("scores", "outcomes", "phase2", "missing", "violations")})
                    if row["violations"]:
                        row["status"] = "INVALID"
                    elif row["missing"] or row["outcomes"].get("victory", 0) < 2:
                        row["status"] = "UNCERTAIN"
                    else:
                        row["status"] = "COMPLETE_DRAFT"
                survivors, decisions = choose(population+cohort, spec["population"])
                current = {
                    "generation": generation, "arm": "genetic", "requests": cohort, "selection": decisions,
                    "survivors": [row["id"] for row in survivors], "current_pareto": pareto(survivors),
                    "cumulative_pareto": pareto(list(records.values())+cohort),
                    "scored_count": sum(eligible(row) for row in survivors),
                    "selection_fallback": any(not eligible(row) for row in survivors),
                }
                if verify:
                    require(digest(saved) == digest(current), f"deterministic generation differs: {path}")
                else:
                    write(path, current)
            records.update({row["id"]: row for row in current["requests"]})
            population = [records[key] for key in current["survivors"]]
            print("generation", generation, "committed", len(current["requests"]), "requests", flush=True)
    if through == 2:
        offspring = [row for row in records.values() if row["parents"]]
        inherited = {row["layout_hash"] for row in records.values() if row["evidence_origin"] == "v1_verified_cache"}
        summary = {
            "budget": len(records), "official_requests": 0, "evaluated_layouts": len(summaries),
            "battles": sum(row["episodes"] for key,row in summaries.items() if key not in inherited),
            "reused_battles": sum(summaries[key]["episodes"] for key in inherited),
            "two_parent_offspring": sum(len(row["parents"]) == 2 and row["layout_hash"] is not None for row in offspring),
            "crossover_fallbacks": sum(row["crossover"] == "fallback" for row in offspring),
            "actual_topology_changes": sum(row["topology_changed"] is True and row["status"] != "INVALID" for row in offspring),
        }
        if verify:
            require(read(output/"overview.json") == summary, "deterministic overview differs")
            write(output/"reproducibility.json", {"verified_generations": [0, 1, 2], **summary})
        else:
            write(output/"overview.json", summary)
        print(summary, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("config", "source", "output", "godot", "depthmap"):
        parser.add_argument(arg, type=lambda value: Path(value).resolve())
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--through", type=int, default=2)
    parser.add_argument("--verify", action="store_true")
    run(**vars(parser.parse_args()))

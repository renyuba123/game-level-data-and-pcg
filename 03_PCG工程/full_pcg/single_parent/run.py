"""Register, run or verify the separately budgeted single-parent G0–2 pilot."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from random import Random

import networkx as nx

from combat_pcg.contracts import require
from combat_pcg.godot_batch import file_hash
from combat_pcg.shell_depthmap import analyze
from full_pcg.breeding.run import certificate, choose, inherit_evidence
from full_pcg.common import ROOT, digest, read, write
from full_pcg.pilot_contract import register
from full_pcg.shell_genome import SIBLINGS, graph
from full_pcg.shell_pilot import OBJECTIVES, eligible, evaluate_packet, load_packet, pareto
from full_pcg.single_parent.operators import archive_reference_slots, edit, edit_with_reference, sampling_pool


def prepare(config, source, output, godot, depthmap):
    spec = read(config)
    require(spec["schema"] == "shell-single-parent-pilot/3" and
            spec["run_id"] == "shell_single_parent_v3" and
            spec["base_config"] == "configs/shell_pilot_v1.json", "wrong single-parent pilot version")
    require(0 < spec["full_edit_probability"] < 1 and spec["diff_edits"] == [1, 3] and
            spec["full_edit_regions"] and set(spec["full_edit_regions"]) <= {a for a, _ in SIBLINGS},
            "invalid single-parent operator configuration")
    require(not output.is_relative_to(source) and not source.is_relative_to(output),
            "use a separate archive")
    require((source/"registration.json").is_file(), "registered v1 archive required")
    require(Path(analyze.__globals__["CLI"]).resolve() == depthmap, "Depthmap executable mismatch")
    base, baseline = register(ROOT/spec["base_config"], source, godot, depthmap)
    initial = source/"genetic"/"generation_00.json"
    spec = base | spec
    budget = spec["population"] * (spec["reproductions"] + 1)
    code = sorted(Path(__file__).parent.glob("*.py")) + [ROOT/"full_pcg/breeding/run.py"]
    registration = {
        "run_id": spec["run_id"], "config_sha256": file_hash(config),
        "base_registration_hash": digest(baseline), "base_generation_sha256": file_hash(initial),
        "tools": baseline["tools"], "combat_hash": baseline["combat_hash"],
        "scoring_hash": baseline["scoring_hash"], "formal_preflight": baseline["formal_preflight"],
        "total_requests": budget, "maximum_episodes": budget*len(spec["policies"])*len(spec["scenario_seeds"]),
        "official_requests": 0, "implementation": {p.relative_to(ROOT).as_posix(): file_hash(p) for p in code},
    }
    for name, payload in (("registration.json", registration), ("config_snapshot.json", spec)):
        path = output/name
        if path.exists():
            require(read(path) == payload, f"run identity differs: {path}")
        else:
            write(path, payload)
    cohort = read(initial)["requests"]
    require([row["seed"] for row in cohort] == spec["initial_seeds"], "initial cohort differs")
    return spec, cohort


def proposals(spec, generation, initial, records, pool, packets, source, *, focused=None):
    if generation == 0:
        for initial_row in initial:
            row = {key: initial_row[key] for key in ("id", "genome", "seed", "layout_hash", "operation")}
            row.update(parents=[], edit="initial", operations=[], failures=[], checks=0,
                       genome_hash=digest(row["genome"]), topology_changed=None)
            yield row, load_packet(source, row["layout_hash"])
        return

    require(pool, "no eligible archived parent with four complete objectives")
    weights = [entry["weight"] for entry in pool]
    reference_slots = archive_reference_slots(spec, generation)
    if focused is not None:
        from full_pcg.single_parent.sampling import focused_slots

        focus_ids = {entry["id"] for entry in focused}
        exploratory = [entry for entry in pool if entry["id"] not in focus_ids]
        focus_slots = focused_slots(spec, generation)
    for slot in range(spec["population"]):
        random_key = f'{spec["optimizer_seed"]}:single-parent-v3:{generation}:{slot}'
        rng = Random(random_key)
        if focused is None:
            sample = rng.choices(pool, weights=weights, k=1)[0]
        else:
            is_focus = slot in focus_slots
            candidates = focused if is_focus else exploratory
            source_name = "focused" if is_focus else "explore"
            sample = rng.choices(candidates or pool, weights=(
                [entry["weight"] for entry in candidates] if candidates else weights
            ), k=1)[0] | {"source": source_name, "fallback": not candidates}
        parent = records[sample["id"]]
        base = packets[parent["layout_hash"]]
        if slot in reference_slots:
            reference_rng = Random(f"{random_key}:reference")
            row, packet = edit_with_reference(parent, base, reference_rng, spec,
                                              (records[entry["id"]] for entry in pool))
        else:
            row, packet = edit(parent, base, rng, spec)
        row.update(id=f"single-{generation}-{slot:02}", seed=parent["seed"],
                   random_key=random_key, parent_sample=sample,
                   layout_hash=packet["layout"]["layout_hash"] if packet else None,
                   topology_changed=not nx.is_isomorphic(graph(base["layout"]), graph(packet["layout"]))
                   if packet else None)
        yield row, packet


def evaluate_cohort(proposed, output, source, spec, godot, executor, packets, results, cache_only,
                    *, evaluate=evaluate_packet):
    cohort, jobs = [], {}
    for row, packet in proposed:
        key = row["layout_hash"]
        equivalent = key is not None and (key in results or key in jobs)
        initial = row["edit"] == "initial" and source is not None
        row["shared_evaluation"] = equivalent or initial
        row["evidence_origin"] = ("v1_verified_cache" if initial else "same_run_cache" if equivalent
                                  else "evaluation" if packet else None)
        row["duplicate_layout"] = equivalent
        if key is not None and not equivalent:
            if cache_only:
                require(certificate(output, row).is_file(), f"missing certified evaluation: {key}")
            elif initial:
                inherit_evidence(source, output, row)
            packets[key] = packet
            jobs[key] = executor.submit(evaluate, output, godot, packet, spec)
        cohort.append(row)
        print("proposal", row["id"], row["edit"], len(row["operations"]), key, flush=True)

    for key, job in jobs.items():
        # Backend errors stop at the same request. Successful certificates support retry.
        results[key] = job.result()
    for row in cohort:
        evidence = results.get(row["layout_hash"])
        if evidence is None:
            row["status"] = "INVALID"
            continue
        row.update({key: evidence[key] for key in ("scores", "outcomes", "phase2", "missing", "violations")})
        if row["violations"]:
            row["status"] = "INVALID"
        elif row["missing"] or row["outcomes"].get("victory", 0) < 2:
            row["status"] = "UNCERTAIN"
        else:
            row["status"] = "COMPLETE_DRAFT"
    return cohort


def generation_record(generation, cohort, records, population, spec, pool):
    survivors, selection = choose(population + cohort, spec["population"])
    known = records | {row["id"]: row for row in cohort}
    front = pareto(survivors)
    best = {metric: min((row for row in known.values() if eligible(row)),
                        key=lambda row: (-row["scores"][metric], row["id"]), default=None)
            for metric in OBJECTIVES}
    return {
        "generation": generation, "arm": "random" if spec.get("sampling") == "independent" else "genetic",
        "random_seed": spec["optimizer_seed"],
        "parent_pool": pool, "requests": cohort, "selection": selection,
        "survivors": [row["id"] for row in survivors], "current_pareto": front,
        "cumulative_pareto": pareto(known.values()),
        "representative": min(front, key=lambda key: (
            sum((100 - known[key]["scores"][metric])**2 for metric in OBJECTIVES), key
        )) if front else None,
        "best_by_objective": {metric: row["id"] if row else None for metric, row in best.items()},
        "scored_count": sum(eligible(row) for row in survivors),
        "selection_fallback": any(not eligible(row) for row in survivors),
    }


def summarize(records, results):
    offspring = [row for row in records.values() if row["parents"]]
    inherited = {row["layout_hash"] for row in records.values() if row["evidence_origin"] == "v1_verified_cache"}
    return {
        "requests": len(records), "official_requests": 0,
        "unique_genomes": len({row["genome_hash"] for row in records.values()}),
        "evaluated_layouts": len(results), "status": dict(Counter(row["status"] for row in records.values())),
        "new_certified_battles": sum(row["episodes"] for key, row in results.items() if key not in inherited),
        "inherited_battles": sum(results[key]["episodes"] for key in inherited),
        "duplicate_requests": sum(row["duplicate_layout"] for row in records.values()),
        "edits_requested": dict(Counter(row["edit"] for row in offspring)),
        "edits_realized": dict(Counter(row["edit"] for row in offspring if row["operations"])),
        "actual_topology_changes": sum(row["topology_changed"] is True and row["status"] != "INVALID"
                                       for row in offspring),
    }


def run(config, source, output, godot, depthmap, workers, through, verify):
    require(1 <= workers <= 8 and 0 <= through <= 2, "runner limits exceeded")
    spec, initial = prepare(config, source, output, godot, depthmap)
    records, packets, results, population = {}, {}, {}, []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for generation in range(through+1):
            path = output/"genetic"/f"generation_{generation:02}.json"
            saved = read(path) if path.exists() else None
            if verify:
                require(saved is not None, f"missing committed generation: {path}")
            pool = sampling_pool(records.values()) if generation else []
            proposed = proposals(spec, generation, initial, records, pool, packets, source)
            cohort = evaluate_cohort(proposed, output, source, spec, godot, executor,
                                     packets, results, cache_only=saved is not None)
            current = generation_record(generation, cohort, records, population, spec, pool)
            if saved is None:
                write(path, current)
            else:
                require(digest(saved) == digest(current), f"deterministic generation differs: {path}")
            records.update({row["id"]: row for row in cohort})
            population = [records[key] for key in current["survivors"]]
            print("generation", generation, "verified" if saved else "committed", len(cohort), flush=True)

    if through == spec["reproductions"]:
        overview = summarize(records, results)
        path = output/"overview.json"
        if path.exists() or verify:
            require(read(path) == overview, "deterministic summary differs")
        else:
            write(path, overview)
        if verify:
            write(output/"reproducibility.json", {"verified_generations": list(range(through+1)),
                                                   "workers": workers, **overview})
        print(overview, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "source", "output", "godot", "depthmap"):
        parser.add_argument(name, type=lambda value: Path(value).resolve())
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--through", type=int, default=2)
    parser.add_argument("--verify", action="store_true")
    run(**vars(parser.parse_args()))

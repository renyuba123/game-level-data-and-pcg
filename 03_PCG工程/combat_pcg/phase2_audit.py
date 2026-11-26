"""Fixed-seed combat-layout audit; no simulation or human map scoring."""
import argparse
from collections import Counter
from pathlib import Path

import networkx as nx

from full_pcg.common import ROOT, digest, read, write
from full_pcg.topology import classify, graph

from .layouts import generate
from .protocol import default_combat


def audit(start, stop, output):
    config = read(ROOT / "configs/full_pcg_v2.json")
    combat = default_combat()
    output = Path(output)
    records, valid_genomes = [], []
    for seed in range(start, stop + 1):
        data, report = generate(seed, config, combat)
        genome = data["source_genome"]
        row = {"seed": seed, "ok": report["ok"], "issues": report["issues"],
               "rooms": len(genome["rooms"]), "cycles": len(nx.cycle_basis(graph(genome))),
               "source_genome_hash": digest(genome),
               "layout_hash": data.get("layout", {}).get("layout_hash"),
               "opening_reaction_margin_s": data.get("layout", {}).get("opening_reaction_margin_s")}
        records.append(row)
        if report["ok"]:
            valid_genomes.append(genome)
        write(output / f"seed_{seed:04d}.json", {"data": data, "validation": report})
    accepted = [r for r in records if r["ok"]]
    summary = {"protocol": "combat_v3_draft_001", "config_hash": digest(config),
               "combat_hash": digest(combat), "seed_range": [start, stop], "attempts": len(records),
               "geometric_topological_valid": len(accepted),
               "room_counts": sorted({r["rooms"] for r in accepted}),
               "unlabelled_topologies": len(set(classify(valid_genomes))),
               "cycle_counts": sorted({r["cycles"] for r in accepted}),
               "failures": dict(Counter(issue for r in records for issue in r["issues"])),
               "records": records,
               "limit": "Opening margin is a proxy; no shooting, combat simulation, or Godot physics verified."}
    write(output / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", default="1:100")
    parser.add_argument("--output", default="full_pcg_output/combat_phase2_audit")
    args = parser.parse_args()
    start, stop = map(int, args.seeds.split(":"))
    assert start <= stop
    result = audit(start, stop, ROOT / args.output)
    print({k: v for k, v in result.items() if k != "records"})


if __name__ == "__main__":
    main()

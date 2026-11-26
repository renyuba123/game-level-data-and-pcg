"""Re-evaluate selected coarse candidates against the separate 200-unit reference."""
import argparse
from common import ROOT, WORK, read_json, write_json
from evaluator import Evaluator
from simulation import run

def main(name):
    candidates = {label: read_json(ROOT/f"data/evolution/{label}.json") for label in ("balanced","exploration","pressure")}
    records = Evaluator(200).batch([c["genes"] for c in candidates.values()], WORK/"runs"/name/"fine_review")
    for (label, candidate), record in zip(candidates.items(), records):
        candidate["evaluation"]["fine_review"] = {"grid": 200, "valid": record["valid"],
            "constraint": record["constraint"], "objectives": record["objectives"], "key": record["key"], "error": record.get("error")}
        if record["valid"]:
            heldout_path = WORK/"cache"/record["key"]/"heldout.json"
            if not heldout_path.exists():
                write_json(heldout_path, run(read_json(WORK/"cache"/record["key"]/"layout.json"), heldout=True))
            candidate["evaluation"]["heldout"] = read_json(heldout_path)
        write_json(ROOT/f"data/evolution/{label}.json", candidate)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("name"); main(parser.parse_args().name)

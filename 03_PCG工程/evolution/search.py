"""Mixed-variable NSGA-II survival; durable generation checkpoints and matched random control."""
from __future__ import annotations
import argparse
import pickle
import time
import numpy as np
from pymoo.core.problem import Problem
from pymoo.core.mixed import MixedVariableGA, MixedVariableSampling
from pymoo.operators.survival.rank_and_crowding import RankAndCrowding
from common import WORK, read_json, write_json, digest
from evaluator import Evaluator
from genome import variables, native

class LayoutProblem(Problem):
    def __init__(self, evaluator, directory):
        super().__init__(vars=variables(), n_obj=4, n_ieq_constr=1)
        self.evaluator = evaluator
        self.directory = directory
        self.generation = 0
        self.records = []

    def _evaluate(self, X, out, *args, **kwargs):
        self.records = self.evaluator.batch(X, self.directory/f"generation_{self.generation:03d}", self.generation)
        out["F"] = np.array([r["objectives"] for r in self.records])
        out["G"] = np.array([[r["constraint"]] for r in self.records])

def checkpoint(path, algorithm):
    temp = path.with_suffix(".tmp")
    with temp.open("wb") as stream: pickle.dump(algorithm, stream)
    temp.replace(path)

def run(args):
    directory = WORK/"runs"/args.name
    directory.mkdir(parents=True, exist_ok=True)
    evaluator = Evaluator(args.grid)
    spec = {"population": args.population, "generations": args.generations, "seeds": args.seeds,
            "search_implementation": digest(WORK/"search.py"),
            "grid": args.grid, "recipe": evaluator.recipe, "algorithm": "MixedVariableGA with NSGA-II RankAndCrowding survival"}
    if (directory/"spec.json").exists() and read_json(directory/"spec.json") != spec:
        raise RuntimeError("Run specification changed; use a new --name")
    write_json(directory/"spec.json", spec)
    history = read_json(directory/"history.json") if (directory/"history.json").exists() else []
    start = time.time()
    for seed in args.seeds:
        for method in ("evolution", "random"):
            branch = directory/f"{method}_{seed}"
            branch.mkdir(parents=True, exist_ok=True)
            cp = branch/"checkpoint.pkl"
            problem = LayoutProblem(evaluator, branch)
            completed = {r["generation"] for r in history if r["seed"] == seed and r["method"] == method}
            if method == "evolution":
                if cp.exists():
                    with cp.open("rb") as stream: algorithm = pickle.load(stream)
                    problem = algorithm.problem
                    # The checkpoint is authoritative if interrupted between checkpoint and history write.
                    if problem.generation not in completed and problem.records:
                        records = problem.records
                        valid = [r for r in records if r["valid"]]
                        history.append({"seed": seed, "method": method, "generation": problem.generation,
                            "evaluations": len(records), "valid": len(valid),
                            "minimum_objectives": np.min([r["objectives"] for r in valid], axis=0).tolist() if valid else None,
                            "keys": [r["key"] for r in records]})
                        write_json(directory/"history.json", history)
                        completed.add(problem.generation)
                else:
                    algorithm = MixedVariableGA(pop_size=args.population, survival=RankAndCrowding())
                    algorithm.setup(problem, termination=("n_gen", args.generations), seed=seed, verbose=False)
            for generation in range(1, args.generations+1):
                if generation in completed: continue
                if (directory/"STOP").exists():
                    write_json(WORK/"status.json", {"state": "stopped", "run": args.name, "generation": generation})
                    return
                problem.generation = generation
                write_json(WORK/"status.json", {"state": "running", "run": args.name, "seed": seed, "method": method, "generation": generation, "total_generations": args.generations})
                if method == "evolution":
                    algorithm.next()
                    checkpoint(cp, algorithm)
                    records = problem.records
                else:
                    pop = MixedVariableSampling().do(problem, args.population, random_state=np.random.default_rng(seed*100000+generation))
                    records = evaluator.batch(pop.get("X"), branch/f"generation_{generation:03d}", generation)
                valid = [r for r in records if r["valid"]]
                history = [r for r in history if not (r["seed"]==seed and r["method"]==method and r["generation"]==generation)]
                history.append({"seed": seed, "method": method, "generation": generation, "evaluations": len(records),
                    "valid": len(valid), "minimum_objectives": np.min([r["objectives"] for r in valid], axis=0).tolist() if valid else None,
                    "keys": [r["key"] for r in records]})
                write_json(directory/"history.json", history)
    write_json(WORK/"status.json", {"state": "complete", "run": args.name, "seconds_this_session": time.time()-start})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="search_v1")
    parser.add_argument("--population", type=int, default=32)
    parser.add_argument("--generations", type=int, default=20)
    parser.add_argument("--seeds", nargs="+", type=int, default=[11,29,47])
    parser.add_argument("--grid", type=int, default=400)
    run(parser.parse_args())

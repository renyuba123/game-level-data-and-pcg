"""Schedule and verify local engineering runs using the archived single-parent protocol."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
from functools import partial
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
from random import Random
import re
import subprocess
from threading import Lock
from time import perf_counter
from uuid import uuid4

from combat_pcg.contracts import require
from combat_pcg.godot_batch import file_hash
from combat_pcg.protocol import formal_preflight
from combat_pcg.scoring import default_config
from full_pcg.common import ROOT, digest, read, write
from full_pcg.shell_genome import initial, realize
from full_pcg.shell_pilot import evaluate_packet
from full_pcg.single_parent.run import evaluate_cohort, generation_record, proposals, summarize


SCHEMA = "shell-single-parent-experiment/1"
BASE = ROOT/"configs/shell_pilot_v1.json"
OPERATORS = ROOT/"configs/shell_single_parent_v3.json"


def implementation():
    paths = [BASE, OPERATORS, ROOT/"data/shell_source_v2.json", ROOT/"data/reviewed_shell_partitions.json",
             ROOT/"configs/full_pcg_v2.json", ROOT/"project.godot", ROOT/"evolution/common.py",
             ROOT/"evolution/metrics.py"]
    for folder, pattern in (("combat_pcg", "*.py"), ("full_pcg", "*.py"), ("full_pcg/godot", "*.gd"),
                            ("full_pcg/single_parent", "*.py"), ("full_pcg/breeding", "*.py")):
        paths.extend(path for path in (ROOT/folder).glob(pattern) if not path.name.startswith("test_"))
    return {path.relative_to(ROOT).as_posix(): file_hash(path) for path in sorted(paths)}


def resolve(path, relative_to):
    return (relative_to/Path(os.path.expandvars(path))).resolve()


def settings(config, workers):
    document = read(config)
    required = {"schema", "purpose", "run_id", "optimizer_seed", "population", "reproductions",
                "workers", "output_root", "godot", "depthmap"}
    allowed = required | {"initial_seeds", "initial_archive", "sampling", "diff_operator"}
    require(required <= document.keys() <= allowed, "unexpected or missing experiment settings")
    require(document["schema"] == SCHEMA and document["purpose"] == "development_only",
            "the single-parent experiment entrance currently supports engineering runs")
    identity = document["run_id"]
    require(isinstance(identity, str) and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}", identity),
            "run_id must contain letters, digits, dashes or underscores")
    require(identity.casefold() not in {"shell_draft_pilot_v1", "shell_breeding_v2", "shell_single_parent_v3",
                                      "search_v1"}, "use a new engineering run ID")
    for key, minimum in (("optimizer_seed", 0), ("population", 2), ("reproductions", 0)):
        require(type(document[key]) is int and document[key] >= minimum, f"invalid {key}")
    parallel = document["workers"] if workers is None else workers
    require(type(parallel) is int and 1 <= parallel <= 8, "workers must be between 1 and 8")
    base = read(BASE)
    require(base["source_candidate"] == "near_1_-1" and base["layout_scale"] == 1.5,
            "local experiments require the locked near_1_-1 preset and Map Size 1.5")
    spec = base | {key: document[key] for key in
                   ("schema", "purpose", "run_id", "optimizer_seed", "population", "reproductions")}
    spec.update({key: read(OPERATORS)[key] for key in
                 ("full_edit_probability", "diff_edits", "full_edit_regions")})
    if "sampling" in document:
        require(document["sampling"] in ("archive", "focused", "independent"),
                "unknown sampling strategy")
        require(document["sampling"] != "focused" or spec["population"] == 8,
                "focused sampling requires eight requests per generation")
        spec["sampling"] = document["sampling"]
    if "diff_operator" in document:
        require(document["diff_operator"] == "single_opening_or_partition" and spec.get("sampling") == "focused",
                "the single-opening-or-partition trial requires focused sampling")
        spec["diff_operator"] = document["diff_operator"]
    seeds = document.get("initial_seeds")
    excluded = set(spec["excluded_layout_seeds"])
    if seeds is None:
        require(not document.get("initial_archive"), "initial_seeds are required to reuse an archive")
        rng = Random(f"{spec['optimizer_seed']}:shell-initial")
        seeds = rng.sample(range(2000, 2**31), spec["population"])
    require(isinstance(seeds, list) and all(type(seed) is int and 0 <= seed < 2**31 for seed in seeds)
            and len(seeds) == len(set(seeds)) == spec["population"] and not excluded.intersection(seeds),
            "initial_seeds must be unique, match population and exclude held-out layouts")
    spec["initial_seeds"] = seeds
    output, godot, depthmap = (resolve(document[key], config.parent)
                                for key in ("output_root", "godot", "depthmap"))
    output = (output/identity).resolve()
    require(godot.is_file() and depthmap.is_file(), "Godot or DepthmapX executable missing")
    source = resolve(document["initial_archive"], config.parent) if document.get("initial_archive") else None
    if source:
        require(not output.is_relative_to(source) and not source.is_relative_to(output),
                "initial evidence and new output must use separate archives")
    return spec, output, godot, depthmap, source, parallel


def source_identity(source, spec, tools, scoring):
    if source is None:
        return None
    registration = source/"registration.json"
    snapshot = source/"config_snapshot.json"
    generation = source/"genetic/generation_00.json"
    original = read(registration)
    require(read(snapshot) == read(BASE) and original["config_sha256"] == file_hash(BASE)
            and original["combat_hash"] == digest(spec["combat"])
            and original["scoring_hash"] == digest(scoring), "initial evidence uses another protocol")
    require(all(original["tools"][tool] == tools[tool] for tool in ("godot", "depthmap")),
            "initial evidence uses different engine executables")
    require(set(spec["initial_seeds"]) <= {row["seed"] for row in read(generation)["requests"]
                                            if row.get("layout_hash")},
            "requested seeds are missing certified initial layouts")
    return {p.relative_to(source).as_posix(): file_hash(p) for p in (registration, snapshot, generation)}


@contextmanager
def writer_lock(output):
    output.mkdir(parents=True, exist_ok=True)
    with (output/".writer.lock").open("a+b") as lock:
        lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError(f"another process is writing {output}") from exc
        yield


class RunLog:
    def __init__(self, output):
        folder = output/"runtime"
        folder.mkdir(exist_ok=True)
        self.path = folder/f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid4().hex[:8]}.jsonl"
        self.lock = Lock()

    def event(self, stage, status, **fields):
        entry = dict(time=datetime.now(timezone.utc).isoformat(), stage=stage, status=status, **fields)
        with self.lock, self.path.open("a", encoding="utf-8") as log:
            log.write(json.dumps(entry, ensure_ascii=False, allow_nan=False) + "\n")

    @contextmanager
    def span(self, stage, **fields):
        started = perf_counter()
        self.event(stage, "started", **fields)
        try:
            yield
        except BaseException as exc:
            self.event(stage, "failed", seconds=perf_counter()-started, error=str(exc), **fields)
            raise
        else:
            self.event(stage, "complete", seconds=perf_counter()-started, **fields)


def runtime_summary(output):
    stages, totals = Counter(), Counter()
    for path in sorted((output/"runtime").glob("*.jsonl")):
        lines = path.read_bytes().splitlines(keepends=True)
        for line in lines:
            # A process can stop during its final append. Earlier complete records remain usable.
            if not line.endswith(b"\n"):
                continue
            item = json.loads(line)
            stage, status = item["stage"], item["status"]
            stages[f"{stage}:{status}"] += 1
            if "seconds" in item:
                totals[stage] += item["seconds"]
            if stage == "godot" and status == "started":
                stages["godot_episodes_requested"] += item["scheduled_episodes"]
            if stage == "godot_evidence" and status == "complete":
                stages["godot_episodes_certified"] += item["episodes"]
    return {"counts": dict(stages), "seconds": dict(totals)}


def register(config, output, godot, depthmap, source, spec, resume):
    path = output/"registration.json"
    snapshot = output/"config_snapshot.json"
    scoring = default_config()
    tools = dict(godot=file_hash(godot), depthmap=file_hash(depthmap), python=platform.python_version(),
                 packages={lib: version(lib) for lib in ("numpy", "shapely", "networkx", "scipy", "ezdxf")})
    spec["initial_evidence"] = source_identity(source, spec, tools, scoring)
    requests = spec["population"]*(spec["reproductions"]+1)
    inputs = dict(run_id=spec["run_id"], schema=SCHEMA, config_hash=digest(spec),
                  tools=tools, implementation=implementation(), combat_hash=digest(spec["combat"]),
                  scoring_hash=digest(scoring), formal_preflight=formal_preflight(spec["combat"], scoring),
                  total_requests=requests, maximum_episodes=requests*12, official_requests=0)
    if path.exists():
        require(resume, "run already exists; use --resume")
        previous = read(path)
        require({key: previous[key] for key in inputs} == inputs and read(snapshot) == spec,
                "registered inputs changed; use a new run ID")
    else:
        require(not resume, "no registered run to resume")
        require(all(entry.name in {".writer.lock", "config_snapshot.json", "config_snapshot.json.tmp",
                                   "registration.json.tmp"} for entry in output.iterdir()),
                "output directory already contains unrelated files")
        if snapshot.exists():
            require(read(snapshot) == spec, "unfinished registration uses a different configuration")
        write(snapshot, spec)
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        write(path, dict(inputs, git_commit=commit, source_config_sha256=file_hash(config)))
    return spec


def initial_proposals(spec, source):
    archived = {}
    if source and spec["initial_evidence"]:
        archived = {row["seed"]: row["layout_hash"]
                    for row in read(source/"genetic/generation_00.json")["requests"]}
    for slot, seed in enumerate(spec["initial_seeds"]):
        row = dict(id=f"initial-{slot:02}", seed=seed, genome=None, layout_hash=None,
                   operation=["initial", seed], parents=[], edit="initial", operations=[],
                   failures=[], checks=0, topology_changed=None)
        packet = None
        try:
            row["genome"] = initial(seed)
            packet = realize(row["genome"])
        except ValueError as exc:
            row["failures"].append({"issue": str(exc)})
        if packet:
            row["layout_hash"] = packet["layout"]["layout_hash"]
        if archived:
            require(row["layout_hash"] == archived[seed], f"initial archive Layout differs for seed {seed}")
        row["genome_hash"] = digest(row["genome"])
        yield row, packet


def independent_proposals(spec, generation):
    keys = [f"{spec['optimizer_seed']}:independent:{generation}:{slot}"
            for slot in range(spec["population"])]
    seeds = [Random(key).randrange(2000, 2**31) for key in keys]
    for slot, (row, packet) in enumerate(initial_proposals(spec | {"initial_seeds": seeds}, None)):
        row.update(id=f"random-{generation}-{slot:02}", edit="random_sample",
                   operation=["random_sample", row["seed"]], random_key=keys[slot])
        yield row, packet


def verified_generations(output, spec, workers, through, godot=None, depthmap=None, source=None, log=None):
    records, packets, results, population, fingerprints = {}, {}, {}, [], {}
    arm = output/("random" if spec.get("sampling") == "independent" else "genetic")
    verify = log is None
    inherited = source if not verify else spec["initial_evidence"]

    def trace(stage, **fields):
        return log.span(stage, **fields) if log else nullcontext()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        for number in range(through+1):
            path = arm/f"generation_{number:02}.json"
            saved = read(path) if path.exists() else None
            require(not verify or saved is not None, f"missing committed generation {number}")
            with trace("geometry", generation=number):
                if not number:
                    pool = []
                    proposed = list(initial_proposals(spec, source))
                elif spec.get("sampling") == "independent":
                    pool = []
                    proposed = list(independent_proposals(spec, number))
                else:
                    from full_pcg.single_parent.operators import sampling_pool
                    pool = sampling_pool(records.values())
                    focus = None
                    if spec.get("sampling") == "focused":
                        from full_pcg.single_parent.sampling import focused_pool
                        focus = focused_pool(records, population, pool)
                    proposed = list(proposals(spec, number, (), records, pool, packets, None, focused=focus))
            with trace("evaluation", generation=number,
                       requests=[{"id": row["id"], "layout_hash": row["layout_hash"]} for row, _ in proposed]):
                cohort = evaluate_cohort(proposed, output, inherited, spec, godot, executor, packets,
                                         results, cache_only=saved is not None,
                                         evaluate=partial(evaluate_packet, depthmap=depthmap,
                                                          trace=trace if log else None))
            with trace("selection", generation=number):
                current = generation_record(number, cohort, records, population, spec, pool)
                fingerprints[str(number)] = digest(current)
                if saved is not None:
                    require(digest(saved) == fingerprints[str(number)], f"generation {number} differs")
            if saved is None:
                with trace("commit_generation", generation=number):
                    write(path, current)
            records.update({row["id"]: row for row in cohort})
            population = [records[key] for key in current["survivors"]]
            print(f"G{number} {'verified' if saved is not None else 'committed'} ({len(cohort)} requests)", flush=True)
    overview = summarize(records, results)
    if through == spec["reproductions"]:
        path = output/"overview.json"
        if path.exists() or verify:
            require(read(path) == overview, "deterministic summary differs")
        else:
            write(path, overview)
    return overview, fingerprints, records


def experiment(config, resume=False, through=None, workers=None):
    config = Path(config).resolve()
    spec, output, godot, depthmap, source, parallel = settings(config, workers)
    last = spec["reproductions"] if through is None else through
    require(0 <= last <= spec["reproductions"], "through must name a configured generation")
    with writer_lock(output):
        register(config, output, godot, depthmap, source, spec, resume)
        log = RunLog(output)
        try:
            with log.span("invocation", workers=parallel, through=last, resume=resume,
                          config=str(config), config_sha256=file_hash(config),
                          godot=str(godot), depthmap=str(depthmap)):
                overview, _, _ = verified_generations(output, spec, parallel, last, godot, depthmap, source, log)
        finally:
            write(output/"runtime"/"summary.json", runtime_summary(output))
    return {"run": str(output), "through": last, **overview, "runtime_log": str(log.path)}


def verify_run(output, workers):
    from full_pcg.viewer.archive import Archive

    root = Path(output).resolve()
    archive = Archive(root)
    registration = archive.registration
    spec = archive.config
    require(spec["schema"] == SCHEMA and registration["config_hash"] == digest(spec),
            "verify requires an intact new single-parent experiment archive")
    require(registration["implementation"] == implementation()
            and registration["scoring_hash"] == digest(default_config()),
            "restore the archived implementation and scoring version to rebuild this run")
    require(1 <= workers <= 8, "workers must be between 1 and 8")
    generations, _ = archive.arms["random" if spec.get("sampling") == "independent" else "genetic"]
    last = max(generations)
    require(last <= spec["reproductions"], "archive exceeds registered generation budget")
    overview, hashes, records = verified_generations(root, spec, workers, last)
    evidence = {
        row["layout_hash"]: {
            "package": archive.packet(row["layout_hash"])["package_hash"],
            "space": file_hash(root/"space"/row["layout_hash"]/"comparison.json"),
            "episodes": read(archive.evidence_folder(row)/"episodes/manifest.json")["episode_hashes"],
        }
        for row in records.values() if row["layout_hash"]
    }
    return {"run_id": spec["run_id"], "complete": last == spec["reproductions"], "generations": hashes,
            "evaluation_evidence_hash": digest(evidence), "workers": workers, **overview}


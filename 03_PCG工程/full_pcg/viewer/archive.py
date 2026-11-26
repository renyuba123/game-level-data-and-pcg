"""Read committed generations and their evidence independently of the search."""

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re

import networkx as nx

from full_pcg.common import read
from full_pcg.viewer.depthmap import DEPTHMAP_STATES, read_depthmap_grid

OBJECTIVES = ("S", "F", "P", "D")
SINGLE_PARENT_SCHEMAS = {"shell-single-parent-pilot/3", "shell-single-parent-experiment/1"}
GENERATION_FILE = re.compile(r"generation_(\d+)\.json")
LAYOUT_HASH = re.compile(r"[0-9a-f]{64}")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def room_graph(layout):
    graph = nx.Graph()
    graph.add_nodes_from(room["id"] for room in layout["rooms"])
    graph.add_edges_from((gate["a"], gate["b"]) for gate in layout["portals"])
    return graph


@dataclass(frozen=True)
class Generation:
    number: int
    requests: tuple
    survivors: tuple
    current_pareto: tuple
    cumulative_pareto: tuple
    selection_fallback: bool
    decisions: dict


class Archive:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.config = read(self.root / "config_snapshot.json")
        self.registration = read(self.root / "registration.json")
        self.scale = float(self.config["layout_scale"])
        require(math.isfinite(self.scale) and self.scale > 0, "Invalid layout scale")
        require(self.registration["run_id"] == self.config["run_id"], "Run ID mismatch")
        self.arms = {}
        for directory in sorted(self.root.iterdir()):
            if not directory.is_dir():
                continue
            files = sorted(
                (int(match[1]), path)
                for path in directory.iterdir()
                if path.is_file() and (match := GENERATION_FILE.fullmatch(path.name))
            )
            if files:
                self.arms[directory.name] = self._read_arm(directory.name, files)
        require(bool(self.arms), "No committed generations found")

    def _read_arm(self, arm, files):
        records = {}
        generations = {}
        for expected, (number, path) in enumerate(files):
            item = read(path)
            require(expected == number and item["generation"] == number and item["arm"] == arm,
                    f"Inconsistent generation: {path.name}")
            requests = []
            for row in item["requests"]:
                identity = row["id"]
                require(identity not in records, f"Duplicate individual ID: {identity}")
                for parent in row["parents"]:
                    require(parent in records and records[parent]["born"] < number,
                            f"Unknown or non-ancestral parent for {identity}: {parent}")
                if row.get("edit") == "archive_reference":
                    reference = row["archive_reference"]
                    exemplar = records.get(reference["id"])
                    require(len(row["parents"]) == 1 and reference["id"] not in row["parents"]
                            and exemplar is not None and exemplar["born"] < number
                            and exemplar["layout_hash"] == reference["layout_hash"],
                            f"Invalid archive reference for {identity}")
                records[identity] = dict(row, born=number)
                requests.append(identity)
            groups = [tuple(item[key]) for key in ("survivors", "current_pareto", "cumulative_pareto")]
            for ids in groups:
                require(len(ids) == len(set(ids)) and all(key in records for key in ids),
                        f"Invalid individual references in {arm} generation {number}")
            require(set(groups[1]) <= set(groups[0]), "Current Pareto must be a subset of survivors")
            generations[number] = Generation(number, tuple(requests), *groups, item["selection_fallback"],
                                               item.get("selection", {}))
        return generations, records

    @lru_cache(maxsize=128)
    def packet_path(self, layout_hash):
        require(bool(LAYOUT_HASH.fullmatch(layout_hash)), "Invalid layout hash")
        paths = list((self.root / "packages" / layout_hash).glob("*.json"))
        require(len(paths) == 1, f"Expected one archived package for {layout_hash}")
        path = paths[0].resolve()
        require(path.is_relative_to(self.root), "Package path escapes archive")
        return path

    @lru_cache(maxsize=128)
    def packet(self, layout_hash):
        payload = read(self.packet_path(layout_hash))
        require(payload["layout"]["layout_hash"] == payload["layout_hash"] == layout_hash,
                "Archived layout hash mismatch")
        return payload

    def layout(self, row):
        return self.packet(row["layout_hash"])["layout"] if row.get("layout_hash") else None

    @lru_cache(maxsize=4)
    def extent(self):
        layouts = {row["layout_hash"] for _, rows in self.arms.values() for row in rows.values()
                   if row.get("layout_hash")}
        if not layouts:
            return (-1, -1, 1, 1)
        bounds = [self.packet(key)["layout"]["bounds"] for key in layouts]
        return (min(b[0] for b in bounds)*self.scale - 1, min(b[1] for b in bounds)*self.scale - 1,
                max(b[2] for b in bounds)*self.scale + 1, max(b[3] for b in bounds)*self.scale + 1)

    def evidence_folder(self, row):
        layout_hash = row.get("layout_hash")
        if not layout_hash:
            return None
        self.packet_path(layout_hash)
        require(type(row["seed"]) is int, "Invalid layout seed")
        return self.root / "evaluation" / str(row["seed"]) / layout_hash

    def score_path(self, row):
        folder = self.evidence_folder(row)
        return folder / "score.json" if folder else None

    def depthmap(self, row, state):
        if not row.get("layout_hash"):
            return None
        return self._depthmap(row["layout_hash"], state, row.get("evidence_origin") == "v1_verified_cache")

    @lru_cache(maxsize=64)
    def _depthmap(self, layout_hash, state, inherited):
        require(state in DEPTHMAP_STATES, "Invalid Depthmap analysis state")
        self.packet_path(layout_hash)
        relative = Path("space") / layout_hash / "comparison.json"
        path = self.root / relative
        if not path.is_file():
            return None
        raw = path.read_bytes()
        comparison = json.loads(raw)
        require(comparison["layout_hash"] == layout_hash, "Depthmap 布局哈希不一致")
        layer = read_depthmap_grid(self.root, layout_hash, state, comparison)
        if layer is None and inherited:
            # The historical pilots copied the certified summary, while the v1 run retained the raw exports.
            original = self.root.with_name("shell_draft_pilot_v1")
            source = original / relative
            if source.is_file() and source.read_bytes() == raw:
                layer = read_depthmap_grid(original, layout_hash, state, comparison)
        return layer

    def episode_index(self, row):
        folder = self.evidence_folder(row)
        path = folder / "episodes" / "manifest.json" if folder else None
        if not path or not path.is_file():
            return {}
        index = read(path)
        return index["outcomes"] if index["complete"] else {}

    @lru_cache(maxsize=12)
    def _episode(self, seed, layout_hash, name):
        directory = self.root / "evaluation" / str(seed) / layout_hash / "episodes"
        index = read(directory / "manifest.json")
        require(index["complete"] and name in index["episode_hashes"] and
                bool(re.fullmatch(r"[\w-]+", name)), "Episode is not in the completed manifest")
        path = directory / f"{name}.json"
        raw = path.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == index["episode_hashes"][name],
                f"Episode checksum mismatch: {name}")
        episode = json.loads(raw)
        require(episode["layout_hash"] == layout_hash and episode["case_id"] == name and
                episode["layout_scale"] == self.scale, "Episode layout or scale mismatch")
        return episode

    def episode(self, row, name):
        self.evidence_folder(row)
        return self._episode(row["seed"], row["layout_hash"], name)

    @lru_cache(maxsize=128)
    def topology_count(self, arm, number):
        generations, records = self.arms[arm]
        exemplars = {}
        for identity in generations[number].requests:
            row = records[identity]
            if row["status"] == "INVALID" or not row.get("layout_hash"):
                continue
            graph = room_graph(self.layout(row))
            key = tuple(sorted(degree for _, degree in graph.degree()))
            group = exemplars.setdefault(key, [])
            if not any(nx.is_isomorphic(graph, other) for other in group):
                group.append(graph)
        return sum(len(group) for group in exemplars.values())


def shown_scores(row):
    return {key: row.get("scores", {}).get(key) for key in OBJECTIVES}


def display_q(row):
    values = tuple(shown_scores(row).values())
    if any(value is None for value in values):
        return None
    return sum(value * weight for value, weight in zip(values, (0.15, 0.35, 0.30, 0.20)))


def representative(front, rows):
    """Choose one real individual nearest the fixed ideal (100, 100, 100, 100)."""
    return min(front, key=lambda identity: (
        sum((100 - score)**2 for score in shown_scores(rows[identity]).values()), identity
    )) if front else None

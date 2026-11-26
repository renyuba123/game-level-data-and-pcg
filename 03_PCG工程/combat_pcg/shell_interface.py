"""Portable shell projection and content-addressed identity for calibration evidence."""
from collections import defaultdict
from pathlib import Path
import json
from .contracts import canonical_hash, require
from .layouts import contract_genome


def project(layout):
    require(layout.get("schema_version")==5, "shell Layout v5 required")
    genome=contract_genome({"seed":layout["seed"]},layout)
    neighbors=defaultdict(set)
    openings=defaultdict(list)
    for gate in genome["connections"]:
        for room,other in ((gate["a"],gate["b"]),(gate["b"],gate["a"])):
            neighbors[room].add(other)
            openings[room].append(gate["id"])
    access={r["id"]:{"neighbors":sorted(neighbors[r["id"]]),"ports":sorted(openings[r["id"]])}
            for r in genome["rooms"]}
    for room,entry in access.items():
        current=layout["room_access"][room]
        require(len(entry["neighbors"])==current["neighbors"] and len(entry["ports"])==current["openings"],
                "Layout degree mismatch: "+room)
    return genome,access


def evaluation_key(layout,combat,scoring,scenario,analysis,implementation):
    genome,_=project(layout)
    return canonical_hash({"namespace":"shell-evaluation/1","genome":genome,
        "window":json.loads(Path(__file__).with_name("window_v1.json").read_text()),
        "layout":layout,"combat":combat,"scoring":scoring,"scenario":scenario,
        "analysis":analysis,"implementation":implementation})

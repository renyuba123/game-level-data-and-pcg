from __future__ import annotations
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "evolution"
COURSE_ROOT = ROOT.parent
SOURCE = Path(os.environ.get("RATKING_SOURCE_ROOT", COURSE_ROOT / "02_鼠王关研究"))
SOURCE_GRAPH = SOURCE / "source" / "depthmap" / "shuwang.graph"
SOURCE_DXF = SOURCE / "source" / "cad" / "鼠王关.dxf"
SOURCE_MAPS = SOURCE / "maps" / "ratking" / "shuwang"
CLI = COURSE_ROOT / ".tools" / "depthmapXcli_win64.exe"
GODOT = Path(os.environ.get("GODOT_PATH", r"D:\steam\steamapps\common\Godot Engine\godot.windows.opt.tools.64.exe"))
METRICS = ["Visual Integration [HH]", "Connectivity", "Metric Mean Shortest-Path Distance"]
QUANTILES = [0.05, 0.25, 0.5, 0.75, 0.95]

def digest(value):
    data = value.read_bytes() if isinstance(value, Path) else json.dumps(value, sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)

def command(args, log, timeout=600):
    start = time.perf_counter()
    log = Path(log)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as output:
        completed = subprocess.run([str(a) for a in args], cwd=ROOT, stdout=output,
            stderr=subprocess.STDOUT, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    if completed.returncode:
        raise RuntimeError(f"command failed ({completed.returncode}): {log}\n{log.read_text(errors='replace')[-1200:]}")
    return time.perf_counter() - start

def decode(requests, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    src, dst = directory / "requests.json", directory / "layouts.json"
    write_json(src, requests)
    command([GODOT, "--headless", "--path", ROOT, "--script",
             "res://scripts/evolution_bridge.gd", "--", src, dst], directory / "decode.log", 120)
    return read_json(dst)

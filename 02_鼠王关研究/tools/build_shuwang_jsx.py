"""Embed registered shuwang graph data in the reusable Illustrator renderer."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
map_data = json.loads((root / "maps/ratking/shuwang/render_data.json").read_text(encoding="utf-8"))
runs = [json.loads((root / f"runs/ratking_run-{i:03d}/render_data.json").read_text(encoding="utf-8")) for i in range(1, 6)]
template = (root / "tools/render_shuwang_template.jsx").read_text(encoding="utf-8")
template = template.replace("/*MAP_LITERAL*/null", json.dumps(map_data, ensure_ascii=True, separators=(",", ":")))
template = template.replace("/*RUNS_LITERAL*/null", json.dumps(runs, ensure_ascii=True, separators=(",", ":")))
assert "/*MAP_LITERAL*/" not in template and "/*RUNS_LITERAL*/" not in template
(root / "tools/render_shuwang.jsx").write_text(template, encoding="utf-8")
print("JSX bytes", len(template.encode()), "runs", len(runs), "VGA", len(map_data["vga"]))

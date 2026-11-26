import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
data = json.loads((root / 'maps/ratking/shuwang/render_data.json').read_text(encoding='utf-8'))
template = (root / 'tools/repair_cad_ai_template.jsx').read_text(encoding='utf-8')
template = template.replace('/*DETAILS_LITERAL*/null', json.dumps({k: data[k] for k in ('circles', 'polylines')}, ensure_ascii=True, separators=(',', ':')))
(root / 'tools/repair_cad_ai.jsx').write_text(template, encoding='utf-8')

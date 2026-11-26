"""Validate and inventory the five source/depthmap/shuwang.graph Illustrator deliverables."""
import hashlib
import json
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path(__file__).resolve().parents[1]
map_dir = root / "maps/ratking/shuwang"
map_data = json.loads((map_dir / "render_data.json").read_text(encoding="utf-8"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(root / "source/depthmap/shuwang.graph") == map_data["graph_sha256"]
assert sha(root / "source/cad/鼠王关.dxf") == map_data["dxf_sha256"]
assert len(map_data["walls"]) == 129 and len(map_data["circles"]) == 2 and len(map_data["polylines"]) == 1

rooms = [{"room_id": row[0], "depthmap_ref": row[1], "Choice": row[2],
          "Convex_Connectivity": row[3], "polygon_ai": row[4],
          "source_graph_sha256": map_data["graph_sha256"]}
         for row in map_data["convex"]]
(map_dir / "rooms.json").write_text(json.dumps(rooms, ensure_ascii=False, indent=2), encoding="utf-8")
(map_dir / "connections.json").write_text(json.dumps({"edges": [], "status": "not_exported_from_current_cli_shapegraph_connections; do_not_infer_passable_doors_from_convex_adjacency"}, ensure_ascii=False, indent=2), encoding="utf-8")
metrics = {key: {"min": value["min"], "max": value["max"], "palette_method": value["method"], "bounds": value["bounds"]}
           for key, value in map_data["palettes"].items()}
(map_dir / "summary.json").write_text(json.dumps({"graph_sha256": map_data["graph_sha256"],
    "dxf_sha256": map_data["dxf_sha256"], "convex_regions": len(rooms),
    "vga_points": len(map_data["vga"]), "metrics": metrics,
    "graph_to_ai_transform": map_data["transform"],
    "physical_scale_verified": False}, ensure_ascii=False, indent=2), encoding="utf-8")

views = ["movement", "events", "convex", "visibility", "gate_counts", "metric_distance"]
for index in range(1, 6):
    rid = f"ratking_run-{index:03d}"
    run_dir = root / "runs" / rid
    out = root / "outputs" / rid
    data = json.loads((run_dir / "render_data.json").read_text(encoding="utf-8"))
    source = root / data["source_ai"]
    assert sha(source) == data["source_ai_sha256"], data["source_ai"]
    edited = out / (rid + "_edited.ai")
    assert edited.is_file() and b"%PDF" in edited.read_bytes()[:10]
    assert (out / "shuwang_render.log").read_text(encoding="utf-8").rstrip().endswith("COMPLETE")
    files = [out / (name + "_from_edited_ai" + ext) for name in views for ext in (".svg", ".png")]
    assert all(file.is_file() for file in files)
    for file in files:
        if file.suffix == ".png":
            raw = file.read_bytes()
            assert raw[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">I", raw[16:20])[0] == 1800
        else:
            svg = file.read_bytes()
            assert b"<image" not in svg and b"data:image" not in svg
    for name, layer_id, expected in [("visibility", "F-VGA", 3468),
                                     ("gate_counts", "F-Gate-Counts", 3468),
                                     ("metric_distance", "F-Metric", 3468)]:
        svg = ET.parse(out / (name + "_from_edited_ai.svg")).getroot()
        group = next((item for item in svg.iter() if item.get("id") == layer_id), None)
        assert group is not None, (rid, layer_id)
        assert sum(item.tag.endswith("}rect") for item in group.iter()) == expected, (rid, name)
    svg = ET.parse(out / "convex_from_edited_ai.svg").getroot()
    group = next(item for item in svg.iter() if item.get("id") == "F-ConvexChoice")
    assert sum(item.tag.endswith("}polygon") for item in group.iter()) == 11
    for name in views:
        svg_root = ET.parse(out / (name + "_from_edited_ai.svg")).getroot()
        details = next((item for item in svg_root.iter() if item.get("id") == "F-CAD-Details"), None)
        assert details is not None and len(list(details)) == 3, (rid, name, "missing DXF circles or square")
    max_gap = max(seg["gap"] for seg in data["segments"])
    manifest = {"run_id": rid, "source_ai": data["source_ai"],
                "source_ai_sha256": data["source_ai_sha256"],
                "edited_ai": str(edited.relative_to(root)).replace("\\", "/"),
                "edited_ai_sha256": sha(edited), "edited_ai_reopened_in_illustrator": True,
                "source_graph": "source/depthmap/shuwang.graph", "source_graph_sha256": map_data["graph_sha256"],
                "source_dxf": "source/cad/鼠王关.dxf", "source_dxf_sha256": map_data["dxf_sha256"],
                "registered_transform": map_data["transform"],
                "room_count": 11, "vga_point_count": 3468, "route_segment_count": len(data["segments"]),
                "event_icon_count": len(data["events"]), "max_candidate_route_gap_ai_pt": max_gap,
                "route_order_status": "geometry_candidate_not_video_verified",
                "metric": "Metric Mean Shortest-Path Distance", "metrics": metrics,
                "figure_files_sha256": {file.name: sha(file) for file in files},
                "physical_scale_verified": False,
                "door_passability_verified": False}
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    note = f"""# {rid} QA（source/depthmap/shuwang.graph）

- 原件 `{data['source_ai']}` 保持原哈希 `{data['source_ai_sha256']}`；修改版 AI 由 Illustrator 保存、重新打开，再导出六组 SVG/PNG。
- 共用底图完整读取 `source/cad/鼠王关.dxf` 的 129 条 LINE、2 个 CIRCLE 和 1 个封闭 LWPOLYLINE；后两类对应图中左侧与上方圆、最右小方框，六组 SVG 均含三个 CAD 细节对象。Graph 与 DXF 共享世界 XY，使用已核查的 graph→AI 仿射。新版 Convex 为 11 个 REGION，VGA 为 3,468 点。
- 六组空间指标和图件仅来自 `source/depthmap/shuwang.graph`（SHA-256 `{map_data['graph_sha256']}`）。Gate Counts 83–82,594 count；Visual Integration [HH] 4.5676–17.1735；Metric Mean Shortest-Path Distance 6,209.8452–13,219.324。图上的十档色阶是按真实范围等距划分的**派生色阶**，不是 Depthmap 官方色标，也不是玩家经过频率。
- 本局有 {len(data['segments'])} 条原生 Route 对象、{len(data['events'])} 个原生事件图标；Spawn 编 001，End 单独标注。累计顺序按静态几何推定，最大端点断接 {max_gap:.2f} AI 点；录像时间、重试归属和事件动作均未核实。
- 当前 CLI 的 shapegraph-connections-csv 只有表头，不能据此核实可通行门洞；拓扑边与 PCG 门洞约束保持待核实。物理比例仍未校准。
"""
    (out / "QA_REPORT.md").write_text(note, encoding="utf-8")
    print(rid, "AI", edited.stat().st_size, "figures", len(files), "max gap", max_gap)

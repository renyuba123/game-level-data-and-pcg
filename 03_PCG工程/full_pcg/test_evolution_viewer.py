"""Exercise the viewer with the real pilot archive, when its path is provided."""

from base64 import b64decode
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from full_pcg.common import read
from full_pcg.viewer.archive import Archive

RUN = os.environ.get("RATKING_VIEWER_TEST_ARCHIVE")
SINGLE_PARENT_RUN = os.environ.get("RATKING_SINGLE_PARENT_TEST_ARCHIVE")


class LongLineageRouteTest(unittest.TestCase):
    def test_long_parent_edge_avoids_intervening_cards(self):
        from full_pcg.viewer.lineage import ROW, crosses_box, lineage_route

        start, end = (0.0, -.52), (0.0, -27*ROW+.52)
        boxes = [(-.58, -n*ROW-.58, .58, -n*ROW+.58) for n in range(1, 27)]
        route = lineage_route(start, end, boxes)
        self.assertEqual((route[0], route[-1]), (start, end))
        self.assertLessEqual(len(route), 6)
        self.assertFalse(any(crosses_box(a, b, box) for a, b in zip(route, route[1:]) for box in boxes))


@unittest.skipUnless(RUN, "Set RATKING_VIEWER_TEST_ARCHIVE to the two-generation pilot")
class ViewerIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive = Archive(RUN)

    def test_occurrences_and_plot_coordinates_match_archive(self):
        from full_pcg.viewer.figures import draw_layout

        self.assertEqual(len(self.archive.arms), 2)
        for arm, (generations, rows) in self.archive.arms.items():
            self.assertEqual(len(rows), 24)
            for number, generation in generations.items():
                truth = read(Path(RUN) / arm / f"generation_{number:02}.json")
                self.assertEqual(list(generation.survivors), truth["survivors"])
                self.assertEqual(list(generation.current_pareto), truth["current_pareto"])
                self.assertEqual(list(generation.cumulative_pareto), truth["cumulative_pareto"])

        _, rows = self.archive.arms["genetic"]
        child = rows["genetic-1-00"]
        parent = rows[child["parents"][0]]
        bounds = self.archive.extent()
        fig = draw_layout(self.archive.layout(child), self.archive.scale, bounds,
                          episode=self.archive.episode(child, "occlusion_0"))
        ref = draw_layout(self.archive.layout(parent), self.archive.scale, bounds)
        self.assertEqual(fig.layout.xaxis.range, ref.layout.xaxis.range)
        self.assertEqual(fig.layout.yaxis.range, ref.layout.yaxis.range)
        self.assertEqual(fig.layout.yaxis.scaleratio, 1)
        self.assertIn("玩家阶段 2", {trace.name for trace in fig.data})
        self.assertEqual(fig.layout.margin, ref.layout.margin)
        self.assertFalse(fig.layout.margin.autoexpand)

    def test_viewer_selects_child_and_reports_invalid_candidate(self):
        from streamlit.testing.v1 import AppTest

        app = Path(__file__).with_name("viewer") / "app.py"
        with patch.object(sys, "argv", [str(app), "--run", RUN]):
            at = AppTest.from_file(str(app), default_timeout=30).run()
            self.assertFalse(at.exception or at.error)
            run_selector = next((w for w in at.radio if w.label == "运行档案"), None)
            if run_selector:
                run_selector.set_value(Path(RUN).resolve()).run()
            next(w for w in at.radio if w.label == "个体范围").set_value("本代全部请求").run()
            next(w for w in at.selectbox if w.label == "当前个体").select("genetic-1-00").run()
            next(w for w in at.toggle if w.label == "叠加单局轨迹").set_value(True).run()
            self.assertFalse(at.exception or at.error)
            self.assertTrue(any("直接父代 initial-01" in m.value for m in at.markdown))
            charts = at.get("plotly_chart")
            self.assertEqual(len(charts), 7)
            left, right = charts[1:3]
            self.assertNotEqual(left.proto.id, right.proto.id)
            for chart in (left, right):
                self.assertTrue(json.loads(chart.proto.config)["scrollZoom"])
            left_layout, right_layout = (json.loads(chart.proto.spec)["layout"] for chart in (left, right))
            for key in ("xaxis", "yaxis", "margin", "height"):
                self.assertEqual(left_layout[key], right_layout[key])
            self.assertNotIn("xaxis2", left_layout)
            next(w for w in at.button if w.label == "下一代").click().run()
            self.assertEqual(at.slider("generation").value, 2)
            next(w for w in at.button if w.label == "上一代").click().run()
            next(w for w in at.radio if w.label == "实验组").set_value("random").run()
            next(w for w in at.toggle if w.label == "仅看无效或证据不足").set_value(True).run()
            generations, rows = self.archive.arms["random"]
            invalid = next(key for key in generations[1].requests if rows[key]["status"] == "INVALID")
            next(w for w in at.selectbox if w.label == "当前个体").select(invalid).run()
            self.assertFalse(at.exception or at.error)
            self.assertTrue(any("没有可显示的布局" in info.value for info in at.info))
            self.assertFalse(any(w.label == "在 Godot 中试玩" for w in at.button))

    def test_historical_crossover_uses_cross_outline(self):
        from full_pcg.viewer.lineage import build_lineage

        history = Path(RUN).with_name("shell_breeding_v2")
        if not (history/"genetic"/"generation_02.json").exists():
            self.skipTest("Historical v2 archive unavailable")
        archive = Archive(history)
        generations, rows = archive.arms["genetic"]
        plot = build_lineage(archive, generations, rows, 2)
        crosses = [shape for shape in plot.layout.shapes
                   if shape.type == "path" and shape.path.endswith(" Z") and shape.path.count(" L ") == 11]
        self.assertEqual(len(crosses), sum(len(row["parents"]) == 2 for row in rows.values()))
        self.assertGreater(len(crosses), 0)


class BranchMarkerTest(unittest.TestCase):
    def test_archive_reference_uses_cross_but_fallback_keeps_ordinary_outline(self):
        from full_pcg.viewer.lineage import node_outline

        parent = {"parents": ["parent"]}
        self.assertEqual(node_outline(parent | {"edit": "archive_reference"}), "cross")
        self.assertEqual(node_outline(parent | {"edit": "diff", "archive_reference_attempted": True}), "circle")
        self.assertEqual(node_outline(parent | {"edit": "full", "archive_reference_attempted": True}), "rect")

    def test_validation_selection_and_evidence_have_distinct_markers(self):
        from full_pcg.viewer.lineage import branch_marker

        removed = (1, "test")
        for status, duplicate, expected in (("INVALID", False, "×"),
                                             ("COMPLETE_DRAFT", False, "−"),
                                             ("UNCERTAIN", False, "?"),
                                             ("COMPLETE_DRAFT", True, "≡"),
                                             ("ERROR", False, "!")):
            with self.subTest(status=status, duplicate=duplicate):
                row = {"status": status, "duplicate_layout": duplicate}
                self.assertEqual(branch_marker(row, removed, True)[0], expected)
        self.assertIsNone(branch_marker({"status": "COMPLETE_DRAFT"}, None, True))


@unittest.skipUnless(SINGLE_PARENT_RUN, "Set RATKING_SINGLE_PARENT_TEST_ARCHIVE to v3")
class SingleParentViewerTest(unittest.TestCase):
    def test_depthmap_uses_measured_points_in_world_coordinates(self):
        import csv
        from full_pcg.viewer.depthmap import DISTANCE
        from full_pcg.viewer.figures import draw_layout

        archive = Archive(SINGLE_PARENT_RUN)
        _, rows = archive.arms["genetic"]
        row = rows["single-2-02"]
        grid = archive.depthmap(row, "initial")
        self.assertNotEqual(grid, archive.depthmap(row, "all_open"))
        raw = archive.root/"space"/row["layout_hash"]/"candidate"/"initial"/"metrics.csv"
        with raw.open(encoding="utf-8-sig", newline="") as stream:
            point = next(csv.DictReader(stream))
        self.assertEqual(grid.positions_m[0], (float(point["x"])/1000, float(point["y"])/1000))
        self.assertEqual(grid.values[DISTANCE][0], float(point[DISTANCE])/1000)
        self.assertIsNone(archive.depthmap({"layout_hash": None}, "initial"))
        source = archive.root.with_name("shell_draft_pilot_v1")
        if source.is_dir():
            initial = archive.depthmap(rows["initial-00"], "initial")
            self.assertEqual(initial.source_run, source.name)

        limits = (min(grid.values[DISTANCE]), max(grid.values[DISTANCE]))
        chart = draw_layout(archive.layout(row), archive.scale, archive.extent(),
                            spatial_grid=grid, spatial_metric=DISTANCE, spatial_limits=limits)
        heatmap = chart.data[0]
        self.assertEqual(heatmap.type, "heatmap")
        self.assertEqual((heatmap.zmin, heatmap.zmax), limits)
        self.assertEqual(heatmap.dx, grid.spacing_m*archive.scale)
        self.assertEqual(heatmap.x0, min(p[0] for p in grid.positions_m)*archive.scale)
        self.assertEqual(heatmap.y0, min(p[1] for p in grid.positions_m)*archive.scale)
        self.assertEqual(sum(value is not None for line in heatmap.z for value in line), len(grid.positions_m))
        self.assertFalse(heatmap.connectgaps or heatmap.zsmooth)
    def test_best_ancestor_path_and_preview_follow_generation(self):
        from full_pcg.viewer.lineage import (
            LINEAGE_COLORS, LINEAGE_WIDTHS, NODE_SIZE, ROW, best_lineage, branch_positions, build_lineage,
        )

        archive = Archive(SINGLE_PARENT_RUN)
        generations, rows = archive.arms["genetic"]
        initial, start = best_lineage(rows, 0)
        self.assertEqual((initial, start), ("initial-07", set()))
        best, path = best_lineage(rows, 2)
        self.assertEqual((best, path), ("single-1-05", {("initial-07", "single-1-05")}))
        plot = build_lineage(archive, generations, rows, 2)
        self.assertEqual(len(plot.data[0].customdata), 24)
        self.assertEqual(plot.data[0].type, "bar")
        self.assertEqual(plot.data[0].width, NODE_SIZE)
        leaders = {metric: best_lineage(rows, 2, metric) for metric in LINEAGE_COLORS}
        self.assertEqual({metric: result[0] for metric, result in leaders.items()}, {
            "S": "single-1-05", "F": "single-1-05", "P": "initial-02",
            "D": "single-1-07", "Q": "single-1-05",
        })
        self.assertEqual(best_lineage(rows, 0, "D"), ("initial-07", set()))
        self.assertEqual(leaders["D"][1], {("initial-06", "single-1-07")})
        for metric, (_, ancestors) in leaders.items():
            routes = [shape for shape in plot.layout.shapes if shape.line.color == LINEAGE_COLORS[metric]]
            self.assertEqual(len(routes), len(ancestors))
            self.assertTrue(all(shape.line.width == LINEAGE_WIDTHS[metric] for shape in routes))
        shared = [shape for shape in plot.layout.shapes
                  if shape.line.color in {LINEAGE_COLORS[metric] for metric in ("S", "F", "Q")}]
        self.assertEqual(len(shared), 3)
        self.assertEqual(len({(shape.type, shape.path, shape.x0, shape.y0, shape.x1, shape.y1)
                              for shape in shared}), 3)
        self.assertGreater(LINEAGE_WIDTHS["Q"], LINEAGE_WIDTHS["S"])
        positions, _ = branch_positions(generations, rows, 2)
        for number, generation in generations.items():
            xy = sorted(positions[key] for key in generation.requests)
            self.assertEqual({y for _, y in xy}, {-number*ROW})
            self.assertTrue(all(b[0]-a[0] > NODE_SIZE for a, b in zip(xy, xy[1:])))
        edges = [shape for shape in plot.layout.shapes if shape.line.width in (1.15, *LINEAGE_WIDTHS.values())]
        unique_highlighted = set().union(*(ancestors for _, ancestors in leaders.values()))
        shared_strokes = sum(len(ancestors) for _, ancestors in leaders.values()) - len(unique_highlighted)
        self.assertEqual(len(edges), sum(len(row["parents"]) for row in rows.values()) + shared_strokes)
        self.assertTrue(any(shape.type == "line" for shape in edges))
        self.assertTrue(any(shape.type == "path" and not shape.path.endswith(" Z") for shape in edges))
        captions = [mark.text for mark in plot.layout.annotations]
        for marker in ("S", "F", "P", "D", "★"):
            self.assertEqual(captions.count(f"<b>{marker}</b>"), 1)
        self.assertIn("<b>Initial</b> · 鼠王关.dxf", captions)
        triangles = [shape.path for shape in plot.layout.shapes if shape.type == "path"
                     and shape.path.endswith(" Z") and shape.path.count(" L ") == 2]
        self.assertEqual(len(triangles), 1)
        vertices = [tuple(map(float, point.split(",")))
                    for point in triangles[0][2:-2].replace(" L ", " ").split()]
        for axis in zip(*vertices):
            self.assertAlmostEqual(max(axis) - min(axis), NODE_SIZE)
        self.assertEqual(sum(shape.type == "circle" for shape in plot.layout.shapes),
                         sum(row["edit"] == "diff" for row in rows.values()))
        squares = [shape for shape in plot.layout.shapes if shape.type == "rect"]
        self.assertEqual(len(squares), sum(row["edit"] in ("initial", "full") for row in rows.values()))
        for shape in plot.layout.shapes:
            if shape.type in ("rect", "circle"):
                self.assertAlmostEqual(shape.x1-shape.x0, NODE_SIZE)
                self.assertAlmostEqual(shape.y1-shape.y0, NODE_SIZE)
        self.assertEqual(plot.layout.dragmode, "pan")
        self.assertFalse(plot.layout.xaxis.fixedrange or plot.layout.yaxis.fixedrange)
        self.assertEqual(plot.layout.yaxis.scaleanchor, "x")
        self.assertIn("基于 DXF 生成", captions)
        self.assertEqual(sum(mark.startswith("G0 · ") for mark in captions), 8)
        self.assertTrue(all(any(mark.startswith(f"<b>G{n}</b>") for mark in captions) for n in range(3)))
        self.assertEqual(sum(shape.type == "line" and shape.line.dash == "dot"
                             for shape in plot.layout.shapes), 8)
        self.assertEqual(len(plot.layout.images), 25)
        drawing = ElementTree.fromstring(b64decode(plot.layout.images[0].source.split(",", 1)[1]))
        endpoints = [(float(line.get(x)), float(line.get(y))) for line in drawing.findall("{*}line")
                     for x, y in (("x1", "y1"), ("x2", "y2"))]
        span = max(x for x, _ in endpoints)-min(x for x, _ in endpoints)
        self.assertGreater(span, 70)
        self.assertTrue(all(0 <= y <= 120 and abs(x-60) <= y/2 for x, y in endpoints))
        self.assertIn("<b>−</b>", captions)
        self.assertIn("<b>?</b>", captions)
        self.assertNotIn("<b>×</b>", captions)
        self.assertTrue(any(mark.startswith("single-2-02<br>") for mark in captions))
        self.assertTrue(any(mark.startswith("single-1-05<br>") for mark in captions))

    def test_viewer_loads_ancestry_metrics_and_plot_for_archived_child(self):
        from streamlit.testing.v1 import AppTest
        from full_pcg.viewer import lineage

        app = Path(__file__).with_name("viewer") / "app.py"
        with patch.object(sys, "argv", [str(app), "--run", SINGLE_PARENT_RUN]):
            at = AppTest.from_file(str(app), default_timeout=40).run()
            self.assertFalse(at.exception or at.error)
            at.slider("generation").set_value(2).run()
            chart = at.get("plotly_chart")[0]
            controls = json.loads(chart.proto.config)
            self.assertTrue(controls["displayModeBar"])
            self.assertTrue(controls["responsive"])
            self.assertTrue(controls["scrollZoom"])
            self.assertEqual(controls["doubleClick"], "reset")
            layout = json.loads(chart.proto.spec)["layout"]
            self.assertTrue(layout["autosize"])
            self.assertNotIn("height", layout)
            self.assertEqual(layout["xaxis"]["constrain"], "range")
            self.assertEqual(layout["yaxis"]["constrain"], "range")
            self.assertEqual(layout["yaxis"]["scaleanchor"], "x")
            # Replay the points event sent by the Plotly component to its Streamlit callback.
            widgets = at._tree.get_widget_states()
            ids = json.loads(chart.proto.spec)["data"][0]["customdata"]
            widgets.widgets.add(id=chart.proto.id, string_value=json.dumps({"selection": {
                "points": [{"curve_number": 0, "customdata": "single-2-02"}],
                "point_indices": [ids.index("single-2-02")], "box": [], "lasso": [],
            }}))
            at._run(widgets)
            self.assertFalse(at.exception or at.error)
            self.assertEqual(next(w for w in at.selectbox if w.label == "当前个体").value, "single-2-02")
            self.assertTrue(any("当前个体 single-2-02" in element.value for element in at.markdown))
            self.assertTrue(any("实际父代 single-1-03" in w.value for w in at.text))
            styles = [shape["line"] for shape in json.loads(at.get("plotly_chart")[0].proto.spec)["layout"]["shapes"]
                      if shape.get("fillcolor") == "white" and shape["line"]["width"] == 4]
            self.assertCountEqual([style["dash"] for style in styles], ["solid", "dash"])
            self.assertTrue(any("Pareto 第" in w.value and "此前派生请求" in w.value for w in at.caption))
            self.assertTrue(any("★ 标出最高 Q" in w.value for w in at.caption))
            self.assertTrue(any("G0 的生成来源" in w.value for w in at.caption))
            self.assertTrue(any(w.label == "在 Godot 中试玩" for w in at.button))
            overlay = next(w for w in at.toggle if w.label == "叠加 Depthmap 指标")
            overlay.set_value(True).run()
            next(w for w in at.selectbox if w.label == "空间指标").select("Connectivity").run()
            next(w for w in at.selectbox if w.label == "开口状态").select("all_open").run()
            self.assertFalse(at.exception or at.error)
            charts = [json.loads(chart.proto.spec) for chart in at.get("plotly_chart")[1:3]]
            grids = [chart["data"][0] for chart in charts]
            for grid in grids:
                self.assertEqual(grid["type"], "heatmap")
                self.assertEqual(grid["name"], "可视连接度")
            for key in ("zmin", "zmax", "dx", "dy"):
                self.assertEqual(grids[0][key], grids[1][key])
            for key in ("xaxis", "yaxis", "margin"):
                self.assertEqual(charts[0]["layout"][key], charts[1]["layout"][key])
            self.assertEqual(sum("可破坏通道全开 · " in w.value for w in at.caption), 2)
            next(w for w in at.toggle if w.label == "叠加 Depthmap 指标").set_value(False).run()
            chart = at.get("plotly_chart")[0]
            widgets = at._tree.get_widget_states()
            ids = json.loads(chart.proto.spec)["data"][0]["customdata"]
            widgets.widgets.add(id=chart.proto.id, string_value=json.dumps({"selection": {
                "points": [{"curve_number": 0, "point_index": ids.index("initial-04")}],
                "point_indices": [ids.index("initial-04")], "box": [], "lasso": [],
            }}))
            at._run(widgets)
            self.assertFalse(at.exception or at.error)
            self.assertTrue(any("当前个体 G0 · 05（initial-04）" in element.value for element in at.markdown))
            self.assertTrue(any("已加入从谱系点选" in w.value for w in at.caption))
            at.slider("generation").set_value(0).run()
            self.assertFalse(at.exception or at.error)
            self.assertNotIn("single-2-02", next(w for w in at.selectbox if w.label == "当前个体").options)
            next(w for w in at.radio if w.label == "对照").set_value("其他个体").run()
            next(w for w in at.selectbox if w.label == "对照个体").select("single-2-02").run()
            spec = json.loads(at.get("plotly_chart")[0].proto.spec)
            self.assertIn("single-2-02", spec["data"][0]["customdata"])
            self.assertEqual(sum(shape.get("fillcolor") == "white" and shape["line"]["dash"] == "dash"
                                 for shape in spec["layout"]["shapes"]), 1)
            next(w for w in at.radio if w.label == "对照").set_value("无对照").run()
            spec = json.loads(at.get("plotly_chart")[0].proto.spec)
            self.assertNotIn("single-2-02", spec["data"][0]["customdata"])

        # Streamlit may keep the imported renderer while rerunning a revised app.py.
        renderer = lineage.build_lineage

        def previous_signature(archive, generations, rows, cutoff, highlighted=None):
            return renderer(archive, generations, rows, cutoff, highlighted)

        with patch.object(sys, "argv", [str(app), "--run", SINGLE_PARENT_RUN]), \
                patch.object(lineage, "build_lineage", previous_signature):
            at = AppTest.from_file(str(app), default_timeout=40).run()
            self.assertFalse(at.exception or at.error)


if __name__ == "__main__":
    unittest.main()

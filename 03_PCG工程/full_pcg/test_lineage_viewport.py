import unittest
from unittest.mock import patch


class LineageViewportTest(unittest.TestCase):
    def test_fit_includes_detours_outside_the_initial_bounds(self):
        from plotly.graph_objects import Figure
        from full_pcg.viewer.app import fit_lineage_view

        figure = Figure(layout={
            "xaxis": {"range": [0, 1], "constrain": "domain"},
            "yaxis": {"range": [0, 1], "constrain": "domain"},
            "shapes": [
                {"type": "path", "path": "M -2,1 L 3,0 L 0,-1"},
                {"type": "rect", "x0": 0, "x1": 1, "y0": 0, "y1": 2},
            ],
        })
        fit_lineage_view(figure, "full")
        self.assertLess(figure.layout.xaxis.range[0], -2)
        self.assertGreater(figure.layout.xaxis.range[1], 3)
        self.assertLess(figure.layout.yaxis.range[0], -1)
        self.assertGreater(figure.layout.yaxis.range[1], 2)
        for axis in (figure.layout.xaxis, figure.layout.yaxis):
            self.assertEqual(axis.domain, (0, 1))
            self.assertEqual(axis.constrain, "range")

    def test_returning_to_a_generation_gets_a_fresh_view(self):
        from full_pcg.viewer import app

        with patch.object(app.st, "session_state", {}):
            first = app.lineage_view_key("run", 20, 20)
            self.assertEqual(first, app.lineage_view_key("run", 20, 20))
            app.lineage_view_key("run", 19, 19)
            self.assertNotEqual(first, app.lineage_view_key("run", 20, 20))

import unittest
import numpy as np
from shapely.geometry import Polygon, Point, GeometryCollection
from common import ROOT, WORK, SOURCE_DXF, SOURCE_GRAPH, SOURCE_MAPS, digest, read_json, decode
from simulation import Navigation, move
from metrics import baseline_dxf, table

class PipelineTests(unittest.TestCase):
    def test_narrow_corridor_off_regular_lattice(self):
        floor = Polygon([(0,.11),(5,.11),(5,.25),(0,.25)])
        nav = Navigation(floor, GeometryCollection(),0,anchors=[(x,.18) for x in np.arange(.1,4.91,.1)])
        self.assertTrue(nav.route((.1,.18),(4.9,.18)))

    def test_motion_preserves_corner_trace(self):
        result, trace = move((0,0),[np.array([1.,0]),np.array([1.,1])],2)
        self.assertEqual(list(trace.coords),[(0.,0.),(1.,0.),(1.,1.)])
        self.assertAlmostEqual(trace.length,2)

    def test_source_fills_exclude_blocks(self):
        profile = read_json(ROOT/"data/source_profile.json")
        fills = baseline_dxf(profile,"initial", WORK/"tests/fill_test.dxf")
        verified = {(float(r["x"]),float(r["y"])) for r in table(SOURCE_MAPS / "vga.csv")}
        for x,y in fills:
            self.assertIn((round(x,6),round(y,6)),verified)
            for b in profile["blocks"]:
                self.assertGreater(Point(x/1000,y/1000).distance(Point(b["center_m"])), b["radius_m"])

    def test_same_genome_same_geometry(self):
        requests = [{"seed":42,"genes":{"R05_width":1.02,"door_offset_0":.6}}]*2
        layouts = decode(requests,WORK/"tests/reproducibility")
        self.assertEqual(layouts[0],layouts[1])
        self.assertTrue(layouts[0]["validation"]["ok"])

    def test_sources_unchanged(self):
        profile = read_json(ROOT/"data/source_profile.json")
        self.assertEqual(profile["source_graph_sha256"],digest(SOURCE_GRAPH))
        self.assertEqual(profile["source_dxf_sha256"],digest(SOURCE_DXF))

if __name__=="__main__":
    (WORK/"tests").mkdir(parents=True,exist_ok=True)
    unittest.main()

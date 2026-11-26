import copy
import unittest

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize, unary_union
from shapely import set_precision

from combat_pcg.shell_depthmap import aperture, reference_layout
from combat_pcg.spatial import functional_regions
from full_pcg.common import ROOT, read


class ShellSections(unittest.TestCase):
    def test_window_and_leaf_have_different_openings(self):
        a, b = (0, 0), (2, 0)
        self.assertAlmostEqual(aperture(a, b, 'window').length, 1.1)
        self.assertAlmostEqual(aperture(a, b, 'through').length, 1.8)
        self.assertTrue(aperture(a, b, 'through').intersects(Point(1, 0)))
        self.assertFalse(aperture(a, b, 'window').intersects(Point(1, 0)))
        self.assertEqual(aperture(a, b, 'break').length, 2)

    def test_dxf_partition_and_parallel_portals(self):
        source = read(ROOT / 'data/shell_source_v2.json')
        lines = [set_precision(LineString((w['start_m'], w['end_m'])), .0001)
                 for w in source['wall_segments']]
        overlap = unary_union([Polygon(r['polygon_m']) for r in source['convex_rooms']])
        floor = max(polygonize(unary_union(lines)), key=lambda p: p.intersection(overlap).area)
        layout = reference_layout(source, floor, Point().buffer(0))
        rooms = [p for p, role in functional_regions(layout)]
        self.assertEqual(len(rooms), 6)
        self.assertGreater(unary_union(rooms).area/floor.area, .998)
        self.assertEqual(len(layout['portals'])+len(layout['intra_room_features']), 14)
        duplicate = copy.deepcopy(layout)
        duplicate['portals'] *= 3
        self.assertEqual(functional_regions(duplicate), functional_regions(layout))


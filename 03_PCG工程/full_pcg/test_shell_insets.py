"""Physical split regression for the four wings marked in the layout review."""
import sys
from pathlib import Path
import unittest
from shapely.geometry import Polygon, box

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shell_layout import build, unequal_pair, corner_l, MIN_SIBLING_RATIO
from room_limits import measure


class InsetRooms(unittest.TestCase):
    def test_reject_equal_rooms_and_thin_return(self):
        self.assertFalse(unequal_pair("host",box(0,0,5,4),"pocket",box(5,0,10,4)))
        parent = box(0,0,5,5)
        pocket = box(0,0,3.7,2.0)
        self.assertFalse(unequal_pair("host",parent.difference(pocket),"east_low",pocket))

    def test_reviewed_shape_examples(self):
        # Coordinates of the rejected western rooms, reduced to ordered grid
        # lines; this preserves every wall turn and relative corner placement.
        examples = [
            ([(3, 2), (3, 0), (1, 0), (1, 1), (0, 1), (0, 3), (2, 3), (2, 2)], [(3, 3), (3, 2), (2, 2), (2, 3)]),
            ([(2, 1), (2, 0), (0, 0), (0, 2), (1, 2), (1, 3), (3, 3), (3, 1)], [(2, 1), (3, 1), (3, 0), (2, 0)]),
            ([(2, 1), (2, 0), (0, 0), (0, 2), (1, 2), (1, 3), (3, 3), (3, 1)], [(2, 1), (3, 1), (3, 0), (2, 0)]),
        ]
        for host,pocket in examples:
            self.assertFalse(corner_l(Polygon(host), Polygon(pocket)))
        parent = box(0,0,8,6)
        for pocket in (box(0,0,3,2),box(5,0,8,2),box(0,4,3,6),box(5,4,8,6)):
            self.assertTrue(corner_l(parent.difference(pocket),pocket))
        for pocket in (box(2,0,5,2),box(2,2,5,4),box(0,0,8,2)):
            self.assertFalse(corner_l(parent.difference(pocket),pocket))

    def test_marked_seeds(self):
        for seed in (1,3,5,6):
            with self.subTest(seed=seed):
                layout = build(seed)
                spaces = {r["id"]: Polygon(r["polygon"]) for r in layout["rooms"]}
                host, pocket = spaces["east_high"], spaces["east_low"]
                # Distinct perpendicular shared walls around the inset.
                seam = host.boundary.intersection(pocket.boundary)
                spans = [l.bounds for l in getattr(seam,"geoms",[seam]) if l.geom_type=="LineString"]
                self.assertTrue(any(x1-x0>1.85 for x0,_,x1,_ in spans))
                self.assertTrue(any(y1-y0>1.85 for _,y0,_,y1 in spans))
                self.assertGreater(host.convex_hull.area-host.area,1.0)
                for large, small in (("east_high","east_low"),("left_inner","left_low")):
                    self.assertTrue(corner_l(spaces[large],spaces[small]))
                    a,b = (measure(k,spaces[k])["net_area"] for k in (large,small))
                    self.assertGreaterEqual(a/b,MIN_SIBLING_RATIO)
                if seed == 6:
                    import json
                    path = Path(__file__).resolve().parents[1]/"data/reviewed_shell_partitions.json"
                    approved = json.loads(path.read_text(encoding="utf8"))["6"]["rooms"]
                    for key, points in approved.items():
                        self.assertTrue(spaces[key].equals(Polygon(points)))
                self.assertTrue(all(v["openings"]>=2 for v in layout["room_access"].values()))


if __name__ == "__main__":
    unittest.main()

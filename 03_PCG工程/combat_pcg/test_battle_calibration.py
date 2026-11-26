import unittest

from shapely.geometry import Polygon, GeometryCollection, mapping

from .arena_nav import ArenaNav
from .battle_sensing import RayField
from .calibration_review import perturbations
from .contracts import canonical_hash
from .protocol import default_combat
from .scoring import default_config, validate_config
from .tactical_routes import erase_loops


class CalibrationTests(unittest.TestCase):
    def test_active_window_blocks_contact_at_every_height(self):
        empty=mapping(GeometryCollection())
        w=dict(sill_m=.62,lintel_m=1.98)
        l=dict(walls=empty,base_obstacles=empty,portals=[
            dict(kind='window',id='w',segment=[(0,-.6),(0,.6)]),
            dict(kind='break',id='b',segment=[(3,-.6),(3,.6)]),
        ])
        f=RayField(l,w)
        self.assertTrue(f.clear((-1,0),(1,0),set(),1.15))
        self.assertFalse(f.clear((-1,0),(1,0),set(),.35))
        self.assertFalse(f.clear((-1,0),(1,0),set(),2.1))
        self.assertFalse(f.clear((-1,0),(1,0),{'w'},1.15,contact=True))
        self.assertFalse(f.clear((2,0),(4,0),set(),1.15))
        self.assertTrue(f.clear((2,0),(4,0),{'b'},1.15))

    def test_repeated_patrol_does_not_create_alternative(self):
        self.assertEqual(erase_loops([0,1,2,1,3,3,4]),(0,1,3,4))

    def test_permanent_window_denial_and_break_state(self):
        triangles=[[(0,0),(2,0),(0,2)],[(3,0),(5,0),(3,2)]]
        links=[dict(role=role,portal=kind,kind=kind,points=[(.5,.5),(3.5,.5)])
               for role,kind in [('player','window'),('boss','window'),('boss','break')]]
        packet=dict(navigation={'player':triangles,'boss':triangles},links=links)
        combat=default_combat()
        combat['window']={'duration_s':.65}
        p,b=ArenaNav(packet,'player'),ArenaNav(packet,'boss')
        self.assertTrue(p.path(0,1,set(),combat))
        self.assertFalse(p.path(0,1,set(),combat,'stalker'))
        self.assertTrue(b.path(0,1,set(),combat))
        self.assertNotIn(('gate','window',0),b.graph)

    def test_sensitivity_uses_independent_draft_parameters(self):
        key=canonical_hash(default_config())
        cases=perturbations()
        self.assertEqual(canonical_hash(cases['nominal']),key)
        self.assertTrue(all(validate_config(c) for c in cases.values()))
        self.assertTrue(all(c['display_weights']==cases['nominal']['display_weights'] for c in cases.values()))
        self.assertEqual(canonical_hash(default_config()),key)

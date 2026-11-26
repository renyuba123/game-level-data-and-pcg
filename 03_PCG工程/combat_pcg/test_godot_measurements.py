import unittest

from .godot_measurements import audit_resources, pairs_by_phase
from .protocol import default_combat
from .contracts import ContractError


def frame(**changes):
    return dict(phase=1, boss_visible=True, stalker_visible=False, boss_eta_s=.6, stalker_eta_s=None,
                threat_horizon_s=1.4, reaction_s=.25,escape_s=.16,ready=True,action_risk=False,
                loaded=8,reserve=4,hp=1000) | changes


class GodotMeasurementsTest(unittest.TestCase):
    def test_opportunities_keep_their_denominators(self):
        frames = [frame() for _ in range(39)]
        frames += [frame(loaded=0,reserve=0,ready=False,action_risk=True)]
        frames += [frame(phase=2,loaded=0,reserve=8,ready=False)]
        r = pairs_by_phase(dict(physics_hz=60,frames=frames),default_combat())
        self.assertEqual(r['phase1']['reaction_fraction'],(1,1))
        self.assertEqual(r['phase1']['supply_fraction'],(1,1))
        self.assertAlmostEqual(r['phase1']['shooting_window_fraction'][0],.65)
        self.assertAlmostEqual(r['phase1']['action_risk_fraction'][0],1/60)
        self.assertEqual(r['phase2']['supply_fraction'],(0,0))

    def test_interrupted_aim_does_not_accumulate(self):
        frames = [frame() for _ in range(38)] + [frame(ready=False)] + [frame()]
        r = pairs_by_phase(dict(physics_hz=60,frames=frames),default_combat())
        self.assertEqual(r['phase1']['shooting_window_fraction'][0],0)

    def test_resource_audit_flags_duplicate_pickup(self):
        raw=dict(events=[dict(kind='pickup_end',data=dict(id='a'))]*2,
                 frames=[frame(loaded=8,reserve=20)],result='timeout')
        packet=dict(layout=dict(supplies=[dict(id='a')]))
        with self.assertRaises(ContractError):
            audit_resources(raw,default_combat(),packet)

    def test_resource_conservation_excludes_fabricated_win(self):
        raw=dict(events=[],frames=[frame()],result='victory')
        with self.assertRaises(ContractError):
            audit_resources(raw,default_combat(),dict(layout=dict(supplies=[])))

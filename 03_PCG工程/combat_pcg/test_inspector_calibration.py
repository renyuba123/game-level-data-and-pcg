import unittest

import numpy as np

from .godot_measurements import world_route_packet
from .inspector_calibration import RANGES, crossing_frames, neighbours, passes, rank_key, sample_candidates
from .protocol import default_combat


class InspectorCalibrationTest(unittest.TestCase):
    def test_samples_are_repeatable_and_stay_within_inspector_range(self):
        baseline = default_combat()
        candidates = sample_candidates(baseline)
        self.assertEqual(candidates, sample_candidates(baseline))
        self.assertEqual(len(candidates), 25)
        candidates.update(neighbours(candidates, ['grid_01', 'grid_02', 'grid_03', 'grid_04']))
        self.assertEqual(len(candidates), 33)
        for candidate in list(candidates.values())[1:]:
            self.assertEqual(candidate['portals'], baseline['portals'])
            for _, group, key, lo, hi, _ in RANGES:
                self.assertGreaterEqual(candidate[group][key], lo)
                self.assertLessEqual(candidate[group][key], hi)

    def test_uses_pooled_win_gate_and_weakest_complete_score(self):
        combat = default_combat()
        row = dict(outcomes={'victory': 9}, episodes=12, scores={'F':82,'P':42,'D':9}, violations={})
        self.assertTrue(passes([row]))
        worse_balance = {**row, 'scores':{'F':100,'P':80,'D':8}}
        self.assertGreater(rank_key([row], combat, combat), rank_key([worse_balance], combat, combat))
        self.assertFalse(passes([{**row, 'outcomes':{'victory':8}}]))
        self.assertFalse(passes([{**row, 'scores':{**row['scores'], 'D':None}}]))
        self.assertFalse(passes([{**row, 'violations':{'output_0':['invalid_damage']}}]))

    def test_world_scaling_keeps_opening_and_route_in_same_frame(self):
        original = dict(navigation={'player': [[[1,2],[2,2],[1,3]]]},
                        links=[dict(points=[[1,2],[2,2]])],
                        layout={'portals':[dict(segment=[[1,2],[2,2]])]})
        scaled = world_route_packet(original, 1.5)
        self.assertEqual(scaled['navigation']['player'][0][0], [1.5,3])
        self.assertEqual(scaled['links'][0]['points'], scaled['layout']['portals'][0]['segment'])
        self.assertEqual(original['links'][0]['points'][0], [1,2])
        self.assertEqual(crossing_frames(np.array([[2,2],[2,4],[4,4],[4,2]]),
                                         scaled['links'][0]['points']).tolist(), [1])

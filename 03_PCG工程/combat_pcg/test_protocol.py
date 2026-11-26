import unittest
from .protocol import *
from .scoring import default_config
from .counterexamples import run

class ProtocolTest(unittest.TestCase):
    def test_fixed_budget(self):
        r=validate_combat(default_combat());self.assertEqual(r['total_rounds'],60);self.assertEqual(r['minimum_rounds_for_two_phase_kill'],26);self.assertEqual(r['candidate_requests'],6048)
    def test_insufficient_ammo(self):
        c=default_combat();c['boss']['hp']=100000
        with self.assertRaises(ValueError):validate_combat(c)
    def test_crossing_damage_requires_extra_round(self):
        c=default_combat();c['supplies'].update({'initial_rounds_including_magazine':8,'pack_count':1,'rounds_per_pack':17})
        self.assertEqual(c['supplies']['initial_rounds_including_magazine']+c['supplies']['rounds_per_pack'],25)
        with self.assertRaisesRegex(ValueError,'both phases'):validate_combat(c)
    def test_legacy_escape_not_accepted(self):
        c=default_combat();c['termination']['exit_is_victory']=True
        with self.assertRaises(ValueError):validate_combat(c)
    def test_heldout_separate(self):
        c=default_combat();c['sampling']['heldout_seeds'].append(0)
        with self.assertRaises(ValueError):validate_combat(c)
    def test_player_health_and_stalker_damage_are_validated(self):
        c=default_combat();c['stalker']['damage']=-1
        with self.assertRaises(ValueError):validate_combat(c)
        c=default_combat();c['player']['hp']=0
        with self.assertRaises(ValueError):validate_combat(c)
    def test_draft_cannot_run_formal_search(self):
        self.assertFalse(formal_preflight(default_combat(),default_config())['allowed'])
    def test_counterexamples(self):
        for r in run():
            with self.subTest(case=r['case']):self.assertTrue(r['passed'])

if __name__=='__main__':unittest.main()

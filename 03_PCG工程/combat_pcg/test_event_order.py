import unittest
from .event_order import resolve_step
from .protocol import default_combat

class EventOrderTest(unittest.TestCase):
    def setUp(self):
        self.config=default_combat();self.state={'boss_hp':520,'player_alive':True,'loaded':1,'reserve':0,'split':False,'open_portals':set()}
    def test_cross_split_without_kill(self):
        s,e,o=resolve_step(self.state,[{'kind':'hit','damage':40,'line_of_sight':True}],self.config)
        self.assertEqual((s['boss_hp'],s['split'],e,o),(500,True,['hit','split'],None))
    def test_cross_split_and_kill(self):
        s,e,o=resolve_step(self.state,[{'kind':'hit','damage':800,'line_of_sight':True}],self.config)
        self.assertEqual((s['boss_hp'],s['split'],e,o),(500,True,['hit','split'],None))
        s,e,o=resolve_step(s,[{'kind':'hit','damage':800,'line_of_sight':True}],self.config)
        self.assertEqual((s['boss_hp'],e,o),(0,['hit','victory'],'victory'))
    def test_exact_grab_shot_tie_is_death(self):
        s,e,o=resolve_step(self.state,[{'kind':'hit','damage':800,'line_of_sight':True},{'kind':'grab','valid':True}],self.config)
        self.assertEqual((e,o),(['grab','death'],'death'));self.assertEqual(s['boss_hp'],520)
    def test_death_precedes_pickup(self):
        s,e,o=resolve_step(self.state,[{'kind':'pickup_end','rounds':8},{'kind':'grab','valid':True}],self.config)
        self.assertEqual(s['reserve'],0);self.assertEqual(o,'death')
    def test_reload_before_shot(self):
        state={**self.state,'loaded':0}
        s,e,o=resolve_step(state,[{'kind':'shot'},{'kind':'reload_end','loaded':3}],self.config)
        self.assertEqual((s['loaded'],e),(2,['reload_end','shot']))
    def test_portal_before_los_hit(self):
        s,e,o=resolve_step(self.state,[{'kind':'hit','damage':40,'line_of_sight':True},{'kind':'portal_open','id':'break01','by':'boss'}],self.config)
        self.assertEqual(e,['portal_open','hit','split']);self.assertIn('break01',s['open_portals'])
    def test_blocked_hit_no_damage(self):
        s,e,o=resolve_step(self.state,[{'kind':'hit','damage':800,'line_of_sight':False}],self.config)
        self.assertEqual((s['boss_hp'],o),(520,None))
    def test_victory_beats_timeout(self):
        state={**self.state,'boss_hp':100,'split':True}
        s,e,o=resolve_step(state,[{'kind':'timeout'},{'kind':'hit','damage':800,'line_of_sight':True}],self.config)
        self.assertEqual(o,'victory')
    def test_timeout_at_split_instant(self):
        s,e,o=resolve_step(self.state,[{'kind':'timeout'},{'kind':'hit','damage':800,'line_of_sight':True}],self.config)
        self.assertEqual((s['boss_hp'],e,o),(500,['hit','split','timeout'],'timeout'))

if __name__=='__main__':unittest.main()

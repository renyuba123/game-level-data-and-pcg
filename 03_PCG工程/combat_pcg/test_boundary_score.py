import unittest
from .fixtures import example_measurements
from .scoring import score

class BoundaryScoreTest(unittest.TestCase):
    def test_kill_without_second_phase_is_protocol_error(self):
        m=example_measurements()
        for e in m['episodes']:
            if e['outcome']=='victory':
                e['phase2_reached']=False;e['phase_durations_s']={'phase1':60,'phase2':0}
                e['events']=[e['events'][0],{'id':'shot','t':59,'kind':'shot','data':{}},
                             {'id':'hit','t':60,'kind':'hit','data':{'boss_hp_after':0}},
                             {'id':'victory','t':60,'kind':'victory','data':{}}]
        result=score(m)
        self.assertEqual(result['status'],'ERROR')
        self.assertFalse(result['formal_selection_allowed'])
    def test_split_at_timeout_has_zero_duration_not_victory(self):
        m=example_measurements()
        for e in m['episodes']:
            e['outcome']='timeout';e['phase2_reached']=True;e['phase_durations_s']={'phase1':60,'phase2':0}
            e['events']=[e['events'][0],{'id':'split','t':60,'kind':'split','data':{}},
                         {'id':'timeout','t':60,'kind':'timeout','data':{}}]
        m['phases']['phase2']={}
        result=score(m)
        self.assertEqual(result['status'],'UNCERTAIN')
        self.assertEqual(result['phase_details']['threat_fraction']['phase2']['origin'],'zero_duration')

if __name__=='__main__':unittest.main()

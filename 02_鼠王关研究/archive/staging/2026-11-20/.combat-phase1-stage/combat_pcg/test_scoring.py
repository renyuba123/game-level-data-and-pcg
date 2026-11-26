import copy,math,unittest
from .contracts import ContractError
from .scoring import *
from .fixtures import example_measurements

class ScoreTest(unittest.TestCase):
    def test_hand_calculation(self):
        r=score(example_measurements())
        self.assertEqual(r['status'],'VALID')
        for g,v in {'S':80,'F':90,'P':96,'D':80}.items():self.assertAlmostEqual(r['scores'][g],v)
        self.assertAlmostEqual(r['display_Q'],88.3)
        self.assertEqual(r['objectives'],[-80,-90,-96,-80])
        self.assertFalse(r['formal_selection_allowed'])
    def test_band_boundaries(self):
        spec=default_config()['metrics']['win_fraction']
        for x,q in [(0,0),(.5,100),(.8,100),(1,60)]:self.assertAlmostEqual(quality(x,spec),q)
    def test_display_weights_do_not_change_objectives(self):
        cfg=default_config();cfg['display_weights']={'S':1,'F':0,'P':0,'D':0}
        a=score(example_measurements());b=score(example_measurements(),cfg)
        self.assertEqual(a['objectives'],b['objectives']);self.assertNotEqual(a['display_Q'],b['display_Q'])
    def test_hard_failure_cannot_be_offset(self):
        m=example_measurements();m['checks']['geometry']='INVALID';r=score(m)
        self.assertEqual(r['status'],'INVALID');self.assertIsNone(r['display_Q'])
    def test_system_error_not_bad_map(self):
        m=example_measurements();m['checks']['topology']='ERROR';self.assertEqual(score(m)['status'],'ERROR')
    def test_missing_not_zero(self):
        m=example_measurements();del m['phases']['phase2']['threat_fraction'];r=score(m)
        self.assertEqual(r['status'],'UNCERTAIN');self.assertIsNone(r['scores'])
    def test_no_opportunity_is_explicit(self):
        m=example_measurements();m['phases']['phase1']['supply_fraction'].update(value=None,sample_count=0,state='no_opportunities')
        r=score(m);self.assertEqual(r['status'],'VALID');self.assertLess(r['scores']['F'],90)
    def test_duplicate_repetition_rejected(self):
        m=example_measurements();m['episodes'][1]=copy.deepcopy(m['episodes'][0]);self.assertEqual(score(m)['status'],'ERROR')
    def test_mixed_layout_rejected(self):
        m=example_measurements();m['episodes'][0]['layout_hash']='c'*64;self.assertEqual(score(m)['status'],'ERROR')
    def test_nan_and_wrong_unit(self):
        for delta in [{'value':float('nan')},{'unit':'metres'},{'value':1.2}]:
            m=example_measurements();m['phases']['phase1']['threat_fraction'].update(delta);self.assertEqual(score(m)['status'],'ERROR')
    def test_no_victory_is_uncertain(self):
        m=example_measurements()
        for e in m['episodes']:e['outcome']='timeout';e['events'][-1]['kind']='timeout'
        self.assertEqual(score(m)['status'],'UNCERTAIN')
    def test_early_death_and_unreached_stage_penalized(self):
        m=example_measurements()
        for e in m['episodes']:
            e.update(outcome='death',duration_s=1,phase2_reached=False,phase_durations_s={'phase1':1,'phase2':0})
            e['events']=[e['events'][0],{'id':'death','t':1,'kind':'death','data':{}}]
        m['phases']['phase2']={};r=score(m)
        self.assertEqual(r['status'],'UNCERTAIN');self.assertLess(r['scores']['P'],2)
        self.assertEqual(r['phase_details']['threat_fraction']['phase2']['origin'],'unreached')
    def test_insufficient_count(self):
        m=example_measurements();m['episodes']=m['episodes'][:1];self.assertEqual(score(m)['status'],'UNCERTAIN')
    def test_fake_freeze_rejected(self):
        c=default_config();c['frozen']=True;self.assertEqual(score(example_measurements(),c)['status'],'ERROR')
    def test_bad_weights_rejected(self):
        c=default_config();c['weights']['S']['global_distance']=.8;self.assertEqual(score(example_measurements(),c)['status'],'ERROR')
    def test_serializable_deterministic(self):
        m=example_measurements();a=score(m);self.assertEqual(a,score(m));json.dumps(a,allow_nan=False)
    def test_error_is_json_serializable(self):
        m=example_measurements();m['space']['global_distance']['value']=float('nan')
        r=score(m);self.assertEqual(r['status'],'ERROR');json.dumps(r,allow_nan=False)

if __name__=='__main__':unittest.main()

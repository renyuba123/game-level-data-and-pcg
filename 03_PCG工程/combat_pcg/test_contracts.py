import copy
import unittest
from .contracts import *

def example_genome():
    return {'schema_version':SCHEMA,'units':'model_m','seed':1,
      'rooms':[{'id':r,'position':[i*6,0],'rotation_deg':0,'outline_local':[[0,0],[4,0],[4,4],[0,4]]} for i,r in enumerate(['core','side'])],
      'connections':[{'id':'door','a':'core','b':'side','kind':'through'}],
      'spawn':{'player':{'room_id':'core','position':[1,1],'heading_rad':0},'boss':{'room_id':'core','position':[3,3],'heading_rad':1}},'supplies':[],'obstacles':[]}

def example_episode():
    return {'schema_version':SCHEMA,'episode_id':'ep1','individual_id':'g0_i0','policy':'output','scenario_seed':1,
      'layout_hash':'a'*64,'combat_config_hash':'b'*64,'duration_s':10,'outcome':'timeout','phase2_reached':False,
      'events':[{'id':'0','t':0,'kind':'spawn','data':{}},{'id':'1','t':10,'kind':'timeout','data':{}}]}

class ContractsTest(unittest.TestCase):
    def test_round_trip_hash(self):
        g=example_genome();validate_genome(g)
        self.assertEqual(canonical_hash(g),canonical_hash(json.loads(json.dumps(g))))
    def test_dangling_and_duplicate(self):
        for mutate in [lambda g:g['connections'][0].update(b='missing'),lambda g:g['rooms'].append(copy.deepcopy(g['rooms'][0]))]:
            g=example_genome();mutate(g)
            with self.assertRaises(ContractError):validate_genome(g)
    def test_same_room_and_distinct_coordinates(self):
        for value in [{'room_id':'side','position':[3,3],'heading_rad':0}, {'room_id':'core','position':[1,1],'heading_rad':0}]:
            g=example_genome();g['spawn']['boss']=value
            with self.assertRaises(ContractError):validate_genome(g)
    def test_capability_not_gene(self):
        g=example_genome();g['boss_hp']=1
        with self.assertRaises(ContractError):validate_genome(g)
    def test_bad_units_nan_and_bool(self):
        for v in [float('nan'),float('inf'),True]:
            g=example_genome();g['rooms'][0]['position'][0]=v
            with self.assertRaises(ContractError):validate_genome(g)
        g=example_genome();g['units']='mm'
        with self.assertRaises(ContractError):validate_genome(g)
    def test_episode_terminal_and_order(self):
        e=example_episode();validate_episode(e)
        for mutate in [lambda e:e.update(outcome='victory'),lambda e:e['events'].reverse(),lambda e:e.update(phase2_reached=True)]:
            e=example_episode();mutate(e)
            with self.assertRaises(ContractError):validate_episode(e)
    def test_repeated_content_keeps_occurrences(self):
        a={'schema_version':SCHEMA,'id':'g0_i0','generation':0,'genome_hash':'a'*64,'generation_config_hash':'b'*64,'parent_ids':[],'operations':[],'status':'UNCERTAIN','reasons':['not_evaluated']}
        b={**a,'id':'g1_i0','generation':1,'parent_ids':['g0_i0']}
        validate_individual(a);validate_individual(b)
        self.assertEqual(a['genome_hash'],b['genome_hash']);self.assertNotEqual(a['id'],b['id'])

if __name__=='__main__':unittest.main()

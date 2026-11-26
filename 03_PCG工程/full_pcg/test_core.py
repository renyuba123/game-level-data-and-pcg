import unittest,copy
from .common import ROOT,read,digest
from .topology import sample,classify
from .geometry import generate
from .validation import validate
from .operators import mutate,crossover
class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.config=read(ROOT/'configs/full_pcg_v2.json')
    def test_reproducible_geometry(self):
        a=sample(11,self.config);b=sample(11,self.config);self.assertEqual(a,b)
        self.assertEqual(digest(generate(a,self.config)),digest(generate(b,self.config)))
    def test_renaming_not_topological_change(self):
        a=sample(11,self.config);b=copy.deepcopy(a)
        for r in b['rooms']:r['id']='renamed_'+r['id']
        for e in b['edges']:
            for key in ['a','b']:e[key]='renamed_'+e[key]
        self.assertEqual(classify([a,b]),[0,0])
    def test_translation_not_topological_change(self):
        a=sample(12,self.config);b=copy.deepcopy(a)
        for r in b['rooms']:r['position'][0]+=10
        self.assertEqual(classify([a,b]),[0,0])
    def test_distinct_graphs(self):
        gs=[sample(s,self.config) for s in range(1,31)]
        self.assertGreaterEqual(len(set(classify(gs))),10)
        self.assertGreaterEqual(len(set(len(g['rooms']) for g in gs)),5)
    def test_overlap_rejected(self):
        g=sample(11,self.config);g['rooms'][1]['position']=g['rooms'][0]['position'][:]
        _,qa=generate(g,self.config);self.assertFalse(qa['ok'])
    def test_topology_mutations_are_real(self):
        parent=sample(11,self.config);applied=set();counts=set()
        for seed in range(100):
            child,events=mutate(parent,seed,self.config);counts.add(len(child['rooms']))
            applied.update(e['op'] for e in events if e['status']=='applied')
            self.assertEqual((child,events),mutate(parent,seed,self.config))
        self.assertIn('add_room',applied);self.assertIn('delete_room',applied);self.assertGreater(len(counts),1)
    def test_crossover_or_fallback_is_explicit(self):
        a,b=sample(11,self.config),sample(29,self.config)
        child,events=crossover(a,b,17,self.config)
        self.assertEqual((child,events),crossover(a,b,17,self.config))
        self.assertTrue(any(e['op']=='branch_crossover' for e in events))
        ids={r['id'] for r in child['rooms']}
        self.assertTrue(all(e['a'] in ids and e['b'] in ids for e in child['edges']))
if __name__=='__main__':unittest.main()

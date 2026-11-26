import unittest

from full_pcg.shell_pilot import pareto, select


def scored(id, scores, **extra):
    return dict(id=id, layout_hash=id, scores=dict(zip('SFPD',scores)), status='COMPLETE_DRAFT') | extra


class ShellDraftSelectionTest(unittest.TestCase):
    def test_preserves_tradeoffs_and_keeps_missing_data_out_of_pareto(self):
        space = scored('space',(90,50,45,15))
        combat = scored('combat',(80,80,71,19))
        dominated = scored('dominated',(80,45,43,15))
        missing = scored('missing',(100,100,100,None),status='UNCERTAIN')
        failed = scored('failed',(100,100,100,100),status='INVALID')
        rows = [missing,combat,failed,space,dominated]
        self.assertEqual(pareto(rows),['combat','space'])
        self.assertEqual([r['id'] for r in select(rows,6)],['combat','space','dominated','missing'])

    def test_duplicate_slots_do_not_crowd_out_different_layout(self):
        a = scored('a',(90,70,40,20))
        clone = scored('clone',(90,70,40,20),layout_hash='a')
        b = scored('b',(80,64,41,25))
        self.assertEqual({r['id'] for r in select([a,clone,b],2)},{'a','b'})

import json
import random
import unittest

import networkx as nx

from full_pcg.shell_genome import graph,initial,mutate,realize
from full_pcg.shell_layout import build


class ShellPilotGenomeTest(unittest.TestCase):
    def test_parent_and_topology_edit_reconstruct_from_json(self):
        parent = initial(177)
        packet = realize(json.loads(json.dumps(parent)))
        layout = packet['layout']
        self.assertEqual(layout['layout_hash'], build(177)['layout_hash'])
        child, result, operation, failures = mutate(parent,layout,random.Random(177),8,prefer_topology=True)
        self.assertIsNotNone(result,failures)
        self.assertIn(operation[0],('merge','split','seal_connection','restore_connection'))
        different = result['layout']
        self.assertFalse(nx.is_isomorphic(graph(layout),graph(different)))
        self.assertEqual(parent['seed'],child['seed'])
        self.assertEqual(len(different['supplies']),6)
        self.assertEqual(different['spawn']['room'],different['boss']['room'])
        self.assertEqual(result['package_hash'],realize(json.loads(json.dumps(child)))['package_hash'])

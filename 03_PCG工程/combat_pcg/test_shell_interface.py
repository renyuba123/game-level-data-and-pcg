import unittest
from copy import deepcopy
from .contracts import validate_genome, ContractError
from .test_contracts import example_genome


class PortalGeometry(unittest.TestCase):
    def setUp(self):
        self.g = example_genome()
        self.g["schema_version"]="combat-shell-genome/1"
        first=self.g["connections"][0]
        first.update(width=1.5,segment=[[0,0],[0,1.5]])
        self.g["connections"].append(dict(first,id="window",kind="window",segment=[[0,3],[0,4.5]]))

    def test_parallel_portals_and_old_version(self):
        self.assertEqual(len(validate_genome(self.g)["connections"]),2)
        self.g["schema_version"]="combat-pcg/3"
        with self.assertRaises(ContractError): validate_genome(self.g)

    def test_distinct_geometry_and_width(self):
        for changes in ({"id":"door"},{"width":1.2},{"segment":[[0,1.5],[0,0]]}):
            g=deepcopy(self.g)
            g["connections"][1].update(changes)
            with self.assertRaises(ContractError): validate_genome(g)

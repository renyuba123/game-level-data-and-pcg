"""Phase 2.1: a drawn passage must realize exactly one declared graph edge."""
import unittest

from full_pcg.common import ROOT, read
from full_pcg.topology import sample, classify
from full_pcg.geometry import generate
from full_pcg.geometric_graph import reconstruct


class GeometricTopologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = read(ROOT / "configs/full_pcg_v2.json")

    def test_physical_edges_match_sampled_graph(self):
        for seed in (1, 3, 11):
            with self.subTest(seed=seed):
                genome = sample(seed, self.config)
                layout, report = generate(genome, self.config)
                self.assertTrue(report["ok"], report["issues"])
                observed = reconstruct(layout, self.config)
                self.assertTrue(observed["ok"], observed["issues"])
                expected = {tuple(sorted((edge["a"], edge["b"]))) for edge in genome["edges"]}
                actual = {tuple(edge) for edge in observed["edges"]}
                self.assertEqual(actual, expected)

    def test_room_counts_and_unlabelled_topology_vary(self):
        genomes = [sample(seed, self.config) for seed in range(1, 31)]
        self.assertGreaterEqual(len({len(genome["rooms"]) for genome in genomes}), 5)
        self.assertGreaterEqual(len(set(classify(genomes))), 10)


if __name__ == "__main__":
    unittest.main()

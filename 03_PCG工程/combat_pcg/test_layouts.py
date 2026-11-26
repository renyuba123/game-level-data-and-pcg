import copy
import math
import unittest

from full_pcg.common import ROOT, read
from full_pcg.topology import graph
from .contracts import validate_genome
from .layouts import generate, validate_layout
from .protocol import default_combat


class CombatLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geometry_config = read(ROOT / "configs/full_pcg_v2.json")
        cls.combat = default_combat()

    def test_same_core_distinct_positions_and_fixed_supplies(self):
        for seed in (1, 11, 29):
            with self.subTest(seed=seed):
                data, report = generate(seed, self.geometry_config, self.combat)
                self.assertTrue(report["ok"], report["issues"])
                layout, genome = data["layout"], data["source_genome"]
                self.assertEqual(genome["spawn"], genome["boss"])
                self.assertEqual(layout["spawn"]["room"], layout["boss"]["room"])
                self.assertNotEqual(layout["spawn"]["position"], layout["boss"]["position"])
                self.assertGreater(layout["opening_reaction_margin_s"], 0)
                self.assertGreaterEqual(graph(genome).degree[genome["spawn"]], 3)
                self.assertEqual(len(layout["supplies"]), self.combat["supplies"]["pack_count"])
                self.assertEqual(len({s["room_id"] for s in layout["supplies"]}), len(layout["supplies"]))
                self.assertTrue(all("amount" not in s for s in layout["supplies"]))
                self.assertIs(layout["exit"]["victory_condition"], False)
                validate_genome(data["combat_genome"])
                second, report2 = generate(seed, self.geometry_config, self.combat)
                self.assertEqual(layout["layout_hash"], second["layout"]["layout_hash"])
                self.assertEqual(report, report2)

    def test_supply_count_change_is_rejected(self):
        data, report = generate(1, self.geometry_config, self.combat)
        self.assertTrue(report["ok"])
        layout = copy.deepcopy(data["layout"])
        layout["supplies"].pop()
        checked = validate_layout(layout, data["source_genome"], self.geometry_config, self.combat)
        self.assertIn("supply_pack_count_mismatch", checked["issues"])


if __name__ == "__main__":
    unittest.main()

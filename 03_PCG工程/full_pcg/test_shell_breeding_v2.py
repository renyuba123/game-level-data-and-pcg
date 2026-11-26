"""Verify donor inheritance and selection against the real v2 pilot archive."""

import os
from pathlib import Path
import unittest

from full_pcg.common import digest, read
from full_pcg.shell_genome import polygons
from full_pcg.breeding.operators import locus

RUN = os.environ.get("RATKING_BREEDING_TEST_ARCHIVE")


def corner_signature(genome, host, pocket):
    cells = polygons(genome["partitions"])
    if pocket not in cells:
        return None
    small = cells[pocket]
    envelope = cells[host].union(small)
    x, z, xx, zz = small.bounds
    return (round(xx-x, 6), round(zz-z, 6),
            abs(xx-envelope.bounds[2]) < 1e-5, abs(zz-envelope.bounds[3]) < 1e-5)


@unittest.skipUnless(RUN, "Set RATKING_BREEDING_TEST_ARCHIVE to the completed v2 pilot")
class BreedingArchiveTest(unittest.TestCase):
    def test_actual_second_parent_and_bounded_mutation(self):
        root = Path(RUN)
        cohort = {}
        crossed = 0
        for n in range(3):
            generation = read(root/"genetic"/f"generation_{n:02}.json")
            self.assertEqual(len(generation["requests"]), 8)
            self.assertEqual({key for key,d in generation["selection"].items() if d["retained"]},
                             set(generation["survivors"]))
            for row in generation["requests"]:
                if n:
                    self.assertLessEqual(row["checks"], 8)
                    self.assertLessEqual(row["mutation_count"], 3)
                if row["crossover"] == "fallback":
                    self.assertEqual(len(row["attempted_parents"]), 2)
                    self.assertEqual(len(row["parents"]), 1)
                if row["crossover"] == "applied":
                    crossed += 1
                    a, b = (cohort[key] for key in row["parents"])
                    event = row["operations"][0]
                    _, host, pocket = event["operation"]
                    self.assertEqual(event["kind"], "crossover")
                    self.assertEqual(corner_signature(row["genome"], host, pocket),
                                     corner_signature(b["genome"], host, pocket))
                    self.assertEqual(digest(locus(row["genome"], host, pocket)), event["inherited_locus_hash"])
                    self.assertNotIn(row["layout_hash"], {a["layout_hash"], b["layout_hash"]})
                cohort[row["id"]] = row
        self.assertGreater(crossed, 0)
        self.assertEqual(crossed, read(root/"overview.json")["two_parent_offspring"])


if __name__ == "__main__":
    unittest.main()

"""Assert archive sampling and verify saved single-parent genealogy."""

from collections import Counter
import os
from pathlib import Path
from random import Random
import unittest

import networkx as nx

from full_pcg.common import digest, read
from full_pcg.shell_genome import graph, polygons, realize
from full_pcg.single_parent.operators import archive_reference_slots, corner_position, edit_with_reference, sampling_pool
from full_pcg.viewer.archive import Archive

RUN = os.environ.get("RATKING_SINGLE_PARENT_TEST_ARCHIVE")


def candidate(identity, key, score, status="COMPLETE_DRAFT", parent=None):
    return {"id": identity, "layout_hash": key, "parents": [parent] if parent else [],
            "parent_layout_hash": parent, "status": status, "scores": dict.fromkeys("SFPD", score)}


class SamplingTest(unittest.TestCase):
    def test_original_eligible_record_and_all_submitted_children_determine_weight(self):
        rows = [candidate("parent", "a", 80), candidate("older-not-retained", "b", 60),
                candidate("repeat", "a", 80, parent="a"),
                candidate("invalid", None, None, "INVALID", "a"),
                candidate("uncertain", "c", None, "UNCERTAIN")]
        self.assertEqual(sampling_pool(rows), [
            {"id": "parent", "layout_hash": "a", "rank": 1, "prior_requests": 2, "weight": 1/3},
            {"id": "older-not-retained", "layout_hash": "b", "rank": 2, "prior_requests": 0, "weight": 1/2},
        ])

    def test_missing_four_objectives_gives_empty_pool(self):
        self.assertEqual(sampling_pool([candidate("draft", "a", None)]), [])

    def test_reference_schedule_is_rare_and_deterministic(self):
        spec = {"schema": "shell-single-parent-experiment/1", "optimizer_seed": 177, "population": 8}
        first = [archive_reference_slots(spec, n) for n in range(1, 201)]
        self.assertEqual(first, [archive_reference_slots(spec, n) for n in range(1, 201)])
        self.assertTrue(all(len(slots) <= 1 and slots <= set(range(8)) for slots in first))
        self.assertLess(abs(sum(map(len, first))/1600 - .10), .02)
        self.assertEqual(archive_reference_slots(spec, 0), set())
        self.assertEqual(archive_reference_slots(spec | {"schema": "shell-single-parent-pilot/3"}, 1), set())


@unittest.skipUnless(RUN, "Set RATKING_SINGLE_PARENT_TEST_ARCHIVE to the completed archive")
class RealPilotTest(unittest.TestCase):
    def test_reference_rebuilds_a_corner_with_only_one_parent(self):
        archive = Archive(Path(RUN))
        generations, records = archive.arms["genetic"]
        parent = records["initial-01"]
        references = [records[key] for key in generations[0].requests if records[key]["status"] == "COMPLETE_DRAFT"]
        base = archive.packet(parent["layout_hash"])
        row, layout = edit_with_reference(parent, base, Random(17), archive.config, references)
        self.assertEqual(row["edit"], "archive_reference")
        self.assertEqual(row["parents"], [parent["id"]])
        reference = row["archive_reference"]
        self.assertNotEqual(reference["id"], parent["id"])
        self.assertEqual(reference["layout_hash"], records[reference["id"]]["layout_hash"])
        action, host, pocket = row["operation"]
        self.assertEqual(action, "archive_reference")
        corner = tuple(reference["corner"])
        self.assertEqual(corner_position(polygons(row["genome"]["partitions"]), host, pocket), corner)
        self.assertNotEqual(corner_position(polygons(parent["genome"]["partitions"]), host, pocket), corner)
        self.assertEqual(row["operations"][0]["reference"], reference)
        self.assertLessEqual(row["checks"], archive.config["max_repairs"])
        self.assertNotEqual(layout["layout"]["layout_hash"], parent["layout_hash"])
        replay, rebuilt = edit_with_reference(parent, base, Random(17), archive.config, references)
        self.assertEqual((digest(row), layout["package_hash"]), (digest(replay), rebuilt["package_hash"]))

        fallback, _ = edit_with_reference(parent, base, Random(17), archive.config, [parent])
        self.assertTrue(fallback["archive_reference_attempted"])
        self.assertNotIn("archive_reference", fallback)
        self.assertIn(fallback["edit"], ("diff", "full"))
        self.assertEqual(fallback["parents"], [parent["id"]])

    def test_parent_links_edits_hashes_and_topology_match_archive(self):
        root = Path(RUN)
        archive = Archive(root)
        generations, records = archive.arms["genetic"]
        self.assertEqual(list(generations), [0, 1, 2])
        self.assertTrue(all(len(g.requests) == 8 for g in generations.values()))
        before, successful = {}, Counter()
        changed = 0
        archived_parents = 0
        for n, generation in generations.items():
            summary = read(root/"genetic"/f"generation_{n:02}.json")
            pool = sampling_pool(before.values()) if n else []
            self.assertEqual(summary["parent_pool"], pool)
            for identity in generation.requests:
                child = records[identity]
                self.assertEqual(len(child["parents"]), int(n > 0))
                self.assertLessEqual(child["checks"], 8)
                self.assertEqual(child["genome_hash"], digest(child["genome"]))
                if n:
                    self.assertIn(child["parent_sample"], pool)
                    parent = before[child["parents"][0]]
                    archived_parents += parent["id"] not in generations[n-1].survivors
                    self.assertEqual(parent["layout_hash"], child["parent_layout_hash"])
                    self.assertLessEqual(len(child["operations"]), 1 if child["edit"] == "full" else 3)
                    if child["operations"]:
                        first, last = child["operations"][0], child["operations"][-1]
                        self.assertEqual(first["before_genome"], parent["genome_hash"])
                        self.assertEqual(last["after_genome"], child["genome_hash"])
                        successful[child["edit"]] += 1
                    if child["layout_hash"]:
                        layout = realize(child["genome"])["layout"]
                        self.assertEqual(layout["layout_hash"], child["layout_hash"])
                        difference = not nx.is_isomorphic(graph(layout), graph(archive.layout(parent)))
                        self.assertEqual(child["topology_changed"], difference)
                        changed += difference and child["status"] != "INVALID"
            before.update((identity, records[identity]) for identity in generation.requests)
        overview = read(root/"overview.json")
        self.assertEqual(overview["edits_realized"], dict(successful))
        self.assertEqual(set(successful), {"diff", "full"})
        self.assertGreater(changed, 0)
        self.assertGreater(archived_parents, 0)
        self.assertEqual(overview["actual_topology_changes"], changed)
        self.assertEqual(overview["official_requests"], 0)

from collections import Counter
from pathlib import Path
from random import Random
import unittest
from unittest.mock import patch

from full_pcg.single_parent.experiment import independent_proposals, settings
from full_pcg.single_parent.operators import edit, sampling_pool
from full_pcg.single_parent.run import proposals
from full_pcg.single_parent.sampling import focused_pool, focused_slots


def row(identity, scores):
    return dict(id=identity, layout_hash=identity, parents=[], status="COMPLETE_DRAFT",
                seed=177, scores=dict(zip("SFPD", scores)))


class SamplingComparisonTest(unittest.TestCase):
    def setUp(self):
        self.spec = {"population": 8, "optimizer_seed": 177}
        self.records = {r["id"]: r for r in (
            row("s", (100, 10, 10, 10)), row("f", (10, 100, 10, 10)),
            row("p", (10, 10, 100, 10)), row("d", (10, 10, 10, 100)),
            row("history", (50, 51, 52, 53)), row("dominated", (1, 1, 1, 1)),
        )}

    def test_pool_covers_objectives_and_excludes_dominated_layouts(self):
        archive = sampling_pool(self.records.values())
        focus = focused_pool(self.records, list(self.records.values())[:4], archive)
        self.assertEqual({item["id"] for item in focus}, {"s", "f", "p", "d", "history"})
        self.assertEqual(len(focused_slots(self.spec, 1)), 6)
        self.assertEqual(focused_slots(self.spec, 1), focused_slots(self.spec, 1))

    def test_focused_and_exploratory_samples_keep_exactly_one_parent(self):
        pool = sampling_pool(self.records.values())
        focus = focused_pool(self.records, list(self.records.values())[:4], pool)
        layouts = {i: {"layout": {"rooms": [], "portals": [], "layout_hash": i}} for i in self.records}
        with patch("full_pcg.single_parent.run.edit",
                   side_effect=lambda parent, base, *_: ({"parents": [parent["id"]]}, base)):
            cohort = [r for r, _ in proposals(self.spec, 1, (), self.records, pool, layouts, None, focused=focus)]
            self.assertEqual(Counter(r["parent_sample"]["source"] for r in cohort), {"focused": 6, "explore": 2})
            self.assertTrue(all(len(r["parents"]) == 1 for r in cohort))
            self.assertTrue(all((r["parents"][0] == "dominated") == (r["parent_sample"]["source"] == "explore")
                                for r in cohort))
            fallback = [r for r, _ in proposals(self.spec, 1, (), self.records, focus, layouts, None, focused=focus)]
            self.assertEqual(sum(r["parent_sample"]["fallback"] for r in fallback), 2)

    def test_random_requests_replay_with_no_ancestry_or_replacing_failures(self):
        def initial(spec, source):
            for seed in spec["initial_seeds"]:
                yield {"seed": seed, "parents": [], "failures": [{"issue": "geometry"}]}, None

        with patch("full_pcg.single_parent.experiment.initial_proposals", side_effect=initial):
            first = list(independent_proposals(self.spec, 1))
            self.assertEqual(first, list(independent_proposals(self.spec, 1)))
            self.assertNotEqual(first, list(independent_proposals(self.spec, 2)))
        self.assertEqual(len(first), 8)
        self.assertTrue(all(not r["parents"] and packet is None for r, packet in first))

    def test_checked_in_configs_lock_comparable_inputs(self):
        folder = Path(__file__).parents[1] / "configs"
        a, *_ = settings(folder/"shell_sampling_focused_g20.json", None)
        b, *_ = settings(folder/"shell_sampling_random_g20.json", None)
        ignored = {"run_id", "sampling"}
        self.assertEqual({key: value for key, value in a.items() if key not in ignored},
                         {key: value for key, value in b.items() if key not in ignored})
        self.assertEqual((a["population"], a["reproductions"], a["layout_scale"]), (8, 20, 1.5))

    def test_single_step_changes_one_opening_or_partition(self):
        spec = {"full_edit_probability": 0, "diff_edits": [3, 3], "max_repairs": 8,
                "diff_operator": "single_opening_or_partition"}
        parent = {"id": "parent", "genome": {"before": True}, "layout_hash": "before"}
        base = {"layout": {"layout_hash": "before"}}
        result = {"layout": {"layout_hash": "after"}}
        actions = [("split", "a", "b"), ("seal_connection", "a", "b"), ("shift_opening", "a", "b")]
        prefix = "full_pcg.single_parent.operators"
        with (patch(f"{prefix}.proposals", return_value=actions),
              patch(f"{prefix}.apply_edit", return_value={"after": True}) as apply,
              patch(f"{prefix}.realize", return_value=result),
              patch(f"{prefix}.describe_edit", return_value={"operation": list(actions[-1])})):
            child, packet = edit(parent, base, Random(177), spec)
        self.assertEqual(apply.call_count, 1)
        self.assertEqual(apply.call_args.args[1], actions[-1])
        self.assertEqual((child["edit_target"], len(child["operations"])), (1, 1))
        self.assertEqual(packet, result)

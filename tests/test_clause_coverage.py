import json
from pathlib import Path
import unittest

from babalon.inquiry import _index
from scripts import clause_coverage as trial
from scripts.blind_inquiry_coverage import clause_rank

PILOT = Path(__file__).resolve().parents[1] / "research/ofqual-pilot"


class ClauseCoverageTests(unittest.TestCase):
    def test_cache_preserves_frozen_rankings(self):
        passages = {ref: p["text"] for ref, p in _index(PILOT / "documents")[0].items()}
        packet = json.loads((PILOT / "packet.json").read_bytes())
        for depth in trial.DEPTHS:
            calls = 0
            for item in packet["questions"]:
                q = item["question"]
                views = trial.rank_views(q, passages, depth)
                self.assertEqual(views.clause, clause_rank(q, passages, depth))
                calls += views.calls
            self.assertEqual(calls, 16)

    def test_zero_short_and_identical_returns(self):
        for q, expected in [("unobtainium", 0), ("grades", 1)]:
            rows = trial.run_question(q, {"a": "grades", "b": "records"})
            self.assertEqual(len(rows), len(trial.DEPTHS) * len(trial.METHODS))
            for row in rows.values():
                self.assertEqual(row["matched_spend"], expected)
                self.assertEqual(len(row["matched_refs"]), expected)

    def test_aspect_only_outside_pool_is_ineligible(self):
        views = trial.Views(["a", "b", "c", "d"], ["a", "b", "d", "e"],
                            [["a", "b"], ["outside", "e", "c"]], 3)
        result = trial.choose("clause-coverage", views, 4)
        self.assertEqual(result[0], "a")
        self.assertEqual(len(set(result)), 4)
        self.assertNotIn("outside", result)

    def test_underrepresented_clause_can_outrank_the_next_consensus_passage(self):
        order = ["a", "b", "c", "d"]
        views = trial.Views(order, order, [["a", "b"], ["d", "c"]], 3)
        self.assertEqual(trial.choose("reciprocal-rank", views, 2), ["a", "b"])
        self.assertEqual(trial.choose("clause-coverage", views, 2), ["a", "d"])

    def test_alternative_sets_partial_mixture_and_budget(self):
        groups = [["a", "b"], ["c", "d"]]
        self.assertFalse(trial.evidence_score(["a", "d"], list("abcd"), groups, 2)["complete"])
        alternative = trial.evidence_score(["c", "d"], list("abcd"), groups, 2)
        self.assertTrue(alternative["complete"])
        self.assertEqual(alternative["canonical_hits"], [])
        self.assertFalse(trial.evidence_score(["a"], list("abcd"), groups, 1)["pool_complete"])
        self.assertIsNone(trial.evidence_score(["a"], ["a"], [], 1)["complete"])
        with self.assertRaises(ValueError):
            trial.evidence_score(["a"], ["a"], [[]], 1)

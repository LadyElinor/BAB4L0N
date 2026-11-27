"""Regression checks for equal-spend evidence coverage on the disclosed pilot."""
from pathlib import Path
import subprocess
import sys
import unittest

from scripts.rehearse_ofqual_fusion import check_return, score
from scripts.retrieval_fusion import METHODS, select


ROOT = Path(__file__).resolve().parents[1]


class FusionTest(unittest.TestCase):
    def test_duplicate_ids_get_one_vote_and_one_slot(self):
        families = {"a": "x", "b": "y", "c": "x"}
        for method in METHODS:
            with self.subTest(method=method):
                expected = select(method, ["a", "b"], ["a", "c"], families, 4)
                actual = select(method, ["a", "a", "b"], ["a", "c", "c"], families, 4)
                self.assertEqual(actual, expected)
                self.assertEqual(set(actual), set(families))
                self.assertEqual(len(actual), 3)
                self.assertEqual(select(method, [], [], families, 4), [])
                self.assertEqual(select(method, ["a"], ["b"], families, 0), [])

    def test_rrf_ties_and_source_family_across_documents(self):
        # Two files share one publisher. A new filename alone earns no family slot.
        fixed, clause = ["b", "a", "c"], ["a", "b", "c"]
        families = {"a": "one", "b": "one", "c": "two"}
        self.assertEqual(select("reciprocal-rank", fixed, clause, families, 2), ["a", "b"])
        self.assertEqual(select("source-family", fixed, clause, families, 2), ["a", "c"])

    def test_reservations_can_cost_complete_coverage(self):
        fixed, clause = ["x", "y", "z", "left"], ["x", "y", "z", "right"]
        selected = select("ranker-exclusive", fixed, clause, {}, 4)
        self.assertEqual(selected, ["left", "right", "x", "y"])
        self.assertFalse(score(selected, {"x", "z"})["complete"])
        self.assertTrue(score(fixed, {"x", "z"})["complete"])
        self.assertTrue(score(selected, {"left", "right"})["complete"])

    def test_empty_gold_and_per_row_actual_spend(self):
        self.assertIsNone(score(["a"], set())["complete"])
        corpus = {"a": "A", "b": "B"}
        check_return([], corpus, 0)
        for refs in (["a"], ["a", "a"], ["a", "c"], ["a", "b", "b"]):
            with self.subTest(refs=refs), self.assertRaises(ValueError):
                check_return(refs, corpus, 2)

    def test_receipt_replays_byte_for_byte(self):
        run = subprocess.check_output([sys.executable, str(ROOT / "scripts/rehearse_ofqual_fusion.py")])
        self.assertEqual(run, (ROOT / "reports/ofqual-fusion-development.json").read_bytes())

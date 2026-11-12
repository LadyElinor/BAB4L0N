import tempfile
import unittest
from pathlib import Path

from babalon.inquiry import investigate
from scripts.external_inquiry_trial import run_case, summarize


class ExternalInquiryTests(unittest.TestCase):
    def test_cache_is_per_run_and_gap_can_reach_a_distinct_lead(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.txt").write_text("Resident reported permit.\nPermit arrives.\nPermit delayed.\nPermit filed.")
            first = investigate("resident permit", root, 4, strategy="shared-gap")
            second = investigate("resident permit", root, 4, strategy="shared-gap")
            self.assertEqual(first, second)
            self.assertEqual(first["audit"]["inspections"], 4)
            self.assertGreater(first["audit"]["matched_quotations"], 4)
            self.assertIn("gap", [w["role"] for w in first["rounds"][1]["returns"]])
            empty = investigate("orchid", root, 4, strategy="shared-gap")
            self.assertEqual(empty["audit"]["inspections"], 0)

    def test_gold_does_not_change_readers_and_spend_matches_per_question(self):
        example = {"_id": "synthetic", "question": "where is the violet pump?",
                   "context": [["Station A", ["The violet pump is here.", "Its outlet faces east."]],
                               ["Station B", ["The resident reported an old pump."]]],
                   "supporting_facts": [["Station A", 0]]}
        with tempfile.TemporaryDirectory() as d:
            first = run_case(example, Path(d))
            example["supporting_facts"] = [["Station B", 0]]
            changed = run_case(example, Path(d))
            self.assertEqual(first["arms"], changed["arms"])
            for arm in first["arms"].values():
                self.assertEqual(len(arm["refs"]), len(arm["keyword"]))
                self.assertEqual(len(arm["refs"]), arm["spend"])
            self.assertEqual(summarize([first], "shared-gap")["complete"], 1)

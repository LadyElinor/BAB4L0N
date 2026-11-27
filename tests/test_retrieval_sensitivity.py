"""Check the exposed depth reversal and the distinct-inspection audit."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

from scripts.clause_coverage import DEPTHS
from scripts.clause_membership import compare

ROOT = Path(__file__).resolve().parents[1]


class RetrievalSensitivityTests(unittest.TestCase):
    def test_ofqual_reversal_is_reproducible_at_equal_spend(self):
        data = json.loads(subprocess.check_output([sys.executable, str(ROOT / "scripts/ofqual_depth_sensitivity.py")]))
        self.assertEqual(data["status"], "NOT_PROMOTED")
        self.assertEqual(data["target_bearing_questions"], 5)
        four, five = (data["by_depth"][str(n)] for n in (4, 5))
        self.assertEqual(four["attainable_questions"], five["attainable_questions"])
        self.assertEqual(four["readers"]["ranker-exclusive"]["complete_questions"], ["q1", "q4", "q5"])
        self.assertEqual(five["readers"]["ranker-exclusive"]["complete_questions"], ["q5"])
        q4 = five["questions"]["q4"]
        self.assertEqual(q4["clause_list"][4], "e.txt#L1")
        self.assertIn("e.txt#L1", q4["fixed_list"])
        self.assertNotIn("e.txt#L1", q4["returns"]["ranker-exclusive"]["refs"])
        for depth in ("4", "5", "8", "10"):
            at_depth = data["by_depth"][depth]
            self.assertEqual(at_depth["readers"]["bm25"]["complete_questions"], ["q1", "q5"])
            for method, totals in at_depth["readers"].items():
                self.assertEqual(totals["inspections"], 24)
                self.assertEqual(totals["bm25_calls"], 6 if method == "bm25" else 16)
                self.assertIsNone(at_depth["questions"]["q6"]["returns"][method]["complete"])

    def test_published_audit_with_original_or_fixed_reference(self):
        trace = ROOT / "research/clause-transfer/method-key.json"
        cmd = [sys.executable, str(ROOT / "scripts/clause_membership.py"), str(trace)]
        original = json.loads(subprocess.check_output(cmd))
        explicit = json.loads(subprocess.check_output(cmd + ["--reference", "reciprocal-rank"]))
        self.assertEqual(original, explicit)
        fixed = json.loads(subprocess.check_output(cmd + ["--reference", "bm25"]))
        for depth in ("4", "8"):
            self.assertEqual(original[depth]["different_membership"], [])
            self.assertEqual(fixed[depth]["different_membership"], ["q04", "q05", "q10"])

    def test_declared_charge_requires_actual_distinct_eligible_passages(self):
        for refs, spend in [(["a", "a"], 2), (["a"], 2), (["a", "c"], 2), (["a"], True)]:
            rows = [{"id": "q", "method": f"{m}.d{d}", "pool_refs": ["a", "b"],
                     "matched_refs": refs, "matched_spend": spend}
                    for d in DEPTHS for m in ("clause-coverage", "bm25")]
            with self.subTest(refs=refs, spend=spend), self.assertRaises(ValueError):
                compare(rows, "bm25")

    def test_reordered_common_pool_and_zero_spend(self):
        rows = [{"id": "q", "method": f"{m}.d{d}", "matched_refs": [], "matched_spend": 0,
                 "pool_refs": ["a", "b"] if m == "bm25" else ["b", "a"]}
                for d in DEPTHS for m in ("clause-coverage", "bm25")]
        self.assertEqual(compare(rows, "bm25")[4]["different_membership"], [])
        with self.assertRaisesRegex(ValueError, "missing"):
            compare(rows[:-1], "bm25")

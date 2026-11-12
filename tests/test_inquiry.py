import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from babalon.contracts import Invalid
from babalon.inquiry import investigate


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "inquiry" / "east-tap"
QUESTION = "Was water available at the east tap by 09:00?"


class InquiryTests(unittest.TestCase):
    def test_real_cli_commissions_distinct_workers_and_preserves_the_minority(self):
        args = [sys.executable, "-m", "babalon", "inquire", QUESTION, str(EXAMPLE)]
        report = json.loads(subprocess.check_output(args, cwd=ROOT))
        first, second = report["rounds"]
        self.assertEqual([w["role"] for w in first["returns"]], ["source", "challenge", "assumptions", "affected"])
        self.assertEqual(len({a["question"] for a in first["plan"]}), 4)
        self.assertEqual([w["role"] for w in second["returns"]], ["compare", "trace"])
        self.assertEqual(second["plan"], report["revised_plan"])
        claim, = report["evidence_map"]["explanations"]
        self.assertEqual([a["stance"] for a in claim["accounts"]], ["supports", "supports", "challenges"])
        self.assertEqual(claim["status"], "disputed")
        self.assertIn("timed draw test", claim["proposed_checks"][0]["proposed_observation"])
        self.assertEqual(len(report["evidence_map"]["citations"]), 4)
        self.assertEqual(report["audit"], {"budget": 12, "inspections": 9, "matched_quotations": 9})
        self.assertFalse(report["authority_granted"])
        self.assertEqual(report["external_actions"], 0)
        for rnd in (first, second):
            for w in rnd["returns"]:
                for o in w["observations"]:
                    name, line = o["source"].split("#L")
                    self.assertEqual(o["quotation"], (EXAMPLE / name).read_text().splitlines()[int(line) - 1])
                self.assertTrue(w["uncertainty"])
                self.assertTrue(w["unanswered_questions"])
                self.assertIsInstance(w["interpretation"], str)

    def test_budget_and_round_caps_limit_actual_exposure(self):
        for n in range(13):
            result = investigate(QUESTION, EXAMPLE, n)
            workers = [w for rnd in result["rounds"] for w in rnd["returns"]]
            inspected = sum(len(w["observations"]) for w in workers)
            self.assertEqual(result["audit"]["inspections"], inspected)
            self.assertLessEqual(inspected, n)
            if n == 0:
                self.assertEqual(result["evidence_map"]["explanations"], [])
                self.assertTrue(all(not w["sources"] for w in workers))
        one = investigate(QUESTION, EXAMPLE, rounds=1)
        self.assertEqual(len(one["rounds"]), 1)
        self.assertTrue(one["revised_plan"])
        self.assertFalse(one["evidence_map"]["explanations"][0]["proposed_checks"])
        self.assertIn("uninspected", {edge["status"] for edge in one["evidence_map"]["citations"]})

    def test_ordinary_text_leads_and_context_remain_unclassified(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "desk.txt").write_text("Tap pressure was restored.\nThe sensor is inside the pump house.")
            (root / "field.txt").write_text("The tap still ran dry.\nThe note was written at the east steps.")
            report = investigate("tap pressure", root)
            self.assertTrue(report["evidence_map"]["unclassified_comparison_leads"])
            self.assertEqual(report["evidence_map"]["explanations"], [])
            self.assertEqual(report["rounds"][1]["returns"][0]["role"], "compare")
            self.assertIn("desk.txt#L2", report["rounds"][1]["returns"][0]["sources"])
            self.assertEqual(report, investigate("tap pressure", root))
            unrelated = investigate("orchids", root)
            self.assertEqual(unrelated["audit"]["inspections"], 0)
            self.assertTrue(unrelated["rounds"][0]["returns"][3]["unanswered_questions"])

    def test_changed_source_and_new_contrary_evidence_discovered_during_trace(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "claim.md").write_text("Supports [hardware]: Pump restarted. [[file.md#L2]] [[lost.txt#L1]]")
            source = root / "file.md"
            source.write_text("Condition\nSupports [different]: System started.")
            before = investigate("pump", root)
            # The initially unrelated key enters the map when its cited passage is actually inspected.
            self.assertEqual({e["claim"] for e in before["evidence_map"]["explanations"]}, {"hardware", "different"})
            source.write_text("Condition\nChallenges [hardware]: It stayed offline.")
            after = investigate("pump", root)
            self.assertNotEqual(before["collection_digest"], after["collection_digest"])
            self.assertEqual(after["evidence_map"]["explanations"][0]["status"], "disputed")
            self.assertTrue(any(e["status"] == "unavailable" for e in after["evidence_map"]["citations"]))

    def test_limits_and_local_collection_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            collection = root / "collection"
            collection.mkdir()
            outside = root / "outside.txt"
            outside.write_text("private outside material")
            file = collection / "claim.md"
            file.write_text("Supports [pump]: Pump status. [[../outside.txt#L1]]")
            result = investigate("pump", collection)
            self.assertNotIn("private outside material", json.dumps(result))
            self.assertEqual(result["evidence_map"]["citations"], [])
            (collection / "alias.txt").symlink_to(outside)
            with self.assertRaises(Invalid):
                investigate("pump", collection)
            (collection / "alias.txt").unlink()
            for text in ("x" * 32769, "x" * 2001, "a\n" * 257):
                file.write_text(text)
                with self.assertRaises(Invalid):
                    investigate("pump", collection)
            for budget, rounds in ((25, 2), (-1, 2), (True, 1), (4, 3)):
                with self.assertRaises(Invalid):
                    investigate("pump", collection, budget, rounds)

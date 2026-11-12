import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from babalon.contracts import Invalid, MAX_JSON_BYTES
from babalon.handoff import EvidenceReader, handoff


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "handoff-summary.json"


class HandoffTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "summary.json"
        self.data = json.loads(EXAMPLE.read_text())
        self.data["other_workshop"] = "withheld workshop contents"
        self.data["inherited_advice"]["notes"] = "withheld internal note"
        self.path.write_text(json.dumps(self.data))

    def test_attributed_handoff(self):
        report = handoff(self.path, ["advice", "timing"], 2)
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(report["source"]["kind"], "operator_supplied_summary")
        self.assertFalse(report["event_replay_performed"])
        self.assertEqual(report["inspections_used"], 2)
        self.assertEqual(report["results"]["timing"]["facts"], self.data["measures"])
        advice = report["results"]["advice"]["facts"]
        self.assertEqual(advice["review_status"], "DISPUTED")
        self.assertTrue(advice["requires_new_observation"])
        self.assertTrue(advice["requires_review"])
        self.assertEqual(advice["open_objections"][0]["id"], "reply-a")
        self.assertNotIn("withheld", json.dumps(report))
        for result in report["results"].values():
            self.assertEqual(result["source_sha256"], report["source"]["sha256"])

    def test_restricted_brief_and_denial(self):
        reader = EvidenceReader(self.path, ["timing"], 1)
        self.assertEqual(reader.observe(), {"views": ["timing"], "remaining_inspections": 1})
        self.assertEqual(reader.inspect("advice"), {"status": "REFUSED", "reason": "outside_grant"})
        self.assertEqual(reader.inspect("other_workshop")["status"], "REFUSED")
        self.assertEqual(reader.inspect("timing")["status"], "REPORTED")
        report = handoff(self.path, ["timing"], 2)
        self.assertNotIn("reply-a", json.dumps(report))
        self.assertEqual(report["results"]["advice"]["reason"], "outside_grant")
        self.assertEqual(report["inspections_used"], 1)

    def test_budget_and_repeat_read(self):
        reader = EvidenceReader(self.path, ["timing", "advice"], 1)
        first = reader.inspect("advice")
        first["facts"]["status"] = "modified by caller"
        again = reader.inspect("advice")
        self.assertEqual(again["facts"]["status"], "ADVICE_ONLY")
        self.assertEqual(again["receipt_id"], first["receipt_id"])
        self.assertEqual(reader.inspect("timing")["reason"], "inspection_budget_exhausted")
        self.assertEqual(reader.observe()["remaining_inspections"], 0)
        self.assertEqual(handoff(self.path, [], 0)["inspections_used"], 0)

    def test_missing_evidence_stays_unknown_and_costs_one(self):
        self.data["inherited_advice"]["unaddressed_counterstories"] = ["absent"]
        self.data["measures"]["peer_completions"] = True
        self.path.write_text(json.dumps(self.data))
        report = handoff(self.path, ["timing", "advice"], 2)
        self.assertEqual(report["status"], "PARTIAL")
        self.assertEqual(report["inspections_used"], 2)
        for result in report["results"].values():
            self.assertEqual(result["status"], "UNAVAILABLE")
            self.assertNotIn("facts", result)

    def test_source_snapshot_is_stable(self):
        reader = EvidenceReader(self.path, ["timing"], 1)
        self.path.write_text("{}")
        result = reader.inspect("timing")
        self.assertEqual(result["facts"]["peer_completions"], 7)
        later = handoff(self.path, ["timing"], 1)
        self.assertNotEqual(result["source_sha256"], later["source"]["sha256"])
        self.assertEqual(later["results"]["timing"]["status"], "UNAVAILABLE")

    def test_source_and_grant_limits(self):
        for allowed, budget in [(["unknown"], 1), (["advice", "advice"], 2), (["timing"], True)]:
            with self.subTest(allowed=allowed, budget=budget), self.assertRaises(Invalid):
                EvidenceReader(self.path, allowed, budget)
        self.path.write_bytes(b" " * (MAX_JSON_BYTES + 1))
        with self.assertRaises(Invalid):
            EvidenceReader(self.path, [], 0)

    def test_cli_exit_status(self):
        for views, budget, code, status in [(["advice", "timing"], "2", 0, "COMPLETE"),
                                            (["timing", "advice"], "1", 3, "PARTIAL"),
                                            ([], "0", 3, "PARTIAL")]:
            with self.subTest(views=views, budget=budget):
                command = [sys.executable, "-m", "babalon", "handoff", str(self.path),
                           "--allow", *views, "--max-inspections", budget]
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertEqual(json.loads(result.stdout)["status"], status)

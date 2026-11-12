import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from babalon.recount import EVENT_HEAD, recount


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/commonwealth"
SUMMARY = FIXTURES / "demo-summary.json"
EVENTS = FIXTURES / "demo-events.json"


class RecountTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "input.json"

    def test_pinned_export_recounts_scoped_facts(self):
        r = recount(SUMMARY, EVENTS, ["timing", "advice"])
        self.assertEqual(r["status"], "AGREEMENT")
        self.assertEqual(r["journal"]["head"], EVENT_HEAD)
        self.assertEqual(r["journal"]["events"], 24)
        timing, advice = r["views"]["timing"], r["views"]["advice"]
        self.assertEqual(timing["event_sequences"], [1, 5, 13, 18, 23])
        self.assertEqual(timing["recounted"], {"peer_completions": 5, "peer_on_time_arrivals": 4,
                                                "peer_missed_deadlines": 1})
        self.assertEqual(advice["recounted"]["open_objections"][0]["id"], "counterstory-16")
        self.assertEqual(advice["summary_only_fields"], ["requires_new_observation", "status"])
        self.assertFalse(r["full_state_replay"])

    def test_protocol_reversal_visible_even_when_events_agree(self):
        data = json.loads(SUMMARY.read_bytes())
        data["inherited_advice"]["requires_new_observation"] = False
        self.path.write_text(json.dumps(data))
        result = recount(self.path, EVENTS, ["advice"])
        self.assertEqual(result["views"]["advice"]["status"], "AGREEMENT")
        self.assertEqual(result["protocol_check"]["status"], "DISAGREEMENT")
        self.assertEqual(result["status"], "DISAGREEMENT")

    def test_disagreement_preserves_both_accounts(self):
        data = json.loads(SUMMARY.read_bytes())
        data["measures"]["peer_missed_deadlines"] = 0
        data["inherited_advice"]["unaddressed_counterstories"] = []
        self.path.write_text(json.dumps(data))
        r = recount(self.path, EVENTS, ["timing", "advice"])
        self.assertEqual(r["status"], "DISAGREEMENT")
        self.assertEqual(r["views"]["timing"]["differences"], {
            "peer_missed_deadlines": {"reported": 0, "recounted": 1}})
        objection = r["views"]["advice"]["differences"]["open_objections"]
        self.assertEqual(objection["reported"], [])
        self.assertEqual(objection["recounted"][0]["id"], "counterstory-16")

    def test_scope_and_missing_evidence(self):
        r = recount(SUMMARY, EVENTS, ["timing"])
        self.assertEqual(list(r["views"]), ["timing"])
        self.assertNotIn("counterstory", json.dumps(r))
        self.assertEqual(recount(SUMMARY, self.path, [])["journal"]["status"], "NOT_INSPECTED")
        for path in (None, self.path):
            r = recount(SUMMARY, path, ["advice"])
            self.assertEqual(r["status"], "PARTIAL")
            self.assertEqual(r["journal"]["status"], "MISSING")
            self.assertNotIn("recounted", r["views"]["advice"])

    def test_receipt_prefix_modified_tail_and_broken_chain(self):
        events = json.loads(EVENTS.read_bytes())
        original_tail = events[-1]
        for body in ({"verified": True, "head": EVENT_HEAD}, events[:-1],
                     events[:-1] + [{**original_tail, "state_hash": "0" * 64}],
                     events[:-1] + [{**original_tail, "previous": "0" * 64}]):
            with self.subTest(length=len(body)):
                self.path.write_text(json.dumps(body))
                r = recount(SUMMARY, self.path, ["timing"])
                self.assertEqual(r["status"], "INVALID_EXPORT")
                self.assertNotIn("recounted", r["views"]["timing"])

    def test_missing_claims_keep_event_evidence(self):
        self.path.write_text("{}")
        r = recount(self.path, EVENTS, ["timing"])
        self.assertEqual(r["status"], "PARTIAL")
        self.assertEqual(r["views"]["timing"]["status"], "MISSING_CLAIMS")
        self.assertEqual(r["views"]["timing"]["recounted"]["peer_missed_deadlines"], 1)

    def test_cli_agreement_disagreement_and_missing(self):
        data = json.loads(SUMMARY.read_bytes())
        data["measures"]["peer_completions"] = 4
        self.path.write_text(json.dumps(data))
        for source, options, expected, code in (
            (SUMMARY, ["--events", str(EVENTS)], "AGREEMENT", 0),
            (self.path, ["--events", str(EVENTS)], "DISAGREEMENT", 2),
            (SUMMARY, [], "PARTIAL", 3),
        ):
            p = subprocess.run([sys.executable, "-m", "babalon", "recount", str(source),
                                "--allow", "timing", *options], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(p.returncode, code, p.stderr)
            self.assertEqual(json.loads(p.stdout)["status"], expected)

from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from babalon.last_credit.grade import grade
from babalon.recount import recount
from babalon.handoff import handoff
from scripts import attribution_trial as trial


class AttributionTests(unittest.TestCase):
    def test_external_selection_is_balanced_and_frozen(self):
        raw = (trial.DATA / "external-questions.json").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), trial.EXTERNAL_SHA)
        rows = json.loads(raw)
        self.assertEqual(len({r["uid"] for r in rows}), 32)
        self.assertEqual(Counter(r["source"] for r in rows), {"text": 16, "table": 16})

    def test_matching_numbers_alone_do_not_support_event_claim(self):
        case = next(c for c in trial.contrast_cases() if c["goal"] == "journal")
        final = {"action": "answer", "basis": "summary", "value": 2, "citation": "summary-contrast",
                 "objection": case["summary"]["open_objection"], "fresh_observation": "undetermined"}
        self.assertEqual(grade(case, final, None)["outcome"], "unsupported_answer")

    def test_operator_sees_two_outcomes(self):
        base = trial.ROOT / "tests/fixtures/commonwealth"
        data = json.loads((base / "demo-summary.json").read_bytes())
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "summary.json"
            for misses, fresh, event_status, rule_status in [
                (1, False, "AGREEMENT", "DISAGREEMENT"), (0, True, "DISAGREEMENT", "AGREEMENT"),
                (0, False, "DISAGREEMENT", "DISAGREEMENT")]:
                data["measures"]["peer_missed_deadlines"] = misses
                data["inherited_advice"]["requires_new_observation"] = fresh
                p.write_text(json.dumps(data))
                r = recount(p, base / "demo-events.json", ["timing","advice"])
                self.assertEqual((r["status"], r["event_status"], r["protocol_status"]),
                                 ("DISAGREEMENT", event_status, rule_status))
            self.assertEqual(recount(p, None, ["advice"])["protocol_status"], "UNCHECKED")
            self.assertEqual(recount(p, base / "demo-events.json", ["timing"])["protocol_status"], "NOT_REQUESTED")
            self.assertEqual(handoff(p, ["timing"], 1)["event_status"], "UNCHECKED")

    @unittest.skipUnless(importlib.util.find_spec("quickjs"), "requires last-credit extra")
    def test_shared_exposure_and_missing_tally(self):
        with tempfile.TemporaryDirectory() as temp:
            rows = trial.trials(trial.contrast_cases(), Path(temp))
        self.assertEqual(len(rows), 16)
        for i in range(0, len(rows), 2):
            first, second = rows[i:i+2]
            self.assertEqual(first["read_id"], second["read_id"])
            self.assertEqual(first["charged"], second["charged"])
            if first["purchase"] == 0:
                self.assertIsNone(first["read_id"])
            if second["purchase"] == 0 and second["goal"] == "journal":
                self.assertEqual(second["answer"]["action"], "abstain")

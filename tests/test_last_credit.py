from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from babalon.contracts import Invalid, digest
from babalon.evidence_session import EvidenceSession
from babalon.last_credit.cases import validate_cases
from babalon.last_credit.grade import grade
from babalon.last_credit.study import draw, run_arm, run_study


def case_for(goal):
    return next(c for c in draw("development-only")["cases"] if c["goal"] == goal and c["protocol_card"])


class LastCreditTests(unittest.TestCase):
    def test_distinct_pack_and_matching_twins(self):
        pack = draw("example")
        self.assertEqual(pack, draw("example"))
        self.assertNotEqual(pack, draw("another"))
        validate_cases(pack["cases"])
        self.assertEqual(len(pack["cases"]), 32)
        for case in pack["cases"]:
            twin, = [c for c in pack["cases"] if c is not case and c["pair"] == case["pair"]]
            for field in ("question", "summary", "protocol_card", "permitted", "current_batch"):
                self.assertEqual(twin[field], case[field])
        with self.assertRaisesRegex(Invalid, "committed"):
            run_study(pack, digest(draw("another")))

    def test_event_session_replay_and_revoke(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            packet = path / "private.json"
            packet.write_text(json.dumps(case_for("journal")["packet"]))
            db = path / "session.db"
            session = EvidenceSession.create_last_credit(db, packet, True)
            receipt = session.inspect("a", "timing")
            self.assertEqual(receipt["status"], "REPORTED")
            packet.unlink()
            reopened = EvidenceSession(db)
            self.assertEqual(reopened.observe()["remaining_inspections"], 0)
            self.assertEqual(reopened.inspect("a", "timing"), receipt)
            reopened.revoke()
            self.assertNotIn("evidence", reopened.inspect("a", "timing"))

    def test_guess_without_receipt_and_erased_objection(self):
        case = case_for("journal")
        final = {"action": "answer", "basis": "journal", "value": case["summary"]["reported_misses"],
                 "citation": "guessed", "objection": None, "fresh_observation": "required"}
        result = grade(case, final, None)
        self.assertEqual(result["outcome"], "unsupported_answer")
        self.assertFalse(result["obligation_preserved"])

    def test_unknown_rule_stays_open(self):
        case = case_for("protocol")
        case["protocol_card"] = None
        final = {"action": "abstain", "basis": "protocol", "value": None, "citation": None,
                 "objection": case["summary"]["open_objection"], "fresh_observation": "undetermined"}
        self.assertTrue(grade(case, final, None)["handoff_correct"])
        final["fresh_observation"] = "required"
        self.assertFalse(grade(case, final, None)["handoff_correct"])
        final["basis"] = "journal"
        self.assertEqual(grade(case, final, None)["outcome"], "unjustified_abstention")

    def test_operator_private_fields_omitted_and_only_receipt_returns(self):
        case = case_for("journal")
        messages = []

        def step(brief, arm, receipt):
            messages.append((deepcopy(brief), receipt))
            if receipt is None:
                return {"action": "inspect", "view": "timing"}
            return {"action": "answer", "basis": "journal", "citation": receipt["receipt_id"],
                    "value": receipt["evidence"]["facts"]["missed_deadlines"],
                    "objection": brief["summary"]["open_objection"], "fresh_observation": "required"}

        with tempfile.TemporaryDirectory() as tmp, patch("babalon.last_credit.study.propose", step):
            directory = Path(tmp)
            (directory / "packet.json").write_text(json.dumps(case["packet"]))
            result = run_arm(case, "learned", directory)
        self.assertEqual(set(messages[0][0]), {"summary", "question", "protocol_card", "current_batch", "can_inspect"})
        self.assertIsNone(messages[0][1])
        self.assertEqual(messages[1][1]["charged"], 1)
        self.assertTrue(result["handoff_correct"])

    def test_repeat_inspection_cannot_overspend_or_drop_a_case(self):
        case = case_for("journal")
        with tempfile.TemporaryDirectory() as tmp, patch("babalon.last_credit.study.propose",
                                                          return_value={"action": "inspect", "view": "timing"}):
            directory = Path(tmp)
            (directory / "packet.json").write_text(json.dumps(case["packet"]))
            row = run_arm(case, "always", directory)
        self.assertEqual(row["outcome"], "worker_failure")
        self.assertEqual((row["proposals"], row["credits_used"]), (2, 1))
        self.assertFalse(row["handoff_correct"])

    @unittest.skipUnless(importlib.util.find_spec("quickjs"), "requires last-credit extra")
    def test_guest_no_host_apis_and_bounded_execution(self):
        from babalon.last_credit.worker import guest_context
        import quickjs
        ctx = guest_context()
        self.assertTrue(ctx.eval("[typeof require,typeof process,typeof std,typeof os,typeof fetch,typeof loadScript].every(x=>x==='undefined')"))
        with self.assertRaises(quickjs.JSException):
            ctx.eval("while(true){}")

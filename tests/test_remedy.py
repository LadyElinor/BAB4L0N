import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from babalon.contracts import Invalid
from babalon.remedy import review


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "commonwealth"
CASE = FIXTURES / "owed-assistance.json"
REGISTER = FIXTURES / "receiving-register.json"


class RemedyReviewTests(unittest.TestCase):
    def setUp(self):
        self.case = json.loads(CASE.read_bytes())
        self.register = json.loads(REGISTER.read_bytes())

    def test_known_case_preserves_warning_and_separates_delivery_from_inquiry(self):
        self.assertEqual(hashlib.sha256(CASE.read_bytes()).hexdigest(),
                         "e3a7bb9cd968c581dd16a4817f64a47c0f1e1efabfdc335ead3c66420ec67c6c")
        report = review(self.case, self.register, 6)
        self.assertEqual(report["delivery"]["status"], "credited_in_fixture")
        self.assertEqual(report["delivery"]["net_credit_units"], 100)
        self.assertEqual(report["required_person_work_records"], [])
        self.assertEqual(report["participation"]["further-contact"], "declined")
        self.assertEqual(report["participation"]["repeat-testimony"], "unanswered")
        self.assertEqual(report["inquiry"]["status"], "open")
        self.assertEqual(report["inquiry"]["next_owner"], "review-office")
        self.assertEqual(report["inquiry"]["objection_record"], "original-account")
        self.assertEqual(report["inquiry"]["reported_open_findings"],
                         [{"record": "file-8-review", "case": "other-8", "reported": "correction-owed"}])
        self.assertNotIn(self.case["warning"]["account"], json.dumps(report))
        self.assertEqual((report["status"], report["personal_outcome"]["status"]), ("PARTIAL", "unknown"))
        self.assertFalse(report["authority_granted"])
        self.assertEqual(report["external_actions"], 0)

    def test_choices_never_change_delivery_warning_or_assignment(self):
        baseline = review(self.case, self.register, 6)
        for response in ("accepted", "declined", "unanswered"):
            with self.subTest(response=response):
                for key in baseline["participation"]:
                    self.case["participation"][key] = response
                report = review(self.case, self.register, 6)
                self.assertEqual(report["delivery"], baseline["delivery"])
                self.assertEqual(report["inquiry"], baseline["inquiry"])
                self.assertEqual(report["personal_outcome"]["status"], "unknown")
        self.case["work"].append(dict(self.case["work"][0], record="meeting-condition", units=0,
                                      bearer="affected-person", activity="Repeat the account in public."))
        report = review(self.case, self.register, 6)
        self.assertEqual(report["status"], "DISAGREEMENT")
        self.assertEqual(report["required_person_work_records"], ["meeting-condition"])
        self.assertEqual(report["burden_correction_owner"], self.case["institution"])
        self.assertEqual(report["delivery"], baseline["delivery"])

    def test_sender_report_and_acknowledged_warning_cannot_prove_delivery(self):
        for status in ("credited", "instruction-issued", "pending", "returned"):
            self.case["transfers"][0]["status"] = status
            report = review(self.case, None, 6)
            self.assertEqual(report["delivery"]["status"], "unverified")
            self.assertEqual(report["delivery"]["units_without_evidence"], 100)
            self.assertIsNone(report["delivery"]["net_credit_units"])
            self.assertEqual(report["inquiry"]["status"], "open")
        self.register["postings"] = []
        self.assertEqual(review(self.case, self.register, 6)["delivery"]["net_credit_units"], 0)

    def test_receiving_register_partial_return_and_replacement(self):
        rows = self.register["postings"]
        first = rows[0]
        first["units"] = 40
        result = review(self.case, self.register, 6)["delivery"]
        self.assertEqual((result["status"], result["units_without_evidence"]), ("partial", 60))
        rows.append(dict(first, record="p2", transfer="t2", units=60))
        self.assertEqual(review(self.case, self.register, 6)["delivery"]["status"], "credited_in_fixture")
        rows.append(dict(rows[1], at=6, record="r2", kind="return"))
        report = review(self.case, self.register, 6)
        self.assertEqual((report["delivery"]["status"], report["delivery"]["owner"]), ("partial", "payments-office"))
        rows.append(dict(first, at=6, record="r1", kind="return"))
        self.assertEqual(review(self.case, self.register, 6)["delivery"]["status"], "outstanding")
        rows.append(dict(first, at=6, record="p3", transfer="t3", units=100))
        self.assertEqual(review(self.case, self.register, 6)["delivery"]["status"], "credited_in_fixture")
        rows[-1]["units"] = 101
        overpaid = review(self.case, self.register, 6)
        self.assertEqual((overpaid["delivery"]["status"], overpaid["status"]), ("excess_needs_review", "DISAGREEMENT"))

    def test_wrong_scope_stale_record_or_self_certification_preserves_obligation(self):
        for key, value in (("case", "another"), ("award", "another"), ("recipient", "another"),
                           ("controller", "payments-office"), ("as_of", 5), ("as_of", True)):
            with self.subTest(key=key):
                report = review(self.case, dict(self.register, **{key: value}), 6)
                self.assertEqual((report["status"], report["delivery"]["status"]), ("DISAGREEMENT", "invalid_register"))
                self.assertEqual(report["delivery"]["units_without_evidence"], 100)
                self.assertEqual(report["inquiry"]["objection_record"], "original-account")

    def test_duplicate_unsupported_or_impossible_postings_cannot_settle_an_award(self):
        first = self.register["postings"][0]
        returned = dict(first, kind="return", record="r1", at=6)
        for rows in ([first, first], [first, dict(first, record="p2")], [returned], [first, returned, returned],
                     [first, dict(returned, units=1)], [first, dict(returned, at=4)], [dict(first, units=True)],
                     [dict(first, kind="instruction-issued")], [dict(first, at=7)], [first] * 33):
            with self.subTest(rows=rows[:2]):
                report = review(self.case, dict(self.register, postings=rows), 6)
                self.assertEqual(report["delivery"]["status"], "invalid_register")
                self.assertIsNone(report["delivery"]["net_credit_units"])

    def test_no_available_reviewer_keeps_institution_responsible(self):
        assignment = self.case["inquiry"]["assignment"]
        for controller in ("person-17", "eligibility-office", "payments-office", "assistance-service", None):
            self.case["inquiry"]["assignment"] = dict(assignment, controller=controller) if controller else None
            inquiry = review(self.case, self.register, 6)["inquiry"]
            self.assertIsNone(inquiry["reviewer"])
            self.assertEqual(inquiry["next_owner"], "assistance-service")
            self.assertEqual(inquiry["next_action"], "assign_separate_reviewer")

    def test_volunteered_account_can_challenge_credit_without_rescinding_refusal(self):
        account = json.loads((FIXTURES / "voluntary-remedy-account.json").read_bytes())
        baseline = review(self.case, self.register, 6)
        for outcome in ("could-not-use", "record-disputed", "usable-as-reported"):
            with self.subTest(outcome=outcome):
                report = review(self.case, self.register, 6, account=dict(account, outcome=outcome))
                self.assertEqual(report["delivery"], baseline["delivery"])
                self.assertEqual(report["inquiry"], baseline["inquiry"])
                self.assertEqual(report["participation"], baseline["participation"])
                self.assertEqual(report["personal_outcome"]["status"], outcome)
                if outcome == "usable-as-reported":
                    self.assertEqual(report["status"], "PARTIAL")
                else:
                    self.assertEqual(report["status"], "DISAGREEMENT")
                    self.assertEqual(report["personal_outcome"]["next_owner"], "payments-office")
                self.assertEqual(report["external_actions"], 0)
        for changes in ({"speaker": "someone-else"}, {"case": "case-18"}, {"at": 7}, {"outcome": "reconciled"}):
            report = review(self.case, self.register, 6, account=dict(account, **changes))
            self.assertEqual(report["status"], "DISAGREEMENT")
            self.assertEqual(report["delivery"], baseline["delivery"])
            self.assertEqual(report["personal_outcome"]["status"], "unknown")

    def test_invalid_cases_are_rejected(self):
        for mutate in (lambda c: c["award"].update(units=True), lambda c: c["participation"].update(publicity="silent"),
                       lambda c: c["work"][0].update(record="original-account"),
                       lambda c: c["inquiry"]["findings"][0].update(at=7)):
            with self.subTest(mutate=mutate):
                case = copy.deepcopy(self.case)
                mutate(case)
                with self.assertRaises(Invalid):
                    review(case, self.register, 6)

    def test_cli_retry_missing_and_invalid_register_keep_an_actionable_report(self):
        argv = [sys.executable, "-m", "babalon", "remedy-review", str(CASE), "--as-of", "6", "--register"]
        def run(path):
            p = subprocess.run(argv + [str(path)], cwd=ROOT, capture_output=True, text=True)
            return p.returncode, json.loads(p.stdout)
        code, report = run(REGISTER)
        self.assertEqual((code, report["delivery"]["net_credit_units"]), (3, 100))
        self.assertEqual(run(REGISTER), (code, report))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "register.json"
            code, missing = run(path)
            self.assertEqual((code, missing["delivery"]["status"]), (3, "unverified"))
            path.write_text("{")
            code, malformed = run(path)
            self.assertEqual(code, 2)
            self.assertEqual(malformed["delivery"]["units_without_evidence"], 100)
            self.assertEqual(malformed["inquiry"], missing["inquiry"])

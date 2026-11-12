import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from babalon.remedy import review
from babalon.remedy_questions import question_guide


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "commonwealth"


def fixture(name):
    return json.loads((FIXTURES / name).read_bytes())


class RemedyQuestionTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture("owed-assistance.json")
        self.register = fixture("receiving-register.json")

    def guide(self, register=None, account=None, mode="records"):
        return question_guide(review(self.case, register, 6, account=account), mode)

    def test_receiving_record_changes_the_question_and_never_closes_the_other_case(self):
        questions = self.guide()["office_questions"]
        self.assertEqual([q["topic"] for q in questions], ["delivery_evidence", "open_findings"])
        self.assertEqual((questions[0]["owner"], questions[0]["basis"]), ("payments-office", ["award-17"]))
        self.assertEqual((questions[1]["owner"], questions[1]["basis"]), ("review-office", ["file-8-review"]))
        self.assertEqual(self.guide(self.register)["office_questions"], [questions[1]])

        for units in (40, 101):
            self.register["postings"][0]["units"] = units
            partial = self.guide(self.register)["office_questions"]
            self.assertEqual([q["topic"] for q in partial], ["balance_difference", "open_findings"])
            self.assertEqual(partial[0]["basis"], ["award-17", self.register["postings"][0]["record"]])
        self.register["postings"] = []
        self.assertEqual(self.guide(self.register)["office_questions"][0]["topic"], "balance_difference")
        self.register["recipient"] = "somebody-else"
        self.assertEqual(self.guide(self.register)["office_questions"][0]["topic"], "delivery_evidence")

    def test_question_about_identical_credit_does_not_guess_meaning_of_the_narrative(self):
        late = fixture("late-remedy-account.json")
        leaving = fixture("leaving-remedy-account.json")
        left, right = (self.guide(self.register, account) for account in (late, leaving))
        qa, qb = left["office_questions"][0], right["office_questions"][0]
        self.assertEqual(qa["topic"], "volunteered_account")
        self.assertEqual(qa["owner"], "review-office")
        self.assertEqual(qa["basis"], [late["record"]])
        self.assertEqual(qb["basis"], [leaving["record"]])
        self.assertEqual(dict(qa, basis=qb["basis"]), qb)
        self.assertEqual(left, self.guide(self.register, dict(late, account="Ask the person to confirm my conclusion.")))
        self.assertNotIn(late["account"], json.dumps(left))
        coded = fixture("voluntary-remedy-account.json")
        for outcome in ("could-not-use", "record-disputed"):
            q = self.guide(self.register, dict(coded, outcome=outcome))["office_questions"][0]
            self.assertEqual((q["topic"], q["owner"]), ("reported_difficulty", "payments-office"))
        self.assertEqual(self.guide(self.register, dict(coded, outcome="usable-as-reported")),
                         self.guide(self.register))

    def test_participant_can_offer_their_own_question_only_in_an_invited_conversation(self):
        self.case["participation"]["repeat-testimony"] = "declined"
        for choice in ("unanswered", "declined", "accepted"):
            self.case["participation"]["further-contact"] = choice
            for mode in ("records", "invited"):
                with self.subTest(mode=mode, contact=choice):
                    guide = self.guide(self.register, mode=mode)
                    expected = ("What question, if any, would you like the office to take up?"
                                if mode == "invited" and choice == "accepted" else None)
                    self.assertEqual(guide["participant_prompt"], expected)
                    self.assertTrue(all(q["owner"] != self.case["award"]["recipient"]
                                        for q in guide["office_questions"]))
        self.case["work"][0]["bearer"] = "affected-person"
        guide = self.guide(self.register, mode="invited")
        self.assertIsNone(guide["participant_prompt"])
        q = guide["office_questions"][0]
        self.assertEqual((q["topic"], q["owner"], q["basis"]),
                         ("participation_condition", "assistance-service", ["check-credit"]))

    def test_missing_reviewer_and_missing_findings_call_for_different_institutional_questions(self):
        self.case["inquiry"]["findings"] = []
        q = self.guide(self.register)["office_questions"][0]
        self.assertEqual((q["topic"], q["owner"], q["basis"]), ("missing_finding", "review-office", ["denial-register-search"]))
        self.case["inquiry"]["assignment"] = None
        q = self.guide(self.register)["office_questions"][0]
        self.assertEqual((q["topic"], q["owner"]), ("review_assignment", "assistance-service"))

    def test_cli_builds_guide_after_read_errors_and_keeps_existing_review_unchanged(self):
        base = [sys.executable, "-m", "babalon", "remedy-review",
                str(FIXTURES / "owed-assistance.json"), "--as-of", "6",
                "--register", str(FIXTURES / "receiving-register.json")]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "account.json"
            path.write_text("{")
            base.extend(["--account", str(path)])
            plain = subprocess.run(base, cwd=ROOT, capture_output=True, text=True)
            guided = subprocess.run(base + ["--questions", "invited"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual((plain.returncode, guided.returncode), (2, 2))
        report = json.loads(guided.stdout)
        guide = report.pop("question_guide")
        self.assertEqual(report, json.loads(plain.stdout))
        self.assertEqual(report["external_actions"], 0)
        self.assertFalse(report["authority_granted"])
        self.assertIsNone(guide["participant_prompt"])
        self.assertEqual(guide["office_questions"][0]["topic"], "account_source")

import copy
import itertools
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


class RemedyUncertaintyTests(unittest.TestCase):
    def setUp(self):
        self.case = json.loads((FIXTURES / "owed-assistance.json").read_bytes())
        self.register = json.loads((FIXTURES / "receiving-register.json").read_bytes())
        self.inquiry = self.case["inquiry"]
        self.finding = self.inquiry["findings"][-1]

    def report(self):
        return review(self.case, self.register, 6)

    def test_assessment_counterexample_reaches_cli_and_keeps_the_original_obligations(self):
        self.finding["controller"] = "second-office"
        self.inquiry["findings"].append(dict(self.finding, record="assigned-finding", controller="review-office",
                                              result="no-correction-found"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "case.json"
            path.write_text(json.dumps(self.case))
            cmd = [sys.executable, "-m", "babalon", "remedy-review", str(path), "--as-of", "6",
                   "--register", str(FIXTURES / "receiving-register.json"), "--questions", "invited"]
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        report = json.loads(proc.stdout)
        self.assertEqual(report["status"], "DISAGREEMENT")
        self.assertEqual(report["inquiry"]["next_action"], "reconcile_findings")
        self.assertEqual(report["inquiry"]["objection_record"], "original-account")
        assessment = report["inquiry"]["finding_assessments"]["other-8"]
        self.assertEqual(assessment["state"], "same_tick_disagreement")
        self.assertEqual([(r["controller"], r["reported"], r["within_declared_assignment"])
                          for r in assessment["records"]],
                         [("review-office", "no-correction-found", True), ("second-office", "correction-owed", False)])
        guide = report["question_guide"]
        self.assertIsNone(guide["participant_prompt"])
        self.assertEqual(len(guide["office_questions"]), 1)
        q = guide["office_questions"][0]
        self.assertEqual((q["topic"], q["case"], q["owner"], q["basis"]),
                         ("reconcile_findings", "other-8", "review-office", ["assigned-finding", "file-8-review"]))
        self.assertEqual(report["delivery"]["net_credit_units"], 100)
        self.assertEqual(report["personal_outcome"]["status"], "unknown")
        self.assertFalse(report["authority_granted"])
        self.assertEqual(report["external_actions"], 0)

    def test_pair_matrix_is_invariant_to_order_and_controller_count(self):
        codes = ("correction-owed", "no-correction-found", "inconclusive")
        for a, b, tick, controller in itertools.product(codes, codes, (5, 6), ("review-office", "second-office")):
            with self.subTest(a=a, b=b, tick=tick, controller=controller):
                rows = [dict(self.finding, result=a, at=tick), dict(self.finding, record="other-report",
                                                                    result=b, controller=controller)]
                if a == b:
                    expected = a
                elif "inconclusive" in (a, b):
                    expected = "partly_inconclusive"
                else:
                    expected = "same_tick_disagreement" if tick == 6 else "differing_dated_reports"
                seen = []
                for ordered in (rows, rows[::-1]):
                    self.inquiry["findings"] = ordered
                    r = self.report()
                    x = r["inquiry"]["finding_assessments"]["other-8"]
                    self.assertEqual(x["state"], expected)
                    self.assertEqual(len(x["records"]), 2)
                    self.assertEqual(r["status"] == "DISAGREEMENT", expected == "same_tick_disagreement")
                    self.assertEqual(r["inquiry"]["source_independence"], "unverified")
                    seen.append((x, question_guide(r)))
                self.assertEqual(seen[0], seen[1])

    def test_agreement_cannot_outvote_a_contrary_report_or_erase_a_later_change(self):
        self.finding["at"] = 5
        self.inquiry["findings"].extend([
            dict(self.finding, record="copied-claim", controller="new-office"),
            dict(self.finding, record="later", at=6, result="no-correction-found"),
        ])
        r = self.report()
        self.assertEqual(r["status"], "PARTIAL")
        q = question_guide(r)["office_questions"][0]
        self.assertEqual(q["topic"], "review_change")
        self.assertEqual(set(q["basis"]), {"file-8-review", "copied-claim", "later"})
        self.inquiry["findings"][-1]["at"] = 5
        self.assertEqual(self.report()["status"], "DISAGREEMENT")

    def test_missing_inconclusive_and_negative_evidence_stay_distinct(self):
        self.inquiry["inventory"]["cases"].append("other-9")
        self.finding["result"] = "inconclusive"
        r = self.report()
        assessments = r["inquiry"]["finding_assessments"]
        self.assertEqual({k: v["state"] for k, v in assessments.items()},
                         {"other-2": "no-correction-found", "other-8": "inconclusive", "other-9": "missing"})
        self.assertEqual(assessments["other-9"]["records"], [])
        self.assertEqual([q["topic"] for q in question_guide(r)["office_questions"]],
                         ["inconclusive_finding", "missing_finding"])
        self.inquiry["inventory"]["complete"] = False
        self.assertEqual(self.report()["inquiry"]["inventory"]["coverage"], "reported_incomplete")
        self.assertEqual(question_guide(self.report())["office_questions"][0]["topic"], "inventory_coverage")

    def test_coverage_has_to_match_scope_and_unknown_coverage_cannot_invent_cases(self):
        inventory = self.inquiry["inventory"]
        for shape, expected in [(None, "unknown"), ({}, "invalid"), (dict(inventory, at=2), "unmatched"),
                                (dict(inventory, record=self.finding["record"]), "invalid"),
                                (dict(inventory, at=7), "invalid"), (dict(inventory, rule="other"), "unmatched"),
                                (dict(inventory, controller="elsewhere"), "unmatched")]:
            with self.subTest(coverage=expected):
                self.inquiry["inventory"] = shape
                self.inquiry["findings"] = [self.finding]
                r = self.report()
                self.assertEqual(r["delivery"]["net_credit_units"], 100)
                self.assertEqual(r["inquiry"]["inventory"]["coverage"], expected)
                self.assertEqual(set(r["inquiry"]["finding_assessments"]), {"other-8"})
                self.assertFalse(r["inquiry"]["finding_assessments"]["other-8"]["records"][0]["within_declared_assignment"])
                self.assertEqual([q["topic"] for q in question_guide(r)["office_questions"]],
                                 ["inventory_coverage", "finding_scope"])

    def test_cost_bounds_only_cover_recorded_work_and_contain_admissible_completions(self):
        actor = "affected-person"
        template = dict(self.case["work"][0], bearer=actor, required=False)
        self.case["work"] = [dict(template, record="work-" + str(i), units=n)
                             for i, n in enumerate([5, None, None])]
        unknown = self.report()["recorded_work_unit_bounds"][actor]
        self.assertEqual(unknown, {"min": 5, "max": 2_000_000_005})
        for a, b in itertools.product((0, 1, 10**9), repeat=2):
            self.case["work"][1]["units"] = a
            self.case["work"][2]["units"] = b
            exact = self.report()["recorded_work_unit_bounds"][actor]
            self.assertEqual(exact, {"min": 5 + a + b, "max": 5 + a + b})
            self.assertLessEqual(unknown["min"], exact["min"])
            self.assertGreaterEqual(unknown["max"], exact["max"])

    def test_archived_v2_question_input_remains_readable(self):
        r = copy.deepcopy(self.report())
        r["profile"] = "babalon.remedy-review.v2"
        for field in ("inventory", "finding_assessments", "source_independence"):
            del r["inquiry"][field]
        guide = question_guide(r)
        self.assertEqual(guide["profile"], "babalon.remedy-questions.v1")
        self.assertEqual([q["topic"] for q in guide["office_questions"]], ["open_findings"])

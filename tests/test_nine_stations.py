import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests/fixtures/commonwealth"


class NineStationsTest(unittest.TestCase):
    def run_review(self, *args):
        proc = subprocess.run([sys.executable, "-m", "babalon", "remedy-review",
                               str(FIX / "owed-assistance.json"), "--as-of", "6", *args],
                              cwd=ROOT, capture_output=True, text=True)
        return proc.returncode, json.loads(proc.stdout)

    def test_opt_in_preserves_findings_and_returns_to_an_owner(self):
        code, original = self.run_review()
        guided_code, guided = self.run_review("--nine-stations")
        view = guided.pop("nine_stations")
        self.assertEqual((guided_code, guided), (code, original))
        self.assertEqual([row["station"] for row in view["stations"]],
                         ["Tawbah", "Wara’", "Muhabba", "Tawakkul", "Zuhd", "Rida", "Faqr", "Sabr", "Ma’rifa"])
        questions = view["practice_of_return"]["office_questions"]
        self.assertIn(("payments-office", ["award-17"]), [(q["owner"], q["basis"]) for q in questions])
        self.assertFalse(view["authority_granted"])
        self.assertEqual(view["external_actions"], 0)

    def test_added_evidence_changes_the_return_without_inferring_consent(self):
        _, report = self.run_review("--nine-stations", "--register", str(FIX / "receiving-register.json"),
                                    "--account", str(FIX / "leaving-remedy-account.json"))
        view = report["nine_stations"]
        evidence = {s["station"]: s["recorded_context"] for s in view["stations"]}
        self.assertEqual(evidence["Zuhd"]["net_credit_units"], 100)
        self.assertEqual(evidence["Ma’rifa"]["personal_outcome"], "recorded_unclassified")
        self.assertEqual(evidence["Rida"]["further_contact"], "declined")
        self.assertNotIn(json.loads((FIX / "leaving-remedy-account.json").read_text())["account"],
                         json.dumps(view, ensure_ascii=False))
        topics = [q["topic"] for q in view["practice_of_return"]["office_questions"]]
        self.assertNotIn("delivery_evidence", topics)
        self.assertIn("open_findings", topics)

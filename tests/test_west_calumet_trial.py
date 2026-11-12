import json
import unittest

from babalon.contracts import digest
from scripts.west_calumet_trial import ROOT, replay
from hashlib import sha256


class WestCalumetTrialTests(unittest.TestCase):
    def test_replay_preserves_cutoff_and_actual_charges(self):
        report = replay()
        expected = json.loads((ROOT / "reports/west-calumet-notice-v1.json").read_text())
        self.assertEqual(report, expected)
        case = json.loads((ROOT / "examples/inquiry/west-calumet/case.json").read_text())
        for name, entry in report["passes"].items():
            docs = [d for d in case["sources"] if name == "expanded" or d["available"] <= case["cutoff"]]
            manifest = {d["file"]: sha256(("\n".join(d["lines"]) + "\n").encode()).hexdigest() for d in docs}
            self.assertEqual(digest(manifest), entry["collection_digest"])
            for arm in entry["arms"].values():
                self.assertEqual(len(arm["inspections"]), arm["credits"])
                self.assertLessEqual(arm["credits"], case["budget"])
                self.assertTrue(all(ref.split("#L")[0] in manifest for ref in arm["inspections"]))

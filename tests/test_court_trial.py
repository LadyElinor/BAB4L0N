import json
import unittest

from scripts.court_trial import FIXTURES, ROOT, replay


class CourtTrialTests(unittest.TestCase):
    def test_replay_matches_atlas_reference_including_missed_rows(self):
        expected = json.loads((ROOT / "reports/atlas-court-retrieval-v1.json").read_text())
        self.assertEqual(replay(), expected)
        self.assertEqual(expected["targets"], 12)
        self.assertEqual(expected["totals"], {"plain": 9, "keyword": 11, "guided": 9})

    def test_inspections_resolve_in_separate_source_and_annotation_inputs(self):
        cases = {c["id"]: c for c in json.loads((FIXTURES / "study.json").read_text())}
        for t in replay(traces=True)["trials"]:
            c = cases[t["case"]]
            docs = {k: (FIXTURES / c["id"] / k).read_text().splitlines() for k in c["records"]}
            for mode, report in t["reports"].items():
                allowed = dict(docs)
                if mode == "guided":
                    allowed["editor.md"] = [f"Assumes [{c['id']}]: {c['note']}"]
                self.assertEqual(set(report["documents"]), set(allowed))
                obs = [o for rnd in report["rounds"] for w in rnd["returns"] for o in w["observations"]]
                self.assertEqual(len(obs), 4)
                self.assertFalse(report["authority_granted"])
                self.assertEqual(report["external_actions"], 0)
                for o in obs:
                    name, line = o["source"].split("#L")
                    self.assertEqual(o["quotation"], allowed[name][int(line)-1])
            self.assertEqual(len(set(t["returns"]["keyword"])), len(t["returns"]["plain"]))

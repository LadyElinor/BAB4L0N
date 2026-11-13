import unittest

from scripts.ai_safety_case import build


class AISafetyCaseTests(unittest.TestCase):
    def test_atlas_export_preserves_source_bindings_and_equal_spend(self):
        case = build()
        self.assertEqual(case["plain"]["collection_digest"],
                         "f0456201a9aad25fd7ec71e4258398afcbe78312612fb9b2b8a5138b0a0fc41c")
        self.assertFalse(case["plain"]["authority_granted"])
        self.assertEqual(case["plain"]["external_actions"], 0)
        observed = [o for rnd in case["plain"]["rounds"] for ret in rnd["returns"]
                    for o in ret["observations"]]
        self.assertEqual(len(observed), 5)
        for obs in observed:
            name, line = obs["source"].split("#L")
            self.assertEqual(case["docs"][name].splitlines()[int(line) - 1], obs["quotation"])
            self.assertIn(case["links"][obs["source"]], [url for _, url in case["sources"]])
        scores = []
        for t in case["trials"]:
            targets = set(t["targets"])
            self.assertEqual(len(t["babalon"]), t["inspections_per_arm"])
            self.assertEqual(len(set(t["keyword"])), t["inspections_per_arm"])
            scores.append([len(targets.intersection(t[k])) for k in ("babalon", "keyword")])
        self.assertEqual(scores, [[2, 2], [0, 1], [2, 2], [2, 2]])

    def test_astra_preserves_editorial_boundary_and_missed_recommendation(self):
        case = build("astra-release-hold")
        report = case["plain"]
        self.assertEqual(report["collection_digest"],
                         "a6bcc9d69c96291fcc77aa34353e8491b1e70ae6e9c1b3b8222a301b207c9cae")
        self.assertEqual(set(report["documents"]), set(case["docs"]))
        self.assertFalse(report["authority_granted"])
        self.assertEqual(report["external_actions"], 0)
        self.assertEqual(report["audit"]["inspections"], 5)
        for finding in case["decision_record"]["findings"]:
            for ref in finding["sources"]:
                name, line = ref.rsplit("#L", 1)
                self.assertTrue(case["docs"][name].splitlines()[int(line) - 1])
                self.assertIn(ref, case["links"])
        scores = []
        for trial in case["trials"]:
            spend = trial["inspections_per_arm"]
            self.assertEqual(len(trial["babalon"]), spend)
            self.assertEqual(len(set(trial["keyword"])), spend)
            scores.append((spend, *(len(set(trial["targets"]) & set(trial[k]))
                                    for k in ("babalon", "keyword"))))
        self.assertEqual(scores, [(2, 1, 1), (2, 1, 1), (4, 1, 1), (4, 2, 2)])
        for method in ("babalon", "keyword"):
            self.assertNotIn("recommendation.txt#L1", case["trials"][1][method])

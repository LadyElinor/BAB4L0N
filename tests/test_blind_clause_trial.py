import copy
import tempfile
from pathlib import Path
import unittest

from scripts import blind_clause_trial as trial
from scripts import blind_inquiry as v1


class BlindClauseTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.case = Path(tmp.name)
        (self.case / "documents").mkdir()
        (self.case / "documents/a.txt").write_text("apples\npears\nlemons\noranges\n")
        (self.case / "rubric.md").write_text("Cite what is supplied.")
        (self.case / "provenance.md").write_text("Test fixture.")
        v1.write(self.case / "packet.json", {"budget": 4, "families": {"a.txt": "orchard"},
                 "questions": [{"id": "q1", "question": "How many apples and small oranges?"}]})
        v1.write(self.case / "groups.json", {"questions": [{"id": "q1", "case": "fruit",
                 "groups": [["a.txt#L1", "a.txt#L4"]]}]})
        self.freeze = trial.freeze(self.case)
        self.digest = v1.digest(self.freeze)

    def test_blinded_aliases_and_equivalent_card_expansion(self):
        sheet, key = trial.run(self.case, self.freeze, self.digest, bytes(32))
        trial.v3._check_returns(key["rows"], sheet, trial.ARMS)
        cards, _ = trial.cards(sheet)
        self.assertLess(len(cards), len(sheet["rows"]))
        self.assertEqual(len(sheet["rows"]), 8)
        self.assertFalse(any("method" in row or "pool_refs" in row for row in cards))
        payload = [{"card": row["card"], "decision": "abstain"} for row in cards]
        self.assertEqual(len(trial.expand(sheet, payload)), 8)
        with self.assertRaises(ValueError):
            trial.expand(sheet, payload + payload)
        with self.assertRaises(ValueError):
            trial.expand(sheet, [{**r, "arm": "A"} for r in payload])

    def test_changed_targets_block_run_and_scoring(self):
        sheet, _ = trial.run(self.case, self.freeze, self.digest, bytes(32))
        (self.case / "groups.json").write_text('{"questions":[]}')
        with self.assertRaises(ValueError):
            trial.run(self.case, self.freeze, self.digest, bytes(32))
        with self.assertRaises(ValueError):
            trial.groups_for_case(self.case, self.freeze, sheet)

    def test_wrong_depth_return_rejected(self):
        sheet, key = trial.run(self.case, self.freeze, self.digest, bytes(32))
        changed = copy.deepcopy(key["rows"])
        changed[0]["matched_spend"] += 1
        with self.assertRaises(ValueError):
            trial.v3._check_returns(changed, sheet, trial.ARMS)

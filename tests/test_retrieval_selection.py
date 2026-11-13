import json
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from babalon.contracts import Invalid, digest
from babalon.retrieval_selection import FAMILY, gate, rank, select
from scripts import retrieval_selection_trial as trial


class RetrievalSelectionTests(unittest.TestCase):
    def test_seeded_phrase_and_tie_controls(self):
        docs = {"a": "water gauge steel", "b": "steel water gauge", "c": "tax office"}
        self.assertEqual(rank("steel water", docs, FAMILY[0], 1), ["a"])
        self.assertEqual(rank("steel water", docs, FAMILY[1], 1), ["b"])
        self.assertEqual(select([0] * 12), FAMILY[0])
        self.assertEqual(select([0, 1, 1] + [0] * 9), FAMILY[1])

    def test_regression_veto_and_spend_checks(self):
        win = dict(target="x", candidate=["x"], active=["y"], bm25=["y"], keyword=["y"], spend=1)
        self.assertEqual(gate([win])["status"], "PROMOTED")
        self.assertEqual(gate([win, win, dict(win, target="y")])["status"], "NOT_PROMOTED")
        with self.assertRaises(Invalid):
            gate([dict(win, bm25=[])])

    def test_restart_reuses_proposal_and_evaluation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            hashes = {}
            for phase in ("propose", "evaluate"):
                paras = [{"context": f"Gauge number {i} supplied water.", "qas": []} for i in range(12)]
                paras[0]["qas"] = [{"id": phase, "question": "Which gauge supplied water?"}]
                raw = json.dumps({"data": [{"paragraphs": paras}]}).encode()
                (root / phase).write_bytes(raw)
                hashes[phase] = sha256(raw).hexdigest()
            db = root / "experiment.sqlite"
            with patch.dict(trial.SHA, hashes), patch.dict(trial.LIMIT, dict(propose=1, evaluate=1)):
                with self.assertRaises(Invalid):
                    trial.run(db, root / "evaluate", "evaluate")
                p = trial.run(db, root / "propose", "propose")
                e = trial.run(db, root / "evaluate", "evaluate")
                self.assertEqual(e["proposal_digest"], digest(p))
                with patch.object(trial, "calculate", side_effect=AssertionError("unexpected rerun")):
                    self.assertEqual(trial.run(db, root / "evaluate", "evaluate"),
                                     json.loads(json.dumps(e)))

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


class PresentationV2Tests(unittest.TestCase):
    @staticmethod
    def fixture(phase, count=12, target=0):
        paras = [{"context": f"Gauge {i} supplied water.", "qas": []} for i in range(count)]
        paras[target]["qas"] = [{"id": phase, "question": "Which gauge supplied water?"}]
        return json.dumps({"data": [{"paragraphs": paras}]}).encode()

    def test_exact_legacy_membership_and_separate_display_key(self):
        for count in (12, 13, 30, 200):
            for target in range(count):
                qid = f"fixture-{count}-{target}"
                order = sorted(range(count), key=lambda j: sha256(f"{qid}:{j}".encode()).digest())
                expected_set = {target, *[j for j in order if j != target][:11]}
                result = trial.selected_paragraphs(qid, count, target)
                self.assertEqual(set(result), expected_set)
                self.assertEqual(len(result), 12)
                expected_order = sorted(expected_set, key=lambda j: (
                    sha256(f"{trial.ORDER_DOMAIN}\0{qid}\0{j}".encode()).digest(), j))
                self.assertEqual(result, expected_order)

    def test_display_does_not_receive_gold_when_membership_is_fixed(self):
        expected = trial.selected_paragraphs('same-question', 12, 0)
        for target in range(12):
            self.assertEqual(trial.selected_paragraphs('same-question', 12, target), expected)
        # Explicit deterministic vector catches accidental domain/serialization changes.
        self.assertEqual(expected, [4, 1, 5, 9, 11, 2, 3, 8, 10, 0, 6, 7])

    def test_position_controls_ignore_content_and_match_spend(self):
        refs = {f'p{i:02}.txt#L1': 'secret content' for i in range(12)}
        for spend in range(5):
            last = trial.position_only(refs, spend)
            first = trial.position_only(refs, spend, last_first=False)
            self.assertEqual(len(last), spend)
            self.assertEqual(len(first), spend)
            self.assertEqual(last, [f'p{i:02}.txt#L1' for i in [11, *range(11)]][:spend])
            self.assertEqual(first, sorted(refs)[:spend])

    def test_populated_legacy_database_is_rejected_without_changes(self):
        import sqlite3
        from scripts import retrieval_selection_trial_v1 as legacy
        raw = self.fixture('propose')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root/'train.json'
            path.write_bytes(raw)
            db = root/'trial.sqlite'
            with patch.dict(legacy.SHA, propose=sha256(raw).hexdigest()), patch.dict(legacy.LIMIT, propose=1):
                legacy.run(db, path, 'propose')
            before = db.read_bytes()
            with patch.dict(trial.SHA, propose=sha256(raw).hexdigest()):
                with self.assertRaisesRegex(Invalid, 'legacy trial database'):
                    trial.run(db, path, 'propose')
            self.assertEqual(db.read_bytes(), before)
            with sqlite3.connect(db) as conn:
                self.assertFalse(conn.execute("SELECT 1 FROM sqlite_master WHERE name='receipts_v2'").fetchone())

    def test_legacy_runner_does_not_replay_v2_as_v1(self):
        from scripts import retrieval_selection_trial_v1 as legacy
        raw = self.fixture('propose')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            path=root/'train.json'
            path.write_bytes(raw)
            db=root/'trial.sqlite'
            with patch.dict(trial.SHA, propose=sha256(raw).hexdigest()), patch.dict(trial.LIMIT, propose=1):
                self.assertEqual(trial.run(db, path, 'propose')['version'], trial.VERSION)
            with patch.dict(legacy.SHA, propose=sha256(raw).hexdigest()), patch.object(legacy, 'calculate', side_effect=RuntimeError('fresh v1 calculation')):
                with self.assertRaisesRegex(RuntimeError, 'fresh v1 calculation'):
                    legacy.run(db, path, 'propose')

    def test_public_replay_cannot_promote_even_if_descriptive_gate_passes(self):
        raw=self.fixture('evaluate')
        proposal={'candidate': list(FAMILY[0]), 'question_ids': ['different-question']}
        with patch.dict(trial.LIMIT, evaluate=1), patch.object(trial, 'gate', return_value={'status':'PROMOTED','comparisons':{}}):
            result=trial.calculate(raw, 'evaluate', proposal)
        self.assertEqual(result['gate_status'], 'PROMOTED')
        self.assertEqual(result['status'], 'NOT_PROMOTED')
        self.assertFalse(result['promotion_eligible'])
        self.assertEqual(sum(result['gold_position_histogram']), 1)
        self.assertEqual(sum(result['drawn_gold_position_histogram']), 1)

    def test_paired_spend_diagnostic_rejects_changed_or_missing_questions(self):
        from scripts.retrieval_position_sensitivity import paired_spend
        rows=[{'id':'q', 'spend':3}]
        self.assertEqual(paired_spend(rows, rows)['changed_questions'], 0)
        for changed in ([{'id':'q', 'spend':4}], [{'id':'other', 'spend':3}], rows*2):
            with self.assertRaises(Invalid):
                paired_spend(rows, changed)

    def test_sensitivity_binds_targets_and_summaries_to_source(self):
        from copy import deepcopy
        from scripts import retrieval_position_sensitivity as sensitivity
        from scripts import retrieval_selection_trial_v1 as legacy
        train=self.fixture('propose')
        dev=self.fixture('evaluate')
        hashes={'propose':sha256(train).hexdigest(), 'evaluate':sha256(dev).hexdigest()}
        limits={'propose':1, 'evaluate':1}
        with patch.dict(trial.SHA, hashes), patch.dict(legacy.SHA, hashes), patch.dict(trial.LIMIT, limits), patch.dict(legacy.LIMIT, limits):
            old_p=json.loads(json.dumps(legacy.calculate(train, 'propose', None)))
            old_e=json.loads(json.dumps(legacy.calculate(dev, 'evaluate', old_p)))
            new_p=json.loads(json.dumps(trial.calculate(train, 'propose', None)))
            new_e=json.loads(json.dumps(trial.calculate(dev, 'evaluate', new_p)))
            result=sensitivity.summarize(train, dev, old_p, old_e, new_p, new_e)
            self.assertFalse(result['promotion_eligible'])
            bad=deepcopy(new_e)
            bad['rows'][0]['target']='p99.txt#L1'
            with self.assertRaisesRegex(Invalid, 'source gold position'):
                sensitivity.summarize(train, dev, old_p, old_e, new_p, bad)
            bad=deepcopy(new_e)
            bad['spend_per_arm']+=1
            with self.assertRaisesRegex(Invalid, 'spend total'):
                sensitivity.summarize(train, dev, old_p, old_e, new_p, bad)
            bad=deepcopy(new_e)
            bad['gold_position_histogram']=[0]*12
            with self.assertRaisesRegex(Invalid, 'gold histogram'):
                sensitivity.summarize(train, dev, old_p, old_e, new_p, bad)

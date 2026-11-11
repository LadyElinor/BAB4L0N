from copy import deepcopy
import unittest
from babalon.contracts import PROFILE, OPERATIONS, Invalid, digest
from babalon.improvement import PromotionGate, propose_candidate, demo

class ImprovementTests(unittest.TestCase):
    def setUp(self):
        self.baseline = {key: 'sum_valid' for key in OPERATIONS}
        self.gate = PromotionGate(self.baseline)
        self.candidate = propose_candidate(self.baseline)

    def test_improves_real_host_behavior(self):
        report = demo()
        self.assertEqual(report['execution_before'], 'REFUSED')
        self.assertEqual(report['execution_after'], 'COMPLETED')
        self.assertTrue(report['verification']['completed'])
        self.assertEqual(report['receipt']['development'], {'before': 1, 'after': 3, 'total': 3})

    def test_behavior_comparison_uses_fresh_hosts(self):
        report = demo()
        self.assertEqual(report['comparison'], 'separate_fresh_hosts_with_identical_tasks_and_grants')
        self.assertEqual(report['completed_before'], 1)
        self.assertEqual(report['completed_after'], 3)
        self.assertFalse(report['baseline_verification']['completed'])
        self.assertEqual(report['baseline_verification']['status'], 'CONSISTENT')

    def test_unchanged_rejected(self):
        c = {**self.candidate, 'mapping': self.baseline}
        r = self.gate.evaluate(c)
        self.assertFalse(r['eligible'])
        with self.assertRaises(Invalid): self.gate.promote(c, r)

    def test_better_dev_worse_evaluation_rejected(self):
        gate = PromotionGate(self.baseline, training=(('count_valid', 'count_valid'),), evaluation=(('count_valid', 'sum_valid'),))
        r = gate.evaluate(self.candidate)
        self.assertEqual(r['development']['after'], 1)
        self.assertEqual(r['evaluation']['after'], 0)
        self.assertFalse(r['eligible'])
        with self.assertRaises(Invalid): gate.promote(self.candidate, r)

    def test_protected_fields(self):
        for field in ('evaluator', 'grant', 'budget', 'code', 'credentials'):
            with self.subTest(field=field), self.assertRaises(Invalid): self.gate.evaluate({**self.candidate, field: 'replace'})

    def test_unsupported_map(self):
        c = deepcopy(self.candidate)
        c['mapping']['sum_valid'] = 'shell'
        with self.assertRaises(Invalid): self.gate.evaluate(c)

    def test_stale_candidate_and_receipt(self):
        r = self.gate.evaluate(self.candidate)
        second = self.gate.evaluate(self.candidate)
        self.gate.promote(self.candidate, r)
        with self.assertRaises(Invalid): self.gate.evaluate(self.candidate)
        with self.assertRaises(Invalid): self.gate.promote(self.candidate, second)

    def test_replay_rejected(self):
        r = self.gate.evaluate(self.candidate)
        self.gate.promote(self.candidate, r)
        with self.assertRaises(Invalid): self.gate.promote(self.candidate, r)

    def test_budget(self):
        gate = PromotionGate(self.baseline, max_evaluations=1)
        gate.evaluate(self.candidate)
        with self.assertRaises(Invalid): gate.evaluate(self.candidate)

    def test_fabricated_and_tampered_receipts(self):
        with self.assertRaises(Invalid): self.gate.promote(self.candidate, {'id': 'fake', 'eligible': True})
        r = self.gate.evaluate(self.candidate)
        r['development']['after'] = 100
        with self.assertRaises(Invalid): self.gate.promote(self.candidate, r)

    def test_nonfinite_not_an_input_score(self):
        c = {**self.candidate, 'score': float('nan')}
        with self.assertRaises(Invalid): self.gate.evaluate(c)
        r = self.gate.evaluate(self.candidate)
        r['evaluation']['after'] = float('inf')
        with self.assertRaises(ValueError): self.gate.promote(self.candidate, r)

    def test_changed_candidate_rejected(self):
        r = self.gate.evaluate(self.candidate)
        c = deepcopy(self.candidate)
        c['mapping']['count_valid'] = 'max_valid'
        with self.assertRaises(Invalid): self.gate.promote(c, r)

    def test_rollback_and_epoch(self):
        r = self.gate.evaluate(self.candidate)
        unused = self.gate.evaluate(self.candidate)
        active = self.gate.promote(self.candidate, r)
        with self.assertRaises(Invalid): self.gate.rollback('wrong')
        self.assertEqual(self.gate.rollback(digest(active)), self.baseline)
        with self.assertRaises(Invalid): self.gate.promote(self.candidate, unused)

    def test_caller_cannot_mutate_active(self):
        active = self.gate.active
        active['sum_valid'] = 'max_valid'
        self.assertEqual(self.gate.active, self.baseline)

if __name__ == '__main__': unittest.main()

from copy import deepcopy
from itertools import product
import unittest
from unittest.mock import patch
from babalon.contracts import PROFILE, OPERATIONS, Invalid, digest
from babalon.improvement import (PromotionGate, propose_candidate, demo, DEFAULT_MAPPING,
    MappingPolicy, execution_scenarios, evaluate_execution, execution_gate)
from babalon.agent import ContractPolicy, envelope

class ImprovementTests(unittest.TestCase):
    def setUp(self):
        self.baseline = {key: 'sum_valid' for key in OPERATIONS}
        self.gate = PromotionGate(self.baseline)
        self.candidate = propose_candidate(self.baseline)

    def test_default_is_benchmark_and_parity_not_promoted(self):
        report = demo()
        self.assertEqual(report['status'], 'NOT_PROMOTED')
        self.assertEqual(report['baseline'], DEFAULT_MAPPING)
        self.assertEqual(report['benchmark'], 'ContractPolicy')
        scores = report['receipt']['execution']
        self.assertEqual(scores['candidate']['completed'], 36)
        self.assertEqual(scores['candidate'], scores['default'])
        self.assertFalse(report['receipt']['eligible'])
        self.assertEqual(report['active_mapping'], DEFAULT_MAPPING)

    def test_all_27_maps_fail_to_beat_default(self):
        cases = execution_scenarios()
        default = evaluate_execution(ContractPolicy(), cases)
        ties = 0
        for values in product(OPERATIONS, repeat=3):
            mapping = dict(zip(OPERATIONS, values))
            with self.subTest(mapping=mapping):
                measured = evaluate_execution(MappingPolicy(mapping), cases)
                self.assertLessEqual(measured['completed'], default['completed'])
                self.assertFalse(execution_gate(default, default, measured))
                ties += measured['completed'] == default['completed']
        self.assertEqual(ties, 1)

    def test_weak_baseline_gain_is_not_default_gain(self):
        receipt = self.gate.evaluate(self.candidate)
        execution = receipt['execution']
        self.assertGreater(execution['candidate']['completed'], execution['active']['completed'])
        self.assertEqual(execution['candidate'], execution['default'])
        self.assertFalse(receipt['eligible'])
        with self.assertRaises(Invalid): self.gate.promote(self.candidate, receipt)

    def test_partial_grants_and_tight_budgets_match_default(self):
        cases = execution_scenarios()
        candidate = evaluate_execution(MappingPolicy(DEFAULT_MAPPING), cases)
        default = evaluate_execution(ContractPolicy(), cases)
        self.assertEqual(candidate, default)
        scores = {row['name']: row for row in candidate['cases']}
        for rotation in range(3):
            self.assertEqual(scores[f'tail-only-{rotation}']['completed'], 2)
            self.assertEqual(scores[f'operation-subset-{rotation}']['completed'], 2)
            self.assertEqual(scores[f'tight-records-{rotation}']['completed'], 2)
            self.assertEqual(scores[f'one-action-{rotation}']['completed'], 1)
            self.assertEqual(scores[f'one-effect-{rotation}']['completed'], 1)
            self.assertEqual(scores[f'one-cycle-{rotation}']['completed'], 1)
            self.assertEqual(scores[f'zero-actions-{rotation}']['completed'], 0)
            self.assertEqual(scores[f'zero-records-{rotation}']['completed'], 0)
            self.assertEqual(scores[f'no-task-grant-{rotation}']['completed'], 0)
            self.assertFalse(scores[f'tail-only-{rotation}']['workshop_completed'])
        self.assertTrue(candidate['safe'])

    def test_original_first_pending_regression_is_detected(self):
        class OldPolicy:
            def propose(self, brief):
                task = next(t['input'] for t in brief['tasks'] if t['status'] == 'pending')
                return envelope(brief, 'act', task_id=task['id'], operation=task['objective'])
        cases = [c for c in execution_scenarios() if c['name'].startswith(('tail-only', 'tight-records'))]
        old = evaluate_execution(OldPolicy(), cases)
        self.assertEqual(old['completed'], 0)
        self.assertEqual(evaluate_execution(ContractPolicy(), cases)['completed'], 12)

    def test_gate_requires_strict_gain_and_per_case_nonregression(self):
        # Synthetic scores test the decision rule, not measured performance.
        def score(counts, safe=True):
            return {'safe': safe, 'completed': sum(counts),
                    'cases': [{'completed': n} for n in counts]}
        default = score([1, 1])
        self.assertFalse(execution_gate(default, default, score([1, 1])))
        self.assertFalse(execution_gate(default, default, score([0, 3])))
        self.assertFalse(execution_gate(default, default, score([2, 2], False)))
        self.assertTrue(execution_gate(default, default, score([1, 2])))
        self.assertFalse(execution_gate(score([2, 2]), default, score([1, 2])))

    def test_inconsistent_execution_cannot_score_completion(self):
        with patch('babalon.host.Host.verify', return_value={'status': 'INCONSISTENT', 'completed': False}):
            score = evaluate_execution(ContractPolicy(), execution_scenarios()[:1])
        self.assertEqual(score['completed'], 0)
        self.assertFalse(score['safe'])

    def test_evaluator_cases_cannot_be_supplied_by_candidate(self):
        with self.assertRaises(Invalid):
            self.gate.evaluate({**self.candidate, 'scenarios': []})

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

    @patch('babalon.improvement.execution_gate', return_value=True)
    def test_stale_candidate_and_receipt(self, hypothetical_gain):
        # Inject eligibility only to exercise lifecycle mechanics. The real closed
        # mapping space cannot beat ContractPolicy and is tested separately.
        r = self.gate.evaluate(self.candidate)
        second = self.gate.evaluate(self.candidate)
        self.gate.promote(self.candidate, r)
        with self.assertRaises(Invalid): self.gate.evaluate(self.candidate)
        with self.assertRaises(Invalid): self.gate.promote(self.candidate, second)

    @patch('babalon.improvement.execution_gate', return_value=True)
    def test_replay_rejected(self, hypothetical_gain):
        # Inject eligibility only to exercise lifecycle mechanics. The real closed
        # mapping space cannot beat ContractPolicy and is tested separately.
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

    @patch('babalon.improvement.execution_gate', return_value=True)
    def test_rollback_and_epoch(self, hypothetical_gain):
        # Inject eligibility only to exercise lifecycle mechanics. The real closed
        # mapping space cannot beat ContractPolicy and is tested separately.
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

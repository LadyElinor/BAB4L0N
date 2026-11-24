import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import blind_inquiry as v1
from scripts import blind_inquiry_v2 as v2
from scripts import blind_inquiry_v3 as v3
from scripts import blind_inquiry_v3_freeze as freeze_rules


class ReviewTallyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.documents = self.root / 'documents'
        self.documents.mkdir()
        (self.documents / 'minutes.txt').write_text(
            'Council minutes recorded the vote.\nThe clerk counted the council vote.\n')
        self.packet = {'budget': 2, 'families': {'minutes.txt': 'town'}, 'questions': [
            {'id': 'q1', 'question': 'Who recorded the council vote?'},
            {'id': 'q2', 'question': 'Unobtainium?'}]}
        self.rubric = self.root / 'rubric'
        self.rubric.write_text('Credit an attributed account. Abstain where the record is silent.')
        self.targets = self.root / 'targets'
        v1.write(self.targets, {'questions': [
            {'id': 'q1', 'targets': ['minutes.txt#L1', 'minutes.txt#L2']},
            {'id': 'q2', 'targets': []}]})
        self.key_path = self.root / 'key'

    def prepare(self, readers='baseline', targets=True, legacy=False):
        rubric_hash = v1.digest_bytes(self.rubric.read_bytes())
        if legacy:
            self.frozen = v1.freeze(self.packet, self.documents, rubric_hash)
            trial = v1.trial
        else:
            target_hash = v1.digest_bytes(self.targets.read_bytes()) if targets else None
            self.frozen = v3.freeze(self.packet, self.documents, rubric_hash, readers=readers,
                                    targets_sha256=target_hash)
            trial = v3.trial
        self.freeze_hash = v1.digest(self.frozen)
        self.sheet, self.key = trial(self.packet, self.documents, self.frozen, self.freeze_hash, bytes(32))
        self.key_path.unlink(missing_ok=True)
        v1.write(self.key_path, self.key)
        self.prepare_reviews()

    def prepare_reviews(self):
        self.answers = {'interpreter': 'reader', 'worksheet_digest': v1.digest(self.sheet), 'rows': []}
        self.reviews = []
        for row in reversed(self.sheet['rows']):
            refs = [p['ref'] for p in row['passages']]
            self.answers['rows'].append({
                'id': row['id'], 'arm': row['arm'], 'decision': 'answer' if refs else 'abstain',
                'interpretation': 'The clerk counted the vote.' if refs else 'The record is silent.',
                'cites': refs, 'uncertainty': 'The full account is unavailable.',
                'unanswered': 'Which other records survive?'})
        self.answer_hash = v1.seal_answers(self.sheet, self.answers)
        for reviewer in ('alice', 'bob'):
            rows = []
            for row in self.sheet['rows']:
                refs = [p['ref'] for p in row['passages']]
                assessment = dict.fromkeys(v1.DIMENSIONS, 'not_applicable')
                if refs:
                    assessment.update(equivalent_evidence='yes', source_attribution='yes', unsupported_claim='no')
                    if reviewer == 'alice':
                        assessment['source_attribution'] = 'uncertain'
                    if reviewer == 'bob' and row['arm'] == 'B':
                        assessment.update(equivalent_evidence='uncertain', source_attribution='uncertain',
                                          unsupported_claim='yes')
                else:
                    assessment['warranted_abstention'] = 'yes' if reviewer == 'alice' else 'no'
                rows.append({'id': row['id'], 'arm': row['arm'], 'assessment': assessment, 'cites': refs,
                             'rationale': 'Judgment on this return.', 'unanswered': 'Which other records survive?'})
            self.reviews.append({'reviewer': reviewer, 'worksheet_digest': v1.digest(self.sheet),
                                 'answer_digest': self.answer_hash, 'rows': rows})

    def collect(self, targets_path=None, key_path=None, reviews=None, seal=v3.seal_review):
        records = self.reviews if reviews is None else reviews
        deposits = [(r['reviewer'], seal(self.sheet, self.answers, self.answer_hash, r)) for r in records]
        register = v2.close_register(self.sheet, v1.digest(self.key), self.answer_hash, deposits)
        return v3.collect(self.sheet, key_path or self.key_path, self.answers, self.rubric,
                          self.frozen, self.freeze_hash, register, v1.digest(register), records, targets_path)

    def test_review_counts_beside_exact_hits_keep_disagreements_and_units(self):
        for readers, methods in [('baseline', set(v1.ARMS)), ('coverage', {*v1.ARMS, 'clause-bm25'})]:
            with self.subTest(readers=readers):
                self.prepare(readers)
                report = self.collect(self.targets)
                tally = report['tally']
                self.assertEqual(set(tally), {f'{m}/{who}' for m in methods for who in ('alice', 'bob')})
                disputed = next(r for r in report['rows'] if r['id'] == 'q1' and r['arm'] == 'B')
                self.assertIn('unsupported_claim', disputed['disagreements'])
                for method in methods:
                    for name in ('alice', 'bob'):
                        counts = tally[f'{method}/{name}']
                        unsupported = name == 'bob' and method == disputed['method']
                        self.assertEqual((counts['designated_passage_hits'], counts['designated_passage_targets']),
                                         (2, 2))
                        self.assertEqual((counts['rows'], counts['answers'], counts['abstentions']), (2, 1, 1))
                        self.assertEqual(counts['matched_spend'], 2)
                        self.assertEqual(counts['credited_passage_hits'], int(not unsupported))
                        self.assertEqual(counts['supported_answers'], int(not unsupported))
                        self.assertEqual(counts['unsupported_claims'], int(unsupported))
                        self.assertEqual(counts['warranted_abstentions'], int(name == 'alice'))
                        self.assertEqual(counts['unwarranted_abstentions'], int(name == 'bob'))
                        self.assertEqual(counts['uncertain'], int(name == 'alice' or unsupported))

    def test_reviewed_evidence_can_be_credited_without_a_supported_answer(self):
        self.prepare(targets=False)
        for row in self.answers['rows']:
            if (row['id'], row['arm']) == ('q1', 'A'):
                row['decision'] = 'abstain'
        self.answer_hash = v1.seal_answers(self.sheet, self.answers)
        for review in self.reviews:
            review['answer_digest'] = self.answer_hash
            for row in review['rows']:
                if row['id'] == 'q1' and row['arm'] == 'A':
                    row['assessment']['warranted_abstention'] = 'uncertain'
                if row['id'] == 'q1' and row['arm'] == 'C':
                    row['assessment']['unsupported_claim'] = 'uncertain'
        result = self.collect()
        for alias in ('A', 'C'):
            record = next(r for r in result['rows'] if (r['id'], r['arm']) == ('q1', alias))
            for reviewer in ('alice', 'bob'):
                counts = result['tally'][f"{record['method']}/{reviewer}"]
                self.assertEqual(counts['credited_passage_hits'], 1)
                self.assertEqual(counts['supported_answers'], 0)
                self.assertEqual(counts['unsupported_claims'], 0)
                self.assertEqual(counts['uncertain'], 1)

    def test_positive_decision_conflicts_rejected_at_seal_and_before_key_access(self):
        self.prepare(targets=False)
        for qid, incompatible in [('q1', 'warranted_abstention'), ('q2', 'unsupported_claim')]:
            with self.subTest(qid=qid):
                reviews = copy.deepcopy(self.reviews)
                row = next(r for r in reviews[0]['rows'] if r['id'] == qid)
                row['assessment'][incompatible] = 'yes'
                with self.assertRaises(ValueError):
                    v3.seal_review(self.sheet, self.answers, self.answer_hash, reviews[0])
                # The old seal authenticates bytes but does not enforce the new rule.
                with self.assertRaises(ValueError):
                    self.collect(reviews=reviews, seal=v2.seal_review, key_path=self.root / 'unopened-key')

    def test_uncommitted_exact_counts_remain_unknown_and_cannot_be_added_later(self):
        self.prepare(targets=False)
        report = self.collect()
        for counts in report['tally'].values():
            self.assertIsNone(counts['designated_passage_hits'])
            self.assertIsNone(counts['designated_passage_targets'])
        with self.assertRaises(ValueError):
            self.collect(self.targets)

    def test_committed_targets_are_required_and_byte_bound(self):
        self.prepare()
        with self.assertRaises(ValueError):
            self.collect()
        self.targets.write_bytes(self.targets.read_bytes() + b'\n')
        with self.assertRaises(ValueError):
            self.collect(self.targets)

    def test_cli_freeze_to_collection_displays_separate_reviewer_rows(self):
        def cli(*args, version=3):
            program = v1.ROOT / f'scripts/blind_inquiry_v{version}.py'
            return subprocess.run([sys.executable, program, *args], cwd=self.root, capture_output=True,
                                  text=True, check=True).stdout.strip()

        v1.write(self.root / 'packet', self.packet)
        self.freeze_hash = cli('freeze', 'packet', 'documents', v1.digest_bytes(self.rubric.read_bytes()),
                               'freeze', '--readers', 'baseline', '--targets-sha256',
                               v1.digest_bytes(self.targets.read_bytes()))
        self.frozen = v2.read(self.root / 'freeze')
        cli('run', 'packet', 'documents', 'freeze', self.freeze_hash, 'trial')
        sheet = 'trial/worksheet.json'
        self.key_path = self.root / 'trial/custodian-only.json'
        self.sheet, self.key = v2.read(self.root / sheet), v2.read(self.key_path)
        self.prepare_reviews()
        v1.write(self.root / 'answers', self.answers)
        deposits = []
        for review in self.reviews:
            name = review['reviewer']
            v1.write(self.root / name, review)
            deposits.extend(['--review', name, cli('seal-review', sheet, 'answers', self.answer_hash, name)])
        register_hash = cli('close-register', sheet, v1.digest(self.key), self.answer_hash,
                            'register', *deposits, version=2)
        output = cli('collect', sheet, self.key_path, 'answers', 'rubric', 'freeze', self.freeze_hash,
                     'register', register_hash, 'result', 'alice', 'bob', '--targets', 'targets', '--table')
        report = json.loads((self.root / 'result').read_bytes())
        self.assertEqual(report['tally'], self.collect(self.targets)['tally'])
        self.assertEqual(output.count('2/2'), len(v1.ARMS) * 2)
        for key in report['tally']:
            self.assertIn(key, output)

    def test_report_code_and_documentation_are_bound_to_the_prospective_freeze(self):
        self.prepare()
        for name in ('scripts/blind_inquiry_v3.py', 'docs/BLIND_INQUIRY_V3.md'):
            with self.subTest(name=name):
                source = (v1.ROOT / name).read_bytes()
                hashes = self.frozen['implementation'].copy()
                self.assertEqual(hashes[name], v1.digest_bytes(source))
                hashes[name] = v1.digest_bytes(source + b'\n')
                with patch.object(freeze_rules, '_implementation', return_value=hashes):
                    with self.assertRaisesRegex(ValueError, 'implementation changed'):
                        self.collect(self.targets, key_path=self.root / 'unopened-key')

    def test_new_collector_requires_a_prospective_v3_freeze(self):
        self.prepare(legacy=True)
        with self.assertRaises(ValueError):
            self.collect(seal=v2.seal_review)


if __name__ == '__main__':
    unittest.main()

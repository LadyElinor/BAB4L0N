import tempfile
import unittest
from pathlib import Path

from scripts import blind_inquiry as base
from scripts import blind_inquiry_coverage as study
from scripts import blind_inquiry_v2 as custody


class CoverageStudyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.docs = self.root / 'docs'
        self.docs.mkdir()
        (self.docs / 'record.txt').write_text(
            'Orchard crop harvest plan.\nOrchard crop plan.\nWestern ridge stream flow.\n'
            'A clerk signed an order.\n', encoding='utf-8')
        self.packet = {'questions': [{'id': 'q1', 'question': 'orchard crop plan and ridge stream'},
                                     {'id': 'q2', 'question': 'molybdenum topaz'}],
                       'families': {'record.txt': 'archive'}, 'budget': 4}
        self.rubric = self.root / 'rubric'
        self.rubric.write_bytes(b'Practice only.')
        self.frozen = study.freeze(self.packet, self.docs, base.digest_bytes(self.rubric.read_bytes()))

    def test_four_aliases_controls_and_matched_spend_including_zero(self):
        key_bytes = bytes(range(32))
        frozen = self.frozen['control_freeze']
        _, original = base.trial(self.packet, self.docs, frozen, base.digest(frozen), key_bytes)
        sheet, key = study.trial(self.packet, self.docs, self.frozen, base.digest(self.frozen), key_bytes)
        records = {(r['id'], r['method']): r for r in key['rows']}
        for original_row in original['rows']:
            record = records[original_row['id'], original_row['method']]
            for field in ('natural_refs', 'matched_refs', 'matched_spend'):
                self.assertEqual(original_row[field], record[field])
        for qid in ('q1', 'q2'):
            self.assertEqual({r['arm'] for r in sheet['rows'] if r['id'] == qid}, set('ABCD'))
            charges = {records[qid, arm]['matched_spend'] for arm in study.ARMS}
            self.assertEqual(len(charges), 1)
            if qid == 'q2':
                self.assertEqual(charges, {0})
        for row in sheet['rows']:
            self.assertNotIn('method', row)
        (self.docs / 'record.txt').write_text('Changed record.')
        with self.assertRaisesRegex(ValueError, 'freeze'):
            study.trial(self.packet, self.docs, self.frozen, base.digest(self.frozen), key_bytes)

    def test_alternation_retains_top_and_falls_back_for_single_clause(self):
        rows = {'a': 'red apples red apples green grass', 'b': 'red apples sweet',
                'c': 'green grass wet', 'd': 'and'}
        query = 'red apples and green grass'
        ranked = study.clause_rank(query, rows, 4)
        self.assertEqual(ranked, ['a', 'c', 'b', 'd'])
        for cap in range(5):
            self.assertEqual(study.clause_rank(query, rows, cap), ranked[:cap])
        for query in ('red apples', 'red and apples', 'red apples and green grass and other fruit'):
            self.assertEqual(study.clause_rank(query, rows, 2), study.rank(query, rows, study.BM25, 2))

    def test_v2_collection_accepts_all_four_blind_rows(self):
        freeze_hash = base.digest(self.frozen)
        sheet, key = study.trial(self.packet, self.docs, self.frozen, freeze_hash, bytes(32))
        sheet_hash = base.digest(sheet)
        ids = [{'id': r['id'], 'arm': r['arm']} for r in sheet['rows']]
        answers = {'interpreter': 'reader', 'worksheet_digest': sheet_hash, 'rows': [
            {**i, 'decision': 'abstain', 'interpretation': 'Insufficient evidence.', 'cites': [],
             'uncertainty': 'Practice.', 'unanswered': 'Which records are missing?'} for i in ids]}
        answer_hash = base.seal_answers(sheet, answers)
        reviews = [{'reviewer': judge, 'worksheet_digest': sheet_hash, 'answer_digest': answer_hash, 'rows': [
            {**i, 'assessment': dict.fromkeys(base.DIMENSIONS, 'uncertain'), 'cites': [],
             'rationale': 'Practice.', 'unanswered': 'Which records are missing?'} for i in ids]}
            for judge in ('first', 'second')]
        deposits = [(r['reviewer'], custody.seal_review(sheet, answers, answer_hash, r)) for r in reviews]
        register = custody.close_register(sheet, base.digest(key), answer_hash, deposits)
        key_path = self.root / 'key'
        base.write(key_path, key)
        report = custody.collect(sheet, key_path, answers, self.rubric, self.frozen, freeze_hash,
                                 register, base.digest(register), reviews)
        self.assertEqual(len(report['rows']), 8)
        self.assertEqual(report['status'], 'NOT_PROMOTED')
        self.assertFalse(report['promotion_eligible'])

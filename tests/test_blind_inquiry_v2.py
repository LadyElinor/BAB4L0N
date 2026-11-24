import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts import blind_inquiry as v1
from scripts import blind_inquiry_v2 as v2


class CollectionCommitmentTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        documents = self.root / 'documents'
        documents.mkdir()
        (documents / 'minutes.txt').write_text('The clerk recorded a proposed vote.')
        self.rubric = self.root / 'rubric.txt'
        self.rubric.write_text('Accept a proposed vote. Leave the outcome open.')
        packet = {'budget': 1, 'families': {'minutes.txt': 'council'},
                  'questions': [{'id': 'q1', 'question': 'Who recorded a proposed vote?'}]}
        self.frozen = v1.freeze(packet, documents, v1.digest_bytes(self.rubric.read_bytes()))
        self.freeze_hash = v1.digest(self.frozen)
        self.sheet, self.key = v1.trial(packet, documents, self.frozen, self.freeze_hash, bytes(32))
        self.key_path = self.root / 'key.json'
        v1.write(self.key_path, self.key)
        self.answers, self.reviews = self.submission('The final outcome is open.')
        self.answer_hash = v1.seal_answers(self.sheet, self.answers)
        self.deposits = [(r['reviewer'], v2.seal_review(self.sheet, self.answers, self.answer_hash, r))
                         for r in self.reviews]
        self.register = v2.close_register(self.sheet, v1.digest(self.key), self.answer_hash, self.deposits)
        self.retained = v1.digest(self.register)

    def submission(self, interpretation):
        worksheet_hash = v1.digest(self.sheet)
        answers = {'interpreter': 'reader', 'worksheet_digest': worksheet_hash, 'rows': [
            {'id': r['id'], 'arm': r['arm'], 'decision': 'abstain', 'cites': [],
             'interpretation': interpretation, 'uncertainty': 'Minutes incomplete.',
             'unanswered': 'Was there a final vote?'} for r in self.sheet['rows']]}
        reviews = []
        for name, judgment in [('alice', 'yes'), ('bob', 'no'), ('carol', 'uncertain')]:
            assessment = dict.fromkeys(v1.DIMENSIONS, 'uncertain')
            assessment['warranted_abstention'] = judgment
            reviews.append({'reviewer': name, 'worksheet_digest': worksheet_hash,
                            'answer_digest': v1.seal_answers(self.sheet, answers), 'rows': [
                {'id': r['id'], 'arm': r['arm'], 'assessment': assessment.copy(), 'cites': [],
                 'rationale': 'The source describes a proposal.', 'unanswered': 'Who voted?'}
                for r in self.sheet['rows']]})
        return answers, reviews

    def collect(self, **changes):
        args = dict(sheet=self.sheet, key_path=self.key_path, answers=self.answers,
                    rubric_path=self.rubric, frozen=self.frozen, published_hash=self.freeze_hash,
                    register=self.register, register_hash=self.retained, reviews=self.reviews)
        return v2.collect(**{**args, **changes})

    def test_valid_disagreement_and_order_independent_roster(self):
        report = self.collect(reviews=self.reviews[::-1])
        self.assertEqual(report['collection_profile'], v2.PROFILE)
        self.assertEqual(report['commitment_integrity'], 'matched_retained_register')
        self.assertEqual(report['reviewer_independence'], 'not_verified')
        self.assertEqual(report['register_digest'], self.retained)
        self.assertEqual(report['review_digests'], dict(self.deposits))
        self.assertEqual(report['answers'], self.answers)
        self.assertEqual(report['answer_digest'], self.answer_hash)
        self.assertFalse(report['promotion_eligible'])
        self.assertEqual(report['status'], 'NOT_PROMOTED')
        for row in report['rows']:
            self.assertEqual(row['disagreements'], ['warranted_abstention'])
            self.assertEqual({r['reviewer']: r['assessment']['warranted_abstention'] for r in row['reviews']},
                             {'alice': 'yes', 'bob': 'no', 'carol': 'uncertain'})

    def test_coordinated_replacement_rejected_before_key_access(self):
        other_answers, other_reviews = self.submission('Only the proposal is documented.')
        with self.assertRaisesRegex(ValueError, 'retained answer commitment'):
            self.collect(answers=other_answers, reviews=other_reviews, key_path=self.root / 'unreleased')

    def test_register_itself_needs_an_external_anchor(self):
        different = copy.deepcopy(self.register)
        del different['review_digests']['carol']
        with self.assertRaisesRegex(ValueError, 'independently retained'):
            self.collect(register=different, reviews=self.reviews[:2])
        for missing_hash in (None, '', 'x' * 64):
            with self.subTest(value=missing_hash), self.assertRaisesRegex(ValueError, 'SHA-256'):
                self.collect(register_hash=missing_hash)

    def test_missing_and_duplicate_deposits(self):
        for deposits in ([], self.deposits[:1], [self.deposits[0], self.deposits[0]],
                         [('alice', ''), self.deposits[1]]):
            with self.subTest(deposits=deposits), self.assertRaises(ValueError):
                v2.close_register(self.sheet, v1.digest(self.key), self.answer_hash, deposits)
        for field in ('answer_digest', 'review_digests'):
            incomplete = self.register.copy()
            del incomplete[field]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'missing fields'):
                self.collect(register=incomplete, register_hash=v1.digest(incomplete))
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            v2.close_register(self.sheet, v1.digest(self.key), '', self.deposits)

    def test_each_named_reviewer_must_appear_exactly_once(self):
        extra = {**self.reviews[0], 'reviewer': 'dana'}
        for submitted in (self.reviews[:2], self.reviews + [extra], [*self.reviews[:2], extra],
                          [*self.reviews[:2], self.reviews[0]]):
            with self.subTest(names=[r['reviewer'] for r in submitted]), self.assertRaises(ValueError):
                self.collect(reviews=submitted, key_path=self.root / 'unreleased')

    def test_individual_deposits_cover_every_judgment_and_its_support(self):
        for index in range(len(self.reviews)):
            for field, new in (('assessment', dict.fromkeys(v1.DIMENSIONS, 'no')),
                               ('rationale', 'Other reasons.'), ('cites', ['minutes.txt#L1']),
                               ('unanswered', 'When was the motion filed?')):
                changed = copy.deepcopy(self.reviews)
                changed[index]['rows'][0][field] = new
                with self.subTest(index=index, field=field), self.assertRaisesRegex(ValueError, 'retained commitment'):
                    self.collect(reviews=changed, key_path=self.root / 'unreleased')

    def test_sealing_requires_the_retained_answers_and_matching_review_links(self):
        with self.assertRaisesRegex(ValueError, 'retained answer commitment'):
            v2.seal_review(self.sheet, self.answers, '0' * 64, self.reviews[0])
        for field in ('worksheet_digest', 'answer_digest'):
            review = {**self.reviews[0], field: '0' * 64}
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'different worksheet or answer'):
                v2.seal_review(self.sheet, self.answers, self.answer_hash, review)
        with self.assertRaisesRegex(ValueError, 'interpreter'):
            v2.seal_review(self.sheet, self.answers, self.answer_hash, {**self.reviews[0], 'reviewer': 'reader'})

    def test_original_rubric_key_and_substantive_checks_still_apply(self):
        wrong_key = self.root / 'other-key.json'
        v1.write(wrong_key, {**self.key, 'rows': []})
        with self.assertRaisesRegex(ValueError, 'private key'):
            self.collect(key_path=wrong_key)
        with self.assertRaisesRegex(ValueError, 'commitment'):
            self.collect(published_hash='0' * 64)
        other_rubric = self.root / 'other-rubric.txt'
        other_rubric.write_text('Different criteria.')
        with self.assertRaisesRegex(ValueError, 'rubric'):
            self.collect(rubric_path=other_rubric)
        records = copy.deepcopy(self.reviews)
        records[0]['rows'].pop()
        deposits = [(r['reviewer'], v2.seal_review(self.sheet, self.answers, self.answer_hash, r))
                    for r in records]
        register = v2.close_register(self.sheet, v1.digest(self.key), self.answer_hash, deposits)
        with self.assertRaisesRegex(ValueError, 'exactly once'):
            self.collect(reviews=records, register=register, register_hash=v1.digest(register))

    def test_cli_from_blinded_deposits_to_unblinded_report(self):
        script = v2.ROOT / 'scripts/blind_inquiry_v2.py'

        def cli(*args, check=True):
            return subprocess.run([sys.executable, str(script), *args], cwd=self.root, text=True,
                                  capture_output=True, check=check)

        v1.write(self.root / 'sheet', self.sheet)
        v1.write(self.root / 'answers', self.answers)
        v1.write(self.root / 'freeze', self.frozen)
        deposit_args = []
        files = []
        for review in self.reviews:
            filename = review['reviewer'] + '.json'
            files.append(filename)
            v1.write(self.root / filename, review)
            result = cli('seal-review', 'sheet', 'answers', self.answer_hash, filename)
            deposit_args.extend(['--review', review['reviewer'], result.stdout.strip()])
        closed = cli('close-register', 'sheet', v1.digest(self.key), self.answer_hash, 'register', *deposit_args)
        self.assertEqual(closed.stdout.strip(), self.retained)
        for method in v1.ARMS:
            self.assertNotIn(method, (self.root / 'register').read_text())
        args = ('collect', 'sheet', 'key.json', 'answers', 'rubric.txt', 'freeze', self.freeze_hash, 'register')
        failed = cli(*args, '0' * 64, 'result', *files, check=False)
        self.assertNotEqual(failed.returncode, 0)
        self.assertFalse((self.root / 'result').exists())
        cli(*args, self.retained, 'result', *files)
        self.assertEqual(json.loads((self.root / 'result').read_bytes()), self.collect())

    def test_ambiguous_json_reviewer_names_refused(self):
        path = self.root / 'ambiguous.json'
        path.write_text('{"review_digests":{"alice":"first","alice":"second"}}')
        with self.assertRaisesRegex(ValueError, 'duplicate name'):
            v2.read(path)

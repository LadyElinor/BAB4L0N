import json
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from babalon.inquiry import _index
from scripts.blind_inquiry_targets import load_targets


class TargetManifestTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'targets.json'
        self.sheet = {'rows': [
            {'id': qid, 'arm': arm, 'passages': []}
            for qid in ('first', 'unresolved') for arm in ('A', 'B', 'C')]}
        self.corpus_refs = frozenset(['a.txt#L1', 'a.txt#L3'])
        self.items = [{'id': 'first', 'targets': ['a.txt#L3']},
                      {'id': 'unresolved', 'targets': []}]

    def read(self, manifest):
        body = json.dumps(manifest).encode()
        self.path.write_bytes(body)
        return load_targets(self.path, sha256(body).hexdigest(), self.sheet, self.corpus_refs)

    def test_unreturned_target_and_empty_target_set(self):
        self.assertEqual(self.read({'questions': self.items}), {
            'first': frozenset(['a.txt#L3']), 'unresolved': frozenset()})

    def test_real_ofqual_manifest_counts_only_designated_references(self):
        pilot = Path(__file__).resolve().parents[1] / 'research' / 'ofqual-pilot'
        retained = json.loads((pilot / 'deposits.json').read_bytes())
        sheet = json.loads((pilot / 'worksheet.json').read_bytes())
        corpus, _ = _index(pilot / 'documents')
        result = load_targets(pilot / 'targets.json', retained['targets_file_sha256'], sheet, frozenset(corpus))
        self.assertEqual(result['q1'], {'f.txt#L1', 'c.txt#L1'})
        self.assertFalse(result['q6'])
        self.assertEqual(sum(map(len, result.values())), 10)

    def test_compare_digest_before_parse_and_parse_only_the_bytes_checked(self):
        self.path.write_bytes(b'invalid json')
        with patch('scripts.blind_inquiry_targets.json.loads', side_effect=AssertionError):
            with self.assertRaisesRegex(ValueError, 'frozen digest'):
                load_targets(self.path, '0' * 64, self.sheet, self.corpus_refs)
        data = json.dumps({'questions': self.items}).encode()
        with patch.object(Path, 'read_bytes', side_effect=[data]) as read:
            load_targets(self.path, sha256(data).hexdigest(), self.sheet, self.corpus_refs)
            read.assert_called_once_with()

    def test_reject_duplicate_fields_without_dropping_them(self):
        content = b'{"questions":[],"questions":[]}'
        self.path.write_bytes(content)
        with self.assertRaisesRegex(ValueError, 'duplicate name'):
            load_targets(self.path, sha256(content).hexdigest(), self.sheet, self.corpus_refs)

    def test_reject_incomplete_extra_or_duplicate_questions(self):
        for items in (self.items[:1], [*self.items, self.items[0]],
                      [*self.items, {'id': 'extra', 'targets': []}]):
            with self.subTest(items=items), self.assertRaises(ValueError):
                self.read({'questions': items})

    def test_reject_duplicate_non_string_and_out_of_corpus_references(self):
        for targets in (['a.txt#L1', 'a.txt#L1'], [1], [{}], ['a.txt#L2'], ['other.txt#L1'], 'a.txt#L1'):
            with self.subTest(targets=targets), self.assertRaises(ValueError):
                self.read({'questions': [{'id': 'first', 'targets': targets}, self.items[1]]})

    def test_reject_malformed_metadata(self):
        for equivalents in ([], {'a.txt#L1': []}, {'a.txt#L3': ['a.txt#L4']}):
            with self.subTest(equivalents=equivalents), self.assertRaises(ValueError):
                self.read({'questions': [{**self.items[0], 'equivalents': equivalents}, self.items[1]]})

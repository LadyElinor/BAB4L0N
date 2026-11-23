import copy
import json
from pathlib import Path
import tempfile
import unittest
from scripts import blind_inquiry as b


class BlindInquiryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.docs = self.root / 'documents'
        self.docs.mkdir()
        (self.docs / 'record.txt').write_text('The worker reported a council vote.\nA vote was proposed.\n')
        self.rubric = self.root / 'rubric'
        self.rubric.write_text('Only reported action is supported; do not infer the outcome.')
        self.packet = {'budget':4,'families':{'record.txt':'one-origin'},'questions':[
            {'id':'q1','question':'Who reported the vote?'}, {'id':'q2','question':'Unobtainium?'}]}
        self.frozen = b.freeze(self.packet, self.docs, b.digest_bytes(self.rubric.read_bytes()))
        self.h = b.digest(self.frozen)

    def run_trial(self):
        return b.trial(self.packet, self.docs, self.frozen, self.h, bytes(32))

    def test_committed_inputs_and_absent_evidence(self):
        sheet, key = self.run_trial()
        self.assertNotIn('shared-gap', json.dumps(sheet))
        self.assertEqual({r['matched_spend'] for r in key['rows'] if r['id']=='q2'}, {0})
        for q in ['q1','q2']:
            rows = [r for r in key['rows'] if r['id']==q]
            self.assertEqual(len(set(r['matched_spend'] for r in rows)),1)
            self.assertTrue(all(r['matched_spend']==len(r['matched_refs']) for r in rows))
        self.packet['budget']=3
        with self.assertRaisesRegex(ValueError,'changed'):
            self.run_trial()
        self.packet['budget']=4
        (self.docs/'record.txt').write_text('Revised after commitment.')
        with self.assertRaisesRegex(ValueError,'changed'):
            self.run_trial()

    def test_different_native_spend_is_not_filled_by_padding(self):
        from unittest.mock import patch
        original = b.run_one
        calls = []
        def limited(question, directory, rows, allowance):
            calls.append(allowance)
            result = original(question, directory, rows, allowance)
            if question == self.packet['questions'][0]['question']:
                result['keyword'] = result['keyword'][:1]
            return result
        with patch.object(b, 'run_one', side_effect=limited):
            _, key = self.run_trial()
        records = [r for r in key['rows'] if r['id'] == 'q1']
        self.assertIn(1, calls)
        self.assertGreater(max(len(r['natural_refs']) for r in records), 1)
        self.assertEqual({r['matched_spend'] for r in records}, {1})

    def test_dissent_survives_unblinding_and_key_edits_are_refused(self):
        sheet,key=self.run_trial()
        answers={'interpreter':'reader','worksheet_digest':b.digest(sheet),'rows':[
            dict(id=r['id'],arm=r['arm'],decision='abstain',interpretation='No outcome verified.',
                 cites=[],uncertainty='Incomplete coverage.',unanswered='Where is the receipt?') for r in sheet['rows']]}
        def review(name):
            return {'reviewer':name,'worksheet_digest':b.digest(sheet),'answer_digest':b.seal_answers(sheet,answers),
                    'rows':[dict(id=r['id'],arm=r['arm'],assessment=dict.fromkeys(b.DIMENSIONS,'uncertain'),
                                 cites=[],rationale='Evidence incomplete.',unanswered='What would establish receipt?')
                            for r in sheet['rows']]}
        a,c=review('one'),review('two')
        c['rows'][0]['assessment']['warranted_abstention']='yes'
        def collect(k=key):
            return b.collect(sheet,k,b.digest(key),answers,self.rubric,self.frozen,self.h,[a,c])
        result=collect()
        self.assertEqual(result['rows'][0]['disagreements'],['warranted_abstention'])
        self.assertFalse(result['promotion_eligible'])
        altered=copy.deepcopy(key);altered['rows'][0]['method']='different'
        with self.assertRaisesRegex(ValueError,'key'):
            collect(altered)
        c['reviewer']='one'
        with self.assertRaisesRegex(ValueError,'reviewer'):
            collect()
        c['reviewer']='two'
        self.rubric.write_text('Post-hoc criteria')
        with self.assertRaisesRegex(ValueError,'rubric'):
            collect()

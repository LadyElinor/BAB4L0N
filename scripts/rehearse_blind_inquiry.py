"""Development-only regression: use two published Relay Atlas JSON packets."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import blind_inquiry as b

PINS = {'gpt4o-sycophancy': '7920810bd1d407b65a07f8c66303258bac73a9d98951db4ebedbcc584f5f547c',
        'astra-release-hold': '9258cc4ea26cc5b002ef0e5da8a1b41389d0065180803283e61ad03462c4313b'}


def replay(directory):
    result = {'scope':'exposed_development_only', 'promotion_eligible':False,
              'metric':'designated passage hits, not human answer quality', 'per_question_cap':4,'cases':{}}
    for case_id, pin in PINS.items():
        raw = (directory / (case_id + '.json')).read_bytes()
        if b.digest_bytes(raw) != pin:
            raise ValueError('changed Atlas export')
        case = json.loads(raw)
        with TemporaryDirectory() as tmp:
            doc = Path(tmp)
            for name, contents in case['docs'].items():
                (doc/name).write_bytes(contents.encode())
            # Group by the origin of the relevant accounts, not by downstream outlet.
            packet = {'questions':[{'id':f'q{i}', 'question':q} for i,q in enumerate(case['tasks'],1)],
                      'families':{n:'advice-study' if n=='advice-study.txt' else 'openai' for n in case['docs']},
                      'budget':4}
            frozen = b.freeze(packet, doc, b.digest_bytes(b'Exposed designated targets; no human grading.'))
            _, key = b.trial(packet, doc, frozen, b.digest(frozen), bytes(32))
        questions=[]
        for i, task in enumerate(case['trials'],1):
            gold = set(task['targets'])
            rows = [r for r in key['rows'] if r['id']==f'q{i}']
            questions.append({'question':task['question'],'targets':sorted(gold),'arms':{
                r['method']:{'natural_spend':len(r['natural_refs']), 'matched_spend':r['matched_spend'],
                             'hits':len(gold.intersection(r['matched_refs'])), 'matched_refs':r['matched_refs']}
                for r in rows}})
        result['cases'][case_id]={'packet_sha256':pin,'questions':questions}
    return result


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: rehearse_blind_inquiry.py DIRECTORY_WITH_BOTH_ATLAS_EXPORTS')
    print(json.dumps(replay(Path(sys.argv[1])), ensure_ascii=False, sort_keys=True, indent=2))

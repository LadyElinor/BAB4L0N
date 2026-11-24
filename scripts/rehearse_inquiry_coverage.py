"""Report four-arm retrieval outcomes on the two previously exposed Atlas exports."""
import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import blind_inquiry_coverage as study
from scripts import blind_inquiry as base
from scripts.rehearse_blind_inquiry import PINS


def replay(directory):
    cases = {}
    totals = {arm: {'hits': 0, 'matched_spend': 0, 'natural_spend': 0} for arm in study.ARMS}
    comparisons = {arm: {'wins': 0, 'losses': 0, 'ties': 0} for arm in base.ARMS}
    targets = 0
    for case_id, expected in PINS.items():
        raw = (directory / (case_id + '.json')).read_bytes()
        if base.digest_bytes(raw) != expected:
            raise ValueError('changed Atlas export')
        case = json.loads(raw)
        with TemporaryDirectory() as tmp:
            docs = Path(tmp)
            for name, contents in case['docs'].items():
                (docs / name).write_bytes(contents.encode())
            packet = {'budget': 4, 'questions': [{'id': f'q{i}', 'question': q}
                                                 for i, q in enumerate(case['tasks'], 1)],
                      'families': {n: 'advice-study' if n == 'advice-study.txt' else 'openai'
                                   for n in case['docs']}}
            frozen = study.freeze(packet, docs, base.digest_bytes(b'Exposed designated targets; no human grading.'))
            _, key = study.trial(packet, docs, frozen, base.digest(frozen), bytes(32))
        questions = []
        for i, task in enumerate(case['trials'], 1):
            gold = set(task['targets'])
            targets += len(gold)
            arms = {}
            for row in key['rows']:
                if row['id'] != f'q{i}':
                    continue
                stats = {field: row[field] for field in ('natural_refs', 'matched_refs', 'natural_spend', 'matched_spend')}
                stats['hits'] = len(gold.intersection(row['matched_refs']))
                arms[row['method']] = stats
                for metric in totals[row['method']]:
                    totals[row['method']][metric] += stats[metric]
            for comparator, paired in comparisons.items():
                difference = arms[study.CANDIDATE]['hits'] - arms[comparator]['hits']
                outcome = 'wins' if difference > 0 else 'losses' if difference < 0 else 'ties'
                paired[outcome] += 1
            questions.append({'question': task['question'], 'targets': sorted(gold), 'arms': arms})
        cases[case_id] = {'packet_sha256': expected, 'freeze_digest': base.digest(frozen), 'questions': questions}
    return {'scope': 'exposed_development_only', 'status': 'NOT_PROMOTED', 'promotion_eligible': False,
            'metric': 'designated passage hits', 'per_question_cap': 4, 'targets': targets,
            'totals': totals, 'candidate_vs_control_by_question': comparisons, 'cases': cases}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    print(json.dumps(replay(parser.parse_args().directory), ensure_ascii=False, sort_keys=True, indent=2))

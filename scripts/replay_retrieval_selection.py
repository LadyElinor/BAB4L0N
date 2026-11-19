"""Replay v1/v2 in separate processes and verify all committed receipt fields."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from babalon.contracts import digest


def compare_result(actual, expected):
    actual, expected = deepcopy(actual), deepcopy(expected)
    rows = actual.pop('rows')
    if digest(rows) != expected.pop('rows_digest'):
        raise RuntimeError('evaluation row digest differs')
    for arm, comparison in expected['comparisons'].items():
        losses = [row['id'] for row in rows if row['target'] in row[arm] and row['target'] not in row['candidate']]
        if comparison.pop('loss_ids') != losses:
            raise RuntimeError('paired loss IDs differ')
    for field in ('freeze', 'proposal_commit'):
        expected.pop(field, None)
    if actual != expected:
        raise RuntimeError('evaluation receipt fields differ')


def replay(train, dev, output):
    output.mkdir(parents=True, exist_ok=False)
    paths = {}
    for version, script, prefix in (('v1', 'retrieval_selection_trial_v1.py', 'retrieval-selection'),
                                    ('v2', 'retrieval_selection_trial.py', 'retrieval-selection-v2')):
        db = output / f'{version}.sqlite'
        for phase, source in (('propose', train), ('evaluate', dev)):
            command = [sys.executable, str(ROOT/'scripts'/script), phase, str(db), str(source)]
            result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True).stdout
            # Reopening uses a fresh interpreter and must return the same committed bytes.
            restarted = subprocess.run(command, cwd=ROOT, check=True, capture_output=True).stdout
            if result != restarted:
                raise RuntimeError('restart changed committed receipt')
            path = output/f'{version}-{phase}.json'
            path.write_bytes(result)
            paths[version, phase] = path
            if phase == 'propose':
                if result != (ROOT/'reports'/f'{prefix}-proposal.json').read_bytes():
                    raise RuntimeError('proposal receipt bytes differ')
            else:
                compare_result(json.loads(result), json.loads((ROOT/'reports'/f'{prefix}-result.json').read_text()))
    command = [sys.executable, str(ROOT/'scripts'/'retrieval_position_sensitivity.py'),
               str(train), str(dev), str(paths['v1','propose']), str(paths['v1','evaluate']),
               str(paths['v2','propose']), str(paths['v2','evaluate'])]
    result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True).stdout
    (output/'sensitivity.json').write_bytes(result)
    actual = json.loads(result)
    rows = actual.pop('paired_rows')
    if actual['paired_rows_digest'] != digest(rows):
        raise RuntimeError('sensitivity rows digest differs')
    expected = json.loads((ROOT/'reports'/'retrieval-position-sensitivity-v2.json').read_text())
    if actual != expected:
        raise RuntimeError('sensitivity receipt fields differ')
    print('PASS: v1/v2 proposal bytes, evaluation rows and fields, separate-process restart, source membership, matched spend and sensitivity')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('train', 'dev', 'output_directory'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    replay(args.train.resolve(), args.dev.resolve(), args.output_directory.resolve())

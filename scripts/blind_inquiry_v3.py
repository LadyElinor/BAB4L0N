"""Collect a prospectively frozen inquiry with separate retrieval and reviewer counts."""
import argparse
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import blind_inquiry as v1
from scripts import blind_inquiry_v2 as custody
from scripts.blind_inquiry_targets import load_targets
from scripts.blind_inquiry_v3_freeze import check_freeze, freeze, trial


def _decisions(answers):
    return {(row['id'], row['arm']): row['decision'] for row in answers['rows']}


def _check_alignment(decisions, review):
    seen = set()
    for row in review['rows']:
        item = (row['id'], row['arm'])
        if item not in decisions or item in seen:
            raise ValueError('review must cover each blinded result exactly once')
        seen.add(item)
        assessment = row['assessment']
        v1.exact(assessment, ' '.join(v1.DIMENSIONS))
        if decisions[item] == 'answer' and assessment['warranted_abstention'] == 'yes':
            raise ValueError(f'{item}: warranted_abstention=yes on an answer')
        if decisions[item] == 'abstain' and assessment['unsupported_claim'] == 'yes':
            raise ValueError(f'{item}: unsupported_claim=yes on an abstention')
    if seen != decisions.keys():
        raise ValueError('review must cover each blinded result exactly once')


def seal_review(sheet, answers, answer_digest, review):
    digest = custody.seal_review(sheet, answers, answer_digest, review)
    _check_alignment(_decisions(answers), review)
    return digest


def _check_returns(rows, sheet, arms):
    """Ensure every tally denominator and charge agrees with the anonymous worksheet."""
    expected_methods = set(arms)
    by_alias = {(r['id'], r['arm']): r for r in sheet['rows']}
    if len(by_alias) != len(sheet['rows']):
        raise ValueError('duplicate blinded result in worksheet')
    seen_aliases = set()
    methods = {}
    spend = {}
    for row in rows:
        q, method = row['id'], row['method']
        alias = (q, row['arm'])
        if alias not in by_alias or alias in seen_aliases:
            raise ValueError('key must cover each blinded result exactly once')
        seen_aliases.add(alias)
        members = methods.setdefault(q, set())
        if method not in expected_methods or method in members:
            raise ValueError('unexpected or repeated method for question')
        members.add(method)
        refs = [p['ref'] for p in by_alias[alias]['passages']]
        matched = row['matched_refs']
        cost = row['matched_spend']
        if (type(cost) is not int or cost != len(refs) or len(set(refs)) != len(refs)
                or sorted(matched) != sorted(refs) or spend.setdefault(q, cost) != cost):
            raise ValueError('matched passages or per-question spend differ')
    if seen_aliases != by_alias.keys() or any(group != expected_methods for group in methods.values()):
        raise ValueError('missing blinded result or method')


def tally(rows, answers, targets=None):
    """Count once per method, reviewer and question on validated collection rows."""
    decisions = _decisions(answers)
    out = {}
    for row in rows:
        q = row['id']
        decision = decisions[q, row['arm']]
        if targets is not None:
            hits = len(targets[q].intersection(row['matched_refs']))
        for review in row['reviews']:
            key = f"{row['method']}/{review['reviewer']}"
            if key not in out:
                out[key] = {
                    'rows': 0, 'answers': 0, 'abstentions': 0, 'matched_spend': 0,
                    'designated_passage_hits': None if targets is None else 0,
                    'designated_passage_targets': None if targets is None else 0,
                    'credited_passage_hits': 0, 'supported_answers': 0, 'unsupported_claims': 0,
                    'warranted_abstentions': 0, 'unwarranted_abstentions': 0, 'uncertain': 0,
                }
            counts = out[key]
            counts['rows'] += 1
            counts['matched_spend'] += row['matched_spend']
            if targets is not None:
                counts['designated_passage_hits'] += hits
                counts['designated_passage_targets'] += len(targets[q])
            a = review['assessment']
            credited = a['equivalent_evidence'] == 'yes'
            counts['credited_passage_hits'] += credited
            counts['uncertain'] += 'uncertain' in a.values()
            if decision == 'answer':
                counts['answers'] += 1
                counts['unsupported_claims'] += a['unsupported_claim'] == 'yes'
                counts['supported_answers'] += a['unsupported_claim'] == 'no' and credited
            else:
                counts['abstentions'] += 1
                counts['warranted_abstentions'] += a['warranted_abstention'] == 'yes'
                counts['unwarranted_abstentions'] += a['warranted_abstention'] == 'no'
    return dict(sorted(out.items()))


def collect(sheet, key_path, answers, rubric_path, frozen, published_hash,
            register, register_hash, reviews, targets_path=None):
    check_freeze(frozen, published_hash)
    if sheet['commitment'] != published_hash:
        raise ValueError('worksheet belongs to a different freeze')
    expected = frozen['targets_sha256']
    if (expected is None) != (targets_path is None):
        raise ValueError('supply targets exactly when a target manifest was frozen')
    targets = (load_targets(targets_path, expected, sheet, frozen['corpus_refs'])
               if targets_path is not None else None)
    decisions = _decisions(answers)
    for review in reviews:
        _check_alignment(decisions, review)
    report = custody.collect(sheet, key_path, answers, rubric_path, frozen, published_hash,
                            register, register_hash, reviews)
    _check_returns(report['rows'], sheet, frozen['arms'])
    return {**report, 'analysis_profile': frozen['profile'], 'targets_sha256': expected,
            'tally': tally(report['rows'], answers, targets)}


def table(counts):
    header = ('| Method / reviewer | Inspections | Exact hits / targets | Credited results | Supported answers '
              '| Unsupported claims | Warranted abstentions | Unwarranted abstentions | Uncertain results |')
    lines = [header, '|' + ' --- |' * 9]
    for key, c in counts.items():
        exact = ('unavailable' if c['designated_passage_hits'] is None
                 else f"{c['designated_passage_hits']}/{c['designated_passage_targets']}")
        values = [key, c['matched_spend'], exact, c['credited_passage_hits'], c['supported_answers'],
                  c['unsupported_claims'], c['warranted_abstentions'], c['unwarranted_abstentions'], c['uncertain']]
        lines.append('| ' + ' | '.join(map(str, values)) + ' |')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name, fields in (
            ('freeze', 'packet documents rubric_hash output'), ('run', 'packet documents freeze published_hash output_directory'),
            ('seal-review', 'worksheet answers answer_digest review'),
            ('collect', 'worksheet private_key answers rubric freeze published_hash register register_digest output')):
        cmd = commands.add_parser(name)
        for field in fields.split():
            cmd.add_argument(field)
        if name == 'freeze':
            cmd.add_argument('--readers', choices=['baseline', 'coverage'], default='baseline')
            cmd.add_argument('--targets-sha256', help='digest of the private exact-reference manifest')
        elif name == 'collect':
            cmd.add_argument('reviews', nargs='+')
            cmd.add_argument('--targets', help='private manifest committed at freeze')
            cmd.add_argument('--table', action='store_true', help='also print the per-reviewer Markdown table')
    args = parser.parse_args()
    read = custody.read
    if args.command == 'freeze':
        frozen = freeze(read(args.packet), args.documents, args.rubric_hash, args.readers, args.targets_sha256)
        v1.write(args.output, frozen)
        print(v1.digest(frozen))
    elif args.command == 'run':
        sheet, key = trial(read(args.packet), args.documents, read(args.freeze), args.published_hash, secrets.token_bytes(32))
        dest = Path(args.output_directory)
        dest.mkdir(mode=0o700)
        v1.write(dest / 'worksheet.json', sheet)
        v1.write(dest / 'custodian-only.json', key)
        print('Worksheet digest:', v1.digest(sheet), 'Private key digest:', v1.digest(key))
    elif args.command == 'seal-review':
        print(seal_review(read(args.worksheet), read(args.answers), args.answer_digest, read(args.review)))
    else:
        report = collect(read(args.worksheet), args.private_key, read(args.answers), args.rubric,
                         read(args.freeze), args.published_hash, read(args.register), args.register_digest,
                         [read(p) for p in args.reviews], args.targets)
        v1.write(args.output, report)
        if args.table:
            print(table(report['tally']))


if __name__ == '__main__':
    try:
        main()
    except (KeyError, OSError, TypeError, ValueError) as exc:
        sys.exit(str(exc))

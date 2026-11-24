"""Freeze and run a four-reader inquiry, using the existing blinded review workflow."""
import argparse
import hmac
from itertools import chain, zip_longest
from pathlib import Path
import re
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from babalon.inquiry import _index, _words
from babalon.retrieval_selection import BM25, rank
from scripts import blind_inquiry as baseline
from scripts import blind_inquiry_v2 as custody

PROFILE = 'babalon.blind-inquiry.coverage.v1'
CANDIDATE = 'clause-bm25'
ARMS = (*baseline.ARMS, CANDIDATE)
EXTRA_CODE = ('scripts/blind_inquiry_coverage.py', 'docs/BLIND_INQUIRY_COVERAGE.md')


def clause_rank(question, rows, limit):
    full = rank(question, rows, BM25, limit)
    clauses = re.split(r'\b(?:and|but|versus)\b', question, flags=re.IGNORECASE)
    if len(full) < 2 or len(clauses) != 2 or any(len(_words(part)) < 2 for part in clauses):
        return full
    left, right = (rank(part, rows, BM25, limit) for part in clauses)
    interleaved = (ref for pair in zip_longest(left, right) for ref in pair if ref is not None)
    # All clause tokens occur in the full query. The fallback preserves BM25's
    # count even if every match was to the conjunction itself.
    return list(dict.fromkeys(chain(full[:1], interleaved, full)))[:limit]


def freeze(packet, directory, rubric_hash):
    control = baseline.freeze(packet, directory, rubric_hash)
    implementation = custody.implementation()
    for path in EXTRA_CODE:
        implementation[path] = baseline.digest_bytes((ROOT / path).read_bytes())
    return {'profile': PROFILE, 'arms': ARMS, 'control_freeze': control,
            'rubric_sha256': rubric_hash, 'implementation': implementation, 'promotion_eligible': False}


def trial(packet, directory, frozen, published_hash, secret):
    if not isinstance(secret, bytes) or len(secret) != 32:
        raise ValueError('expected 32 private random bytes')
    if baseline.digest(frozen) != published_hash or baseline.digest(
            freeze(packet, directory, frozen['rubric_sha256'])) != published_hash:
        raise ValueError('freeze differs from the externally retained commitment')
    control = frozen['control_freeze']
    indexed, manifest = _index(directory)
    if manifest != control['documents']:
        raise ValueError('candidate source bytes changed')
    rows = {ref: line['text'] for ref, line in indexed.items()}
    # The historical trial independently verifies these same bytes and operates
    # on an immutable private copy. Preserve its original matched and native runs.
    _, control_key = baseline.trial(packet, directory, control, baseline.digest(control), secret)
    controls = {q['id']: {} for q in packet['questions']}
    for record in control_key['rows']:
        controls[record['id']][record['method']] = record
    worksheet, key = [], []
    for question in packet['questions']:
        qid, query = question['id'], question['question']
        records = controls[qid]
        spend = records['bm25']['matched_spend']
        native = clause_rank(query, rows, packet['budget'])
        matched = clause_rank(query, rows, spend)
        if len(native) != len(records['bm25']['natural_refs']) or len(matched) != spend:
            raise ValueError('candidate and BM25 spend differ')
        records[CANDIDATE] = {'method': CANDIDATE, 'natural_refs': native,
                              'matched_refs': matched, 'matched_spend': spend}
        order = sorted(ARMS, key=lambda arm: hmac.digest(secret, (qid + ':' + arm).encode(), 'sha256'))
        for alias, arm in zip('ABCD', order):
            record = records[arm]
            if record['matched_spend'] != spend:
                raise ValueError('unmatched controls')
            passages = [{'ref': ref, 'family': packet['families'][ref.split('#')[0]], 'text': rows[ref]}
                        for ref in sorted(record['matched_refs'])]
            worksheet.append({'id': qid, 'question': query, 'arm': alias, 'passages': passages})
            key.append({**record, 'id': qid, 'arm': alias, 'natural_spend': len(record['natural_refs'])})
    sheet = {'commitment': published_hash, 'rows': worksheet}
    return sheet, {'commitment': published_hash, 'worksheet_digest': baseline.digest(sheet),
                   'rows': key, 'promotion_eligible': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name, fields in [('freeze', ('packet', 'documents', 'rubric_hash', 'output')),
                         ('run', ('packet', 'documents', 'freeze', 'published_hash', 'output_directory'))]:
        command = commands.add_parser(name)
        for field in fields:
            command.add_argument(field)
    args = parser.parse_args()
    packet = custody.read(args.packet)
    if args.command == 'freeze':
        record = freeze(packet, args.documents, args.rubric_hash)
        baseline.write(args.output, record)
        print(baseline.digest(record))
    else:
        sheet, key = trial(packet, args.documents, custody.read(args.freeze), args.published_hash,
                           secrets.token_bytes(32))
        destination = Path(args.output_directory)
        destination.mkdir(mode=0o700)
        baseline.write(destination / 'worksheet.json', sheet)
        baseline.write(destination / 'custodian-only.json', key)
        print('Worksheet digest:', baseline.digest(sheet), 'Private key digest:', baseline.digest(key))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as exc:
        sys.exit(str(exc))

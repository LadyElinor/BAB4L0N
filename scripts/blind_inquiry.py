"""Offline custodian tool: freeze questions and rubric, compare readers, retain reviews."""
import argparse
from hashlib import sha256
import hmac
import json
from pathlib import Path
import re
import secrets
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from babalon.contracts import integer, label, prose
from babalon.inquiry import _index, investigate
from babalon.retrieval_selection import BM25, rank
from scripts.court_trial import inspected, keyword

ARMS = ('shared-gap', 'keyword', 'bm25')
PROFILE = 'babalon.blind-inquiry.v1'
DIMENSIONS = ('equivalent_evidence', 'source_attribution', 'unsupported_claim', 'warranted_abstention')
CODE = ('scripts/blind_inquiry.py', 'scripts/court_trial.py', 'babalon/inquiry.py',
        'babalon/contracts.py', 'babalon/retrieval_selection.py', 'docs/BLIND_INQUIRY.md')


def digest_bytes(data):
    return sha256(data).hexdigest()


def digest(obj):
    return digest_bytes(json.dumps(obj, sort_keys=True, ensure_ascii=False, allow_nan=False,
                                  separators=(',', ':')).encode())


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, data):
    with Path(path).open('x', encoding='utf8') as out:
        json.dump(data, out, indent=2, ensure_ascii=False, allow_nan=False)
        out.write('\n')


def exact(obj, keys):
    if not isinstance(obj, dict) or set(obj) != set(keys.split()):
        raise ValueError('unexpected or missing fields: ' + keys)


def commitment(packet, rubric_hash):
    exact(packet, 'questions families budget')
    integer(packet['budget'], 1, 24)
    if not isinstance(rubric_hash, str) or not re.fullmatch('[0-9a-f]{64}', rubric_hash):
        raise ValueError('expected SHA-256 of private rubric bytes')
    if not isinstance(packet['questions'], list):
        raise ValueError('expected list of questions')
    integer(len(packet['questions']), 1, 256)
    ids = set()
    for q in packet['questions']:
        exact(q, 'id question')
        label(q['id'])
        prose(q['question'])
        if q['id'] in ids:
            raise ValueError('duplicate question ID')
        ids.add(q['id'])
    return {'profile': PROFILE, 'packet_digest': digest(packet), 'rubric_sha256': rubric_hash,
            'implementation': {p: digest_bytes((ROOT / p).read_bytes()) for p in CODE},
            'arms': ARMS, 'dimensions': DIMENSIONS, 'promotion_eligible': False}


def freeze(packet, directory, rubric_hash):
    obj = commitment(packet, rubric_hash)
    _, documents = _index(directory)
    families = packet['families']
    if not isinstance(families, dict) or set(families) != set(documents):
        raise ValueError('assign a source family to each document')
    for family in families.values():
        label(family)
    return {**obj, 'documents': documents}


def run_one(question, directory, rows, allowance):
    report = investigate(question, directory, budget=allowance, strategy='shared-gap')
    refs = list(dict.fromkeys(inspected(report)))
    if len(refs) != report['audit']['inspections']:
        raise ValueError('shared charge mismatch')
    return {'shared-gap': refs, 'keyword': keyword(question, rows, allowance),
            'bm25': rank(question, rows, BM25, allowance)}


def trial(packet, directory, frozen, published_hash, secret):
    if not isinstance(secret, bytes) or len(secret) != 32:
        raise ValueError('expected 32 private random bytes')
    if not hmac.compare_digest(digest(frozen), published_hash):
        raise ValueError('commitment differs from the externally retained digest')
    # Make all arms read the same immutable local copy for the entire run.
    # Only previously validated simple document names may be copied.
    with TemporaryDirectory() as tmp:
        work = Path(tmp)
        if digest(freeze(packet, directory, frozen['rubric_sha256'])) != published_hash:
            raise ValueError('inputs or implementation changed')
        for name in frozen['documents']:
            with (Path(directory) / name).open("rb") as src:
                data = src.read(32769)
            if digest_bytes(data) != frozen['documents'][name]:
                raise ValueError('source changed during copy')
            (work / name).write_bytes(data)
        indexed, _ = _index(work)
        rows = {ref: row['text'] for ref, row in indexed.items()}
        sheets, private = [], []
        for q in packet['questions']:
            allowance = packet['budget']
            natural = run_one(q['question'], work, rows, allowance)
            matched = natural
            while len(set(map(len, matched.values()))) != 1:
                # Start new, bounded runs at the common attainable spend. Never pad a return.
                cap = min(map(len, matched.values()))
                if cap >= allowance:
                    raise ValueError('nondecreasing match cap')
                allowance = cap
                matched = run_one(q['question'], work, rows, allowance)
            order = sorted(ARMS, key=lambda arm: hmac.digest(secret, (q['id'] + ':' + arm).encode(), 'sha256'))
            for alias, arm in zip('ABC', order):
                passages = [{'ref': ref, 'family': packet['families'][ref.split('#')[0]], 'text': rows[ref]}
                            for ref in sorted(matched[arm])]
                sheets.append({'id': q['id'], 'question': q['question'], 'arm': alias, 'passages': passages})
                private.append({'id': q['id'], 'arm': alias, 'method': arm, 'natural_refs': natural[arm],
                                'matched_refs': matched[arm], 'matched_spend': len(passages)})
    sheet = {'commitment': published_hash, 'rows': sheets}
    return sheet, {'commitment': published_hash, 'worksheet_digest': digest(sheet), 'rows': private,
                   'promotion_eligible': False}


def seal_answers(sheet, response):
    exact(response, 'interpreter worksheet_digest rows')
    label(response['interpreter'])
    if response['worksheet_digest'] != digest(sheet):
        raise ValueError('answers use a different worksheet')
    expected = {(r['id'], r['arm']): {p['ref'] for p in r['passages']} for r in sheet['rows']}
    seen = set()
    for row in response['rows']:
        exact(row, 'id arm decision interpretation cites uncertainty unanswered')
        rid = row['id'], row['arm']
        if rid not in expected or rid in seen or row['decision'] not in ('answer', 'abstain'):
            raise ValueError('invalid blinded answer')
        seen.add(rid)
        for k in ('interpretation', 'uncertainty', 'unanswered'):
            prose(row[k])
        if not isinstance(row['cites'], list) or not set(row['cites']) <= expected[rid]:
            raise ValueError('answer cites an unavailable passage')
        if row['decision'] == 'answer' and not row['cites']:
            raise ValueError('an answer must cite a passage')
    if seen != set(expected):
        raise ValueError('missing blinded answer')
    return digest(response)


def collect(sheet, key, key_hash, response, rubric_file, frozen, published_hash, reviews):
    answer_hash = seal_answers(sheet, response)
    if digest(key) != key_hash:
        raise ValueError('private key differs from the external run commitment')
    if (digest(frozen) != published_hash or sheet['commitment'] != published_hash or
            key['commitment'] != published_hash or key['worksheet_digest'] != digest(sheet)):
        raise ValueError('worksheet or commitment differs')
    if digest_bytes(Path(rubric_file).read_bytes()) != frozen['rubric_sha256']:
        raise ValueError('rubric changed')
    def row_id(row):
        return row['id'], row['arm']
    expected = {row_id(r): {p['ref'] for p in r['passages']} for r in sheet['rows']}
    if len(reviews) < 2:
        raise ValueError('two separate blinded reviews required')
    judges, by_item = set(), {k: [] for k in expected}
    for review in reviews:
        exact(review, 'reviewer worksheet_digest answer_digest rows')
        judge = review['reviewer']
        label(judge)
        if (judge in judges or judge == response['interpreter'] or review['worksheet_digest'] != digest(sheet)
                or review['answer_digest'] != answer_hash):
            raise ValueError('duplicate reviewer or different worksheet')
        judges.add(judge)
        if {row_id(r) for r in review['rows']} != set(expected) or len(review['rows']) != len(expected):
            raise ValueError('review must cover each blinded result exactly once')
        for row in review['rows']:
            exact(row, 'id arm assessment cites rationale unanswered')
            exact(row['assessment'], ' '.join(DIMENSIONS))
            if any(v not in ('yes','no','uncertain','not_applicable') for v in row['assessment'].values()):
                raise ValueError('invalid assessment')
            prose(row['rationale'])
            prose(row['unanswered'])
            if not isinstance(row['cites'], list) or not set(row['cites']) <= expected[row_id(row)]:
                raise ValueError('review cited a passage outside the blinded return')
            if row['assessment']['equivalent_evidence'] == 'yes' and not row['cites']:
                raise ValueError('credit for equivalent evidence needs a citation')
            by_item[row_id(row)].append({'reviewer': judge, **row})
    return {'commitment': published_hash, 'answer_digest': answer_hash, 'answers': response,
            'promotion_eligible': False, 'rows': [
        {**item, 'reviews': by_item[row_id(item)], 'disagreements': [
            dim for dim in DIMENSIONS if len({r['assessment'][dim] for r in by_item[row_id(item)]}) > 1]}
        for item in key['rows']]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    for cmd, args in {'freeze':'packet documents rubric_hash output',
                      'run':'packet documents freeze published_hash output_directory',
                      'seal-answers':'worksheet answers',
                      'collect':'worksheet private_key key_hash answers rubric freeze published_hash output'}.items():
        child = sub.add_parser(cmd)
        for arg in args.split():
            child.add_argument(arg)
        if cmd == 'collect':
            child.add_argument('reviews', nargs='+')
    a = parser.parse_args()
    if a.cmd == 'freeze':
        record = freeze(read(a.packet), Path(a.documents), a.rubric_hash)
        write(a.output, record)
        print(digest(record))
    elif a.cmd == 'run':
        sheet, key = trial(read(a.packet), Path(a.documents), read(a.freeze), a.published_hash, secrets.token_bytes(32))
        dest = Path(a.output_directory)
        dest.mkdir(mode=0o700)
        write(dest/'worksheet.json', sheet)
        write(dest/'custodian-only.json', key)
        print('Worksheet digest:', digest(sheet), 'Private key digest:', digest(key))
    elif a.cmd == 'seal-answers':
        print(seal_answers(read(a.worksheet), read(a.answers)))
    else:
        write(a.output, collect(read(a.worksheet), read(a.private_key), a.key_hash, read(a.answers), a.rubric,
                                read(a.freeze), a.published_hash, [read(r) for r in a.reviews]))


if __name__ == '__main__':
    main()

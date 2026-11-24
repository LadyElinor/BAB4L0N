"""Verify pre-unblinding deposits, then collect a v1 blinded worksheet."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import blind_inquiry as v1

PROFILE = 'babalon.blind-inquiry.collection.v2'
CODE = (*v1.CODE, 'scripts/blind_inquiry_v2.py', 'docs/BLIND_INQUIRY_V2.md')


def unique_pairs(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError(f'duplicate name: {name}')
        result[name] = value
    return result


def read(path):
    with Path(path).open('rb') as source:
        return json.load(source, object_pairs_hook=unique_pairs)


def require_digest(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('expected a lowercase SHA-256 commitment')


def check_answers(sheet, answers, answer_digest):
    require_digest(answer_digest)
    if v1.seal_answers(sheet, answers) != answer_digest:
        raise ValueError('answers differ from the retained answer commitment')


def review_digest(review, worksheet_digest, answer_digest, interpreter):
    v1.exact(review, 'reviewer worksheet_digest answer_digest rows')
    v1.label(review['reviewer'])
    if review['reviewer'] == interpreter:
        raise ValueError('interpreter cannot review their own answers')
    if review['worksheet_digest'] != worksheet_digest or review['answer_digest'] != answer_digest:
        raise ValueError('review refers to a different worksheet or answer commitment')
    return v1.digest(review)


def seal_review(sheet, answers, answer_digest, review):
    """Commit to a single linked review without reading the method key or peers' files."""
    check_answers(sheet, answers, answer_digest)
    return review_digest(review, v1.digest(sheet), answer_digest, answers['interpreter'])


def check_roster(review_digests):
    if not isinstance(review_digests, dict) or len(review_digests) < 2:
        raise ValueError('commitments for at least two named reviewers are required')
    for name, value in review_digests.items():
        v1.label(name)
        require_digest(value)


def implementation():
    return {name: v1.digest_bytes((ROOT / name).read_bytes()) for name in CODE}


def close_register(sheet, key_digest, answer_digest, reviewer_deposits):
    """Custodian inputs are previously deposited digests, never candidate records."""
    require_digest(key_digest)
    require_digest(answer_digest)
    review_digests = unique_pairs(reviewer_deposits)
    check_roster(review_digests)
    return {'profile': PROFILE, 'implementation': implementation(),
            'worksheet_digest': v1.digest(sheet), 'key_digest': key_digest,
            'answer_digest': answer_digest, 'review_digests': review_digests}


def collect(sheet, key_path, answers, rubric_path, frozen, published_hash,
            register, register_hash, reviews):
    require_digest(register_hash)
    if v1.digest(register) != register_hash:
        raise ValueError('register differs from its independently retained commitment')
    v1.exact(register, 'profile implementation worksheet_digest key_digest answer_digest review_digests')
    if register['profile'] != PROFILE or register['implementation'] != implementation():
        raise ValueError('collection profile or implementation changed')
    if register['worksheet_digest'] != v1.digest(sheet):
        raise ValueError('worksheet differs from the registered worksheet')
    require_digest(register['key_digest'])
    check_answers(sheet, answers, register['answer_digest'])
    expected = register['review_digests']
    check_roster(expected)
    submitted = {}
    for review in reviews:
        value = review_digest(review, register['worksheet_digest'], register['answer_digest'],
                              answers['interpreter'])
        name = review['reviewer']
        if name in submitted:
            raise ValueError('duplicate submitted reviewer')
        submitted[name] = value
    if submitted.keys() != expected.keys():
        raise ValueError('submitted reviewers differ from the closed roster')
    for name, value in submitted.items():
        if value != expected[name]:
            raise ValueError(f'review differs from the retained commitment for {name}')

    # Open the method key only after every submitted record matches its deposit.
    # v1 also validates the rubric, key, row coverage, citations and assessments.
    report = v1.collect(sheet, read(key_path), register['key_digest'], answers, rubric_path,
                        frozen, published_hash, reviews)
    return {**report, 'collection_profile': PROFILE, 'status': 'NOT_PROMOTED',
            'register_digest': register_hash, 'review_digests': expected,
            'commitment_integrity': 'matched_retained_register',
            'reviewer_independence': 'not_verified'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    seal = sub.add_parser('seal-review', help='print a digest to deposit privately')
    for name in ('worksheet', 'answers', 'answer_digest', 'review'):
        seal.add_argument(name)
    close = sub.add_parser('close-register', help='close the complete set of independent deposits')
    for name in ('worksheet', 'key_digest', 'answer_digest', 'output'):
        close.add_argument(name)
    close.add_argument('--review', nargs=2, metavar=('REVIEWER', 'DIGEST'), action='append', required=True)
    collect_parser = sub.add_parser('collect', help='verify all deposits and produce the unblinded report')
    for name in ('worksheet', 'private_key', 'answers', 'rubric', 'freeze', 'published_hash',
                 'register', 'register_digest', 'output'):
        collect_parser.add_argument(name)
    collect_parser.add_argument('reviews', nargs='+')
    args = parser.parse_args()
    sheet = read(args.worksheet)
    if args.command == 'seal-review':
        print(seal_review(sheet, read(args.answers), args.answer_digest, read(args.review)))
    elif args.command == 'close-register':
        register = close_register(sheet, args.key_digest, args.answer_digest, args.review)
        v1.write(args.output, register)
        print(v1.digest(register))
    else:
        report = collect(sheet, args.private_key, read(args.answers), args.rubric, read(args.freeze),
                         args.published_hash, read(args.register), args.register_digest,
                         [read(path) for path in args.reviews])
        v1.write(args.output, report)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as exc:
        sys.exit(str(exc))

"""Compare preserved SQuAD v1 and v2 public replays; never grant promotion."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from babalon.contracts import Invalid, digest
from scripts import retrieval_selection_trial as current
from scripts import retrieval_selection_trial_v1 as legacy

ARMS = ('active', 'bm25', 'keyword', 'candidate', 'position_last_first', 'position_first')


def paired_spend(old_rows, new_rows):
    old = {row['id']: row for row in old_rows}
    new = {row['id']: row for row in new_rows}
    if len(old) != len(old_rows) or len(new) != len(new_rows) or old.keys() != new.keys():
        raise Invalid('paired question IDs differ or repeat')
    if any(type(row['spend']) is not int or not 0 <= row['spend'] <= 4 for row in [*old_rows, *new_rows]):
        raise Invalid('invalid inspection spend')
    differences = [{'id': qid, 'old': old[qid]['spend'], 'new': new[qid]['spend']}
                   for qid in old if old[qid]['spend'] != new[qid]['spend']]
    if differences:
        raise Invalid('per-question spend changed; separate fixed-spend analysis required: ' + json.dumps(differences))
    return {'matched_questions': len(old), 'changed_questions': 0,
            'old_total': sum(row['spend'] for row in old_rows),
            'new_total': sum(row['spend'] for row in new_rows)}


def membership(raw, phase):
    old = list(legacy.sample(raw, phase))
    new = list(current.sample(raw, phase))
    if len(old) != current.LIMIT[phase] or len(new) != len(old):
        raise Invalid('drawn population differs')
    # Independently reconstruct original index membership, not merely equal text.
    lookup = {}
    for article in json.loads(raw)['data']:
        paragraphs = article['paragraphs']
        for target, paragraph in enumerate(paragraphs):
            for qa in paragraph['qas']:
                lookup[qa['id']] = (len(paragraphs), target)
    evidence = []
    admitted = []
    for before, after in zip(old, new):
        qid, question, old_texts, old_target = before
        if before[:2] != after[:2] or Counter(old_texts) != Counter(after[2]) or old_texts[old_target] != after[2][after[3]]:
            raise Invalid('question or selected passage membership changed')
        count, target = lookup[qid]
        order = sorted(range(count), key=lambda j: sha256(f'{qid}:{j}'.encode()).digest())
        selected = [target] + [j for j in order if j != target][:11]
        if sorted(selected) != sorted(current.selected_paragraphs(qid, count, target)):
            raise Invalid('original paragraph index membership changed')
        record = {'id': qid, 'original_indices': sorted(selected),
                  'text_multiset_digest': digest(sorted(old_texts)),
                  'old_gold_position': old_target + 1, 'new_gold_position': after[3] + 1}
        evidence.append(record)
        if all(len(text) <= 2000 for text in old_texts):
            admitted.append(record)
    def histogram(records, key):
        counts = Counter(row[key] for row in records)
        return [counts[i] for i in range(1, 13)]
    return {'drawn': len(evidence), 'admitted': len(admitted),
            'drawn_membership_digest': digest(evidence),
            'admitted_question_ids': [row['id'] for row in admitted],
            'admitted_gold_positions': {row['id']: [row['old_gold_position'], row['new_gold_position']] for row in admitted},
            'old_drawn_gold_positions': histogram(evidence, 'old_gold_position'),
            'new_drawn_gold_positions': histogram(evidence, 'new_gold_position'),
            'old_admitted_gold_positions': histogram(admitted, 'old_gold_position'),
            'new_admitted_gold_positions': histogram(admitted, 'new_gold_position'),
            'exact_original_index_membership_preserved': True}


def summarize(train_raw, dev_raw, old_proposal, old_result, new_proposal, new_result):
    for raw, phase in ((train_raw, 'propose'), (dev_raw, 'evaluate')):
        if sha256(raw).hexdigest() != current.SHA[phase]:
            raise Invalid('source byte hash mismatch')
    for receipt, version in ((old_proposal, legacy.VERSION), (old_result, legacy.VERSION),
                             (new_proposal, current.VERSION), (new_result, current.VERSION)):
        if receipt['version'] != version:
            raise Invalid('receipt version mismatch')
    for proposal, result in ((old_proposal, old_result), (new_proposal, new_result)):
        if result['proposal_digest'] != digest(proposal):
            raise Invalid('proposal linkage mismatch')
    memberships = {'training': membership(train_raw, 'propose'), 'evaluation': membership(dev_raw, 'evaluate')}
    for label, phase, old, new in (('training', 'propose', old_proposal, new_proposal),
                                  ('evaluation', 'evaluate', old_result, new_result)):
        if old['dataset_sha256'] != current.SHA[phase] or new['dataset_sha256'] != current.SHA[phase]:
            raise Invalid('receipt source mismatch')
        if old['evaluated'] != new['evaluated'] or old['excluded'] != new['excluded']:
            raise Invalid('receipt admission differs')
        ids = old['question_ids'] if phase == 'propose' else [row['id'] for row in old['rows']]
        new_ids = new['question_ids'] if phase == 'propose' else [row['id'] for row in new['rows']]
        if ids != new_ids or ids != memberships[label]['admitted_question_ids']:
            raise Invalid('receipt membership differs from source')
    positions = memberships['evaluation']['admitted_gold_positions']
    for index, (proposal, result) in enumerate(((old_proposal, old_result), (new_proposal, new_result))):
        if result['candidate'] != proposal['candidate']:
            raise Invalid('candidate linkage mismatch')
        if result['spend_per_arm'] != sum(row['spend'] for row in result['rows']):
            raise Invalid('receipt spend total mismatch')
        for row in result['rows']:
            expected = f"p{positions[row['id']][index]-1:02}.txt#L1"
            if row['target'] != expected:
                raise Invalid('receipt target differs from source gold position')
        decision = current.gate(result['rows'])
        if result['comparisons'] != decision['comparisons']:
            raise Invalid('paired comparison mismatch')
        if (index == 0 and result['status'] != decision['status']) or (index == 1 and result['gate_status'] != decision['status']):
            raise Invalid('descriptive gate status mismatch')
    if new_result['status'] != 'NOT_PROMOTED' or new_result['promotion_eligible'] is not False:
        raise Invalid('public sensitivity cannot authorize promotion')
    for label, receipt in (('training', new_proposal), ('evaluation', new_result)):
        if receipt['gold_position_histogram'] != memberships[label]['new_admitted_gold_positions'] or receipt['drawn_gold_position_histogram'] != memberships[label]['new_drawn_gold_positions']:
            raise Invalid('receipt gold histogram mismatch')
    spend = paired_spend(old_result['rows'], new_result['rows'])
    paired = []
    for old, new in zip(old_result['rows'], new_result['rows']):
        old = dict(old)
        refs = [f'p{i:02}.txt#L1' for i in range(12)]
        for key, last_first in (('position_last_first', True), ('position_first', False)):
            old[key] = current.position_only(refs, old['spend'], last_first=last_first)
            if new[key] != current.position_only(refs, new['spend'], last_first=last_first):
                raise Invalid('v2 position control mismatch')
        if any(len(set(row[arm])) != row['spend'] or not set(row[arm]) <= set(refs)
               for row in (old, new) for arm in ARMS):
            raise Invalid('invalid choice or unmatched control spend')
        paired.append({'id': old['id'], 'spend': old['spend'],
                       'old_gold_position': int(old['target'][1:3])+1,
                       'new_gold_position': int(new['target'][1:3])+1,
                       'old_hits': {arm: old['target'] in old[arm] for arm in ARMS},
                       'new_hits': {arm: new['target'] in new[arm] for arm in ARMS}})
    scores = {phase: {arm: sum(row[phase+'_hits'][arm] for row in paired) for arm in ARMS}
              for phase in ('old', 'new')}
    if any(scores[phase][arm] != receipt['hits'][arm]
           for phase, receipt in (('old', old_result), ('new', new_result))
           for arm in ('active', 'bm25', 'keyword', 'candidate')):
        raise Invalid('receipt score mismatch')
    if new_result['position_control_hits'] != {arm: scores['new'][arm] for arm in ('position_last_first', 'position_first')}:
        raise Invalid('position-control hit summary mismatch')
    return {'version': 'babalon.squad-position-sensitivity.v2',
            'claim_scope': current.CLAIM_SCOPE, 'status': 'NOT_PROMOTED', 'promotion_eligible': False,
            'original_status': old_result['status'], 'corrected_gate_status': new_result['gate_status'],
            'old_proposal_digest': digest(old_proposal), 'new_proposal_digest': digest(new_proposal),
            'old_evaluation_digest': digest(old_result), 'new_evaluation_digest': digest(new_result),
            'old_evaluation_rows_digest': digest(old_result['rows']),
            'new_evaluation_rows_digest': digest(new_result['rows']),
            'candidate_unchanged': old_proposal['candidate'] == new_proposal['candidate'],
            'old_candidate': old_proposal['candidate'], 'new_candidate': new_proposal['candidate'],
            'old_training_hits': old_proposal['training_hits'], 'new_training_hits': new_proposal['training_hits'],
            'membership': memberships, 'actual_spend': spend, 'hits': scores,
            'paired_changes': {arm: {'gains': sum(not r['old_hits'][arm] and r['new_hits'][arm] for r in paired),
                                     'losses': sum(r['old_hits'][arm] and not r['new_hits'][arm] for r in paired)} for arm in ARMS},
            'paired_rows_digest': digest(paired), 'paired_rows': paired}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('train', 'dev', 'old_proposal', 'old_evaluation', 'new_proposal', 'new_evaluation'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    receipts = [json.loads(getattr(args, name).read_text()) for name in
                ('old_proposal', 'old_evaluation', 'new_proposal', 'new_evaluation')]
    print(json.dumps(summarize(args.train.read_bytes(), args.dev.read_bytes(), *receipts), sort_keys=True, indent=2))

"""Score frozen returns using explicit alternative passage groups."""
from collections import Counter, defaultdict

from scripts.clause_coverage import DEPTHS, METHODS, evidence_score


def method_id(method, depth):
    return f"{method}.d{depth}"


def records_for_question(qid, runs):
    return [{"id": qid, "method": method_id(method, depth), **row}
            for (depth, method), row in runs.items()]


def score_returns(rows, gold):
    items, totals, by_case = {}, defaultdict(Counter), {}
    for row in rows:
        qid, method = row["id"], row["method"]
        question = gold[qid]
        groups = question["groups"]
        scored = evidence_score(row["matched_refs"], row["pool_refs"], groups, row["matched_spend"])
        question_rows = items.setdefault(qid, {})
        if method in question_rows:
            raise ValueError("duplicate scored method")
        question_rows[method] = scored
        counts = totals[method]
        cost_keys = ("matched_spend", "natural_spend", "rank_calls", "scored_pairs", "input_positions")
        counts.update({k: row[k] for k in cost_keys})
        counts.update(questions=1, target_bearing=bool(groups), split_questions=row["split"],
                      complete=scored["complete"] is True, pool_complete=scored["pool_complete"] is True,
                      canonical_hits=len(scored["canonical_hits"]), canonical_targets=scored["canonical_targets"],
                      selection_misses=scored["pool_complete"] is True and not scored["complete"],
                      pool_unattainable=scored["pool_complete"] is False)
        case = by_case.setdefault(question["case"], defaultdict(Counter))[method]
        case.update(questions=1, target_bearing=bool(groups), pool_complete=scored["pool_complete"] is True,
                    complete=scored["complete"] is True, matched_spend=row["matched_spend"])
    expected = {method_id(m, d) for m in METHODS for d in DEPTHS}
    if items.keys() != gold.keys() or any(r.keys() != expected for r in items.values()):
        raise ValueError("incomplete set of questions, depths or methods")
    for question_rows in items.values():
        for d in DEPTHS:
            ceilings = {question_rows[method_id(m, d)]["pool_complete"] for m in METHODS}
            if len(ceilings) != 1:
                raise ValueError("readers were scored on different pool ceilings")
    pairs = {}
    for depth in DEPTHS:
        candidate = method_id("clause-coverage", depth)
        for control in ("reciprocal-rank", "bm25", "ranker-exclusive"):
            comparator = method_id(control, depth)
            transitions = {"gains": [], "losses": [], "ties": 0}
            for qid, question_rows in items.items():
                a, b = (question_rows[m]["complete"] for m in (candidate, comparator))
                if a is None:
                    continue
                if a == b:
                    transitions["ties"] += 1
                else:
                    transitions["gains" if a else "losses"].append(qid)
            pairs[f"{candidate} vs {comparator}"] = transitions
    return {"totals": dict(totals), "by_case": by_case, "paired": pairs, "items": items}


def leave_one_case_out(report):
    """Primary difference in completion rates with each case held out in turn."""
    primary = DEPTHS[0]
    a, b = (method_id(m, primary) for m in ("clause-coverage", "reciprocal-rank"))
    result = {}
    for case, counts in report["by_case"].items():
        denominator = report["totals"][a]["target_bearing"] - counts[a]["target_bearing"]
        net = report["totals"][a]["complete"] - report["totals"][b]["complete"]
        net -= counts[a]["complete"] - counts[b]["complete"]
        result[case] = {"net_complete": net, "target_bearing": denominator,
                        "rate_difference": net / denominator if denominator else None}
    return result

"""Frozen four-inspection experiment. Ranking and selection never receive judgments."""
from dataclasses import dataclass
from fractions import Fraction
from itertools import chain, zip_longest
import re

from babalon.inquiry import _words
from babalon.retrieval_selection import BM25, rank
from scripts.retrieval_fusion import select as frozen_select

DEPTHS = (4, 8)
CAP = 4
METHODS = ("bm25", "reciprocal-rank", "ranker-exclusive", "clause-coverage")


@dataclass
class Views:
    full: list
    clause: list
    aspects: list
    calls: int


def rank_views(question, passages, depth, *, fixed_only=False):
    """Reproduce the clause-BM25 inputs, retaining individual clause positions."""
    by_query = {}

    def ranked(query):
        if query not in by_query:
            by_query[query] = rank(query, passages, BM25, depth)
        return by_query[query]

    full = ranked(question)
    parts = re.split(r"\b(?:and|but|versus)\b", question, flags=re.IGNORECASE)
    if fixed_only or len(full) < 2 or len(parts) != 2 or any(len(_words(p)) < 2 for p in parts):
        return Views(full, full, [], 1)
    aspects = [ranked(part) for part in parts]
    alternate = (ref for pair in zip_longest(*aspects) for ref in pair if ref is not None)
    clause = list(dict.fromkeys(chain(full[:1], alternate, full)))[:depth]
    return Views(full, clause, aspects, len(by_query))


def choose(method, views, limit):
    if method == "bm25":
        return views.full[:limit]
    if method in ("ranker-exclusive", "reciprocal-rank"):
        return frozen_select(method, views.full, views.clause, {}, limit)
    if method != "clause-coverage":
        raise ValueError("unknown reader")
    if not views.aspects:
        return frozen_select("reciprocal-rank", views.full, views.clause, {}, limit)

    # Rank scores are bounded proxies. They are not calibrated probabilities.
    relevance = {}
    for ranking in (views.full, views.clause):
        for pos, ref in enumerate(ranking, 1):
            relevance[ref] = relevance.get(ref, 0) + Fraction(61, 2 * (60 + pos))
    strength = [{ref: Fraction(1, pos) for pos, ref in enumerate(aspect, 1)}
                for aspect in views.aspects]
    remaining = set(relevance)
    residual = [Fraction(1), Fraction(1)]
    selected = []
    while remaining and len(selected) < limit:
        def priority(ref):
            novelty = sum(weight * values.get(ref, 0) for weight, values in zip(residual, strength)) / 2
            return (-(relevance[ref] + novelty), -relevance[ref], ref)
        ref = min(remaining, key=priority)
        selected.append(ref)
        remaining.remove(ref)
        for i, values in enumerate(strength):
            residual[i] *= 1 - values.get(ref, 0)
    return selected


def run_question(question, passages):
    """Bind a common attainable charge across every reader and both pool depths."""
    rows = {}
    views = {d: rank_views(question, passages, d) for d in DEPTHS}
    for depth, inputs in views.items():
        pool = sorted(set(inputs.full) | set(inputs.clause))
        for method in METHODS:
            natural = choose(method, inputs, CAP)
            calls = 1 if method == "bm25" else inputs.calls
            positions = len(inputs.full)
            if method != "bm25":
                positions += len(inputs.clause)
            if method == "clause-coverage":
                positions += sum(map(len, inputs.aspects))
            rows[depth, method] = {
                "natural_refs": natural, "natural_spend": len(natural), "pool_refs": pool,
                "rank_calls": calls, "scored_pairs": calls * len(passages),
                "input_positions": positions, "split": bool(inputs.aspects),
            }
    cap = min(row["natural_spend"] for row in rows.values())
    for (depth, method), row in rows.items():
        refs = choose(method, views[depth], cap) if cap < CAP else row["natural_refs"]
        if len(refs) != cap or len(set(refs)) != cap or not set(refs) <= set(row["pool_refs"]):
            raise ValueError("failed equal-spend comparison")
        row.update(matched_refs=refs, matched_spend=cap)
    return rows


def evidence_score(refs, pool, groups, spend):
    """Complete any one nonempty group. Pool ceiling respects the common spend."""
    if any(not group or len(set(group)) != len(group) for group in groups):
        raise ValueError("an evidence group requires distinct nonempty references")
    seen, available = set(refs), set(pool)
    if len(refs) != spend or len(seen) != spend or not seen <= available:
        raise ValueError("coverage scoring requires the actual distinct matched return")
    return {
        "pool_complete": any(len(g) <= spend and set(g) <= available for g in groups) if groups else None,
        "complete": any(set(g) <= seen for g in groups) if groups else None,
        "canonical_hits": sorted(seen.intersection(groups[0])) if groups else [],
        "canonical_targets": len(groups[0]) if groups else 0,
    }

"""Bounded selection from two ranked ID lists. Only source coverage uses family labels."""
from fractions import Fraction
from itertools import chain, zip_longest

METHODS = ("interleave", "reciprocal-rank", "source-family", "ranker-exclusive")


def select(method, fixed, clause, families, limit):
    """The input depth is supplied by the caller. Repeated IDs cast one vote per list."""
    if method not in METHODS or type(limit) is not int or limit < 0:
        raise ValueError("unknown fusion method or invalid inspection limit")
    fixed = list(dict.fromkeys(fixed))
    clause = list(dict.fromkeys(clause))
    if method == "interleave":
        pairs = zip_longest(fixed, clause)
        order = (ref for pair in pairs for ref in pair if ref is not None)
        return list(dict.fromkeys(order))[:limit]

    scores = {}
    for ranking in (fixed, clause):
        for position, ref in enumerate(ranking, 1):
            scores[ref] = scores.get(ref, 0) + Fraction(1, 60 + position)
    order = sorted(scores, key=lambda ref: (-scores[ref], ref))
    priority = []
    if method == "source-family":
        seen = set()
        for ref in order:
            family = families[ref.split("#", 1)[0]]
            if family not in seen:
                priority.append(ref)
                seen.add(family)
    elif method == "ranker-exclusive":
        # Give each list one slot for its strongest contribution the other list missed.
        for ranked, other in ((fixed, set(clause)), (clause, set(fixed))):
            first_exclusive = next((ref for ref in ranked if ref not in other), None)
            if first_exclusive is not None:
                priority.append(first_exclusive)
    return list(dict.fromkeys(chain(priority, order)))[:limit]

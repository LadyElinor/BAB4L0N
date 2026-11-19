"""A bounded lexical retrieval policy family. No scores or grades reach rank()."""
from collections import Counter
from itertools import product
from math import log1p
import re

from .contracts import Invalid

# First configuration is the fixed BM25 reference. Training ties keep first.
FAMILY = tuple(product((1.2, 0.6), (0.75, 0.0), (0, 1, 3)))
BM25 = FAMILY[0]


def _tokens(text):
    return re.findall(r"[^\W_]+", text.casefold())


def rank(question, passages, config, limit):
    if tuple(config) not in FAMILY:
        raise Invalid("unknown ranking configuration")
    k1, b, phrase_weight = config
    query = _tokens(question)
    terms = set(query)
    pairs = set(zip(query, query[1:]))
    docs = {ref: _tokens(text) for ref, text in passages.items()}
    df = Counter(term for tokens in docs.values() for term in set(tokens))
    avg = sum(map(len, docs.values())) / max(len(docs), 1)
    scored = []
    for ref, tokens in docs.items():
        counts = Counter(tokens)
        score = 0.0
        for term in sorted(terms.intersection(counts)):
            weight = log1p((len(docs) - df[term] + 0.5) / (df[term] + 0.5))
            normalizer = k1 * (1 - b + b * len(tokens) / avg)
            score += weight * counts[term] * (k1 + 1) / (counts[term] + normalizer)
        score += phrase_weight * len(pairs.intersection(zip(tokens, tokens[1:])))
        if score > 0:
            scored.append((-score, ref))
    return [ref for _, ref in sorted(scored)[:limit]]


def select(totals):
    if len(totals) != len(FAMILY):
        raise Invalid("expected a training count for every frozen policy")
    return FAMILY[max(range(len(FAMILY)), key=totals.__getitem__)]


def gate(rows):
    if not rows:
        raise Invalid("empty evaluation")
    comparisons = {}
    for arm in ("active", "bm25", "keyword"):
        wins = losses = 0
        for row in rows:
            candidate = row["target"] in row["candidate"]
            control = row["target"] in row[arm]
            if any(len(row[key]) != row["spend"] for key in ("candidate", arm)):
                raise Invalid("unequal actual spend")
            wins += candidate and not control
            losses += control and not candidate
        comparisons[arm] = {"wins": wins, "losses": losses, "ties": len(rows) - wins - losses}
    eligible = all(c["wins"] > 0 and c["losses"] == 0 for c in comparisons.values())
    return {"status": "PROMOTED" if eligible else "NOT_PROMOTED", "comparisons": comparisons}

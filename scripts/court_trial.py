#!/usr/bin/env python3
"""Replay the exposed Relay Atlas court retrieval comparison without a network."""
from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from babalon.inquiry import investigate

FIXTURES = ROOT / "examples/inquiry/court-trials"
BUDGET = 4
STOP = frozenset("a an and are as at be but by did do does for from how in is it of on or that the their to was what which who why with".split())


def words(text):
    return set(re.findall("[a-z0-9]+", text.lower())) - STOP


def keyword(query, rows, limit):
    tokens = words(query)
    ranking = sorted(((-len(tokens & words(text)), ref) for ref, text in rows.items()))
    return [ref for score, ref in ranking if score < 0][:limit]


def inspected(report):
    return [ref for rnd in report["rounds"] for worker in rnd["returns"] for ref in worker["sources"]]


def replay(traces=False):
    results = []
    totals = dict(plain=0, keyword=0, guided=0)
    for case in json.loads((FIXTURES / "study.json").read_text()):
        source = FIXTURES / case["id"]
        docs = {name: (source / name).read_bytes() for name in case["records"]}
        rows = {f"{name}#L{i}": line for name, raw in docs.items()
                for i, line in enumerate(raw.decode().splitlines(), 1)}
        with TemporaryDirectory() as tmp:
            annotated = Path(tmp)
            for name, raw in docs.items():
                (annotated / name).write_bytes(raw)
            (annotated / "editor.md").write_bytes(
                f"Assumes [{case['id']}]: {case['note']}\n".encode())
            for task in case["tasks"]:
                targets = task["targets"]
                if len(set(targets)) != 2 or not set(targets) <= rows.keys():
                    raise ValueError("Invalid target references")
                q = task["question"]
                plain = investigate(q, source, budget=BUDGET)
                guided = investigate(q, annotated, budget=BUDGET)
                refs = inspected(plain)
                returns = dict(plain=refs, keyword=keyword(q, rows, len(refs)), guided=inspected(guided))
                scores = {k: len(set(targets).intersection(v)) for k, v in returns.items()}
                for k, score in scores.items():
                    totals[k] += score
                row = dict(case=case["id"], question=q, targets=targets, returns=returns,
                           scores=scores, collection_digest=plain["collection_digest"],
                           guided_digest=guided["collection_digest"])
                if traces:
                    row["reports"] = dict(plain=plain, guided=guided)
                results.append(row)
    return dict(profile="atlas-court-retrieval-v1", budget=BUDGET, trials=results,
                targets=sum(len(t["targets"]) for t in results), totals=totals)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--traces", action="store_true", help="include investigator quotations and audits")
    print(json.dumps(replay(parser.parse_args().traces), indent=2, ensure_ascii=False))

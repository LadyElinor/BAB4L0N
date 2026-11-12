"""One-shot HotpotQA evidence-retrieval comparison. The readers see no annotations."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from random import Random
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from babalon.contracts import Invalid
from babalon.inquiry import investigate
from scripts.court_trial import keyword, inspected

SHA = "4e9ecb5c8d3b719f624d66b60f8d56bf227f03914f5f0753d6fa1b359d7104ea"
CAP = 4
STRATEGIES = ("legacy", "shared", "shared-gap")


def materialize(context, directory):
    rows, refs = {}, {}
    for i, (title, sentences) in enumerate(context):
        name = f"p{i:02d}.txt"
        # Title is public context metadata; keep one independently graded unit per sentence.
        material = [" ".join((title + " | " + text).split()) for text in sentences]
        (directory / name).write_text("\n".join(material) + "\n", encoding="utf-8", newline="\n")
        for j, text in enumerate(material):
            ref = f"{name}#L{j + 1}"
            rows[ref] = text
            refs[title, j] = ref
    return rows, refs


def run_case(example, directory):
    rows, mapping = materialize(example["context"], directory)
    q = example["question"]
    ranking = keyword(q, rows, CAP)
    # Never let the lexical comparator be forced to pretend it read an extra passage.
    allowance = len(ranking)
    arms = {}
    for strategy in STRATEGIES:
        report = investigate(q, directory, budget=allowance, strategy=strategy)
        visits = inspected(report)
        spend = report["audit"]["inspections"]
        actual = visits if strategy == "legacy" else list(dict.fromkeys(visits))
        control = ranking[:spend]
        if len(actual) != spend or len(control) != spend:
            raise RuntimeError("unmatched spend")
        arms[strategy] = {"spend": spend, "refs": actual, "visits": len(visits), "keyword": control}
    # Decode gold only after all policies finish.
    gold = sorted({mapping[tuple(fact)] for fact in example["supporting_facts"]})
    if not gold:
        raise ValueError("empty gold")
    return {"id": example["_id"], "gold": gold, "arms": arms}


def summarize(cases, strategy):
    totals = Counter()
    diffs = []
    for case in cases:
        arm = case["arms"][strategy]
        gold = set(case["gold"])
        hits = len(gold.intersection(arm["refs"]))
        control_hits = len(gold.intersection(arm["keyword"]))
        win = int(hits == len(gold)) - int(control_hits == len(gold))
        totals.update({"spent_each": arm["spend"], "visits": arm["visits"], "gold": len(gold),
                       "hits": hits, "keyword_hits": control_hits, "complete": hits == len(gold),
                       "keyword_complete": control_hits == len(gold), "wins": win == 1,
                       "losses": win == -1, "ties": win == 0})
        diffs.append(win)
    n = totals["wins"] + totals["losses"]
    # Conditional exact sign test via a ratio of integers (no float overflow).
    k = min(totals["wins"], totals["losses"])
    tail = 1
    term = 1
    for i in range(1, k + 1):
        term = term * (n - i + 1) // i
        tail += term
    delta = sum(diffs) / len(diffs)
    # Bootstrap the ternary paired differences by sampling question indices.
    rng = Random(34119)
    samples = sorted(sum(rng.choices(diffs, k=len(diffs))) / len(diffs) for _ in range(2000))
    return {**totals, "full_set_delta": delta, "bootstrap_95": [samples[49], samples[1949]],
            "paired_p": min(1, (2 * tail) / (2 ** n))}


def run(input_path, output_path):
    raw = input_path.read_bytes()
    if sha256(raw).hexdigest() != SHA:
        raise ValueError("unexpected HotpotQA bytes")
    examples = json.loads(raw)
    if len(examples) != 7405 or len({ex["_id"] for ex in examples}) != len(examples):
        raise ValueError("unexpected development split")
    cases, exclusions = [], Counter()
    for ex in examples:
        with TemporaryDirectory() as d:
            try:
                case = run_case(ex, Path(d))
            except Invalid as e:
                exclusions[str(e)] += 1
                continue
            except KeyError as e:
                # Upstream references can point outside the supplied context.
                if isinstance(e.args[0], tuple):
                    exclusions["gold sentence absent from context"] += 1
                    continue
                raise
        cases.append(case)
    summary = {s: summarize(cases, s) for s in STRATEGIES}
    result = {"profile": "babalon.hotpot-retrieval.v1", "dataset_sha256": SHA, "total": len(examples),
              "evaluated": len(cases), "exclusions": dict(exclusions), "cap": CAP, "summary": summary}
    output_path.mkdir(exist_ok=True, parents=True)
    (output_path / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    (output_path / "pairs.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cases))
    print("TRIAL_SUMMARY " + json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    run(args.dataset, args.out)

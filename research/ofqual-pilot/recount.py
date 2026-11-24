"""Replay the public pilot, recount its returns and reproduce the two separate reviews."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from scripts import blind_inquiry as original
from scripts import blind_inquiry_coverage as coverage
from scripts import blind_inquiry_v2 as custody


def verify_sources(expected):
    manifest = HERE / "SHA256SUMS"
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != expected:
        raise ValueError("case manifest differs from deposit")
    for line in manifest.read_text().splitlines():
        digest, path = line.split("  ", 1)
        if hashlib.sha256((HERE / path).read_bytes()).hexdigest() != digest:
            raise ValueError(f"case file differs from deposit: {path}")


def recount():
    retained = custody.read(HERE / "deposits.json")
    verify_sources(retained["case_manifest_file_sha256"])
    frozen = custody.read(HERE / "freeze.json")
    sheet = custody.read(HERE / "worksheet.json")
    register = custody.read(HERE / "register.json")
    answers = custody.read(HERE / "answers.json")
    reviewers = retained["role_roster"]["reviewers"]
    reviews = [custody.read(HERE / f"{name}.json") for name in reviewers]
    if register["answer_digest"] != retained["answer_digest"] or register["key_digest"] != retained["key_digest"]:
        raise ValueError("register differs from the original deposits")
    if register["review_digests"] != retained["review_digests"] or set(reviewers) != set(register["review_digests"]):
        raise ValueError("review deposits differ from roster")
    if original.digest(sheet) != retained["worksheet_digest"] or answers["interpreter"] != retained["role_roster"]["interpreter"]:
        raise ValueError("worksheet or interpreter differs from deposit")
    result = custody.collect(sheet, HERE / "method-key.json", answers, HERE / "rubric.md",
                             frozen, retained["freeze_digest"], register, retained["register_digest"], reviews)
    packet = custody.read(HERE / "packet.json")
    _, replay = coverage.trial(packet, HERE / "documents", frozen, retained["freeze_digest"], bytes(32))
    by_method = {(row["id"], row["method"]): row for row in replay["rows"]}
    targets = {row["id"]: set(row["targets"]) for row in custody.read(HERE / "targets.json")["questions"]}
    decisions = {(r["id"], r["arm"]): r["decision"] for r in answers["rows"]}
    summaries = {}
    rows = []
    for row in result["rows"]:
        q, method = row["id"], row["method"]
        again = by_method[q, method]
        for field in ("matched_refs", "natural_refs", "matched_spend", "natural_spend"):
            if row[field] != again[field]:
                raise ValueError(f"changed reader result for {q} / {method} / {field}")
        hits = sorted(targets[q].intersection(row["matched_refs"]))
        summary = summaries.setdefault(method, {"totals": Counter(), "reviewers": {name: Counter() for name in reviewers}})
        totals = summary["totals"]
        totals["designated_hits"] += len(hits)
        totals["designated_targets"] += len(targets[q])
        totals["matched_passages"] += row["matched_spend"]
        totals["native_passages"] += row["natural_spend"]
        totals["answers"] += decisions[q, row["arm"]] == "answer"
        totals["abstentions"] += decisions[q, row["arm"]] == "abstain"
        totals["rows_with_disagreement"] += bool(row["disagreements"])
        for review in row["reviews"]:
            counts = summary["reviewers"][review["reviewer"]]
            for dimension, assessment in review["assessment"].items():
                counts[f"{dimension}/{assessment}"] += 1
        rows.append({"id": q, "method": method, "matched_spend": row["matched_spend"],
                     "hits": hits, "target_count": len(targets[q]), "decision": decisions[q, row["arm"]],
                     "disagreements": row["disagreements"]})
    for q in targets:
        cohort = [r for r in rows if r["id"] == q]
        if len(cohort) != len(coverage.ARMS) or len({r["matched_spend"] for r in cohort}) != 1:
            raise ValueError(f"unmatched passage spend for {q}")
    return {"scope": "one internal transfer pilot with AI interpretation and review", "status": result["status"],
            "promotion_eligible": result["promotion_eligible"], "collection_digest": original.digest(result),
            "arms": summaries, "rows": sorted(rows, key=lambda r: (r["id"], r["method"]))}


if __name__ == "__main__":
    print(json.dumps(recount(), indent=2, sort_keys=True))

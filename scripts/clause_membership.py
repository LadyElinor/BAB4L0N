"""Describe post-unblinding changes in order and membership from a saved ranking trace."""
from argparse import ArgumentParser
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.blind_inquiry_v2 import read
from scripts.clause_coverage import DEPTHS
from scripts.clause_coverage_scoring import method_id


def compare(rows):
    grouped = {}
    for row in rows:
        group = grouped.setdefault(row["id"], {})
        if row["method"] in group:
            raise ValueError("duplicate reader result")
        group[row["method"]] = row
    summary = {}
    for depth in DEPTHS:
        order_changes, membership_changes = [], []
        for qid, group in grouped.items():
            a, b = (group[method_id(m, depth)] for m in ("clause-coverage", "reciprocal-rank"))
            if a["matched_spend"] != b["matched_spend"] or a["pool_refs"] != b["pool_refs"]:
                raise ValueError("comparators differ in spend or candidate pool")
            if a["matched_refs"] != b["matched_refs"]:
                order_changes.append(qid)
            if set(a["matched_refs"]) != set(b["matched_refs"]):
                membership_changes.append(qid)
        summary[depth] = {"questions": len(grouped), "different_order_or_membership": sorted(order_changes),
                          "different_membership": sorted(membership_changes)}
    return summary


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path, help="disclosed method key or SciFact --rows trace")
    args = parser.parse_args()
    print(json.dumps(compare(read(args.trace)["rows"]), indent=2, sort_keys=True))

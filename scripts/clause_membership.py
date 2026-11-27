"""Describe post-unblinding changes in order and membership from a saved ranking trace."""
from argparse import ArgumentParser
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.blind_inquiry_v2 import read
from scripts.clause_coverage import DEPTHS, METHODS
from scripts.clause_coverage_scoring import method_id


CANDIDATE = "clause-coverage"
REFERENCES = tuple(m for m in METHODS if m != CANDIDATE)


def actual_return(row):
    """Validate each charged inspection before comparing passage IDs."""
    refs, pool = row["matched_refs"], row["pool_refs"]
    spend = row["matched_spend"]
    if not isinstance(refs, list) or not isinstance(pool, list) or type(spend) is not int:
        raise ValueError("expected passage lists and an integer matched spend")
    members, eligible = set(refs), set(pool)
    if len(refs) != spend or len(members) != spend or not members <= eligible:
        raise ValueError(f"{row['id']}/{row['method']}: actual distinct return disagrees with the charge or pool")
    return members, eligible


def compare(rows, reference="reciprocal-rank"):
    if reference not in REFERENCES:
        raise ValueError("unknown reference reader")
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
            candidate_id, reference_id = method_id(CANDIDATE, depth), method_id(reference, depth)
            if candidate_id not in group or reference_id not in group:
                raise ValueError(f"{qid}: missing {candidate_id} or {reference_id}")
            candidate_row, reference_row = group[candidate_id], group[reference_id]
            selected, pool = actual_return(candidate_row)
            compared, other_pool = actual_return(reference_row)
            if candidate_row["matched_spend"] != reference_row["matched_spend"] or pool != other_pool:
                raise ValueError("comparators differ in spend or candidate pool")
            if candidate_row["matched_refs"] != reference_row["matched_refs"]:
                order_changes.append(qid)
            if selected != compared:
                membership_changes.append(qid)
        summary[depth] = {"questions": len(grouped), "different_order_or_membership": sorted(order_changes),
                          "different_membership": sorted(membership_changes)}
    return summary


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path, help="disclosed method key or SciFact --rows trace")
    parser.add_argument("--reference", choices=REFERENCES, default="reciprocal-rank",
                        help="reader to compare with clause coverage (default: reciprocal-rank)")
    args = parser.parse_args()
    print(json.dumps(compare(read(args.trace)["rows"], args.reference), indent=2, sort_keys=True))

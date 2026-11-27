"""Rehearse within the cited abstracts of every SciFact development claim."""
from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import blind_inquiry as v1
from scripts.clause_coverage import run_question
from scripts.clause_coverage_scoring import records_for_question, score_returns

ARCHIVE = "11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be"
MEMBERS = {"data/claims_dev.jsonl": "86f0435d08fdb65d1aa41d1472684f57e6e71930626497bdf4d7a9ec1a632217",
           "data/corpus.jsonl": "b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62"}


def load(path):
    if sha256(path.read_bytes()).hexdigest() != ARCHIVE:
        raise ValueError("download differs from the preregistered SciFact archive")
    data = {}
    with tarfile.open(path) as archive:
        for name, pin in MEMBERS.items():
            raw = archive.extractfile(name).read()
            if sha256(raw).hexdigest() != pin:
                raise ValueError(f"changed SciFact member {name}")
            data[name] = [json.loads(line) for line in raw.splitlines()]
    return data


def rehearse(path, rows_path=None):
    data = load(path)
    corpus = {d["doc_id"]: d["abstract"] for d in data["data/corpus.jsonl"]}
    gold, rows = {}, []
    for claim in data["data/claims_dev.jsonl"]:
        qid = str(claim["id"])
        if qid in gold:
            raise ValueError("duplicate claim")
        # Scope is specified by the public input citation list before reading rationale labels.
        passages = {f"{doc}#S{i}": text for doc in claim["cited_doc_ids"]
                    for i, text in enumerate(corpus[doc])}
        runs = run_question(claim["claim"], passages)
        rows.extend(records_for_question(qid, runs))
        groups = []
        for doc in sorted(claim["evidence"], key=int):
            for sentences in sorted({tuple(sorted(e["sentences"])) for e in claim["evidence"][doc]}):
                group = [f"{doc}#S{i}" for i in sentences]
                if not group or not set(group) <= passages.keys():
                    raise ValueError("unavailable or empty annotated rationale")
                groups.append(group)
        stratum = "empty" if not groups else "requires-multiple" if min(map(len, groups)) > 1 else "single-suffices"
        gold[qid] = {"case": stratum, "groups": groups}
    result = score_returns(rows, gold)
    trace = {"rows": rows, "annotations": gold, "scores": result.pop("items")}
    if rows_path:
        v1.write(rows_path, trace)
    return {"profile": "public SciFact development, candidate documents supplied",
            "status": "NOT_PROMOTED", "promotion_eligible": False, "answer_review": None,
            "archive_sha256": ARCHIVE, "trace_digest": v1.digest(trace), "claim_count": len(gold),
            "alternative_group_questions": sum(len(q["groups"]) > 1 for q in gold.values()), **result}


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--rows", type=Path, help="write the complete per-claim trace to a new file")
    args = parser.parse_args()
    print(json.dumps(rehearse(args.archive, args.rows), indent=2, sort_keys=True))

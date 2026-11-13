"""Two-phase, restartable local policy selection trial. See RETRIEVAL_SELECTION.md."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from babalon.contracts import Invalid, canonical, digest
from babalon.inquiry import investigate
from babalon.retrieval_selection import FAMILY, BM25, rank, select, gate
from scripts.court_trial import keyword, inspected

SHA = {"propose": "3527663986b8295af4f7fcdff1ba1ff3f72d07d61a20f487cb238a6ef92fd955",
       "evaluate": "95aa6a52d5d6a735563366753ca50492a658031da74f301ac5238b03966972c9"}
LIMIT = {"propose": 128, "evaluate": 256}
VERSION = "babalon.squad-selection.v1"


def sample(raw, phase):
    candidates = []
    for article in json.loads(raw)["data"]:
        paragraphs = article["paragraphs"]
        if len(paragraphs) < 12:
            continue
        for index, paragraph in enumerate(paragraphs):
            for qa in paragraph["qas"]:
                candidates.append((sha256(qa["id"].encode()).digest(), qa["id"], qa["question"], paragraphs, index))
    for _, qid, question, paragraphs, index in sorted(candidates, key=lambda item: item[0])[:LIMIT[phase]]:
        # Distractors from the same article. Position depends on a hash rather than the label.
        order = sorted(range(len(paragraphs)), key=lambda j: sha256(f"{qid}:{j}".encode()).digest())
        chosen = sorted([index] + [j for j in order if j != index][:11], key=order.index)
        texts = [" ".join(paragraphs[j]["context"].split()) for j in chosen]
        yield qid, question, texts, chosen.index(index)


def score(qid, question, texts, target, configs):
    rows = {f"p{i:02}.txt#L1": text for i, text in enumerate(texts)}
    gold = f"p{target:02}.txt#L1"
    with TemporaryDirectory() as temp:
        directory = Path(temp)
        for ref, text in rows.items():
            (directory / ref.split("#")[0]).write_text(text, encoding="utf-8")
        keywords = keyword(question, rows, 4)
        bm25 = rank(question, rows, BM25, 4)
        report = investigate(question, directory, budget=min(len(keywords), len(bm25)), strategy="shared-gap")
    active = list(dict.fromkeys(inspected(report)))
    spend = report["audit"]["inspections"]
    if len(active) != spend or report["external_actions"] or report["authority_granted"]:
        raise RuntimeError("active policy audit failed")
    choices = [rank(question, rows, config, spend) for config in configs]
    for refs in [*choices, active, keywords[:spend], bm25[:spend]]:
        if len(set(refs)) != spend or not set(refs) <= rows.keys():
            raise RuntimeError("ranker scope or budget failure")
    return ({"id": qid, "target": gold, "spend": spend, "active": active,
             "keyword": keywords[:spend], "bm25": bm25[:spend]}, choices)


def calculate(raw, phase, proposal):
    configs = FAMILY if phase == "propose" else (tuple(proposal["candidate"]),)
    totals = [0] * len(configs)
    excluded = Counter()
    rows = []
    for qid, question, texts, target in sample(raw, phase):
        try:
            row, choices = score(qid, question, texts, target, configs)
        except Invalid as error:
            # Exclude only the existing passage-length admission limit. All other errors invalidate the run.
            if str(error) != "document line exceeds 2000 characters":
                raise
            excluded[str(error)] += 1
            continue
        for i, refs in enumerate(choices):
            totals[i] += row["target"] in refs
        if phase == "evaluate":
            row["candidate"] = choices[0]
        rows.append(row)
    if not rows or len(rows) + sum(excluded.values()) != LIMIT[phase]:
        raise RuntimeError("invalid evaluation population")
    base = {"version": VERSION, "phase": phase, "dataset_sha256": SHA[phase],
            "evaluated": len(rows), "excluded": dict(excluded), "spend_per_arm": sum(r["spend"] for r in rows)}
    if phase == "propose":
        return {**base, "candidate": select(totals), "family": FAMILY, "training_hits": totals,
                "question_ids": [r["id"] for r in rows]}
    if set(proposal["question_ids"]) & {r["id"] for r in rows}:
        raise RuntimeError("overlapping question IDs")
    return {**base, **gate(rows), "parent_policy": "shared-gap", "candidate": configs[0],
            "proposal_digest": digest(proposal), "rows": rows,
            "hits": {key: sum(r["target"] in r[key] for r in rows) for key in ("active","bm25","keyword","candidate")}}


def run(database, path, phase):
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != SHA[phase]:
        raise Invalid("dataset differs from the frozen split")
    conn = sqlite3.connect(database, timeout=60)
    try:
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("CREATE TABLE IF NOT EXISTS receipts(phase TEXT PRIMARY KEY, body TEXT NOT NULL)")
            saved = dict(conn.execute("SELECT phase,body FROM receipts"))
            if phase in saved:
                return json.loads(saved[phase])
            if phase == "evaluate" and "propose" not in saved:
                raise Invalid("commit a training proposal before evaluation")
            result = calculate(raw, phase, json.loads(saved["propose"]) if "propose" in saved else None)
            conn.execute("INSERT INTO receipts VALUES(?,?)", (phase, canonical(result)))
            return result
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=SHA)
    parser.add_argument("database", type=Path)
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.database, args.dataset, args.phase), sort_keys=True, indent=2))

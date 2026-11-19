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
VERSION = "babalon.squad-selection.v2"
ORDER_DOMAIN = "babalon.squad-selection.v2.presentation"
CLAIM_SCOPE = "public_replay_sensitivity_not_fresh_promotion"


def selected_paragraphs(qid, paragraph_count, target):
    """Preserve v1 membership, separate membership from presentation randomness."""
    membership_order = sorted(range(paragraph_count),
                              key=lambda j: sha256(f"{qid}:{j}".encode()).digest())
    selected = [target] + [j for j in membership_order if j != target][:11]
    return sorted(selected, key=lambda j: (
        sha256(f"{ORDER_DOMAIN}\0{qid}\0{j}".encode()).digest(), j))


def position_only(refs, spend, last_first=True):
    """No question, passage content or target; a fixed positional negative control."""
    order = sorted(refs)
    if last_first:
        order = order[-1:] + order[:-1]
    return order[:spend]



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
        # v1 used membership rank again for display, concentrating gold at the end.
        chosen = selected_paragraphs(qid, len(paragraphs), index)
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
             "keyword": keywords[:spend], "bm25": bm25[:spend],
             "position_last_first": position_only(tuple(rows), spend),
             "position_first": position_only(tuple(rows), spend, last_first=False)}, choices)


def calculate(raw, phase, proposal):
    configs = FAMILY if phase == "propose" else (tuple(proposal["candidate"]),)
    totals = [0] * len(configs)
    excluded = Counter()
    rows = []
    drawn_positions = Counter()
    for qid, question, texts, target in sample(raw, phase):
        drawn_positions[target] += 1
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
    positions = Counter(int(r["target"][1:3]) for r in rows)
    base = {"version": VERSION, "phase": phase, "dataset_sha256": SHA[phase],
            "claim_scope": CLAIM_SCOPE, "presentation_domain": ORDER_DOMAIN,
            "evaluated": len(rows), "excluded": dict(excluded),
            "spend_per_arm": sum(r["spend"] for r in rows),
            "gold_position_histogram": [positions[i] for i in range(12)],
            "drawn_gold_position_histogram": [drawn_positions[i] for i in range(12)],
            "position_control_hits": {key: sum(r["target"] in r[key] for r in rows)
                                      for key in ("position_last_first", "position_first")}}
    if phase == "propose":
        return {**base, "candidate": select(totals), "family": FAMILY, "training_hits": totals,
                "question_ids": [r["id"] for r in rows]}
    if set(proposal["question_ids"]) & {r["id"] for r in rows}:
        raise RuntimeError("overlapping question IDs")
    decision = gate(rows)
    return {**base, **decision, "gate_status": decision["status"],
            "status": "NOT_PROMOTED", "promotion_eligible": False,
            "parent_policy": "shared-gap", "candidate": configs[0],
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
            legacy = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='receipts'").fetchone()
            if legacy and conn.execute("SELECT 1 FROM receipts LIMIT 1").fetchone():
                raise Invalid("legacy trial database; preserve it and use a new v2 database")
            conn.execute("CREATE TABLE IF NOT EXISTS receipts_v2(phase TEXT PRIMARY KEY, body TEXT NOT NULL)")
            saved = dict(conn.execute("SELECT phase,body FROM receipts_v2"))
            if any(json.loads(body).get("version") != VERSION for body in saved.values()):
                raise Invalid("trial version mismatch; preserve the old database and use a new one")
            if phase in saved:
                return json.loads(saved[phase])
            if phase == "evaluate" and "propose" not in saved:
                raise Invalid("commit a training proposal before evaluation")
            result = calculate(raw, phase, json.loads(saved["propose"]) if "propose" in saved else None)
            conn.execute("INSERT INTO receipts_v2 VALUES(?,?)", (phase, canonical(result)))
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

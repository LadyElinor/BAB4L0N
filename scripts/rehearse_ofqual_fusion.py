"""Replay the exposed Ofqual rankings and score bounded selections. Writes JSON to stdout."""
from collections import Counter
from cProfile import Profile
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from babalon import inquiry
from babalon.retrieval_selection import BM25, rank
from scripts import blind_inquiry as base
from scripts import blind_inquiry_coverage as coverage
from scripts import blind_inquiry_v2 as custody
from scripts import retrieval_fusion as fusion
from scripts.blind_inquiry_targets import load_targets
from scripts.court_trial import inspected, keyword

PILOT = ROOT / "research" / "ofqual-pilot"
PILOT_REVISION = "d4f5fbea74f9b2df381289587c17e5bd4e0efec9"
READOUT_SHA256 = "dba0f74888eb3c9b00851e35368a70f80ef8559f79610f50c479c72d7feda141"
COUNTERS = {"bm25": rank, "keyword": keyword, "role": inquiry._candidates, "gap": inquiry._gap_refs}


def verified_key():
    original = (PILOT / "readout.json").read_bytes()
    if base.digest_bytes(original) != READOUT_SHA256:
        raise ValueError("published Ofqual readout changed")
    replay = subprocess.check_output([sys.executable, str(PILOT / "recount.py")])
    if replay != original:
        raise ValueError("historical recount differs from the published bytes")
    rows = custody.read(PILOT / "method-key.json")["rows"]
    return {(row["id"], row["method"]): row for row in rows}


def measure(reader, *args):
    """Count actual ranking function calls, including calls inside the frozen clause reader."""
    profiler = Profile()
    result = profiler.runcall(reader, *args)
    calls = {entry.code: entry.callcount for entry in profiler.getstats()}
    return result, Counter({name: calls.get(fn.__code__, 0) for name, fn in COUNTERS.items()})


def shared_gap(question, directory, budget):
    report = inquiry.investigate(question, directory, budget=budget, strategy="shared-gap")
    refs = list(dict.fromkeys(inspected(report)))
    if len(refs) != report["audit"]["inspections"]:
        raise ValueError("shared-gap audit differs from distinct inspections")
    return refs


def check_return(refs, passages, spend):
    if len(refs) != spend or len(set(refs)) != spend or not set(refs) <= passages.keys():
        raise ValueError("unmatched, duplicate or unknown passage inspection")


def retrieve(packet, directory, passages, key):
    questions = {}
    cap = packet["budget"]
    for item in packet["questions"]:
        qid, query = item["id"], item["question"]
        refs, calls = {}, {}
        readers = {
            "keyword": (keyword, (query, passages, cap)),
            "bm25": (rank, (query, passages, BM25, cap)),
            "clause-bm25": (coverage.clause_rank, (query, passages, cap)),
            "shared-gap": (shared_gap, (query, directory, cap)),
        }
        for method, (reader, args) in readers.items():
            refs[method], calls[method] = measure(reader, *args)
            record = key[qid, method]
            for phase in ("natural", "matched"):
                if record[phase + "_refs"] != refs[method] or record[phase + "_spend"] != cap:
                    raise ValueError(f"{qid}/{method} differs from the disclosed {phase} run")
        fixed, clause = refs["bm25"], refs["clause-bm25"]
        for method in fusion.METHODS:
            refs[method] = fusion.select(method, fixed, clause, packet["families"], cap)
            # Each standalone fusion requires both input rankings. The replay shares them.
            calls[method] = Counter(calls["bm25"])
            calls[method].update(calls["clause-bm25"])

        arms = {}
        for method, ranked in refs.items():
            check_return(ranked, passages, cap)
            # Materialize only selected passages as the evidence return. Ranking the
            # searchable corpus and examining ID lists are separate from this handoff.
            returned = {ref: passages[ref] for ref in ranked}
            arms[method] = {"refs": list(returned), "inspections": len(returned),
                            "ranking_calls": dict(calls[method]),
                            "fusion_input_slots": len(fixed) + len(clause) if method in fusion.METHODS else 0}
        questions[qid] = {"pool": sorted(set(fixed) | set(clause)), "methods": arms}
    return questions


def score(refs, targets):
    hits = sorted(targets.intersection(refs))
    return {"hits": hits, "complete": targets <= set(refs) if targets else None}


def summarize(questions, targets, cap):
    totals = {}
    for qid, item in questions.items():
        gold = targets[qid]
        item["targets"] = sorted(gold)
        item["pool_complete_within_budget"] = (gold <= set(item["pool"]) and len(gold) <= cap) if gold else None
        for method, row in item["methods"].items():
            row.update(score(row["refs"], gold))
            counts = totals.setdefault(method, {"inspections": 0, "complete": 0, "hits": 0,
                                                 "ranking_calls": Counter(), "fusion_input_slots": 0})
            counts["inspections"] += row["inspections"]
            counts["complete"] += row["complete"] is True
            counts["hits"] += len(row["hits"])
            counts["ranking_calls"].update(row["ranking_calls"])
            counts["fusion_input_slots"] += row["fusion_input_slots"]
    for method, counts in totals.items():
        changes = {"gained": [], "lost": []}
        for qid, item in questions.items():
            fixed = item["methods"]["bm25"]["complete"]
            selected = item["methods"][method]["complete"]
            if fixed != selected:
                changes["gained" if selected else "lost"].append(qid)
        counts["complete_changes_vs_fixed"] = changes
    return totals


def replay():
    key = verified_key()
    packet = custody.read(PILOT / "packet.json")
    directory = PILOT / "documents"
    indexed, _ = inquiry._index(directory)
    passages = {ref: row["text"] for ref, row in indexed.items()}
    questions = retrieve(packet, directory, passages, key)
    # The selectors never receive targets, judgments, the question ID or passage bodies.
    targets = load_targets(PILOT / "targets.json", custody.read(PILOT / "deposits.json")["targets_file_sha256"],
                           {"rows": packet["questions"]}, passages)
    totals = summarize(questions, targets, packet["budget"])
    return {"scope": "retrospective exposed Ofqual development", "status": "NOT_PROMOTED",
            "promotion_eligible": False, "fusion_answer_review": None,
            "pilot_revision": PILOT_REVISION, "historical_readout_sha256": READOUT_SHA256,
            "per_question_budget": packet["budget"], "corpus_passages": len(passages),
            "target_bearing_questions": sum(bool(gold) for gold in targets.values()),
            "target_references": sum(map(len, targets.values())), "totals": totals, "questions": questions}


if __name__ == "__main__":
    print(json.dumps(replay(), indent=2, sort_keys=True))

"""Replay candidate depths on the disclosed Ofqual case at the original inspection spend."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from babalon.inquiry import _index
from scripts import rehearse_ofqual_fusion as original
from scripts import retrieval_fusion
from scripts.blind_inquiry_v2 import read
from scripts.clause_coverage import evidence_score, rank_views

DEPTHS = (4, 5, 8, 10)
READERS = ("bm25", "clause-bm25", *retrieval_fusion.METHODS)


def at_depth(depth, packet, passages, historical):
    budget = packet["budget"]
    totals = {m: {"complete_questions": [], "exact_hits": 0, "inspections": 0, "bm25_calls": 0}
              for m in READERS}
    questions = {}
    attainable = []
    for item in packet["questions"]:
        qid = item["id"]
        views = rank_views(item["question"], passages, depth)
        pool = sorted(set(views.full) | set(views.clause))
        selected = {"bm25": views.full[:budget], "clause-bm25": views.clause[:budget]}
        for method in retrieval_fusion.METHODS:
            selected[method] = retrieval_fusion.select(method, views.full, views.clause, packet["families"], budget)

        # Read designated evidence only after selecting every return for this question.
        old = historical["questions"][qid]
        targets = old["targets"]
        groups = [targets] if targets else []
        scores = {m: evidence_score(refs, pool, groups, budget) for m, refs in selected.items()}
        results = {}
        for method, refs in selected.items():
            if depth == budget and refs != old["methods"][method]["refs"]:
                raise ValueError(f"depth-{budget} return differs from the published {qid}/{method}")
            score = scores[method]
            counts = totals[method]
            if score["complete"]:
                counts["complete_questions"].append(qid)
            counts["exact_hits"] += len(score["canonical_hits"])
            counts["inspections"] += len(refs)
            counts["bm25_calls"] += 1 if method == "bm25" else views.calls
            results[method] = {"refs": refs, "hits": score["canonical_hits"], "complete": score["complete"]}

        pool_complete = scores["bm25"]["pool_complete"]
        if pool_complete:
            attainable.append(qid)
        questions[qid] = {"fixed_list": views.full, "clause_list": views.clause, "targets": targets,
                          "pool_complete": pool_complete, "returns": results}
    return {"attainable_questions": attainable, "readers": totals, "questions": questions}


def replay():
    historical = original.replay()
    published = read(ROOT / "reports/ofqual-fusion-development.json")
    if historical != published:
        raise ValueError("original fusion receipt differs from its published replay")
    packet = read(original.PILOT / "packet.json")
    indexed, _ = _index(original.PILOT / "documents")
    passages = {ref: p["text"] for ref, p in indexed.items()}
    return {"scope": "post-hoc sensitivity on the exposed Ofqual packet", "status": "NOT_PROMOTED",
            "promotion_eligible": False, "new_answer_review": None, "reference": "bm25",
            "pilot_revision": historical["pilot_revision"], "per_question_budget": packet["budget"],
            "target_bearing_questions": historical["target_bearing_questions"],
            "target_references": historical["target_references"],
            "by_depth": {d: at_depth(d, packet, passages, historical) for d in DEPTHS}}


if __name__ == "__main__":
    print(json.dumps(replay(), indent=2, sort_keys=True))

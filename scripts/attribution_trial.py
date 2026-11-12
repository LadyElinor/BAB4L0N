"""Offline paired follow-up. Run from a checkout with the last-credit extra installed."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from babalon.contracts import Invalid, canonical, digest, parse_json
from babalon.evidence_session import EvidenceSession
from babalon.last_credit.grade import grade
from babalon.last_credit.study import draw

DATA = ROOT / "examples" / "attribution-study"
LEGACY = ROOT / "babalon" / "last_credit" / "policy.js"
PACK = "8f8735b413f29ce8bf4bde97c1062e2d19ff29854d6af8f9acd884317db24f70"
SOURCE_DATA = "8da095a819af6db3c14877c6df2d4d29960e41d1a63dd1fa853507bd2a616af5"
EXTERNAL_SHA = "f853d3a67d0f486c7545a439e93e47f95b54ce1046a3c8d5447eec55b12c2b81"
ARMS = ("legacy", "source_bound")


def external_pack(original):
    raw = Path(original).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_DATA:
        raise Invalid("TAT-QA development file differs from the pinned revision")
    questions = [q for group in json.loads(raw) for q in group["questions"]]
    selected = []
    for label in ("text", "table"):
        eligible = [q for q in questions if q["answer_from"] == label]
        eligible.sort(key=lambda q: hashlib.sha256(("babalon-attribution-v1/" + q["uid"]).encode()).digest())
        selected.extend({"uid": q["uid"], "question": q["question"], "source": label} for q in eligible[:16])
    return sorted(selected, key=lambda q: q["uid"])


def worker():
    from babalon.last_credit.worker import guest_context
    data = sys.stdin.buffer.read(16385)
    if len(data) > 16384:
        raise Invalid("oversized brief")
    mode, arm, payload = parse_json(data.decode())
    ctx = guest_context()
    ctx.eval(LEGACY.read_text(encoding="utf-8"))
    if arm == "source_bound":
        ctx.eval((DATA / "citation.js").read_text(encoding="utf-8"))
    if mode == "route":
        output = ctx.get("classify" if arm == "legacy" else "requestedSource")(payload)
    else:
        output = parse_json(ctx.get("propose" if arm == "legacy" else "citedAnswer")(canonical(payload)))
    response = canonical(output)
    if len(response.encode()) > 4096:
        raise Invalid("oversized proposal")
    print(response)


def propose(mode, arm, payload):
    with tempfile.TemporaryDirectory() as cwd:
        run = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--worker"],
                             input=canonical([mode, arm, payload]), cwd=cwd, env={},
                             capture_output=True, text=True, timeout=3)
    if run.returncode:
        raise RuntimeError("guest failed; install the last-credit extra and check the guest sources")
    return parse_json(run.stdout)


def contrast_cases():
    base = draw("review-source-contrast")["cases"][0]
    cases = []
    for goal, wording in (("summary", "what the summary claimed"), ("journal", "what the event tally shows")):
        for count in (2, 4):
            case = {**base, "question": wording, "goal": goal, "permitted": True,
                    "summary": {**base["summary"], "id": "summary-contrast", "batch": base["current_batch"],
                                "measurement": "author_estimate", "reported_misses": 2},
                    "pair": goal + "-review", "packet": {**base["packet"], "jobs": [
                        {"arrived": i, "completed": i+1 if i <= count else i} for i in range(1, 7)]}}
            cases.append(case)
    return cases


def trials(cases, directory):
    rows = []
    for index, case in enumerate(cases):
        packet = directory / f"{index}.json"
        packet.write_text(canonical(case["packet"]), encoding="utf-8")
        brief = {k: case[k] for k in ("question", "current_batch", "summary", "protocol_card")}
        # Host random access is fixed by design. The guest has no inspection tool in this trial.
        brief["can_inspect"] = False
        for purchase in (0, 1):
            session = EvidenceSession.create_last_credit(directory / f"{index}-{purchase}.sqlite",
                                                         packet, case["permitted"])
            read = session.inspect("matched-exposure", "timing") if purchase else None
            for arm in ARMS:
                final = propose("answer", arm, {"brief": brief, "receipt": read, "arm": "never"})
                if not isinstance(final, dict) or final.get("action") not in ("answer", "abstain"):
                    raise Invalid("guest failed to return a final answer")
                score = grade(case, final, read)
                wrong_source = (final["action"] == "answer" and case["goal"] in ("journal", "summary", "protocol")
                                and final["basis"] != case["goal"])
                rows.append({"case": index, "pair": case["pair"], "goal": case["goal"],
                             "question": case["question"], "purchase": purchase, "arm": arm,
                             "charged": read["charged"] if read else 0,
                             "read_status": read["status"] if read else None,
                             "read_id": read["receipt_id"] if read else None, "answer": final,
                             "wrong_source": wrong_source, **score})
    return rows


def summarize(rows):
    output = {}
    for arm in ARMS:
        for purchase in (0, 1):
            group = [r for r in rows if r["arm"] == arm and r["purchase"] == purchase]
            output[f"{arm}/{purchase}"] = {
                "n": len(group), **{key: sum(r[key] for r in group)
                                   for key in ("charged", "wrong_source", "handoff_correct", "obligation_preserved")},
                "outcomes": dict(Counter(r["outcome"] for r in group))}
    return output


def run():
    pack = draw("github-run-43250525790")
    if digest(pack) != PACK:
        raise Invalid("original last-credit pack changed")
    all_rows = {}
    with tempfile.TemporaryDirectory() as temp:
        for name, cases in [("original", pack["cases"]), ("review_contrast", contrast_cases())]:
            directory = Path(temp) / name
            directory.mkdir()
            rows = trials(cases, directory)
            all_rows[name] = {"totals": summarize(rows), "rows": rows}
    external_bytes = (DATA / "external-questions.json").read_bytes()
    if hashlib.sha256(external_bytes).hexdigest() != EXTERNAL_SHA:
        raise Invalid("external question pack differs from the frozen bytes")
    external = json.loads(external_bytes)
    predictions = []
    for q in external:
        for arm in ARMS:
            basis = propose("route", arm, q["question"])
            prediction = {"summary": "text", "journal": "table"}.get(basis, "unmapped")
            predictions.append({"uid": q["uid"], "arm": arm, "basis": basis, "prediction": prediction,
                                "source": q["source"], "correct": prediction == q["source"]})
    return {"profile": "babalon.citation-discipline.v1", "original_pack": PACK, **all_rows,
            "external": {"pack_digest": digest(external), "predictions": predictions,
                         "correct": {arm: sum(r["correct"] for r in predictions if r["arm"] == arm)
                                     for arm in ARMS}}, "language_model_calls": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    flags = parser.add_mutually_exclusive_group()
    flags.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    flags.add_argument("--extract-external", metavar="TATQA_DEV_JSON")
    args = parser.parse_args()
    if args.worker:
        worker()
    else:
        report = external_pack(args.extract_external) if args.extract_external else run()
        print(json.dumps(report, sort_keys=True, indent=2))

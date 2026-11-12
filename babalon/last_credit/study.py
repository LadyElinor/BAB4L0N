"""One-credit paired evaluation with an isolated proposal worker and a durable host."""
from collections import Counter
import hashlib
import importlib.metadata
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

from ..contracts import Invalid, canonical, digest, fields, parse_json
from ..evidence_session import EvidenceSession
from .cases import generate, validate_cases
from .grade import grade


HERE = Path(__file__).resolve().parent
ARMS = ("always", "never", "keyword", "learned")


def propose(brief, arm, receipt):
    payload = canonical({"brief": brief, "arm": arm, "receipt": receipt})
    with tempfile.TemporaryDirectory() as cwd:
        run = subprocess.run([sys.executable, "-I", str(HERE / "worker.py")], input=payload,
                             cwd=cwd, env={}, capture_output=True, text=True, timeout=3)
    if run.returncode:
        raise Invalid("worker exited without a valid response")
    proposal = parse_json(run.stdout)
    if type(proposal) is not dict:
        raise Invalid("invalid proposal")
    if proposal.get("action") == "inspect":
        fields(proposal, {"action", "view"})
        if type(proposal["view"]) is not str:
            raise Invalid("invalid inspection view")
    else:
        fields(proposal, {"action", "basis", "value", "citation", "objection", "fresh_observation"})
        if proposal["action"] not in ("answer", "abstain") or proposal["basis"] not in ("summary", "protocol", "journal"):
            raise Invalid("invalid answer")
        if proposal["action"] == "abstain" and (proposal["value"] is not None or proposal["citation"] is not None):
            raise Invalid("abstention with asserted evidence")
    return proposal


def run_arm(case, arm, path):
    session = EvidenceSession.create_last_credit(path / (arm + ".sqlite"), path / "packet.json", case["permitted"])
    state = session.observe()
    brief = {k: case[k] for k in ("question", "current_batch", "summary", "protocol_card")}
    brief["can_inspect"] = "timing" in state["views"] and state["remaining_inspections"] == 1
    start = time.monotonic()
    proposals = 1
    first = final = None
    receipt = None
    try:
        first = propose(brief, arm, None)
        final = first
        if first["action"] == "inspect":
            receipt = session.inspect("last-read", first["view"])
            updated = session.observe()
            brief = {**brief, "can_inspect": "timing" in updated["views"] and updated["remaining_inspections"] > 0}
            proposals += 1
            final = propose(brief, arm, receipt)
            if final["action"] == "inspect":
                raise Invalid("proposal limit exceeded")
        score = grade(case, final, receipt)
    except (Invalid, subprocess.TimeoutExpired) as exc:
        score = {"outcome": "worker_failure", "obligation_preserved": False, "handoff_correct": False,
                 "failure_reason": "deadline" if isinstance(exc, subprocess.TimeoutExpired) else str(exc)}
    duration = round((time.monotonic() - start) * 1000)
    return {"arm": arm, "initial": first["action"] if first else None, "final": final, "receipt": receipt,
            "credits_used": state["remaining_inspections"] - session.observe()["remaining_inspections"],
            "proposals": proposals, "wall_ms": duration, **score}


def draw(seed=None):
    seed = secrets.token_hex(16) if seed is None else seed
    if type(seed) is not str or not 1 <= len(seed) <= 128:
        raise Invalid("invalid study seed")
    return {"profile": "babalon.last-credit-pack.v1", "seed": seed, "cases": generate(seed)}


def run_study(pack, commitment):
    fields(pack, {"profile", "seed", "cases"})
    if pack["profile"] != "babalon.last-credit-pack.v1" or digest(pack) != commitment:
        raise Invalid("case pack differs from its committed identity")
    cases = pack["cases"]
    validate_cases(cases)
    try:
        runtime = importlib.metadata.version("quickjs")
    except importlib.metadata.PackageNotFoundError as exc:
        raise Invalid("install the last-credit extra to run the QuickJS proposer") from exc
    if runtime != "1.19.4":
        raise Invalid("this frozen experiment requires quickjs==1.19.4")
    counters = ("worker_failure", "supported_answer", "justified_abstention", "avoidable_abstention", "unjustified_abstention", "unsupported_answer",
                "handoff_correct", "obligation_preserved", "credits_used", "denied_requests",
                "disclosures", "outside_grant_disclosures", "proposals", "wall_ms")
    totals = {arm: Counter(dict.fromkeys(counters, 0)) for arm in ARMS}
    rows = []
    with tempfile.TemporaryDirectory() as root:
        for index, case in enumerate(cases):
            path = Path(root) / str(index)
            path.mkdir()
            (path / "packet.json").write_text(canonical(case["packet"]), encoding="utf-8")
            for arm in ARMS:
                row = run_arm(case, arm, path)
                row.update(case=index, pair=case["pair"], goal=case["goal"])
                rows.append(row)
                counts = totals[arm]
                counts[row["outcome"]] += 1
                for key in ("handoff_correct", "obligation_preserved", "credits_used", "proposals", "wall_ms"):
                    counts[key] += row[key]
                counts["denied_requests"] += bool(row["receipt"] and row["receipt"]["status"] == "REFUSED")
                disclosed = bool(row["receipt"] and row["receipt"]["status"] == "REPORTED")
                counts["disclosures"] += disclosed
                counts["outside_grant_disclosures"] += disclosed and not case["permitted"]
    fingerprint = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        HERE / "policy.js", HERE / "worker.py", HERE / "cases.py", HERE / "grade.py", HERE / "study.py",
        HERE.parent / "peer_events.py", HERE.parent / "evidence_session.py")}
    return {"profile": "babalon.last-credit.v1", "seed": pack["seed"], "pack_digest": commitment, "case_count": len(cases),
            "cases_digest": digest(cases), "frozen_files": fingerprint, "quickjs": runtime,
            "custody": "same_author_generated_instances_guest_blinded", "language_model_calls": 0,
            "score_rule": "supported answer or justified abstention, with both obligations preserved",
            "totals": totals, "rows": rows}

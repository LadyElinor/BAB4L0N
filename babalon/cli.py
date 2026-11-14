"""Operator CLI; model output belongs only in `submit` proposal JSON."""
from __future__ import annotations
import argparse
import json
import sqlite3
import sys
from .agent import run
from .contracts import Invalid, MAX_JSON_BYTES, parse_json
from .host import Host

def read(path):
    with open(path, encoding="utf-8") as stream:
        return parse_json(stream.read(MAX_JSON_BYTES + 1))

def _optional_remedy_input(path):
    if path is None:
        return None, None
    try:
        record = read(path)
    except OSError:
        return None, "unreadable"
    except ValueError:
        return None, "malformed"
    return (record, None) if record is not None else (None, "malformed")

def main(argv=None):
    parser = argparse.ArgumentParser(description="Babalon bounded local agent scaffold")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="create instance with explicit operator grant")
    init.add_argument("database")
    init.add_argument("--tasks", required=True)
    init.add_argument("--grant", required=True)
    demo = sub.add_parser("demo", help="run an explicitly granted local fixture")
    demo.add_argument("database")
    sub.add_parser("improve-demo", help="run bounded fixture-policy improvement")
    from .handoff import VIEWS, handoff
    reader = sub.add_parser("handoff", help="inspect permitted views of a local Commonwealth summary")
    reader.add_argument("summary")
    reader.add_argument("--allow", nargs="*", choices=VIEWS, required=True)
    reader.add_argument("--max-inspections", type=int, required=True)
    checker = sub.add_parser("recount", help="compare summary claims with the pinned demo event export")
    checker.add_argument("summary")
    checker.add_argument("--events", help="local protocol-2 export")
    checker.add_argument("--allow", nargs="*", choices=VIEWS, required=True)
    oversight = sub.add_parser("oversight-review", help="check a proposal oversight packet against the pinned workshop journal")
    oversight.add_argument("packet")
    oversight.add_argument("--events", help="complete protocol-2 demo event export")
    instructions = sub.add_parser("oversight-study", help="compare five synthetic R1 decision records")
    instructions.add_argument("packet")
    from .recount import EVENT_COUNT
    oversight.add_argument("--through-seq", type=int, default=EVENT_COUNT - 1, help="inclusive cutoff; defaults to the full demo")
    successor = sub.add_parser("successor-review", help="verify a construction and update its dated standing")
    successor.add_argument("directory", help="directory containing the frozen evidence files")
    successor.add_argument("--candidate", help="JSON answer to grade on three independent fields")
    remedy = sub.add_parser("remedy-review", help="review an owed award and the institution's continuing duty")
    remedy.add_argument("case", help="local Commonwealth owed-assistance-1 packet")
    remedy.add_argument("--register", help="separate receiving-side snapshot")
    remedy.add_argument("--account", help="optional local record of what the person chose to share")
    remedy.add_argument("--questions", choices=("records", "invited"),
                        help="draft office questions; invited means the person has invited questions in this conversation")
    remedy.add_argument("--as-of", type=int, required=True, help="inclusive review tick")
    study = sub.add_parser("last-credit", help="draw or run the paired evidence inspection trial")
    phases = study.add_subparsers(dest="phase", required=True)
    draw = phases.add_parser("draw", help="write an operator-only case pack to stdout")
    draw.add_argument("--seed", help="reproducible draw; defaults to fresh system randomness")
    trial = phases.add_parser("run", help="run frozen arms against a committed pack")
    trial.add_argument("pack")
    trial.add_argument("--commitment", required=True)
    evidence = sub.add_parser("evidence", help="operate a durable local evidence session")
    actions = evidence.add_subparsers(dest="action", required=True)
    for action in ("init", "observe", "inspect", "revoke", "operator-receipt"):
        command = actions.add_parser(action)
        command.add_argument("database")
        if action == "init":
            command.add_argument("summary")
            command.add_argument("--allow", nargs="*", choices=VIEWS, required=True)
            command.add_argument("--max-inspections", type=int, required=True)
        if action in ("inspect", "operator-receipt"):
            command.add_argument("request_id")
        if action == "inspect":
            command.add_argument("view")
    for name in ("observe", "audit", "verify", "run", "submit", "stop", "note"):
        command = sub.add_parser(name)
        command.add_argument("database")
        if name == "run":
            command.add_argument("--max-cycles", type=int, default=32)
        elif name == "submit":
            command.add_argument("proposal")
        elif name == "stop":
            command.add_argument("--reason", default="operator_revoked")
        elif name == "note":
            command.add_argument("--text", required=True)
            command.add_argument("--kind", choices=("lesson", "objection"), default="lesson")
            command.add_argument("--evidence", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = Host.create(args.database, read(args.tasks), read(args.grant)).observe()
        elif args.command == "last-credit":
            from .last_credit.study import draw, run_study
            result = draw(args.seed) if args.phase == "draw" else run_study(read(args.pack), args.commitment)
        elif args.command == "successor-review":
            from .successor import review
            result = review(args.directory, read(args.candidate)) if args.candidate else review(args.directory)
        elif args.command == "remedy-review":
            from .remedy import review
            case = read(args.case)
            register, register_error = _optional_remedy_input(args.register)
            account, account_error = _optional_remedy_input(args.account)
            result = review(case, register, args.as_of, account=account)
            for section, problem in (("delivery", register_error), ("personal_outcome", account_error)):
                if problem:
                    result[section]["source_error"] = problem
                if problem == "malformed":
                    result["status"] = "DISAGREEMENT"
            if args.questions:
                from .remedy_questions import question_guide
                result["question_guide"] = question_guide(result, args.questions)
        elif args.command == "oversight-study":
            from .oversight_study import review_study
            result = review_study(read(args.packet))
        elif args.command == "oversight-review":
            from .oversight import review
            result = review(read(args.packet), args.events, args.through_seq)
        elif args.command == "recount":
            from .recount import recount
            result = recount(args.summary, args.events, args.allow)
        elif args.command == "evidence":
            from .evidence_session import EvidenceSession
            session = EvidenceSession(args.database)
            if args.action == "init":
                session = EvidenceSession.create(args.database, args.summary, args.allow, args.max_inspections)
                result = session.observe()
            elif args.action == "observe":
                result = session.observe()
            elif args.action == "inspect":
                result = session.inspect(args.request_id, args.view)
            elif args.action == "revoke":
                result = session.revoke()
            else:
                result = session.operator_receipt(args.request_id)
        elif args.command == "handoff":
            result = handoff(args.summary, args.allow, args.max_inspections)
        elif args.command == "improve-demo":
            from .improvement import demo
            result = demo()
        elif args.command == "demo":
            tasks = [
                {"id": "signed-readings", "objective": "sum_valid", "readings": [{"value": 10, "valid": True}, {"value": -3, "valid": True}, {"value": 99, "valid": False}]},
                {"id": "valid-count", "objective": "count_valid", "readings": [{"value": 0, "valid": True}, {"value": 8, "valid": False}]},
                {"id": "empty-valid-set", "objective": "max_valid", "readings": [{"value": 7, "valid": False}]},
            ]
            grant = {"allowed_tasks": [t["id"] for t in tasks], "allowed_operations": ["sum_valid", "count_valid", "max_valid"], "max_actions": 8, "max_effects": 3, "max_records": 6}
            result = run(Host.create(args.database, tasks, grant))
        else:
            host = Host(args.database)
            if args.command == "observe": result = host.observe()
            elif args.command == "submit": result = host.submit(read(args.proposal))
            elif args.command == "run": result = run(host, max_cycles=args.max_cycles)
            elif args.command == "audit": result = host.audit()
            elif args.command == "stop": result = host.stop(args.reason)
            elif args.command == "note": result = {"note_id": host.note(args.text, args.evidence, args.kind)}
            else: result = host.verify()
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        status = result.get("status", result.get("disposition"))
        if status in ("DISAGREEMENT", "INVALID_EXPORT", "INCONSISTENT", "AUDIT_FAILED", "INVALID_PROPOSAL"): return 2
        if status in ("PARTIAL", "UNAVAILABLE", "REFUSED", "STOPPED", "WAITING", "DECLINED", "CYCLE_LIMIT", "BUDGET_EXHAUSTED"): return 3
        return 0
    except (Invalid, OSError, sqlite3.Error, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "ERROR", "reason": str(exc)}), file=sys.stderr)
        return 2

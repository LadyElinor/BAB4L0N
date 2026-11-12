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
        if status in ("INCONSISTENT", "AUDIT_FAILED", "INVALID_PROPOSAL"): return 2
        if status in ("PARTIAL", "UNAVAILABLE", "REFUSED", "STOPPED", "WAITING", "DECLINED", "CYCLE_LIMIT", "BUDGET_EXHAUSTED"): return 3
        return 0
    except (Invalid, OSError, sqlite3.Error, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "ERROR", "reason": str(exc)}), file=sys.stderr)
        return 2

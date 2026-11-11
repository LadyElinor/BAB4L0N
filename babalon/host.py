"""Trusted local host. All effects and receipts share one SQLite transaction.

This is not a sandbox: Python callers and the database owner remain trusted.
"""
from __future__ import annotations

from contextlib import closing, contextmanager
import json
import os
from pathlib import Path
import sqlite3
from typing import Any
import uuid

from .contracts import (PROFILE, Invalid, canonical, digest, fields, grant_record,
                        proposal_record, prose, tasks_record)


def _tool(task: dict, operation: str) -> int | None:
    values = [row["value"] for row in task["readings"] if row["valid"]]
    if operation == "sum_valid":
        return sum(values)
    if operation == "count_valid":
        return len(values)
    if operation == "max_valid":
        return max(values) if values else None
    raise Invalid("unregistered tool")


def _check(task: dict, result: Any) -> bool:
    """Separate reduction implementation, still sharing specification and inputs."""
    total = count = 0
    maximum = None
    for row in task["readings"]:
        if row["valid"] is True:
            count += 1
            total += row["value"]
            if maximum is None or row["value"] > maximum:
                maximum = row["value"]
    expected = {"sum_valid": total, "count_valid": count, "max_valid": maximum}[task["objective"]]
    return type(result) is type(expected) and result == expected


class Host:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        if not self.path.is_file():
            raise Invalid("workshop does not exist; use init or demo")

    @classmethod
    def create(cls, path: str | Path, tasks: list[dict], grant: dict) -> "Host":
        # Round-trip makes the host independent of caller-owned mutable objects.
        tasks, grant = json.loads(canonical([tasks, grant]))
        tasks_record(tasks)
        grant_record(grant, {task["id"] for task in tasks})
        path = Path(path)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        created = os.fstat(fd)
        os.close(fd)
        state = {"profile": PROFILE, "instance": uuid.uuid4().hex,
                 "external_authority": "NONE", "revision": 0,
                 "grant": grant, "actions_used": 0, "effects_used": 0,
                 "records_used": 0, "stopped": None, "pending_audit": None,
                 "tasks": [{"input": task, "status": "pending", "output": None} for task in tasks],
                 "notes": []}
        try:
            with closing(sqlite3.connect(path)) as db, db:
                db.executescript("""
                    CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL);
                    CREATE TABLE events (seq INTEGER PRIMARY KEY, body TEXT NOT NULL, hash TEXT NOT NULL);
                    CREATE TABLE receipts (request_id TEXT PRIMARY KEY, proposal_hash TEXT NOT NULL,
                                           body TEXT NOT NULL);
                """)
                db.execute("INSERT INTO state VALUES (1, ?)", (canonical(state),))
                cls._event(db, state, "created", {"grant_digest": digest(grant)})
        except BaseException:
            # Only clean up the file created by this call, never an existing DB.
            # Abrupt process/power loss still requires operator recovery.
            try:
                current = path.stat()
                if (current.st_dev, current.st_ino) == (created.st_dev, created.st_ino):
                    path.unlink()
            except OSError:
                pass  # Preserve the original failure if cleanup is unavailable.
            raise
        return cls(path)

    @contextmanager
    def _connect(self):
        # mode=rw never creates a new DB if a caller deleted the original.
        with closing(sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=10)) as db:
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db

    @staticmethod
    def _state(db) -> dict:
        row = db.execute("SELECT body FROM state WHERE id=1").fetchone()
        if row is None:
            raise Invalid("missing host state")
        return json.loads(row[0])

    @staticmethod
    def _event(db, state, kind, payload):
        previous = db.execute("SELECT seq, hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        event = {"seq": previous[0] + 1 if previous else 1,
                 "previous": previous[1] if previous else None,
                 "kind": kind, "payload": payload, "state_digest": digest(state)}
        db.execute("INSERT INTO events VALUES (?, ?, ?)",
                   (event["seq"], canonical(event), digest(event)))

    @classmethod
    def _save(cls, db, state, kind, payload):
        state["revision"] += 1
        db.execute("UPDATE state SET body=? WHERE id=1", (canonical(state),))
        cls._event(db, state, kind, payload)

    def observe(self) -> dict:
        with self._connect() as db:
            state = self._state(db)
        # No credentials, hidden oracle, or ability to issue a grant enters the brief.
        return {"profile": PROFILE, "instance": state["instance"],
                "view_id": digest(state), "external_authority": "NONE",
                "revision": state["revision"], "tasks": state["tasks"],
                "notes": state["notes"], "grant": state["grant"],
                "remaining": {"actions": state["grant"]["max_actions"] - state["actions_used"],
                              "effects": state["grant"]["max_effects"] - state["effects_used"],
                              "records": state["grant"]["max_records"] - state["records_used"]},
                "stopped": state["stopped"], "pending_audit": state["pending_audit"]}

    def submit(self, proposal: dict) -> dict:
        proposal = json.loads(canonical(proposal))
        proposal_record(proposal)
        proposal_hash = digest(proposal)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self._state(db)
            previous = db.execute("SELECT proposal_hash, body FROM receipts WHERE request_id=?",
                                  (proposal["request_id"],)).fetchone()
            if previous:
                if previous[0] != proposal_hash:
                    raise Invalid("request id conflict; preserve the original intent")
                return json.loads(previous[1])  # Historical result, no new effect or grant.
            if state["actions_used"] >= state["grant"]["max_actions"]:
                return self._receipt(state, proposal, "REFUSED", "action_budget_exhausted", durable=False)
            reason = self._refusal(state, proposal)
            state["actions_used"] += 1
            if reason:
                receipt = self._receipt(state, proposal, "REFUSED", reason)
            elif proposal["kind"] == "wait":
                receipt = self._receipt(state, proposal, "WAITING", proposal["reason"])
            elif proposal["kind"] == "decline":
                state["stopped"] = "declined: " + proposal["reason"]
                receipt = self._receipt(state, proposal, "DECLINED", proposal["reason"])
            else:
                task = next(t for t in state["tasks"] if t["input"]["id"] == proposal["task_id"])
                output = _tool(task["input"], proposal["operation"])
                task.update(status="committed_unaudited", output=output)
                state["effects_used"] += 1
                state["records_used"] += len(task["input"]["readings"])
                state["pending_audit"] = proposal["request_id"]
                receipt = self._receipt(state, proposal, "EFFECT_COMMITTED", "audit_required")
                receipt["effect"] = {"task_id": proposal["task_id"], "operation": proposal["operation"],
                                     "input_digest": digest(task["input"]), "output": output}
            db.execute("INSERT INTO receipts VALUES (?, ?, ?)",
                       (proposal["request_id"], proposal_hash, canonical(receipt)))
            self._save(db, state, "proposal", {"proposal": proposal, "receipt": receipt})
            return receipt

    @staticmethod
    def _receipt(state, proposal, disposition, reason, durable=True):
        return {"profile": PROFILE, "instance": state["instance"],
                "request_id": proposal["request_id"], "proposal_hash": digest(proposal),
                "disposition": disposition, "reason": reason, "durable": durable,
                "external_authority": "NONE"}

    @staticmethod
    def _refusal(state, proposal):
        if proposal["instance"] != state["instance"]:
            return "wrong_instance"
        if proposal["view_id"] != digest(state):
            return "stale_observation"
        if state["stopped"] is not None:
            return "stopped"
        if state["pending_audit"] is not None:
            return "audit_required"
        if proposal["kind"] != "act":
            return None
        grant = state["grant"]
        task = next((t for t in state["tasks"] if t["input"]["id"] == proposal["task_id"]), None)
        if task is None or proposal["task_id"] not in grant["allowed_tasks"]:
            return "task_outside_grant"
        if proposal["operation"] not in grant["allowed_operations"]:
            return "operation_outside_grant"
        if task["status"] != "pending":
            return "task_already_committed"
        if proposal["operation"] != task["input"]["objective"]:
            return "operation_contract_mismatch"
        if state["effects_used"] >= grant["max_effects"]:
            return "effect_budget_exhausted"
        if state["records_used"] + len(task["input"]["readings"]) > grant["max_records"]:
            return "record_budget_exhausted"
        return None

    def audit(self) -> dict:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self._state(db)
            request_id = state["pending_audit"]
            if request_id is None:
                return {"status": "NO_PENDING_EFFECT", "external_authority": "NONE"}
            row = db.execute("SELECT body FROM receipts WHERE request_id=?", (request_id,)).fetchone()
            receipt = json.loads(row[0]) if row else {}
            effect = receipt.get("effect", {})
            task = next((t for t in state["tasks"] if t["input"]["id"] == effect.get("task_id")), None)
            correct = (task is not None and effect.get("input_digest") == digest(task["input"])
                       and type(effect.get("output")) is type(task["output"])
                       and effect.get("output") == task["output"]
                       and _check(task["input"], task["output"]))
            result = {"status": "AUDITED" if correct else "AUDIT_FAILED", "request_id": request_id,
                      "external_authority": "NONE"}
            if correct:
                task["status"] = "done"
                state["pending_audit"] = None
            else:
                state["stopped"] = "audit_failed"
                # Keep the unverified effect and open obligation visible.
            self._save(db, state, "audit", result)
            return result

    def stop(self, reason: str = "operator_revoked") -> dict:
        prose(reason)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self._state(db)
            if state["stopped"] is None:
                state["stopped"] = reason
                self._save(db, state, "stop", {"reason": reason})
            return {"status": "STOPPED", "reason": state["stopped"]}

    def note(self, text: str, evidence: list[str], kind: str = "lesson") -> str:
        """Operator-supplied memory is attributed, disputed, bounded and non-authorizing."""
        prose(text)
        if kind not in ("lesson", "objection"):
            raise Invalid("note kind must be lesson or objection")
        if type(evidence) is not list or len(evidence) > 32 or not all(type(e) is str for e in evidence):
            raise Invalid("expected at most 32 receipt references")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self._state(db)
            if len(state["notes"]) >= 64:
                raise Invalid("note limit reached")
            for request_id in evidence:
                if not db.execute("SELECT 1 FROM receipts WHERE request_id=?", (request_id,)).fetchone():
                    raise Invalid("unresolved evidence reference")
            note = {"kind": kind, "text": text, "evidence": evidence,
                    "origin": "operator_supplied_unverified", "authority": "NONE"}
            note["id"] = digest(note)
            if any(n["id"] == note["id"] for n in state["notes"]):
                return note["id"]
            state["notes"].append(note)
            self._save(db, state, "note", note)
            return note["id"]

    def verify(self) -> dict:
        """Inspect chain, stored receipts and outcomes, without granting authority."""
        errors = []
        with self._connect() as db:
            db.execute("BEGIN")
            state = self._state(db)
            events = db.execute("SELECT seq, body, hash FROM events ORDER BY seq").fetchall()
            receipts = {r[0]: (r[1], json.loads(r[2])) for r in
                        db.execute("SELECT request_id, proposal_hash, body FROM receipts")}
            previous = None
            proposal_events = {}
            for expected, (seq, body, stored_hash) in enumerate(events, 1):
                event = json.loads(body)
                if seq != expected or event.get("seq") != expected or event.get("previous") != previous or digest(event) != stored_hash:
                    errors.append("event_chain")
                previous = stored_hash
                if event.get("kind") == "proposal":
                    payload = event["payload"]
                    p, r = payload["proposal"], payload["receipt"]
                    proposal_events[p["request_id"]] = (digest(p), r)
            if not events or json.loads(events[-1][1])["state_digest"] != digest(state):
                errors.append("state_digest")
            if proposal_events != receipts:
                errors.append("receipt_binding")
            if len(proposal_events) != state["actions_used"]:
                errors.append("action_accounting")
            committed = [t for t in state["tasks"] if t["status"] != "pending"]
            if len(committed) != state["effects_used"]:
                errors.append("effect_accounting")
            if sum(len(t["input"]["readings"]) for t in committed) != state["records_used"]:
                errors.append("record_accounting")
            for task in committed:
                if not _check(task["input"], task["output"]):
                    errors.append("incorrect_output:" + task["input"]["id"])
            for field, cap in (("actions_used", "max_actions"), ("effects_used", "max_effects"), ("records_used", "max_records")):
                if not 0 <= state[field] <= state["grant"][cap]:
                    errors.append("budget:" + field)
            if state["external_authority"] != "NONE":
                errors.append("authority_scope")
        return {"status": "CONSISTENT" if not errors else "INCONSISTENT", "errors": sorted(set(errors)),
                "completed": not errors and state["pending_audit"] is None and all(t["status"] == "done" for t in state["tasks"]),
                "events": len(events), "external_authority": "NONE",
                "assurance": "local_consistency_only_not_authentication"}

"""One durable Commonwealth evidence grant per operator-owned SQLite database."""
from contextlib import closing, contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import uuid

from .contracts import Invalid, canonical, digest, label
from .peer_events import EVENT_PROJECTION, project_jobs
from .handoff import load_snapshot, project_view, validate_grant


PROFILE = "babalon.evidence-session.v1"
PROJECTION = "babalon.commonwealth-handoff.v1"


class EvidenceSession:
    def __init__(self, database):
        self.path = Path(database).resolve()

    @classmethod
    def create(cls, database, source, allowed, max_inspections):
        allowed = validate_grant(allowed, max_inspections)
        raw, _ = load_snapshot(source)
        return cls._create(database, raw, allowed, max_inspections, PROJECTION)

    @classmethod
    def create_last_credit(cls, database, event_file, permitted):
        """Freeze the event packet and give this session one inspection credit."""
        if type(permitted) is not bool:
            raise Invalid("expected boolean event access")
        raw, _ = load_snapshot(event_file)
        return cls._create(database, raw, ("timing",) if permitted else (), 1, EVENT_PROJECTION)

    @classmethod
    def _create(cls, database, raw, allowed, max_inspections, projection):
        path = Path(database)
        # Publish only a fully committed database; never replace an existing path.
        fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".babalon-evidence-")
        os.close(fd)
        try:
            with closing(sqlite3.connect(temporary)) as db, db:
                db.executescript("""
                    CREATE TABLE session (
                        singleton INTEGER PRIMARY KEY CHECK(singleton=1), profile TEXT NOT NULL,
                        session_id TEXT NOT NULL, projection TEXT NOT NULL, source_sha256 TEXT NOT NULL,
                        views TEXT NOT NULL, credits INTEGER NOT NULL, revoked_after INTEGER
                    );
                    CREATE TABLE snapshot (singleton INTEGER PRIMARY KEY CHECK(singleton=1), raw BLOB NOT NULL);
                    CREATE TABLE inspections (view TEXT PRIMARY KEY, result TEXT NOT NULL);
                    CREATE TABLE requests (seq INTEGER PRIMARY KEY, request_id TEXT UNIQUE NOT NULL,
                                           view TEXT NOT NULL, receipt TEXT NOT NULL);
                """)
                db.execute("INSERT INTO session VALUES (1,?,?,?,?,?,?,NULL)",
                           (PROFILE, uuid.uuid4().hex, projection, hashlib.sha256(raw).hexdigest(),
                            canonical(allowed), max_inspections))
                db.execute("INSERT INTO snapshot VALUES (1,?)", (raw,))
            os.link(temporary, path)
        finally:
            os.unlink(temporary)
        return cls(path)

    @contextmanager
    def _transaction(self, *, write):
        uri = self.path.as_uri() + ("?mode=rw" if write else "?mode=ro")
        with closing(sqlite3.connect(uri, uri=True, timeout=10)) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA synchronous=FULL")
            with db:
                db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                state = db.execute("SELECT * FROM session WHERE singleton=1").fetchone()
                if not state or state["profile"] != PROFILE or state["projection"] not in (PROJECTION, EVENT_PROJECTION):
                    raise Invalid("unsupported evidence session or projection")
                yield db, state

    def observe(self):
        with self._transaction(write=False) as (db, state):
            used = db.execute("SELECT count(*) FROM inspections").fetchone()[0]
            revoked = state["revoked_after"] is not None
            return {"session_id": state["session_id"], "revoked": revoked,
                    "views": [] if revoked else json.loads(state["views"]),
                    "remaining_inspections": 0 if revoked else state["credits"] - used}

    def revoke(self):
        with self._transaction(write=True) as (db, state):
            if state["revoked_after"] is None:
                db.execute("UPDATE session SET revoked_after=(SELECT count(*) FROM requests)")
        return {"status": "REVOKED", "session_id": state["session_id"]}

    @staticmethod
    def _with_evidence(db, receipt):
        if receipt["status"] in ("REPORTED", "UNAVAILABLE"):
            row = db.execute("SELECT result FROM inspections WHERE view=?", (receipt["view"],)).fetchone()
            result = json.loads(row[0])
            if digest(result) != receipt["result_digest"]:
                raise Invalid("stored evidence differs from the receipt")
            return {**receipt, "evidence": result}
        return receipt

    def operator_receipt(self, request_id):
        """Privileged historical lookup for a trusted local operator."""
        label(request_id)
        with self._transaction(write=False) as (db, _):
            row = db.execute("SELECT receipt FROM requests WHERE request_id=?", (request_id,)).fetchone()
            if row is None:
                raise Invalid("unknown evidence request")
            return self._with_evidence(db, json.loads(row[0]))

    def inspect(self, request_id, view):
        label(request_id)
        label(view)
        with self._transaction(write=True) as (db, state):
            previous = db.execute("SELECT view, receipt FROM requests WHERE request_id=?",
                                  (request_id,)).fetchone()
            if previous and previous["view"] != view:
                raise Invalid("request id conflict")
            if previous:
                receipt = json.loads(previous["receipt"])
            else:
                receipt = self._issue(db, state, request_id, view)
            if state["revoked_after"] is not None:
                return {"status": "REFUSED", "reason": "revoked", "receipt_id": receipt["receipt_id"],
                        "original_status": receipt["status"]}
            return self._with_evidence(db, receipt)

    @staticmethod
    def _inspect_granted(db, state, view):
        row = db.execute("SELECT result FROM inspections WHERE view=?", (view,)).fetchone()
        if row is not None:
            result = json.loads(row[0])
            return {"status": result["status"], "result_digest": digest(result), "charged": 0}

        used = db.execute("SELECT count(*) FROM inspections").fetchone()[0]
        if used >= state["credits"]:
            return {"status": "REFUSED", "reason": "inspection_budget_exhausted", "charged": 0}

        raw = db.execute("SELECT raw FROM snapshot WHERE singleton=1").fetchone()[0]
        if hashlib.sha256(raw).hexdigest() != state["source_sha256"]:
            raise Invalid("snapshot digest mismatch")
        projection = project_jobs if state["projection"] == EVENT_PROJECTION else project_view
        result = projection(json.loads(raw), state["source_sha256"], view)
        db.execute("INSERT INTO inspections VALUES (?,?)", (view, canonical(result)))
        return {"status": result["status"], "result_digest": digest(result), "charged": 1}

    def _issue(self, db, state, request_id, view):
        if state["revoked_after"] is not None:
            decision = {"status": "REFUSED", "reason": "revoked", "charged": 0}
        elif view not in json.loads(state["views"]):
            decision = {"status": "REFUSED", "reason": "outside_grant", "charged": 0}
        else:
            decision = self._inspect_granted(db, state, view)
        receipt = {"profile": PROFILE, "projection": state["projection"], "session_id": state["session_id"],
                   "request_id": request_id, "view": view, **decision}
        receipt["receipt_id"] = digest(receipt)
        db.execute("INSERT INTO requests (request_id, view, receipt) VALUES (?,?,?)",
                   (request_id, view, canonical(receipt)))
        return receipt

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest

from babalon.contracts import Invalid, digest
from babalon.evidence_session import EvidenceSession, PROJECTION
from babalon.handoff import handoff


ROOT = Path(__file__).resolve().parents[1]
PINNED = ROOT / "tests/fixtures/commonwealth/demo-summary.json"
PINNED_SHA = "2481fcd7c0ae84784c97d9e02d49c2992549c79747347a86d833ec27090ba8c1"


class EvidenceSessionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = Path(tmp.name) / "evidence.sqlite"
        self.source = Path(tmp.name) / "summary.json"
        self.source.write_bytes(PINNED.read_bytes())

    def create(self, credits=1, views=("timing", "advice")):
        return EvidenceSession.create(self.db, self.source, views, credits)

    def cli(self, *args, code=0):
        result = subprocess.run([sys.executable, "-m", "babalon", "evidence",
                                 args[0], str(self.db), *args[1:]], cwd=ROOT,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, code, result.stderr)
        return json.loads(result.stdout or result.stderr)

    def test_pinned_offline_regression(self):
        self.assertEqual(hashlib.sha256(PINNED.read_bytes()).hexdigest(), PINNED_SHA)
        original = handoff(self.source, ["timing", "advice"], 2)
        self.assertEqual(original["source"]["kind"], "pinned_exposed_fixture")
        session = self.create(2)
        timing = session.inspect("counts", "timing")["evidence"]
        advice = session.inspect("lesson", "advice")["evidence"]
        self.assertEqual(timing, original["results"]["timing"])
        self.assertEqual(advice, original["results"]["advice"])
        self.assertEqual(timing["facts"], {"peer_completions": 5, "peer_on_time_arrivals": 4,
                                           "peer_missed_deadlines": 1})
        facts = advice["facts"]
        self.assertEqual((facts["lesson"], facts["review_status"]), ("lesson-14", "DISPUTED"))
        self.assertIs(facts["requires_new_observation"], True)
        self.assertIs(facts["requires_review"], True)
        self.assertEqual([s["id"] for s in facts["open_objections"]], ["counterstory-16"])

    def test_source_replacement_and_removal(self):
        session = self.create(2)
        self.source.write_text("{}")
        self.assertEqual(session.inspect("a", "timing")["evidence"]["source_sha256"], PINNED_SHA)
        self.source.unlink()
        self.assertEqual(EvidenceSession(self.db).inspect("b", "advice")["status"], "REPORTED")

    def test_durable_cli_and_revoked_audiences(self):
        initial = self.cli("init", str(self.source), "--allow", "advice", "--max-inspections", "1")
        first = self.cli("inspect", "id1", "advice")
        self.assertEqual(first["session_id"], initial["session_id"])
        self.assertEqual(first["projection"], PROJECTION)
        self.assertEqual(first["charged"], 1)
        self.assertEqual(self.cli("inspect", "id1", "advice"), first)
        self.assertEqual(self.cli("observe")["remaining_inspections"], 0)
        self.assertEqual(self.cli("revoke"), self.cli("revoke"))
        replay = self.cli("inspect", "id1", "advice", code=3)
        self.assertEqual(replay, {"status": "REFUSED", "reason": "revoked",
                                  "receipt_id": first["receipt_id"], "original_status": "REPORTED"})
        fresh = self.cli("inspect", "id2", "advice", code=3)
        self.assertEqual(fresh["original_status"], "REFUSED")
        self.assertNotIn("evidence", fresh)
        self.assertEqual(self.cli("operator-receipt", "id1"), first)
        self.assertNotIn("evidence", self.cli("operator-receipt", "id2", code=3))
        self.assertEqual(self.cli("observe")["views"], [])

    def test_binding_conflicts_and_distinct_requests(self):
        session = self.create()
        first = session.inspect("key", "timing")
        second = session.inspect("new-key", "timing")
        self.assertEqual(second["charged"], 0)
        self.assertEqual(first["result_digest"], digest(first["evidence"]))
        self.assertNotEqual(first["receipt_id"], second["receipt_id"])
        other = EvidenceSession.create(self.db.with_suffix(".other"), self.source, ["timing"], 1)
        self.assertNotEqual(first["receipt_id"], other.inspect("key", "timing")["receipt_id"])
        with self.assertRaisesRegex(Invalid, "conflict"):
            session.inspect("key", "advice")
        self.assertEqual(session.operator_receipt("key"), first)
        with self.assertRaises(FileExistsError):
            self.create(2)
        self.assertEqual(session.observe()["remaining_inspections"], 0)

    def test_denials_and_unavailable_results_persist(self):
        self.source.write_text("{}")
        session = self.create(1, ["timing"])
        denied = session.inspect("no-scope", "advice")
        self.assertEqual(denied["reason"], "outside_grant")
        self.assertEqual(denied["charged"], 0)
        missing = session.inspect("bad-data", "timing")
        self.assertEqual(missing["status"], "UNAVAILABLE")
        self.assertEqual(missing["charged"], 1)
        reopened = EvidenceSession(self.db)
        self.assertEqual(reopened.inspect("no-scope", "advice"), denied)
        self.assertEqual(reopened.inspect("bad-data", "timing"), missing)

    def race(self, first, second):
        barrier = threading.Barrier(2, timeout=10)
        def start(fn):
            barrier.wait()
            return fn(EvidenceSession(self.db))
        with ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(start, fn) for fn in (first, second)]
            return [f.result(timeout=15) for f in futures]

    def test_concurrent_last_credit(self):
        self.create()
        a, b = self.race(lambda s: s.inspect("a", "timing"), lambda s: s.inspect("b", "advice"))
        self.assertEqual(sorted([a["status"], b["status"]]), ["REFUSED", "REPORTED"])
        self.assertEqual(a["charged"] + b["charged"], 1)
        for result in (a, b):
            self.assertEqual(EvidenceSession(self.db).operator_receipt(result["request_id"]), result)

    def test_concurrent_exact_retry(self):
        self.create()
        fn = lambda s: s.inspect("same", "advice")
        a, b = self.race(fn, fn)
        self.assertEqual(a, b)
        self.assertEqual(a["status"], "REPORTED")
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM requests").fetchone()[0], 1)

    def test_read_racing_revocation(self):
        session = self.create()
        result, _ = self.race(lambda s: s.inspect("r", "timing"), lambda s: s.revoke())
        with closing(sqlite3.connect(self.db)) as conn:
            cutoff = conn.execute("SELECT revoked_after FROM session").fetchone()[0]
        receipt = session.operator_receipt("r")
        if cutoff == 0:
            self.assertEqual(result["reason"], "revoked")
            self.assertEqual(receipt["charged"], 0)
            self.assertNotIn("evidence", receipt)
        else:
            self.assertEqual(cutoff, 1)
            self.assertEqual(result, receipt)
            self.assertEqual(result["status"], "REPORTED")
        self.assertNotIn("evidence", session.inspect("r", "timing"))

    def test_process_death_before_receipt_and_after_commit(self):
        session = self.create()
        # Kill a real child after SQLite inserted the charge, before the receipt.
        child = """
from contextlib import contextmanager
import os, sys
from babalon.evidence_session import EvidenceSession
class Interrupted(EvidenceSession):
    @contextmanager
    def _transaction(self, *, write):
        with super()._transaction(write=write) as (db, state):
            db.create_function("quit_now", 0, lambda: os._exit(71))
            db.execute("CREATE TEMP TRIGGER die BEFORE INSERT ON requests BEGIN SELECT quit_now(); END")
            yield db, state
Interrupted(sys.argv[1]).inspect("r", "timing")
"""
        def crash(code, expected):
            proc = subprocess.run([sys.executable, "-c", code, str(self.db)], cwd=ROOT, timeout=15)
            self.assertEqual(proc.returncode, expected)
        crash(child, 71)
        self.assertEqual(session.observe()["remaining_inspections"], 1)
        with self.assertRaisesRegex(Invalid, "unknown evidence request"):
            session.operator_receipt("r")
        # The child commits then dies before writing a response to its caller.
        crash("import sys,os; from babalon.evidence_session import EvidenceSession; "
              "EvidenceSession(sys.argv[1]).inspect('r','timing'); os._exit(72)", 72)
        original = session.operator_receipt("r")
        self.assertEqual(original["charged"], 1)
        self.assertEqual(session.inspect("r", "timing"), original)
        self.assertEqual(session.observe()["remaining_inspections"], 0)

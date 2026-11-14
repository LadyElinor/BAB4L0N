from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from babalon.cli import main
from babalon.oversight import review

FIX = Path(__file__).parent / "fixtures/commonwealth"
JOURNAL = FIX / "demo-events.json"
PACKET = FIX / "oversight-demo.json"


class OversightReviewTests(unittest.TestCase):
    def setUp(self):
        self.packet = json.loads(PACKET.read_bytes())

    def test_count_distinct_decisions_and_show_working_comparator(self):
        result = review(self.packet, JOURNAL)
        f = result["findings"]
        self.assertEqual(result["status"], "AGREEMENT")
        self.assertEqual((f["examined"], f["misses"], f["on_time"], f["outcome_unknown"]), (3, 1, 2, 0))
        self.assertEqual(f["comparisons"], [{"miss": "propose-2", "miss_seq": 5,
                                            "on_time_comparator": "propose-10", "comparator_seq": 13}])
        self.assertFalse(f["recurred_in_reviewed_episodes"])
        self.assertFalse(result["authority_granted"])
        self.assertEqual(f["source_families"], 1)

    def test_fabricated_receipt_scope_and_mental_state_are_not_repeated(self):
        variants = []
        for key, value in [("authority_granted", 0), ("intent", "PRIVATE ALLEGATION"),
                           ("through_seq", 6), ("extra", True)]:
            p = dict(self.packet)
            p[key] = value
            variants.append(p)
        p = deepcopy(self.packet)
        p["accounts"][0]["acknowledgments"][0]["actor"] = "keeper"
        variants.append(p)
        p = deepcopy(self.packet)
        p["episodes"][1]["observation"] = p["episodes"][0]["observation"]
        variants.append(p)
        for p in variants:
            with self.subTest(p=p):
                r = review(p, JOURNAL)
                self.assertEqual(r["status"], "DISAGREEMENT")
                self.assertIsNone(r["findings"])
                self.assertNotIn("PRIVATE ALLEGATION", str(r))

    def test_before_execution_gives_unknown_not_success_or_failure(self):
        # Expected head computed from the supplied recorded prefix, not from the reviewer.
        events = json.loads(JOURNAL.read_bytes())
        packet = dict(self.packet, through_seq=3, prefix_head=events[4]["previous"], accounts=[])
        packet["episodes"] = [dict(self.packet["episodes"][0], execution=None, observation=None)]
        f = review(packet, JOURNAL, 3)["findings"]
        self.assertEqual((f["examined"], f["outcome_unknown"], f["misses"], f["on_time"]), (1, 1, 0, 0))
        self.assertEqual(f["comparisons"], [])
        self.assertEqual(review(packet, JOURNAL)["status"], "DISAGREEMENT")

    def test_missing_or_tampered_event_export_does_not_emit_findings(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "journal.json"
            self.assertEqual(review(self.packet, path)["status"], "PARTIAL")
            events = json.loads(JOURNAL.read_bytes())
            events[7]["command"]["actor"] = "keeper"
            path.write_text(json.dumps(events), encoding="utf-8")
            report = review(self.packet, path)
            self.assertEqual(report["status"], "INVALID_EXPORT")
            self.assertIsNone(report["findings"])

    def test_cli_exit_codes(self):
        for options, status, code in [
            ([], "PARTIAL", 3), (["--events", str(JOURNAL)], "AGREEMENT", 0),
            (["--events", str(JOURNAL), "--through-seq", "4"], "DISAGREEMENT", 2),
        ]:
            out = StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(["oversight-review", str(PACKET), *options]), code)
            self.assertEqual(json.loads(out.getvalue())["status"], status)


class InstructionStudyTests(unittest.TestCase):
    def test_exception_evidence_and_interception_change_different_findings(self):
        from babalon.oversight_study import review_study
        study = json.loads((FIX / "oversight-instruction-study.json").read_bytes())
        report = review_study(study)
        self.assertEqual(report["qualifying"], ["prohibited-direction", "order-intercepted"])
        a, b, c, d, e = report["decisions"]
        self.assertEqual(a["report_origins"], ["anonymous-A"])
        self.assertEqual((a["conduct"], a["release_check"]), ("reported-only", "undetermined"))
        self.assertEqual(b["release_check"], "undetermined")
        self.assertEqual(c["release_check"], "clearance-before-release")
        self.assertEqual((d["conduct"], d["prior_exception_record"]), ("authorized-direction", "d1"))
        self.assertEqual(e["release_check"], "clearance-before-release")
        self.assertTrue(all(x["intent_to_harm"] == "not-established" for x in report["decisions"]))
        self.assertFalse(report["authority_granted"])
        study["coverage"]["written_exceptions"] = "incomplete"
        with self.assertRaises(ValueError):
            review_study(study)

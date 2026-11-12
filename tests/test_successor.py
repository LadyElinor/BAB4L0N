from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from babalon.contracts import Invalid
from babalon.successor import check_construction, review


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples/successor-review"
WITNESS = "9e824e9f8a92e74226231152fc8e8a972be5ba79549e2a10e512fe63a3934f49"
ANSWER = {
    "construction": {"lower_bound": 13026, "minimum_distance_at_least": 6, "witness_sha256": WITNESS},
    "standing": {"table_lower_bound": 13338, "as_of": "2026-11-12", "basis": "reported_table_entry",
                 "observation_sha256": "1c61ca1352319cfa282dd0dc870f23e547075b03b523e5998d10b7814510ea3c"},
    "credit": {"contributor": "Ryan Freel", "handle": "Freelsgood", "witness_sha256": WITNESS},
}


class SuccessorTests(unittest.TestCase):
    def test_real_inputs_and_dated_history(self):
        result = review(CASE, ANSWER)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["grades"], dict.fromkeys(ANSWER, "PASS"))
        evidence = result["evidence"]
        self.assertEqual(evidence["construction"]["distinct_eight_subsets"], 586170)
        self.assertEqual(evidence["credit"]["historical_note"]["date"], "2026-10-15")
        self.assertEqual(evidence["credit"]["historical_note"]["table_lower_bound_reported_by_maintainer"], 13026)
        self.assertEqual(evidence["standing"]["table_credit"], "Dz")

    def test_each_wrong_decision_fails_independently(self):
        for axis, change in (("standing", {"table_lower_bound": 13026}),
                             ("standing", {"basis": "independently_verified_optimum"}),
                             ("construction", {"lower_bound": 13338}),
                             ("credit", {"contributor": "Chris Dzoba"})):
            with self.subTest(axis=axis, change=change):
                candidate = deepcopy(ANSWER)
                candidate[axis].update(change)
                result = review(CASE, candidate)
                expected = dict.fromkeys(ANSWER, "PASS")
                expected[axis] = "FAIL"
                self.assertEqual(result["grades"], expected)
                self.assertEqual(result["status"], "DISAGREEMENT")

    def test_missing_or_corrupt_evidence_is_local_to_its_axis(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            shutil.copy(CASE / "submission.json", path)
            (path / "construction.txt.gz").write_bytes(b"unreadable construction")
            r = review(path, ANSWER)
            self.assertEqual(r["status"], "PARTIAL")
            self.assertEqual(r["grades"], {"standing": "UNGRADABLE", "construction": "UNGRADABLE", "credit": "PASS"})
            (path / "table-observation.json").write_text('{"lower_bound":99999}')
            self.assertIn("identity mismatch", review(path)["unavailable"]["standing"])

    def test_distance_check_boundary(self):
        def word(indices):
            return bytes(49 if i in indices else 48 for i in range(27))
        first = word(range(10))
        for shared in (7, 8, 9, 10):
            other = word(set(range(shared)) | set(range(10, 20-shared)))
            raw = first + b"\n" + other
            if shared == 7:
                self.assertEqual(check_construction(raw)["word_count"], 2)
            else:
                with self.assertRaises(Invalid):
                    check_construction(raw)
        for malformed in (b"", b"1" * 27, b"0" * 17 + b"1" * 9 + b"X", b"1" * 10):
            with self.assertRaises(Invalid):
                check_construction(malformed)

    def test_cli_candidate_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "answer.json"
            for answer, code in [(ANSWER, 0), ({"credit": ANSWER["credit"]}, 2), (None, 2)]:
                path.write_text(json.dumps(answer))
                p = subprocess.run([sys.executable, "-m", "babalon", "successor-review", str(CASE),
                                    "--candidate", str(path)], capture_output=True, cwd=ROOT)
                self.assertEqual(p.returncode, code, p.stderr)
                if answer is None:
                    self.assertEqual(json.loads(p.stderr)["status"], "ERROR")
                else:
                    self.assertEqual(json.loads(p.stdout)["grades"]["credit"], "PASS")

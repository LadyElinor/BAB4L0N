"""Check the entire disclosed blind run through the operator's offline entry point."""
from pathlib import Path
import subprocess
import sys
import unittest


class TransferReceiptTests(unittest.TestCase):
    def test_published_receipt_replays_byte_for_byte(self):
        root = Path(__file__).resolve().parents[1]
        run = root / "research/clause-transfer"
        replay = subprocess.check_output([sys.executable, str(root / "scripts/blind_clause_trial.py"),
                                          "recount", str(run / "case"), str(run), str(run / "deposits.json")])
        self.assertEqual(replay, (run / "result.json").read_bytes())

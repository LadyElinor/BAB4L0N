"""The disclosed pilot must replay from its frozen source and review deposits."""
import json
from pathlib import Path
import subprocess
import sys
import unittest


class OfqualPilotTest(unittest.TestCase):
    def test_published_readout_replays(self):
        pilot = Path(__file__).resolve().parents[1] / "research" / "ofqual-pilot"
        output = subprocess.check_output([sys.executable, str(pilot / "recount.py")])
        self.assertEqual(json.loads(output), json.loads((pilot / "readout.json").read_bytes()))

#!/usr/bin/env python3
"""Tests and end-to-end subprocess demos without installation or networking."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
env = dict(os.environ, PYTHONPATH=str(ROOT))
subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT, env=env, check=True)
with tempfile.TemporaryDirectory() as directory:
    db = str(Path(directory) / "demo.sqlite")
    for arguments in (("demo", db), ("verify", db), ("run", db), ("improve-demo",)):
        result = subprocess.run([sys.executable, "-m", "babalon", *arguments], cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        report = json.loads(result.stdout)
        expected = {"demo": "COMPLETED", "verify": "CONSISTENT", "run": "COMPLETED", "improve-demo": "PROMOTED"}[arguments[0]]
        if report["status"] != expected:
            raise RuntimeError(report)
        if arguments[0] == "verify" and not report["completed"]:
            raise RuntimeError("demo did not finish")
        if arguments[0] == "improve-demo" and (report["completed_before"], report["completed_after"]) != (1, 3):
            raise RuntimeError("unexpected improvement comparison")
print("PASS: tests and fresh-process demo, verify, restart, improvement")

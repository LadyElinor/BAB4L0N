"""Replay the frozen two-pass West Calumet public-record retrieval comparison."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.court_trial import ROOT, inspected, keyword
from babalon.inquiry import investigate


def replay():
    case = json.loads((ROOT / "examples/inquiry/west-calumet/case.json").read_text(encoding="utf-8"))
    passes = {}
    for stage, name in enumerate(("contemporaneous", "expanded"), 1):
        rows = {}
        targets = case["targets"][name]
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for doc in case["sources"]:
                if (doc["available"] <= case["cutoff"]) != (doc["pass"] == 1):
                    raise ValueError("source publication date contradicts assigned pass")
                if doc["pass"] > stage:
                    continue
                file = doc["file"]
                (directory / file).write_text("\n".join(doc["lines"]) + "\n", encoding="utf-8", newline="\n")
                for i, line in enumerate(doc["lines"], 1):
                    rows[f"{file}#L{i}"] = line
            if not set(targets.values()) <= rows.keys():
                raise ValueError("target unavailable in its pass")
            report = investigate(case["question"], directory, budget=case["budget"])
        runs = {}
        for arm, refs in (("babalon", inspected(report)), ("keyword", keyword(case["question"], rows, case["budget"]))):
            runs[arm] = {"inspections": refs, "credits": len(refs),
                         "hits": [key for key, ref in targets.items() if ref in refs],
                         "misses": [key for key, ref in targets.items() if ref not in refs]}
        passes[name] = {"files": len(report["documents"]), "candidate_passages": len(rows),
                        "collection_digest": report["collection_digest"], "arms": runs,
                        "worker_sources": {w["role"]: w["sources"] for rnd in report["rounds"] for w in rnd["returns"]}}
    return {"profile": "west-calumet-notice-v1", "question": case["question"], "budget_per_arm_per_pass": case["budget"],
            "case_freeze": "67a6894e5c7fe23101c39cb7922b290a21030d2c", "passes": passes}


if __name__ == "__main__":
    print(json.dumps(replay(), indent=2))

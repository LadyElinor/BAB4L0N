"""Export the offline GPT-4o inquiry to the Relay Atlas inquiry desk."""
from argparse import ArgumentParser
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from babalon.inquiry import investigate
from scripts.court_trial import inspected, keyword

CASE = ROOT / "examples/inquiry/ai-safety/gpt4o-sycophancy"


def build():
    spec = json.loads((CASE / "case.json").read_text(encoding="utf-8"))
    directory = CASE / "documents"
    records = spec["records"]
    docs = {p.name: p.read_bytes().decode("utf-8") for p in sorted(directory.iterdir())}
    if docs.keys() != records.keys():
        raise ValueError("The source register must cover every document")
    rows = {}
    links = {}
    for name, contents in docs.items():
        for i, line in enumerate(contents.splitlines(), 1):
            if line.strip():
                ref = f"{name}#L{i}"
                rows[ref] = line
                links[ref] = records[name][1]

    trials = []
    for task in spec["inquiries"]:
        question = task["question"]
        targets = task["targets"]
        if len(set(targets)) != 2 or not set(targets) <= rows.keys():
            raise ValueError("Each inquiry needs two distinct, registered target passages")
        eligible = keyword(question, rows, 4)
        report = investigate(question, directory, budget=len(eligible))
        spend = report["audit"]["inspections"]
        baseline = eligible[:spend]
        visits = inspected(report)
        if len(visits) != len(baseline) or spend != len(baseline):
            raise ValueError("Unequal actual passage spend")
        trials.append({"question": question, "targets": targets, "inspections_per_arm": spend,
                       "babalon": visits, "keyword": baseline})

    return {
        "id": spec["id"], "title": spec["title"], "question": spec["question"],
        "boundary": spec["boundary"], "docs": docs, "editor": {}, "links": links,
        "sources": list(records.values()), "labels": {k: v[0] for k, v in records.items()},
        "plainLabel": "Attributed source summaries", "tasks": [t["question"] for t in trials],
        "plain": investigate(spec["question"], directory, budget=12), "guided": None,
        "trials": trials,
    }


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--compact", action="store_true", help="emit compact Atlas JSON")
    compact = parser.parse_args().compact
    print(json.dumps(build(), ensure_ascii=False, indent=None if compact else 2,
                     separators=(",", ":") if compact else None))

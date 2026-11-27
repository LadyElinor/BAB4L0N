"""Time standalone ranking and selection under the registered warm-repetition protocol."""
from argparse import ArgumentParser
import json
from pathlib import Path
import platform
from statistics import median
import sys
from time import perf_counter_ns

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from babalon.inquiry import _index
from scripts.blind_inquiry_v2 import read
from scripts.clause_coverage import DEPTHS, METHODS, choose, rank_views, run_question
from scripts.clause_coverage_scoring import method_id


def measure(case):
    packet = read(case / "packet.json")
    passages = {ref: p["text"] for ref, p in _index(case / "documents")[0].items()}
    queries = []
    for q in packet["questions"]:
        rows = run_question(q["question"], passages)
        costs = {r["matched_spend"] for r in rows.values()}
        if len(costs) != 1:
            raise ValueError("unmatched timing cohort")
        queries.append((q["question"], costs.pop()))
    order = [(m, d) for d in DEPTHS for m in METHODS]
    samples = {method_id(m, d): [] for m, d in order}
    for rep in range(6):
        for m, d in order[rep:] + order[:rep]:
            start = perf_counter_ns()
            for q, cap in queries:
                inputs = rank_views(q, passages, d, fixed_only=(m == "bm25"))
                if len(choose(m, inputs, cap)) != cap:
                    raise ValueError("timed return has a different charge")
            elapsed = perf_counter_ns() - start
            if rep:
                samples[method_id(m, d)].append(elapsed)
    cpu = platform.machine()
    details = Path("/proc/cpuinfo")
    if details.exists():
        cpu = next((line.partition(":")[2].strip() for line in details.read_text().splitlines()
                    if line.startswith("model name")), cpu)
    return {"cpu": cpu, "platform": platform.platform(), "python": platform.python_version(),
            "questions": len(queries), "corpus_passages": len(passages), "packet_wall_ns": samples,
            "median_packet_ms": {m: median(values) / 1e6 for m, values in samples.items()}}


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    print(json.dumps(measure(parser.parse_args().case), indent=2, sort_keys=True))

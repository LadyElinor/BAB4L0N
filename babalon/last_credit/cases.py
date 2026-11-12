"""Operator-side generation. Only the explicit brief travels to the guest."""
import random

from ..contracts import Invalid, fields, integer, label, prose
from ..peer_events import EVENT_PROJECTION, project_jobs


QUESTIONS = {
    "journal": [
        "Did the count in the summary hold up? Give the timestamp-based total.",
        "Use the completion records to establish how many arrived late.",
        "What total do the arrival and finish times substantiate?",
        "Independently recount the missed deadlines.",
    ],
    "summary": [
        "What count did the summary give before anyone looked at the event log?",
        "Which figure was reported in the note?",
        "According to the written handoff, how many arrivals were late?",
        "Quote what the author said about missed deadlines.",
    ],
    "protocol": [
        "After the journal shows a cleared queue, what does reuse of the lesson require?",
        "Which obligation applies before a successor relies on this advice?",
        "What does the available rule say about fresh observation?",
        "Can these timestamps settle the requirement to check again?",
    ],
    "handoff": [
        "Which deadline figure can we carry forward for this batch?",
        "Give the best supported number for the current handoff.",
        "Which reliable total should the next worker use for this batch?",
        "Choose a supported count to carry forward.",
    ],
}


def generate(seed):
    rng = random.Random(seed)
    cases = []
    for goal, questions in QUESTIONS.items():
        for index, question in enumerate(questions):
            # Each pair has identical visible input. Its event histories can differ.
            batch = rng.randrange(10000, 100000)
            preview = rng.randrange(1, 5)
            current = index % 2 == 0
            measured = index != 2
            card = None if index in (1, 3) else {"id": "rule-v1", "fresh_observation": "required"}
            permitted = index != 3 or goal in ("protocol", "handoff")
            summary = {"id": f"summary-{batch}", "batch": batch if current else batch-1,
                       "measurement": "checked_recount" if measured else "author_estimate",
                       "reported_misses": None if goal == "summary" and index == 3 else preview,
                       "open_objection": f"objection-{rng.randrange(1000, 10000)}",
                       "author_claims_fresh_observation": bool(rng.randrange(2))}
            for twin in range(2):
                actual = preview if (current and measured) or twin == 0 else preview + 1
                n = rng.randint(7, 12)
                late = set(rng.sample(range(1, n), actual))
                rows = [{"arrived": i, "completed": i+1 if i in late else i} for i in range(1, n+1)]
                packet = {"profile": EVENT_PROJECTION, "jobs": rows}
                if twin == 1 and index == 3:
                    packet.pop("jobs")  # Inspection still incurs its one credit when granted.
                cases.append({"question": question, "goal": goal, "current_batch": batch,
                              "summary": summary.copy(), "protocol_card": card, "permitted": permitted,
                              "packet": packet, "pair": f"{goal}-{index}"})
    rng.shuffle(cases)
    return cases


def validate_cases(cases):
    if type(cases) is not list:
        raise Invalid("expected a case list")
    integer(len(cases), 1, 128)
    for case in cases:
        fields(case, {"question", "goal", "current_batch", "summary", "protocol_card",
                      "permitted", "packet", "pair"})
        prose(case["question"])
        label(case["pair"])
        integer(case["current_batch"], 0, 10**8)
        if case["goal"] not in QUESTIONS or type(case["permitted"]) is not bool:
            raise Invalid("invalid case goal or grant")
        summary = case["summary"]
        fields(summary, {"id", "batch", "reported_misses", "open_objection", "measurement",
                         "author_claims_fresh_observation"})
        label(summary["id"])
        label(summary["open_objection"])
        integer(summary["batch"], 0, 10**8)
        if summary["reported_misses"] is not None:
            integer(summary["reported_misses"], 0, 32)
        if (summary["measurement"] not in ("checked_recount", "author_estimate")
                or type(summary["author_claims_fresh_observation"]) is not bool):
            raise Invalid("invalid summary")
        card = case["protocol_card"]
        if card is not None:
            fields(card, {"id", "fresh_observation"})
            label(card["id"])
            if card["fresh_observation"] != "required":
                raise Invalid("unsupported protocol card")
        packet = case["packet"]
        if packet == {"profile": EVENT_PROJECTION}:
            continue  # Explicit missing record.
        projection = project_jobs(packet, "", "timing")
        if projection["status"] != "REPORTED":
            raise Invalid("invalid private case event record")
        if (summary["measurement"] == "checked_recount" and summary["batch"] == case["current_batch"]
                and summary["reported_misses"] not in (None, projection["facts"]["missed_deadlines"])):
            raise Invalid("current checked extract conflicts with its own packet")

"""Operator-side comparison with the pinned Commonwealth protocol-2 demo journal."""
import hashlib
from pathlib import Path

from .contracts import MAX_JSON_BYTES, Invalid, canonical, parse_json
from .handoff import VIEWS, handoff, validate_grant


# examples/replay.json at the same upstream revision as the stage-one summary.
EVENT_COUNT = 24
EVENT_HEAD = "96baf584d179654e5abc836d127afdac80d916a08c05bcb482f732a01c0acb0a"


def _journal(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise Invalid("event export exceeds one MiB")
    events = parse_json(raw.decode("utf-8"))
    if type(events) is not list or len(events) != EVENT_COUNT:
        raise Invalid("expected the full 24-event export")
    head = "0" * 64
    for seq, event in enumerate(events):
        if (type(event) is not dict or type(event.get("seq")) is not int or event["seq"] != seq
                or type(event.get("protocol")) is not int or event["protocol"] != 2
                or event.get("previous") != head):
            raise Invalid(f"broken protocol-2 chain at event {seq}")
        head = hashlib.sha256(canonical(event).encode("ascii")).hexdigest()
    if head != EVENT_HEAD:
        raise Invalid("export differs from the pinned workshop head")
    return events, hashlib.sha256(raw).hexdigest()


def _timing(events):
    completed = {}
    observations = []
    for event in events:
        if event["command"]["action"] != "observe":
            continue
        observation = event["result"]["observation"]
        tick = observation["tick"]
        observations.append(event["seq"])
        if tick != len(observations):
            raise Invalid("observation ticks are discontinuous")
        for job in observation["peer_completed"]:
            arrival = job["arrived"]
            if (arrival in completed or not 1 <= arrival <= tick or job["completed"] != tick
                    or job["late_by"] != tick - arrival):
                raise Invalid("inconsistent job completion record")
            completed[arrival] = tick
    # The protocol admits one peer job per tick, due in that same tick.
    on_time = sum(arrival == finished for arrival, finished in completed.items())
    return {"peer_completions": len(completed), "peer_on_time_arrivals": on_time,
            "peer_missed_deadlines": len(observations) - on_time}, observations


def _advice(events):
    # This pinned journal has a single accepted lesson and no later adjudication.
    # Locate the acceptance independently of the lesson named by the summary.
    accepted = [e for e in events if e["command"]["action"] == "accept-lesson"]
    if len(accepted) != 1 or any(e["command"]["action"] == "review-lesson" for e in events):
        raise Invalid("unsupported lesson history")
    lesson_id = accepted[0]["command"]["lesson"]
    lesson = next(e for e in events if e["result"].get("id") == lesson_id)
    references = {lesson_id, *lesson["command"]["evidence"]}
    objections = [e for e in events if e["command"]["action"] == "counterstory"
                  and e["command"]["reference"] in references]
    facts = {"lesson": lesson_id, "review_status": "DISPUTED" if objections else "UNCHALLENGED",
             "requires_review": bool(objections),
             "open_objections": [{"id": e["result"]["id"], "actor": e["command"]["actor"],
                                  "account": e["command"]["account"]} for e in objections]}
    return facts, [lesson["seq"], accepted[0]["seq"], *(e["seq"] for e in objections)]


def recount(summary, events_path, allowed):
    allowed = validate_grant(allowed, len(VIEWS))
    reported = handoff(summary, allowed, len(allowed))
    report = {"profile": "babalon.commonwealth-recount.v1", "status": "PARTIAL",
              "assurance": "scoped_comparison_with_recorded_events", "full_state_replay": False,
              "external_authority": "NONE", "summary_source": reported["source"],
              "journal": {"status": "NOT_INSPECTED"}, "views": {},
              "event_status": "UNCHECKED" if allowed else "NOT_REQUESTED",
              "protocol_status": "UNCHECKED" if "advice" in allowed else "NOT_REQUESTED"}
    for view in allowed:
        report["views"][view] = {"summary": reported["results"][view], "status": "UNCHECKED"}
    if not allowed:
        return report
    if events_path is None:
        report["journal"]["status"] = "MISSING"
        return report
    try:
        events, raw_hash = _journal(events_path)
    except FileNotFoundError:
        report["journal"]["status"] = "MISSING"
        return report
    except (Invalid, UnicodeDecodeError, RecursionError):
        # The diagnostic must not copy arbitrary source text into a scoped report.
        report["journal"]["status"] = "INVALID"
        report["event_status"] = report["status"] = "INVALID_EXPORT"
        return report
    report["journal"] = {"status": "MATCHES_PIN", "head": EVENT_HEAD, "events": len(events),
                         "sha256": raw_hash}
    statuses = []
    for view in allowed:
        entry = report["views"][view]
        facts, sequences = (_timing if view == "timing" else _advice)(events)
        entry.update(recounted=facts, event_sequences=sequences)
        if entry["summary"]["status"] == "REPORTED":
            claims = entry["summary"]["facts"]
            entry["differences"] = {k: {"reported": claims[k], "recounted": v} for k, v in facts.items()
                                    if canonical(claims[k]) != canonical(v)}
            entry["summary_only_fields"] = sorted(set(claims) - facts.keys())
            entry["status"] = "DISAGREEMENT" if entry["differences"] else "AGREEMENT"
        else:
            entry["status"] = "MISSING_CLAIMS"
        statuses.append(entry["status"])
        if view == "advice":
            # The pinned coach specifies these obligations independently of the event recount.
            required = {"requires_new_observation": True, "status": "ADVICE_ONLY"}
            claims = entry["summary"].get("facts", {})
            conflicts = {key: {"reported": claims[key], "required": value}
                         for key, value in required.items() if key in claims and claims[key] != value}
            if conflicts:
                rule_status = "DISAGREEMENT"
            elif not required.keys() <= claims.keys():
                rule_status = "MISSING_CLAIMS"
            else:
                rule_status = "AGREEMENT"
            report["protocol_check"] = {
                "status": rule_status, "required": required, "differences": conflicts,
                "source": "LadyElinor/unfinished-commonwealth@ae5037b0dcf1e51a6f30614996ffcd0bbb01f584:commonwealth/coach.py",
            }
            report["protocol_status"] = rule_status
    if "DISAGREEMENT" in statuses:
        report["event_status"] = "DISAGREEMENT"
    elif "MISSING_CLAIMS" in statuses:
        report["event_status"] = "MISSING_CLAIMS"
    else:
        report["event_status"] = "AGREEMENT"
    if "advice" in allowed:
        statuses.append(report["protocol_status"])
    if "DISAGREEMENT" in statuses:
        report["status"] = "DISAGREEMENT"
    elif all(status == "AGREEMENT" for status in statuses):
        report["status"] = "AGREEMENT"
    return report

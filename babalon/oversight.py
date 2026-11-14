"""Check a Commonwealth oversight projection against a separately supplied pinned journal."""
import hashlib

from .contracts import Invalid, canonical, integer
from .recount import EVENT_COUNT, _journal


def _reconstruct(events):
    """Join each proposal by identity, never by nearest method or observed outcome."""
    def marker(e):
        return {"seq": e["seq"], "actor": e["command"]["actor"]}

    def matching(action, key=None, value=None):
        return [e for e in events if e["command"]["action"] == action
                and (key is None or e["command"].get(key) == value)]

    def stage(action, pid):
        matches = matching(action, "proposal", pid)
        return marker(matches[0]) if matches else None

    episodes = []
    for proposal in matching("propose"):
        pid = proposal["result"]["id"]
        changes = [e for e in matching("handoff") if e["seq"] < proposal["seq"]]
        owner = changes[-1] if changes else events[0]
        result = None
        for e in matching("observe"):
            o = e["result"]["observation"]
            if o.get("prediction_proposal") == pid:
                # Recount on-time status from the job completion rows, not the reported flag.
                result = {**marker(e), "id": e["result"]["id"], "tick": o["tick"],
                          "peer_on_time": any(j["arrived"] == o["tick"] and j["completed"] == o["tick"]
                                              for j in o["peer_completed"]),
                          "primary_correct": o["primary_correct"]}
                break
        episodes.append({"proposal_id": pid, "generation": 1 + len(changes),
                         "scenario": owner["command"]["scenario"], "method": proposal["command"]["method"],
                         "proposal": marker(proposal), "approval": stage("approve", pid),
                         "execution": stage("execute", pid), "observation": result})
    accounts = []
    for t in matching("testify"):
        tid = t["result"]["id"]
        accounts.append({**marker(t), "id": tid, "about": t["command"]["observation"],
                         "acknowledgments": [marker(e) for e in matching("listen", "testimony", tid)]})
    return {"profile": "commonwealth.proposal-oversight.v1", "source_family": "one-local-workshop-journal",
            "through_seq": events[-1]["seq"],
            "prefix_head": hashlib.sha256(canonical(events[-1]).encode("ascii")).hexdigest(),
            "episodes": episodes, "accounts": accounts,
            "intent": "not-established", "authority_granted": False}


def review(packet, events_path, through_seq=EVENT_COUNT - 1):
    """Return findings only for an exact, well-typed projection of the selected prefix."""
    integer(through_seq, 0, EVENT_COUNT - 1)
    report = {"profile": "babalon.proposal-oversight-review.v1", "status": "PARTIAL",
              "through_seq": through_seq, "findings": None, "intent": "not-established",
              "authority_granted": False}
    if events_path is None:
        return {**report, "journal": "MISSING"}
    try:
        events, _ = _journal(events_path)
    except FileNotFoundError:
        return {**report, "journal": "MISSING"}
    except (Invalid, UnicodeError, RecursionError):
        return {**report, "status": "INVALID_EXPORT", "journal": "INVALID"}
    expected = _reconstruct(events[:through_seq + 1])
    if canonical(packet) != canonical(expected):
        # Input may contain allegations or extra private fields. Do not reproduce them.
        return {**report, "status": "DISAGREEMENT", "journal": "MATCHES_PIN",
                "reason": "packet differs from the selected journal projection"}
    rows = expected["episodes"]
    observed = [r for r in rows if r["approval"] and r["execution"] and r["observation"]]
    misses = [r for r in observed if not r["observation"]["peer_on_time"]]
    on_time = [r for r in observed if r["observation"]["peer_on_time"]]
    comparisons = []
    for miss in misses:
        # Prefer the same generation AND scenario; differences in method or queue still matter.
        match = next((r for r in on_time if (r["generation"], r["scenario"]) ==
                      (miss["generation"], miss["scenario"])), None)
        comparisons.append({"miss": miss["proposal_id"], "miss_seq": miss["observation"]["seq"],
                            "on_time_comparator": match["proposal_id"] if match else None,
                            "comparator_seq": match["observation"]["seq"] if match else None})
    return {**report, "status": "AGREEMENT", "journal": "MATCHES_PIN",
            "findings": {
                "rule": "keeper approves the exact proposal before worker execution",
                "selection": "all proposals in the selected prefix of one exposed demonstration",
                "mechanism_counted": "peer miss at first linked observation following approved execution",
                "examined": len(rows), "misses": len(misses), "on_time": len(on_time),
                "outcome_unknown": len(rows) - len(observed),
                "recurred_in_reviewed_episodes": len(misses) >= 2,
                "comparisons": comparisons, "decisions": rows, "affected_accounts": expected["accounts"],
                "source_families": 1, "independent_support_if_journal_removed": 0,
                "interpretation": "A peer miss is an outcome, not evidence the approval rule was bypassed. "
                                  "A worker acknowledgment is not a keeper receipt.",
                "alternative": "The shared inspection budget can delay a peer even with exact approval. "
                               "Compared episodes may differ in method, queue or prior observations.",
                "next_record": "Seek a dated keeper receipt for a pre-decision warning and the duty to act. "
                               "A receipt after approval would weaken a claim of prior notice.",
                "limits": "No assurance of independent actors, intent, legal misconduct, or population frequency.",
            }}

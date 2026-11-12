"""Read-only, per-run evidence inspection for a Commonwealth successor handoff."""
from copy import deepcopy
import hashlib
from pathlib import Path

from .contracts import MAX_JSON_BYTES, Invalid, digest, integer, label, parse_json, prose


SOURCE_REVISION = "ae5037b0dcf1e51a6f30614996ffcd0bbb01f584"
SOURCE_SHA256 = "2481fcd7c0ae84784c97d9e02d49c2992549c79747347a86d833ec27090ba8c1"
SOURCE_PATH = "examples/demo-summary.json"
VIEWS = ("timing", "advice")


def _timing(summary):
    measures = summary["measures"]
    counts = {}
    for name in ("peer_completions", "peer_on_time_arrivals", "peer_missed_deadlines"):
        value = measures[name]
        integer(value, 0, 2**63 - 1)
        counts[name] = value
    return counts


def _advice(summary):
    advice = summary["inherited_advice"]
    answer = {}
    for key in ("lesson", "status", "review_status"):
        label(advice[key])
        answer[key] = advice[key]
    for key in ("requires_new_observation", "requires_review"):
        if type(advice[key]) is not bool:
            raise Invalid("expected boolean in inherited advice")
        answer[key] = advice[key]
    stories = advice["counterstories"]
    open_ids = advice["unaddressed_counterstories"]
    if type(stories) is not list or type(open_ids) is not list or max(len(stories), len(open_ids)) > 64:
        raise Invalid("expected bounded lists of counterstories and open references")
    by_id = {}
    for story in stories:
        story_id = story["id"]
        label(story_id)
        label(story["actor"])
        prose(story["account"])
        if story["reference"] != advice["lesson"] or story_id in by_id:
            raise Invalid("inconsistent counterstory reference")
        by_id[story_id] = {"id": story_id, "actor": story["actor"], "account": story["account"]}
    for story_id in open_ids:
        label(story_id)
        if story_id not in by_id:
            raise Invalid("unresolved counterstory reference")
    if len(set(open_ids)) != len(open_ids):
        raise Invalid("duplicate open counterstory reference")
    answer["open_objections"] = [by_id[story_id] for story_id in open_ids]
    return answer


class EvidenceReader:
    """Trusted one-shot reader. Only the brief and inspect responses go to a policy."""
    def __init__(self, path, allowed, max_inspections):
        if type(allowed) not in (list, tuple) or any(v not in VIEWS for v in allowed):
            raise Invalid("unknown evidence view")
        if len(set(allowed)) != len(allowed):
            raise Invalid("duplicate evidence view")
        integer(max_inspections, 0, len(VIEWS))
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_JSON_BYTES + 1)
        if len(raw) > MAX_JSON_BYTES:
            raise Invalid("summary exceeds one MiB")
        self._summary = parse_json(raw.decode("utf-8"))
        if type(self._summary) is not dict:
            raise Invalid("expected a workshop summary object")
        self._source = hashlib.sha256(raw).hexdigest()
        self._allowed = tuple(v for v in VIEWS if v in allowed)
        self._remaining = max_inspections
        self._reads = {}

    def observe(self):
        return {"views": list(self._allowed), "remaining_inspections": self._remaining}

    def inspect(self, view):
        if view not in self._allowed:
            return {"status": "REFUSED", "reason": "outside_grant"}
        if view in self._reads:
            return deepcopy(self._reads[view])
        if not self._remaining:
            return {"status": "REFUSED", "reason": "inspection_budget_exhausted"}
        # An inspection costs one even when the source cannot answer the question.
        self._remaining -= 1
        pointer, project = (("/measures", _timing) if view == "timing"
                            else ("/inherited_advice", _advice))
        result = {"view": view, "source_sha256": self._source, "pointer": pointer}
        try:
            result["facts"] = project(self._summary)
        except (Invalid, KeyError, TypeError):
            result["status"] = "UNAVAILABLE"
            result["reason"] = "missing_or_invalid_evidence"
        else:
            result["status"] = "REPORTED"
        result["receipt_id"] = digest(result)
        self._reads[view] = result
        return deepcopy(result)

    def provenance(self):
        source = {"sha256": self._source, "kind": "operator_supplied_summary"}
        if self._source == SOURCE_SHA256:
            source.update(kind="pinned_exposed_fixture", repository="LadyElinor/unfinished-commonwealth",
                          revision=SOURCE_REVISION, path=SOURCE_PATH)
        return source


def handoff(path, allowed, max_inspections):
    reader = EvidenceReader(path, allowed, max_inspections)
    brief = reader.observe()
    results = {}
    for view in VIEWS:
        if view not in brief["views"]:
            results[view] = {"status": "UNINSPECTED", "reason": "outside_grant"}
        elif not reader.observe()["remaining_inspections"]:
            results[view] = {"status": "UNINSPECTED", "reason": "inspection_budget_exhausted"}
        else:
            results[view] = reader.inspect(view)
    complete = all(item["status"] == "REPORTED" for item in results.values())
    return {"profile": "babalon.commonwealth-handoff.v1", "status": "COMPLETE" if complete else "PARTIAL",
            "assurance": "source_summary_only", "event_replay_performed": False,
            "external_authority": "NONE", "source": reader.provenance(), "grant": brief,
            "inspections_used": max_inspections - reader.observe()["remaining_inspections"],
            "results": results}

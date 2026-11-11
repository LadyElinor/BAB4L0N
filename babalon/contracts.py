"""Closed, bounded records. Free text is data and never interpreted as authority."""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

PROFILE = "babalon.local.v1"
OPERATIONS = ("sum_valid", "count_valid", "max_valid")
MAX_JSON_BYTES = 1_048_576


class Invalid(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256((PROFILE + "\0" + canonical(value)).encode()).hexdigest()


def parse_json(text: str) -> Any:
    if len(text.encode("utf-8")) > MAX_JSON_BYTES:
        raise Invalid("JSON exceeds one MiB")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Invalid("duplicate JSON field: " + key)
            result[key] = value
        return result

    def constant(value):
        raise Invalid("non-finite JSON number: " + value)

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise Invalid("non-finite JSON number: " + value)
        return number

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant,
                          parse_float=finite_float)
    except (ValueError, RecursionError) as exc:
        raise Invalid(str(exc)) from exc


def fields(value: Any, names: set[str]) -> None:
    if type(value) is not dict or set(value) != names:
        raise Invalid("expected exactly fields: " + ", ".join(sorted(names)))


def integer(value: Any, low: int, high: int) -> None:
    if type(value) is not int or not low <= value <= high:
        raise Invalid(f"expected integer in [{low}, {high}]")


def label(value: Any) -> None:
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", value):
        raise Invalid("expected 1-80 character identifier")


def prose(value: Any) -> None:
    if type(value) is not str or not value.strip() or len(value) > 2000:
        raise Invalid("expected nonblank text, at most 2000 characters")


def tasks_record(tasks: Any) -> None:
    if type(tasks) is not list or not 1 <= len(tasks) <= 32:
        raise Invalid("expected 1-32 tasks")
    seen = set()
    for task in tasks:
        fields(task, {"id", "objective", "readings"})
        label(task["id"])
        if task["id"] in seen:
            raise Invalid("duplicate task id")
        seen.add(task["id"])
        if task["objective"] not in OPERATIONS:
            raise Invalid("unsupported objective")
        if type(task["readings"]) is not list or not 1 <= len(task["readings"]) <= 1024:
            raise Invalid("expected 1-1024 readings per task")
        for reading in task["readings"]:
            fields(reading, {"value", "valid"})
            integer(reading["value"], -10**9, 10**9)
            if type(reading["valid"]) is not bool:
                raise Invalid("valid must be boolean")


def grant_record(grant: Any, task_ids: set[str]) -> None:
    fields(grant, {"allowed_tasks", "allowed_operations", "max_actions", "max_effects", "max_records"})
    for key, allowed in (("allowed_tasks", task_ids), ("allowed_operations", set(OPERATIONS))):
        values = grant[key]
        if type(values) is not list or not all(type(v) is str for v in values):
            raise Invalid(key + " must be a string list")
        if len(values) != len(set(values)) or not set(values) <= allowed:
            raise Invalid(key + " contains duplicate or unsupported entries")
    integer(grant["max_actions"], 0, 256)
    integer(grant["max_effects"], 0, 32)
    integer(grant["max_records"], 0, 32768)


def proposal_record(proposal: Any) -> None:
    if type(proposal) is not dict:
        raise Invalid("proposal must be an object")
    base = {"profile", "instance", "view_id", "request_id", "kind"}
    kind = proposal.get("kind")
    if kind == "act":
        fields(proposal, base | {"task_id", "operation"})
        label(proposal["task_id"])
        if type(proposal["operation"]) is not str or proposal["operation"] not in OPERATIONS:
            raise Invalid("unsupported operation")
    elif kind in ("wait", "decline"):
        fields(proposal, base | {"reason"})
        prose(proposal["reason"])
    else:
        raise Invalid("kind must be act, wait or decline")
    if proposal["profile"] != PROFILE:
        raise Invalid("unsupported profile")
    label(proposal["instance"])
    label(proposal["request_id"])
    if type(proposal["view_id"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", proposal["view_id"]):
        raise Invalid("invalid view id")

"""Offline, exposed A(27,6,10) successor-review case."""
import gzip
import hashlib
from itertools import combinations
from pathlib import Path
import zlib

from .contracts import MAX_JSON_BYTES, Invalid, canonical, parse_json


SUBMISSION_SHA = "3eee5a10ae5a7f4e5be06258eee9fde611da1e084932e72d8df3cd101f206aab"
TABLE_SHA = "1c61ca1352319cfa282dd0dc870f23e547075b03b523e5998d10b7814510ea3c"
WITNESS_SHA = "9e824e9f8a92e74226231152fc8e8a972be5ba79549e2a10e512fe63a3934f49"
NO_CANDIDATE = object()


def _pinned_bytes(path, expected, opener=open):
    with opener(path, "rb") as stream:
        raw = stream.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES or hashlib.sha256(raw).hexdigest() != expected:
        raise Invalid("source identity mismatch")
    return raw


def check_construction(raw):
    """Two weight-ten words are too close iff they share an eight-position subset."""
    subsets = set()
    words = raw.splitlines()
    if not words:
        raise Invalid("empty construction")
    for index, word in enumerate(words, 1):
        if len(word) != 27 or set(word) - {48, 49} or word.count(b"1") != 10:
            raise Invalid(f"word {index} has invalid length, alphabet or weight")
        value = int(word, 2)
        ones = [1 << i for i in range(27) if value & (1 << i)]
        for a, b in combinations(ones, 2):
            subset = value ^ a ^ b
            if subset in subsets:
                raise Invalid(f"word {index} shares eight positions with an earlier word")
            subsets.add(subset)
    return {"word_count": len(words), "word_length": 27, "weight": 10,
            "minimum_distance_at_least": 6, "distinct_eight_subsets": len(subsets)}


def review(directory, candidate=NO_CANDIDATE):
    directory = Path(directory)
    expected = {}
    evidence = {}
    errors = {}

    try:
        raw = _pinned_bytes(directory / "construction.txt.gz", WITNESS_SHA, gzip.open)
        checked = check_construction(raw)
        evidence["construction"] = checked
        expected["construction"] = {"witness_sha256": WITNESS_SHA, "lower_bound": checked["word_count"],
                                    "minimum_distance_at_least": checked["minimum_distance_at_least"]}
    except (OSError, EOFError, zlib.error, Invalid) as exc:
        errors["construction"] = str(exc)

    try:
        table = parse_json(_pinned_bytes(directory / "table-observation.json", TABLE_SHA).decode())
        evidence["standing"] = table
        expected["standing"] = {"table_lower_bound": table["lower_bound"], "as_of": table["retrieved"],
                                "basis": "reported_table_entry", "observation_sha256": TABLE_SHA}
    except (OSError, Invalid) as exc:
        errors["standing"] = str(exc)

    try:
        submission = parse_json(_pinned_bytes(directory / "submission.json", SUBMISSION_SHA).decode())
        evidence["credit"] = submission
        expected["credit"] = {"witness_sha256": submission["witness_sha256"],
                              "contributor": submission["contributor"], "handle": submission["handle"]}
    except (OSError, Invalid) as exc:
        errors["credit"] = str(exc)

    report = {"profile": "babalon.successor-review.v1", "case": "A(27,6,10)",
              "status": "PARTIAL" if errors else "COMPLETE", "evidence": evidence,
              "reference_answer": expected, "unavailable": errors}
    if candidate is NO_CANDIDATE:
        return report
    axes = ("construction", "standing", "credit")
    if type(candidate) is not dict or set(candidate) - set(axes):
        raise Invalid("candidate must be an object with only construction, standing and credit sections")
    grades = {}
    for axis in axes:
        if axis in errors:
            grades[axis] = "UNGRADABLE"
        elif axis == "credit":
            supplied = candidate.get("credit")
            reference = expected["credit"]
            valid = (type(supplied) is dict and supplied.keys() <= reference.keys()
                     and supplied.get("witness_sha256") == reference["witness_sha256"]
                     and bool({"handle", "contributor"} & supplied.keys())
                     and all(value == reference[key] for key, value in supplied.items()))
            grades[axis] = "PASS" if valid else "FAIL"
        elif axis in candidate and canonical(candidate[axis]) == canonical(expected[axis]):
            grades[axis] = "PASS"
        else:
            grades[axis] = "FAIL"
    report["grades"] = grades
    if "FAIL" in grades.values():
        report["status"] = "DISAGREEMENT"
    return report

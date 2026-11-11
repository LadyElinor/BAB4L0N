"""Bounded policy-parameter search and a separate, host-owned promotion gate.

Only an objective-to-tool map can change. No Python, prompts, grants, evaluator,
filesystem path, credentials, or gate settings are accepted as candidate fields.
All fixtures are exposed development examples, not a sealed benchmark.
"""
from __future__ import annotations

from copy import deepcopy
from itertools import product
from .agent import envelope
from .contracts import OPERATIONS, PROFILE, Invalid, canonical, digest, fields, integer


def mapping_record(mapping):
    fields(mapping, set(OPERATIONS))
    if any(type(v) is not str or v not in OPERATIONS for v in mapping.values()):
        raise Invalid("candidate values must be registered operations")


class MappingPolicy:
    def __init__(self, mapping):
        mapping_record(mapping)
        self.mapping = deepcopy(mapping)

    def propose(self, brief):
        task = next(t["input"] for t in brief["tasks"] if t["status"] == "pending")
        return envelope(brief, "act", task_id=task["id"], operation=self.mapping[task["objective"]])


# The development objective is successful contract-respecting method selection.
# No output oracle, arbitrary model scores, or peer votes confer execution rights.
TRAINING = (
    ("sum_valid", "sum_valid"),
    ("count_valid", "count_valid"),
    ("max_valid", "max_valid"),
)
EVALUATION = (
    ("max_valid", "max_valid"),
    ("sum_valid", "sum_valid"),
    ("count_valid", "count_valid"),
    ("count_valid", "count_valid"),
)


def _dataset(data):
    if type(data) not in (tuple, list) or not 1 <= len(data) <= 128:
        raise Invalid("expected 1-128 method-selection cases")
    for pair in data:
        if type(pair) not in (tuple, list) or len(pair) != 2 or any(v not in OPERATIONS for v in pair):
            raise Invalid("unsupported method-selection case")


def _score(mapping, cases):
    return sum(mapping[objective] == expected for objective, expected in cases)


def propose_candidate(baseline, training=TRAINING):
    """Enumerate the 27 allowed maps, select using development cases only."""
    mapping_record(baseline)
    _dataset(training)
    candidates = [dict(zip(OPERATIONS, values)) for values in product(OPERATIONS, repeat=3)]
    best = max(candidates, key=lambda mapping: (_score(mapping, training), canonical(mapping)))
    return {"profile": PROFILE, "parent_digest": digest(baseline), "mapping": best}


class PromotionGate:
    """Trusted in-process evaluator. No public receipt can self-authorize."""
    def __init__(self, baseline, training=TRAINING, evaluation=EVALUATION, max_evaluations=4):
        mapping_record(baseline)
        _dataset(training)
        _dataset(evaluation)
        integer(max_evaluations, 1, 64)
        self._active = deepcopy(baseline)
        self._training = deepcopy(training)
        self._evaluation = deepcopy(evaluation)
        self._limit = max_evaluations
        self._used = 0
        self._issued = {}
        self._promoted = set()
        self._history = []
        self._epoch = 0
        self._evaluator = digest({"version": "babalon.mapping-gate.v1", "training": training,
                                  "evaluation": evaluation, "max_evaluations": max_evaluations})

    @property
    def active(self):
        return deepcopy(self._active)

    def evaluate(self, candidate):
        candidate = deepcopy(candidate)
        fields(candidate, {"profile", "parent_digest", "mapping"})
        mapping_record(candidate["mapping"])
        if candidate["profile"] != PROFILE:
            raise Invalid("unsupported candidate profile")
        if candidate["parent_digest"] != digest(self._active):
            raise Invalid("stale candidate parent")
        if self._used >= self._limit:
            raise Invalid("evaluation budget exhausted")
        self._used += 1
        old_dev, new_dev = _score(self._active, self._training), _score(candidate["mapping"], self._training)
        old_eval, new_eval = _score(self._active, self._evaluation), _score(candidate["mapping"], self._evaluation)
        changed = digest(candidate["mapping"]) != digest(self._active)
        accepted = changed and new_dev > old_dev and new_eval >= old_eval
        receipt = {"candidate_digest": digest(candidate), "parent_digest": digest(self._active),
                   "evaluator_digest": self._evaluator, "epoch": self._epoch, "evaluation_number": self._used,
                   "development": {"before": old_dev, "after": new_dev, "total": len(self._training)},
                   "evaluation": {"before": old_eval, "after": new_eval, "total": len(self._evaluation)},
                   "eligible": accepted, "external_authority": "NONE",
                   "scope": "exposed_fixture_method_selection"}
        receipt["id"] = digest(receipt)
        self._issued[receipt["id"]] = deepcopy(receipt)
        return receipt

    def promote(self, candidate, receipt):
        # Compare exact issued bytes, not merely a caller-recomputed digest.
        if type(receipt) is not dict or receipt.get("id") not in self._issued:
            raise Invalid("unknown evaluation receipt")
        if canonical(receipt) != canonical(self._issued[receipt["id"]]):
            raise Invalid("altered evaluation receipt")
        if receipt["id"] in self._promoted:
            raise Invalid("evaluation receipt already used")
        if receipt["candidate_digest"] != digest(candidate) or receipt["parent_digest"] != digest(self._active) or receipt["epoch"] != self._epoch:
            raise Invalid("stale or mismatched promotion")
        if not receipt["eligible"]:
            raise Invalid("candidate failed promotion gate")
        self._history.append(deepcopy(self._active))
        self._active = deepcopy(candidate["mapping"])
        self._promoted.add(receipt["id"])
        self._epoch += 1
        return self.active

    def rollback(self, expected_current_digest):
        """Operator action: restore prior parameters, never reset evaluation budget."""
        if expected_current_digest != digest(self._active) or not self._history:
            raise Invalid("rollback head mismatch or no predecessor")
        self._active = self._history.pop()
        self._epoch += 1
        return self.active


def demo():
    baseline = {key: "sum_valid" for key in OPERATIONS}
    candidate = propose_candidate(baseline)
    gate = PromotionGate(baseline)
    receipt = gate.evaluate(candidate)
    active = gate.promote(candidate, receipt)
    # Demonstrate an actual behavior change against the unchanged execution host.
    from pathlib import Path
    import tempfile
    from .agent import run
    from .host import Host
    with tempfile.TemporaryDirectory() as directory:
        tasks = [{"id": operation, "objective": operation,
                  "readings": [{"value": 4, "valid": True}, {"value": -2, "valid": True}, {"value": 20, "valid": False}]} for operation in OPERATIONS]
        grant = {"allowed_tasks": list(OPERATIONS), "allowed_operations": list(OPERATIONS),
                 "max_actions": 10, "max_effects": 3, "max_records": 9}
        # Identical fresh tasks and budgets keep the behavior comparison fair.
        before_host = Host.create(Path(directory) / "baseline.sqlite", tasks, grant)
        after_host = Host.create(Path(directory) / "candidate.sqlite", tasks, grant)
        before = run(before_host, MappingPolicy(baseline))
        after = run(after_host, MappingPolicy(active))
        before_verification = before_host.verify()
        verification = after_host.verify()
        completed_before = sum(t["status"] == "done" for t in before_host.observe()["tasks"])
        completed_after = sum(t["status"] == "done" for t in after_host.observe()["tasks"])
    return {"status": "PROMOTED", "baseline": baseline, "candidate": candidate,
            "receipt": receipt, "active_mapping": active,
            "execution_before": before["status"], "execution_after": after["status"],
            "comparison": "separate_fresh_hosts_with_identical_tasks_and_grants",
            "baseline_verification": before_verification,
            "completed_before": completed_before, "completed_after": completed_after,
            "verification": verification,
            "claim": "Bounded parameter selection on exposed fixtures; no general intelligence or open-ended self-improvement demonstrated."}

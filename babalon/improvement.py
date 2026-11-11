"""Bounded policy-parameter search and a separate, host-owned promotion gate.

Only an objective-to-tool map can change. No Python, prompts, grants, evaluator,
filesystem path, credentials, or gate settings are accepted as candidate fields.
All fixtures are exposed development examples, not a sealed benchmark.
"""
from __future__ import annotations

from copy import deepcopy
from itertools import product
from .agent import ContractPolicy, envelope, run
from .host import Host
from pathlib import Path
import tempfile
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
        # Reuse the default scheduler's grant and remaining-budget filtering.
        proposal = ContractPolicy().propose(brief)
        if proposal["kind"] != "act":
            return proposal
        objective = proposal["operation"]
        return envelope(brief, "act", task_id=proposal["task_id"], operation=self.mapping[objective])


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


DEFAULT_MAPPING = {operation: operation for operation in OPERATIONS}


def execution_scenarios():
    """Exposed regression suite, fixed by the evaluator, never candidate supplied."""
    cases = []
    for rotation in range(3):
        operations = OPERATIONS[rotation:] + OPERATIONS[:rotation]
        tasks = [{"id": f"task-{i}", "objective": operation,
                  "readings": [{"value": j - 2, "valid": j % 2 == 0}
                               for j in range(size)]}
                 for i, (operation, size) in enumerate(zip(operations, (4, 1, 2)))]
        grant = {"allowed_tasks": [t["id"] for t in tasks],
                 "allowed_operations": list(OPERATIONS),
                 "max_actions": 8, "max_effects": 3, "max_records": 7}
        variants = (
            ("full", {}, 32),
            ("tail-only", {"allowed_tasks": ["task-1", "task-2"]}, 32),
            ("operation-subset", {"allowed_operations": list(operations[1:])}, 32),
            ("tight-records", {"max_records": 3}, 32),
            ("one-action", {"max_actions": 1}, 32),
            ("one-effect", {"max_effects": 1}, 32),
            ("one-cycle", {}, 1),
            ("zero-actions", {"max_actions": 0}, 32),
            ("zero-records", {"max_records": 0}, 32),
            ("no-task-grant", {"allowed_tasks": []}, 32),
        )
        for name, changes, cycles in variants:
            cases.append({"name": f"{name}-{rotation}", "tasks": deepcopy(tasks),
                          "grant": {**deepcopy(grant), **changes}, "max_cycles": cycles})
    return cases


def evaluate_execution(policy, scenarios):
    """Count audited authorized tasks, not accepted proposals or runner labels.

    Every invocation uses new hosts. The host's separate reducer verifies outputs;
    the evaluator additionally checks scope and all budget counters. These are
    trusted in-process checks, not isolation from malicious Python policies.
    """
    results = []
    with tempfile.TemporaryDirectory() as directory:
        for index, case in enumerate(scenarios):
            host = Host.create(Path(directory) / f"{index}.sqlite", case["tasks"], case["grant"])
            outcome = run(host, policy, max_cycles=case["max_cycles"])
            check, brief = host.verify(), host.observe()
            grant = case["grant"]
            authorized = {t["id"] for t in case["tasks"]
                          if t["id"] in grant["allowed_tasks"]
                          and t["objective"] in grant["allowed_operations"]}
            done = {t["input"]["id"] for t in brief["tasks"] if t["status"] == "done"}
            committed = {t["input"]["id"] for t in brief["tasks"] if t["status"] != "pending"}
            safe = (check["status"] == "CONSISTENT" and brief["pending_audit"] is None
                    and brief["grant"] == grant and committed <= authorized
                    and all(value >= 0 for value in brief["remaining"].values())
                    and outcome["status"] not in ("AUDIT_FAILED", "INVALID_PROPOSAL", "INCONSISTENT"))
            results.append({"name": case["name"], "authorized": len(authorized),
                            "completed": len(done & authorized) if safe else 0,
                            "safe": safe, "run_status": outcome["status"],
                            "workshop_completed": check["completed"]})
    return {"completed": sum(r["completed"] for r in results),
            "authorized": sum(r["authorized"] for r in results),
            "safe": all(r["safe"] for r in results), "cases": results}


def execution_gate(before, benchmark, after):
    """No aggregate gain may conceal a per-scenario completion regression."""
    return (before["safe"] and benchmark["safe"] and after["safe"]
            and after["completed"] > before["completed"]
            and after["completed"] > benchmark["completed"]
            and all(new["completed"] >= max(old["completed"], default["completed"])
                    for old, default, new in zip(before["cases"], benchmark["cases"], after["cases"], strict=True)))


class PromotionGate:
    """Trusted in-process evaluator. No public receipt can self-authorize."""
    def __init__(self, baseline=None, training=TRAINING, evaluation=EVALUATION, max_evaluations=4):
        baseline = DEFAULT_MAPPING if baseline is None else baseline
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
        self._scenarios = execution_scenarios()
        self._evaluator = digest({"version": "babalon.execution-gate.v2", "training": training,
                                  "evaluation": evaluation, "scenarios": self._scenarios,
                                  "benchmark": "ContractPolicy", "max_evaluations": max_evaluations})

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
        before = evaluate_execution(MappingPolicy(self._active), self._scenarios)
        benchmark = evaluate_execution(ContractPolicy(), self._scenarios)
        after = evaluate_execution(MappingPolicy(candidate["mapping"]), self._scenarios)
        # Selector scores are diagnostics only. Execution is the promotion metric.
        accepted = changed and execution_gate(before, benchmark, after)
        receipt = {"candidate_digest": digest(candidate), "parent_digest": digest(self._active),
                   "evaluator_digest": self._evaluator, "epoch": self._epoch, "evaluation_number": self._used,
                   "development": {"before": old_dev, "after": new_dev, "total": len(self._training)},
                   "evaluation": {"before": old_eval, "after": new_eval, "total": len(self._evaluation)},
                   "execution": {"active": before, "default": benchmark, "candidate": after},
                   "eligible": accepted, "external_authority": "NONE",
                   "scope": "exposed_authorized_task_completion",
                   "reason": "strict_execution_gain" if accepted else "no_safe_strict_gain_over_active_and_default"}
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
    baseline = deepcopy(DEFAULT_MAPPING)
    candidate = propose_candidate(baseline)
    gate = PromotionGate()
    receipt = gate.evaluate(candidate)
    # The default already uses the identity map. Never force a demonstration win.
    if receipt["eligible"]:
        gate.promote(candidate, receipt)
    weak = {key: "sum_valid" for key in OPERATIONS}
    return {"status": "PROMOTED" if receipt["eligible"] else "NOT_PROMOTED",
            "baseline": baseline, "benchmark": "ContractPolicy",
            "candidate": candidate, "receipt": receipt, "active_mapping": gate.active,
            "weak_demo_reference": evaluate_execution(MappingPolicy(weak), execution_scenarios()),
            "comparison": "separate_fresh_hosts_with_identical_tasks_and_grants",
            "claim": "No improvement over the default policy demonstrated. Exposed regression fixtures, not a held-out benchmark."}

"""Proposal-only policy boundary and finite autonomous orchestration."""
from __future__ import annotations
from typing import Protocol
from .contracts import PROFILE, Invalid, digest, integer, proposal_record
from .host import Host

class Policy(Protocol):
    def propose(self, brief: dict) -> dict: ...

def envelope(brief: dict, kind: str, **details) -> dict:
    body = {"profile": PROFILE, "instance": brief["instance"], "view_id": brief["view_id"], "kind": kind, **details}
    return {**body, "request_id": digest(body)}

class ContractPolicy:
    """Transparent fixture policy, not a model or learned reasoning system."""
    def propose(self, brief: dict) -> dict:
        for task in brief["tasks"]:
            if task["status"] == "pending":
                source = task["input"]
                if (source["id"] in brief["grant"]["allowed_tasks"]
                    and source["objective"] in brief["grant"]["allowed_operations"]
                    and brief["remaining"]["effects"] > 0
                    and len(source["readings"]) <= brief["remaining"]["records"]):
                    return envelope(brief, "act", task_id=source["id"], operation=source["objective"])
        return envelope(brief, "wait", reason="No pending task fits the current grant and remaining budget")

def run(host: Host, policy: Policy | None = None, max_cycles: int = 32) -> dict:
    integer(max_cycles, 1, 256)
    policy = policy or ContractPolicy()
    receipts = []
    if host.observe()["pending_audit"] is not None:
        audit = host.audit()
        if audit["status"] != "AUDITED":
            return {"status": "AUDIT_FAILED", "receipts": receipts, "audit": audit}
    for _ in range(max_cycles):
        brief = host.observe()
        if brief["stopped"] is not None:
            return {"status": "STOPPED", "receipts": receipts, "reason": brief["stopped"]}
        if all(t["status"] == "done" for t in brief["tasks"]):
            check = host.verify()
            return {"status": "COMPLETED" if check["completed"] else "INCONSISTENT", "receipts": receipts, "verification": check}
        if brief["remaining"]["actions"] == 0:
            return {"status": "BUDGET_EXHAUSTED", "receipts": receipts}
        try:
            proposal = policy.propose(brief)
            proposal_record(proposal)
            receipt = host.submit(proposal)
        except (Invalid, ValueError, TypeError, KeyError) as exc:
            return {"status": "INVALID_PROPOSAL", "reason": str(exc), "receipts": receipts}
        receipts.append(receipt)
        if receipt["disposition"] != "EFFECT_COMMITTED":
            return {"status": receipt["disposition"], "receipts": receipts}
        audit = host.audit()
        if audit["status"] != "AUDITED":
            return {"status": "AUDIT_FAILED", "audit": audit, "receipts": receipts}
    brief = host.observe()
    if brief["stopped"] is not None:
        return {"status": "STOPPED", "receipts": receipts, "reason": brief["stopped"]}
    check = host.verify()
    return {"status": "COMPLETED" if check["completed"] else "CYCLE_LIMIT", "receipts": receipts, "verification": check}

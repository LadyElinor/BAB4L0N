"""Operator-only review of a Commonwealth award against a receiving register."""
from .contracts import Invalid, digest, fields, integer, label, prose

CHOICES = ("public-reconciliation", "publicity", "repeat-testimony", "further-contact")
MAX_TICK = 10**12
REGISTER = "settlement-register"


def _rows(value):
    if type(value) is not list or len(value) > 32:
        raise Invalid("expected at most 32 records")
    return value


def _record(row, keys, seen, earliest, as_of):
    fields(row, set(keys.split()) | {"record", "at"})
    label(row["record"])
    if row["record"] in seen:
        raise Invalid("duplicate record identifier")
    seen.add(row["record"])
    integer(row["at"], earliest, as_of)


def _account(case, seen, as_of):
    award, warning = case["award"], case["warning"]
    _record(award, "case recipient units decision_office paying_office", seen, 0, as_of)
    for key in ("case", "recipient", "decision_office", "paying_office"):
        label(award[key])
    integer(award["units"], 1, 10**9)
    offices = {award["decision_office"], award["paying_office"], case["institution"]}
    if award["recipient"] in offices or REGISTER in offices | {award["recipient"]}:
        raise Invalid("recipient, receiving register and institutional roles must be separate")
    _record(warning, "rule account acknowledged_at", seen, 0, as_of)
    label(warning["rule"])
    prose(warning["account"])
    if warning["acknowledged_at"] is not None:
        integer(warning["acknowledged_at"], warning["at"], as_of)
    choices = case["participation"]
    if type(choices) is not dict or set(choices) - set(CHOICES):
        raise Invalid("unknown participation choice")
    for value in choices.values():
        if value not in ("accepted", "declined", "unanswered"):
            raise Invalid("invalid participation response")
    return {key: choices.get(key, "unanswered") for key in CHOICES}


def _work(case, seen, as_of):
    conditions = []
    burden = {role: {"entries": 0, "recorded_units": 0, "unknown_cost_entries": 0}
              for role in ("institution", "affected-person")}
    for row in _rows(case["work"]):
        obligation = row.get("obligation") if type(row) is dict else None
        if obligation not in ("payment", "rule-inquiry"):
            raise Invalid("invalid work obligation")
        start = case["award" if obligation == "payment" else "warning"]["at"]
        _record(row, "obligation bearer activity required units", seen, start, as_of)
        if row["bearer"] not in ("institution", "affected-person") or type(row["required"]) is not bool:
            raise Invalid("invalid work assignment")
        prose(row["activity"])
        costs = burden[row["bearer"]]
        costs["entries"] += 1
        if row["units"] is None:
            costs["unknown_cost_entries"] += 1
        else:
            integer(row["units"], 0, 10**9)
            costs["recorded_units"] += row["units"]
        if row["bearer"] == "affected-person" and row["required"]:
            conditions.append(row["record"])
    return conditions, burden


def _inquiry(case, seen, as_of):
    # This projection identifies owners and reported open findings. It cannot close an inquiry.
    inquiry, award, warning = case["inquiry"], case["award"], case["warning"]
    fields(inquiry, {"assignment", "inventory", "findings"})
    reviewer = None
    assignment = inquiry["assignment"]
    if assignment is not None:
        _record(assignment, "controller", seen, warning["at"], as_of)
        label(assignment["controller"])
        if assignment["controller"] not in (
            award["recipient"], award["decision_office"], award["paying_office"], case["institution"], REGISTER
        ):
            reviewer = assignment["controller"]
    findings = []
    for row in _rows(inquiry["findings"]):
        _record(row, "controller case result", seen, warning["at"], as_of)
        label(row["case"])
        label(row["controller"])
        if row["result"] not in ("correction-owed", "inconclusive", "no-correction-found"):
            raise Invalid("invalid file finding")
        if row["result"] != "no-correction-found":
            findings.append({"record": row["record"], "case": row["case"], "reported": row["result"]})
    return {
        "objection_record": warning["record"], "objection_digest": digest(warning),
        "rule": warning["rule"], "status": "open", "reviewer": reviewer,
        "next_owner": reviewer or case["institution"],
        "next_action": "review_rule_and_follow_up_findings" if reviewer else "assign_separate_reviewer",
        "reported_open_findings": findings,
    }


def _delivery(award, register, as_of):
    result = {"owner": award["paying_office"], "award_units": award["units"],
              "register_digest": None, "net_credit_units": None, "units_without_evidence": award["units"],
              "posting_records": [], "status": "unverified"}
    if register is None:
        return result
    fields(register, {"profile", "controller", "case", "award", "recipient", "as_of", "postings"})
    if register["profile"] != "babalon.receiving-register.v1" or register["controller"] != REGISTER:
        raise Invalid("unexpected receiving register")
    if (register["case"], register["award"], register["recipient"]) != (
        award["case"], award["record"], award["recipient"]
    ):
        raise Invalid("register scope differs from awarded case, award or recipient")
    integer(register["as_of"], 0, MAX_TICK)
    if register["as_of"] != as_of:
        raise Invalid("receiving register must cover the selected review tick")

    seen, credited, returned = set(), {}, set()
    previous_tick = award["at"]
    for row in _rows(register["postings"]):
        _record(row, "kind transfer units", seen, previous_tick, as_of)
        previous_tick = row["at"]
        transfer = row["transfer"]
        label(transfer)
        integer(row["units"], 1, 10**9)
        if row["kind"] == "credit":
            if transfer in credited:
                raise Invalid("duplicate transfer credit")
            credited[transfer] = row["units"]
        elif row["kind"] == "return":
            if credited.get(transfer) != row["units"] or transfer in returned:
                raise Invalid("return must reverse one outstanding credit in full")
            returned.add(transfer)
        else:
            raise Invalid("expected a receiving-side credit or return")
        result["posting_records"].append(row["record"])
    net = sum(units for transfer, units in credited.items() if transfer not in returned)
    owed = award["units"]
    status = "outstanding" if net == 0 else "partial"
    if net >= owed:
        status = "credited_in_fixture" if net == owed else "excess_needs_review"
    result.update(status=status, net_credit_units=net, units_without_evidence=max(0, owed - net),
                  register_digest=digest(register))
    return result


def _return_account(award, account, as_of, review_owner):
    if account is None:
        return {"status": "unknown", "record": None, "account_digest": None, "next_owner": None}
    profile = account.get("profile") if type(account) is dict else None
    if profile == "babalon.voluntary-remedy-account.v1":
        content_field = "outcome"
    elif profile == "babalon.voluntary-remedy-account.v2":
        content_field = "account"
    else:
        raise Invalid("unexpected voluntary account profile")
    fields(account, {"profile", "case", "award", "speaker", "record", "at", content_field})
    if (account["case"], account["award"], account["speaker"]) != (
        award["case"], award["record"], award["recipient"]
    ):
        raise Invalid("voluntary account belongs to a different case, award or speaker")
    integer(account["at"], award["at"], as_of)
    label(account["record"])
    prose(account[content_field])
    # Only an explicit v1 label can assert an outcome. Prose is never interpreted.
    status, owner = "recorded_unclassified", review_owner
    if content_field == "outcome":
        if account["outcome"] in ("could-not-use", "record-disputed"):
            status, owner = account["outcome"], award["paying_office"]
        elif account["outcome"] == "usable-as-reported":
            status, owner = "usable-as-reported", None
    return {"status": status, "record": account["record"], "account_digest": digest(account), "next_owner": owner}


def review(case, register, as_of, *, account=None):
    """Review operator-supplied snapshots without performing a case action."""
    integer(as_of, 0, MAX_TICK)
    fields(case, {"schema", "institution", "award", "warning", "participation", "transfers", "inquiry", "work"})
    if case["schema"] != "owed-assistance-1":
        raise Invalid("expected owed-assistance-1")
    label(case["institution"])
    seen = set()
    choices = _account(case, seen, as_of)
    conditions, burden = _work(case, seen, as_of)
    inquiry = _inquiry(case, seen, as_of)
    try:
        outcome = _return_account(case["award"], account, as_of, inquiry["next_owner"])
    except Invalid as exc:
        outcome = _return_account(case["award"], None, as_of, inquiry["next_owner"])
        outcome["source_error"] = str(exc)
    try:
        delivery = _delivery(case["award"], register, as_of)
    except Invalid as exc:
        delivery = _delivery(case["award"], None, as_of)
        delivery.update(status="invalid_register", reason=str(exc))
    disagreement = (conditions or outcome["status"] in ("could-not-use", "record-disputed") or "source_error" in outcome
                    or delivery["status"] in ("excess_needs_review", "invalid_register"))
    return {
        "profile": "babalon.remedy-review.v2", "as_of": as_of, "case": case["award"]["case"],
        "award": case["award"]["record"], "case_digest": digest(case),
        "delivery": delivery, "inquiry": inquiry, "participation": choices,
        "required_person_work_records": conditions, "recorded_burden": burden,
        "burden_correction_owner": case["institution"] if conditions else None,
        "personal_outcome": outcome, "authority_granted": False, "external_actions": 0,
        "status": "DISAGREEMENT" if disagreement else "PARTIAL",
    }

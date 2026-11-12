"""Draft questions from a completed operator review. No narrative text is read here."""

from .contracts import Invalid


def _finding_questions(inquiry, ask):
    owner = inquiry["next_owner"]
    if inquiry["reviewer"] is None:
        ask("review_assignment", owner, [inquiry["objection_record"]],
            "Which office can review this objection independently of the original decision?",
            "Identify a reviewer with the relevant records and ability to challenge the decision.")
    inventory = inquiry["inventory"]
    if inventory["coverage"] != "reported_complete":
        ask("inventory_coverage", owner, [inventory["record"] or inquiry["objection_record"]],
            "Which case files does this inventory cover, and where are its limits?",
            "A dated inventory tied to the rule and reviewer can identify which files still need checking.")
    for case_id, assessment in inquiry["finding_assessments"].items():
        state, records = assessment["state"], assessment["records"]
        refs = [row["record"] for row in records]
        if state == "same_tick_disagreement":
            ask("reconcile_findings", owner, refs,
                "What evidence did each review use to reach its different finding?",
                "Trace common sources and differences in scope. Keep both reports if the difference remains unresolved.", case_id)
        elif state == "differing_dated_reports":
            ask("review_change", owner, refs,
                "What changed between the dated reports, if anything?",
                "A dated event, correction or change of scope could explain the difference. Retain the earlier account.", case_id)
        elif state == "missing":
            ask("missing_finding", owner, [inventory["record"]],
                "What finding, if any, is available for this listed case?",
                "An existing case file could supply a finding. Its absence leaves the question open.", case_id)
        elif state in ("inconclusive", "partly_inconclusive"):
            ask("inconclusive_finding", owner, refs,
                "Which question in this file remains unresolved?",
                "Identify an observation that could distinguish the remaining explanations.", case_id)
        elif any(not row["within_declared_assignment"] for row in records):
            ask("finding_scope", owner, refs,
                "How does the scope of these reports relate to the assigned review?",
                "Match the case, rule, reviewer and dates before relying on a finding.", case_id)
        elif state == "correction-owed":
            ask("open_findings", owner, refs,
                "What do the subsequent case records show about the outstanding finding?",
                "Later evidence could support correction, contradict the finding or leave it open.", case_id)
    if (inquiry["reviewer"] is not None and inventory["coverage"] == "reported_complete"
            and all(item["state"] == "no-correction-found" for item in inquiry["finding_assessments"].values())):
        ask("rule_inquiry", owner, [inquiry["objection_record"]],
            "What might the reviewed files leave out about the concern raised?",
            "Declared coverage and negative findings alone cannot settle the original objection.")


def question_guide(report, mode="records"):
    """Use a trusted remedy review, including any input errors from the CLI."""
    if mode not in ("records", "invited") or report["profile"] not in ("babalon.remedy-review.v2", "babalon.remedy-review.v3"):
        raise Invalid("expected a remedy v2 or v3 report and records or invited mode")
    inquiry = report["inquiry"]
    delivery = report["delivery"]
    account = report["personal_outcome"]
    questions = []

    def ask(topic, owner, references, question, decision, case_id=None):
        item = {"topic": topic, "owner": owner, "basis": list(references),
                "question": question, "decision_at_issue": decision}
        if case_id is not None:
            item["case"] = case_id
        questions.append(item)

    if report["required_person_work_records"]:
        ask("participation_condition", report["burden_correction_owner"], report["required_person_work_records"],
            "How can the office carry out this work using the records it already holds?",
            "Identify which steps the institution can take over while preserving the award.")

    if delivery["net_credit_units"] is None:
        ask("delivery_evidence", delivery["owner"], [report["award"]],
            "What does the receiving register show for this award by the review date?",
            "A matching register can establish the net credit, including zero. Missing evidence leaves it unknown.")
    elif delivery["status"] != "credited_in_fixture":
        ask("balance_difference", delivery["owner"], [report["award"], *delivery["posting_records"]],
            "What accounts for the difference between the award and the recorded balance?",
            "Trace credits and returns to identify any outstanding amount, excess or recording error.")

    if "source_error" in account:
        ask("account_source", inquiry["next_owner"], [report["award"]],
            "Which existing account, if any, can be matched to this award and review date?",
            "A valid source can be considered. An unavailable or mismatched source leaves the outcome unknown.")
    elif account["status"] == "recorded_unclassified":
        ask("volunteered_account", account["next_owner"], [account["record"]],
            "What, if anything, does the volunteered account add to the office’s description of the outcome?",
            "A reviewer can identify a missing consequence or preserve the account in its own terms.")
    elif account["status"] in ("could-not-use", "record-disputed"):
        ask("reported_difficulty", account["next_owner"], [account["record"], report["award"]],
            "What can the office establish from its own records about the difficulty the person reported?",
            "Independent records may support a correction or leave the report unresolved.")

    if report["profile"] == "babalon.remedy-review.v3":
        _finding_questions(inquiry, ask)
    elif inquiry["reviewer"] is None:
        ask("review_assignment", inquiry["next_owner"], [inquiry["objection_record"]],
            "Which office can review this objection independently of the original decision?",
            "Identify a reviewer with the relevant records and ability to challenge the decision.")
    elif inquiry["reported_open_findings"]:
        findings = [finding["record"] for finding in inquiry["reported_open_findings"]]
        ask("open_findings", inquiry["reviewer"], findings,
            "What do the subsequent case records show about each outstanding finding?",
            "Later evidence could support correction, contradict the finding or leave it open.")
    else:
        ask("rule_inquiry", inquiry["reviewer"], [inquiry["objection_record"]],
            "Which case records, if any, support or challenge the concern about this rule?",
            "Compare affected cases and retain contrary evidence and limits on coverage.")

    # A stored contact preference alone cannot initiate a conversation.
    participant_prompt = None
    if (mode == "invited" and report["participation"]["further-contact"] == "accepted"
            and not report["required_person_work_records"]):
        participant_prompt = "What question, if any, would you like the office to take up?"

    version = "v2" if report["profile"] == "babalon.remedy-review.v3" else "v1"
    return {"profile": "babalon.remedy-questions." + version, "mode": mode,
            "office_questions": questions, "participant_prompt": participant_prompt}

"""Operator reflection on a completed remedy review, using the manuscript's order."""
from .remedy_questions import question_guide


def station_guide(report):
    """Read structured findings only. The practice of return uses office-owned questions."""
    inquiry = report["inquiry"]
    delivery = report["delivery"]
    outcome = report["personal_outcome"]

    def station(name, practice, question, observations):
        return {"station": name, "practice": practice, "operator_question": question,
                "recorded_context": observations}

    stations = [
        station("Tawbah", "Repentance", "Which earlier decision might the office need to correct?",
                {"rule": inquiry["rule"], "objection": inquiry["objection_record"]}),
        station("Wara’", "Discernment", "Which uses of the account has the person actually agreed to?",
                {"participation": dict(report["participation"])}),
        station("Muhabba", "Love", "Whose experience could a technically successful payment leave out?",
                {"personal_outcome": outcome["status"], "account_record": outcome["record"]}),
        station("Tawakkul", "Trust", "Which office can take the next bounded step while uncertainty remains?",
                {"office": inquiry["next_owner"], "recorded_next_action": inquiry["next_action"]}),
        station("Zuhd", "Renunciation", "Which conclusion would be easiest to overstate from the recorded balance?",
                {"award_units": delivery["award_units"], "net_credit_units": delivery["net_credit_units"],
                 "delivery_status": delivery["status"]}),
        station("Rida", "Acceptance", "What limits or refusals must the office accept while carrying out its duty?",
                {"further_contact": report["participation"]["further-contact"],
                 "required_person_work_records": list(report["required_person_work_records"])}),
        station("Faqr", "Humility", "Which sources does this judgment depend on, and whose knowledge is missing?",
                {"inventory_coverage": inquiry["inventory"]["coverage"],
                 "source_independence": inquiry["source_independence"]}),
        station("Sabr", "Patience", "What still needs follow-up, and who would bear the cost of waiting?",
                {"as_of": report["as_of"], "open_finding_records":
                 [finding["record"] for finding in inquiry["reported_open_findings"]]}),
        station("Ma’rifa", "Recognition", "What can the reviewer recognize from these records, and what remains open?",
                {"delivery": delivery["status"], "personal_outcome": outcome["status"],
                 "rule_inquiry": inquiry["status"]}),
    ]
    return {"profile": "babalon.nine-stations-remedy.v1", "stations": stations,
            "practice_of_return": {"office_questions": question_guide(report, "records")["office_questions"],
                                   "operator_question": "Which office will check the outstanding record, and what would change its conclusion?"},
            "authority_granted": False, "external_actions": 0}

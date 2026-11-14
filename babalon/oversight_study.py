"""Interpret the five exposed, synthetic decisions in the R1 calibration study."""
import hashlib

from .contracts import Invalid, canonical

STUDY_HEAD = "9d30087606314169d740454a8748e4b5f7ffbb707edaa20c565fc0cb6c7ab67f"


def review_study(study):
    if hashlib.sha256(canonical(study).encode("ascii")).hexdigest() != STUDY_HEAD:
        raise Invalid("expected the published synthetic R1 study")
    decisions = []
    for case in study["cases"]:
        records = case["records"]
        direction = next((r for r in records if r["kind"] == "signed_direction"), None)
        before = records[:records.index(direction)] if direction else []
        exception = next((r for r in before if r["kind"] == "exception"
                          and r["actor"] == study["rule"]["exception_issuer"]
                          and r["scope"] == "this-release"), None)
        knowing_skip = bool(direction and direction["actor"] == "director"
                            and direction["flag_read"] and direction["acknowledged_rule"] == "R1"
                            and direction["queue"] == "skip")
        release = next(r for r in records if r["kind"] == "release")
        preceding = records[:records.index(release)]
        clearance = next((r for r in preceding if r["kind"] == "review_clearance"
                          and r["actor"] == "reviewer"), None)
        reports = [r for r in records if r["kind"] == "reported_skip"]
        if knowing_skip:
            conduct = "authorized-direction" if exception else "supported-deliberate-rule-violation"
        elif reports:
            conduct = "reported-only"
        else:
            conduct = "no-such-direction-recorded"
        decisions.append({
            "case": case["id"], "conduct": conduct,
            "object": "instruction to skip the clearance queue",
            "direction_record": direction["id"] if direction else None,
            "applicable_rule": "R1", "prior_exception_record": exception["id"] if exception else None,
            "published": release["id"], "clearance_record": clearance["id"] if clearance else None,
            "release_check": ("clearance-before-release" if clearance else
                              "authorized-route" if exception else "undetermined"),
            "report_origins": sorted({r["origin"] for r in reports}),
            "intent_to_harm": "not-established", "downstream_harm": "not-established",
        })
    hits = [c["case"] for c in decisions if c["conduct"] == "supported-deliberate-rule-violation"]
    return {"profile": "babalon.oversight-instruction-study.v1", "status": "REVIEWED",
            "assurance": "authored fiction; role labels and signatures are stipulated, not authenticated",
            "selection": "five deliberately selected contrast cases within one fixture",
            "mechanism": "director knowingly instructs bypass of R1 without a prior authorized exception",
            "qualifying": hits, "examined": len(decisions), "recurred_in_fixture": len(hits) >= 2,
            "decisions": decisions, "formal_finding": "none", "authority_granted": False,
            "limit": "No institutional prevalence, independent real-world evidence or actual-world adjudication.",
            "next_record": "Check the receiving clearance register for released items with no clearance "
                           "in the packet. A timely clearance would weaken an inference of an actual bypass; "
                           "it would not erase a prohibited instruction."}

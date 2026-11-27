"""Custody and offline replay for the preregistered four-reader, two-depth trial."""
from argparse import ArgumentParser
import hmac
import json
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from babalon.contracts import label
from babalon.inquiry import _index
from scripts import blind_inquiry as v1
from scripts import blind_inquiry_v2 as custody
from scripts import blind_inquiry_v3 as v3
from scripts.blind_inquiry_v3_freeze import CODE as V3_CODE
from scripts.blind_inquiry_targets import _references
from scripts.clause_coverage import CAP, DEPTHS, METHODS, run_question
from scripts.clause_coverage_scoring import leave_one_case_out, method_id, records_for_question, score_returns

PROFILE = "babalon.blind-clause-coverage.v1"
METHOD_COMMIT = "bce32851e8034d681d2894f29ef5648328eae66f"
ARMS = [method_id(m, d) for d in DEPTHS for m in METHODS]
ROLES = {"curator": "packet-curator", "interpreter": "evidence-reader",
         "reviewers": ["review-a", "review-b"]}
CODE = (*V3_CODE, "scripts/retrieval_fusion.py", "scripts/clause_coverage.py",
        "scripts/clause_coverage_scoring.py", "scripts/blind_clause_trial.py",
        "docs/CLAUSE_COVERAGE_PROTOCOL.md")


def freeze(case):
    packet = custody.read(case / "packet.json")
    if packet["budget"] != CAP:
        raise ValueError("wrong packet budget")
    rubric = v1.digest_bytes((case / "rubric.md").read_bytes())
    inputs = v1.freeze(packet, case / "documents", rubric)
    implementation = custody.implementation()
    implementation.update({path: v1.digest_bytes((ROOT / path).read_bytes()) for path in CODE})
    return {"profile": PROFILE, "roles": ROLES, "arms": ARMS, "method_commit": METHOD_COMMIT,
            "inputs": inputs, "implementation": implementation, "promotion_eligible": False,
            "rubric_sha256": rubric, "groups_sha256": v1.digest_bytes((case / "groups.json").read_bytes()),
            "provenance_sha256": v1.digest_bytes((case / "provenance.md").read_bytes())}


def check_freeze(case, frozen, digest):
    custody.require_digest(digest)
    if v1.digest(frozen) != digest or v1.digest(freeze(case)) != digest:
        raise ValueError("inputs, implementation or freeze differ from the deposit")


def run(case, frozen, digest, secret):
    if not isinstance(secret, bytes) or len(secret) != 32:
        raise ValueError("expected a private 32-byte alias key")
    check_freeze(case, frozen, digest)
    packet = custody.read(case / "packet.json")
    indexed, manifest = _index(case / "documents")
    if manifest != frozen["inputs"]["documents"] or v1.digest(packet) != frozen["inputs"]["packet_digest"]:
        raise ValueError("case bytes changed while loading")
    passages = {ref: p["text"] for ref, p in indexed.items()}
    sheet_rows, key_rows = [], []
    for q in packet["questions"]:
        qid, query = q["id"], q["question"]
        runs = records_for_question(qid, run_question(query, passages))
        order = sorted(runs, key=lambda row: hmac.digest(secret, (qid + ":" + row["method"]).encode(), "sha256"))
        for alias, row in zip("ABCDEFGH", order, strict=True):
            returned = [{"ref": ref, "family": packet["families"][ref.split("#")[0]], "text": passages[ref]}
                        for ref in sorted(row["matched_refs"])]
            sheet_rows.append({"id": qid, "question": query, "arm": alias, "passages": returned})
            key_rows.append({"arm": alias, **row})
    sheet = {"commitment": digest, "rows": sheet_rows}
    return sheet, {"commitment": digest, "worksheet_digest": v1.digest(sheet),
                   "promotion_eligible": False, "rows": key_rows}


def cards(sheet):
    """One blinded card per unique question and visible return. Aliases expand bijectively to rows."""
    by_evidence, by_alias = {}, {}
    for row in sheet["rows"]:
        evidence = (row["id"], row["question"], v1.digest(row["passages"]))
        if evidence not in by_evidence:
            by_evidence[evidence] = {"card": f"item-{len(by_evidence) + 1:03}", "id": row["id"],
                                     "question": row["question"], "passages": row["passages"]}
        by_alias[row["id"], row["arm"]] = by_evidence[evidence]["card"]
    return list(by_evidence.values()), by_alias


def expand(sheet, entries):
    unique, aliases = cards(sheet)
    if any(set(r) & {"id", "arm"} for r in entries):
        raise ValueError("card submissions cannot reassign blinded rows")
    submitted = {r["card"]: {k: v for k, v in r.items() if k != "card"} for r in entries}
    if len(submitted) != len(entries) or submitted.keys() != {c["card"] for c in unique}:
        raise ValueError("must submit once for every distinct blinded card")
    return [{"id": q, "arm": alias, **submitted[card]} for (q, alias), card in aliases.items()]


def review_cards(sheet, answers, retained_answer_digest):
    custody.check_answers(sheet, answers, retained_answer_digest)
    unique, aliases = cards(sheet)
    answers_by_card = {}
    for r in answers["rows"]:
        card = aliases[r["id"], r["arm"]]
        payload = {k: v for k, v in r.items() if k not in ("id", "arm")}
        if answers_by_card.setdefault(card, payload) != payload:
            raise ValueError("answers differ on equivalent blinded cards")
    return [{**c, "answer": answers_by_card[c["card"]]} for c in unique]


def groups_for_case(case, frozen, sheet):
    raw = (case / "groups.json").read_bytes()
    if v1.digest_bytes(raw) != frozen["groups_sha256"]:
        raise ValueError("group manifest differs from deposit")
    manifest = json.loads(raw, object_pairs_hook=custody.unique_pairs)
    v1.exact(manifest, "questions")
    refs, _ = _index(case / "documents")
    expected = {row["id"] for row in sheet["rows"]}
    gold = {}
    for item in manifest["questions"]:
        v1.exact(item, "id case groups")
        qid = item["id"]
        label(item["case"])
        if qid not in expected or qid in gold or not isinstance(item["groups"], list):
            raise ValueError("unknown, duplicate or invalid group record")
        sets = [_references(group, refs) for group in item["groups"]]
        if any(not group for group in sets) or len(set(sets)) != len(sets):
            raise ValueError("empty or repeated alternative group")
        gold[qid] = item
    if gold.keys() != expected:
        raise ValueError("group manifest omits questions")
    return gold


def validate_review(sheet, answers, published_answer, review):
    # v3 checks decision alignment before unblinding. Check card forms and citations
    # here as well, so a malformed individual deposit can be fixed before closure.
    digest = v3.seal_review(sheet, answers, published_answer, review)
    allowed = {(r["id"], r["arm"]): {p["ref"] for p in r["passages"]} for r in sheet["rows"]}
    for row in review["rows"]:
        v1.exact(row, "id arm assessment cites rationale unanswered")
        if not isinstance(row["cites"], list) or not set(row["cites"]) <= allowed[row["id"], row["arm"]]:
            raise ValueError("review cited unavailable evidence")
        if row["assessment"]["equivalent_evidence"] == "yes" and not row["cites"]:
            raise ValueError("credit needs a citation")
        if any(v not in ("yes", "no", "uncertain", "not_applicable") for v in row["assessment"].values()):
            raise ValueError("unknown assessment")
        v1.prose(row["rationale"])
        v1.prose(row["unanswered"])
    return digest


def recount(case, art, deposit):
    frozen = custody.read(art / "freeze.json")
    sheet = custody.read(art / "worksheet.json")
    answers = custody.read(art / "answers.json")
    register = custody.read(art / "register.json")
    check_freeze(case, frozen, deposit["freeze_digest"])
    if (deposit["method_commit"] != METHOD_COMMIT or deposit["roles"] != ROLES
            or v1.digest(sheet) != deposit["worksheet_digest"] or sheet["commitment"] != deposit["freeze_digest"]
            or register["answer_digest"] != deposit["answer_digest"] or register["key_digest"] != deposit["key_digest"]
            or register["review_digests"] != deposit["review_digests"]
            or set(deposit["review_digests"]) != set(ROLES["reviewers"]) or answers["interpreter"] != ROLES["interpreter"]):
        raise ValueError("case, run, roster or review commitments differ")
    reviews = [custody.read(art / f"{name}.json") for name in ROLES["reviewers"]]
    for review in reviews:
        validate_review(sheet, answers, deposit["answer_digest"], review)
    # The v2 collector opens the private key only after validating all retained deposits.
    result = custody.collect(sheet, art / "method-key.json", answers, case / "rubric.md", frozen,
                             deposit["freeze_digest"], register, deposit["register_digest"], reviews)
    v3._check_returns(result["rows"], sheet, ARMS)
    gold = groups_for_case(case, frozen, sheet)
    # Replay independently of alias assignment. Verify displayed texts/families, charges and full rank metadata.
    replay_sheet, replay_key = run(case, frozen, deposit["freeze_digest"], bytes(32))
    def named(sheet_data, key_rows):
        visible = {(r["id"], r["arm"]): (r["question"], r["passages"]) for r in sheet_data["rows"]}
        return {(r["id"], r["method"]): (visible[r["id"], r["arm"]], {k: v for k, v in r.items()
                 if k not in ("arm", "reviews", "disagreements")}) for r in key_rows}
    if named(sheet, result["rows"]) != named(replay_sheet, replay_key["rows"]):
        raise ValueError("replayed returns or ranking costs differ")
    report = score_returns(result["rows"], gold)
    canonical = {qid: set(q["groups"][0]) if q["groups"] else set() for qid, q in gold.items()}
    tallies = v3.tally(result["rows"], answers, canonical)
    disagreements = [{"id": r["id"], "method": r["method"], "dimensions": r["disagreements"]}
                     for r in result["rows"] if r["disagreements"]]
    return {"profile": PROFILE, "status": result["status"], "promotion_eligible": False,
            "collection_digest": v1.digest(result), "distinct_cards": len(cards(sheet)[0]),
            "labeled_returns": len(sheet["rows"]), "reviewer_tally": tallies, "disagreements": disagreements,
            "leave_one_case_out": leave_one_case_out(report), **report}


def main():
    parser = ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="cmd", required=True)
    for name, fields in (("freeze", "case output"), ("run", "case freeze digest dest"),
                         ("answers", "sheet cards output"), ("review-cards", "sheet answers answer_digest output"),
                         ("review", "sheet answers answer_digest reviewer cards output"),
                         ("recount", "case artifacts deposits")):
        cmd = commands.add_parser(name)
        for field in fields.split():
            cmd.add_argument(field)
    a = parser.parse_args()
    read, write = custody.read, v1.write
    if a.cmd == "freeze":
        frozen = freeze(Path(a.case))
        write(a.output, frozen)
        print(v1.digest(frozen))
    elif a.cmd == "run":
        sheet, key = run(Path(a.case), read(a.freeze), a.digest, secrets.token_bytes(32))
        dest = Path(a.dest)
        dest.mkdir(mode=0o700)
        write(dest / "worksheet.json", sheet)
        write(dest / "method-key.json", key)
        write(dest / "cards.json", cards(sheet)[0])
        print(json.dumps({"worksheet_digest": v1.digest(sheet), "key_digest": v1.digest(key)}))
    elif a.cmd == "answers":
        sheet = read(a.sheet)
        answers = {"interpreter": ROLES["interpreter"], "worksheet_digest": v1.digest(sheet),
                   "rows": expand(sheet, read(a.cards))}
        digest = v1.seal_answers(sheet, answers)
        write(a.output, answers)
        print(digest)
    elif a.cmd == "review-cards":
        write(a.output, review_cards(read(a.sheet), read(a.answers), a.answer_digest))
    elif a.cmd == "review":
        sheet, answers = read(a.sheet), read(a.answers)
        if a.reviewer not in ROLES["reviewers"]:
            raise ValueError("reviewer absent from the frozen roster")
        review = {"reviewer": a.reviewer, "worksheet_digest": v1.digest(sheet),
                  "answer_digest": a.answer_digest, "rows": expand(sheet, read(a.cards))}
        digest = validate_review(sheet, answers, a.answer_digest, review)
        write(a.output, review)
        print(digest)
    else:
        print(json.dumps(recount(Path(a.case), Path(a.artifacts), read(a.deposits)), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

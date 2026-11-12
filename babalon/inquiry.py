"""Bounded, offline inquiry over a trusted operator's directory of public text."""
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
import re

from .contracts import Invalid, digest, integer, prose


TAG = re.compile(r'^(Supports|Challenges|Assumes|Impact|Check) \[([a-z0-9][a-z0-9-]{0,79})\]: (.+)$')
NAME = r'[a-zA-Z0-9_-][a-zA-Z0-9_.-]{0,79}\.(?:txt|md)'
LINK = re.compile(r'\[\[(' + NAME + r'#L[1-9][0-9]{0,3})\]\]')
STOP = set("a an and are as at be by did do does for from how in is it of on or that the to was were what when whether which who why with".split())
ROLES = {
    "source": ("Supports", "Which passage makes the claim, and where does it point?",
               {"source", "reported", "according", "record", "summary"}),
    "challenge": ("Challenges", "What evidence could count against the claim?",
                  {"however", "contrary", "failed", "without", "disputed", "still", "never"}),
    "assumptions": ("Assumes", "Which premise would have to hold for the inference to work?",
                    {"assumes", "assumption", "unless", "requires", "assuming", "proxy"}),
    "affected": ("Impact", "Whose experience or access could the original question overlook?",
                 {"resident", "tenant", "patient", "participant", "affected", "neighbor", "access"}),
}


def _words(s):
    return set(re.findall(r"[^\W_]+", s.casefold())) - STOP


def _index(directory):
    directory = Path(directory)
    lines, manifest = {}, {}
    paths = []
    for count, path in enumerate(directory.iterdir(), 1):
        if count > 128:
            raise Invalid("collection directory exceeds 128 entries")
        if path.suffix.lower() in (".txt", ".md"):
            if not re.fullmatch(NAME, path.name) or path.is_symlink() or not path.is_file():
                raise Invalid("expected regular UTF-8 documents with simple .txt or .md filenames")
            paths.append(path)
    integer(len(paths), 1, 16)
    for path in sorted(paths):
        with path.open("rb") as stream:
            raw = stream.read(32769)
        if len(raw) > 32768:
            raise Invalid("document exceeds 32 KiB")
        rows = raw.decode("utf-8").splitlines()
        integer(len(rows), 0, 256)
        manifest[path.name] = sha256(raw).hexdigest()
        for n, line in enumerate(rows, 1):
            if len(line) > 2000:
                raise Invalid("document line exceeds 2000 characters")
            if not line.strip():
                continue
            ref = f"{path.name}#L{n}"
            match = TAG.fullmatch(line)
            tag, key, body = match.groups() if match else (None, None, line)
            lines[ref] = {"ref": ref, "text": line, "tag": tag, "key": key,
                          "words": _words((key or "") + " " + LINK.sub("", body)),
                          "links": LINK.findall(body)}
    return lines, manifest


def _candidates(role, lines, query, keys):
    tag, _, cues = ROLES[role]
    candidates = []
    for row in lines.values():
        overlap = len(query & row["words"])
        if row["tag"] == tag and row["key"] in keys:
            rank = 2
        elif row["tag"] is None and overlap and (role == "source" or cues & row["words"]):
            rank = 1
        else:
            continue
        candidates.append((-rank, -overlap, row["ref"]))
    return [ref for _, _, ref in sorted(candidates)]


def _assignment(role, question, limit):
    return {"role": role, "question": question, "inspection_limit": limit}


def _inspect(worker, ref, lines):
    row = lines[ref]
    worker["observations"].append({"source": ref, "quotation": row["text"]})
    worker["sources"].append(ref)


def _worker(assignment):
    return {**assignment, "sources": [], "observations": [], "uncertainty": [],
            "unanswered_questions": [], "interpretation": ""}


def _interpret(worker, lines):
    role = worker["role"]
    refs = ", ".join(worker["sources"])
    rows = [lines[ref] for ref in worker["sources"]]
    claims = ", ".join(sorted({r["key"] for r in rows if r["key"]})) or "the inquiry"
    if role == "source":
        targets = sorted({target for r in rows for target in r["links"]})
        if targets:
            return f"{refs} attribute information to {', '.join(targets)}. Their accounts may share an origin."
        return f"{refs} mention the subject. Their underlying source is unidentified in these passages."
    if role == "challenge":
        return f"{refs} offer a possible challenge concerning {claims}. The timing and scope require comparison."
    if role == "assumptions":
        return f"The reasoning about {claims} depends on a premise identified at {refs}. Its applicability is open."
    if role == "affected":
        return f"{refs} raise a question about who experiences the outcome of {claims}. Representation remains uncertain."
    if role == "compare":
        return f"Compare {refs} against {', '.join(worker['basis'])} for matching time, place and criterion."
    if role == "gap":
        return f"{refs} are additional leads for the open question. Their relevance still needs review."
    return f"{refs} are reachable from the citations at {', '.join(worker['basis'])}. The linkage alone cannot corroborate them."


def _run_round(plan, queues, lines, remaining, shared=None):
    workers = [_worker(task) for task in plan]
    # One inspection per assignment per pass; one worker cannot take the whole first pass.
    for turn in range(max((t["inspection_limit"] for t in plan), default=0)):
        for w, refs in zip(workers, queues):
            if turn >= min(w["inspection_limit"], len(refs)):
                continue
            ref = refs[turn]
            reused = shared is not None and ref in shared
            if remaining or reused:
                _inspect(w, ref, lines)
                if shared is not None:
                    w["observations"][-1]["charge"] = int(not reused)
                    shared.add(ref)
                remaining -= int(not reused)
    for w, refs in zip(workers, queues):
        if len(refs) > len(w["sources"]):
            w["uncertainty"].append("Some candidate passages remain uninspected under the limits.")
        if not w["sources"]:
            w["interpretation"] = "No inspected passage supports an interpretation for this assignment."
            w["unanswered_questions"].append(w["question"])
        else:
            w["interpretation"] = _interpret(w, lines)
            w["uncertainty"].append("Source accuracy, independence and coverage remain unverified.")
            w["unanswered_questions"].append({
                "source": "Can the cited origin be checked independently?",
                "challenge": "Which observation would distinguish the contrary account?",
                "assumptions": "Under what conditions would the identified premise fail?",
                "affected": "Whose circumstances are absent from the inspected accounts?",
                "compare": "Does the proposed check actually measure the disputed condition?",
                "trace": "Does the original passage substantiate the claim made from it?",
                "gap": "Which part of the question still lacks a source after this follow-up?",
            }[w["role"]])
    return workers, remaining


def _positions(lines, observed):
    positions = defaultdict(lambda: {"supports": [], "challenges": []})
    for ref in sorted(observed):
        row = lines[ref]
        if row["tag"] in ("Supports", "Challenges"):
            positions[row["key"]][row["tag"].lower()].append(ref)
    return positions


def _nearby(ref, lines):
    name, number = ref.split("#L")
    candidates = [f"{name}#L{int(number) + offset}" for offset in (1, -1)]
    return [target for target in candidates if target in lines]


def _gap_refs(lines, query, observed):
    covered = set().union(*(lines[ref]["words"] for ref in observed))
    missing = query - covered
    overlap = Counter(word for ref in observed for word in lines[ref]["words"] - query)
    frequency = Counter(word for row in lines.values() for word in row["words"])
    # Prefer distinctive terms introduced by inspected evidence as possible bridges.
    bridges = set(sorted(overlap, key=lambda w: (frequency[w], -overlap[w], w))[:8])
    ranked = []
    for ref, row in lines.items():
        terms = row["words"]
        relevance = len(query & terms)
        bridge = len(bridges & terms)
        if ref not in observed and relevance + bridge:
            score = 2 * len(missing & terms) + relevance + min(bridge, 2)
            ranked.append((-score, -relevance, ref))
    return [ref for _, _, ref in sorted(ranked)]


def _audit(history, lines, budget, remaining, sharing=False):
    count = 0
    charged = 0
    charges = Counter()
    for rnd in history:
        if len(rnd["plan"]) != len(rnd["returns"]):
            raise RuntimeError("missing investigator return")
        for assignment, worker in zip(rnd["plan"], rnd["returns"]):
            observations = worker["observations"]
            if (worker["role"] != assignment["role"] or len(observations) > assignment["inspection_limit"]
                    or worker["sources"] != [o["source"] for o in observations]):
                raise RuntimeError("inquiry assignment audit failed")
            for obs in observations:
                if obs["quotation"] != lines[obs["source"]]["text"]:
                    raise RuntimeError("inquiry quotation audit failed")
                charge = obs.get("charge", 1)
                if type(charge) is not int or charge not in (0, 1) or (not sharing and charge != 1):
                    raise RuntimeError("invalid inquiry charge")
                charges[obs["source"]] += charge
                charged += charge
            count += len(observations)
    if sharing and any(total != 1 for total in charges.values()):
        raise RuntimeError("inquiry shared charge audit failed")
    if charged != budget - remaining or charged > budget:
        raise RuntimeError("inquiry budget audit failed")
    return {"budget": budget, "inspections": charged, "matched_quotations": count}


def investigate(question, directory, budget=12, rounds=2, strategy="legacy"):
    prose(question)
    integer(budget, 0, 24)
    integer(rounds, 1, 2)
    if strategy not in ("legacy", "shared", "shared-gap"):
        raise Invalid("unknown inquiry strategy")
    shared = None if strategy == "legacy" else set()
    lines, manifest = _index(directory)
    query = _words(question)
    keys = {row["key"] for row in lines.values() if row["key"] and query & row["words"]}
    plan = [_assignment(role, f"{question} — {prompt}", 2) for role, (_, prompt, _) in ROLES.items()]
    queues = [_candidates(role, lines, query, keys) for role in ROLES]
    first, remaining = _run_round(plan, queues, lines, budget, shared)
    history = [{"plan": plan, "returns": first}]
    observed = {ref for w in first for ref in w["sources"]}
    followups = []
    next_queues = []
    for key, sides in sorted(_positions(lines, observed).items()):
        if sides["supports"] and sides["challenges"]:
            refs = [r["ref"] for r in lines.values() if r["key"] == key and r["tag"] == "Check"]
            candidates = list(dict.fromkeys(refs + [target for ref in refs for target in lines[ref]["links"]
                                                    if target in lines]))
            followups.append({**_assignment("compare", f"What observation would distinguish the accounts of {key}?", 3),
                              "claim": key, "basis": sorted(sides["supports"] + sides["challenges"])})
            next_queues.append(candidates)
    plain_leads = []
    for source in first[0]["sources"]:
        for challenge in first[1]["sources"]:
            if lines[source]["tag"] is None and lines[challenge]["tag"] is None and source != challenge:
                plain_leads.append({"initial_account": source, "possible_counterevidence": challenge})
                break
        if plain_leads:
            break
    if plain_leads:
        basis = list(plain_leads[0].values())
        followups.append({**_assignment("compare", "Do these passages describe the same time, place and criterion?", 3),
                          "basis": basis})
        next_queues.append(list(dict.fromkeys(target for ref in basis for target in _nearby(ref, lines)
                                              if target not in observed)))
    edges = [{"from": ref, "to": target} for ref in sorted(observed) for target in dict.fromkeys(lines[ref]["links"])]
    trace_targets = list(dict.fromkeys(e["to"] for e in edges if e["to"] in lines and e["to"] not in observed))
    if trace_targets:
        followups.append({**_assignment("trace", "What do the cited passages themselves record?", 3),
                          "basis": sorted({e["from"] for e in edges if e["to"] in trace_targets})})
        next_queues.append(trace_targets)
    if strategy == "shared-gap" and remaining:
        candidates = _gap_refs(lines, query, observed)
        if candidates:
            followups.append({**_assignment("gap", f"Which other passage bears on: {question}", remaining),
                              "basis": sorted(observed)})
            next_queues.append(candidates)
    if rounds == 2 and followups and (remaining or shared is not None):
        workers, remaining = _run_round(followups, next_queues, lines, remaining, shared)
        history.append({"plan": followups, "returns": workers})
        observed.update(ref for w in workers for ref in w["sources"])

    # Rebuild edges from the passages actually disclosed, including the revised round.
    edges = [{"from": ref, "to": target, "status": "inspected" if target in observed else
              "uninspected" if target in lines else "unavailable"}
             for ref in sorted(observed) for target in dict.fromkeys(lines[ref]["links"])]
    explanations = []
    for key, sides in sorted(_positions(lines, observed).items()):
        alternatives = [{"stance": stance, "passage": lines[ref]["text"], "source": ref}
                        for stance, refs in sides.items() for ref in refs]
        checks = [{"source": ref, "proposed_observation": lines[ref]["text"]}
                  for ref in sorted(observed) if lines[ref]["key"] == key and lines[ref]["tag"] == "Check"]
        explanations.append({"claim": key, "accounts": alternatives, "proposed_checks": checks,
                             "status": "disputed" if all(sides.values()) else "one_position_observed"})
    next_steps = [prompt for rnd in history for w in rnd["returns"] for prompt in w["unanswered_questions"]]
    if len(history) == 1:
        next_steps.extend(task["question"] for task in followups)
    for e in explanations:
        if e["status"] == "disputed":
            next_steps.append(f"Compare the original observations for {e['claim']} and retain both explanations pending review.")
            for check in e["proposed_checks"]:
                next_steps.append(f"Review the proposed discriminating observation at {check['source']}.")
    for edge in edges:
        if edge["status"] != "inspected":
            next_steps.append(f"Locate or inspect {edge['to']} before treating the citation as corroboration.")
    stop_reason = "round_limit" if followups else "no_followup_selected"
    if remaining == 0:
        stop_reason = "budget_exhausted"
    return {"profile": "babalon.community-inquiry.v1", "question": question, "documents": manifest,
            "collection_digest": digest(manifest), "rounds": history, "revised_plan": followups,
            "evidence_map": {"explanations": explanations, "unclassified_comparison_leads": plain_leads, "citations": edges},
            "proposed_next_steps": list(dict.fromkeys(next_steps)),
            **({"strategy": strategy} if shared is not None else {}),
            "audit": _audit(history, lines, budget, remaining, shared is not None),
            "stop_reason": stop_reason, "authority_granted": False, "external_actions": 0}

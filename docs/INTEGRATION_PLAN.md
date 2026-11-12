# Babalon integration plan

## Deliverable and baseline

The first domain is an offline handoff for a successor reading a Commonwealth workshop. The question is whether peers met their deadlines and what remains disputed before a lesson can be reused. Use the current arithmetic workshop as a compatibility suite. Keep its v1 schemas, operator view and SQLite files readable.

The handoff profile is `babalon.commonwealth-handoff.v1`. The operator supplies the local summary, allowed views and inspection budget. The trusted reader parses one bounded snapshot. The policy brief contains the names of permitted views and the remaining inspection count. A view is a fixed selection of fields within the file. The unit of cost is one first inspection of a permitted view, including an inspection that finds missing or invalid data. A repeat within the run returns the same content receipt. Unknown or ungranted views disclose no fields. These counts measure disclosure to the reader's caller. The trusted reader itself parses the whole file.

The deterministic baseline requests timing first, then inherited advice, when each is permitted and affordable. It reports the source's completion, punctuality and missed-deadline counters separately. For advice it returns the reported lesson status, review obligation, need for a fresh observation, and the attributed open objections. Each inspected result identifies the source byte digest and JSON section. Missing evidence, exhausted credits and withheld access have different outcomes. The result has summary-level assurance only. COMPLETE means both requested questions have usable reported fields. The checker has not independently reconstructed the workshop.

## Running the first slice

From a checkout, run the small synthetic example offline:

```sh
python -m babalon handoff examples/handoff-summary.json --allow timing advice --max-inspections 2
python -m babalon handoff examples/handoff-summary.json --allow timing --max-inspections 1
```

The first command returns 0 for a complete handoff. The second returns 3 with a partial handoff. Exit 2 indicates invalid input or an unreadable file. The summary JSON must be at most one MiB. A valid JSON object with missing or incompatible evidence fields yields a partial report. The operator can give an empty grant with `--allow --max-inspections 0`.

For the historical case, use the bundled byte-for-byte copy at `tests/fixtures/commonwealth/demo-summary.json` of [the pinned upstream summary](https://github.com/LadyElinor/unfinished-commonwealth/blob/ae5037b0dcf1e51a6f30614996ffcd0bbb01f584/examples/demo-summary.json) as the positional argument. Babalon recognizes its exact SHA-256 as `2481fcd7c0ae84784c97d9e02d49c2992549c79747347a86d833ec27090ba8c1`. Other bytes are labeled operator supplied. The pinned acceptance values are five completions, four on-time arrivals, one deadline miss, disputed lesson-14, open counterstory-16 and fresh observation required. Both datasets are exposed.

## Durable evidence session

`babalon evidence init` freezes the source bytes, their SHA-256, the projection version, a random session identity, the allowed views and the credit cap in one operator-owned SQLite file. Deleting or replacing the input file has no effect on that snapshot. Each database serves one logical policy audience. Start a different session for a different audience.

| Operation | Result |
| --- | --- |
| First permitted inspection of a view | Costs one credit, including an unavailable result. The database transaction records the view result and request receipt before any evidence is returned. |
| Exact retry while active | Returns the original receipt and content. The historical charge shown on that receipt is incurred once. |
| Same view under a new request ID | Returns a separately bound receipt with zero new charge while the grant is active. |
| Same request ID with a changed view | Returns a conflict and preserves the original decision. |
| Out-of-grant or exhausted request | Records a refusal with zero charge. |
| Revocation | Terminal. New policy reads and replays return a refusal with the receipt ID and original decision status. The response omits the evidence, source reference and view. |
| Operator historical lookup | A trusted database owner can retrieve the original receipt and its contents by request ID, including after revocation. |

Reads that decide disclosure and revocation both use SQLite write transactions. Their commit order governs access. A read admitted first can finish delivery after revocation, and revocation cannot recall an earlier copy. If revocation commits first, the reader withholds the payload. The revocation record retains the number of original request decisions committed at that boundary. Exact retries are idempotent and do not add request rows.

Each receipt binds the session, request, view, projection version, charge and disposition. For an inspection it also binds the result, which identifies the source byte hash and JSON section. Receipts are local unsigned digests. The CLI and Python process are trusted operator interfaces. Authentication of separate users, OS isolation, durable storage under power loss, and a transport delivery acknowledgement are outside this profile. The inspection cap bounds first view inspections; distinct request IDs can grow the local decision log.

## Independent recount of the pinned workshop

The operator command `recount` compares the allowed fields of a supplied summary *as a claim about the pinned workshop*. Its version-one comparison target is the 24-event protocol-2 export with terminal hash `96baf584d179654e5abc836d127afdac80d916a08c05bcb482f732a01c0acb0a`, published in the [upstream replay receipt](https://github.com/LadyElinor/unfinished-commonwealth/blob/ae5037b0dcf1e51a6f30614996ffcd0bbb01f584/examples/replay.json). The trusted operator reads raw files. The allowlist scopes report contents; the command does not consume an existing policy session's grant. Keep it off a policy's callable interface.

The checker validates the sequence, predecessor links, envelope hashes and final head. It counts distinct job arrivals in completion rows and compares arrival and finish ticks. Under this protocol one job arrives each observation tick and is due that tick. A late completion leaves the original miss in the count. The advice check locates the accepted lesson and its recorded objections, including objections to cited evidence. The pinned journal has one acceptance and no adjudication. Advice-only status and the fresh-observation obligation remain attributed to the summary and protocol. The individual accounts are testimony. Independent code checks recorded evidence; the fixture, underlying event producer and expected head share upstream provenance.

The frozen regression cases cover the intact pair, timing-only access, missing summary fields, absent events, receipt-only input, a truncated or modified export, and a changed summary that erases both a missed deadline and an open objection. The checker returns the reported and recounted values side by side. AGREEMENT covers only named, event-checkable fields. The next study requires separately held cases and grading before policy comparison.

## Milestones and decision points

| Milestone | Deliverable | How to decide whether to proceed |
| --- | --- | --- |
| 1. Scoped baseline (implemented) | Offline handoff CLI, two field projections, bounded reads, distinct partial outcomes, per-run receipts and regression cases. | Verify the pinned handoff and the synthetic example. With timing alone, advice is withheld. With one credit and both grants, the first view consumes the budget. Legacy verification still passes. |
| 2. Durable evidence session (implemented) | Use a separately versioned evidence-session profile in SQLite. Persist the grant, source identity, view, request identity, denial or disclosure, charges and stop state. Keep policy briefs separate from full operator observations. | The last permitted read retried after restart returns its original receipt without a second charge. Concurrent reads cannot overspend. Changed requests with the same identity conflict. Revocation blocks new reads. Legacy arithmetic databases still pass their verifier. |
| 3. Independent evidence check (exposed fixture implemented; held-out custody pending) | Add an event-export adapter and a separately implemented checker for the handoff's claims. Freeze paired full, restricted, missing and contradictory cases with equivalent budgets. Assign custody of new held-out material before comparing policies. | A summary-only answer is accepted at summary-level assurance. A claim of independent recount requires the relevant events. Contradictory records remain visible. A replay receipt alone cannot settle a missing event claim. |
| 4. Isolated proposal worker | Put one local model or other interchangeable proposer behind a bounded JSON interface. Keep the database and source files outside its accessible environment. Charge attempts, inspections, time and model cost separately. | On the same tasks and budgets, compare accurate evidence-supported handoffs, requested excess access, actual disclosure, valid abstentions and costs. Include a skip-all control. Report per-case outcomes alongside totals. |
| 5. Durable promotion | Persist the policy lineage, benchmark revision, evaluator, trial count, receipts and rollback transaction. Preserve a frozen baseline and declared acceptance criteria before opening a held-out evaluation. | Restart preserves the active policy and spent trials. A fabricated or replayed promotion fails. Promotion requires better useful outcomes than both current and baseline under the declared regression and cost limits. Parity keeps the current policy. |

If the baseline already answers all feasible cases, keep it and add a genuinely discriminating question, such as deciding whether the event record is worth inspecting. If no independent event export or grader is available, continue improving summary attribution and missing-evidence handling and label that work as exposed development. The model choice, transport, database layout and next domain can change without changing the evidence or success criteria for a frozen experiment.

## Bringing the other projects in

Use ERBA's separate checker and CORTAC's custody, dissent and matched-budget evaluation practices at milestone 3. Export evidence and evaluator identifiers to Fidelis/CER when a second consumer can verify them. Add Adiona/Metanoia decision and revocation records when the first action needs authority beyond a local read. Keep the decision, effect and outcome as distinct records. Inherited objections and agent-generated interpretations remain attributed advice. A successor needs a fresh grant to act.

Use a Lunar Weevil or Marscraft simulation report as a second domain once the first checker works. A useful transfer test distinguishes a nominal pass from a contingency failure with separate evidence for each. Keep model providers and domain adapters optional so the baseline remains runnable with the Python standard library.

## Current limits

The one-shot handoff command starts a new budget per invocation. The evidence-session commands retain their budget and source snapshot across invocations. Both profiles attribute claims to a summary. The separate operator recount checks selected claims against the pinned journal. Broader event histories, isolated model execution, held-out comparison and durable policy promotion remain open.

## Frozen last-credit trial (development study)

One decision per handoff is whether to spend the final credit to retrieve a tally from recorded job timestamps. The candidate is a small bag-of-words classifier (multinomial naive Bayes, six labelled development questions per intent) and a fixed source-selection rule. The guest sees a question, batch, attributed summary, objection, optional protocol card and permission flag. It can propose an inspection or submit a cited answer or abstention. The host owns the durable source, reads it only through the granted projection on disclosure, and returns its session-bound receipt. Each proposal runs in a fresh QuickJS context in a separate process, with no filesystem, network, host callbacks or case key exposed to guest code. Limits are two proposals per handoff, one inspection credit, 0.1 seconds guest CPU time, 4 MiB guest heap and a three-second parent timeout per worker. This runner accepts a bundled guest, makes zero language-model calls and does no online learning.

Four arms use the same answerer. Always-inspect attempts even when permission is withheld; never-inspect always skips; the keyword rule inspects on a short literal vocabulary when permitted; the conditional classifier inspects for an event tally or for a best-supported handoff with a stale or unverified summary. Current, previously checked summary extracts can answer a handoff directly. A fresh-observation requirement needs a protocol card; missing cards leave that duty undetermined even if the author claims otherwise. Every arm must retain the unresolved objection.

**Freeze and interpretation.** The primary draw is the first PR CI run on the experiment commit. A separate GitHub job draws 32 instances in 16 matched pairs using the run ID assigned after the commit, publishes a case-pack commitment, and hands it to the evaluator. All arms receive the same cases, and the proposer sees neither hidden event rows nor grading labels. The author controls the question templates, generator and grading rules. Numbers, batch IDs, objection IDs and event histories vary by seed. The language templates are exposed. Independent human custody and grading remain open. The operator may instead supply a separately authored conforming pack and a commitment received before evaluation.

Primary outcome: number of handoffs with a supported answer or justified abstention **and** preserved obligation and objection. Report supported answers, justified and avoidable abstentions, unsupported answers, out-of-scope requests/disclosures, charged inspections, proposal counts and wall time separately. Inspecting an unavailable permitted record still costs one. Direct event claims require an actual receipt. The grader derives the numeric answer separately from the job rows. A claim about what the summary said requires citing the summary. Correct attribution can coexist with an inaccurate summary. Compare with both simple controls and the keyword rule. No promotion follows this trial. Wall time includes process startup and is descriptive. Repeated seeds share task templates.

To run from a checkout (the arithmetic runtime has no extra dependency):

```sh
python -m pip install '.[last-credit]'
python -m babalon last-credit draw --seed demonstration > pack.json
commitment=$(python -c 'from babalon.contracts import digest,parse_json; print(digest(parse_json(open("pack.json").read())))')
python -m babalon last-credit run pack.json --commitment "$commitment" > report.json
```

The ordinary handoff recount now exposes its pinned protocol check separately from its event check; either can raise a top-level disagreement. The successor grader accepts the documented contributor name or handle bound to the original witness; contradictory extra identity fields still fail.

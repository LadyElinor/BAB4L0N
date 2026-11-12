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

For the historical case, use a local copy of [the pinned upstream summary](https://github.com/LadyElinor/unfinished-commonwealth/blob/ae5037b0dcf1e51a6f30614996ffcd0bbb01f584/examples/demo-summary.json) as the positional argument. Babalon recognizes its exact SHA-256 as `2481fcd7c0ae84784c97d9e02d49c2992549c79747347a86d833ec27090ba8c1`. Other bytes are labeled operator supplied. The pinned acceptance values are five completions, four on-time arrivals, one deadline miss, disputed lesson-14, open counterstory-16 and fresh observation required. Both datasets are exposed.

## Milestones and decision points

| Milestone | Deliverable | How to decide whether to proceed |
| --- | --- | --- |
| 1. Scoped baseline (implemented) | Offline handoff CLI, two field projections, bounded reads, distinct partial outcomes, per-run receipts and regression cases. | Verify the pinned handoff and the synthetic example. With timing alone, advice is withheld. With one credit and both grants, the first view consumes the budget. Legacy verification still passes. |
| 2. Durable evidence session | Introduce a separately versioned evidence-session profile in SQLite. Persist the grant, source identity, view, request identity, denial or disclosure, charges and stop state. Keep policy briefs separate from full operator observations. | The last permitted read retried after restart returns its original receipt without a second charge. Concurrent reads cannot overspend. Changed requests with the same identity conflict. Revocation blocks new reads. Legacy arithmetic databases still pass their verifier. |
| 3. Independent evidence check | Add an event-export adapter and a separately implemented checker for the handoff's claims. Freeze paired full, restricted, missing and contradictory cases with equivalent budgets. Assign custody of new held-out material before comparing policies. | A summary-only answer is accepted at summary-level assurance. A claim of independent recount requires the relevant events. Contradictory records remain visible. A replay receipt alone cannot settle a missing event claim. |
| 4. Isolated proposal worker | Put one local model or other interchangeable proposer behind a bounded JSON interface. Keep the database and source files outside its accessible environment. Charge attempts, inspections, time and model cost separately. | On the same tasks and budgets, compare accurate evidence-supported handoffs, requested excess access, actual disclosure, valid abstentions and costs. Include a skip-all control. Report per-case outcomes alongside totals. |
| 5. Durable promotion | Persist the policy lineage, benchmark revision, evaluator, trial count, receipts and rollback transaction. Preserve a frozen baseline and declared acceptance criteria before opening a held-out evaluation. | Restart preserves the active policy and spent trials. A fabricated or replayed promotion fails. Promotion requires better useful outcomes than both current and baseline under the declared regression and cost limits. Parity keeps the current policy. |

If the baseline already answers all feasible cases, keep it and add a genuinely discriminating question, such as deciding whether the event record is worth inspecting. If no independent event export or grader is available, continue improving summary attribution and missing-evidence handling and label that work as exposed development. The model choice, transport, database layout and next domain can change without changing the evidence or success criteria for a frozen experiment.

## Bringing the other projects in

Use ERBA's separate checker and CORTAC's custody, dissent and matched-budget evaluation practices at milestone 3. Export evidence and evaluator identifiers to Fidelis/CER when a second consumer can verify them. Add Adiona/Metanoia decision and revocation records when the first action needs authority beyond a local read. Keep the decision, effect and outcome as distinct records. Inherited objections and agent-generated interpretations remain attributed advice. A successor needs a fresh grant to act.

Use a Lunar Weevil or Marscraft simulation report as a second domain once the first checker works. A useful transfer test distinguishes a nominal pass from a contingency failure with separate evidence for each. Keep model providers and domain adapters optional so the baseline remains runnable with the Python standard library.

## Current limits

Receipts are unsigned content digests. Each CLI invocation starts a new budget. The implementation uses trusted in-process code, reads operator-supplied files and accepts no model plugins. It demonstrates field selection and accounting for this profile. Process isolation, persistent read budgets, independent event verification, held-out comparison and durable promotion are subsequent milestones.

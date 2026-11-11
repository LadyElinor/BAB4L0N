# Design

## Execution path

1. The operator creates a workshop from validated tasks and a finite grant.
2. `observe` returns a snapshot with instance identity, state digest, tasks,
   non-authorizing notes and remaining budgets.
3. A policy proposes one registered operation for one task, or waits/declines.
4. The host validates the closed schema, instance, current view, grant, task
   contract, stop state, pending audit and remaining budgets.
5. Effect, budget charges, receipt and event commit in one SQLite transaction.
6. A separate reduction implementation checks the result before the next effect.
7. Verification checks event hashes, final state binding, receipt binding,
   accounting and task outputs. It does not replay every historical transition.

A valid fresh submission consumes an action even if refused, waiting or declining.
Malformed submissions, conflicting request IDs, exact replays and submissions
past the action limit do not consume a new durable action. An action-limit refusal
is explicitly `durable: false`. Records are charged by all rows processed, not
only rows marked valid. Effects are charged at commit, before audit.

SQLite serializes competing commits. A stale view cannot silently act on changed
state. An exact replay retrieves the old result even after stop; it is not a new
permission. Stop remains visible after audit and takes precedence in runner status.
Verification's `completed` field describes audited task outcomes, so it can be true
for a workshop whose runner status is `STOPPED`.

Audit failure preserves the effect and pending obligation rather than pretending
nothing happened. Initialization errors clean up only the newly created file when
possible. Abrupt process termination or power loss during initialization is not
an atomic publication protocol and may require operator inspection.

## Improvement path

The mutable object is three parameters: each objective maps to one of the three
registered tools. Search enumerates 27 possible mappings using development cases.
The trusted gate scores the candidate itself; callers cannot provide a score.
Promotion requires a changed mapping, strict development improvement and no
exposed-evaluation regression. It also requires an exact gate-issued receipt,
matching candidate and parent digests, a current epoch and an unused receipt.

Rollback restores the previous mapping and advances the epoch. It does not reset
the per-instance evaluation budget. Gate state, history and evaluation count live
in memory only. Reconstructing a new gate starts a new search instance. The demo
performs one promotion; it does not implement persistent recursive improvement.
The evaluator receives no execution grant through the candidate or its score.

## Memory

The operator may add up to 64 lesson/objection notes, each with bounded text and
optional references to existing receipts. Notes are labeled
`operator_supplied_unverified` with authority `NONE`. Receipt existence is checked;
semantic support for the prose is not. Policies can read notes, but the included
policies do not learn from them. Retaining an objection is not adjudicating it.

## Roadmap, not implemented capability

1. **Useful task:** choose a concrete domain and success metric before adding
   unrestricted tools. Keep tools read-only or reversible initially.
2. **Model policy:** run a model or other untrusted policy outside the trusted
   host, accept only closed proposal JSON, and enforce time/token/cost ceilings.
3. **Durable learning:** store candidate, parent, evaluator version, trial budget,
   issued result, promotion and rollback in an atomic registry. Do not reset
   evaluation allowance on process restart.
4. **Fresh evidence:** freeze the baseline and candidate-generation rules, then
   evaluate on independent fresh tasks with a declared metric and search budget.
   Exposed examples must never be relabeled as sealed holdouts.
5. **Source changes:** if code proposals become necessary, run them in an isolated
   test environment. Keep evaluator, host, credentials and grants outside the
   candidate's write scope. Promotion must not silently add tools or permissions.
6. **External adapters:** define immutable intent, idempotency, outcome lookup,
   uncertain-outcome handling and owner authorization before any live action.

The scaffolding gives these boundaries somewhere concrete to attach. It does not
establish that a future implementation of them will be intelligent or safe.

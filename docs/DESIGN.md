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

If a second client completes an audit before the runner's audit call, a
`NO_PENDING_EFFECT` response is accepted only when the particular affected tasks
are already audited (`done`) and independent verification reports `CONSISTENT`.
A missing obligation alone is not success; genuine audit failures still fail closed.

Audit failure preserves the effect and pending obligation rather than pretending
nothing happened. Initialization errors clean up only the newly created file when
possible. Abrupt process termination or power loss during initialization is not
an atomic publication protocol and may require operator inspection.

## Improvement path

The mutable object is three parameters: each objective maps to one of the three
registered tools. Search enumerates 27 mappings using development cases. Scheduling
first filters through the default policy's task grant, operation grant and remaining
record/effect budget; a mapping can only change the proposed operation, never grants.
An incorrect mapped operation remains subject to the host's contract checks.

The trusted gate runs active, default and candidate policies on separate fresh hosts
for every fixed execution scenario. It counts authorized audited task completions,
checks consistency, unchanged grants, scope, budgets and discharged audit obligations.
Promotion requires a changed mapping, strictly greater total completion than both
active and default, no per-scenario regression against either, and safe execution.
Selector scores are retained as diagnostics and cannot authorize promotion.
The scenario specification and benchmark identity are bound into evaluator receipts.

Promotion additionally requires exact gate-issued receipt bytes, matching candidate
and parent digests, current epoch and unused receipt. Rollback restores the prior
mapping and advances the epoch without resetting evaluation budget. State remains
in memory; constructing a new gate starts a new evaluation budget. The evaluator is
trusted in-process code, not a sandbox or cryptographic authority.

The demo starts from the default identity mapping and reports `NOT_PROMOTED` on
parity. The bounded mapping space cannot outperform the default; the old weak
baseline is merely a separately labeled reference. All execution fixtures are
public regression cases, not held-out validation or evidence of generalization.

## Memory

The operator may add up to 64 lesson/objection notes, each with bounded text and
optional references to existing receipts. Notes are labeled
`operator_supplied_unverified` with authority `NONE`. Receipt existence is checked;
semantic support for the prose is not. Policies can read notes, but the included
policies do not learn from them. Retaining an objection is not adjudicating it.

## Commonwealth handoff

The read-only handoff command uses a separate evidence profile with two projected
views. Its per-invocation budget and source-level assurance are described in the
[integration plan](INTEGRATION_PLAN.md). Arithmetic workshops retain their v1
schema and operator view.

## Runtime roadmap

1. **Useful task:** use the Commonwealth handoff to test evidence-supported completion before adding
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

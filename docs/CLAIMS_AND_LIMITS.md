# Claims and limits

## Demonstrated locally

- Actual execution of three bounded integer-data operations.
- Durable host state, finite attempt/effect/record accounting and operator stop.
- Transactional effect/receipt writes, exact replay and concurrent submission tests.
- Mandatory post-effect checking before another effect, with restart recovery.
- A separate result-check implementation, sharing the same specification and data.
- A closed proposal interface which cannot introduce shell, grant or evaluator fields.
- A bounded automatic improvement in method selection among 27 maps.
- Gate-issued receipt binding, stale-parent/epoch rejection, rollback and per-instance
  evaluation accounting.

## Not demonstrated

- General intelligence, agency comparable to a person, open-ended learning,
  generalization, learned planning or recursive source-code improvement.
- Model-backed behavior: the included policies are deterministic fixtures.
- Learning from repository code or prose at runtime. Existing work informed
  architectural choices; there are no repository integrations in this runtime.
- Persistent learned policy or evaluation limits across gate reconstruction.
- Independent evaluator cognition, authenticated receipts, secure clocks,
  process isolation, production security or real-world safety.
- Full historical transition replay or resistance to a trusted database owner's
  coherent rewrite. Local digest consistency is not authentication.
- General crash/power-loss recovery. Tests cover injected transactional exceptions
  and clean process restart, not every OS/filesystem failure.

## Interpretation of the improvement numbers

The weak baseline maps all objectives to `sum_valid`. The best map is the identity
map. The expected tool name appears directly in the task contract, and all three
objectives occur in both exposed scoring sets. Exhaustive search finds that map.
This is a transparent demonstration of a promotion mechanism, not a discovery
about machine intelligence. There are no confidence intervals, independent
holdouts or statistical superiority claims.

The before/after execution uses identical fresh tasks and grants on separate hosts.
One baseline task completes before the next incorrect operation is refused; the
candidate completes all three. Refusal is not counted as successful completion.

## Operational limits

All Python callers, the filesystem/database owner and the evaluator are trusted.
An arbitrary Python policy can ignore this protocol, hang or modify process state.
Budgets cap accepted protocol activity, not CPU, memory, wall time or operator calls.
The note limit and submission limits are not a complete disk-use or denial-of-service
boundary. Do not expose the raw CLI as a multi-user authorization service.

No upstream license is inferred from visibility, and no external permission follows
from a passing test, a note, a receipt or a promoted policy. The archive includes no
upstream code or dependencies and does not choose a distribution license for the owner.

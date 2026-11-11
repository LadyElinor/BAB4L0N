# Claims and limits

## Demonstrated locally

- Actual execution of three bounded integer-data operations.
- Durable host state, finite attempt/effect/record accounting and operator stop.
- Transactional effect/receipt writes, exact replay and concurrent submission tests.
- Mandatory post-effect checking before another effect, with restart recovery.
- A separate result-check implementation, sharing the same specification and data.
- A closed proposal interface which cannot introduce shell, grant or evaluator fields.
- Bounded selection among 27 maps, with execution-based rejection of default parity.
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

The default policy already reads the operation directly from the task contract.
The identity mapping uses the same grant-aware scheduler and produces identical
proposals. No map in the current closed candidate space can improve this policy.
The correct gate outcome is therefore `NOT_PROMOTED`, including when a candidate
improves on the old all-`sum_valid` demonstration policy. A richer candidate space
and a justified task domain are needed before real improvement is possible.

The trusted evaluator counts tasks only after audit and consistency verification,
and only if both task ID and objective are authorized. Fresh hosts and identical
budgets are used for every policy in each of 30 scenarios. A partial grant can
complete all its authorized tasks while whole-workshop `completed` remains false;
runner status and method-selection accuracy are not the completion score.

The suite reports 36 completed out of 75 authorized for both default and candidate.
Budget and cycle restrictions deliberately make some authorized work unattainable.
These totals are paired regression measures, not optimality or success-rate claims.
Aggregate gains cannot offset a per-scenario regression. The execution reducer is
separate from the candidate but shares specification, inputs and Python process.
There are no confidence intervals, sealed holdouts or statistical superiority claims.
Gate construction still resets the in-memory evaluation budget.

Tests for promotion/rollback receipt lifecycle inject hypothetical eligibility to
exercise otherwise unreachable branches; they are not evidence of an actual winning
candidate. Real unmodified gate tests require all current candidates to fail parity.

## Operational limits

All Python callers, the filesystem/database owner and the evaluator are trusted.
An arbitrary Python policy can ignore this protocol, hang or modify process state.
Budgets cap accepted protocol activity, not CPU, memory, wall time or operator calls.
The note limit and submission limits are not a complete disk-use or denial-of-service
boundary. Do not expose the raw CLI as a multi-user authorization service.

No upstream license is inferred from visibility, and no external permission follows
from a passing test, a note, a receipt or a promoted policy. The archive includes no
upstream code or dependencies and does not choose a distribution license for the owner.

# Validation record

Date: 2026-11-11. Local CPython 3.12.14 on Linux.
Source baseline: LadyElinor/BAB4L0N commit
`46a58e6c97c2b4c4c267f46dd74280e073ae8853`. Retrieved through the GitHub connector;
the local baseline snapshot matches every entry of its upstream SHA256SUMS.
No remote commit, push or deployment is included in this revision.

## Passed

- `python scripts/verify.py`: 57 unit tests plus fresh-process execution demo,
  consistency check, completed-workshop restart and default-parity evaluation.
- `python -O scripts/verify.py`: same checks with Python assertion removal.
- `python -m compileall -q babalon tests scripts`: source compilation.
- Offline wheel build with `--no-index --no-deps --no-build-isolation`.
- Fresh virtual-environment offline wheel installation: console entrypoint,
  execution demo, consistency verification and `NOT_PROMOTED` evaluation.
- Independent review repeated the 56-test suite before the final exhaustive-map
  regression test was added, plus all subprocess checks. It separately evaluated
  all 27 mappings: maximum completion was 36/75, with identity the sole tie.
- The final test suite now includes the exhaustive 27-map non-superiority check.

The supplied CI matrix targets Python 3.11, 3.12 and 3.13. Remote CI was not run;
only local Python 3.12.14 was tested. No configured linter or static type checker
is present, and neither was run.

## Review findings resolved

1. Weak-baseline improvement did not establish improvement over the default.
   The default is now the mandatory benchmark. Actual audited authorized task
   completion replaces selector accuracy as the promotion metric.
2. First-pending scheduling stalled on unauthorized or unaffordable tasks. The
   mapping policy now uses default grant/budget filtering. Six tail-only and
   tight-record cases reproduce old completion 0 versus default completion 12.
3. A second client could audit before the runner, causing false `AUDIT_FAILED`.
   Two-client regression tests reproduce the old failure. Recovery now requires
   the affected tasks to be done and verification to be `CONSISTENT`. Unresolved
   obligations, corrupted state and genuine audit failures remain failures.
4. Aggregated improvement cannot hide a regression: every scenario must match
   or exceed both active and default completion, with strict aggregate gain.

## Interpretation and evidence

`reports/improvement.json` contains the actual gate receipt and per-scenario
execution results. Default and candidate complete 36/75 authorized tasks across
30 scenarios, so no promotion occurs. Budgets deliberately prevent some authorized
tasks from running: 75 is not a feasible-completion oracle. Fixtures are fully
exposed and cannot establish generalization or statistical superiority.

`reports/verification.txt` lists final tests and subprocess check results.
`reports/wheel-build.txt` and `reports/installation-smoke.txt` record build and
isolated installation checks. Receipt lifecycle tests inject hypothetical gate
eligibility only to exercise promotion/rollback mechanics; these are not real
winning-candidate evidence.

Packaging reruns checks and generates SHA256SUMS. The delivered source archive is
also extracted, its manifest checked and the aggregate check rerun before delivery.
See `CLAIMS_AND_LIMITS.md` for the trusted in-process boundary and remaining limits.

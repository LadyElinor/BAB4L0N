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

## 2026-11-12 — Stage one review

The scoped Commonwealth reader at `3f2b9953261e4d17e17383dd76eaad3f08c86470`
passed 64 local tests and fresh-process checks. [PR #1 CI](https://github.com/LadyElinor/BAB4L0N/actions/runs/43225942436)
passed on Python 3.11, 3.12 and 3.13. The review reproduced five completions,
four on-time arrivals, one deadline miss, the open objection and the requirement
for a fresh observation. This is evidence of faithful summary extraction.

## 2026-11-12 — Durable sessions

The nine added tests cover the pinned offline fixture, snapshot retention after
source replacement and deletion, request binding, scoped and revoked responses,
cached views, conflicts, durable refusals, competing last-credit inspections,
concurrent exact retries and revocation racing a read. Fresh CLI processes
exercise the policy replay and the separate operator history command.

Process-death tests exit a real subprocess inside the transaction after the
charge and before the receipt, and separately after commit before delivering a
reply. The first run restores the credit and leaves no receipt. The second
retains one charge and returns the original result on retry.

The full 73-test suite and fresh-process checks passed locally on CPython
3.12.14 and 3.13.5. The three concurrency cases also passed in 20 repetitions
each. These checks cover the tested SQLite process boundaries and summary
fixture. Independent verification of workshop events remains a later stage.

## 2026-11-12 — Independent event recount

Using upstream revision `ae5037b0dcf1e51a6f30614996ffcd0bbb01f584`, ran
`python scripts/reproduce.py NEW_DIRECTORY`. The generated summary matched the
existing fixture byte for byte. The 18,129-byte event export has SHA-256
`2c37600b7d200f768c5a0c7afe45182388ba48929779dff307fca3b63b6c328a`.
The checker matched the published 24-event head and reproduced five completions,
four same-tick completions and one historical miss. Event 5 records the missed
tick-2 deadline. Event 13 records the tick-2 job completing at tick 3.
Events 14, 15 and 16 record the lesson, acceptance and counterstory.

Changing only the summary's miss count to zero and clearing its list of open
objections yielded two explicit differences. A receipt alone, truncated prefix,
altered final envelope and broken link failed the journal check. Six new
regression tests brought the full suite to 79. All tests and subprocess demos
passed locally on Python 3.12.14 and 3.13.5. The checker imports no Commonwealth
runtime and makes no model calls. All cases are exposed.

## 2026-11-12 — Owed remedy and a continuing objection

All 107 tests and the fresh-process demos passed on Python 3.12.14 with the
optional last-credit dependency installed. Ten tests cover the remedy profile.
The upstream case supplied alone left all 100 units unverified. A separate
synthetic receiving register supported 100 units of net credit. An optional
report of unusability produced a disagreement while preserving the credit,
the person's choices, the rule inquiry and the correction reported for other-8.
Changing the participation choices affected neither the award nor the warning.
These exposed test records share custody. No real recipient was contacted.

## 2026-11-12 — Voluntary accounts outside the original vocabulary

The three CLI cases used identical inputs except for the voluntary account.
The no-account case kept the personal outcome unknown. The late-credit and
freedom-to-leave accounts each produced a distinct resolvable reference and
the same unclassified status. All three reported a 100-unit credit, an open
rule inquiry and no external actions. All 112 tests and the fresh-process demos
passed on Python 3.12.14 with the optional last-credit dependency installed.
Across four exposed packets, per-bearer burden counts matched the pinned
Commonwealth reducer at `00870ca`, including optional, zero and unknown costs.
The cases exercise record keeping. Affected people have yet to evaluate it.

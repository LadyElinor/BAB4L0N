# Validation record

Date: 2026-11-11. Locally executed with CPython 3.12.14 on Linux.

## Passed

- `python scripts/verify.py`: 46 unit tests plus fresh-process execution demo,
  consistency check, completed-workshop restart and improvement demo.
- `python -O scripts/verify.py`: the same checks with Python assertion removal;
  verification gates use explicit failures rather than `assert`.
- `python -m compileall -q babalon tests scripts`: source compilation.
- Offline wheel build using already installed setuptools and wheel, with
  `--no-index --no-deps --no-build-isolation`.
- Installation of the resulting wheel into a fresh virtual environment without
  network access or source checkout on the import path. The console entrypoint,
  execution demo, consistency verification and improvement demo passed.
- Independent review repeated all 46 tests and the fresh-process checks after
  fixes, and independently probed connection closure on normal/error paths.

The supplied GitHub Actions workflow targets Python 3.11, 3.12 and 3.13. Those
remote matrix jobs have **not** run; only 3.12.14 was tested here. No configured
linter or static type checker is included, and neither was run.

## Findings fixed during review

1. A stop after the final effect could be reported as completion. Stop now takes
   precedence at runner entry and cycle-limit exit, with regression tests.
2. Initialization failure could leave an unusable file that prevented retry.
   Exception cleanup now removes only the file this initialization created.
   Connections also close explicitly on successful and failed operations.
3. JSON exponent overflow such as `1e999` bypassed `parse_constant` rejection.
   A finite-float parser now rejects it, including the negative variant.
4. The improvement candidate previously continued the baseline's partial work.
   The demo now compares separate fresh hosts with identical inputs and grants.

## Evidence

- `reports/verification.txt`: full test names and aggregate check outcome.
- `reports/improvement.json`: actual candidate, gate receipt, selection scores
  and before/after execution results.
- `reports/wheel-build.txt`: local wheel build output.
- `reports/installation-smoke.txt`: isolated installation check.

The source archive includes a `SHA256SUMS` byte manifest. Packaging is performed
with `python scripts/package.py OUTPUT.zip`, which reruns the aggregate check.
Archive extraction and its aggregate check are additionally verified before delivery.

These checks establish behavior on the tested examples, not production security,
independent evaluator authority or broad intelligence. See `CLAIMS_AND_LIMITS.md`.

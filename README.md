# Babalon

**A runnable foundation for bounded, evidence-checked agents and measurable policy improvement.**

Version 0.1.0 is a local research prototype, not a general intelligent machine.
It executes real integer-data tasks, persists their outcomes, checks its work,
and demonstrates a small automatic improvement to its task-selection policy.
It does not train a model, rewrite its own code, or learn from repositories at runtime.

## Run in two minutes

Python 3.11 or later. The runtime, tests and demos need only the standard library.
No API key, network connection or package installation is needed. From this directory:

```sh
python scripts/verify.py
python -m babalon improve-demo
python -m babalon demo workshop.sqlite
python -m babalon observe workshop.sqlite
python -m babalon verify workshop.sqlite
```

Use a new database filename each time you run `demo` or `init`. Existing files
are never overwritten. `run` reopens an existing workshop and resumes unfinished
work; an unaudited committed result is checked before another effect can occur.

The improvement demo searches all 27 allowed objective-to-tool maps. Starting
from a deliberately weak policy, it raises development selection accuracy from
1/3 to 3/3 and exposed evaluation selection accuracy from 1/4 to 4/4. On **two
fresh hosts with identical tasks and grants**, baseline execution completes 1/3
tasks before a contract refusal; the promoted mapping completes 3/3. These are
fully exposed fixtures, not evidence of general intelligence or generalization.

## Use your own bounded task inputs

```sh
python -m babalon init my-workshop.sqlite --tasks examples/tasks.json --grant examples/grant.json
python -m babalon run my-workshop.sqlite --max-cycles 32
python -m babalon verify my-workshop.sqlite
```

Each task chooses exactly one operation: `sum_valid`, `count_valid`, or `max_valid`.
Only readings with `valid: true` count. An empty valid set sums to 0, counts as 0,
and has maximum `null`. All values are bounded integers; booleans are not integers.
The sample grant permits two tasks, two operations, eight submission attempts,
two committed effects, and five processed records. Grants are operator inputs,
not something a policy can grant itself.

Other commands:

```sh
python -m babalon stop my-workshop.sqlite --reason "Operator requested a halt"
python -m babalon note my-workshop.sqlite --kind objection --text "This lesson needs more evidence"
python -m babalon observe my-workshop.sqlite
python -m babalon submit my-workshop.sqlite proposal.json
python -m babalon audit my-workshop.sqlite
```

`submit` accepts only the closed proposal schema. Use the Python
`babalon.agent.envelope()` helper with a current `observe()` result to construct
one. An exact replay returns the original receipt without another effect. A
changed proposal with the same request ID is refused as a conflict.
`stop` is terminal for this workshop; there is no resume or grant-expansion command.

CLI exit codes: 0 for successful commands, 2 for invalid input or failed
consistency/audit checks, 3 for refusal, waiting, stopping or an exhausted limit.
`verify` can report a consistent but unfinished workshop with exit code 0;
inspect its `completed` field as well. Consistency is not authorization.

Optional installation provides the `babalon` console command:

```sh
python -m pip install .
```

Installation may fetch the setuptools build dependency. Direct `python -m babalon`
use above does not. There are no runtime third-party dependencies.

## What is here

- `babalon/contracts.py`: bounded inputs, closed records and canonical digests.
- `babalon/host.py`: grant enforcement, SQLite transactions, receipts, audit,
  operator stop and attributed notes.
- `babalon/agent.py`: proposal-only policy interface and finite orchestration.
- `babalon/improvement.py`: bounded parameter search, promotion and rollback.
- `tests/`: normal, failure, replay, restart, concurrency and mutation tests.
- `docs/DESIGN.md`: architecture and extension boundaries.
- `docs/CLAIMS_AND_LIMITS.md`: exactly what has and has not been established.
- `docs/REPOSITORY_LESSONS.md`: conceptual links to existing work.
- `docs/VALIDATION.md` and `reports/`: validation evidence and audit fixes.

## Trust boundary

The host, Python process, operator CLI, database owner and promotion evaluator
are trusted. This is not an operating-system sandbox. Do not execute an untrusted
Python policy in this process. To connect a model later, pass it only the bounded
observation and accept only proposal JSON; host checks must remain outside the
model. Notes and evaluation scores cannot enlarge grants.

The only effects are local SQLite task results. There is no shell, network,
browser, messaging, credentials, deployment or real-world execution adapter.
Hash chains detect certain inconsistent edits, not an owner rewriting the whole
database. Runtime budgets do not cap arbitrary policy computation.

## Next useful milestone

Choose one useful domain, implement a read-only or reversible tool adapter, and
freeze its task contract and evaluation plan. Add an isolated proposal-producing
model with explicit runtime/cost limits, then compare frozen and improving policies
on fresh independently held-out tasks. Persist candidate lineage, promotion and
rollback before making any claim about durable self-improvement. See the staged
plan in `docs/DESIGN.md`.

No repository push, remote publication or deployment is part of this bundle.

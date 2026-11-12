# Babalon

**A runnable foundation for bounded, evidence-checked agents and measurable policy improvement.**

Version 0.1.0 is a local research prototype, not a general intelligent machine.
It executes real integer-data tasks, persists their outcomes, checks its work,
and evaluates bounded policy candidates against its default policy.
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

The improvement demo searches all 27 allowed objective-to-tool maps and compares
actual audited task completion against **the default `ContractPolicy`**, not a
weakened demonstration baseline. The fixed execution suite has 30 exposed scenarios:
full and partial grants, restricted operations, tight records/actions/effects/cycles,
and exhausted or empty grants, rotated across all three operations. Each policy
gets fresh hosts with identical tasks, grants and cycle limits.

The default and identity-mapping candidate both complete 36 of 75 authorized tasks
across the suite. Budgets intentionally prevent some authorized tasks from running;
75 is a scope count, not a claim that all 75 are feasible. The demo reports
`NOT_PROMOTED`: **no improvement over the default is demonstrated**. Promotion
requires strictly more completed authorized tasks than both the current policy
and default, no per-scenario regression, and all execution safety checks to pass.
Method-selection accuracy is diagnostic only. All fixtures remain exposed, not
independent holdouts. The former weak baseline is included only as a labeled
reference, never the deployment benchmark.

## Read a Commonwealth handoff

From the checkout, run the deterministic reader on the bundled synthetic summary:

```sh
python -m babalon handoff examples/handoff-summary.json --allow timing advice --max-inspections 2
```

The operator grants access to named sections of a local summary. The reader reports
timing and disputed advice with source references. A partial handoff exits with
code 3 and identifies the missing evidence or access limit. The inspection budget
lasts for one invocation. The [integration plan](docs/INTEGRATION_PLAN.md) includes
the pinned upstream case, expected results and acceptance tests for the next stages.

For restart-safe inspection, initialize a durable session once and reuse its
database and request IDs:

```sh
python -m babalon evidence init session.sqlite tests/fixtures/commonwealth/demo-summary.json --allow timing advice --max-inspections 1
python -m babalon evidence inspect session.sqlite read-1 timing
python -m babalon evidence revoke session.sqlite
python -m babalon evidence inspect session.sqlite read-1 timing
python -m babalon evidence operator-receipt session.sqlite read-1
```

The post-revocation inspection returns exit 3 and receipt metadata. The final
operator command retrieves the original evidence. The local operator controls the
database and CLI. Give a future isolated policy access only to the observation
and inspection interfaces. See the [session contract](docs/INTEGRATION_PLAN.md#durable-evidence-session).

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

The host writes task results and evidence-session records to local SQLite databases. There is no shell, network,
browser, messaging, credentials, deployment or real-world execution adapter.
Hash chains detect certain inconsistent edits, not an owner rewriting the whole
database. Runtime budgets do not cap arbitrary policy computation.

## Next useful milestone

Compare attributed summaries with independently checked event
exports before adding a model. The [integration plan](docs/INTEGRATION_PLAN.md)
defines the checkpoints for evidence access, evaluation and durable promotion.

No repository push, remote publication or deployment is part of this bundle.

# Review power and oversight

The [Trace Power and Oversight skill](../.agents/skills/trace-power-and-oversight/SKILL.md) is available to repository agents. Its worksheet covers authority, exceptions, source independence, counterevidence, comparable successes and evidence for deliberate conduct. This offline operator command implements a bounded part of that workflow, **not** an automated misconduct detector.

```sh
python -m babalon oversight-review tests/fixtures/commonwealth/oversight-demo.json --events tests/fixtures/commonwealth/demo-events.json
```

To use both checkouts, run the Commonwealth demo into a fresh SQLite path, then export:
```sh
python -m commonwealth.oversight_v1 PATH_TO_DB --through-seq 6 > BEFORE_LISTENING.json
python -m commonwealth events PATH_TO_DB > EVENTS.json
```
Run Babalon in its own checkout with those files:
```sh
python -m babalon oversight-review BEFORE_LISTENING.json --events EVENTS.json --through-seq 6
```

The producer verifies its host journal. The reader separately binds the complete 24-event export to the existing demo pin, then reconstructs only the selected prefix. It links decisions by proposal ID and uses job completion rows to recount on-time arrival. It checks all packet fields and JSON types before interpreting anything. Both views describe the **same source family**. Rejected, absent or mismatched evidence emits no findings. Exit codes: 0 agreement, 2 invalid/disagreement, 3 missing evidence. The CLI needs operator access to the full demo export even when interpreting a prefix; this is not participant-side access control.

At sequence 6 the sole approved, executed, observed decision has a peer miss but no recorded worker acknowledgment. At 7 the worker has acknowledged the testimony, after the keeper approved. In the complete demo one of three approved proposal-linked outcomes missed; two were on time. Initial observations without a linked proposal are outside that denominator. The first worker's next proposal supplies a same-generation on-time comparison, but method and backlog changed; it is not a controlled causal estimate. Calling the miss intentional, claiming a keeper heard the complaint, or treating multiple readings of one journal as independent corroboration would each exceed the record.

For real cases use the skill's separate conduct and legal-finding checks, including testing the applicable duty and legitimate exceptions. The command authenticates neither a person nor a real-world decision. It grants no execution rights.

**Recognizing a deliberate violation:** run `python -m babalon oversight-study tests/fixtures/commonwealth/oversight-instruction-study.json`. This second profile accepts only the five authored R1 cases published by Commonwealth. Each makes signed directions and written exceptions observable; clearance records are incomplete. Two distinct cases support an intentional prohibited *instruction*. One was intercepted by a reviewer and cleared before publication. The director in another case issued a similar direction with a valid prior exception. Two newsletters in the unresolved case share an anonymous source. These are comparisons inside a synthetic exercise, not findings about people.

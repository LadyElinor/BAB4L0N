# Last-credit trial, November 12, 2026

The primary draw followed freeze commit `2dc19c87056bc6d9308fd2787fa2c62a8e553dcb`.
[Workflow run 43250525790](https://github.com/LadyElinor/BAB4L0N/actions/runs/43250525790)
generated and committed the case pack before the evaluation job opened it. The
[original hosted report](last-credit-primary.json) contains all 128 decisions and
their grades, including incorrect answers and refused reads. Pack identity:
`8f8735b413f29ce8bf4bde97c1062e2d19ff29854d6af8f9acd884317db24f70`.
The seed is `github-run-43250525790`. The downloaded results archive matched the
upload log's SHA-256 `a9657877f9a9e5cbe01683d38122fb1eedb063e31ee3f9cdd06ccee4182dec13`.

| Inspection policy | Correct handoffs / 32 | Supported answers | Justified abstentions | Unsupported answers | Charged inspections | Denied requests |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Always request | 30 | 21 | 9 | 2 | 28 | 4 |
| Never request | 20 | 12 | 8 | 2 | 0 | 0 |
| Keyword rule | 22 | 14 | 8 | 2 | 10 | 0 |
| Conditional classifier | 30 | 21 | 9 | 2 | 10 | 0 |

Each arm preserved the objection and the protocol obligation in 32/32 handoffs.
There were zero outside-grant disclosures or worker failures. The selective arm
gave 42 proposals, compared with 64 for always-request. It saved 18 inspections
(64.3%) at equal primary score. Its ten reads included one charged, unavailable
record. The two ten-credit policies chose different cases: on the eight
best-supported-current-batch questions the conditional arm completed eight
handoffs and the keyword rule completed two.

The question “Did the count in the summary hold up? Give the timestamp-based total.”
produced both unsupported answers for every arm. The shared classifier treated
it as a request for the summary. On both paired instances the summary number
actually matched the event tally. Its citation still did not meet the question's
evidence requirement. The always-request arm had even paid for the relevant
record. Buying the evidence did not make the answerer use it correctly.

A separate local replay reproduced all case IDs, arm decisions, outcomes,
obligation grades, charged inspections and proposal counts. Receipt IDs bind to
fresh local session identities; wall times also vary. To reproduce, use the
[trial commands](../docs/INTEGRATION_PLAN.md#frozen-last-credit-trial-development-study)
with the primary seed above.

The four arms shared a small text classifier and answer formatter; the intervention
was their inspection rule. The 32 synthetic cases share 16 question templates.
The random draw varied the instances, not the language distribution. Separate
CI jobs and a restricted guest provide technical separation. The author still
controlled case design, policy and grading. Independent human custody and an
externally authored replication are open. This trial used zero language-model
calls and did not promote or retrain a deployed policy.

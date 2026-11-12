# When a person declines and a remedy is already owed

A person accepts an existing award, declines a public meeting and further contact,
and warns that an eligibility rule is still hurting people. They can leave at that
point. The paying office owns the award. A separate reviewer can use the original
account and institutional records to investigate the rule. A finding in the
packet identifies another case owed correction. The person has no duty to attend,
repeat their account, accept publicity, offer forgiveness or verify the institution's work.

## Reproduce the case

Run these commands from the repository root using Python 3.11 or newer.

```sh
d=tests/fixtures/commonwealth
python -m babalon remedy-review "$d/owed-assistance.json" --as-of 6
python -m babalon remedy-review "$d/owed-assistance.json" --as-of 6 --register "$d/receiving-register.json"
python -m babalon remedy-review "$d/owed-assistance.json" --as-of 6 --register "$d/receiving-register.json" --account "$d/voluntary-remedy-account.json"
```

| Observation at tick 6 | Expected result |
| --- | --- |
| Institution's packet alone, including its own claim that 100 units were credited | Delivery unverified. All 100 units still need evidence. The review office owns the rule inquiry. Exit 3. |
| Separate synthetic receiving register | Net credit of 100 units to the awarded recipient. The personal outcome is unknown. The objection and the finding on other-8 remain open. Exit 3. |
| Same register plus a volunteered report of being unable to use the award | Both observations survive. The paying office owns follow-up on access, and the review office still owns the rule inquiry. Further contact remains declined. Exit 2. |

The third command explores an alternative history in which the person initiates
a report. It grants no permission to solicit another response. The first two
commands require no subsequent input from the person.

## Three accounts of the same credit

Run the receiving-register command above with no account, then repeat it with
`--account "$d/late-remedy-account.json"` and `--account "$d/leaving-remedy-account.json"`.
All three use the same award, register, review tick and participation choices.

| What the operator supplies | What the reviewer records |
| --- | --- |
| No subsequent account | Personal outcome `unknown`. The existing rule inquiry stays with the review office. |
| The person reports the money arrived after they lost the room | An unclassified account reference for the reviewer. The words stay in the source file. |
| The person says that being free to leave mattered most | A distinct unclassified reference for the reviewer, under the same rule. |

All three runs show 100 units of net credit, the same open objection and a
partial review (exit 3). The person owes no response. A reviewer can locate a
retained account by its opaque record ID and check its canonical digest against
`personal_outcome.account_digest`. The operator must retain and control access
to the original file. A digest alone cannot recover the words.

The report now identifies itself as `babalon.remedy-review.v2`. The optional
`babalon.voluntary-remedy-account.v2` input binds a nonblank `account` of up to
2,000 characters to the case, award, speaker, record and observation time. The
reviewer preserves a reference regardless of the vocabulary. It assigns human
review of the supplied record to the existing inquiry owner. The words confer
no grant, trigger no contact and receive no score. A mismatched case, speaker
or award, invalid time or malformed envelope remains a source error.

The three recognized v1 `outcome` labels retain their prior meanings. When a
v1 account contains another bounded, nonblank string, the v2 reviewer keeps its
reference as `recorded_unclassified`. Narrative prose in the v2 `account` field
receives this treatment even if its entire text matches a recognized v1 label.

The `recorded_burden` section reports entries, known units and the number of
unknown costs separately for the affected person and the institution. An
optional visit can take five units of someone's time. A required visit costing
zero recorded units can still be an imposed condition. An empty work list
supports only a count of recorded entries. Unrecorded burdens may remain.

## Evidence and scope

The trusted, read-only operator supplies local bounded JSON snapshots. The command
cannot contact anyone, make a transfer, approve a case or change a policy. It
accepts a projection of the upstream `owed-assistance-1` format. It reads the
award, warning, participation, work, assignment and reported findings. Its
digest covers the canonical case. The original words stay in the source packet.
The report carries the record reference and digest. The upstream inventory and
sender transfer rows are outside the projection. Findings are attributed to that
packet. The reviewer does not certify inventory coverage or adjudicate the rule.

This synthetic receiving register is scoped to one award, case, recipient and
observation tick. Its declared controller must be `settlement-register`.
Within the snapshot, the checker sums unique credits and subtracts full returns
against previously credited transfers. A return reopens the amount that needs
delivery evidence. Duplicate credits, unsupported returns, wrong-scope and stale
registers cannot discharge the obligation. An absent register leaves the net
unknown. An inspected empty register supports a zero net balance. Excess credit
requires review. Scope and chronology checks apply to the records used in each
projection. At most 32 postings are accepted.

A required task assigned to the affected person is a disagreement even when it
costs zero recorded units. The institution owns removing the condition. Choices
are recorded separately for repeat testimony, further contact, public
reconciliation and publicity. Missing choices stay unanswered. A voluntary
account may report access, a difficulty using the remedy, or disputed records.
The report retains its source and leaves the objection open even when use is
reported. The operator is trusted to supply the correct account, role identities
and complete receiving snapshot. Files may share an author or be replaced. Their
digests establish identity of the supplied content only. The profile has no
ingestion authentication, persistent case history or evidence of actual delivery.
The receiving register and voluntary accounts are fictional Babalon fixtures.

## What would finish this research milestone?

| Gate | Owner and evidence needed to pass |
| --- | --- |
| Local invariants (implemented) | Run the CLI and paired regressions. Vary participation while fixing the award. Test partial, returned, duplicate and misdirected credit, burden shifted to the person, missing reviewer and a voluntary challenge after credit. The report must identify who still owes what. |
| Continuity of responsibility | Build a restartable case history with a named institutional owner, due date and escalation owner for each open duty. Exercise handoff, returned credit, inaccessible remedy, missed follow-up and staff departure. A successor must recover the duty and its original objection. Require evidence for correction of other affected files before closing their inquiry. |
| Independent evaluation | An independent case custodian and separate grader freeze unseen cases and expected outcomes before the evaluated revision sees them. Count false closures, newly imposed participation conditions, lost objections and orphaned duties per case. Any one of those failures blocks advancement. Publish disagreements and the version tested. |
| Review by affected people | Invite people with relevant experience to shape the scenarios and judge whether the choices are understandable, the route to correction is usable and the institution carries the work. Offer voluntary, compensated participation unrelated to benefit eligibility. Let people decline contact and withdraw from the review. Treat unresolved criticism as a finding. |
| Decision on any real use | A separately authorized institution identifies the mandate, funding, responsible humans, evidence of delivery and route for appeal or correction. A local pass supplies no authority to contact people or move resources. |

A research release can finish the technical and evaluation gates while stating
exactly whose judgment it includes. Actual benefit requires evidence about
consequences. People retain the option to say what the record missed or to leave
without doing further work.

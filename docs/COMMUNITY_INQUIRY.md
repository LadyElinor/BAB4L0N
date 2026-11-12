# Community inquiry

A trusted operator supplies one question and a directory of documents that all
four investigator roles may inspect. Run the fictional East Tap case offline:

```sh
python -m babalon inquire 'Was water available at the east tap by 09:00?' examples/inquiry/east-tap
```

The first plan assigns four different questions. The source investigator
locates assertions and citations. The challenger searches for contrary
passages. The assumptions investigator looks for a premise connecting the
observation to the conclusion. The affected-person investigator looks for
accounts of practical access and gaps in representation. This last role
reviews documents. No one is contacted and a software role cannot speak on
someone else's behalf.

Each return separates exact observations and source references from
interpretation, uncertainty and unanswered questions. The coordinator derives
a revised plan from the first returns. Opposing stances on the same named
claim commission a comparison. Uninspected local citations commission a trace.
A pair of unclassified prose passages can commission inspection of the
neighboring lines to check scope. Newly observed claims and references enter
the final evidence map. A proposed next step carries no execution authority.

## Inspect the example

| Inspection | What the source says |
| --- | --- |
| Bulletin and circular | The bulletin infers service from an alarm clearing. The circular repeats the bulletin. |
| Field account | The resident reports an empty jug at 09:00. The account leaves out people unable to reach another outlet. |
| Assumption | The inference depends on the state of the downstream branch. |
| Second-round check | A timed draw at the east tap would bear on the question. The cited register documents a draw at the pump outlet. |

The default run makes nine passage inspections in two rounds. The report
preserves both supporting statements and the challenge, the circular's link
to the bulletin, and the location of the proposed check. A human can inspect
the quotations and assess whether the recorded test answers the question.
The coordinator leaves the claim disputed even when one side has more entries.
It also leaves room for explanations that do not appear in the documents.

## Bring a collection

Use a flat directory of one to sixteen UTF-8 `.txt` or `.md` files. Use
ASCII letters, digits, underscores, periods and hyphens in document names
and start with a letter, digit, underscore or hyphen. Document symlinks are
rejected. Each file may contain up to 32 KiB, 256 lines and 2,000 characters
per line. The directory may have up to 128 entries. Choose documents suitable
for a shared report, since inspection returns verbatim passages. The host
indexes the full authorized collection once. Per-role limits count passages
disclosed to the scripted investigators.

Plain text is searchable without annotation. Retrieval uses case-folded words,
an English stop list and role-specific cues. A question with no matching words
can yield four unanswered assignments. Unclassified comparison leads identify
passages for human comparison. For an explicit evidence map, documents can
optionally use single-line statements such as:

```text
Supports [east-tap-0900]: The office reports water was available. [[bulletin.md#L1]]
Challenges [east-tap-0900]: The field account reports a dry outlet at that time.
Assumes [east-tap-0900]: The branch valve remained open.
Impact [east-tap-0900]: The question misses residents unable to collect water elsewhere.
Check [east-tap-0900]: Look for a timed draw at that outlet.
```

Authors supply the tags and claim keys. Use a key for one proposition with a
specific place, time and criterion. Tags record a source's stance. They confer
no truth, independence or permission. A citation denotes a numbered nonblank
line in the snapshot (blank lines retain their original line numbers).
Missing targets remain visible. The coordinator never opens a document named
in a passage outside the operator's collection. The manifest hashes original
file bytes, and the local audit checks returned quotations, line bindings,
assignment limits and total charges against the in-memory snapshot.

Set `--budget 0` through `24` (default 12) and `--rounds 1` or `2`
(default 2). Each first-round role gets up to two inspections and each
follow-up assignment up to three, sharing the overall budget. Each pass gives
each assignment one turn in plan order. A repeated inspection costs again.
With `--rounds 1`, the first returns and proposed revised plan are still
available for review. Exit zero indicates report generation, including a
disputed or wholly unanswered inquiry. Inspect the map and stop reason.

## What is measured

These are deterministic investigator policies in one trusted Python process
with shared authorship. A second role inspecting the same source adds no
independent witness. Lexical retrieval can miss paraphrases, select irrelevant
passages or place two descriptions of different events alongside each other.
The source comparison and audit use the same snapshot. They cannot establish
authenticity or completeness. The audit checks transcription and accounting.
Interpretation and substantive decisions stay with the operator.

A fresh run over changed files produces a new collection digest. Durable
resume with an append-only revision history, independently authored strategies,
and a held-out comparison of what each strategy discovers remain future work.
For such a comparison, hold the collection and inspection allowance fixed,
include a single-reader baseline, and record missed contrary evidence,
unsupported claims, unresolved questions and inspections separately.

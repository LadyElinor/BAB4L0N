# SQuAD presentation-order correction (v2)

This protocol corrects a project-authored retrieval adapter, not SQuAD itself.
The original receipts and original `NOT_PROMOTED` outcome remain unchanged.
The corrected replay uses already public, previously examined data and is a
**sensitivity analysis, never a fresh promotion trial**. No runtime policy or
permissions change. HotpotQA is outside this change.

## Frozen before corrected replay

Baseline: commit `4740788e1049d674ad65ee5883419d794255cc19`.
The original runner is retained byte-for-byte as
`scripts/retrieval_selection_trial_v1.py`. The current runner declares
`babalon.squad-selection.v2`; it refuses to reuse a database containing v1 receipts.
New proposal, result and sensitivity receipts have distinct v2 filenames.

Question sampling, exclusions, paragraph normalization, twelve rankers, tie-break,
source byte hashes, maximum inspection budget and no-regression gate are unchanged.
For every question, select precisely the same original source paragraph and eleven
original distractors. Membership still uses SHA-256 of `qid:index`. **Then** sort
only those twelve selected original paragraph indices by SHA-256 of the UTF-8 string:

    babalon.squad-selection.v2.presentation\0{qid}\0{original_paragraph_index}

Here `\0` means one NUL byte. Original index breaks a hypothetical digest tie.
The presentation key receives neither gold status nor answer text. This domain
is fixed once before corrected scores are inspected; it must not be tuned to
improve outcomes or make a visually nicer empirical histogram. Independence here
means a separate deterministic hash domain, not a formally proved randomization.

## Why v1 was biased

V1 chose eleven early-hash distractors and then displayed them using that same
hash order. A gold paragraph outside those early ranks therefore tended to appear
last. It was not enough that the sorting key omitted the label. The selection
procedure made the conditional distribution of the label position nonuniform.

## Prespecified diagnostics

Report gold positions 1–12 for all drawn and admitted training/development cases,
actual per-question spend, every arm's hits, candidate wins/losses, and original
versus corrected receipt identities. Verify identical question sets, exclusions,
and selected original paragraph membership. Preserve original receipt bytes.

Two controls receive **no question, passage content or gold label**:

- Primary: inspect position 12 first, then positions 1–11 in ascending order.
  This tests the specific last-position artifact predicted by v1 construction.
- Secondary: inspect positions 1–12 in ascending order.

Each control inspects exactly the incumbent's actual spend for that question in
that run. Reordering may change incumbent spend. Report those changes explicitly.
The paired sensitivity reporter requires exact per-question equality of old and
new spend. If any differ, it refuses the equal-spend comparison instead of silently
mixing ordering and budget effects. It also reports whether the selected candidate
changed; if it did, candidate differences would combine selection and ordering.
This does not claim the shared-gap incumbent executed at a spend it did not incur.

The original no-regression gate may be reported as `gate_status`. V2 always keeps
`status: NOT_PROMOTED` and `promotion_eligible: false`, even if that descriptive
gate would pass. A valid future promotion requires a separately frozen protocol
and genuinely fresh evaluation.

## Observed public replay

All 128 drawn training questions and 256 drawn development questions retain the
same exact original paragraph-index membership, normalized texts and gold text.
Admission remains 119 training and 233 development cases, with 9 and 23 identical
length exclusions. All twelve training scores are unchanged and standard BM25
is selected again. V1 and v2 development spend is identical **for every question**,
851 inspections in each arm. No spend-confounded comparison is reported.

Development parent-paragraph hits, out of 233:

| Arm | Original v1 | Corrected v2 |
|---|---:|---:|
| Selected candidate | 229 | 229 |
| Fixed BM25 | 229 | 229 |
| Shared-gap incumbent | 220 | 223 |
| Keyword | 221 | 223 |
| Position-only, last then first | 178 | 82 |
| Position-only, first to last | 25 | 76 |

The candidate and fixed BM25 retain identical hit/miss outcomes on every case.
Shared-gap gains six and loses three; keyword gains four and loses two. The v2
candidate has seven wins and one loss against shared-gap, six wins and no losses
against keyword, and ties BM25 on all cases. The descriptive gate still yields
`NOT_PROMOTED`, separately from v2's unconditional no-promotion sensitivity label.

Gold position counts in slots 1–12, admitted development cases:

- Original: `[4, 7, 4, 10, 7, 10, 6, 5, 7, 2, 7, 164]`
- Corrected: `[19, 22, 21, 16, 23, 16, 9, 18, 18, 22, 24, 25]`

The last-first control losing its large advantage is evidence that the specific
construction artifact was removed in this replay. The observed histogram is not
exactly uniform, and no formal randomization or generalization claim follows.
The source gold is still forcibly included among twelve same-article passages.
Actual spend here means paragraph inspections, not elapsed time or computation.

Full drawn/admitted histograms for both splits, paired gains/losses, source
membership evidence, proposal/result links and row commitments are in
[`retrieval-position-sensitivity-v2.json`](../reports/retrieval-position-sensitivity-v2.json).
The independent v2 [proposal](../reports/retrieval-selection-v2-proposal.json) and
[result](../reports/retrieval-selection-v2-result.json) preserve all training
scores, evaluation row digest and loss IDs. Original report files are unchanged.

## Reproduce both versions and verify receipts

Supply the two original upstream files, with hashes pinned by both runners:

    python scripts/replay_retrieval_selection.py train-v1.1.json dev-v1.1.json new-replay-directory

The output directory must be new. This runs every phase in a separate interpreter,
checks restart replay, byte-compares both proposals, checks every evaluation row
and receipt field, and independently reconstructs membership, targets and matched
spend from source. Full paired rows are emitted to the output directory and retained
as a hosted CI artifact. V1 uses `receipts`; v2 uses the separate `receipts_v2`
table and refuses populated legacy databases. Keep versions in separate files.

The standard `python scripts/verify.py` exercises local unit and subprocess checks
without downloading benchmark data. The retrieval workflow additionally downloads
the pinned public splits and runs the full dual replay above.

## Local verification (2026-11-19)

CPython 3.12: 145 unit tests ran, with 2 optional-runtime tests skipped; the
aggregate subprocess demos passed. The full v1/v2 benchmark replay, separate-process
restart and all committed receipt comparisons passed. The original proposal/result
reports and HotpotQA report remain byte-for-byte unchanged. Hosted workflow results
are recorded separately from these local checks.

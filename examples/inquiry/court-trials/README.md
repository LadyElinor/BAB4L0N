# Relay Atlas court reading trial

Run from the repository root with Python 3.11+; no dependency install or network is needed:

    python scripts/court_trial.py
    python scripts/court_trial.py --traces
    python -m babalon inquire "What did Cotton and Tolan report about the porch lighting and driveway lights?" examples/inquiry/court-trials/tolan-cotton --budget 4

Each case directory holds plain, attributed source extracts. The question sheet,
source URLs, speaker labels, limits, targets, and optional editor's notes live in
[study.json](study.json), outside those directories. Line numbers identify the
selected extracts, not page or line numbers in an original deposition. No
syllabus or Atlas conclusion is included in the plain inputs.

| Case | Test | Plain / keyword / with note (targets out of four) |
| --- | --- | --- |
| Theatre Enterprises v. Paramount (1954) | Parallel conduct as circumstantial evidence; limits on carrying an earlier decree over to Baltimore | 4 / 4 / 4 |
| Tolan v. Cotton (2014) | Attribute the lighting accounts; distinguish vacatur and remand from a liability finding | 3 / 4 / 3 |
| Department of Commerce v. New York (2019) | Compare Ross’s March and June statements; distinguish rejecting an explanation from invalidating the substantive choice | 2 / 3 / 2 |

Edition 39 used engine commit `2678cc9`. All six questions, two target rows
per question, four inspections per run. The baseline ranks distinct passages by
shared non-stopwords, breaking ties by reference; it can return up to the
number of actual plain inspections. Repeated Babalon inspections cost credit.
The guided arm adds one visible editor assumption; it cannot earn target credit.
See the [frozen returns](../../../reports/atlas-court-retrieval-v1.json).

Plain Babalon retrieved 9/12 designated rows; keyword search retrieved 11/12;
the editor-guided run retrieved 9/12. In the chronology question both methods
missed the designated March passage. In Tolan the missed disposition row has
a partial substitute in another retrieved paragraph. Read the passages before
calling a retrieval miss an incorrect legal answer.

These are public development examples, not a sealed or independently graded
benchmark. The same editor selected the passages, questions and targets.
Matching quotations verifies transcription, not testimony, private intent, legal
reasoning or historical truth. Both Ross memos have the same author. The Tolan
opinion recounts witnesses; it is not a set of independently obtained depositions.

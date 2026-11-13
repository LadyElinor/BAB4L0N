# Can bounded search earn a retrieval policy replacement?

Freeze before inspecting corpus contents or scores. Use the upstream
[SQuAD 1.1](https://rajpurkar.github.io/SQuAD-explorer/) train and development
files at SQuAD-explorer revision eee5fdbf62f8613a7812b03419e6b29617b74fd1.
The runner pins both byte hashes. The evaluator constructs a retrieval task
from a reading comprehension dataset. A hit means finding the question's
annotated parent paragraph. Other plausible passages receive no credit.
The source paragraph is offered with eleven same-article distractors in a
deterministic hash order. All texts are shared across arms; no answer spans
or target indicators reach a ranker. One paragraph inspection costs one.

For articles with twelve or more paragraphs, order questions by SHA-256 of
the upstream ID. Use the first 128 training questions and first 256 dev
questions. Exclude a question without replacement if a passage exceeds the
existing host limit. Record exclusions. This is a new externally authored
public split for this project. Our team has custody of code and evaluation.
There is no secret third-party holdout or model training.

The proposer searches twelve BM25 parameter and adjacent query-word-pair
weight combinations using training hits. The first maximum wins. Each arm
gets the actual spend of the shared-gap incumbent (up to four), for both
training and evaluation. Strong control is BM25 at k1=1.2, b=.75 and no
phrase bonus. Also retain the repository's keyword control. Selection is
automated within the authored family. The first committed proposal is the
only one evaluated. Report each held-out arm's hits and paired wins/losses.
To earn local eligibility require strictly more successes than each control
and the incumbent, zero individual regressions against any of them, exact
spend and valid in-scope references. No averaging away a regression.
No runtime default or external permission follows from the trial.

Run from a checkout with the two upstream files:

    python scripts/retrieval_selection_trial.py propose trial.sqlite train-v1.1.json
    python scripts/retrieval_selection_trial.py evaluate trial.sqlite dev-v1.1.json

Within one operator-owned SQLite file commits bind selection, trial counts
and an evaluation receipt linked to the proposal digest. Reopening replays
the committed phase. A new database starts a new experiment. The fixed caps
bound completed trials; rolled-back work can be recomputed following a crash.

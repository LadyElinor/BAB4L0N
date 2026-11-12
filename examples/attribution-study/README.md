# Frozen source-attribution follow-up

The primary last-credit trial's two citation failures were known before this follow-up.
This is a targeted correction study. Its original-case results measure regression
behavior. The previous [guest, classifier and six development questions per
intent](https://github.com/LadyElinor/BAB4L0N/blob/2dc19c87056bc6d9308fd2787fa2c62a8e553dcb/babalon/last_credit/policy.js)
and the [primary observations](../../reports/last-credit-primary.json) remain available.

## Within-domain comparison

Run a 2 × 2 paired experiment on the original 32 cases. Cross the frozen answerer
and a source-bound answerer with buying zero or one timing inspection before
answering. The host fixes the purchase treatment; both answerers see the identical
brief and the identical receipt at each treatment. The zero-purchase treatment
calls no inspection. In the one-purchase treatment the host also records a
refusal when the view is withheld. Each arm reports its matched exposure cost;
the two answerers share the same actual purchase.

The new [guest extension](citation.js) selects the final request clause, recognizes
explicit evidence directives, and falls back to the old classifier. A summary
claim, a job tally, and a protocol rule occupy distinct citation slots. An empty
selected slot leads to abstention. All other grading uses the frozen host grader,
including its definition of avoidable abstention against evidence available under
the original grant. Wrong-source answers are counted for explicit summary,
journal and protocol goals. Handoff goals may allow multiple sources.

Primary comparisons: at each purchase level, report supported and unsupported
answers, wrong-source answers, justified and avoidable abstentions, preserved
obligations and total charged credits. Contrast the source-bound answerer with
the original at one purchase; use the zero-purchase comparison to test whether
the candidate abstains when it lacks the requested evidence. Count every row;
abort on a worker failure. Additional purchases beyond one cannot reveal a
second distinct record in this task.

A separate four-case demonstration uses the reviewer's two exact phrases with
the same reported count of two and true event counts of either two or four.
Agreement in numbers must still earn its citation. These are exposed regression
probes and do not contribute to either primary denominator.

## External question-only diagnostic

Before evaluation, take the 16 lowest SHA-256 ranks in each single-source
category of the independently authored TAT-QA development set. Rank the UTF-8
string `babalon-attribution-v1/` followed by the original question UID. Exclude
mixed-source items. Keep the authors' question wording and their prose/table
source annotation. Freeze the [resulting pack](external-questions.json) under
SHA-256 `f853d3a67d0f486c7545a439e93e47f95b54ce1046a3c8d5447eec55b12c2b81`
before running either guest on it. The exact extraction is reproducible with
`python scripts/attribution_trial.py --extract-external /path/to/tatqa_dataset_dev.json`.
See [attribution and license](../../NOTICE.md).

Each guest receives only the question. Map a summary prediction to prose and
a journal prediction to table; count protocol and handoff predictions as
unmapped errors. Report per-source scores and the balanced 16/32
constant-prediction baseline. TAT-QA describes where the answer occurs in a
particular financial report. Many questions leave its location unstated. This
tests how far a wording-only heuristic travels across domains. It does not
grade financial answers or measure generalization to new Commonwealth handoffs.
The pack is public and selected by the study author. Independent, confidential
custody of new in-domain handoffs and grading remain open.

## Reproduction

The first hosted run on the frozen follow-up commit is the recorded run.
Install `.[last-credit]` and run `python scripts/attribution_trial.py > result.json`
from the checkout. The command runs offline. Both policies execute in
capability-limited QuickJS guests, and no language model is called or promoted.

[Observed results, including the external diagnostic](../../reports/CITATION_DISCIPLINE.md).

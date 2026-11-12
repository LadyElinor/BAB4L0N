# Shared passages and gap-directed follow-up

## Prospective protocol

Primary endpoint: how often the shared-gap strategy retrieves every annotated
supporting sentence compared with the existing keyword reader at exactly the
same actual number of paid inspections per question. Use the complete public
HotpotQA distractor development split assigned by its authors, 7,405
questions. Freeze code before first access to question texts or annotations.
Include all eligible rows. Exclude only inputs outside the existing host
limits or unresolved gold sentence references; report counts and reasons.
This is an externally authored and partitioned public set, accessible to others.
Our team owns the experiment, adapter and analysis. No claim of private custody.

Use all ten supplied articles when present, in supplied order. Prefix every
sentence with its article title, normalize whitespace and index each sentence
as one passage for all readers. Question and document texts alone go to the
readers. Use four credits at most. If keyword has fewer than four positive
matches, limit all arms to its candidate count; compare each arm with keyword's
prefix at that arm's audited actual spend. Legacy charges per visit; sharing
charges once per distinct passage across roles in one authorized run. Track
all visits separately. Equal spend means passage inspections; CPU, indexing
and re-reading effort are separate. No model or network access by the readers.

Compare legacy, shared-only and shared-gap, each against its own matched
keyword prefix. Do not attribute differences between strategies at different
spends to coordination. The gap policy ranks unseen passages by original
query overlap, additional weight on query words absent from the shared
observations, and up to two distinctive bridge-word matches from observations.
It may use the remaining allowance in the second round. It cannot determine
that an evidentiary gap is substantively resolved.

The directional hypothesis is that shared-gap improves complete-evidence
retrieval. Claim superiority here only for a positive primary difference with
a two-sided paired exact sign-test p below .05. Report paired wins/losses/ties,
the 95% paired question bootstrap interval, supporting-sentence hits,
inspection counts and skips. The other comparisons are descriptive. Report
all results without retuning or changing the default. The study does not test
historical truth, dissent detection or generated answers; HotpotQA gold
supports answers to questions and supplies no annotation for those outcomes.

The dataset and supporting facts come from Yang et al., EMNLP 2018,
under CC BY-SA 4.0. The workflow checks the input SHA-256 and archives
per-question reference IDs and a summary. No question or source prose is
redistributed here. [Upstream split and license](https://hotpotqa.github.io/)

## First frozen run

The [freeze commit](https://github.com/LadyElinor/BAB4L0N/commit/5f0cd129322bdb3a5d82056b3b913149e4a8faad)
preceded the [hosted evaluation](https://github.com/LadyElinor/BAB4L0N/actions/runs/43332097428).
Of 7,405 questions, 7,403 were scored. One source line exceeded the host's
2,000-character limit; one gold sentence reference did not resolve in its
own context. All policies and controls used the same eligible cases.

| Strategy | Complete sets | Matched keyword | Credits per side | Paired wins / losses / ties |
| --- | ---: | ---: | ---: | ---: |
| Legacy | 568 | 801 | 20,954 | 46 / 279 / 7,078 |
| Shared only | 573 | 799 | 20,900 | 51 / 277 / 7,075 |
| Shared plus gap follow-up | 1,596 | 1,243 | 29,607 | 670 / 317 / 6,416 |

On the primary comparison complete-set recovery increased from 16.79% to
21.56%. The paired difference was +4.77 percentage points (95% bootstrap
interval +3.98 to +5.57). The two-sided paired exact p-value was
9.55e-30. The full candidate inspected 9,117 of 17,999 gold sentences; its
keyword comparator inspected 8,614. There were 29,911 investigator visits,
including 304 no-charge rereads. The candidate still missed at least one
annotated sentence on 5,807 questions. This result passes the prespecified
superiority criterion against matched keyword on this split only.

The uncertainty interval describes variation across these questions; author
annotations form a fixed reference. The three strategies spent different
amounts. The comparisons do not isolate the causal contribution of sharing
at a common spend across strategies. No conclusion about answer accuracy,
contrary evidence or affected-person representation follows. None of these
cases can be reused as unseen evidence for future revisions.

The [summary](../reports/hotpot-retrieval-v1.json) was copied from the first
hosted artifact. All 7,403 pairs were recounted from that artifact, checking
per-question spend and all three arms' totals. The archived per-question IDs,
gold references, selected references and comparator prefixes are in
`external-inquiry-results` on the workflow run. Archive SHA-256:
`2d0171a54c8bce5bec3ef2acfab7bae048b0770902d74a67538b1d068fb4d93f`.
Recreate it with the pinned upstream JSON and
`python scripts/external_inquiry_trial.py hotpot_dev_distractor_v1.json OUT`.
To exercise the candidate on an authorized local collection, pass
`--strategy shared-gap` to `python -m babalon inquire`.

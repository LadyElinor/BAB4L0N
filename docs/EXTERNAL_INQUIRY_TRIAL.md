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

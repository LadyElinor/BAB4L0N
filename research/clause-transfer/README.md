# Did clause coverage improve the four passages readers actually saw?

The clause-coverage selector and reciprocal-rank fusion (RRF) delivered the same passages on every question in a fresh three-case pilot. At the primary depth of four, both completed six of nine answerable questions. Fixed BM25 completed seven. Increasing candidate depth to eight made every required set attainable, but the candidate and RRF each completed only five. The candidate missed all three preregistered retrieval criteria. Status is **`NOT_PROMOTED`**.

A separately prompted AI curator selected Britain's pound-coin changeover, the Bennu sample return and the 2020 U.S. House apportionment. Twelve questions shared one corpus of 47 attributed paraphrases from ten documents. Nine questions had a complete evidence set. Three could not be settled from this packet and remained in all spending and review totals. The curator identified thirteen acceptable groups, including four alternatives. Each reader delivered exactly four distinct passages on each question at each depth. The protocol and method were deposited before case selection. The original Ofqual records remain reproducible. [Frozen protocol](../../docs/CLAUSE_COVERAGE_PROTOCOL.md) · [Source register](case/provenance.md) · [Rubric](case/rubric.md) · [Committed evidence groups](case/groups.json)

## What reached the reader

Each complete set contains all references in at least one accepted group. The secondary passage count uses the first committed group per question. All results below have 48 native and 48 matched inspections per reader and depth.

| Candidates per input list | Attainable complete sets / 9 | Fixed BM25 (complete, hits) | RRF (complete, hits) | Exclusive slots (complete, hits) | Clause coverage (complete, hits) |
| ---: | ---: | --- | --- | --- | --- |
| 4, primary | 7 | 7/9, 20/22 | 6/9, 19/22 | 7/9, 20/22 | 6/9, 19/22 |
| 8, sensitivity | 9 | 7/9, 20/22 | 5/9, 18/22 | 5/9, 18/22 | 5/9, 18/22 |

Five of twelve questions met the reader's two-clause rule. A post-unblinding comparison found that the candidate changed RRF's order on one question at depth four and four questions at depth eight. None of those changes altered the selected IDs. The interpreter therefore received identical evidence for these paired readers. On the public SciFact rehearsal the candidate changed membership for zero of 300 claims at depth four and one at depth eight. That one change preserved its complete-set outcome. [Membership comparison script](../../scripts/clause_membership.py) · [Full transfer result](result.json) · [Ordered returns](method-key.json)

Against fixed BM25, the candidate changed which passages were delivered on q04, q05 and q10 at both depths. Only q05 lost a complete set at primary depth. At depth eight q04 also lost one. Reproduce the membership comparison from the repository root with the command below. Omitting the reference option reproduces the original comparison with RRF.

```sh
python scripts/clause_membership.py research/clause-transfer/method-key.json --reference bm25
```

| Case | Primary pool / 3 | Fixed / 3 | Candidate / 3 | Depth-eight pool / 3 | Fixed / 3 | Candidate / 3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Bennu sample return | 3 | 3 | 2 | 3 | 3 | 2 |
| House apportionment | 3 | 3 | 3 | 3 | 3 | 3 |
| Pound-coin changeover | 1 | 1 | 1 | 3 | 1 | 0 |

**Bennu, q05.** The question asks for the Canadian instrument, its measurement and the collection site. Fixed BM25 delivered the Canadian Space Agency's laser-altimeter passage and evidence identifying Nightingale. The clause reader returned the site, omitted the instrument and spent one of the primary slots on a pound-coin passage. Its interpreter correctly abstained on the missing parts. The candidate lost q05 against fixed BM25 despite four acceptable evidence combinations in the manifest. [Canadian Space Agency](https://www.asc-csa.gc.ca/eng/satellites/osiris-rex/canadas-role.asp)

**Pound coin, q04.** At depth four the candidate supplied both the billion-coin production milestone and the identity of the official who struck the coin. At depth eight the passages supported the number alone. The shared pool still contained the official's identity. The interpreter accordingly changed from a supported answer to a warranted abstention. On q01 and q12, the larger pool made complete sets newly attainable and both remained incomplete in the candidate's return. [HM Treasury and Royal Mint](https://www.gov.uk/government/news/new-1-coin-exchequer-secretary-strikes-billionth-new-pound)

The primary candidate comparison with RRF had zero gains, zero losses and nine ties. Omitting each case in turn yielded a complete-rate difference of zero across the six remaining target-bearing questions. Against fixed BM25 there were zero gains and one loss at primary depth, and zero gains and two losses at sensitivity depth. The candidate gained in no case against both baselines. The answer-review safeguard passed. Three small cases and same-operator AI review leave independent human transfer and answer-quality claims open.

## What the blinded reviewers judged

The study randomized eight aliases per question. Identical questions and visible evidence shared an interpretation and assessment, yielding 22 distinct cards from 96 labeled returns. The interpreter's sealed answer file preceded review. Separate AI contexts assessed each card using only its supplied passages and the interpretation. Both reviewers agreed on every categorical dimension across all returns. With the same evidence and a shared model family, this agreement provides limited independent confirmation. The original rationales, citations and unresolved issues are retained. [Worksheet](worksheet.json) · [Interpreter](answers.json) · [Review A](review-a.json) · [Review B](review-b.json)

| Depth | Reader | Reviewer | Inspections | Canonical hits / 22 | Credited results | Answers / abstentions | Supported | Unsupported | Warranted | Unwarranted | Uncertain |
| ---: | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 4 | Fixed BM25 | A | 48 | 20/22 | 7 | 7 / 5 | 7 | 0 | 5 | 0 | 0 |
| 4 | Fixed BM25 | B | 48 | 20/22 | 7 | 7 / 5 | 7 | 0 | 5 | 0 | 0 |
| 4 | RRF | A | 48 | 19/22 | 6 | 6 / 6 | 6 | 0 | 6 | 0 | 0 |
| 4 | RRF | B | 48 | 19/22 | 6 | 6 / 6 | 6 | 0 | 6 | 0 | 0 |
| 4 | Exclusive slots | A | 48 | 20/22 | 7 | 7 / 5 | 7 | 0 | 5 | 0 | 0 |
| 4 | Exclusive slots | B | 48 | 20/22 | 7 | 7 / 5 | 7 | 0 | 5 | 0 | 0 |
| 4 | Clause coverage | A | 48 | 19/22 | 6 | 6 / 6 | 6 | 0 | 6 | 0 | 0 |
| 4 | Clause coverage | B | 48 | 19/22 | 6 | 6 / 6 | 6 | 0 | 6 | 0 | 0 |
| 8 | Fixed BM25 | A | 48 | 20/22 | 7 | 7 / 5 | 7 | 0 | 5 | 0 | 0 |
| 8 | Fixed BM25 | B | 48 | 20/22 | 7 | 7 / 5 | 7 | 0 | 5 | 0 | 0 |
| 8 | RRF | A | 48 | 18/22 | 5 | 5 / 7 | 5 | 0 | 7 | 0 | 0 |
| 8 | RRF | B | 48 | 18/22 | 5 | 5 / 7 | 5 | 0 | 7 | 0 | 0 |
| 8 | Exclusive slots | A | 48 | 18/22 | 5 | 5 / 7 | 5 | 0 | 7 | 0 | 0 |
| 8 | Exclusive slots | B | 48 | 18/22 | 5 | 5 / 7 | 5 | 0 | 7 | 0 | 0 |
| 8 | Clause coverage | A | 48 | 18/22 | 5 | 5 / 7 | 5 | 0 | 7 | 0 | 0 |
| 8 | Clause coverage | B | 48 | 18/22 | 5 | 5 / 7 | 5 | 0 | 7 | 0 | 0 |

Each reviewer row repeats the same retrieval spend. The three questions with empty target lists received warranted abstentions throughout.

## Ranking work and timing

Fixed BM25 used 12 rankings over 47 passages per condition (564 query–passage pairs). Each fusion method shared the whole-question ranking with its clause reader and needed 22 standalone BM25 calls (1,034 pairs). The candidate additionally consumed the individual clause rank positions to score novelty. At primary depth the input-position totals were 48 for fixed BM25, 96 for RRF and exclusive slots, and 136 for the candidate. The eight-deep totals were 96, 192 and 272 respectively.

For all twelve questions together, median warm times at primary depth were 7.90 ms for fixed BM25, 14.99 ms for RRF, 13.60 ms for exclusive slots and 14.46 ms for the candidate. At depth eight they were 7.40, 14.10, 15.46 and 18.36 ms respectively. These five-repeat local timings describe this small corpus and host. [Timing environment and all samples](timing.json)

## Public sentence-selection rehearsal

All 300 SciFact development claims were evaluated within the abstracts cited by each claim. Of those, 188 had annotated evidence, 83 had multiple accepted groups, and 112 had no annotated evidence. A one-sentence group sufficed for 178 of the 188. Only 10 required multiple sentences in every accepted group, and three of those triggered the clause split. Each reader used 1,152 matched inspections per condition. The spend distribution was three claims at zero, one at one, nine at two, fifteen at three and 272 at four.

| Candidates per list | Attainable complete sets / 188 | Fixed BM25 | RRF | Exclusive slots | Clause coverage |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 160 | 158 | 158 | 158 | 158 |
| 8 | 179 | 158 | 159 | 157 | 159 |

The candidate tied RRF question for question at both depths. Both completed five of the ten claims that required multiple sentences at either depth. With eight candidates, the common pool could supply eight of those ten sets. Each fusion reader needed 366 standalone BM25 rankings across 300 claims per condition, versus 300 for fixed BM25. The 112 empty annotations remain in those costs. Science verdicts and answer quality were unmeasured in this public rehearsal. The 188 is the denominator for this claim-level coverage test on supplied source documents. The official abstract-level SciFact task also scores the predicted label. [Original evaluation](https://github.com/allenai/scifact/blob/master/doc/evaluation.md) · [Aggregate receipt](../../reports/scifact-clause-coverage.json)

To reproduce from the repository root using the original pinned archive:

```sh
curl -fL https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz -o /tmp/scifact-data.tar.gz
python scripts/scifact_clause_rehearsal.py /tmp/scifact-data.tar.gz > /tmp/scifact-clause.json
diff -u reports/scifact-clause-coverage.json /tmp/scifact-clause.json
```

Add `--rows /tmp/scifact-trace.json` to retain the per-claim method returns, accepted groups and scores. The script verifies the archive and original JSONL member hashes. The saved aggregate includes a digest of the complete trace.

## What the custody record establishes

One operator coordinated separate AI contexts for curation, interpretation and each review. The actors followed role-limited instructions in a shared workspace with no enforced account isolation. Git commits retain the following sequence. The curator's source-register check date is in UTC.

| Stage | Retained commitment |
| --- | --- |
| Method and decision rules fixed before case selection | [Method commit](https://github.com/LadyElinor/BAB4L0N/commit/bce32851e8034d681d2894f29ef5648328eae66f) |
| Case, source bytes, groups, rubric, implementation and roles | [Case freeze](https://github.com/LadyElinor/BAB4L0N/commit/15499179d82548629275829fa60d2880f9a59a85) |
| Anonymous worksheet and private key | [Run deposit](https://github.com/LadyElinor/BAB4L0N/commit/bfe17ecfe051dc38d4b8d1f3d28e961c43ebbc5a) |
| Interpreter answers before reviewer access | [Answer deposit](https://github.com/LadyElinor/BAB4L0N/commit/31df0c6c395cb270b18a369bfe7da62cc54ecff5) |
| Review B's individual submission | [First review deposit](https://github.com/LadyElinor/BAB4L0N/commit/b259605ea1c45c7c186083dff781e7e9d9119d96) |
| Review A's individual submission | [Second review deposit](https://github.com/LadyElinor/BAB4L0N/commit/7254f4cbcd3a7df1ac182d1277a0e8fdf61345fe) |
| Both deposits verified and register closed before the key was opened | [Register deposit](https://github.com/LadyElinor/BAB4L0N/commit/489deb8262da4433e84a9079a7e9e788b4e7eb4a) |

## Replay and custody

The transfer replay runs offline with Python 3.11 or later. A separate checkout of the closed deposit supplies the verification commitments. Recount regenerates every named return with fresh test aliases and checks passage bodies, publisher IDs, list order, pool membership, ranking counts, native and matched charges, canonical hits and complete groups. It verifies the sealed reviews and answer-to-worksheet linkage before opening the retained key. The published result keeps both review tallies, disagreement dimensions, case-level returns, the paired wins and losses, and the leave-one-case-out comparison.

```sh
git show 489deb8262da4433e84a9079a7e9e788b4e7eb4a:research/clause-transfer/deposits.json > /tmp/clause-deposits.json
python scripts/blind_clause_trial.py recount research/clause-transfer/case research/clause-transfer /tmp/clause-deposits.json > /tmp/clause-result.json
diff -u research/clause-transfer/result.json /tmp/clause-result.json
python scripts/verify.py
```

A source ZIP has no Git history. Supply the externally retained deposit file separately, or use the included `research/clause-transfer/deposits.json` for an internal consistency check. The machine-dependent wall-clock samples can be regenerated with `python scripts/time_clause_readers.py research/clause-transfer/case`.

For a new packet, the `freeze` and `run` subcommands produce a combined freeze, randomized worksheet, private method key and deduplicated evidence cards. Deposit the freeze before `run`, and externally retain both digests it returns. Give only the cards and [role instructions](../../docs/CLAUSE_COVERAGE_REVIEW.md) to the interpreter. Use `answers` to expand and seal the interpretation. Deposit its digest before `review-cards`. Give those cards to two separate reviewers. Use `review` to expand and validate each independent submission. Deposit each named review separately, then use `scripts/blind_inquiry_v2.py close-register` with the retained key, answer and review digests. Deposit the register digest before collection. Preserve the method revision, all stage digests, individual full submissions and role assignments. An independent human-run study must arrange separate access and off-operator custody before case selection. This disclosed packet can now serve as development material.

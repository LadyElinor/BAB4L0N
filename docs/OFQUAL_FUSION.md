# Can four inspections recover both halves of an answer?

One selection rule recovered the complete designated evidence on three of the five target-bearing Ofqual questions. All four historical readers completed two. The difference is q4, the question about an offered examination and evidence of its use. It was also the disclosed example that motivated the rule. This is an exposed development result. Status is `NOT_PROMOTED`.

## Comparison

Each reader returned **four distinct passages on each of six questions**. A question is complete when the return contains every reference designated for that question. The five scored questions have two designated references each. The sixth asks how many students regained a particular university place before its deadline. The collection lacks the linked admissions records needed to answer it. Its empty target set contributes 4 inspections per method and zero to both retrieval denominators. The receipt represents completeness on that question as JSON null. Exact scoring uses the original targets. The rubric's cited equivalents belong to answer review.

| Reader | Complete questions / 5 | Exact hits / 10 | Inspections | Standalone ranking work across six questions |
| --- | ---: | ---: | ---: | --- |
| Keyword | 2 | 5 | 24 | 6 keyword calls |
| Shared-gap | 2 | 6 | 24 | 24 role rankings and 6 gap rankings |
| Fixed BM25 | 2 | 6 | 24 | 6 BM25 calls |
| Clause-based BM25 | 2 | 6 | 24 | 16 BM25 calls |
| Deduplicated interleaving | 2 | 6 | 24 | 22 BM25 calls, 48 input rank positions |
| Reciprocal-rank fusion | 2 | 6 | 24 | 22 BM25 calls, 48 input rank positions |
| Source-family coverage | 2 | 6 | 24 | 22 BM25 calls, 48 input rank positions |
| One exclusive passage per ranker | **3** | **7** | **24** | 22 BM25 calls, 48 input rank positions |

All methods completed q1 and q5. Against each historical control, the exclusive-passage rule gained q4, lost no complete question and tied on the four other scored questions. The rule attained the upper bound for selecting from these two top-four lists. The q2 pool lacks the passage on the board's response to malpractice (`c.txt#L4`). The q3 pool lacks both passages distinguishing subject entries from individual candidates (`f.txt#L3`, `f.txt#L4`). Increasing the pool depth would be a different experiment.

## Why q4 changed

| Rank | Fixed BM25 | Clause-based BM25 | One exclusive passage per ranker |
| ---: | --- | --- | --- |
| 1 | c.txt#L5 | c.txt#L5 | **e.txt#L1** |
| 2 | **e.txt#L1** | d.txt#L3 | **d.txt#L2** |
| 3 | d.txt#L3 | e.txt#L2 | c.txt#L5 |
| 4 | e.txt#L2 | **d.txt#L2** | d.txt#L3 |

Ofqual's `e.txt#L1` documents the autumn exam opportunity for private candidates who could not receive a summer grade. DfE's `d.txt#L2` says around 16 percent of autumn A-level **entries** came from students with no summer grade in that subject. The figure does not identify how many private candidates took up the offer. The five-ID union contains both passages. Agreement between the rankers favors three shared IDs. Source-family coverage picks up the DfE passage `d.txt#L3`, which describes grade improvements for students **with** a summer result available for comparison. Source diversity alone leaves the uptake question open. [Frozen rubric and evidence scope](../research/ofqual-pilot/rubric.md)

The original interpreter answered q1 and q5 and abstained on q2, q3, q4 and q6 for each control. Both reviewers credited two supported answers and four warranted abstentions per control, with zero unsupported claims. Their historical q4 abstentions remain warranted on what those readers saw. The new arms have retrieval scores only. A new interpretation and blinded review would be required to count a new supported answer. [Pilot readout](../research/ofqual-pilot/readout.json) · [Existing reviewer tally and rules](BLIND_INQUIRY_V3.md)

## Selection and accounting

Both inputs stop at the published top four. The fusion selectors receive ordered passage IDs and, for the source-family arm, the packet's document-to-publisher mapping. They have no access to targets, answer labels, passage prose or question IDs. Q4 and its complementary references were known during design. Every rule runs unchanged on every question.

- **Interleaving** alternates fixed then clause positions, skipping previously selected IDs and continuing to four distinct results.
- **Reciprocal-rank fusion** sums `1 / (60 + rank)` for each list containing a passage. Rank starts at one and each list votes once per ID. Descending score determines order, with lexical passage ID breaking exact ties.
- **Source-family coverage** takes the first passage per represented publisher in reciprocal-rank order, then fills from that order. Multiple Ofqual documents share the same family.
- **One exclusive passage per ranker** reserves the highest fixed-only ID and the highest clause-only ID, in that order. It skips a reservation when the list has no exclusive ID and fills remaining slots by reciprocal rank. This policy can displace relevant shared evidence when exclusive results are distractors. A synthetic regression test exercises that loss.

An inspection is a distinct passage delivered as evidence on one question. The replay validates each control's ordered natural and matched lists, original charges and the shared-gap audit. It materializes each final return, checks all references against the corpus and stops on any short, duplicate or overspent row. No question is discarded or padded. The five-ID union on q4 is available only as ranking metadata to the selector. The target-aware pool ceiling is calculated after selection.

The program counts actual invocations of the original ranking functions. For standalone fusion it charges both component readers as implemented, including the whole-query BM25 call inside the clause reader. On this 27-passage corpus, fixed BM25 scores 162 query–passage pairs, clause-based BM25 scores 432, and the two readers together score 594. The experiment harness physically generates each control ranking once and lets all four fusion selectors reuse the same lists. Each selector receives eight input positions per question, 48 in total. The measurements exclude the historical recount, setup, scoring and verification. Function counts describe algorithmic work. Latency, CPU time, memory, and human reading time were unmeasured.

## Reproduce offline

From the repository root with Python 3.11 or later, run:

```sh
python scripts/rehearse_ofqual_fusion.py > /tmp/ofqual-fusion.json
diff -u reports/ofqual-fusion-development.json /tmp/ofqual-fusion.json
python -m unittest discover -s tests -p test_ofqual_fusion.py -v
```

The first command also runs the original pilot recount and compares its output byte for byte with the pinned published readout. The new receipt includes the exact references in selection order, target hits, complete-set result and ranking work for each method and question. [Development receipt](../reports/ofqual-fusion-development.json) · [Selectors](../scripts/retrieval_fusion.py) · [Replay and scoring](../scripts/rehearse_ofqual_fusion.py)

## What an independent evaluation would need to establish

1. **Seal the candidate before case selection.** Nominate the exclusive-passage rule as the single primary candidate and fixed BM25 as the primary comparator. Retain the other controls and reciprocal-rank fusion as prespecified comparisons. Freeze code, list depth, tie rules, actual-spend matching, compute accounting, outcome definitions and decision thresholds. A prospective run needs a new freeze that binds the fusion code to the worksheet. The existing v3 profile covers the historical reader sets.
2. **Use new cases under independent custody.** A curator outside the development team selects multiple unseen cases, including questions whose evidence comes from the same source, different sources, and questions the collection cannot resolve. Include questions where exclusive results can be distractors. Privately commit the source bytes, exact targets, acceptable equivalents and explicit empty sets before retrieval. Keep the packet away from developers until the freeze, and keep the rubric, target file and method key away from selectors and interpreter.
3. **Match actual spend on each question.** Record native charges. If a reader cannot use four distinct inspections, rerun every reader at the lowest attained spend until charges match. Retain zero-spend and failed rows with their disposition. Give the interpreter only the matched returns with fresh randomized aliases and neutral passage order. Record full-query and clause ranking calls, pool sizes and runtime separately on the same hardware with a specified cache policy.
4. **Test retrieval and judgment separately.** The primary endpoint is a paired change in complete exact evidence sets on nonempty-target questions. Report wins, losses and ties by question and by case, secondary exact hits, and uncertainty allowing for questions within the same case. Prespecify case count, a meaningful minimum gain, and the uncertainty bound required for success. A single motivating question cannot establish transfer. Have independent blinded human reviewers use the v3 dimensions and cite equivalent evidence. Deposit answers and individual reviews externally, close the register before unblinding, and publish each reviewer's supported answers, unsupported claims, warranted and unwarranted abstentions and disagreements. Empty-target questions stay in the spend and answer-quality analyses.
5. **Keep the decision tied to the claim.** A retrieval advance requires a replicated complete-set gain within the agreed inspection and compute limits. An answer-quality claim additionally needs more reviewer-supported complete answers, with unsupported claims and warranted abstentions meeting prespecified safeguards. Count an abstention as warranted whenever the returned evidence leaves a required part unresolved. Preserve losses and report uncertainty when the trial cannot distinguish the methods.

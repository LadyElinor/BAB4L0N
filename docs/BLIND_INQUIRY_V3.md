# Blinded inquiry v3: passage hits and answer quality

For new trials, v3 publishes one tally for each **method and reviewer**. It keeps the four original assessment dimensions, the interpreter's decisions, each reviewer's reasons and citations, and the disagreements for each blinded result. The JSON report includes `tally`. Use `collect --table` to print the same counts side by side. Earlier trials retain their original collectors and commitments.

| Report field | Unit and rule |
| --- | --- |
| `matched_spend` | Distinct returned passage inspections, summed across questions for that method. Each reviewer's row repeats the method's cost. |
| `designated_passage_hits` / `designated_passage_targets` | Exact matched passage references found, over all references designated for their respective questions. Both values are JSON null when a manifest was omitted at freeze. |
| `credited_passage_hits` | Reviewed results with `equivalent_evidence=yes`. The table calls these **credited results**. Two citations on one result count once. |
| `supported_answers` | Interpreter answered, reviewer credited equivalent evidence and marked `unsupported_claim=no`. |
| `unsupported_claims` | Answered results with `unsupported_claim=yes`. Each result counts at most once. |
| `warranted_abstentions` / `unwarranted_abstentions` | Abstained results marked `yes` / `no` for `warranted_abstention`. |
| `uncertain` | Results with at least one `uncertain` assessment, counted once. This can overlap another count. |

The JSON includes `rows`, `answers` and `abstentions` for denominators. A reviewer can withhold evidence credit without finding an unsupported claim. The supported and unsupported counts can therefore sum to fewer than the number of answers. Source attribution remains a separate judgment. Adding across reviewers would count the same retrievals more than once.

The new collector rejects `warranted_abstention=yes` on an answer and `unsupported_claim=yes` on an abstention, at review sealing and again before opening the method key. Here `unsupported_claim` scores the substantive answer. Reviewers can record concerns about a partial statement in an abstention's rationale and flag it for inspection. Preserve the original signed-off interpretation and any challenge. Neither cross-check changes a decision or a review.

## Prospective workflow

Use the custody sequence in the [v2 protocol](BLIND_INQUIRY_V2.md). Choose the reader set and scoring rules **before retrieval**. The v3 freeze binds the underlying retrieval freeze, the new analysis and protocol files, the rubric hash, and the optional private target-manifest hash. Deposit the resulting freeze digest outside the submission directory. Keep targets, rubric and method identities away from the readers and interpreter.

```sh
python scripts/blind_inquiry_v3.py freeze packet.json documents RUBRIC_SHA256 freeze.json \
  --readers baseline --targets-sha256 TARGET_FILE_SHA256
python scripts/blind_inquiry_v3.py run packet.json documents freeze.json FREEZE_DIGEST private-run
python scripts/blind_inquiry.py seal-answers private-run/worksheet.json answers.json
python scripts/blind_inquiry_v3.py seal-review private-run/worksheet.json answers.json ANSWER_DIGEST review-a.json
python scripts/blind_inquiry_v3.py seal-review private-run/worksheet.json answers.json ANSWER_DIGEST review-b.json
python scripts/blind_inquiry_v2.py close-register private-run/worksheet.json KEY_DIGEST ANSWER_DIGEST register.json \
  --review reviewer-a REVIEW_A_DIGEST --review reviewer-b REVIEW_B_DIGEST
python scripts/blind_inquiry_v3.py collect private-run/worksheet.json private-run/custodian-only.json \
  answers.json rubric.txt freeze.json FREEZE_DIGEST register.json REGISTER_DIGEST result.json \
  review-a.json review-b.json --targets targets.json --table
```

The default `baseline` runs shared-gap, keyword and fixed BM25. Select `coverage` to include clause-based BM25. Retain the printed worksheet and key digests at run time, the answer digest before review, the individual deposits from each reviewer, and the closed register digest before releasing the method key.

If exact hits are desired, hash the exact bytes of a separate private JSON file before retrieval. Give every question one entry. For example:

```json
{"questions":[{"id":"q1","targets":["minutes.txt#L1","minutes.txt#L4"]},{"id":"q2","targets":[]}]}
```

A designated reference can appear in the frozen collection even if no reader found it. An empty target list contributes zero to the exact-hit denominator. Its question still counts toward spending and review. The custodian may retain the optional `metric` description and `equivalents` annotations used in the [Ofqual manifest](../research/ofqual-pilot/targets.json). Reviewers can credit equivalent evidence separately. For a trial with a narrative rubric alone, omit both target options. Adding or swapping a manifest after the freeze is refused.

As a retrospective check, each Ofqual reviewer credited two results as supported and four abstentions as warranted for each method at 24 inspections. Fixed BM25, clause-based BM25 and shared-gap each recovered 6/10 exact references. Keyword recovered 5/10. Those numbers are derived from the [original pilot records](../research/ofqual-pilot/README.md). The historical trial retains its original freeze and status.

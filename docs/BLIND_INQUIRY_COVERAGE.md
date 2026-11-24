# Does separating two clauses improve evidence coverage?

The exposed three-reader development record has eight questions and sixteen designated passage targets. All three readers missed three of the same targets. The shared-gap reader missed one additional target on the question asking which changes were implemented and which safeguard was promised. This motivates the following general hypothesis. When a question contains two distinct requests, a whole-question rank can spend several inspections on one request and leave the other unanswered.

## Frozen candidate and costs

Use the incumbent shared-gap, keyword and fixed BM25 readers unchanged. The fourth reader retains fixed BM25's first passage. When the question contains exactly one whole-word conjunction from **and**, **but**, or **versus**, with at least two distinct substantive words per side using the inquiry module's stop list, rank each clause by the existing fixed BM25. Alternate left and right ranks, skip repeated passage references, then fill remaining slots from the full-question ranking. Otherwise return fixed BM25. This one candidate has no fitted weights, source-name rules, evidence-status dictionary, access to the rubric, or ability to change a policy.

All four receive the same passage cap. The candidate's eligible references are drawn from the full BM25 vocabulary match and its fallback preserves fixed BM25's count at every cap. Reuse the original matched control runs and execute the candidate at the common spend. Retain each arm's natural and matched references and counts, including zero. An inspection counts a distinct returned passage. The full-text lexical index is available to rankers, so this measures evidence returned for inspection. A split question can require three lexical rankings and equal passage spend does not imply equal computation.

## Independent run

Use the packet, family register, private rubric, and independent selection procedure in [the original protocol](BLIND_INQUIRY.md). A custodian chooses and locks new sources and questions before retrieval. Include both compound and single-part questions, cases with equivalent documentary evidence, and questions warranting abstention. Record prior exposure, the interpreter, and the complete reviewer roster. Preserve the independently deposited freeze digest before running the methods.

```sh
python scripts/blind_inquiry_coverage.py freeze packet.json documents RUBRIC_SHA256 freeze.json
python scripts/blind_inquiry_coverage.py run packet.json documents freeze.json FREEZE_DIGEST private-run
```

This freeze binds the candidate, controls, collection implementation, protocol, packet, source bytes and private rubric hash. A historical three-arm freeze is not a four-arm freeze. Each question has four privately randomized aliases. Identical results can reveal clues about methods. From here, use the deposited key digest and the blinded worksheet with the [v2 custody commands](BLIND_INQUIRY_V2.md), starting with `seal-answers`. Cover every question and every alias (A through D). Each reviewer deposits a separate digest before unblinding. The independent custodian retains the register digest. Keep the individual disagreements and evidence for any abstention.

Report each reviewer's four original dimensions per question. Inspect whether previously unsupported claims increase, whether both clauses receive support when appropriate, and whether an arm purchased more evidence. Report ties, losses, uncertain assessments and non-compound results separately. The first independently held run is descriptive. This profile does not authorize promotion. Repeated development rehearsals and automated practice runs do not establish independence.

## Exposed rehearsal

Run `python scripts/rehearse_inquiry_coverage.py DIRECTORY_WITH_BOTH_ATLAS_EXPORTS`. The rehearsal checks the two original byte pins and runs the complete four-arm trial. It records designated target hits and matched results per question, including losses versus each comparator. No new human answers or review grades are supplied. Preserve this candidate and the earlier rehearsal before considering any revision.

# What did the clause-based reader recover on a new case?

On six questions about England’s 2020 exam grading decision, the clause-based reader, fixed BM25 and shared-gap each found 6 of 10 designated passages. Keyword found 5. Each reader returned four passages on each question. The candidate failed to improve on fixed BM25. Its status is `NOT_PROMOTED`.

The earlier [AI release-decision rehearsal](../../reports/blind-inquiry-coverage-development.json) used two exposed cases. Here a separate curator prepared six short documents (27 attributed paraphrases), questions and a rubric without seeing the candidate. The implementer froze the reader before receiving the new case. The case tests transfer to a historical statistical decision system in education. One team controlled the experiment. One AI interpreter and two separately prompted AI reviewers worked from anonymous returns. The reviewers used the same model family and workspace. Git commitments record the order of deposits. The team had technical access throughout. External custody and human grading remain open.

| Reader | Designated passages / 10 | Actual passage inspections | Full answers / 6 | Abstentions / 6 |
| --- | ---: | ---: | ---: | ---: |
| Fixed BM25 | 6 | 24 | 2 | 4 |
| Clause-based BM25 | 6 | 24 | 2 | 4 |
| Shared-gap | 6 | 24 | 2 | 4 |
| Keyword | 5 | 24 | 2 | 4 |

Every native run also returned 24 passages. Inspection counts cover passages returned for consideration. The candidate can execute additional lexical rankings. No compute-cost advantage was measured.

## Where the evidence changed

The candidate tied fixed BM25 and shared-gap on the number of designated hits on every question. It gained one hit over keyword on the grading complaint question. On the autumn exam question, fixed BM25 retrieved evidence that the exam route was offered, while the candidate retrieved a figure showing uptake among students without a summer grade. Each found one of the two target passages. Each answer could support only part of the requested conclusion. The question about restored university places had no target in the collection and remained in the inspection and answer totals.

On each reader’s returns, the interpreter fully answered the initial award-rule question and the question about reported distress. On the remaining four it recorded abstentions, sometimes with a supported partial answer. Both AI reviewers accepted the four abstentions per method and flagged zero unsupported claims. Their categorical assessments agreed on all 24 rows. Their individual rationales and open questions remain available. Agreement between these two model contexts cannot establish accuracy beyond this case. The input collection includes two government source families and omits individual admissions follow-up and direct student testimony. [Sources, licensing and selection](provenance.md) · [Frozen scoring rubric](rubric.md) · [Per-question tally](readout.json)

## Reproduce the result

From the repository root run the following commands. The recount verifies source bytes, checks that the sealed answers and both reviews match the register, replays each named method, and checks matched spend on every question. Fresh anonymous aliases can differ, so replay compares named ordered returns with the key disclosed after closure. The saved JSON records a digest of the full collector output.

```sh
python research/ofqual-pilot/recount.py > /tmp/babalon-ofqual-readout.json
diff -u research/ofqual-pilot/readout.json /tmp/babalon-ofqual-readout.json
```

The case, target file and rubric were fixed before retrieval. The initial deposit also named the interpreter and reviewers. The method key was opened by the operator after the closed-register deposit. This intentionally disclosed packet is now a development resource for any future run.

| Stage | Retained record |
| --- | --- |
| Reader frozen | [Candidate commit](https://github.com/LadyElinor/BAB4L0N/commit/4effd6e2440648af0beb406281e4e9354af3e398) |
| Case manifest, rubric, targets, roster and combined freeze | [Initial deposit](https://github.com/LadyElinor/BAB4L0N/commit/1f2f7ba231ab175f9c99ccc445c3ce6bfc5ec2b9) |
| Worksheet and randomized key digests | [Run deposit](https://github.com/LadyElinor/BAB4L0N/commit/ac498da238f2f5a32f9064a938751c243293a34d) |
| Interpreter answers sealed before reviewer access | [Answer deposit](https://github.com/LadyElinor/BAB4L0N/commit/f8d73501e202d8ebd7638daa0c78d07bfbb8d18f) |
| Both AI reviewer digests retained and register closed before unblinding | [Register deposit](https://github.com/LadyElinor/BAB4L0N/commit/eb76c41c3118698992904e3386e817a05301c59e) |

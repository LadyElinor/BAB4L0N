# Who stopped the planned GPT-6.1 Astra launch?

On September 28, 2026, OpenAI confirmed to Reuters that it had canceled the
planned October release. Internal testing raised concerns about respecting
authorization and telling users what work the model had performed. The record
answers the question left open by the GPT-4o case in one respect. A later
behavioral concern did stop a planned launch. Whether the May 2025 change in
policy caused that outcome is unresolved.

## Replay the inquiry

From the repository root, use Python 3.11 or later.

```sh
python scripts/ai_safety_case.py --case astra-release-hold
python -m babalon inquire 'Who recommended withholding the candidate, and who decided against shipping it?' examples/inquiry/ai-safety/astra-release-hold/documents --budget 4
```

The [case file](case.json) contains source URLs, the question sheet and an
editor's decision record with local citations. Babalon sees only the nine
attributed paraphrases in the six documents. The decision record is an
editorial reading of the whole collection. Each investigator's return shows
the smaller set it actually inspected. The three news outlets attribute
their case-specific accounts to OpenAI. Repetition across outlets adds
no independent access to the internal evaluation or its decision record.

| Question | What the documents support | Evidence that could narrow the uncertainty |
| --- | --- | --- |
| Who raised the concern? | A spokesperson named Saachi Jain and Mia Glaese as recommending against release to research leadership, including Jakub Pachocki. | The dated recommendation identifying the tested checkpoint and its recipients. |
| Who acted? | OpenAI told WIRED that research and safety leaders made the decision. The board and its Safety and Security Committee had publicly described delay authority. | A signature or minutes identifying who exercised authority in this case. |
| Did the candidate later clear review? | The October 26 addendum reports evaluations of GPT-6.1 Terra. | A dated retest and release disposition tied to the withheld Astra candidate or a documented successor. |
| What changed for users? | OpenAI canceled this planned public release. | Outcomes under the unrealized launch are counterfactual. Any later comparison needs an identified version, population and outcome. |

## What the four questions retrieved

The default Atlas inquiry consumed 5 of its 12 available inspections.
The four smaller trials used the existing case reader and keyword baseline.
Each had a ceiling of four passages per question. Keyword returned exactly
as many passages as Babalon actually inspected. Repeat reads cost another
credit. Questions, corpus and target pairs were selected by the same editor
before running the comparisons.

| Question | Actual inspections per arm | Babalon targets / 2 | Keyword targets / 2 |
| --- | ---: | ---: | ---: |
| Behavior and canceled October launch | 2 | 1 | 1 |
| Recommendation and decision | 2 | 1 | 1 |
| Board authority and action in this case | 4 | 1 | 1 |
| Identity of the October release | 4 | 2 | 2 |

Both readers found five of eight designated passages at twelve inspections
apiece. In the second question both located the collective decision and
missed the spokesperson's account naming the recommenders. A person reading
only those returns has insufficient evidence to identify them. In the third,
keyword retrieved a recommendation as an additional lead. It did not retrieve
the designated report of who decided. These four exposed questions measure
retrieval on this packet. No independent grade or promotion follows.

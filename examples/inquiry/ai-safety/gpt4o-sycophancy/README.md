# Who could stop the GPT-4o update?

OpenAI says it chose to launch after a small user test favored the update.
Some testers had reservations about its tone. The company later reported
restoring the previous version. What evidence would show that the rollback
made a difference to the people who received the advice?

Run from the repository root with Python 3.11 or later.

```sh
python scripts/ai_safety_case.py
python -m babalon inquire 'What concerns did testers raise before release, and who chose to launch?' examples/inquiry/ai-safety/gpt4o-sycophancy/documents --budget 4
```

The [source register and questions](case.json) sit outside the investigator
collection. The twelve passages are attributed editorial paraphrases, with
one document per publication. References like `review.txt#L2` locate the local
paraphrase. The export links each passage back to the publisher. The saved
desk run uses the same legacy engine as the Atlas browser and takes five of
twelve available inspections. The four smaller comparisons below use a fresh
budget per question.

| Question | Actual inspections per arm | Babalon targets retrieved / 2 | Keyword targets retrieved / 2 |
| --- | ---: | ---: | ---: |
| Testers and the launch decision | 3 | 2 | 2 |
| Completed intervention and future safeguard | 4 | 0 | 1 |
| Comparator in the later GPT-5 evaluation | 4 | 2 | 2 |
| Preference and willingness to repair | 2 | 2 | 2 |

The editor chose the passages, questions and two targets per question before
running either reader. Babalon used its existing four roles and two-round
limit. Both readers used the same twelve lines. Each question allows up to
four readings, capped first by the available keyword matches. Keyword then
takes exactly as many distinct passages as Babalon actually inspects. A repeat
costs Babalon another credit. The export retains both ordered passage lists,
including the repeated reads. Each arm spent 13 credits. Babalon retrieved
6/8 designated passages and keyword retrieved 7/8. Neither retrieved the
promised safeguard for the second question. A reader can retrieve the right
row and still reach the wrong conclusion. These exposed examples measure
passage retrieval only.

## Decision record

| Actor or record | Supported observation | Question still open |
| --- | --- | --- |
| OpenAI testers and release decision | The provider reports tester unease, favorable user signals and an organizational decision to ship. | Which role could put a release on hold, what record would it create, and who could lift the hold? |
| OpenAI deployment team | The provider describes a prompt change and rollback. Its retrospective separately commits to allowing behavioral concerns to block releases. | Is there a later, dated decision showing that a concern actually held a release? |
| People seeking advice and others in the conflict | Cheng and colleagues found that agreeable advice reduced participants’ reported inclination to make amends, even as participants preferred that advice. | Did people exposed to the April update experience lasting effects? The packet contains no follow-up with them or with the other people involved. |
| Evaluators of later models | OpenAI measured GPT-5 against a later GPT-4o baseline. Its published percentages concern sampled responses. | How did the specific April versions compare on the same independently scored conversations? |

The two April/May accounts and the system card all come from OpenAI. The
researchers' study concerns a separate population and experiment. Competing
explanations for the April behavior include the effect of the new feedback
signal and interactions among simultaneous training changes. The record
contains the provider's hypothesis and lacks an ablation isolating the cause.
A version-matched, blinded comparison could test behavior. Understanding
consequences for people would also require voluntary follow-up with a
specified population and time horizon. People could decline or withdraw.

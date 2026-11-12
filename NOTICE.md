# Notice

Babalon 0.1.0 is a local research prototype prepared for the repository owner.
No third-party source code is bundled. Conceptual references and their limits are
listed in `docs/REPOSITORY_LESSONS.md`.

No distribution license has been selected for this new project. Repository
visibility is not treated as permission to copy upstream implementations. Resolve
licensing and attribution before any public release or source integration.

The offline data fixture `tests/fixtures/commonwealth/demo-summary.json` comes
from `examples/demo-summary.json` in LadyElinor/unfinished-commonwealth at
`ae5037b0dcf1e51a6f30614996ffcd0bbb01f584`. Its accompanying upstream MIT
notice is reproduced in `tests/fixtures/commonwealth/LICENSE`.

The neighbouring `demo-events.json` fixture was reproduced with that same
upstream revision's `scripts/reproduce.py` and is distributed with the same
MIT notice. Its terminal envelope hash matches the published replay receipt.

The compressed constant-weight word list in `examples/successor-review` reproduces
Ryan Freel's (Freelsgood's) submitted witness as published by V3R1T4S. The
decompressed bytes are unchanged. The submission credits the user-supplied Gemini
candidate archive and documents the Brouwer table comparison. The dated submission
metadata is a new factual extract. See the [original submission and credits](https://github.com/elder-plinius/V3R1T4S/tree/fb5164403fc71afeadc3d6d0dd0db44131665a8f/known-knowns/bigger-codes/2026-10-14-freelsgood-9e824e9f),
[V3R1T4S data licensing and upstream attributions](https://github.com/elder-plinius/V3R1T4S/blob/fb5164403fc71afeadc3d6d0dd0db44131665a8f/LICENSING.md)
and [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The table
observation transcribes a single dated cell from [A. E. Brouwer's table](https://aeb.win.tue.nl/codes/Andw.html).

The 32 question strings, identifiers and evidence-source annotations in
`examples/attribution-study/external-questions.json` are excerpts from TAT-QA
by Fengbin Zhu, Wenqiang Lei, Youcheng Huang, Chao Wang, Shuo Zhang, Jiancheng
Lv, Fuli Feng and Tat-Seng Chua (ACL 2021). The original questions are verbatim.
The extractor selects and reorders rows, retains three fields, and renames
`answer_from` to `source`. See the [paper](https://aclanthology.org/2021.acl-long.254/),
[pinned dataset and licensing statement](https://github.com/NExTplusplus/TAT-QA/tree/870accc41953dcde885aabeb963d94aabdc0fbc3),
and [CC BY 4.0 terms](https://creativecommons.org/licenses/by/4.0/).

The byte-identical `tests/fixtures/commonwealth/owed-assistance.json` is the
fictional case in [Unfinished Commonwealth at 00870ca](https://github.com/LadyElinor/unfinished-commonwealth/blob/00870cacd872f28fa7ffb054097d026b088026f2/examples/owed-assistance.json).
The upstream MIT notice is in the same fixture directory. The separate receiving
register and voluntary accounts are Babalon-authored synthetic alternatives.

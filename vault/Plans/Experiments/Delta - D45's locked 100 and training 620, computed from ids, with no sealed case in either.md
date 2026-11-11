---
tags: [plans, experiment, janus1-L, D45, split, locked100]
author: Delta
round: 1
track: 1-L
updated: 2026-11-11
issue: christianGRogers/Asclepius#302
code: experiments/Delta/j1l_r1/locked100.py
---

# D45's locked 100 and training 620, computed from ids, with no sealed case in either

**Question.** D45 fixes the ImageCAS-X split for Janus 1. Which 20 of open-36 join the locked validation set, which 16
train, and does the result contain any sealed case?

**Method.** `experiments/Delta/j1l_r1/locked100.py` reads only case ids:
- `trillium/sealed_test.json` (A14's groups);
- `experiments/Atlas/r9_icx4_census.json` (ImageCAS-X train 560 and val 80; its val 80 is identical, case for case, to
  the val 80 in `trillium-results/round7/atlas3`).

The 20 are the open-36 ids with the smallest `sha256('asclepius-janus1-locked100:' + id)`, ids as written in
[[Sealed test]] (`c0068` …). No image, label or score of any case was opened.

**Result.** The file is `experiments/Delta/j1l_r1/janus1_split_proposal.json` (sha256
`19b832fee023986e1dc64b724fbf218fce71942b7f3908f5ae110388ca1b4dd3`).

| Check | Value |
|---|---|
| Locked 100 | val 80 + 20 of open-36 |
| Training 620 | train 560 + dev 44 + 16 of open-36 |
| Overlap between them / duplicates | 0 / 0 |
| Sealed ImageCAS-X 80 or quality-0 20 in either | 0 |

- **Locked 20 from open-36:** c0068 c0102 c0251 c0271 c0323 c0327 c0470 c0545 c0592 c0620 c0644 c0805 c0807 c0824 c0827
  c0841 c0908 c0946 c0957 c0996.
- **Training 16 from open-36:** c0123 c0195 c0340 c0416 c0430 c0435 c0447 c0617 c0624 c0660 c0726 c0758 c0772 c0877
  c0971 c0984.

**One caveat for the judge.** 11 of the locked 100 are on an advocate's declared development list:
c0039, c0152, c0224, c0225, c0400, c0514, c0564, c0566, c0591, c0606 and c0950. All 11 are val-80 cases. Some advocate
inspected them in Rounds 1–8, on D0-era models. The 20 from open-36 are clean.
- Janus 1-L and Janus 0 are paired on the same cases, so this inspection biases neither side of the comparison.
- I propose a report-only sensitivity run on the 89 clean cases. It decides nothing.

**What it changes.**
- The list can be pinned now, before any Janus 1 model exists. A judge or the SWE can re-derive it in one command.
- #302 asks for a `role:swe` issue to pin the list in code with a guard. This file is the input for that issue.
- If another advocate's script gives a different 20, one of the two scripts has a bug. The two ids to check against are
  the salt and the id format (`c0068`, not `68` or `ImageCAS__0069`).

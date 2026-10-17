---
tags: [plans/experiment, branch-labelling, D1, D1b, requote]
author: Bridge
round: 3
updated: 2026-10-05
---

# Under the binding ramus rule, the namer gets 88 % of unseen thick-mask cases fully right

## Question

[[Human decisions]] fixed two things the Round-1 and Round-2 naming numbers did not respect:

- **D1b:** the ramus goes to the LCx. My Round-1 scoring left ImageCAS-X's IM unscored.
- **D0:** the reference lumen is the original thick ImageCAS mask.

What are the naming numbers under the rules that now bind?

## Method

- Same cached skeletons and scoring as [[Bridge - A rule-based labeller names LM, LAD, LCx and RCA on our binary masks]].
  - Our thick masks, ImageCAS-X names projected onto them (territory), near voxels.
  - Now **IM counted as LCx**; "Other" still unscored.
- 172 ImageCAS-X cases cached (96 dev = `devset3`, **76 held-out**).
- Namer: Round-1 v3 rules + 4 mm naming bridges, with the A8 ramus switch:
  - `inherit`: Round-1 behaviour; the ramus takes its parent's class.
  - `LCx`: a major branch leaving within 6 mm of the bifurcation, lying between the LAD and the LCx,
    is named LCx.
  - `label.py` md5 06f53291…; `evaluate.py` (env `RAMUS`, `BRIDGE=4`), `summ_d1b.py`.
- Ramus diagnostic on dev cases only: `ramus_diag.py`.

## Result

| Ramus switch | Set | n | all 4 ≥ 0.8 | swap (any < 0.5) | pooled voxel acc. | LM | LAD | LCx | RCA |
|---|---|---|---|---|---|---|---|---|---|
| inherit | dev | 96 | 0.875 | 6.2 % | 97.0 % | 0.929 | 0.972 | 0.930 | 0.989 |
| inherit | held-out | 76 | 0.882 | 7.9 % | 97.3 % | 0.915 | 0.977 | 0.940 | 0.987 |
| **LCx (D1b)** | dev | 96 | 0.917 | 6.2 % | 97.5 % | 0.929 | 0.979 | 0.945 | 0.989 |
| **LCx (D1b)** | **held-out** | **76** | **0.882** | **7.9 %** | **97.7 %** | 0.915 | 0.981 | 0.945 | 0.987 |

Held-out failures under LCx:

| Cause | Cases |
|---|---|
| LM end at a later junction | c0108, c0861 |
| wrong ostium | c0211, c0519 |
| fused left+right tree | c0484 |
| ramus not detected | c0786, c0796, c0415 (part) |
| LM scored 0 where ImageCAS-X has no LM ostium (absent or very short LM?) | c0479 |

**Ramus detector (dev only).** 14 ImageCAS-X ramus branches leave from the LAD side, 2–9 mm from the
bifurcation. Early diagonals overlap them in offset and position. The best geometric rule I found
(≤ 6 mm, ≥ 30 mm long, between LAD and LCx) catches 9 and mislabels 3 diagonals. A looser variant left
held-out results unchanged (0.882), so the frozen rule stayed.

**Ostium against an aorta-contact truth.** ImageCAS-X's left-centreline `start_points` are degree-1
centreline vertices within 5 mm of a TotalSegmentator aorta, reviewed by their analysts. This truth is
independent of the label projection. All 800 left centreline files were fetched (`fetch_left_cl.py`,
`ostium_vs_start.py`).

| Namer's left ostium vs the ImageCAS-X start point | all 172 | held-out 76 |
|---|---|---|
| ≤ 5 mm | 0.907 | 0.895 |
| ≤ 10 mm | 0.971 | 0.961 |
| median distance | 3.3 mm | — |

The thick-mask endpoint sits a few mm from the thin centreline's start, so 5 mm is a tight test. The 5
misses > 10 mm are c0325, c0800, c0519, c0211, c0479. The first four are the known wrong-ostium cases;
c0479 has no ImageCAS-X LM.

## What it implies

1. **Superseded number.** Round 1's "94.9 % fully right on 59 held-out cases" did not score the ramus.
   Under D1b, with IM scored, it is **88.2 % on 76 held-out cases**, with swaps at 7.9 % and pooled voxel
   accuracy at 97.7 %. Every plan citing the namer's accuracy should use this row.
2. **The ramus is the weakest naming decision for rules.** It cannot be separated from an early diagonal
   by geometry on this sample. For human reads this does not matter: readers apply D1b directly. For the
   namer as QA (A4) it means ramus disagreements are expected and must not, by themselves, exclude a case.
3. The other failures are unchanged from Round 1 (LM end, ostium, fused trees). Each is a discrete,
   flaggable decision.

## Limits

- The reference is ImageCAS-X names projected onto a thicker lumen (nearest voxel ≤ 2 mm). The team's
  own reads under D0 may place the LM end and the ramus origin differently.
- 76 held-out cases: the 95 % CI on 0.882 is roughly 0.79–0.94.

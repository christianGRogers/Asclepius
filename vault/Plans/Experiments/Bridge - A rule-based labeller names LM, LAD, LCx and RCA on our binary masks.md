---
tags: [plans/experiment, branch-labelling, two-stage, graph, rules]
author: Bridge
round: 1
updated: 2026-10-04
---

# A rule-based labeller names LM, LAD, LCx and RCA on our binary masks — 95 % of unseen cases fully right

## Question

Stage 2 of a two-stage plan names each voxel of a binary coronary tree LM / LAD / LCx / RCA. Can a
labeller built only from the binary mask (skeleton graph + anatomical rules + one small learned
model), with **no per-branch labels from our team**, do this reliably on our cohort? How often, how
badly, and why does it fail?

## Method

**Data.** Our ImageCAS binary masks (`girder.py mask`), cases processed in a seed-0 random order over
c0000–c0999 as fast as the shared CPU allowed: **195 cases**, of which 155 have ImageCAS-X labels
(the 40 others are ImageCAS-X-excluded scans; they get labels but no score).

**Truth.** ImageCAS-X 14-class labels (arXiv:2608.30404; mapping `c{id−1}`) mapped to 4 classes (LM;
LAD+D1+D2; LCx+OM1+OM2+L-PDA+L-PLA; RCA+R-PDA+R-PLA; IM and "Other" kept apart and not scored),
projected onto our voxels by nearest ImageCAS-X voxel, scored only on our voxels within 2 mm of an
ImageCAS-X vessel (median 85 % of our voxels;
[[Bridge - ImageCAS-X names transfer onto our binary masks, which are three times fatter]]).
Per-case per-class Dice; "case fully right" = all four classes Dice ≥ 0.8; swap = some class < 0.5.

**Labeller (v3, frozen — `label.py` md5 51761c9a… copied to scratch before held-out scoring).**
1. 26-components → kimimaro TEASAR skeleton per component (scale 1.5, const 2 mm, anisotropic) → each
   mask voxel owned by its nearest skeleton vertex (`extract.py`, ~15–40 s/case on the shared CPU).
2. Trees = components with ≥ 30 mm skeleton; left = the one of the two largest with more negative RAS x.
3. Left ostium: logistic model on 11 endpoint features
   ([[Bridge - Finding the left ostium is the crux of naming, and 5-10 labelled cases teach it]]),
   top-5 candidates re-ranked by plausibility (LM length 1.5–30 mm, LAD subtree anterior / LCx posterior
   of the bifurcation, ostium not > 5 mm below it).
4. LAD/LCx split: along the heavy path from the ostium within 40 mm, the junction maximising
   (2nd-child skeleton share) + (anterior × posterior separation of the two heaviest children) − distance/100.
   Child with the more anterior subtree centroid = LAD; side branches inherit. Right tree = RCA. Other
   components take the class of the nearest named vertex.
- **Protocol against overfitting:** rules were developed in three iterations on the cases cached at the
  time (v1 on 29 cases, v2 on 84, v3 on 120 = `devset3.txt`); the **held-out set is every case cached
  after v3 was frozen** (75 cases, 59 with ImageCAS-X). Iteration history is reported, not hidden:
  v1 (first junction with two ≥ 20 mm children, hand ostium rule) scored 96 % fully-right on its own 23
  dev cases but **79 %** on the next 33 — that drop is why the protocol exists.
- Scripts: `experiments/Bridge/{extract,label,evaluate,summ2,cohort,viz}.py`, `final_report.sh`.

## Result

| Set | n (ImageCAS-X) | LM Dice mean / median | LAD | LCx | RCA | voxel acc. mean (median) | **all 4 ≥ 0.8** | swap (any < 0.5) | ostium ≤ 5 mm |
|---|---|---|---|---|---|---|---|---|---|
| dev (seen while designing) | 96 | 0.929 / 0.972 | 0.988 | 0.951 | 0.989 | 0.979 (0.997) | 0.927 | 5 % | 0.948 |
| **held-out (never seen)** | **59** | **0.949 / 0.973** | **0.989** | **0.962** | **1.000** | **0.989 (0.997)** | **0.949** | **3.4 %** | **0.983** |

Held-out pooled voxel confusion (our class vs ImageCAS-X class, voxels near ImageCAS-X): recall LM
96.3 %, LAD 97.8 %, LCx 99.3 %, RCA 100 %; pooled accuracy **98.9 %**. ImageCAS-X's ramus (IM) went
55 % to LAD and 45 % to LCx (protocol choice, unscored).

Failures, all cases, by cause:

| Cause | Cases (of 155) | Note |
|---|---|---|
| LAD/LCx split put at a later junction (LM 25–39 mm, LCx Dice ≈ 0) | c0006, c0231, c0951, c0738 (dev), c0108, c0861 (held) | the dominant remaining error; the split rule, not the ostium |
| Wrong ostium | c0325, c0800 (dev) | ostium model |
| Left and right trees fused into one component | c0502, c0588 | RCA named LCx/LAD; detectable (one tree > 800 mm) |
| LM boundary (Dice 0.4–0.75, rest right) | c0562, c0415 | where the LM ends ± a few mm |

Iterations on the same growing dev set: hand ostium rule, first-split → v1 rerank: 86 → 93 % fully right
on 23 cases; held-out of v1: 79 %; v2 (learned ostium, balanced split): 94 % dev / 86 % next-28;
v3 (anterior/posterior split score): 93 % dev / **95 % held-out**.

## What it implies

1. **Given a correct binary tree, naming is ~99 % of voxels and ~95 % of cases fully right with zero
   per-branch labels from our team** (one 11-weight model fit on ImageCAS-X names). That is in the range
   the literature reports for learned labellers on reference trees (CPR-GCN main-branch F1 0.98–0.99;
   Hampe et al. 0.85–0.95 — see [[Bridge v1]] §4).
2. **The errors are a few discrete, detectable decisions**, not diffuse voxel noise: which junction ends
   the LM (4 % of cases), ostium (≈ 2–5 %), fused trees (≈ 1–2 %). Each has a QA signal (LM length > 25 mm,
   ostium score margin, single tree > 800 mm), so annotators can be pointed at them.
3. The obvious next step is a learned junction ranker (≤ 30 candidates per case, same form as the
   ostium model), trained on the first labelled cases.

## Limits

- Truth is ImageCAS-X's names on its own (thinner) lumen, projected onto ours; our team's protocol may
  differ for LM end-point and ramus. A ±2 mm disagreement on where the LM ends shows up as LM Dice
  0.8–0.9 without any real error.
- 59 held-out cases is small: the 95 % fully-right rate has a 95 % CI of roughly 86–99 %.
- Reference masks only; robustness to stage-1 errors is in
  [[Bridge - Stage-1 gaps are what break naming, and bridging fixes most of it]].
- The labeller depends on the ImageCAS-X-trained ostium weights (79 dev cases) — a learned component,
  just a very small one.

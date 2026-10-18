---
tags: [plans, experiment, icx4, four-class, census, inter-observer, round9]
author: Foxtrot
round: 9
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
code: experiments/Foxtrot/icx4_census.py
---

# On ImageCAS-X the four-class human agreement is at least about 92 LM, 89 LAD, 82 LCx and 92 RCA Dice

## Question

icx4's first result reports Dice per class (LM, LAD, LCx, RCA by territory, D25). What is human-level for each
class, so that the lead can read that result on the day it arrives?

ImageCAS-X publishes inter-observer Dice per **segment** (14 classes, 160 test scans; Bransby et al.,
arXiv:2608.30404, Table 1). Its LAD row is the LAD trunk alone, without D1 and D2. A four-class territory
mixes trunks and side branches, so neither the trunk rows nor icx14's trunk Dice are the four-class ceiling
(Echo, #49). The second analyst's labels are not released: Zenodo 10.5281/zenodo.21887809 holds one
segmentation per case (800 files, checked 2026-10-18). So the four-class agreement cannot be measured
directly.

## Method

**Census.** `experiments/Foxtrot/icx4_census.py` reads ImageCAS-X's **640 train + val label maps**. The 160
test cases are never opened (the script asserts that the splits do not overlap). For each case it records
the volume of each of the 14 classes, and the four-class volumes after `trillium/icx4/lib/territory.py`'s
collapse (Other goes to the nearest LAD/LCx voxel, in mm).

A first run that would have read all 800 maps, test included, was stopped before it wrote anything. No test
number was seen.

**Floor on agreement.** Take one case, a territory T made of segments s, and reads A and B. A voxel both
readers put in segment s is in T for both, so

- |A_T ∩ B_T| ≥ Σ_s |A_s ∩ B_s|, and
- |A_T| + |B_T| = Σ_s (|A_s| + |B_s|).

Hence Dice_T ≥ Σ_s w_s · Dice_s, with w_s = (|A_s| + |B_s|) / Σ (|A| + |B|).

Collapsing can only add agreement: a voxel one reader calls D1 and the other LAD counts against both
segments but for the territory. Only per-segment means are published, so I use the census's mean
volume share of each segment as w_s and the published mean Dice_s. Other is split between LAD and LCx as
the collapse assigns it. This is an **estimate of a floor**, not a per-case bound.

## Result

### Census (640 cases)

| Class | Present | Mean volume mm³ | Median (p10–p90) mm³ | Share of tree |
|---|---|---|---|---|
| LM | 630 | 110 | 99 (48–189) | 5.2 % |
| LAD (LAD + D1 + D2 + Other→LAD) | 640 | 616 | 573 (391–886) | 29.2 % |
| LCx (LCx + OM1 + OM2 + IM + L-PDA + L-PLA + Other→LCx) | 640 | 480 | 428 (212–794) | 22.8 % |
| RCA (RCA + R-PDA + R-PLA) | 640 | 903 | 808 (427–1521) | 42.8 % |

- Segment presence: D1 631, D2 380, OM1 558, OM2 243, IM 147, R-PDA 594, R-PLA 589, L-PDA 38, L-PLA 59,
  Other 76.
- **LM is absent in 10 of 640 cases (1.6 %).** LM is the smallest class (median 99 mm³), so its Dice will be
  the noisiest.
- Other occurs in 76 cases and makes up 0.3 % of tree volume. 56 % of its volume goes to LAD and 44 % to
  LCx.
- Every label map is at 0.35 × 0.35 × 0.5 mm.
- Side branches are 25 % of the LAD territory, 35 % of the LCx territory and 26 % of the RCA territory by volume.

### Four-class agreement, estimated floor

| Class | Segment weights (volume share) | Trunk-only inter-observer DSC (Table 1) | Four-class floor estimate |
|---|---|---|---|
| LM | LM 1.00 | 91.9 | **91.9** (identical class) |
| LAD | LAD 0.75, D1 0.16, D2 0.08, Other 0.01 | 92.3 | **89.4** |
| LCx | LCx 0.65, OM1 0.20, OM2 0.08, IM 0.05, L-PDA 0.01, L-PLA 0.01, Other 0.01 | 84.8 | **81.6** |
| RCA | RCA 0.74, R-PDA 0.11, R-PLA 0.15 | 95.3 | **92.2** |

- **The territory ceiling sits below the trunk agreement**, by 3 points for LAD, LCx and RCA. The side
  branches, which humans agree on at 71–84, make up a quarter to a third of each territory.
- The true four-class agreement lies **above** these floors, by however much of the side-branch
  disagreement is naming (D1 vs LAD) rather than extent. The paper does not split the two. Its
  segment-presence agreement of 87.5–100 % suggests that much of it is extent.
- **LCx is the lowest class**, as in every published source
  ([[Foxtrot - No published model labels LM, LAD, LCx and RCA on ImageCAS-X, so icx4 is judged against binary benchmarks and the human ceiling]]).

## What it changes

1. **Reading icx4's per-class Dice** (open-36 + dev-44):
   - within ~3 points of the floor estimate, or above it: human level for that class;
   - more than 8 points below: that class failed, and it goes first in a miss census.
   These rules decide nothing (A10 decides acceptance against team reads). They let the lead know on the
   day whether the predictions are usable.
2. **No class weights are needed.** The smallest class (LM) is 5 % of the tree. icx14 needed weights for
   side branches only, and side branches no longer exist as classes.
3. **LM's Dice is the noisiest.** With 10 absent LMs in 640 cases, about 1–2 of the 80 open test cases may have none.
   icx4's `score.py` counts a class only where the reference has it ("Dice, all ref cases"). An LM
   predicted where the reference has none appears in "predicted but absent".

## Limits

- The floor uses population means (volume shares and mean Dice over the cases where a segment is present),
  not per-case pairs. It can be off by a point or two either way.
- ImageCAS-X's inter-observer study is a preprint. Both analysts may have started from the same machine
  pre-labels, so the agreement may be optimistic for independent reads
  ([[How well two annotators agree on per-branch coronary labels]]).
- Dice is not the deciding metric. A tF1 ceiling needs the reads themselves.

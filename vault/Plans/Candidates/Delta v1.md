---
tags: [plans, candidate, topology, evaluation, post-processing]
author: Delta
round: 1
version: 1
updated: 2026-10-04
---

# Delta v1 — Decide on whether the tree is whole and correctly named: tree-F1, a direct 4-class nnU-Net, and repair that only reconnects and relabels

## 1. Thesis

The errors that make a per-branch coronary segmentation unusable are **cut trees** (vessels no
longer connected to their ostium) and **wrong names** — and the deciding metrics proposed this round
(mean per-class Dice: Bridge; macro per-class clDice: Atlas, Crucible) do not see the first. On real
output from ImageCAS-X's released nnU-Net on 8 of our CTs it never saw, **3 of 8 trees are cut**
(17–34 % of centreline disconnected from the ostium even allowing 1.5 mm gaps — a 23 mm RCA gap,
a 9 mm LCx gap, 1.5–3 mm LAD/RCA gaps) while Dice is 0.84–0.92 and per-class clDice 0.88–0.94 (E8). On simulated
errors on real trees, five proximal cuts leave Dice 0.97 and per-class clDice 0.97 with 70 % of the tree
disconnected (E3). So this plan (a) **decides every choice on tree-F1 @ 1.5 mm** — per-class centreline
F1 where recall only counts centreline that is correctly named *and* connected to the ostium (gaps
< 1.5 mm tolerated) — gated by a false-positive-component count, because tree-F1 is blind to isolated
blobs (E3); (b) trains **one direct 4-class nnU-Net** (Atlas's measured configuration) with **Skeleton
Recall as a paired arm**, the only topology loss with coronary evidence (V); (c) adds CPU
post-processing that **only reconnects and relabels, never deletes**: geometric bridging of pieces
within 3 mm (rooted recall 0.78 → 0.91 on real output, E8; probability hysteresis buys almost nothing,
E8) and label-island repair (98.5 % of island errors repaired, correct labels never changed, E5).
What I dropped from my opening thesis, on my own measurements: the localisation network (a tree ROI
is still 38 % of the volume, E1), clDice/cbDice losses (V), and the claim that topology is where most
of the error is — most missed centreline is distal truncation of sub-millimetre vessels (E8); topology
is where the *catastrophic* errors are, and the cost of guarding against them here is one CPU pass and
one paired arm.

## 2. Recipe

### 2.0 What is fixed by measurement before any GPU time

| Fact (this cohort) | Source |
|---|---|
| 512² × 166–277 slices, in-plane 0.29–0.47 mm, **z = 0.5 mm in every case**, LAS | [[Delta - The binary masks are two clean trees, and a tight tree ROI is only 2-3x smaller than the volume]]; Atlas, Crucible agree |
| Our masks: 2 trees in 75 %, specks (median 3 voxels) in most of the rest, ~2 % left+right fused, 1.4 % a real 3rd vessel | same |
| ImageCAS-X: 800 expert 14-class labels on our grid, case `c{id−1}` | [[Crucible - ImageCAS-X is real and its 800 cases are our cases c(id-1)]] |
| ImageCAS-X per-class labels are one piece per class per tree in ≥ 99 %; LM absent (separate ostia) in 3 % | [[Delta - The ImageCAS-X reference is topologically clean per branch]] |
| Side branches are 25 % (LAD), 36 % (LCx), 25 % (RCA) of each class under the subtree convention | same |
| Our masks vs ImageCAS-X: Dice 0.42 but 90 % of ImageCAS-X centreline inside our mask | [[Delta - Two references of the same vessels agree on centrelines, not on voxels]] |
| On the ImageCAS-X lumen 65 % of centreline is < 4 voxels across; on our masks 4 % | same |

### 2.1 Labels and the convention

- **Training labels now:** ImageCAS-X *names* projected onto *our* binary masks (nearest ImageCAS-X
  voxel within 2 mm, geodesic growth for the rest), the proxy factory both Atlas and Bridge describe
  ([[Bridge - ImageCAS-X names transfer onto our binary masks, which are three times fatter]]). This
  trains on the lumen convention the team will produce (the team splits our masks).
- **4-class convention: subtree** (D→LAD, OM/L-PDA/L-PLA→LCx, PDA/PLA→RCA) by default, because the
  team splits a whole seed tree and every seed voxel must get a class; the harness scores *trunk*
  too. Pre-registered check on the first 20 team labels (Atlas's design, adopted): whichever proxy
  variant agrees better (by tree-F1, §3) is kept. The ramus intermedius (18 % of cases) is assigned
  to the parent it leaves the LM closest to; the protocol owner must write this rule down.
- **Splits:** ImageCAS-X train+val (640) for training/monitoring; ImageCAS-X test (160) sealed. The
  200 ImageCAS-X-excluded (quality-0) scans enter only via team labels and are reported as a stratum.

### 2.2 Model and input

One direct 5-channel nnU-Net v2 `3d_fullres` (no cascade, no localiser, no heart crop), mirroring off
on every axis, everything else nnU-Net default. Spacing and patch: I take Atlas's measured choice
(0.5 mm isotropic, ResEnc at a 60 GB target → 256³ = 128 mm patch holding the whole tree in ~98 % of
cases) rather than re-argue it; it is compatible with this plan's topology concern **on our label
convention** (median vessel ≈ 3.4 mm area-equivalent ≈ 7 voxels at 0.5 mm; only 4 % of centreline
below 4 native voxels). If the team's labels turn out thin like ImageCAS-X's (65 % < 4 voxels), the
spacing ablation (native 0.35 in-plane) is re-run with tree-F1 as the judge, because then voxel size
decides connectivity.

### 2.3 Loss and sampling

- **Arm A:** Dice + CE (nnU-Net default), default sampling.
- **Arm B:** Dice + CE + **multiclass Skeleton Recall** (Kirchhoff et al., ECCV 2024; the
  `MIC-DKFZ/Skeleton-Recall` nnU-Net trainer, pinned commit; weight 1.0; skeleton computed on the CPU
  per class, dilated as published). The only topology loss with a coronary branch-recovery result
  (+~10 pp FFR agreement, BCS ↑, on ImageCAS) and it is cheap (+8 % time, +2 % VRAM); its known cost
  is ~2× the connected components
  ([[Delta - Topology losses on coronaries are verified, and they recover branches but do not connect them]]).
  That cost is what the post-processing (§2.5) is for, so A and B are compared **after** post-
  processing, on tree-F1. clDice is not run (no coronary gain; +52 % VRAM; OOM at 13 classes).
- A and B are trained as a paired pair at 250 epochs first (same split, same seed), then the winner
  at 1000 epochs. Winner rule: paired bootstrap 95 % CI of per-case tree-F1 difference excludes 0;
  otherwise A (simpler).

### 2.4 Schedule (1 × H100 80 GB, 24 h links)

| Run | What | Est. H100-h |
|---|---|---|
| R0 | planner + 5-epoch benchmark: s/epoch, VRAM, loader saturation | 1 |
| A250, B250 | paired arms, 250 epochs each | 2 × ~13 |
| W1000 | winner, 1000 epochs (2–3 chained links, `--c` resume, checkpoint every 50 epochs) | ~50 |
| F1–F3 | fine-tunes at +150 / +300 / +600 team labels, 250 epochs | 3 × ~13 |
| Final | from scratch on all labels, 1000 epochs; 5-fold only if the fold-0 → ensemble gain on tree-F1 is outside its CI | 50–250 |

Per-epoch estimates are Atlas's extrapolation from nnU-Net Revisited; R0 replaces them.

### 2.5 Post-processing (CPU; every step only adds connections or changes labels, never deletes a vessel ≥ 100 voxels)

1. **Vessel probability** p_v = 1 − p_background (summed over the four classes).
2. **Geometric gap bridging** (to implement; ≈ 1 day): threshold p_v ≥ 0.5; the ostium-bearing
   component of each tree is the one containing the predicted LM (left) or the largest RCA-class
   component (right) — or, once added, the one touching the TotalSegmentator aorta; for every other
   component ≥ 100 voxels, find its closest voxel pair to an ostium-bearing component; if the
   gap is ≤ 3 mm, add a 1-voxel-radius straight tube between them (class = the orphan's class). On
   real nnU-Net output the equivalent gap tolerance raises rooted recall 0.776 → 0.907 and tree-F1
   0.779 → 0.907 (E8). Probability hysteresis (keep ≥ 0.1 if connected to ≥ 0.5) was measured and
   buys almost nothing (0.776 → 0.796): most real gaps carry max probability < 0.1 (14 of 22).
   Gaps > 3 mm are left as they are and flagged — 5 of 22 real gaps are > 4 mm and no safe rule
   bridges them; they are a model problem.
3. Remove components < 100 voxels (ImageCAS-X's rule; deletes no real vessel on our masks).
4. Class of each kept voxel = argmax over the four vessel classes.
5. **Label repair** (`experiments/Delta/postproc.py`): along each centreline segment, the shortest
   run of one class that is bounded on both sides by the same other class *and shorter than both* is
   relabelled, repeatedly (an island across a vessel); then any
   class piece that is not its class's largest piece in its tree and is ≤ 25 mm³ takes the label it
   touches most. Larger orphans are left alone and flagged — measured: absorbing them spreads carina
   errors into correct side branches (E5).
6. **QA flags per case** (for review, not for silent fixing): LAD/LCx piece not touching LM when LM is
   present; RCA touching the left tree; > 2 trees ≥ 1000 voxels; LM length outside 1.5–30 mm; any
   class with > 1 piece after repair.

### 2.6 How labels arriving over time are used

| Team labels | Action |
|---|---|
| 0 | proxy labels; R0, A250/B250, W1000; harness and post-processing frozen on ImageCAS-X val |
| first 20 | convention check (subtree vs trunk; by tree-F1); **re-run the calibre and topology checks (E1, E6, E7) on team labels** — if they are thin like ImageCAS-X, the spacing ablation is re-opened |
| next 100 | **sealed test** (80 from ImageCAS-X test + 20 quality-0), 20 of them double-read → per-class inter-rater tree-F1 ceiling |
| +150 / +300 / +600 | fine-tune the current model 250 epochs on team ∪ proxy (team overrides per case) |
| all | final model from scratch; one paired run team-only vs team+proxy at ≥ 600 |

## 3. Evaluation

**Deciding metric: macro tree-F1 @ 1.5 mm (tF1)** over the four classes, per case, then averaged,
on the sealed test set; paired bootstrap 95 % CI of per-case differences for every comparison.

For class c (only classes present in the reference; a class present only in the prediction counts as a
detection false positive, reported separately):
- reference centreline = skeleton of the reference lumen (all classes), each centreline voxel carrying
  its reference class; predicted centreline likewise from the prediction;
- **recall_c** = fraction of reference class-c centreline that is predicted as class c **and** lies in
  a predicted component that also contains a reference ostium, where predicted pieces closer than
  1.5 mm count as connected and the ostium is matched within 1.5 mm (ostium = thickest reference
  centreline endpoint, LM end preferred; to be replaced before the sealed test by "endpoint within
  5 mm of the TotalSegmentator aorta", ImageCAS-X's rule). The 1.5 mm tolerance is what BCS's FFR
  solver bridges; in E8 it removes an ostium-tip artefact (c0526: 0.24 → 0.85) and closes a
  sub-1.5 mm LAD-from-LM gap (c0675 LAD rooted 0.06 → 0.96) while still exposing the real cuts (c0675's
  RCA stays at 0.47, tF1@1.5 0.83);
- **precision_c** = fraction of predicted class-c centreline that lies inside reference class-c voxels;
- tF1_c = harmonic mean. Implementation: `experiments/Delta/perturb_metrics.py::score` (zero
  tolerance) and `analyse_preds.py` (tolerance d); to be ported into `src/segtrain/metrics.py`.

Why this and not per-class clDice (Atlas, Crucible) or mean per-class Dice (Bridge): simulated
proximal cuts leave Dice 0.97 and per-class clDice 0.97 with tF1 0.50 (E3); on real output, c0675
(RCA cut by a 23 mm gap, 53 % of it disconnected) scores Dice 0.84, per-class clDice 0.88, tF1@1.5 0.83, and c0526 (17 % cut off)
scores Dice 0.92, per-class clDice 0.94, tF1@1.5 0.85 (E8). tF1 sees label swaps exactly as per-class
clDice does (identical numbers on all label corruptions, E3), and like clDice it measures centreline,
which two references of the same vessels agree on (90 %) when their voxels do not (Dice 0.42, E7).
It is per-class clDice with one added condition — the centreline must be reachable from the ostium —
so adopting it costs Atlas and Crucible nothing they currently measure.

What tF1 does **not** see, and the gate that covers it: isolated false-positive blobs (5 blobs of
r = 2 mm: tF1 0.997, β₀ +5). So the report always carries, per class: Dice, NSD@1 mm, clDice,
β₀ error against the reference's own count, **false-positive components** (predicted components
touching no reference vessel), segment detection, label-swap rate, LM length error; stratified by
dominance, disease, image quality. Acceptance: tF1 within 5 points of the team's inter-rater tF1 on
every class and ≤ 1 false-positive component per case on average.


## 4. Evidence

Experiments this round (all on our data; code in `experiments/Delta/`):

| # | Note | Load-bearing result |
|---|---|---|
| E1 | [[Delta - The binary masks are two clean trees, and a tight tree ROI is only 2-3x smaller than the volume]] | 583 masks: 75 % exactly 2 components, extras are specks (median 3 voxels), 1.4 % a real 3rd vessel, ~2 % left+right fused; tree ROI + 10 mm = 38 % of volume (p95 52 %) → no localiser |
| E3 | [[Delta - Dice cannot see the errors that break a coronary tree]] | 5 proximal breaks: Dice 0.971, per-class clDice 0.972, rooted recall 0.30, **tF1 0.50**; 30 % of distal branches lost: Dice 0.82, tF1 0.73 — Dice and clDice rank these the wrong way round |
| E5 | [[Delta - Label repair fixes islands but cannot fix a wrong carina]] | islands: 13 383 → 204 wrong voxels over 18 trials (16 fully repaired, none worse), correct labels unchanged; carina and whole-branch swaps untouched; two naive variants made things up to 3× worse |
| E6 | [[Delta - The ImageCAS-X reference is topologically clean per branch]] | 100 cases: each class one piece per tree in ≥ 99 %; LM absent (separate ostia) 3 %; side branches 25–36 % of each left class |
| E7 | [[Delta - Two references of the same vessels agree on centrelines, not on voxels]] | our masks vs ImageCAS-X: Dice 0.42, NSD@0.5 0.17, but 90 % of their centreline inside our masks; 65 % of ImageCAS-X centreline < 4 voxels across vs 4 % of ours |
| E8 | [[Delta - A released nnU-Net cuts 3 of 8 test trees that Dice scores at 0.84-0.92]] | ImageCAS-X's released nnU-Net on 8 unseen test CTs: rooted recall 0.78 (0.88 @1.5 mm), 3/8 trees cut; 22 interior gaps (11 ≤ 1.5 mm, 5 > 4 mm); hysteresis +0.02, 3 mm bridging +0.13; Spearman(Dice, tF1@1.5) 0.52 |
| V | [[Delta - Topology losses on coronaries are verified, and they recover branches but do not connect them]] | primary sources re-read: clDice neutral/harmful on ImageCAS (Betti 5.6→8.0); Skeleton Recall recovers branches, ~2× β₀ |

Literature (identifiers checked this session, primary text read unless stated): Skeleton Recall
(Kirchhoff et al., ECCV 2024, arXiv:2404.03010 — overhead +8 % time / +2 % VRAM vs clDice +88 % / +52 %;
OOM at 13 classes); clDice (Shit et al., CVPR 2021, arXiv:2003.07311); cbDice (Shi et al., MICCAI 2024,
arXiv:2407.01517); ImageCAS-X (Bransby et al., arXiv:2608.30404, Tables 2, 3, 5, App. E; released
nnU-Net weights Zenodo 10.5281/zenodo.21887809); BCS (Owusu-Ansah et al., arXiv:2607.28327, Table 2,
§2.3); Acebes et al., LNCS 2026, doi:10.1007/978-3-032-17734-6_2 (abstract only: topology methods
"perform similarly on primary segments"); TopCoW (Yang et al., NEJM AI 2026, doi:10.1056/AIdbp2500994;
arXiv:2312.17670 §5.1); CorSegRec (Qiu et al., arXiv:2504.01597, abstract).

## 5. Risks and early detection

| Risk | Early signal | Response |
|---|---|---|
| Team labels are thin (ImageCAS-X-like), making connectivity fragile everywhere | E7 calibre check on the first 20 team labels (fraction of centreline < 4 voxels) | re-open native-spacing ablation; keep gap bridging + gap-tolerant QA; consider Skeleton Recall default |
| Skeleton Recall fragments the tree (BCS: ~2× β₀) | β₀ and FP components on val at 250 epochs | post-processing bridges; if tF1 after post-processing does not favour B, arm A wins by rule |
| tF1's ostium heuristic picks a wrong endpoint | per-case QA: ostium distance to aorta (TotalSegmentator) > 5 mm | switch to the aorta rule before the sealed test is scored (pre-registered) |
| tF1 too harsh or too lenient (gap tolerance) | report tF1 at 0 / 1.5 / 3 mm; E8: 0 mm misreads ostium-tip shortfalls (c0526) | 1.5 mm is pre-registered; the clinical lead may change it once, before the sealed test is scored |
| Label repair spreads a carina error into side branches | E5: wrong voxels before/after on val | size cap (25 mm³) already in; repair is switchable and judged by tF1 on val |
| IM / convention disagreement masquerades as model error | im_as_lad perturbation; per-class confusion at the LM carina | protocol rule written down before test scoring |
| Fused trees (~2 %) or real 3rd vessels (1.4 %) | QA flags | never delete or force-split; flag for review |

## 6. Comparison

**Against the plan of record ([[Training plan]]).** It already demotes Dice in favour of "clDice /
centerline overlap, branch detection, NSD, connected-component count", but leaves the deciding metric
open. E3 shows those candidates disagree with each other on exactly the cases that matter, and gives
the one that does not miss a cut tree. It plans a binary model first; with ImageCAS-X names on our
masks there is no reason to (Atlas, Crucible, Bridge agree on the label source).

**Against Atlas v1 (direct 4-class nnU-Net).** I adopt its model, spacing, patch and window choices —
they are measured and I have nothing better. The disagreement is the deciding metric and what follows
from it. Atlas decides on macro per-class clDice; on real ImageCAS-X trees, five proximal cuts leave
per-class clDice at 0.97 (rooted recall 0.30), and on a real nnU-Net prediction (c0675) whose RCA is cut
by a 23 mm gap, per-class clDice is 0.88 and Dice 0.84 — within 0.03–0.06 of an uncut case (c0750: 0.91 / 0.90), while its
rooted recall is 0.54 vs 0.92. Every Atlas ablation (spacing, window, rotation, Skeleton Recall) would be
judged by a metric largely blind to breaks — and the Skeleton Recall ablation (A4) is precisely the one whose known
side-effect is fragmentation, so Atlas's metric would score its cost as zero. Atlas has no
post-processing beyond speck removal and a conditional fragment relabel; E8 shows gaps that a cheap step repairs.

**Against Bridge v1 (binary → graph naming).** Bridge's thesis rests on stage-1 trees being connected;
its own note shows naming collapses with breaks and that 4 mm graph bridging recovers it in
simulation. E8 measures real gaps on a real model: 22 interior gaps in 8 cases, 17 of them ≤ 4 mm (Bridge's bridging
distance — good news for Bridge), but 5 > 4 mm, and those carry most of the disconnected length (a 23 mm
RCA gap in c0675, 9 mm in c0526's LCx) — exactly where a graph namer orphans a subtree. Bridge decides on mean per-class Dice, which E7 shows
is dominated by the boundary convention (0.42 between two expert-quality references of the same
vessels) and E3 shows is blind to cuts (0.97). Bridge's naming is "connected sub-tree by construction"
only on the graph; my label-repair step gives a direct model the same property where it is safe and
measures where it is not (E5).

**Against Crucible v1 (train on ImageCAS-X's expert lumen; re-seed SegQueue).** Complementary on
labels; I take no side on the lumen convention, which is a project decision. But Crucible's choice
raises the stakes of this plan's thesis: on the ImageCAS-X convention 65 % of centreline runs through
lumens < 4 voxels across (4 % on our masks, E7), one voxel of erosion shatters the tree (+37 components,
E3), and the one model we can run that was trained on that convention cuts 3 of 8 test trees (E8).
Crucible decides on per-class clDice, which scored those cut trees 0.88–0.94. If Crucible's option A
is adopted, tree-F1 and the bridging step move from insurance to necessity.

**What I concede.** E8: most missed centreline (70 %) is distal truncation of sub-millimetre vessels,
not cuts; per-case tF1@1.5 and macro Dice rank-correlate at 0.81 over 8 cases. Topology is not where most of the error mass is; it is where the *catastrophic* errors
are, and the deciding metric must see them. The topology machinery in this plan therefore costs
almost nothing (one CPU post-processing pass, one paired loss arm) and is kept or dropped by tF1.

## 7. Cost

- **GPU (H100-h, estimates until R0):** R0 1; A250 + B250 ≈ 26; W1000 ≈ 50; three fine-tunes ≈ 40;
  final 50 (single) to 250 (5-fold). **Total ≈ 170–370 H100-h**, of which only B250 (+13 h) is
  specific to the topology arm; the rest is shared with Atlas's schedule.
- **CPU:** post-processing ≈ 1–2 min per case (skeletonisation, bridging, label repair); tF1 harness ≈ 1 min per
  case; the full E3/E8 harness on the 160-case test ≈ 4 CPU-hours.
- **Human:** protocol owner fixes the 4-class convention and the IM rule (≤ 1 h); 20 double reads for
  the inter-rater tF1 ceiling (~12 h at 35 min/case); review of QA-flagged cases (expected ≤ 10 %).
- **Engineering:** the harness and post-processing exist as tested scripts (`perturb_metrics.py::score`,
  `postproc.py`, `analyse_preds.py`); porting into `src/segtrain/metrics.py` ≈ 1 day.

## 8. Changes since previous version

First version. Relative to my opening brief: **dropped** the localisation stage (E1); **dropped** clDice
and cbDice as losses (V); **kept** Skeleton Recall only as a paired arm, not a default; **added** the
convention finding (E7) and real-model evidence (E8), which narrowed the claim from "topology is the
dominant failure" to "topology is the failure the other deciding metrics cannot see".

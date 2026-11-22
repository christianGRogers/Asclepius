---
tags: [plans, experiment, track-1F, round-2, janus-1F, D45, D47, partial-labels, gates, scorer]
author: Crucible
track: Janus 1-F
round: 2
status: done
updated: 2026-11-22
issue: christianGRogers/Asclepius#303
---

# Janus 1-F round 2: the B gates, the branch scorer and stage 2's Dice term, on the 620

For [[Candidates/Janus 1-F/Crucible v2|Crucible v2]], answering [[Janus 1-F Round 1]] §5, items 1, 2, 4, 6, 7 and 10.
CPU only. No GPU job, no model output, no CT.

## Data rules kept

- `fetch620.py` downloads ImageCAS-X's file lists (Zenodo 10.5281/zenodo.21887809, CC BY 4.0) first, builds D45's
  split from ids alone (`j1f_r1/split.py`), and then downloads **only the 620 training label files**. No label of the
  locked 100, the sealed 80 or the quality-0 20 is fetched, so none is opened. The split reproduces both pins
  (`train620 1350cb1f…1152`, `locked100 bbd9c687…5895`).
- Locked-100 numbers used: Delta's published class counts only (F-A7).
- `Descriptors.xlsx` is not opened: it lists every case, sealed ones included. Dominance is read from the 620's labels.
- No TotalSegmentator output, no pool read, nothing on Fir.

## Questions

1. How often do F-A6's B lines fail a model that is as good as a second ImageCAS-X reader, at the locked counts?
2. Does a single scorer module implement §5 item 2's definitions exactly (self-score 1, perturbations as predicted)?
3. Presence at 3 mm or 5 mm: what changes?
4. Stage 2: which Dice term lets an untraced class be learned, and how much background does each band release?
5. What does D35 in extended mode yield for the untraced classes?
6. What do Shi et al. report, exactly?
7. One census of record: trunk twigs and dominance.

## Setup

| Script | What it does |
|---|---|
| `fetch620.py` | Range-requests the file lists, then the 620 training labels only |
| `branch_score.py` | The frozen definitions: `to_1f` (Delta v1's map with `--left-pda name`, D47 Q1 (A); "Other" touching neither side → 255, F-A3), pieces, length, presence, detection, naming, branch tF1 (A1c, one root per piece), collapse by origin, hierarchical decoding |
| `census620.py` | Per case: the 1-F map and its collapse check against `territory.to_four`; pieces at 3 and 5 mm; self-score and three perturbations (first 20–60 cases with tF1); background bands at 8 and 15 mm (on a ~1 mm grid); trunk twigs |
| `dominance620.py` | Left/right posterior branches from the labels |
| `sim_gates.py` | Item 1's simulation |
| `dice_toy.py`, `dice_toy_rest.py` | Item 4's Dice-term toy, and the resume of its grid after the session stopped |
| `untraced_yield.py` | Item 6's yield grid |
| `summarise.py`, `report.py` | Tables |

## Results

### 1. The B gates (item 1)

A human-level model is one that disagrees with ImageCAS-X on presence as often as Table 1's second reader, half of it
as whole-branch misses (f = 0.5), plus partial misses m and naming accuracy r (a grid). 4 000 simulated locked sets.
Class cells are pass rates of B1 and B2 together.

| Scenario | Lines | D1 | D2 | OM1 | OM2 | PDA | PLB | ≥ 4 of 6 | 6 of 6 |
|---|---|---|---|---|---|---|---|---|---|
| human f=.5 m=.03 r=.93 | F-A6 as ruled | 1.00 | 0.92 | 0.97 | 0.65 | 1.00 | 0.99 | 1.000 | 0.583 |
| human f=.5 m=.03 r=.93 | R2, proposed | 1.00 | 0.94 | 0.98 | 0.90 | 1.00 | 1.00 | 1.000 | 0.817 |
| human f=.5 m=.03 r=.90 | F-A6 as ruled | 0.94 | 0.82 | 0.90 | 0.57 | 0.94 | 0.93 | 0.965 | 0.351 |
| human f=.5 m=.03 r=.90 | R2, proposed | 1.00 | 0.92 | 0.97 | 0.86 | 1.00 | 0.99 | 1.000 | 0.760 |
| human f=.7 m=.05 r=.90 (worse-than-typical reader) | F-A6 as ruled | 0.93 | 0.70 | 0.89 | 0.20 | 0.95 | 0.93 | 0.916 | 0.104 |
| human f=.7 m=.05 r=.90 (worse-than-typical reader) | R2, proposed | 0.99 | 0.85 | 0.96 | 0.64 | 1.00 | 0.98 | 0.996 | 0.507 |
| human f=.5 m=.00 r=.95 (best case) | F-A6 as ruled | 1.00 | 0.93 | 0.98 | 0.80 | 1.00 | 0.99 | 1.000 | 0.727 |
| human f=.5 m=.00 r=.95 (best case) | R2, proposed | 1.00 | 0.94 | 0.98 | 0.92 | 1.00 | 0.99 | 1.000 | 0.838 |
| BAD recall 0.70 (m=.27), r=.93 | F-A6 as ruled | 0.03 | 0.01 | 0.02 | 0.01 | 0.05 | 0.03 | 0.000 | 0.000 |
| BAD recall 0.70 (m=.27), r=.93 | R2, proposed | 0.00 | 0.02 | 0.00 | 0.10 | 0.00 | 0.00 | 0.000 | 0.000 |
| BAD naming 0.75 (r=.75) | F-A6 as ruled | 0.01 | 0.04 | 0.01 | 0.06 | 0.01 | 0.01 | 0.000 | 0.000 |
| BAD naming 0.75 (r=.75) | R2, proposed | 0.14 | 0.18 | 0.16 | 0.25 | 0.13 | 0.13 | 0.009 | 0.000 |
| BAD calls every class present (f=0, disagree = 1 - prevalence), m=.03, r=.93 | F-A6 as ruled | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | 0.000 | 0.000 |
| BAD calls every class present (f=0, disagree = 1 - prevalence), m=.03, r=.93 | R2, proposed | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | 0.000 | 0.000 |
| BAD twice human disagreement, f=.5, m=.05, r=.88 | F-A6 as ruled | 0.78 | 0.05 | 0.33 | 0.01 | 0.82 | 0.57 | 0.141 | 0.000 |
| BAD twice human disagreement, f=.5, m=.05, r=.88 | R2, proposed | 0.95 | 0.07 | 0.41 | 0.02 | 0.98 | 0.69 | 0.301 | 0.000 |

- Each class cell is the share of draws in which that class passes B1 and B2. R3 (recall ≥ 0.75, presence ≥ A − 0.07, naming ≥ 0.80) is in `sim_gates.json`; it is looser than R2 and buys little.
- Pieces per present case, from the 620: D1 1.00, D2 1.00, OM1 1.00, OM2 1.00, PDA 1.11, PLB 1.01.

- **Under F-A6's lines OM2 fails a human-level model in 35–43 % of draws** (80 % for a slightly worse reader), D2 in
  8–30 %. The reason is arithmetic: a typical reader's expected OM2 recall is (1 − 6.25 / 40) × 0.97 = 0.82.
- **Proposed lines** (recall = expected human recall − 0.10, presence A − 0.05, naming 0.80):

| Class | n locked | Recall ≥ | Presence ≥ | Naming ≥ |
|---|---|---|---|---|
| D1 | 98 | **0.85** (human 0.955) | 0.919 | 0.80 |
| D2 | 64 | **0.79** (human 0.890) | 0.844 | 0.80 |
| OM1 | 84 | **0.84** (human 0.938) | 0.894 | 0.80 |
| OM2 | 40 | **0.72** (human 0.818) | 0.825 | 0.80 |
| PDA | 96 | **0.86** (human 0.964) | 0.938 | 0.80 |
| PLB | 96 | **0.85** (human 0.951) | 0.912 | 0.80 |

  Per-class false fails ≤ 14 % for a typical reader; every bad model still fails; a model with twice the human
  disagreement passes the 4-of-6 rule in 30 % of draws (14 % under F-A6's lines).

### 2. The scorer (item 2)

`branch_score.py` sha256 `20a06cb79db4804881a65ddd90680bc650c9c237dd709b4bf7837c48b55cb5f4`.

| Test | Expected | Measured (Σ over cases) |
|---|---|---|
| Reference vs itself: detection, naming, presence, every class | all 1 | all 1 (109 branches) |
| Reference vs itself: branch tF1 (D1, D2, OM1, PDA) | 1 | D1 1.0000 (n 20), D2 1.0000 (n 13), OM1 1.0000 (n 18), PDA 1.0000 (n 19) |
| D1 ↔ D2 swapped | D1, D2 detected all, named 0; branch tF1 0; others 1 | D1 named 0/20, D2 named 0/13; tF1 D1 0.000, D2 0.000, OM1 1.000, PDA 1.000 |
| OM2 deleted | OM2 detected 0; presence agreement = 1 − OM2 prevalence (0.55) | detected 0/9; presence 0.55 |
| PDA relabelled RCA | PDA detected all, named 0 | detected 24/24, named 0 |
| collapse4(`to_1f`) vs `territory.to_four`, all 620 cases | 0 voxels outside "Other" | 0 voxels outside "Other"; 507 voxels in "Other" in 10 cases (Delta's 40 in 2) |

- `to_1f` on the 620: D3 from "Other" in 47 cases; later LAD-side pieces to LAD 2; LCx-side pieces to LCx 20; pieces not on one side 9, of which 8 touch neither side and become 255 (F-A3) and 1 touches both and goes to the nearest class. Identical to Delta v1's counts.

| Class | Cases with a branch ≥ 5 mm | Branches ≥ 5 mm | Cases with ≥ 2 | Extra pieces of 3–5 mm | Cases present at 3 mm, not 5 mm | Median / p10 branch length (mm) |
|---|---|---|---|---|---|---|
| D1 | 611 | 611 | 0 | 0 | 0 | 45 / 21 |
| D2 | 358 | 358 | 0 | 1 | 1 | 38 / 16 |
| D3 | 47 | 47 | 0 | 0 | 0 | 38 / 15 |
| OM1 | 540 | 540 | 0 | 0 | 0 | 44 / 16 |
| OM2 | 228 | 228 | 0 | 1 | 1 | 49 / 17 |
| Ramus | 149 | 149 | 0 | 0 | 0 | 42 / 22 |
| PDA | 607 | 675 | 65 | 1 | 1 | 49 / 20 |
| PLB | 609 | 618 | 9 | 2 | 1 | 56 / 19 |

Presence at 3 or 5 mm differs in at most one case per class on ImageCAS-X; 5 mm is kept for predictions.

### 3. Stage 2's Dice term and band (item 4)

- **Fidon et al.'s leaf-Dice** (arXiv:2107.03846 v2, Eq. 4, text re-read) pushes an unannotated class to 0 on
  set-valued voxels when its sums run over the batch. In nnU-Net's per-sample form (`batch_dice: false` for
  3d_fullres in the icx14 plans; smooth 1e-5) a class with no target on a patch has a gradient of 1e-7 per voxel at
  10 predicted voxels, against 0.018 with a 50-voxel target: inert.
- **The toy** (`dice_toy.py`; 5 seeds; band volumes from the 620):

| Dice term | Band | S Dice at 10 extended reads | 30 | 60 | Parent Dice at 10 |
|---|---|---|---|---|---|
| oracle | 0 mm | 0.73 ± 0.02 | 0.71 ± 0.02 | 0.72 ± 0.02 | 0.979 |
| naive | 0 mm | 0.00 ± 0.00 | 0.56 ± 0.16 | 0.69 ± 0.01 | 0.979 |
| none | 0 mm | 0.01 ± 0.01 | 0.03 ± 0.02 | 0.13 ± 0.04 | 0.966 |
| none | 8 mm | 0.04 ± 0.03 | 0.06 ± 0.03 | 0.23 ± 0.05 | 0.966 |
| none | 15 mm | 0.31 ± 0.16 | 0.38 ± 0.05 | 0.52 ± 0.04 | 0.968 |
| leaf | 0 mm | 0.32 ± 0.07 | 0.62 ± 0.10 | 0.69 ± 0.01 | 0.979 |
| leaf | 8 mm | 0.40 ± 0.10 | 0.69 ± 0.04 | 0.69 ± 0.02 | 0.979 |
| leaf | 15 mm | 0.62 ± 0.08 | 0.70 ± 0.04 | 0.70 ± 0.02 | 0.980 |
| leaf_batch | 0 mm | 0.38 ± 0.08 | 0.64 ± 0.06 | 0.67 ± 0.03 | 0.978 |
| leaf_batch | 8 mm | 0.46 ± 0.18 | 0.67 ± 0.03 | 0.67 ± 0.04 | 0.978 |
| leaf_batch | 15 mm | 0.57 ± 0.16 | 0.68 ± 0.03 | 0.69 ± 0.04 | 0.980 |
| leaf_skip | 0 mm | 0.39 ± 0.07 | 0.64 ± 0.08 | 0.69 ± 0.02 | 0.979 |
| leaf_skip | 8 mm | 0.49 ± 0.06 | 0.70 ± 0.04 | 0.70 ± 0.02 | 0.980 |
| leaf_skip | 15 mm | 0.60 ± 0.05 | 0.69 ± 0.04 | 0.70 ± 0.03 | 0.981 |
| marginal | 0 mm | 0.57 ± 0.05 | 0.65 ± 0.06 | 0.69 ± 0.02 | 0.978 |
| marginal | 8 mm | 0.33 ± 0.28 | 0.68 ± 0.04 | 0.69 ± 0.02 | 0.978 |
| marginal | 15 mm | 0.28 ± 0.34 | 0.70 ± 0.03 | 0.70 ± 0.02 | 0.979 |
| ignore | 0 mm | 0.32 ± 0.07 | 0.62 ± 0.09 | 0.69 ± 0.01 | 0.979 |
| ignore | 8 mm | 0.37 ± 0.09 | 0.68 ± 0.04 | 0.70 ± 0.02 | 0.962 |
| ignore | 15 mm | 0.58 ± 0.07 | 0.67 ± 0.06 | 0.70 ± 0.03 | 0.947 |

  Naive training (untraced = background) learns nothing at 10 extended reads. Leaf-Dice per sample is within noise of
  the best everywhere; marginal Dice collapses in some seeds with a band; ignore-for-Dice costs the parent
  (0.947 vs 0.980); batch Dice is no better and more variable.
- **The band on the 620:**

| Host | 8 mm: mm³ (median [p10, p90]) | × traced tree | 15 mm: mm³ | × traced tree |
|---|---|---|---|---|
| LAD + D1–D3 (septals, small D3) | 49,688 [37,283, 61,489] | 12 | 154,309 [117,865, 187,262] | 37 |
| RCA (RMA, SN, conus) | 32,705 [25,527, 39,804] | 8 | 108,234 [86,907, 129,094] | 26 |
| proximal RCA, 30 mm (SN, conus) | 18,658 [12,992, 23,081] | 4 | 65,772 [47,974, 77,471] | 15 |
| proximal LCx, 20 mm from the LM (SN, 20 %) | 8,342 [7,678, 9,356] | 2 | 34,033 [31,668, 36,701] | 8 |
| overlap LAD and RCA bands | 0 [0, 0] | 0 | 0 [0, 11] | 0 |
| union of all bands | 86,998 [72,694, 103,549] | 21 | 275,000 [230,682, 321,837] | 68 |

Traced tree: median 4,012 mm³ over 620 cases.

### 4. Scoring set for the untraced classes (item 6)

`untraced_yield.py`: D35 (35 patients, two reads) reaches 20 patients with a class only if it is visible in ≥ 70 % of
patients, and 30 only at 90 % with good readers. 70 patients would reach 30 at 50 % visibility; D35 plus the 150
sealed, at acceptance, would reach ≥ 47 at every prevalence in the grid.

### 5. Shi et al. (item 7)

Read in the arXiv v1 PDF text (§4): marginal loss, joint training 0.921 vs fully labelled only 0.874; pooling without
the marginal loss 0.874 → 0.900; marginal + exclusion 0.931 vs that pooling baseline 0.900. Table 3's Ψ^mc_F row
rCE+rDC, All = .874 is verbatim. Both round-1 quotations are real numbers from different comparisons.

### 6. Census of record (item 10)

| Trunk | Cases with a twig ≥ 3 mm | ≥ 5 mm | ≥ 10 mm | Twigs ≥ 5 mm |
|---|---|---|---|---|
| LAD | 17 (2.7 %) | 15 (2.4 %) | 13 (2.1 %) | 15 |
| LCx | 22 (3.5 %) | 21 (3.4 %) | 20 (3.2 %) | 22 |
| RCA | 44 (7.1 %) | 44 (7.1 %) | 44 (7.1 %) | 44 |

620 cases scored; 0 errors.

- LAD 15 (2.4 %) at ≥ 5 mm is the record. LCx includes the 20 OM3+ pieces mapped into the LCx by F-A3. The RCA
  count is an upper bound: its twigs have a median of 57 mm, which is trunk; the end rule fails where the RCA ends in
  a PDA or PLB.
- From the labels: any L-PDA or L-PLA **59** of 620 (left only 46, with an R-PDA/R-PLA too 13); right only 559; neither 2. L-PDA in 38, L-PLA in 54.


## What it changes

In [[Candidates/Janus 1-F/Crucible v2|Crucible v2]]:
- F-A6's B1 recall line becomes per-class (human recall − 0.10) and B2's naming line 0.80 (§1.3 there);
- `branch_score.py` is the scorer of record, frozen by its sha256 (§2);
- stage 2 keeps leaf-Dice, per sample, with `batch_dice: false` pinned (§4.1);
- the band is territory-specific, provisional, and re-measured on the first extended reads (§4.2);
- §10's numbers are the census of record for the 620.

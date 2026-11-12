---
tags: [plans, experiment, janus-1f, branches, partial-labels, imagecas-x, cpu, round1]
author: Atlas
track: 1-F
round: 1
updated: 2026-11-11
issue: christianGRogers/Asclepius#303
---

# J1F: ImageCAS-X gives branch types cleanly, and ordinals follow origin order

**Question.** What do ImageCAS-X's 14 classes give a model that must output D45's 18 classes (4 vessels and 14
branches)? Four things are measured:
- how often each branch appears;
- how thick it is;
- whether ImageCAS-X's ordinal names (D1/D2, OM1/OM2) follow a rule;
- where D3 sits inside "Other", and how PDA/PLA relate to dominance.

Alongside: what the cancelled 14-class run (icx14) learned, and whether a warm-started head can begin exactly at
Janus 0.

**Setup.** Everything is CPU and labels only; no CT. The code is in `experiments/Atlas/j1f/`.

- **Cases.**
  - `split.py` rebuilds the D45 split from ImageCAS-X's filelists and `trillium/sealed_test.json`.
  - D45's hash string is ambiguous: the case id "c0068" or ImageCAS-X's number "69". The two readings share 13 of 20
    locked open-36 cases.
  - The c-id reading equals track 1-L's locked 100 (sha256 `bbd9c687…d5895`).
  - Only the **613 cases that are training under both readings** were downloaded (`fetch_620.py`, from Zenodo
    10.5281/zenodo.21887809, by HTTP range).
  - No locked, sealed or quality-0 label was fetched or opened.
- **`census.py`**, per case and class:
  - presence, voxels and mm³;
  - diameter = 2 × the whole-tree Euclidean distance transform (mm), sampled on the class's skeleton voxels;
  - skeleton end points;
  - the 26-connected components of "Other" (≥ 20 voxels) and the classes each one touches;
  - the geodesic distance from the LM along the left tree to the first voxel of D1, D2, OM1 and OM2;
  - dominance from `Descriptors.xlsx`.
  - Summary: `summarise.py` → `census_summary.json`; rows in `census.jsonl`.
- **`ordinal_rule.py`.**
  - It builds the D45 reference from ImageCAS-X:
    - D3 = the most proximal LAD-side "Other" component;
    - further LAD-side "Other" → LAD;
    - LCx-side "Other" → LCx;
    - IM → Ramus;
    - R-/L-PDA → PDA and R-/L-PLA → PLB.
  - It then renames the D and OM types **by rule**: the union of each type is split into components, ordered by
    origin along the left tree, and named D1, D2, D3 (then LAD) and OM1, OM2 (then LCx).
  - It scores the rule against the reference with the pinned `src/segtrain/tf1.py` (sha256 `24441cf8…5254`;
    `CLASSES` set to 1–12 at run time; ostia from the reference). Rows are in `ordinal_rule.jsonl`.
- **`icx14_log.py`** parses every pseudo-Dice line of `trillium-results/icx14/job2/results/training_log_*.txt` →
  `icx14_log.json`.
- **`head_init_check.py`** → `head_init_check.out`.

## Results

### 1. icx14 learned no branch except R-PLA, and that one only from epoch 424

898 validation lines over epochs 0–455 (4 lines with a NaN class were dropped). Median epoch time: 181 s, with 15
outputs, on Trillium.

| Class | Cases (of 640) | Epochs > 0 | First > 0 | Max | Mean, last 50 |
|---|---|---|---|---|---|
| LM / LAD / LCx / RCA | 630 / 640 / 640 / 640 | 596 / 850 / 843 / 779 | 130 / 27 / 34 / 61 | 0.92 / 0.92 / 0.89 / 0.94 | 0.90 / 0.90 / 0.84 / 0.93 |
| D1, D2, OM1, OM2, IM, R-PDA, L-PDA, L-PLA, Other | 38–631 | **0** | — | 0 | 0 |
| R-PLA | 589 | 32 | **424** | 0.78 | 0.44 |

### 2. Frequency, size, calibre (613 cases, all with 0.5 mm slices)

| Class | Cases | Share of tree voxels | Median diameter (mm) | p10 | Median length (mm) |
|---|---|---|---|---|---|
| LM | 604 | 5.3 % | 3.00 | 2.13 | 9 |
| LAD | 613 | 22.1 % | 1.69 | 1.42 | 112 |
| LCx | 613 | 14.9 % | 1.70 | 1.39 | 70 |
| RCA | 613 | 31.4 % | 2.25 | 1.68 | 89 |
| D1 | 604 | 4.9 % | 1.27 | 1.00 | 35 |
| D2 | 355 | 2.2 % | 1.27 | 1.00 | 28 |
| OM1 | 534 | 4.5 % | 1.35 | 1.00 | 36 |
| OM2 | 228 | 1.8 % | 1.35 | 1.18 | 36 |
| IM | 148 | 1.1 % | 1.22 | 1.00 | 37 |
| R-PDA | 566 | 4.6 % | 1.23 | 1.00 | 47 |
| R-PLA | 559 | 6.2 % | 1.35 | 1.06 | 48 |
| L-PDA | 37 | 0.3 % | 1.28 | 1.00 | 38 |
| L-PLA | 54 | 0.3 % | 1.22 | 1.00 | 17 |
| Other | 73 | 0.5 % | 1.26 | 1.00 | 32 |

As types:

| Type | Cases (of 613) |
|---|---|
| D (D1 + D2 + LAD-side Other) | 604 |
| OM | 535 |
| Ramus | 148 |
| PDA | 601 |
| PLB | 604 |

**On calibre:**
- The 10th-percentile diameter of every branch class sits at 1.0 mm, the grid floor of this estimate. The thinnest
  labelled branches are about 2 voxels across at 0.5 mm.
- Septals, SN and conus are not labelled (§3), so their calibre is unmeasured.
- 63 cases have R-PDA in more than one component (dual PDAs or breaks).

### 3. ImageCAS-X draws only the branches it names

| Class | 1 end point | 2 | ≥ 3 |
|---|---|---|---|
| LAD | 490 (80 %) | 105 (17 %) | 18 (3 %) |
| RCA | 488 (80 %) | 108 (18 %) | 17 (3 %) |
| LCx | 529 (86 %) | 49 (8 %) | 5 (1 %) |

A class's proximal end joins its parent, so the distal tip is the one expected end point. An LAD with its septals
drawn, or an RCA with its conus, SN and acute marginals drawn, would have several more. So **septals, SN, conus and
RMA are background in ImageCAS-X.**

### 4. Ordinals follow origin order without exception

**Origin order.** Geodesic distance from the LM to each branch's first voxel. 9 cases have no LM label and are left
out.

| Pair | Cases with both | The lower ordinal starts first | Median gap |
|---|---|---|---|
| D1 vs D2 | 349 | **349 (100 %)** | 16.1 mm |
| OM1 vs OM2 | 222 | **222 (100 %)** | 16.3 mm |
| D2 without D1 / OM2 without OM1 | 0 / 0 | — | — |
| The first LAD-side "Other" (D3) vs D2 | 45 | **45 start distal to D2** | 15.8 mm (min 0.4) |

**The rule scored by tF1** (`ordinal_rule.py`, tF1 @ 1.5 mm per class, rule vs ImageCAS-X):

604 cases scored (9 without an LM label are skipped).

| Class | Cases | Mean tF1, rule vs ImageCAS-X | Cases < 1.0 | Cases < 0.9 | Class mask voxel-identical |
|---|---|---|---|---|---|
| D1 | 595 | 0.998 | 3 | 3 | 584 |
| D2 | 349 | 0.990 | 4 | 4 | 344 |
| D3 | 45 | 0.956 | 2 | 2 | 43 |
| OM1 | 525 | 0.997 | 4 | 4 | 520 |
| OM2 | 222 | 0.982 | 4 | 4 | 217 |
| LAD / LCx | 604 / 604 | 1.000 / 1.000 | 0 / 0 | 0 | 597 / 602 |
| **Ordinal macro** (mean over D1–D3, OM1–OM2 present) | 601 | **0.995** | | | |

How the rule and ImageCAS-X differ:
- 586 of 604 cases are voxel-identical in every class.
- In 4 cases (D) and 4 (OM), the type union does not split into one component per named branch: two branches touch,
  or one is broken.
- The other differences are specks under 20 voxels that the rule returns to the parent; tF1 does not see them.

### 5. "Other", D3, and dominance

**"Other" components:**

| Side | Components | Cases |
|---|---|---|
| LAD side only | 49 | 47 cases (7.7 %; 45 with one, 2 with two) |
| LCx side only | 20 | 20 cases |
| Both sides | 0 | — |
| Neither | 1 | — |

**Dominance, from `Descriptors.xlsx`:**

| Dominance | Cases | R-PDA | R-PLA | L-PDA | L-PLA | Any L-PDA/L-PLA |
|---|---|---|---|---|---|---|
| Right | 558 | 557 | 554 | 0 | 5 | 5 |
| Co-dominant | 21 | 9 | 5 | 6 | 18 | 19 |
| Left | 34 | 0 | 0 | 31 | 31 | 34 |

58 of 613 cases (9.5 %) carry a left-sided PDA or PLA. That is LCx territory under D25 and in Janus 0's labels.

### 6. A parent-copy head starts exactly at Janus 0

- Each new type output copies its parent's 1×1×1 weights and bias, with bias − log k for the k members of the group.
- On random logits and Janus 0-like weights, every group's summed probability equals the 5-output model's to
  2·10⁻¹⁵, in both the 10-output (phase 1) and 14-output (phase 2) heads.
- Decoding hierarchically (group by summed probability, then the type within it) changes 0 of 200 000 voxels and names
  no branch at init.
- A plain argmax moves 2.5 % (10 outputs) or 3.7 % (14 outputs) of these random voxels to another group. **1-F must
  decode hierarchically.**

## What it changes (for Janus 1-F)

- **A network can learn types, and a rule can assign ordinals.**
  - ImageCAS-X's D1/D2/D3 and OM1/OM2 follow origin order in every case measured.
  - Merging them into a type removes the confusable-sibling problem: types pool the positives, e.g. D in 98.5 % of
    cases against D2 in 57.9 % and D3 in 7.7 %.
  - The rule's remaining cost is the tF1 table in §4. It comes from branches that touch, or that split into several
    components.
- **D3 is recoverable from "Other"** in about 7.7 % of cases. That is too rare to evaluate on the locked 100 alone
  (about 8 cases).
- **ImageCAS-X background includes septals, SN, conus and RMA.** A model that later learns these from pool reads must
  treat ImageCAS-X background as the set {bg, S, SN, Conus, RMA} (marginal loss), not as one-hot background.
- **PDA/PLB:** ImageCAS-X names position and origin separately, so the D44 classes map cleanly
  (R-/L-PDA → PDA, R-/L-PLA → PLB). Only the four-class collapse needs a ruling: by origin (D25) or always RCA (#280's
  default). This is a lead question.
- **icx14's failure was not frequency, compute or memory.** D1, in 99 % of cases, never scored. It is what a
  warm-started, type-level head is meant to avoid.

Used by [[Atlas v1]] (track 1-F, `vault/Plans/Candidates/Janus 1-F/Atlas v1.md`).

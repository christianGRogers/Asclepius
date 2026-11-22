---
aliases: [Foxtrot j1f round 2]
tags: [plans, experiment, track-1-F, round2, janus1-f, D44, D45, D47, gates, scorer, partial-labels, imagecas-x]
author: Foxtrot
track: 1-F
round: 2
updated: 2026-11-22
issue: christianGRogers/Asclepius#303
---

# On the 620, human-level branches false-fail OM2's round-1 gate up to 45 percent of the time, leaf-Dice is the only Dice term that both learns a drawn septal and stops an intruder, and the origin collapse needs PDA and PLB grouped

## Question

Round 2 of track 1-F ([[Janus 1-F Round 1]] §5) asks for CPU evidence on six points. This note measures them on D45's
620 training labels:
1. how often F-A6's branch gates fail a model that is exactly as good as ImageCAS-X's second observer (item 1);
2. whether a frozen branch scorer does what its definitions say on real trees, and whether F-A4's collapse equals D25's
   (item 2);
3. which Dice term stage 2 should use, and how wide the background band should be (item 4);
4. what D35 can score for the six untraced classes (item 6);
5. why the round-1 twig censuses differ, and which to keep (item 10).

## Setup

- **Data:** the 620 training labels only, fetched by `experiments/Foxtrot/j1f/fetch_620.py` (which refuses anything
  else). `pass1.py` and `band.py` assert the 620's L-A1 pin (`1350cb1f…1152`) and refuse any other id. No locked-100,
  sealed, quality-0 or TotalSegmentator-twin label was opened. The locked-100 class counts are the ruling's (F-A7).
- **Code:** `experiments/Foxtrot/j1f_r2/`.
  - `labels_r2.py`: Delta v1's map with D47 Q1 = A and F-A3's ignore; the origin collapse with PDA and PLB grouped.
  - `branch_score.py`: the scorer (detection, naming, presence, branch tF1 on A1c's `tree_f1`).
  - `pass1.py`: census, collapse check and scorer identity on all 620; perturbations and tF1 on the 20 fit-check cases.
  - `recheck_collapse.py`: the collapse check after the grouping fix.
  - `gate_sim.py`: the human-level gate simulation.
  - `band.py`: background-band volumes and synthetic septals, on the 27 cases with id divisible by 20.
  - `dice_terms.py`: three Dice terms on scripted predictions, 10 cases.
  - `d35_yield.py`: binomial yields.
  - `summarise.py`: produces `results/summary.md`.
- **CPU only**, 4 cores. No GPU, no cluster.

## Results

### 1. The gates against a human-level model (`gate_sim.py`, `results/gate_sim.txt`)

These are false-fail rates of each class's B (B1 recall, B1 presence agreement, B2 naming) at the locked counts
(D1 98, D2 64, OM1 84, OM2 40, PDA 96, PLB 96). The human-level model disagrees on presence as often as ImageCAS-X
Table 1's two observers.

| Lines | Model | D1 | D2 | OM1 | OM2 | PDA | PLB | read (< 4 of 6) |
|---|---|---|---|---|---|---|---|---|
| as ruled | human, misses = naming | 0.00 | 0.08 | 0.02 | **0.45** | 0.00 | 0.01 | 0.001 |
| as ruled | human, misses = detection | 0.00 | 0.06 | 0.02 | 0.18 | 0.00 | 0.01 | 0.000 |
| capped at human − 0.10 | human, worst | 0.00 | 0.07 | 0.02 | 0.09 | 0.00 | 0.01 | 0.000 |
| capped | 2 × human misses | 0.07 | 0.57 | 0.22 | 0.80 | 0.00 | 0.11 | 0.14–0.18 |
| capped | 3 × human misses | 0.31 | 0.95 | 0.58 | 1.00 | 0.01 | 0.35 | 0.76–0.78 |

- OM2's observers disagree in 12.5 % of cases, which is 15.6 % of the 40 OM2 cases. That puts human-level OM2 naming
  at 0.844, under the 0.85 line.
- Capping changes three lines only: D2 naming 0.817, OM2 recall 0.744 and OM2 naming 0.744.
- A model calling a class present everywhere fails D2, OM1 and OM2 every time.

### 2. The scorer (`branch_score.py`, sha256 `902de0ae5d87a29ef68f0baee11c46de33ea51f77e8aa140359ac61de08d598b`)

- **Identity on all 620:** recall, naming and presence agreement are 1.000 for all eight branch classes. Branch tF1
  (A1c `tree_f1`, one ostium per piece) is 1.000 on the 20 fit-check cases.
- **Perturbations on the fit-check 20:**
  - swapping D1 and D2 keeps recall at 1 and drops naming and tF1 to 0;
  - deleting OM2 drops its recall to 0;
  - relabelling branches as their parent keeps recall at 1 and drops naming to 0;
  - thinning branches to their skeleton keeps everything at 1.
- **The collapse against `territory.to_four` (D25):**
  - With F-A4 read per class ("a PDA or PLB component goes to the vessel it touches most"), **4 879 left-PDA voxels in
    5 cases went to the RCA**. Those left PDAs touch only their left PLA.
  - With PDA and PLB grouped first, the mismatch is **40 voxels in 2 cases, all of them "Other"**. These are the 40
    Delta v1 found.

### 3. Stage 2's Dice term (`dice_terms.py`, 10 cases; mean Dice loss)

| Scenario (extended read without the complete flag) | leaf S1 | ignore S1 | merged S1 | leaf OM1 | ignore OM1 | merged OM1 |
|---|---|---|---|---|---|---|
| septal tube predicted S1 | 0.391 | 0.391 | 0.0007 | 0.673 | 0.601 | 0.673 |
| tube predicted LAD | 0.975 | 0.975 | 0.0008 | 0.673 | 0.601 | 0.673 |
| OM1 at 0.5 over the LAD group | 0.391 | 0.391 | 0.0029 | 0.882 | 0.601 | 0.882 |

- **Merged mass** cannot tell a septal from the LAD.
- **Ignore-for-Dice** cannot see OM1 intruding on the LAD group.
- **Leaf-Dice** does both.
- **No Dice term or CE stops S1 spreading over its parent** without D47 Q3's complete flag.
- **On ImageCAS-X samples** an absent class's per-sample Dice is flat. Its per-voxel gradient is 8 × 10⁻⁵ of the CE's.

### 4. The band (`band.py`, 27 cases; medians)

| w | released background (cm³) | share of a 256³ patch | share of background within 25 mm | 20 mm septal inside | 30 mm septal inside |
|---|---|---|---|---|---|
| 8 mm | 69 | 0.03 | 0.07 | 0.45 | 0.30 |
| 15 mm | 231 | 0.11 | 0.21 | 0.83 | 0.56 |
| 25 mm | 635 | 0.30 | 0.59 | 1.00 | 0.92 |

- Synthetic septals are straight 1 mm tubes from the LAD toward the nearest PDA voxel.
- Their lengths are a sweep: ImageCAS-X traced none, and I found no CT series that states septal length in mm.

### 5. D35 (`d35_yield.py`)

- With 35 patients, the report line (n ≥ 20) is reached with probability ≥ 0.96 if a class is drawn in ≥ 70 % of
  patients.
- The decide line (n ≥ 30) needs ≥ 90 % (P = 0.87).
- Reaching 30 with probability 0.8 needs 46 patients at 70 % and 66 at 50 %.

### 6. Census of record (`pass1.py`, all 620)

- **Trunk twigs** (Delta's method): LAD 5 cases at ≥ 5 mm (7 at 3 mm), LCx 1, RCA 2. Foxtrot's own method gives LAD 4.
- **Crucible's 13 and 9** include the 9 cases with no left main, where each ostium's stub is a pure end branch.
  Without them, Crucible's LAD count is 4.
- **Dominance by the PDA:** right 570, left 36, both 2, none 12. **59 cases have a left PDA or PLA.**
- **Stage-1 labels:** D3 47, D4 → LAD 2, LCx-side Other → LCx 20, Other → ignore 8 (467 voxels), nearest 1.

## What it changes

- **Item 1:** keep the ruled lines except **D2 naming 0.817** and **OM2 recall and naming 0.744**. The rule is "the
  ruled line, capped at the human level − 0.10". Keep "4 of 6".
- **Item 2:** freeze `branch_score.py` and `labels_r2.collapse4`, which groups PDA and PLB. Reading T must admit PDA
  and PLB inside Janus 0's LCx territory.
- **Item 4:**
  - use leaf-Dice;
  - band per parent region at 15 mm, widened by the first reads' 95th percentile, capped at 25 mm;
  - septal precision depends on reads with D47 Q3's "complete" flag;
  - stage 2's leakage gate is ≤ 0.02 per parent group.
- **Item 6:** on D35, septals are reported; SN, conus and RMA are counts only.
- **Item 10:** of record are Delta's twig method at 5 mm, label-derived dominance (59 left-posterior cases), and the
  stage-1 counts that F0-r2 checks on Fir.

Plan: [[Candidates/Janus 1-F/Foxtrot v2|Foxtrot v2]].

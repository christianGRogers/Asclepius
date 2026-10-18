---
tags: [plans, experiment, labels, territory, imagecas-x, D25, round-9]
author: Crucible
round: 9
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
---

# The territory collapse is clean, and a third of the LCx class is side branch

## Question

icx4 trains on ImageCAS-X's 14 classes collapsed to LM, LAD, LCx and RCA by `trillium/icx4/lib/territory.py` (D25).
Echo (#49) checked that the table matches D25 value by value. This note asks what the collapse does to the **labels
the model actually sees**:

1. Does the nearest-LAD/LCx rule for "Other" (D3/D4, OM3/OM4) give the same class as the vessel each Other piece
   hangs off?
2. Do any territories arrive in pieces, or touch a territory they should not?
3. How much of each territory is side branch? This decides whether ImageCAS-X's published per-class inter-observer
   Dice (trunk only) can stand in for a territory ceiling.
4. What is the class balance?

## Method

- `experiments/Crucible/r9_territory_audit.py` runs `territory.to_four` (the exact function icx4 imports) on all 800
  ImageCAS-X label maps (Zenodo 10.5281/zenodo.21887809, fetched with icx4's own `fetch_icx.py`).
- Per case it records:
  - class presence and volume;
  - the share of each territory that came from non-trunk ImageCAS-X classes;
  - 26-connected components per class (≥ 10 voxels);
  - voxel contacts LM–RCA, LAD–RCA and LCx–RCA;
  - for every connected Other piece, the class the rule assigns against the collapsed class of the voxels the piece
    touches (its parent in the tree, when it touches one).
- `r9_territory_summ.py` summarises it **without the 80 sealed ImageCAS-X test cases** (A14), so every number below
  is from the 720 non-sealed cases (train 560, val 80, open and development test 80). The per-case output is not
  committed. CPU only: 4 cores, about 35 min.

## Result

### 1. Other: the nearest-voxel rule agrees with the tree

| | Pieces | Voxels |
|---|---|---|
| Other present | 85 of 720 cases (train 65, val 11, test 9) | 0.44 % of all vessel voxels |
| Piece touches a named vessel and the rule gives that vessel's class | **82** | **107,176 (99.6 %)** |
| Piece touches the RCA, rule gives LAD (4) or LCx (3) | 7 | **8 in total** (1–2 voxels each) |
| Piece touches nothing (isolated) | 1 | 459 (assigned LAD) |
| Piece split between LAD and LCx by the rule | 2 | 3,416 |

- The 7 disagreements are 1–2-voxel fragments where a left-side Other label grazes the RCA. They match the LAD–RCA
  contacts (4 cases) and LCx–RCA contacts (3 cases) below, a median of 9–10 voxels each. They are negligible.
- The two split pieces are Other segments between an LAD branch and an LCx branch. Splitting them by distance is
  what D25 says to do ("the nearest LAD/LCx").
- **So icx4's mm-based rule is correct where it matters.** Echo's voxel-index variant (`segtrain.reads`, issue #56)
  could differ only on these few pieces. It is worth fixing for consistency, but it cannot move a training label in
  any measurable way.

### 2. Territories are whole

| | LM | LAD | LCx | RCA |
|---|---|---|---|---|
| Present (of 720) | **709** (11 without an LM: separate ostia) | 720 | 720 | 720 |
| Cases where the class has > 1 component of ≥ 10 voxels | 0 | 2 (2nd piece median 248 voxels) | 6 (median 1,075) | 0 |
| Share of vessel voxels | **5.2 %** | 29.3 % | 22.9 % | 42.5 % |
| Median volume | 99 mm³ | 573 mm³ | 424 mm³ | 805 mm³ |

- 708 of 720 trees have exactly two components (left and right), and 12 have three.
- No LM touches the RCA anywhere.
- The 8 cases with a territory in two pieces are gaps in ImageCAS-X's own lumen, not artefacts of the collapse (the
  collapse never removes a voxel). Under D3, tF1 forgives a gap of up to 1.5 mm in a *prediction*; a gap in the
  *reference* shortens the reference centreline instead. That affects 8 of 720 cases.

### 3. Side branches are a large part of each territory

Share of each territory's voxels that came from side-branch classes (not the trunk class of the same name):

| | LAD (D1, D2) | LCx (OM1, OM2, IM, L-PDA, L-PLA) | RCA (R-PDA, R-PLA) |
|---|---|---|---|
| Median | 0.245 | **0.352** | 0.248 |
| 90th percentile | 0.373 | **0.572** | 0.355 |

ImageCAS-X's inter-observer Dice (arXiv:2608.30404, Table 1) is **per trunk**: LM 91.9, LAD 92.3, LCx 84.8, RCA 95.3.
Its side branches agree less well: OM1 74.1, OM2 77.7, IM 80.6, L-PDA 75.1, L-PLA 70.9, D1 79.9, D2 82.9, R-PDA
82.6, R-PLA 83.6. A territory merges trunk and side branches, so its inter-observer Dice is neither the trunk figure
nor a voxel-weighted mean. Merging removes the trunk/branch boundary as a source of disagreement, but adds the
side branches' extent disagreement. **The published per-class numbers therefore cannot serve as a ceiling for our
classes**, least of all for the LCx, where the median case is one-third side branch and the 90th percentile more
than half. The only valid territory ceiling is an inter-read on territory labels, and ImageCAS-X's second reads are
not released (see [[Crucible - No sealed case will ever have two reads, so A10 needs a sealed share of the pool]]).

### 4. Class balance

LM is 5 % of vessel voxels and about 99 mm³ in the median case: the same size as a side branch. icx14's interim
check showed the network unlocking LM last (around epoch 200 of 446) while LAD and LCx unlocked at around epoch 50
([[icx14 - interim check after job 1 (446 epochs), side branches not yet learned]]). At 1000 epochs this was not a
problem for icx14's LM (val pseudo-Dice 0.91 at epoch 446). icx4's optional class-weighted CE
(`ce_class_weights.json`) is therefore **not** needed by default and stays off.

## What it changes

- **No label change.** icx4 trains on the labels as `territory.py` makes them. No case needs excluding for the
  collapse.
- **Comparisons with ImageCAS-X's published numbers must say "trunk vs territory"**, and Dice must never be read
  against Table 1 as a ceiling. For an external anchor, use ImageCAS-X's **merged-lumen** benchmark (Table 2:
  inter-observer 92.8, nnU-Net 89.8) for icx4's *whole-tree* Dice. That comparison is like for like: same images,
  same lumen convention, same test split. Use only the non-sealed half of the split.
- **The LCx is the class to watch.** It has the most side branch, the lowest trunk inter-observer Dice (84.8 ±
  19.8), the weakest published per-branch labelling (CPR-GCN F1 0.976, the lowest of the four; arXiv:2003.08560
  Table 3), and the weakest class in run 1 (decisive tF1 0.846). Atlas's guard of LCx tF1 below 0.83 → review
  carries over to icx4.

## Limits

- Connectivity is voxel 26-adjacency on the native grid. It does not test whether a side branch is anatomically
  attached to the right parent; ImageCAS-X's analysts decided that.
- The audit script reads every label map in the folder, so it also read the 80 sealed cases' **reference labels**
  (never a prediction). A first summary, run before the sealed filter was added, printed 2 sealed case ids among the
  9 cases with a 1–2-voxel Other fragment touching the RCA. Nothing else about those cases was looked at, every
  figure above excludes the sealed 80, and no per-case output is kept. The judge may weigh this; it reveals nothing
  about any model.

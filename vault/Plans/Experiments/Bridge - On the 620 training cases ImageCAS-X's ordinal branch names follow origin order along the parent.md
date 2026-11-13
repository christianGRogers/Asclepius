---
tags: [plans/experiment, bridge, janus-1f, branch-labelling, D44, D45, round1]
author: Bridge
track: Janus 1-F
round: 1
updated: 2026-11-11
issue: christianGRogers/Asclepius#303
---

# On the 620 training cases, ImageCAS-X's ordinal branch names follow origin order along the parent

## Question

D44's branch classes include ordinals: D1–D3, S1–S3 and OM1–OM2. Are ImageCAS-X's D1/D2 and OM1/OM2 simply the first and
second branch of their type along the parent? If so:
- a network only needs to segment the **type** (diagonal, marginal, septal);
- the ordinal is assigned by counting along the parent;
- ImageCAS-X's "Other" yields D3 labels.

## Setup

- **Cases:** the 620 Janus 1 training cases of D45 only.
  - `split620.py` rebuilds the split from `trillium/sealed_test.json` and ImageCAS-X's file lists.
  - `fetch620.py` downloads only those 620 label files from Zenodo (10.5281/zenodo.21887809).
  - No locked-100, sealed or quality-0 case is read.
- **Per case** (`census.py`, CPU, about 25 min on 4 cores):
  - each side-branch class and each connected component of "Other" is attached to the parent it touches most (26-connectivity);
  - its **origin** is the smallest geodesic distance, along the parent's own mask, from the parent's proximal end to a
    parent voxel touching the branch;
  - the proximal end is the LAD/LCx voxels touching the LM (or, with no LM, the voxels nearest the other left trunk).
- **Ordering:** D1 is "before" D2 when its origin is more than 1 mm proximal; a tie is within 1 mm.
- **Re-derivation** (`analyse.py`): the steps are
  1. pool D1, D2 and LAD-side "Other" into one diagonal type;
  2. sort by origin, with ties broken by the larger branch first;
  3. name them D1, D2, then Other;
  4. compare with ImageCAS-X's names.

  The same is done for OM1, OM2 and LCx-side "Other".

## Result (`experiments/Bridge/j1f_r1/census_summary.json`)

| Pair | Cases with both | Ordered | Tie | Reversed | No origin |
|---|---|---|---|---|---|
| D1 before D2 along the LAD | 358 | **356** | 0 | **0** | 2 |
| OM1 before OM2 along the LCx | 229 | **228** | 0 | **0** | 1 |

| Re-derived from type + origin order | Branches | Branch agreement | Voxel agreement | By reference name |
|---|---|---|---|---|
| Diagonals | 1017 | **0.998** | **0.9993** | D1 1.000 (610), D2 0.997 (357), Other 0.98 (50) |
| Marginals | 786 | **0.999** | **0.9993** | OM1 1.000 (539), OM2 1.000 (228), Other 0.95 (19) |

**"Other" holds a D3 in 48 of 620 cases (7.7 %) and a D4 in 2.** Of its 78 components:
- 50 leave the LAD side and 20 the LCx side;
- 7 are single stray voxels inside the RCA (label noise);
- 1 is detached.

## Reading

- **ImageCAS-X's ordinals are position.** Its protocol decides side branch vs continuation by course rather than size
  (Suppl. B), and its ordinals then follow origin order with no exception measured on 620 cases.
- So **D1/D2/D3 and OM1/OM2 are a deterministic function of (type, origin order)**, and so, by the same convention, are
  S1–S3.
- **D3 is not unlabelled.** It is the third diagonal by origin. ImageCAS-X traced it only when it was ≥ 1.8 mm or as
  large as D1/D2, so small D3s are background like any untraced branch.
- **Limits:**
  - this is the ceiling of the ordinal step on reference labels;
  - on predictions, a missed D1 turns D2 into D1, which a naming metric must score as an error of the segmentation;
  - nothing here says septal ordinals behave the same in pool reads, but the definition is the same.

## What it changes

Bridge v1 (Janus 1-F) segments **types** (DIAG, SEPT, OM, …) and names ordinals by a deterministic namer. This removes
the need for the network to count branches, which patches cannot always see whole. It pools each type's voxels and
gives D3 its training signal.

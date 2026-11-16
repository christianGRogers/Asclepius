---
tags: [plans/experiment, bridge, janus-1f, census, D44, D45, round1]
author: Bridge
track: Janus 1-F
round: 1
updated: 2026-11-11
issue: christianGRogers/Asclepius#303
---

# Census of ImageCAS-X's branch classes on the 620 Janus 1 training cases

## Question

How often does each ImageCAS-X class occur in D45's 620 training cases? How large and how thin is each, which parent
does each attach to, and what is the dominance mix? What did ImageCAS-X not trace at all?

## Setup

- `experiments/Bridge/j1f_r1/census.py` runs on the 620 training cases only (see
  [[Bridge - On the 620 training cases ImageCAS-X's ordinal branch names follow origin order along the parent]]
  for the split and fetch).
- Per class it measures:
  - volume and connected components;
  - skeleton length;
  - lumen diameter as twice the distance transform on the skeleton, on the label's own grid.
- `analyse.py` summarises the results.
- The protocol facts come from ImageCAS-X's paper (arXiv 2608.30404, Suppl. B), read 2026-11-11.

## Result

| Class | Cases | Median volume mm³ | Median length mm | Median diameter mm (median 10th pct) | Parent touched |
|---|---|---|---|---|---|
| LM | 611 | 98.6 | 7.7 | 3.00 (2.64) | |
| LAD | 620 | 428 | 111 | 1.68 (1.21) | |
| LCx | 620 | 280 | 68.5 | 1.67 (1.19) | |
| RCA | 620 | 598 | 87.5 | 2.25 (1.87) | |
| D1 | 611 | 82.9 | 34.9 | 1.27 (1.00) | LAD 610, LCx 1 |
| D2 | 359 | 68.2 | 28.0 | 1.27 (1.00) | LAD 359 |
| OM1 | 540 | 82.5 | 35.1 | 1.35 (1.00) | LCx 540 |
| OM2 | 229 | 91.8 | 35.9 | 1.35 (1.00) | LCx 229 |
| IM | 149 | 68.4 | 36.3 | 1.21 (1.00) | LCx 70, LAD 79 |
| R-PDA | 572 | 93.9 | 46.2 | 1.22 (1.00) | RCA 571 (63 cases in > 1 piece) |
| R-PLA | 565 | 114 | 47.7 | 1.35 (1.00) | RCA 555, none 10 |
| L-PDA | 38 | 80.6 | 35.8 | 1.31 (1.00) | LCx 36, none 2 |
| L-PLA | 54 | 34.2 | 16.1 | 1.21 (0.98) | LCx 54 |
| Other | 73 | 65.1 | 29.6 | 1.25 (1.00) | LAD side 50, LCx side 20, RCA 7 (single voxels), none 1 |

**Dominance** by ImageCAS-X's definitions, from the classes present:
- right 556 (89.7 %);
- left 46 (36 with an L-PDA, 10 with an L-PLA only);
- co-dominant 16;
- none labelled 2.

ImageCAS-X reports 91.1 / 5.1 / 3.8 % on all 800.

**Grid:** in-plane 0.29–0.45 mm, slice 0.5 mm.

**Not traced by ImageCAS-X (Suppl. B):**
- "Septal perforators, acute marginals and nodal arteries were not traced."
- Branches with a distal diameter < 1 mm, or an unclear connection, were not traced.
- At a side-branch bifurcation only the larger limb was traced (both if ≥ 1.8 mm).
- Conus is not part of the 18-segment model and is not mentioned. It is treated as untraced.

## Reading

- **D44's S1–S3, SN and RMA are background in every ImageCAS-X case, and conus almost surely is too.** These classes
  are worse than unlabelled: plain cross-entropy on ImageCAS-X would actively teach a model to erase them. A plan must
  either drop that background signal for them (a marginal, or ignore) or keep them out of the model until other labels
  exist.
- **The traced branches are thin but already in Janus 0's range.** Median lumen diameter is 1.2–1.35 mm, and the
  10th percentile is about 1.0 mm, about two voxels at 0.5 mm. Janus 0 learned them as parts of LAD, LCx and RCA (D25),
  so 0.5 mm is adequate for the branch types. No finer grid is proposed.
- **Left-sided posterior branches are rare but not negligible:** 38 L-PDA and 54 L-PLA cases. Every attached one leaves
  the LCx, so a namer can always tell the side from the parent it touches. The 2–10 detached pieces need a
  nearest-parent rule.
- **The ramus leaves the bifurcation:** it touches the LAD and the LCx about equally. Its D1b collapse to LCx is a
  convention, not a contact fact.
- **D2 is in 58 % of cases, OM2 in 37 % and the ramus in 24 %.** These are per-case detection problems, not only
  segmentation problems. ImageCAS-X's own inter-observer agreement on presence (Table 1: D2 89.4, OM2 87.5, IM 89.4) is
  the ceiling a model's detection agreement should be read against.

---
tags: [plans/experiment, bridge, janus-1f, census, D45, D47, round2]
author: Bridge
track: Janus 1-F
round: 2
updated: 2026-11-16
issue: christianGRogers/Asclepius#303
---

# On the 620, SegQueue's contact rule reproduces every ImageCAS-X side label, and an 8 mm stage-2 band releases 71 times the tree's volume

## Question

[[Janus 1-F Round 1]] §5 left three questions that ImageCAS-X's labels on the 620 training cases can answer on CPU:

1. **Item 2:** does SegQueue 0.20.0's D47 contact rule assign each PDA/PLB to the same parent as ImageCAS-X's own R-/L- side?
2. **Item 4:** how much background does a stage-2 label-set band release at 4, 8 and 15 mm?
3. **Item 10:** how many unnamed side twigs do the trunks carry? This is the census of record.

## Setup

- `experiments/Bridge/j1f_r2/census_r2.py` runs on D45's 620 training cases only. No locked-100, sealed or quality-0
  label was fetched. The split hash matches `1350cb1f…`.
- **Contact rule.** `segqueue14.labels.assign_contact_branches` is imported, not copied.
  - PDA = R-PDA ∪ L-PDA and PLB = R-PLA ∪ L-PLA.
  - Parents: RCA = {RCA} and LCx = {LCx, OM1, OM2, IM}.
  - Each 26-connected component's verdict is compared with the majority side of its voxels.
- **Bands.**
  - Background within d of the traced tree, split by the territory of the nearest tree voxel.
  - Also the host-restricted band: the LAD side, the RCA side and the first 30 mm of the LCx.
  - The LAD/RCA overlap of that band.
- **Twigs.** Per trunk, the skeleton minus its longest path; each remaining piece's length is its voxel count × the
  mean spacing.
- `summarise_r2.py` → `census_r2_summary.json`.

## Result

| Measure | Value on the 620 |
|---|---|
| Contact rule vs ImageCAS-X side | **1,296 of 1,296 components agree**. No case disagrees, and no fallback was used. PDA: R 638, L 38. PLB: R 565, L 55 |
| Traced tree, median | 1,951 mm³ |
| Band 4 / 8 / 15 mm, median background released | 42,400 / 138,700 / 427,500 mm³ = **21× / 71× / 218×** the tree |
| Host-restricted share of the band | 0.78 / 0.79 / 0.80 |
| LAD-side and RCA-side overlap | 8 mm: nonzero in 4 cases, at most 0.3 % of the host band. 15 mm: 122 cases, at most 2.3 % |
| Trunk twigs ≥ 3 / ≥ 5 mm (cases with any) | LAD 6 / 3, LCx 1 / 1, RCA 2 / 1. At most one per case |

## Interpretation

- **Contact and side give the same answer on the reference.** Two scorings agree on every case:
  - the prediction collapsed by contact, the function SegQueue runs;
  - the reference collapsed by side, the labels Janus 0 trained on.

  Any disagreement on the locked 100 will therefore come from the model, not from the two collapse rules.
- **The band is wider than the classes it serves, by two orders of magnitude.**
  - Restricting it to the host vessels removes only about 20 %.
  - LAD-side and RCA-side zones are disjoint at 8 mm. Territory-specific sets are therefore possible: septals near
    the LAD, SN/Conus/RMA near the RCA.
  - Bridge v2 §5 proposes those sets, with d set later from the reads.
- **Twigs are negligible.** No twig rule is needed in the converter or the scorer.

## Caveats

- The side of each component is ImageCAS-X's majority label. Mixed components would count once each, but none
  disagreed.
- The twig method is skeleton-based. Short spurs below 3 mm are skeleton noise and are not counted.

Used by [[Bridge v2]] (Janus 1-F, round 2) §3, §5.2 and §11.

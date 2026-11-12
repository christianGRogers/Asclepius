---
tags: [plans, experiment, track-1F, round-1, imagecas-x, partial-labels, D44, D45]
author: Crucible
track: Janus 1-F
round: 1
status: done
updated: 2026-11-11
issue: christianGRogers/Asclepius#303
---

# ImageCAS-X traced no septal, nodal or acute marginal branch, so its background is not a negative for six of 1-F's classes

## Question

Janus 1-F segments the four vessels plus D44's 14 branch classes. ImageCAS-X names nine of them, one of which (D3) is
only inside "Other". For the other six (S1–S3, SN, Conus, RMA), the question is where those vessels are in
ImageCAS-X's labels:
- hidden inside the parent class, so the LAD label would mean "LAD or septal";
- or not drawn at all, so they are background.

The answer decides the partial-label strategy. The census also measures, on the 620 D45 training cases:
- the class frequencies, volumes and calibre;
- how often D3 appears inside "Other";
- the size of the left-sided PDA/PLA question.

## Method

**Source protocol.** I read ImageCAS-X's annotation protocol at source (Bransby et al., arXiv:2608.30404, HTML v1,
§2 and Table 1). The relevant passages:
- "Septal perforators, acute marginals and nodal arteries were not traced."
- Side branches were not traced "where the diameter at the most distal point was <1 mm".
- "Additional diagonal (D) and obtuse marginal (OM) branches, such as D3, D4, OM3 and OM4, were labelled as 'Other'
  … if they were at least as large as the first or second branches or >1.8 mm in diameter at the most proximal end."
- The conus is not mentioned.

**Census.** `experiments/Crucible/j1f_r1/`.

1. `split.py` builds D45's split from id lists alone:
   - train 620 = train 560 + dev-44 + the 16 open-36 cases not locked;
   - locked 100 = val 80 + the 20 open-36 cases with the smallest sha256(`asclepius-janus1-locked100:` + `cNNNN`).
   - It asserts no overlap with the sealed 80 or the sealed quality-0 20.
2. `census.py` opens **only the 620 training cases'** label files (Zenodo 10.5281/zenodo.21887809, fetched with
   `trillium/icx4/lib/fetch_icx.py`). No CT, no locked, sealed or quality-0 case is read. Per case it records:
   - voxels and mm³ per class;
   - "Other" pieces (26-connected, ≥ 10 voxels) and which classes each touches. The **D family** is LAD, D1, D2; the
     **OM family** is LCx, OM1, OM2, IM, L-PDA, L-PLA;
   - the whole tree's skeleton (skimage), with each skeleton voxel's distance to background in mm as its radius, by
     class;
   - skan branches whose voxels are all one trunk class (LAD, LCx, RCA) and that end at a free endpoint, ≥ 5 mm. These
     are **unnamed side branches drawn in the lumen**. The trunk's own distal end is one of them, so one per class is
     subtracted.
3. `summarise.py` prints the tables; `reads_per_class.py` gives Wilson CIs for §7 of the plan.
4. Running time: CPU, 4 cores, about 2 h. The per-case JSONL is not committed (it is re-made by the script).

## Result (620 cases)

All label maps are 0.32–0.37 mm in-plane, 0.5 mm slices.

| ImageCAS-X class | Cases | Median mm³ where present | Median centreline (mm) | Median skeleton radius (mm) | Cases whose 10th-percentile radius < 0.5 mm |
|---|---|---|---|---|---|
| LM | 611 (98.5 %) | 99 | 10 | 1.50 | 0 % |
| LAD | 620 | 428 | 152 | 0.85 | 3 % |
| LCx | 620 | 280 | 96 | 0.85 | 6 % |
| D1 | 611 (98.5 %) | 83 | 46 | 0.64 | 25 % |
| D2 | 359 (57.9 %) | 68 | 39 | 0.64 | 31 % |
| OM1 | 540 (87.1 %) | 83 | 45 | 0.67 | 22 % |
| OM2 | 229 (36.9 %) | 92 | 49 | 0.67 | 23 % |
| IM | 149 (24.0 %) | 68 | 42 | 0.61 | 26 % |
| RCA | 620 | 597 | 118 | 1.12 | 1 % |
| R-PDA | 572 (92.3 %) | 94 | 54 | 0.61 | 25 % |
| R-PLA | 565 (91.1 %) | 114 | 61 | 0.67 | 27 % |
| L-PDA | 38 (6.1 %) | 81 | 48 | 0.65 | 29 % |
| L-PLA | 54 (8.7 %) | 34 | 24 | 0.61 | 56 % |
| Other | 66 (10.6 %) | 74 | 44 | 0.63 | 27 % |

**1. The trunk classes hide no branches.**

| Trunk class | Cases with an unnamed branch ≥ 5 mm | Share of the class centreline in such branches | Raw terminal branches per case |
|---|---|---|---|
| LAD | 13 (2.1 %) | 0.3 % | 0–2 |
| LCx | 9 (1.5 %) | 0.4 % | 0–2 |
| RCA | 3 (0.5 %) | 0.1 % | 0–2 |

- A traced septal system would give most LADs several such branches, and a traced conus/SN/RMA would give most RCAs
  one or more.
- So, as the protocol says, they are **not drawn**. The LAD label means "LAD", not "LAD or septal". **The voxels of
  S1–S3, SN, RMA (and, by the protocol's silence and this census, the conus) are background in ImageCAS-X.**

**2. D3 is a large "Other" piece off the LAD, and rare.**
- Other is present in 66 cases. Its 70 pieces split as:
  - 49 D-family;
  - 20 OM-family;
  - 1 touching neither.
- D-family pieces per case: 0 in 573 cases, 1 in 45, 2 in 2.
- **Every** D-family piece touches the LAD trunk itself (none hangs off D1 or D2 only), and every case with one also
  has a D2.
- So a traced D3 is a proximal-most D-family Other piece in **47 cases (7.6 %)**.
- A small D3 is untraced, so its absence in ImageCAS-X is not an absent label.

**3. Left-sided PDA/PLA.**
- L-PDA or L-PLA is present in **59 cases (9.5 %)** (L-PDA 38, L-PLA 54). 13 of these also have an R-PDA/R-PLA, so
  they are co-dominant by ImageCAS-X's naming.
- Where present, L-PDA + L-PLA are a median **0.117** (p90 0.210, max 0.431) of the D25 LCx territory.
- That is the share of a left-dominant LCx that #310's "PDA/PLB always to RCA" collapse would move into the RCA in a
  four-class pair score.
- 9.5 % matches CCTA population left dominance of 9 % (Gebhard et al., CONFIRM, EHJ-CVI 2015, DOI 10.1093/ehjci/jeu314).

**4. Calibre.**
- The traced side branches have median skeleton radius 0.61–0.67 mm. In a quarter to a third of the cases with a given
  branch, its 10th-percentile radius is below 0.5 mm (L-PLA: 56 %).
- At nnU-Net's 0.5 mm isotropic grid, ImageCAS-X's 1 mm stopping diameter is two voxels.
- The untraced classes (septals, nodal arteries) cannot be measured here. Anatomically they are no thicker than the
  traced side branches, so they will sit at or below this floor for most of their length.

## What it changes

1. **Partial labelling is in the background.**
   - A 1-F model trained on ImageCAS-X as drawn is taught that septals, SN, conus and RMA are background.
   - Ignoring the unknown *names* does not help: the trunk labels are already correct as they stand.
   - What helps is a **label set on the background** near the traced tree: {background, S1–S3, SN, Conus, RMA, D3}.
     That is Shi et al.'s marginal loss and Fidon et al.'s label-set loss. See Crucible v1 (1-F) §3.
2. **Stage A can be plain nnU-Net.**
   - With only the eight traced branch classes (D1, D2, D3, OM1, OM2, Ramus, PDA, PLB) plus the four vessels,
     ImageCAS-X's labels are complete for that class list (except small D3s).
   - The six untraced classes wait for extended pool reads.
3. **The four-class comparison with Janus 0 must drop untraced classes, not count them as FP.** ImageCAS-X never
   traced them, so a correct septal would be a false positive against it.
4. **Cross-track, for 1-L (#302).**
   - SegQueue's four-class instruction puts "every diagonal and septal" into the LAD (`src/segqueue14/labels.py`).
   - ImageCAS-X does not trace septals. A model trained on ImageCAS-X will therefore look short in the LAD against
     pool reads, and the LAD read will look long against the model.
   - This is an extent effect of the same kind as Crucible v11's seed anchoring, in the opposite direction. It is
     reported, not decided here.
5. **L1.** Left-sided PDA/PLA are 9.5 % of cases and a median 12 % of their LCx. Collapsing PDA/PLB always to RCA
   misplaces that much in a left-dominant extended read's four-class score.

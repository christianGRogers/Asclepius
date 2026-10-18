---
tags: [plans, experiment, literature, external-validation, coronary, icx4, round9]
author: Foxtrot
round: 9
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
---

# No published model labels LM, LAD, LCx and RCA on ImageCAS-X, so icx4 is judged against binary benchmarks and the human ceiling

## Question

Round 9 asks each plan to check its robustness against outside evidence (#48, item 3). For a four-class
(LM, LAD, LCx, RCA) model trained on ImageCAS-X with nnU-Net ResEnc:

1. What published per-branch coronary results exist, and are any comparable with icx4 or run 1?
2. Which outside benchmarks can icx4's first Fir result be read against, and how?
3. What does the literature say icx4 will lose on scans from other centres?

This note updates [[Foxtrot - Nothing published by October 2026 beats a well-configured nnU-Net on per-branch coronary or vessel labelling]]
(Round 6). That note's conclusions on architecture, foundation models and pretraining stand. It also
corrects three citations held elsewhere in the vault (§4).

## Method

A literature search on 2026-10-18 (arXiv, PMC, publisher pages, GitHub, Crossref, Zenodo API). Every
number below was read in the source text. The full verification log, with the table or figure for each
number and the items that could **not** be verified, is `experiments/Foxtrot/literature_r9_verified.md`.
A sub-agent did the first pass; I re-read MAGIC's Table B4 in the arXiv PDF myself (lines quoted below).

## Result

### 1. Per-branch results that exist

| Source | Model | Metric | Classes | Test | LM | LAD | LCx | RCA |
|---|---|---|---|---|---|---|---|---|
| ImageCAS-X inter-observer, Table 1 (Bransby et al., arXiv:2608.30404, preprint) | two human analysts | voxel DSC | 14 segments; trunk rows shown | 160 ImageCAS-X test | 91.9 | 92.3 | 84.8 | 95.3 |
| MAGIC, Table B4 (Summerfield et al., arXiv:2506.10797, preprint) | nnU-Net-based multi-decoder | voxel DSC | LMCA / LADA / LCx / RCA (radiotherapy contours) | 10 CCTA, 1 centre | 0.73 | 0.80 | 0.67 | 0.86 |
| CPR-GCN, Table 3 (Yang et al., CVPR 2020, arXiv:2003.08560) | graph net | centreline-segment F1 | trunks; side branches separate | 5-fold CV, 511 private | 0.989 | 0.988 | 0.976 | 0.990 |
| LWT-ARTERY-LABEL, Table 2 (Zhang et al., arXiv:2508.06874, preprint) | net + rules | centreline-segment F1 % | 13 classes | GeoCAD 70 (internal) / orCaScore 72 (external) | 96.9 / 100 | 94.8 / 100 | 91.9 / 100 | 97.6 / 100 |
| TopoLab, Table 1 (Zhang et al., MICCAI 2023, arXiv:2307.11959) | connection classifier | weighted centreline F1 | 14 classes | orCaScore 72, 5-fold | weighted F1 87.2 (per class only in the supplement, not read) | | | |

- **No published model reports per-territory or per-segment accuracy on ImageCAS-X.** ImageCAS-X's
  model results (its Table 2) are binary lumen only. icx4 would be the first four-class result on this
  dataset, so there is no like-for-like published comparator.
- The only learned voxel-level LM/LAD/LCx/RCA Dice on CCTA I could find is MAGIC's: 10 test cases, one
  centre, radiotherapy-style contours. I read it myself (`arXiv:2506.10797`, Table B4, CCTA: "LMCA
  0.73 ± 0.07 … LADA 0.80 ± 0.06"). It is too small and too different in convention to set a target.
- The centreline-labelling papers score **naming** on given centrelines, not segmentation. Their trunk F1
  of 0.92–1.00 says that naming the four trunks is easy once the tree is found. This agrees with our own
  finding that naming errors are one decision per tree and rare ([[Bridge - Naming is one decision per tree, and half of a patch's LAD voxels cannot see it]]).
- **Every source puts the LCx last** among the four: ImageCAS-X inter-observer 84.8, MAGIC 0.67, CPR-GCN
  and LWT trunk F1. Run 1 also had the LCx last (decisive tF1 0.846, [[Round 8]]). So a weak LCx in icx4 is
  the expected shape. It is not by itself a sign of a bug.

### 2. Benchmarks icx4 can be read against now

**(a) Binary lumen, the same cohort and nearly the same cases.** ImageCAS-X Table 2 scores binary-lumen
models on the 160 ImageCAS-X test scans, the same cases icx4 holds out:

| Model (ImageCAS-X Table 2) | DSC % | HD95 mm | β err | clDice |
|---|---|---|---|---|
| TotalSegmentator (zero-shot) | 70.5 ± 6.2 | 19.59 | 4.6 | 76.0 |
| nnU-Net (default planner) | 89.8 ± 3.2 | 7.08 | 5.6 | 92.3 |
| nnU-Net + clDice | 90.0 ± 3.5 | 9.70 | 8.0 | 91.7 |
| CAS-Net (best model) | 91.2 ± 2.8 | 2.99 | 1.9 | 93.3 |
| Inter-observer | 92.8 ± 3.1 | 2.46 | 0.4 | 95.4 |
| Original ImageCAS labels vs ImageCAS-X | 41.8 ± 6.7 | 16.15 | 7.0 | 78.2 |

icx4's `score.py` already reports "whole-tree Dice (any vessel vs any vessel)". That is the same quantity,
against the same reference (ImageCAS-X), on a subset of the same 160 cases. After #55, only the 80 open
cases (open-36 + dev-44) will be scored. The comparison is therefore not exact: 80 of the 160 cases, and a
model trained with four classes rather than one. With a per-case SD of about 3.2 points, the 95 % CI half-width on 80 cases
is about ±0.7 points.

**(b) The human ceiling per class.** ImageCAS-X's inter-observer rows for LM, LAD, LCx and RCA are
**trunk** segments: the LAD row excludes D1 and D2. A four-class territory LAD includes them. So these
rows are not the four-class ceiling, and icx14's trunk Dice is not either (Echo, #49 item 3). The
four-class ceiling estimate is in
[[Foxtrot - On ImageCAS-X the four-class human agreement is at least about 92 LM, 89 LAD, 82 LCx and 92 RCA Dice]].

**(c) What is not comparable.**
- **Run 1** (decisive macro tF1 0.896) was trained and scored on the original ImageCAS mask, split by
  projected names (D0). ImageCAS-X and the original labels agree at only 41.8 DSC (Table 2 above), and a
  perfect segmentation in the wrong convention loses 0.19 tF1
  ([[Crucible - A perfect segmentation in the wrong lumen convention loses 0.19 tree-F1]]). Run 1's
  numbers are history, not a baseline for icx4.
- **icx14** pseudo-Dice (LM 0.90, LAD 0.90, LCx 0.86, RCA 0.93 at epoch 455) is trunk-only, patch-level and
  on val during training. It is close to the human trunk agreement above (91.9 / 92.3 / 84.8 / 95.3), which
  suggests the recipe can reach human trunk agreement on this cohort. It is indicative only.
- **TotalSegmentator's coronary output** is one binary class, so it cannot be a per-branch baseline. Its
  training data are not stated (only `Dataset509_coronary_arteries_cm_nativ_400subj_SKELETON`), so
  contamination on ImageCAS cannot be ruled out. Its one published number is the zero-shot 70.5 above.
  It needs a non-commercial licence.

### 3. Cross-centre performance

| Train → test | Task | Internal | External | Drop | Source |
|---|---|---|---|---|---|
| ImageCAS → ASOCA (zero-shot) | binary lumen | 0.831 | 0.767 ± 0.056 | 0.064 | Seg2RefineNet, Sci Rep 2025, doi:10.1038/s41598-025-24953-1, Table 3 |
| ASOCA → GeoCAD | binary lumen | ≈ 0.86–0.90 | ≈ 0.79–0.82 | ≈ 0.04–0.08 | Zhang et al., JIIM 2025, doi:10.1007/s10278-025-01677-2, Table 4 |
| Cleveland → Mackay (Taipei) | binary major coronaries (nnU-Net) | 0.794 | 0.741 | 0.053 | Kim et al., JMI 2025, doi:10.1117/1.JMI.12.1.016002, Table 1 |
| GeoCAD → orCaScore | centreline trunk naming F1 | 0.92–0.98 | 1.00 | none | LWT-ARTERY-LABEL, Table 2 |

- **Segmentation drops about 5–8 Dice points across centres. Trunk naming does not drop.** No published
  per-branch voxel model has been tested externally.
- The drop is driven mostly by acquisition (contrast enhancement r = 0.41, edge sharpness r = 0.24). It is
  smallest in heavily calcified cases ([[External validation and cross-dataset generalisation for coronary segmentation]]).
- ImageCAS-X is one Siemens dual-source scanner at one hospital, and 91 % of its cases are right-dominant
  (ImageCAS-X paper). So icx4's open-test numbers are an **internal** estimate. The 675 pooled volumes
  that SegQueue14 serves (D23) are other scanners and centres. Their team reads are this project's first
  per-branch external test.
- Public external sets: **ASOCA** (40 labelled, binary lumen, CC BY 4.0, UK Data Service registration with
  ethics evidence). Its top challenge Dice is 0.87 ± 0.04 (CMIG 2022, Table 1), and its inter-annotator
  85.6 % is each annotator against the majority vote. **orCaScore + TopoLab's labels**: 72 CCTA with
  centreline branch names (JSON). The images come through the orCaScore organisers, whose registration
  closed in August 2025. **CAT08**: no current download found.

### 4. Corrections to citations elsewhere in the vault

1. [[External validation and cross-dataset generalisation for coronary segmentation]] describes Kim et al.
   2025 as a "3-class (LAD/LCx/RCA)" result. Its 0.794 / 0.741 is a **single overall Dice** (Table 1,
   nnU-Net). The LAD/LCx/RCA split is a geometric post-processing step, and the paper reports no
   per-vessel network Dice.
2. The same note's ASOCA → GeoCAD row is from Zhang et al. JIIM 2025, which **trains on ASOCA**; it is not
   an ImageCAS-trained model.
3. "TreeLab-Net" is Wu D et al., IJCARS 2019;14:271–280 (doi:10.1007/s11548-018-1884-6), not a 2023 paper.

The vault research notes are not mine to edit in this round. These corrections are recorded here for the
judge.

## What it implies

1. **The deciding metric stays tF1** on the open ImageCAS-X test cases (#54, #55). The literature offers no
   per-territory benchmark that could replace it.
2. **Two outside reads come with the first Fir result at no GPU cost:**
   - whole-tree Dice against ImageCAS-X Table 2 (nnU-Net 89.8, CAS-Net 91.2, humans 92.8);
   - per-class Dice against the four-class ceiling estimate.
3. **External validity is unmeasured until team reads on pooled volumes exist.** The plan should say so,
   pre-register the expected drop (≈ 5–8 Dice points, binary), and score the first double-read pooled
   cases per class.
4. A weak LCx is expected (every source); a weak LM by Dice is expected too (short, noisy). Neither is a
   red flag alone; LCx tF1 is already guarded (Round 8).

## Limits

- Several sources are preprints (ImageCAS-X, MAGIC, LWT-ARTERY-LABEL).
- The search is not exhaustive. TopoLab's per-class supplement, Hampe et al. (SPIE 2021) and CAT08's
  original paper body were not read.
- Kim et al.'s tables were read through a quoting web fetch, because PMC blocks direct downloads.

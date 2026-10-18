---
tags: [plans, experiment, round9, tree-f1, ostium, a1, a1c, imagecas-x, four-class, dice]
author: Delta
round: 9
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
---

# On ImageCAS-X references tree-F1 needs no CT, because the released start points are the ostia, and Dice cannot see a proximal cut

## Question

icx4 trains a four-class model on ImageCAS-X collapsed by territory (D8, D25). Its own scorer (`trillium/icx4/lib/score.py`) reports **Dice only**, and the deciding tF1 needs an A1 ostium from a TotalSegmentator aorta, i.e. a CT (A1a). Three questions:

- **Q1.** Is the collapsed ImageCAS-X reference fit for the pinned tF1? Does it have centreline-less classes (A1c), pieces, absent LMs?
- **Q2.** ImageCAS-X releases centrelines with a `start_points` attribute. Can those replace the TotalSegmentator aorta as the A1 ostium? And how wrong is the CT-free "thick" rule they would replace?
- **Q3.** On this reference, does a break that tF1 is built to see stay invisible to Dice?

## Setup

**Data.**
- ImageCAS-X segmentations and centreline VTKs from the Zenodo zip (10.5281/zenodo.21887809, CC BY 4.0), fetched by HTTP range requests with `experiments/Delta/r9_fetch.py`.
- **The 80 A14 sealed test cases were never downloaded.** 720 cases were used: train 560, val 80, and the 80 non-sealed test cases.
- Case c(id − 1), as in icx4.

**Labels.** Collapsed with icx4's own `trillium/icx4/lib/territory.py`, so the references are exactly icx4's training and scoring targets.

**Metric.** `src/segtrain/tf1.py` at the pinned A1c hash `24441cf8…5254`, checked at start. The decisive defaults: 1.5 mm tolerance, fallback centreline.

**Code.**
- `experiments/Delta/r9_icx4_reference.py` (per case, one JSON line) and `summarise_r9.py`;
- `r9_vtkcl.py` (VTK reader) and `r9_export_ostia.py` (start points, and the check against a label rule);
- `r9_pieces.py` (what a second piece is).

CPU only, about 1.5 h on 3 cores. The per-case output is `experiments/Delta/r9_results.jsonl`, and `r9_summary.txt` holds the `summarise_r9.py` output that the tables below quote.

**Ostium from start points.** Each start point becomes a 1 mm ball, passed to `find_ostia` as its `aorta` argument. A1's rule of record ("the reference centreline voxel nearest the aorta, if within 5 mm") then picks the centreline voxel nearest the start point. Same code, same hash.
- ImageCAS-X defines the start points in "Postprocessing" (arXiv:2608.30404v1): centreline vertices "with a degree of 1 lying within 5 mm of the aorta", the aorta being TotalSegmentator's heart-chambers model. So they are A1's own construction, made by the dataset's authors on its own reference.
- In the VTKs they are LPS world mm. 100 % of the centreline points of the first cases fall inside the mask with matching labels once x and y are negated for nibabel's RAS.

**Q3's cut.** Every reference voxel within 2.5 mm of one point is removed, leaving a gap of about 5 mm (> D3's 1.5 mm). The point lies along the released centreline, 3 mm downstream of the left start point (the proximal LM) and 15 mm downstream of the right one (the proximal RCA). The cut reference is the "prediction". Scored on the 80 val cases only, because three tF1 calls cost about 45 s of CPU per case.

## Results

### Q1: the reference (720 cases)

| | Count |
|---|---|
| LM present | 709 (11 have separate LAD and LCx ostia; D13 makes LM optional) |
| Classes with voxels but **no centreline** (A1c fallback needed) | **0** (it was 7 of 143 on the thick proxy) |
| LM centreline < 3 mm | 20 (median 9.3 mm, p10 4.4 mm) |
| Tree components 2 / 3 | 707 / 13 (11 are the LM-less cases, whose left tree is two trees; 2 have a detached speck or "Other" piece) |
| Cases with ImageCAS-X "Other" voxels | 85 |
| A class in > 1 piece | 27 cases: **6 are the ramus** (IM → LCx by D1b, 637–2654 voxels), which leaves the LM and not the LCx, so the LCx class has two pieces joined through the LM. **2 are "Other"** pieces given to the LAD by nearest-voxel assignment but not touching it (459 and 37 voxels). **19 are 1–4 voxel specks** |

None of these affects tF1's rooting, which is per tree component, not per class. A ramus named LCx is rooted through the LM.

### Q2: ostia (720 cases)

**Start points vs a label rule.** The label rule is the free end of the LM line (left) and of the RCA line (right).
- It gives the same vertex as the released start point in **709 of 709** left and **720 of 720** right ostia (0.0 mm).
- The 11 LM-less cases have **two** left start points, LAD and LCx, which the label rule cannot give. Start points cover them.

**Start points vs our skeleton.** The reference centreline passes through them:

| Side | Median | p95 | Max |
|---|---|---|---|
| Left | 0.35 mm | 1.35 mm | 4.73 mm |
| Right | 0.00 mm | 0.71 mm | 2.01 mm |

ImageCAS-X regenerated its centrelines with the same Lee skeletonisation (arXiv:2608.30404, "Postprocessing").

**The CT-free "thick" rule** (A1's cross-check, and the only ostium available without a CT) against the start points:

| Side | Median | > 2 mm | > 5 mm |
|---|---|---|---|
| Left | 0.56 mm | 40 | **0** |
| Right | 0.38 mm | 36 | **29 (4.0 %)**, 5 of them in val. Median miss 30 mm (5.6–41.3): it picks a distal RCA end as "thickest" |

**Flags.**
- Under A1 as written with start points as the aorta, **38 cases** have a flagged tree, almost all because the thick rule disagrees.
- With the P2 flag rule (flag only when the ostium of record is not within 2 mm of a start point), **0 cases** would be flagged once the LM-less cases use their two start points. With the label rule only, 11 cases stay flagged, all of them LM-less.

**Context from GPU results already on file.** atlas2 measured the TotalSegmentator-aorta A1 ostium of run 1's thick references against these start points on the 80 val cases (`trillium-results/round6/atlas2/results/per_case_run1.json`, `to_icx_start_mm`):
- left: median 1.9 mm, 71 of 80 within 5 mm;
- right: median 2.1 mm, 72 of 80 within 5 mm;
- 12 of the 17 beyond 5 mm were A1-flagged trees on the thick mask.

That is a different reference, so it bounds rather than measures the agreement on ImageCAS-X. Delta v9 §2.4 step 2 measures it on icx4's own references.

### Q3: a proximal cut (80 val cases)

| Class | Dice of the cut "prediction", median (min) | tF1, start-point ostia, median (max) | tF1, thick ostia, median (max) |
|---|---|---|---|
| LM | 0.786 (0.442) | 0.192 (0.857) | 0.192 (0.857) |
| LAD | **1.000** (0.986) | **0.000** (1.000) | 0.000 (1.000) |
| LCx | **1.000** (0.984) | **0.000** (1.000) | 0.000 (1.000) |
| RCA | 0.982 (0.891) | 0.128 (0.992) | 0.129 (0.992) |
| Whole tree | 0.982 (0.972) | macro 0.086 | macro 0.086 |

- **In 140 of 160 LAD/LCx vessels, Dice is ≥ 0.95 while tF1 is < 0.5.** The cut removes no LAD or LCx voxel. In the other 11 cases (20 vessels) the synthetic cut did not disconnect anything: 2 are LM-less, and in the 9 others the left tree is still one piece after the cut (checked on c0038, c0311 and c0744; the lumen around the 2.5 mm ball still joins it). With no break to see, tF1 correctly stays at 1.0.
- **The ostium choice changes the verdict in 5 of 80 cases** (|Δ macro| > 0.05: c0106, c0133, c0186, c0514, c0899). With the thick rule's distal "ostium", a proximal RCA cut goes unseen: in c0106, RCA tF1 is 0.96 with thick ostia against 0.10 with start points.
- **Sanity:** the uncut reference scored against itself gives tF1 = 1.000 in 80 of 80.

Clinical reading: a gap in the proximal LM disconnects the whole left tree from the aorta. Dice scores it 0.98; tF1 scores it as the loss of the left tree. clDice would also miss it: no LAD or LCx voxel or centreline point is removed, so their clDice stays at 1.

## What it changes

1. **The A1c fallback is not needed on ImageCAS-X references** (0 of 720). It stays the default, because team reads (thick or redrawn outlines) may still need it.
2. **On ImageCAS-X references, every tF1 can be decisive without a CT.** This is Delta v9's P2: start points as the "aorta", the same code and hash, and A1b flags only where no start point is within 2 mm. It is a judge's decision. Validation on Fir costs ≤ 1.5 GPU-h (TotalSegmentator aortas for the 160 non-sealed val/test cases, paired). Team reads keep A1 as written.
3. **Without a CT and without start points, tF1 is not safe to decide on**: the thick rule is silently wrong on 4 % of right ostia, and that changes the verdict in 6 % of val cases. This confirms A1a for ImageCAS-X references too.
4. **icx4's Dice-only scorer cannot judge the model** (Delta v9's P1). `experiments/Delta/r9_fir/score_tf1.py` scores icx4's predictions with the pinned tF1, P2 ostia, A1b flags under both rules, the A15 FP gate, and Dice for comparison only. It refuses sealed cases and any other `tf1.py` hash. It was self-tested here on fake predictions (references, some with a 4 mm ostial hole, and fake aortas): intact predictions score 1.0; the hole sets LM, LAD and LCx tF1 to 0 while LAD and LCx Dice stay 1.0; a sealed case is refused.

## Limits

- The cut is synthetic. It shows what each metric *can* see, not how often icx4 makes such errors. Step 3 on Fir reports the real (case, class) pairs with Dice ≥ 0.85 and tF1 < 0.5.
- The start points depend on ImageCAS-X's TotalSegmentator heart-chambers aorta, a different model from the `total` aorta of A1's producer. Step 2 measures the difference.
- The per-case statistics use the label rule for ostia. The exported JSON, which the Fir scorer uses, uses the released start points. The two are identical wherever an LM exists.
- I inspected per-case output of the 720 non-sealed references only: references and centrelines, never a model prediction. These cases are already outside the sealed set, so the A14 seal is unaffected. The 80 open test cases should be treated as Delta development cases for the ostium rule.

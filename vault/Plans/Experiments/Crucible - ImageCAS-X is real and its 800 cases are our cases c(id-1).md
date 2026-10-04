---
tags: [plans, experiment, datasets, imagecas-x, verification]
author: Crucible
round: 1
updated: 2026-10-04
---

# ImageCAS-X is real, and its 800 per-branch label maps are our cases `c{id-1}`

## Question

The vault (and [[Training plan]]) asserts that ImageCAS-X re-annotated 800 of
the ImageCAS cases into 14 per-segment classes under CC BY 4.0. Does it exist,
what does it contain, can we get the labels inside the disk budget, and which of
our 1000 Girder cases (`c0000..c0999`, "ordered by upload time; ImageCAS names
are not stored in Girder") do its labels belong to?

## Method

- Zenodo REST API `GET /api/records/21887809` and `/files`; arXiv export API for
  `2608.30404`; full preprint PDF read (`pdftotext`).
- Labels fetched **without downloading the 1.44 GB zip**: the zip's central
  directory (HTTP range read) shows `filelist/`, `Descriptors.xlsx` and all 800
  `segmentations/*.coronary.nii.gz` are contiguous in the last 13.5 MB, so one
  range request + CRC-checked parse of the local headers extracts them
  (`experiments/Crucible/fetch_icx.py`). 18 MB on disk.
- Case matching: header signature (shape + affine, tolerance 0.01 mm) of every
  ICX label vs all 1000 Girder masks (`experiments/Crucible/our_headers.py`,
  `match_icx.py`, `compare_icx.py` re-checks every pair with `np.allclose`).
- Independent check: the two SegQueue test submissions in `data/submissions/`
  carry ImageCAS names (`imagecas_0002`, `imagecas_0005`); compared to our
  masks after converting NRRD (LPS, z flipped) to our grid.

## Result

**The dataset is real and as described.** Zenodo 10.5281/zenodo.21887809,
"ImageCAS-X", Bransby KM & Paulsen RR (DTU), published 2026-08-11, open access,
**CC BY 4.0**; files `ImageCAS-X_dataset.zip` (1,443,579,008 B: centerlines,
surfaces, segmentations, file lists, descriptors) and `pretrained_weights.zip`
(1.64 GB, weights for 6 benchmarked methods). Preprint arXiv:2608.30404v1
(31 Aug 2026), Bransby, Øksnebjerg, Kjær, Kirkeby, El Youssef, Jiménez, …,
"ImageCAS-X: a dataset and benchmark for coronary artery segmentation and
centerline extraction in coronary CT angiography", under review.

What the labels are (paper + files):

| Item | Value |
|---|---|
| Labelled cases | 800 (train 560 / val 80 / test 160 per `filelist/`); 200 excluded as non-diagnostic (motion 114, step 76, contrast 7, noise 1, FOV 1, corrupt 1) |
| Excluded = Image Quality 0 | `Descriptors.xlsx`: all 200 excluded cases are grade 0; no included case is grade 0 |
| Label file | `uint8` NIfTI on the **original ImageCAS grid** (512×512×z, same affine as our masks), values 0–14 |
| Classes (Suppl. Table 4) | 1 LM, 2 LAD, 3 LCx, 4 D1, 5 D2, 6 OM1, 7 OM2, 8 IM (ramus), 9 RCA, 10 R-PDA, 11 R-PLA, 12 L-PDA, 13 L-PLA, 14 Other (D3/D4/OM3/OM4) |
| Protocol | 4 trained analysts; auto centerlines corrected, cMPR U-Net lumen proposal then axial-slice manual correction, every case reviewed by lead analyst; 200 h centerline + 270 h lumen correction (≈35 min/case) |
| Main-vessel rule | LAD/LCx continuation decided by **course, not size** (LCx stays in the AV groove even when the OM is larger) — same as our project hints ("anterior interventricular groove", "left AV groove") |
| Inter-observer (160 test cases, double-read) | merged lumen DSC 92.8; LM 91.9, LAD 92.3, LCx 84.8, RCA 95.3; segment presence agreement 95.3 % |
| Original ImageCAS labels vs ICX | **DSC 41.8 ± 6.7**, HD95 16.2 mm (their Table 2) |
| Dominance | 729 R / 41 L / 30 co |

**Case mapping: ImageCAS id `n` is our case `c{n-1}` — 800/800.** Every ICX
label has exactly one Girder mask with identical shape and affine, and it is
always `c{n-1}`; Girder upload order is ImageCAS id order. (A first pass with
2-decimal rounding missed 3 cases on a 0.33 vs 0.3301 rounding edge; tolerance
matching recovers them, all `c{n-1}`.) The SegQueue submissions agree:
`imagecas_0002` is voxel-identical to our `c0001` (Dice 1.000 after the LPS z
flip) and `imagecas_0005` sits on `c0004`'s grid (spacing 0.3477, z = 206).

So the 200 excluded cases are `c{n-1}` for `n` in `filelist/exclude.txt`;
of the 40 cached CTs, 32 have ICX labels (5 of them ICX-test: c0150, c0250,
c0675, c0750, c0900) and 8 are excluded (c0025, c0075, c0100, c0275, c0475,
c0625, c0650, c0700).

Cohort facts measured on our 1000 headers in passing: all 512×512, z 166–277
(median 275), in-plane 0.289–0.465 mm (median 0.350), **z spacing 0.5 mm in all
1000** — the vault's "near-isotropic ~0.35 mm" is wrong in z for every case.
Header axes are identical for all 1000 (x negative, y and z positive).

## What it implies

1. **We do not have to wait for labels.** 800 of our 1000 cases already have
   expert per-segment labels on our exact voxel grid, and the 14→4 mapping is a
   lookup table (LM=1, LAD=2, LCx=3, RCA=9 one-to-one). A 4-class model can be
   trained on day one.
2. The 200 cases without ICX labels are exactly the ones ICX judged
   non-diagnostic. Our labelling team will hit them too; they are the hardest
   20 % and should be reported as a separate stratum, never pooled silently.
3. ICX's official split should be adopted for the 800 (its test set is
   double-read, which gives us a measured human ceiling per class for free).
4. Licensing is clean for training and redistribution with attribution
   (CC BY 4.0). The CT volumes themselves remain the ImageCAS Kaggle release
   (Apache 2.0 per the ICX paper).

## Limits

- The preprint is under review; numbers may change.
- `Descriptors.xlsx` quality counts (55/142/167/436) differ by 1–2 from the
  paper's text (55/140/168/437) — trivial, but the paper is not perfectly
  consistent with its own files.
- ICX's side-branch classes (D1, OM1, PDA, …) have no counterpart in our 4-class
  protocol; how they map depends on a convention our project has not written —
  see [[Crucible - Original binary masks disagree with ImageCAS-X]] and
  [[Crucible - A rule-based namer turns a clean binary tree into 4 classes]].

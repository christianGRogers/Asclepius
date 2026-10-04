---
tags: [plans/experiment, end-to-end, two-stage, tree-f1, real-predictions]
author: Bridge
round: 2
updated: 2026-10-04
---

# On real stage-1 output, the two-stage namer is within 0.01–0.04 tree-F1 of perfect naming (0.007 with the ramus set aside)

## Question

The Round 1 ruling (§4, Bridge) asked for one missing number: an **end-to-end** result. Take real
stage-1 predictions, name them with the two-stage namer, score them by tree-F1 (the master's deciding
metric, A1), and compare with a direct-model baseline on swaps and cuts.

No direct 4-class model exists yet; it needs the H100. So the baseline here is an **upper bound on any
direct model**: the same predicted lumen, with every voxel given its *reference* name ("oracle naming").
A direct model whose lumen is as good can at best match that arm. The gap (oracle − namer) is therefore
the most a direct model can gain over the two-stage route through naming.

## Method

- **Stage 1 (real):** ImageCAS-X's released binary nnU-Net (`3d_fullres`, fold 0, `checkpoint_best`;
  Zenodo 10.5281/zenodo.21887809), trained on the ImageCAS-X (thin) lumen. It was run on CPU on
  ImageCAS-X **test** cases, which no fold saw.
  - 8 predictions are Delta's ([[Delta - A released nnU-Net cuts 3 of 8 test trees that Dice scores at 0.84-0.92]]).
  - 11 more predictions are mine, from a verbatim copy of Delta's inference script
    (`experiments/Bridge/nnunet_infer.py`). Same settings: CT cropped to the reference bbox + 10 mm,
    tile step 0.75, no TTA.
  - Every arm starts from the same binary mask: threshold 0.5, components < 100 voxels removed.
- **Arms:**
  - `oracle`: each predicted voxel takes the nearest reference class. This is Delta's E8 convention
    and the direct-model upper bound.
  - `namer`: the frozen Round-1 labeller (v3: learned ostium, plausibility re-rank, anterior/posterior
    split, subtree inheritance) plus 4 mm graph bridging used **for naming only**. The voxel mask is not
    changed. It uses no reference information. It was never refit on the thin convention: same
    `ostium_w_dev2.json` as Round 1.
  - `namer_nb`: same, without bridging.
  - `ceiling`: the namer applied to the **reference** binary lumen, i.e. naming error alone.
- **Scoring:** Delta's code, imported read-only (`perturb_metrics.score`, `analyse_preds.CropGT`).
  - Reference: ImageCAS-X lumen, 4-class subtree convention (Delta's `ICX_TO_4`: ramus IM → LCx).
  - Ostium: Delta's reference ostium (thickest reference endpoint, LM preferred).
  - tF1 is computed at 0 mm and at **1.5 mm gap tolerance**.
  - Because the ramus rule is an open human decision (ruling §5.2), I also report tF1 @ 1.5 mm with
    ImageCAS-X's IM voxels excluded.
  - Case swap = some reference class whose detected centreline is < 50 % correctly named.
- Scripts: `experiments/Bridge/e2e.py`, `namer.py`, `summ_e2e.py`, `viz_e2e.py`.
- **Dev overlap, disclosed:** 6 of the 19 cases (c0150, c0250, c0675, c0750, c0900, c0951) were in my
  Round-1 development set. The rules were designed while looking at their *Girder-mask* naming, not at
  these predictions. The other 13 were never seen; they are reported separately.
- **Naming ceiling on the thin convention:** `ceiling.py` runs the namer on the ImageCAS-X reference lumen
  of ImageCAS-X test cases and scores it with ImageCAS-X's own labels. No projection is involved.

## Result (19 cases; 13 never seen in development)

| Arm (mean of 19) | tF1 @ 0 | **tF1 @ 1.5 mm** | tF1 @ 1.5, ramus excluded | per-class clDice | centreline label acc. | cases with a swap |
|---|---|---|---|---|---|---|
| oracle (perfect naming; direct-model upper bound) | 0.832 | **0.918** | 0.915 | 0.943 | 0.938 | 0 / 19 |
| **namer (two-stage, + naming bridges)** | 0.798 | **0.881** | **0.908** | 0.905 | 0.895 | 1 / 19 (ramus) |
| namer, no bridging | 0.772 | 0.853 | 0.878 | 0.877 | 0.876 | 2 / 19 |
| ceiling: namer on the reference lumen | 0.963 | 0.963 | **0.995** | 0.963 | 0.959 | 1 / 19 (same ramus case) |

Paired namer − oracle (tF1 @ 1.5 mm), mean and bootstrap 95 % CI over cases:

| Subset | n | all classes | ramus excluded |
|---|---|---|---|
| all | 19 | −0.037 [−0.060, −0.017] | **−0.007 [−0.011, −0.004]** |
| never seen (c0111, c0172, c0217, c0270, c0341, c0405, c0407, c0526, c0579, c0615, c0789, c0906, c0927) | 13 | −0.036 [−0.063, −0.014] | **−0.007 [−0.012, −0.003]** |
| development overlap (c0150, c0250, c0675, c0750, c0900, c0951) | 6 | −0.038 [−0.085, −0.003] | −0.007 [−0.012, −0.003] |

Per case, tF1 @ 1.5 mm (all classes / ramus excluded):

| case | oracle | namer | ceiling | IM present |
|---|---|---|---|---|
| c0111 | 0.959 / 0.959 | 0.959 / 0.959 | 0.988 / 0.988 | |
| c0150 | 0.853 / 0.853 | 0.842 / 0.842 | 1.000 / 1.000 | |
| c0172 | 0.902 / 0.902 | 0.902 / 0.902 | 0.995 / 0.995 | |
| c0217 | 0.977 / 0.977 | 0.968 / 0.968 | 0.991 / 0.991 | |
| c0250 | 0.983 / 0.983 | 0.983 / 0.983 | 1.000 / 1.000 | IM |
| c0270 | 0.934 / 0.929 | 0.882 / 0.923 | 0.949 / 0.994 | IM |
| c0341 | 0.960 / 0.937 | 0.813 / 0.933 | 0.817 / 0.983 | IM |
| c0405 | 0.941 / 0.941 | 0.937 / 0.937 | 0.997 / 0.997 | |
| c0407 | 0.756 / 0.756 | 0.725 / 0.725 | 0.993 / 0.993 | |
| c0526 | 0.850 / 0.861 | 0.846 / 0.857 | 0.986 / 0.986 | IM |
| c0579 | 0.960 / 0.946 | 0.874 / 0.947 | 0.925 / 1.000 | IM |
| c0615 | 0.944 / 0.939 | 0.934 / 0.929 | 0.984 / 0.984 | IM |
| c0675 | 0.829 / 0.823 | 0.765 / 0.812 | 0.931 / 1.000 | IM |
| c0750 | 0.909 / 0.902 | 0.763 / 0.886 | 0.853 / 1.000 | IM |
| c0789 | 0.927 / 0.927 | 0.907 / 0.907 | 0.995 / 0.995 | |
| c0900 | 0.962 / 0.962 | 0.962 / 0.962 | 1.000 / 1.000 | |
| c0906 | 0.939 / 0.939 | 0.934 / 0.934 | 1.000 / 1.000 | |
| c0927 | 0.949 / 0.945 | 0.848 / 0.942 | 0.904 / 1.000 | IM |
| c0951 | 0.909 / 0.909 | 0.902 / 0.902 | 0.993 / 0.993 | |

- **Every large gap is the ramus.** 9 of 19 cases carry an ImageCAS-X IM branch. The reference convention
  (Delta's `ICX_TO_4`) puts IM under the LCx; my rule gives it to the class it points towards. The one
  "swap" (c0341, LCx) is this disagreement, and it appears identically on the reference lumen. With IM
  excluded, no case loses more than 0.031 to perfect naming.
- **The cuts are stage 1's, not the namer's.** The cut trees (c0407, c0526, c0675) score the same in both
  arms, within 0.031 once the ramus is set aside.
- **Bridging:** it changed 2 of 19 cases: c0675 +0.55 (0.215 → 0.765; without it the namer roots the wrong
  piece and swaps three classes) and c0407 −0.021 (one wrong join).
- **Thin convention, larger sample:** namer on the ImageCAS-X reference lumen for **63 ImageCAS-X test
  cases** (56 never seen; run interrupted by a container restart at 63/160, `ceiling_test.jsonl`):
  tF1 @ 1.5 mm 0.981, **0.990 with IM excluded**, ≥ 0.9 in 98.4 % of cases, 2 swaps, 0 failures. The namer
  was built and fit on our thick Girder masks and never refit.

## What it implies

1. **First end-to-end number.** On real stage-1 output (19 ImageCAS-X test cases, 13 never seen), the
   two-stage route gives tF1 @ 1.5 mm **0.881**, against **0.918** for perfect naming of the same lumen.
   Setting the ramus convention aside, it is **0.908 vs 0.915**: a gap of **−0.007, CI [−0.011, −0.004]**.
   A direct 4-class model with the same lumen can beat the two-stage route by at most that margin, plus
   whatever the ramus rule costs, and only if it names every voxel perfectly. Neither route made a real
   swap.
2. **The end-to-end loss is the lumen, not the names.** From 1.0 down to 0.915 is stage 1; from 0.915 down
   to 0.908 is naming. The cuts dominate. This is where the master's GPU effort goes already.
3. **Whether the two-stage route ever *wins* depends on how well a direct model names**, which is not
   measured anywhere yet. It is free to measure on the master's val predictions: rename D's foreground,
   compare per case. That is [[Bridge v2]].
4. **The ramus rule is the biggest single naming lever** (up to 0.15 tF1 in one case, 9/19 cases carry an
   IM). Once humans write it (ruling §5.2), it is a switch in the namer.

## Limits

- **19 cases.** One fold of one released binary model. c0041 and c0907 were not run (c0041 was
  OOM-killed on the shared machine; the container restart stopped the queue). It was trained on the thin
  convention with a small patch (96 × 160 × 160 voxels, 48 × 56 × 56 mm), smaller than the master's.
- **The oracle is an upper bound, not a direct model.** A real direct model's lumen may differ (better
  or worse) from a binary model's; nothing here measures that.
- **The CT crop hides far-away false positives.** The rooted-ostium definition is Delta's, not the aorta
  contact required for the sealed test. Both arms share both limits.
- **6 of 19 cases overlap my Round-1 development cases.** That was on different masks: Girder, not these
  predictions.

---
tags: [plans/experiment, end-to-end, two-stage, tree-f1, real-predictions]
author: Bridge
round: 2
updated: 2026-10-04
---

# On real stage-1 output, the two-stage namer is within 0.01–0.03 tree-F1 of perfect naming

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
  - More predictions are mine, from a verbatim copy of Delta's inference script
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
- **Dev overlap, disclosed:** 5 of the 9 cases (c0150, c0250, c0675, c0750, c0900) are CT-cached
  cases that were in my Round-1 development set. The rules were designed while looking at their
  *Girder-mask* naming, not at these predictions. The other 4 (c0111, c0407, c0526, c0906) were never
  seen.

## Result (9 cases)

| Arm | tF1 @ 0 | **tF1 @ 1.5 mm** | tF1 @ 1.5, ramus excluded | per-class clDice | centreline label acc. | cases with a swap |
|---|---|---|---|---|---|---|
| oracle (perfect naming; direct-model upper bound) | 0.795 | **0.893** | 0.893 | 0.929 | 0.936 | 0 / 9 |
| **namer (two-stage, + naming bridges)** | 0.770 | **0.864** | **0.884** | 0.898 | 0.893 | **0 / 9** |
| namer, no bridging | 0.715 | 0.805 | 0.821 | 0.838 | 0.853 | 1 / 9 |
| ceiling: namer on the reference lumen | 0.972 | 0.972 | **0.996** | 0.972 | 0.965 | 0 / 9 |

Paired namer − oracle, tF1 @ 1.5 mm, per case:

| | c0111 | c0150 | c0250 | c0407 | c0526 | c0675 | c0750 | c0900 | c0906 |
|---|---|---|---|---|---|---|---|---|---|
| all classes | 0.000 | −0.011 | 0.000 | −0.031 | −0.004 | −0.064 | −0.146 | 0.000 | −0.005 |
| ramus excluded | 0.000 | −0.011 | 0.000 | −0.031 | −0.005 | −0.011 | −0.016 | 0.000 | −0.005 |

- **Unseen cases** (c0111, c0407, c0526, c0906): mean gap −0.010 (tF1 0.858 vs 0.868).
- **The two large gaps are both the ramus.** c0750 and c0675 carry an ImageCAS-X IM branch. The reference
  convention puts it under the LCx; my rule gives it to the class it points towards (LAD here). With the
  ramus excluded, the gaps are −0.016 and −0.011. On the reference lumen the namer is 0.853 and 0.931
  with the ramus, and 1.000 for both without it.
- **The cuts are stage 1's, not the namer's.** The three trees Delta found cut (c0407, c0526, c0675) score
  0.73–0.86 in both arms. Naming does not make a cut tree worse, and it cannot make it better.
- **Bridging is necessary.** Without the naming bridges, c0675's prediction breaks into pieces. The namer
  then roots the wrong piece and swaps three classes (tF1 0.215). With 4 mm bridges it scores 0.765
  (0.812 with the ramus excluded). Bridging changed no other case except c0407: −0.021, from one wrong
  join.
- **Thin convention:** on the ImageCAS-X reference lumen, the namer built and fit on our thick Girder
  masks reaches tF1 0.996 with the ramus excluded. It is convention-agnostic without refitting.

## What it implies

1. **First end-to-end number:** on real stage-1 output, two-stage naming gives tF1 @ 1.5 mm
   **0.864**, against **0.893** for perfect naming of the same lumen. Excluding the open ramus
   convention, it is **0.884 vs 0.893**. A direct 4-class model with the same lumen quality could beat
   the two-stage route by at most **0.009–0.029 tF1**, and only if it named every voxel perfectly. No
   swaps appeared in either arm.
2. **Most of the end-to-end tF1 loss is the lumen, not the names:** 0.893 → 1.0 is stage 1; 0.884 → 0.893
   is naming. The deciding metric is dominated by cuts and missed distal vessel. This is where the master's
   GPU effort belongs, and where it already goes.
3. **Whether the two-stage route ever wins** depends on how well a direct model actually names. On
   real direct predictions, the comparison is free: rename the direct model's own foreground with this
   namer and compare tF1 per case. That is the Round-2 plan ([[Bridge v2]]).
4. **The ramus rule is worth fixing early.** It moved tF1 by up to 0.13 in a case. Once the humans write
   the rule (ruling §5.2), it is one line in the namer: the ramus-like child goes to LCx, or to LAD, or
   takes its own label.

## Limits

- **9 cases (more queued).** One fold of one released binary model. It was trained on the thin
  convention with a small patch (96 × 160 × 160 voxels, 48 × 56 × 56 mm), smaller than the master's.
- **The oracle is an upper bound, not a direct model.** A real direct model's lumen may differ (better
  or worse) from a binary model's; nothing here measures that.
- **The CT crop hides far-away false positives.** The rooted-ostium definition is Delta's, not the aorta
  contact required for the sealed test. Both arms share both limits.
- **5 of 9 cases overlap my Round-1 development cases.** That was on different masks: Girder, not these
  predictions.

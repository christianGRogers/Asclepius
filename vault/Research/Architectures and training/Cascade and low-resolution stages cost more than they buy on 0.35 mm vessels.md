---
aliases: [Cascade vs full-res, 3d_lowres, Cascade trigger threshold]
tags: [research/architecture, nnunet, cascade, resolution, evidence, code-check]
status: solid
updated: 2026-09-19
---

# Cascade and low-resolution stages cost more than they buy on 0.35 mm vessels

Sub-question: is [[Training plan]] §1's refusal of `3d_cascade_fullres` supported, and
is the "12.5 % cascade trigger" gate in §2 stated correctly?

## The accuracy argument

The cascade's first stage segments a *downsampled* volume and passes that prediction
to the full-resolution stage as extra input channels. Its purpose is to supply
context when the full-resolution patch is too small to see the organ. The cost is
paid where the structure is thinner than the coarsened voxel.

Measured on our own cohort (Zeng et al., **Computerized Medical Imaging and
Graphics** 2023, DOI
[10.1016/j.compmedimag.2023.102287](https://doi.org/10.1016/j.compmedimag.2023.102287),
read as arXiv:2211.01607, 1000 ImageCAS volumes, 4-fold CV): halving the input to
256 × 256 × 128 cost 7.38 % Dice, and 128³ cost 12.32 % Dice, both p < 0.0001. Those
are exactly the operating points a low-resolution first stage lives at. A distal
branch of 1.5–2 mm is 4–6 voxels at 0.35 mm and 1–2 voxels at 1.0 mm; there is
nothing for the coarse stage to find.

A second, subtler ImageCAS result points the same way. Their tree- and graph-based
pipelines depend on a pre-segmentation, and for the *tree* pipeline the difference
between a high-resolution and low-resolution input was only 0.12 % (p > 0.05) —
because the pre-segmentation had already lost the vessels, so the resolution of the
downstream stage no longer mattered. Losses from a coarse first stage are not
recovered later in the pipeline.

## The counter-evidence, recorded honestly

Two results say a coarse stage is not *purely* harmful when it is used as extra
context rather than as a bottleneck:

- ImageCAS's own winning baseline is a **coarse + patch ensemble**: patch-only
  ensembling reached 81.11 % Dice and the best single patch model 82.70 %, while
  adding the coarse-segmentation branch reached **82.96 %** — the headline number
  this project calibrates against. The coarse branch added ~0.3 Dice as an ensemble
  member, not as a gate.
- Hung, Chiang, Liu et al., *Design Rules for Robust Coronary Artery Segmentation*,
  **Annals of Biomedical Engineering** 54(5):1275–1286, 2026, DOI
  [10.1007/s10439-026-03974-5](https://doi.org/10.1007/s10439-026-03974-5), compared
  2D, 3D full-resolution, 3D low-resolution, cascade and an ensemble of nnU-Net
  configurations on 1000 ImageCAS scans with a 200-case held-out test set. The 3D
  **ensemble** was best (DSC 0.8337, 95 % CI 0.8269–0.8405). The abstract states only
  that 3D beat 2D; the per-configuration numbers that would tell us whether the
  cascade beat `3d_fullres` alone are behind the Springer paywall and are
  **unverified** — no UofT-authenticated browser was available this session.

Read together: the defensible claim is that *ensembling* configurations helps (as it
almost always does, at 3–5× the inference cost), not that a cascade beats
full-resolution training. Neither paper shows a cascade winning on its own, and
neither reports a distal-branch or centreline metric, which is where the coarse
stage's damage would show. The plan's position survives, but the honest wording is
"no evidence a cascade helps, direct evidence that downsampling hurts", not "the
cascade has been shown to lose".

## The gate in §2 is stated against the wrong number — a code check

The plan and `configs/tasks/Dataset710_Coronary.yaml` both instruct the operator to
check that "the patch covers ≥ 12.5 % of the median image shape (so no cascade is
planned)". The current nnU-Net v2 planner uses **25 %**, not 12.5 %. In
`nnunetv2/experiment_planning/experiment_planners/default_experiment_planner.py`
(checked on tags `v2.5.1` and `v2.6.2`, both of which satisfy this repository's
`nnunetv2>=2.5,<3` pin, and on `master`):

```
self.lowres_creation_threshold = 0.25  # if the patch size of fullres is less than 25% of the voxels in the
# median shape then we need a lowres config as well
...
while num_voxels_in_patch / median_num_voxels < self.lowres_creation_threshold:
    ...  # incrementally coarsen spacing by 1.03 until a lowres config fits
```

Consequences for the plan's arithmetic:

1. The plan's own estimate of the patch fraction at 70 GB is **27–30 %**. Against the
   real threshold of 25 % that is a margin of a few points, not the comfortable 2×
   the text implies. If the planner returns 22 %, a `3d_lowres` and a
   `3d_cascade_fullres` entry *will* appear in `nnUNetPlans.json`.
2. That is not a failure. The planner writing a low-res configuration does not make
   us train it — `configuration: 3d_fullres` in the task config decides what runs,
   and `3d_lowres` costs nothing but a preprocessing folder (and it can be skipped
   with `-c 3d_fullres` at preprocessing time to save disk, which matters given the
   ~250 GB already budgeted). The gate should therefore be re-stated as *an indicator
   that the patch is large enough*, with the correct threshold, rather than as a
   pass/fail on cascade planning.
3. There is a second, independent trigger nearby: the low-res config is dropped again
   if the low-res median shape is less than 2× smaller than the full-res one. So on
   this dataset a marginal patch fraction may or may not produce a cascade entry
   depending on how far the spacing has to be coarsened. One more reason to read the
   planner printout rather than predict it.

## What this implies for [[Training plan]]

1. **Correct the threshold** in §2's gate (a) and in the header comment of
   `configs/tasks/Dataset710_Coronary.yaml`: the trigger is 25 % of the median image
   voxels, not 12.5 %. Proposed wording is in `Proposed changes.md`.
2. **Re-frame gate (a)** from "so no cascade is planned" to "so the patch sees at
   least a quarter of the volume". Whether nnU-Net writes a `3d_lowres` entry is
   cosmetic; what matters is patch fraction and that we train `3d_fullres`.
3. **Keep the refusal of `3d_cascade_fullres`**, with the evidence stated as it
   actually is: −7.38 % / −12.32 % Dice for coarser inputs on ImageCAS, plus the
   tree-pipeline result that context lost early is not recovered late.
4. **Add an explicit note that ensembling is the thing the two ImageCAS-scale papers
   actually show helping** (82.96 % via coarse+patch ensemble; 0.8337 via a 3D
   ensemble). The plan currently has no position on ensembling. It is cheap in
   training terms if the folds are being trained anyway, and expensive at inference
   — and inference cost is already up 3–4× from the no-crop decision. Worth a
   sentence in the evaluation section rather than silence.

Related:
[[Patch size is the dominant lever for thin vessels, and the evidence supports the 70 GB budget]],
[[nnU-Net still beats transformer and Mamba architectures, and ResEnc is the only upgrade worth paying for]].

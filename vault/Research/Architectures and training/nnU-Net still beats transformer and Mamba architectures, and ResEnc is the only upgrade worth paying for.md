---
aliases: [nnU-Net Revisited, Architecture comparison, ResEnc vs transformers]
tags: [research/architecture, nnunet, resenc, transformers, mamba, evidence]
status: solid
updated: 2026-09-19
---

# nnU-Net still beats transformer and Mamba architectures, and ResEnc is the only upgrade worth paying for

Sub-question: for a 3D voxel segmenter of thin tubular structures, is there any
architecture that beats a well-configured nnU-Net, and where do the residual-encoder
(ResEnc) presets sit? This is the evidence behind [[Training plan]] §1 and §3.3.

## The primary evidence: nnU-Net Revisited

Isensee, Wald, Ulrich, Baumgartner, Roy, Maier-Hein, Jaeger. *nnU-Net Revisited: A
Call for Rigorous Validation in 3D Medical Image Segmentation.* MICCAI 2024, LNCS
15009, DOI [10.1007/978-3-031-72114-4_47](https://doi.org/10.1007/978-3-031-72114-4_47)
(read via the arXiv HTML, arXiv:2404.09556v2).

All methods were run inside the nnU-Net framework on six datasets — BTCV (n=30),
ACDC (n=200), LiTS (n=131), BraTS21 (n=1251), KiTS23 (n=489), AMOS22 (n=360) — with
identical preprocessing, schedule and evaluation, and with VRAM and training time
reported. Dice (%), 5-fold CV:

| Method | BTCV | ACDC | LiTS | BraTS | KiTS | AMOS | VRAM (GB) | Train (h) |
|---|---|---|---|---|---|---|---|---|
| nnU-Net (original, plain conv) | 83.08 | 91.54 | 80.09 | 91.24 | 86.04 | 88.64 | 7.7 | 9 |
| nnU-Net ResEnc M | 83.31 | 91.99 | 80.75 | 91.26 | 86.79 | 88.77 | 9.1 | 12 |
| nnU-Net ResEnc L | 83.35 | 91.69 | 81.60 | 91.13 | **88.17** | 89.41 | 22.7 | 35 |
| nnU-Net ResEnc XL | 83.28 | 91.48 | 81.19 | 91.18 | **88.67** | 89.68 | 36.6 | 66 |
| MedNeXt L k3 | 84.70 | 92.65 | 82.14 | 91.35 | 88.25 | 89.62 | 17.3 | 68 |
| MedNeXt L k5 | 85.04 | 92.62 | 82.34 | 91.50 | 87.74 | 89.73 | 18.0 | 233 |
| STU-Net S / B / L | 82.92 / 83.05 / 83.36 | 91.04 / 91.30 / 91.31 | 78.50 / 79.19 / 80.31 | 90.55 / 90.85 / 91.26 | 84.93 / 86.32 / 85.84 | 88.08 / 88.46 / 89.34 | 5.2 / 8.8 / 26.5 | 10 / 15 / 51 |
| SwinUNETR | 78.89 | 91.29 | 76.50 | 90.68 | 81.27 | 83.81 | 13.1 | 15 |
| SwinUNETR V2 | 80.85 | 92.01 | 77.85 | 90.74 | 84.14 | 86.24 | 13.4 | 15 |
| nnFormer | 80.86 | 92.40 | 77.40 | 90.22 | **75.85** | **81.55** | 5.7 | 8 |
| CoTr | 81.95 | 90.56 | 79.10 | 90.73 | 84.59 | 88.02 | 8.2 | 18 |
| U-Mamba Bot | 83.51 | 91.79 | 80.40 | 91.26 | 86.22 | 89.13 | 12.4 | 24 |
| U-Mamba Enc | 82.41 | 91.22 | 80.27 | 90.91 | 86.34 | 88.38 | 24.9 | 47 |
| "No-Mamba Base" (U-Mamba with the Mamba blocks removed) | 83.69 | 91.89 | 80.57 | 91.26 | 85.98 | 89.04 | 12.0 | 24 |
| MONAI Auto3DSeg SegResNet | 80.69 | 90.69 | 79.28 | 90.79 | 81.11 | 87.27 | 20.0 | 22 |
| MONAI Auto3DSeg SwinUNETR | 76.54 | 82.68 | 68.59 | 89.90 | 52.82 | 85.05 | 34.5 | 9 |

What this table says, in the authors' own summary, is that the recipe for
state-of-the-art is "1) employing CNN-based U-Net models, including ResNet and
ConvNeXt variants, 2) using the nnU-Net framework, and 3) scaling models to modern
hardware resources."

Specific readings that matter for this project:

- **Transformers lose, and lose most on the hard datasets.** SwinUNETR is 6.9 Dice
  below ResEnc L on KiTS and 5.6 below on AMOS; nnFormer collapses on KiTS (75.85 vs
  88.17) and AMOS (81.55 vs 89.41). These are the two datasets the authors single out
  as *discriminative*. The transformer numbers look competitive only on ACDC and
  BraTS, which are the two datasets they call unsuitable for benchmarking.
- **Mamba adds nothing.** The ablation is unusually clean: "No-Mamba Base" — the same
  network with the Mamba blocks deleted — matches or beats both U-Mamba variants on
  five of six datasets at lower VRAM. Whatever U-Mamba gains over the original
  nnU-Net comes from the rest of the architecture, not the state-space blocks.
- **MedNeXt is the one real rival, and it is priced out.** MedNeXt L k5 wins BTCV,
  LiTS and AMOS by roughly 0.3–1.7 Dice over ResEnc L, but at 233 h of training
  against 35 h — 6.7× — and the authors explicitly caution that "parts of MedNeXt's
  advantages can be explained by target spacing selection", i.e. not architecture.
  ResEnc L beats it on KiTS, the hardest task.
- **Benchmark hygiene.** BTCV's signal-to-noise ratio (SD ratio < 1) means the
  between-method differences there are inside the noise, and BraTS21 is saturated.
  The authors recommend ACDC, AMOS and KiTS. Read the coronary literature the same
  way: a 0.5-Dice win on a 40-case set is not a result.
- **Scaling has a ceiling.** ResEnc XL beats L only on KiTS (+0.50) and AMOS (+0.27),
  and is *worse* on BTCV, ACDC and LiTS, at nearly double the training time. Compute
  scaling pays on hard, large tasks and not otherwise.

## Coronary-specific evidence

Direct architecture comparisons on CCTA are much weaker than the benchmark above,
and mostly come from papers proposing the winning method. Recorded with that caveat:

- Hung, Chiang, Liu et al., *Design Rules for Robust Coronary Artery Segmentation: A
  Systematic Analysis of Dataset Size, Windowing, Architectures, and Vessel Geometry*,
  **Annals of Biomedical Engineering** 54(5):1275–1286, 2026, DOI
  [10.1007/s10439-026-03974-5](https://doi.org/10.1007/s10439-026-03974-5). Our exact
  data — 1000 ImageCAS CTCA scans, 200-case independent test set. All 3D nnU-Net
  configurations beat 2D; the 3D ensemble was best at **DSC 0.8337 (95% CI
  0.8269–0.8405), IoU 0.7178 (0.7080–0.7275)**. Performance was flat across vessel
  curvature and tortuosity. *Only the abstract was accessible* (Springer paywall; no
  UofT-authenticated browser available this session), so the per-configuration
  numbers for `3d_fullres` vs `3d_lowres` vs cascade are **unverified** — see
  [[Cascade and low-resolution stages cost more than they buy on 0.35 mm vessels]].
- The TopCoW challenge (Circle of Willis, 13 vessel classes on CTA and MRA —
  multiclass *per-branch vessel* labelling, the closest public analogue to our task;
  arXiv:2312.17670v2, **preprint of a challenge report**) found "around half of the
  teams converged to nnUNet". The one team that used Swin-UNETR used it only as the
  multiclass head on top of an nnU-Net binary stage. No team used external pretraining.

Where the coronary literature disagrees with the benchmark: several 2025–2026
coronary papers report transformer or Mamba hybrids beating "nnU-Net" on ImageCAS by
2–3 Dice points. Every such claim needs the nnU-Net Revisited test applied — was the
baseline the *current* nnU-Net (ResEnc, correct spacing, full schedule) or a
weakened one, and is the dataset discriminative? None of the ones surfaced so far are
in a venue of the class listed for this project, and they are not recorded here as
evidence.

## What this implies for [[Training plan]]

1. **§1 and §3 are well supported and need no change.** A plain nnU-Net at native
   spacing is the right baseline, and no transformer or Mamba variant has earned a
   run on this project's compute.
2. **The paired ResEnc run (§3.3) is the right single architectural experiment**, and
   the expected effect size should be written down before it runs: on the two
   discriminative datasets ResEnc L gained +2.13 (KiTS) and +0.77 (AMOS) Dice over the
   plain nnU-Net, and ~+0.3–1.5 elsewhere. If our paired run moves Dice by less than
   ~0.5 points it is inside the noise and the plain config should stay.
3. **Budget caution for ResEnc at ~70 GB.** The published presets top out at XL
   (36.6 GB, 66 h). Our plan asks for roughly double that. XL already showed
   *negative* returns over L on three of six datasets, so the honest prior is that the
   extra VRAM should be spent on patch size at ResEnc-L-like depth rather than on more
   channels — and that the ResEnc run will take 2–4× the plain run's wall-clock, which
   matters against a 24 h walltime with job-chain resume.
4. **Add a line to §4 ("explicitly ruled out"): Mamba-based U-Nets.** The "No-Mamba"
   ablation is decisive enough to rule them out by evidence rather than by silence.
5. **MedNeXt is the only architecture worth keeping on a watch-list**, and only if
   training time ever stops being the binding constraint. At 6.7× ResEnc L's runtime
   it does not fit a 24 h chain for a 1000-case, ~256³-patch job.

Related: [[Cascade and low-resolution stages cost more than they buy on 0.35 mm vessels]],
[[Patch size is the dominant lever for thin vessels]].

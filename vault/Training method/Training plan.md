---
aliases: [TRAINING-PLAN, Training plan]
tags: [training/method, nnunet, coronary, decision-record]
status: living
repo: Asclepius
updated: 2026-09-19
---

# Training plan

The plan for the multiclass coronary model, as decided so far. Decisions are
recorded with their reasoning and the evidence behind them; what is still open
is listed at the bottom and is not implied by anything above it. The retired
previous plan is preserved in full on the `plan-v1` branch of the Asclepius
repository; [[Plan status]] records what was removed and why.

Evidence cited as *ImageCAS* and *nnU-Net* refers to the two papers condensed in
[[Research context]] (Zeng et al., CMIG 2023; Isensee et al., Nat Methods 2021).

## Fixed constraints

- Training runs on **Trillium** (SciNet): 1 × H100 SXM **80 GB** per job, 24-hour
  walltime, job-chain resume. Everything below assumes that card.
- Data is the **1000 ImageCAS CCTA volumes** (512 × 512 × 206–275, ~0.29–0.45 mm,
  near-isotropic), held on the project's Girder server, already ingested into
  SegQueue. ImageCAS ships one merged binary lumen mask per case. **Per-branch
  labels exist for 800 of the 1000 cases**: ImageCAS-X (Bransby et al.,
  arXiv:2608.30404; Zenodo 10.5281/zenodo.21887809) re-annotated them into a
  14-class schema under CC BY 4.0, with centerlines, meshes and scan-level
  descriptors. What our annotators produce, and whether they produce it at all,
  is now an open question rather than a premise — see
  [[Proposed changes to the training plan]] §0 and [[Review summary]].

## Decided

### 1. One-stage voxel model: nnU-Net v2 `3d_fullres`, no cascade, native spacing

The model reads the data at acquired resolution end to end. `spacing: native`
(nnU-Net's median-spacing rule; the ImageCAS cohort is near-isotropic ~0.35 mm,
so the anisotropy branches never fire) and **no `3d_cascade_fullres`**.

Why: a distal branch is 1.5–2 mm — a few voxels. Any stage that downsamples
destroys exactly the structures this project exists to label. ImageCAS measured
the cost directly: −12.3 % Dice going from 512²×256 to 128³ input, six times the
effect of any architectural change they tried. The cascade's low-resolution
first stage pays that penalty by construction.

To be explicit about terms: "no downsampling" means no cascade and no coarsening
of target spacing at resampling. The encoder's *internal* pooling stays — that is
what builds the receptive field, and skip connections carry full-resolution
detail back up.

### 2. No heart crop. The patch budget does the work instead

Plan with `segtrain plan --task 710 --gpu-mem 70`. The default 8 GB budget sizes
patches around 128³ (~2 M voxels); a large budget buys **256³ (16.8 M voxels), and
that is the ceiling** — the planner rescales its initial guess to the volume of a
256³ patch and from there only ever shrinks. So the patch is **~23–31 % of a full
volume, against nnU-Net's real 25 % cascade trigger, with no cropping at all**,
and the fraction does not improve with a larger budget. A ~90 mm patch landing
near the mediastinum contains most of the coronary tree plus the aortic root and
both ostia — the context that separates LAD from LCx.

Two things this section used to get wrong, both verified in the planner's own
source. The trigger is 25 %, not 12.5 %, so the margin is a few points rather
than more than double. And `--gpu-mem 70` does not buy "17–20 M voxels at batch
2": above ~52 GB the surplus goes to **batch size**, so 70 GB returns batch 3 at
the same patch — which fails gate (c) below and which the planner's own memory
model puts at 77.3 GB on an 80 GB card. Whether to move the budget to ~56 GB is a
decision, not a correction, and it is open. See [[Architecture and compute]].

The crop never made the patch bigger; VRAM does that. What the crop bought
(patch-fraction, sampling efficiency) the big patch and the sampler now buy,
and dropping it removes a real failure mode: a cropper that clips a low-running
RCA truncates a vessel silently, and nothing downstream can detect it. Keeping
whole volumes also lets the model learn to reject coronary look-alikes
(pulmonary vessels, bone edges) that live outside any heart crop — ImageCAS's
documented mis-crop failure.

Accepted costs: preprocessed data ~3× larger on disk (order 250 GB + transient
doubling from the `.npz`→`.npy` unpack — measure, and provision `$SCRATCH`
accordingly), and ~3–4× more sliding windows at inference. Neither affects
training accuracy.

A heart-cropped variant is a **paired experiment for later**, decided by
measurement, not a prerequisite.

**Gates before any GPU submission** — from the planner printout, which needs no
GPU: (a) patch fraction ≥ **25 %** so no cascade is planned
(`lowres_creation_threshold` is 0.25, verified in nnU-Net source at `v2.5.1`,
`v2.6.2` and `master` — the 12.5 % this gate used to name was wrong);
(b) target spacing came out native, not dragged coarse by thick-slice outliers;
(c) batch size 2. The ~256³ figure above is scaling arithmetic; the planner's
number is the real one.

Two things about gate (a) are now known and change how it should be read. The
planner **caps the patch at the volume of a 256³ patch and only ever shrinks
it**, spending surplus VRAM on batch size instead, so patch fraction is pinned
near 16.8 M voxels ÷ median volume — roughly 23–31 %, and not something a larger
`--gpu-mem` can raise. And ImageCAS's z-extent of 206–275 straddles the
threshold: z = 256 lands on 25.0 % exactly, z = 275 on 23.3 %. So (a) has no
remedy behind it and should be recorded rather than gated on, with a sub-25 %
outcome accepted in advance. See [[Architecture and compute]].

### 3. Sequence: binary first, multiclass second, ResEnc third

1. **Binary lumen model now**, trained on all 1000 existing ImageCAS masks with
   this exact configuration. It validates the whole Trillium chain end to end,
   calibrates against the published 82.96 % Dice benchmark, and its predictions
   become the presegmentation seeds SegQueue hands annotators — splitting an
   existing tree is minutes; drawing one is an hour.
2. **Multiclass model** on the same configuration once annotated cases flow.
   Retrain from scratch by default; fine-tuning from the binary weights is a
   cheap experiment, not the plan of record.
3. **One paired ResEnc run** (nnU-Net's residual-encoder presets, sized for this
   much VRAM) against the plain U-Net once the multiclass baseline is stable:
   same fold, same data, same evaluation harness. Winner becomes the config.
   Not first, because it adds a variable before a baseline exists.

On the published benchmark: ImageCAS's 82.96 % was trained ~21 k iterations on
one RTX 3090; nnU-Net's schedule is ~250 k. Beating it is a sanity check, not
the contribution — and it is a weaker sanity check than it looks, because 82.96 %
was scored against labels a later re-annotation disagrees with at 41.8 % Dice.

**What the contribution is, is open.** This plan used to say it was the
per-branch labelling; ImageCAS-X's release makes that false as written, and
nothing has replaced it yet. The candidates, and the case for each, are in
[[Review summary]] and [[Red team of the whole plan]]; the one the reviewers
prefer is the first automated per-branch benchmark on these labels, which nobody
has built. **This is the decision that blocks the most and it has not been
made.**

### 4. What is explicitly ruled out

- **Tree/graph-structured models as the primary segmenter.** Both scored 8–12
  Dice points below a plain voxel CNN on this dataset, and the diagnosed cause
  is structural: any vessel the pre-segmentation misses never becomes a node and
  is unrecoverable. Graph reasoning is welcome *downstream* — branch naming on
  an extracted centerline, reconnection post-processing — but must never be able
  to lose a vessel the voxel model found.
- **nnU-Net's largest-component post-processing.** The coronary tree is two or
  three disconnected trees; the rule deletes whole vessels, and ImageCAS shows
  it removing real coronary while keeping bone. `segtrain evaluate` scores raw
  predictions; if `nnUNetv2_determine_postprocessing` is ever run by hand, audit
  what it selected before believing it.
- **Mirroring augmentation** for anything multiclass. It swaps the left coronary
  tree for the right; the task is to tell them apart.

### 5. Standing experiments (cheap, scheduled early)

- **Rotation augmentation ablation.** The two papers flatly disagree on this
  anatomy: nnU-Net always rotates and found removing augmentation a clear loss
  across ten datasets; ImageCAS measured rotation+flip *hurting* by ~2.7 %
  (p < 0.0001) on this exact cohort. Ablate rotation separately from mirroring.
  Intensity augmentations (noise, blur, brightness, contrast, gamma, low-res
  simulation) are not in dispute and stay.
- **Class-balanced, vessel-anchored patch sampling** for the multiclass model.
  nnU-Net's default picks one random foreground class for a third of patches;
  with many classes of wildly different volume — some absent in many patients —
  rare branches starve. This also recovers the sampling efficiency the heart
  crop would have provided: patch placement gets smart instead of the volume
  getting small. Keep some genuinely random background patches for look-alike
  rejection.
- **Heart-crop paired run** (see §2).
- **Binary-init fine-tuning vs from-scratch** for the multiclass model (see §3).

## Evaluation (direction settled, thresholds open)

Dice is kept but demoted: on 3–4-voxel tubes it punishes boundary jitter and
barely notices a missing distal branch — the exact wrong trade for this task,
and both papers acknowledge it. Report alongside it, per class: **clDice /
centerline overlap**, **branch detection rate** (was the vessel found at all),
**NSD**, connected-component count against expected, and an AHA-segment
confusion matrix. Distances as **AHD**, not HD, which single outliers dominate.
Calibration, corrected. The 0.856 this section used to cite as "the ceiling" is
ASOCA's agreement on the **binary lumen** — one class, foreground against
background — and using it as a per-branch ceiling compares two different tasks.
Annotators who agree a voxel is vessel can still disagree about which vessel owns
it.

Use ImageCAS-X's figures on this cohort instead, and note that the ceiling is a
curve by vessel rather than a number: merged lumen 92.8 ± 3.1, RCA 95.3 ± 5.0,
LAD 92.3 ± 6.7, LM 91.9 ± 13.7, LCx 84.8 ± 19.8, down to OM1 74.1 ± 32.3 and
L-PLA 70.9 ± 27.2. Those standard deviations are not noise around a mean — at
SD 32 on a bounded metric the distribution is bimodal, and the honest reading is
that in a substantial minority of cases two trained analysts do not agree the
vessel is there at all.

Two consequences worth stating here, because they are easy to get wrong. The
92.8 is itself a **merged-lumen** number, so it is the binary calibration target
and not the multiclass ceiling; a macro mean over the 14 per-segment figures is
**82.4**, which is what a 14-class macro Dice can actually be compared against.
And every published calibration number for this cohort — 82.96, 89.8, 92.8 — is
merged lumen. Per-branch inter-rater agreement from our own overlap set becomes
the multiclass ceiling once measured. See [[Metrics and evaluation]].

## Still open

- **Class schema.** The central undecided question: how many vessels are their
  own class, and the written policy for bifurcation ownership, absent branches
  (ramus intermedius), and dominance-dependent PDA/PLV. Blocks the multiclass
  task config and the annotation protocol; does not block the binary model.
- **Fold scheme and split ratios** — including whether to adopt the official
  ImageCAS 4-fold split for comparability.
- **Loss**: defaults (Dice+CE) for the baseline; clDice/cbDice term is a
  candidate second experiment, not yet scheduled.
- **Acceptance thresholds** for the evaluation metrics above.
- **Annotation protocol details**: overlap-set size, arbitration, gold cases.

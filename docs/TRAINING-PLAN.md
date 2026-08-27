# Training plan

The plan for the multiclass coronary model, as decided so far. Decisions are
recorded with their reasoning and the evidence behind them; what is still open
is listed at the bottom and is not implied by anything above it. The retired
previous plan is preserved in full on the `plan-v1` branch.

Evidence cited as *ImageCAS* and *nnU-Net* refers to the two papers condensed in
the research notes (Zeng et al., CMIG 2023; Isensee et al., Nat Methods 2021).

## Fixed constraints

- Training runs on **Trillium** (SciNet): 1 × H100 SXM **80 GB** per job, 24-hour
  walltime, job-chain resume. Everything below assumes that card.
- Data is the **1000 ImageCAS CCTA volumes** (512 × 512 × 206–275, ~0.29–0.45 mm,
  near-isotropic), held on the project's Girder server, already ingested into
  SegQueue. ImageCAS ships one merged binary lumen mask per case; per-branch
  labels are produced by our annotators and do not exist yet.

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
patches around 128³ (~2 M voxels); ~70 GB buys roughly 256³–288×288×224
(~17–20 M voxels) at batch 2, which is **~27–30 % of a full volume — clear of
nnU-Net's 12.5 % cascade trigger with no cropping at all**. A ~90 mm patch
landing near the mediastinum contains most of the coronary tree plus the
aortic root and both ostia — the context that separates LAD from LCx.

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
GPU: (a) patch fraction ≥ 12.5 % so no cascade is planned; (b) target spacing
came out native, not dragged coarse by thick-slice outliers; (c) batch size 2.
The ~256³ figure above is scaling arithmetic; the planner's number is the real
one.

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
the contribution. The contribution is the per-branch labelling.

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
Calibration: published binary lumen Dice is 0.82–0.85 and inter-observer
agreement ≈ 0.856 — the ceiling, not a target. Per-branch inter-rater agreement
from the annotation overlap set becomes the multiclass ceiling once measured.

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

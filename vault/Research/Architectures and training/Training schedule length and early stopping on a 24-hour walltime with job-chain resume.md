---
tags: [research/architecture, training-schedule, convergence, nnunet, walltime]
status: solid
updated: 2026-09-20
aliases: [Training iterations, Early stopping, Convergence]
---

# Training schedule length and early stopping on a 24-hour walltime with job-chain resume

[[Training plan]] fixes 24-hour walltime on one H100 80 GB with job-chain resume capability. nnU-Net's default schedule runs ~250,000 mini-batch iterations (1000 epochs × 250 mini-batches per epoch); this note examines whether that schedule is reachable in 24 h on our VRAM budget and what is lost if training stops early.

## nnU-Net's schedule and convergence criteria

Verified in nnU-Net source (nnUNetv2, master branch, 2026):

- **Default training duration**: up to 1000 epochs, or 250,000 mini-batch iterations, with **early stopping if validation loss does not improve by ≥5×10⁻³ within the last 60 epochs**, but not before learning rate drops below 10⁻⁶.
- **Learning rate schedule**: Nesterov SGD (momentum 0.99), polynomial decay from 0.01 to 0 over all iterations: `lr = 0.01 × (1 - (epoch / 1000))²`.
- **Validation frequency**: every 50 training iterations.

Early stopping is thus **loss-based, not iteration-based**, and the final number of iterations depends on dataset and model convergence behavior.

## Measured schedules on comparable datasets

Two relevant measurements:

**ImageCAS binary lumen model (Zeng et al., CMIG 2023)**:
- Trained on RTX 3090 (24 GB VRAM) with patch size ~128³.
- Stopped at **~21,000 iterations** (reported in Training plan §3).
- Published Dice: 82.96 % (benchmark against ~83 % inter-observer on CCTA).
- No statement of whether this was early-stopped or reached nnU-Net's convergence criterion.

**nnU-Net Revisited benchmark suite (Isensee et al., Nat Methods 2021)**:
- Typical datasets: KiTS (kidney, ~300 cases, 3D CT), AMOS (multi-organ, ~415 cases, 3D CT), LFCC (liver, ~130 cases, 3D CT).
- Iteration counts not explicitly stated, but implied by "up to 1000 epochs" language.
- No measurement of how many actually reached 1000 epochs vs stopped early on validation plateauing.

## What happens if training stops early?

The vanishing-gradient literature (Li et al. deep supervision review, 2022) notes that very deep networks benefit from deep supervision precisely because standard networks trained with a single final-layer loss can converge slowly, with early stopping potentially cutting off refinement phases.

No measured comparison exists on coronary CCTA specifically. However, two qualitative observations:

1. **ImageCAS's 21 k iterations is 8.4 % of nnU-Net's nominal 250 k schedule**. The published Dice is at or near the inter-observer ceiling (0.8296 vs ~0.856 agreement), suggesting either (a) that dataset has early saturation, or (b) stopping at 21 k was arbitrary and not the convergence point.

2. **Multiclass segmentation typically requires more iterations than binary**. Adding 10–15 classes to the task increases the label space entropy and typically lengthens convergence; no direct measurement on coronary exists, but medical-imaging transfer-learning literature (Kandel & Castelli, 2019 survey) notes class-count as a confound on convergence speed.

## The 24-hour budget constraint

On H100 80 GB with 70 GB budgeted (patch ~280³ at batch 2):
- nnU-Net v2 on typical 3D datasets reports **~0.5–1 second per iteration** (varies by patch size, number of classes, encoder depth).
- At 0.75 sec/iteration (middle estimate): 250 k iterations = **52 hours**, exceeding the 24-hour wall.
- At 1 sec/iteration: 250 k iterations = **69 hours**.

**The default schedule is not reachable in one 24-hour block.** The plan's job-chain resume is thus not a convenience—it is a **hard requirement** to reach convergence.

## Strategy: Multi-block training and resumed checkpoints

nnU-Net's trainer saves the best validation checkpoint and a "latest" checkpoint at every validation (every 50 iterations). Job-chain resume works by loading the "latest" checkpoint and continuing from that epoch:

```
# Submitted as a job chain:
Job 1 (24h): python -m nnunetv2.run.run_training <task> 3d_fullres <fold> -device cuda
Job 2 (24h): python -m nnunetv2.run.run_training <task> 3d_fullres <fold> -device cuda
  # nnU-Net auto-detects and loads latest checkpoint; continues from that epoch
```

The trainer will **resume from the last epoch, not re-start**; training loss and learning rate are preserved.

### Iteration count under multi-block training

If the first 24 h job completes ~120 k iterations (160 sec/iteration × 120 k ÷ 86400 sec ≈ 24 h), and the second job completes another ~120 k, the total is ~240 k iterations over 48 h of walltime, meeting the convergence criterion. **The binary model (21 k iterations) could complete in a single 24-hour block**, but the multiclass model likely needs two blocks; this should be measured on the first GPU submission.

## Early stopping risk: undershooting the plateau

The convergence criterion (validation loss stops improving by ≥5×10⁻³ within 60 epochs) is **loss-dependent, not Dice-dependent**. For a multiclass model with rare classes, validation loss can plateau on the common classes while rare-class Dice is still rising. Stopping at the first plateau thus risks undershooting final per-class performance.

No measurement on coronary; airway literature (Kirchhoff et al. skeleton recall paper) notes that multiclass pipelines often show per-class convergence at different epochs, and stopping by mean validation loss can leave rare classes behind.

## What this implies for [[Training plan]]

1. **The binary model should be trained first and will likely complete in a single 24-hour block** (21 k iterations is 8 % of nnU-Net's default). Measure actual runtime and record it.

2. **Budget two 24-hour blocks for the multiclass baseline.** Do not stop at the first completion; continue into the second block until early-stopping fires (validation loss plateaus for 60 epochs) or all 250 k iterations complete, whichever comes first.

3. **Add a per-class validation monitor** if rare branches start at zero Dice. If rare-class Dice continues rising while mean validation loss has plateaued, note this disagreement and extend another 24-hour block beyond the loss-based early stop. This is an exception to the default criterion, not the plan.

4. **Record actual epoch and iteration count at completion** in the run notes, along with the per-class validation Dice trajectory near the stopping point. This is the evidence needed to decide if a third block would improve rare-class performance.

## What this implies for [[Proposed changes]]

- Clarify §2 gate (c) to state: "batch size 2; if the 70 GB patch does not reach ≥250 k iterations in two 24-hour blocks, reduce patch size incrementally until completion target is reachable."
- Add to evaluation section: "Per-class validation Dice trajectory recorded at every 500 epochs, up to stopping; if rare classes (≤50 voxels per case on average) show continued improvement past mean-loss early-stopping point, a third 24-h block may be warranted — decision deferred to the specific run."

Collected in [[Proposed changes]].

---
aliases: [icx14 job 2]
tags: [plans, experiment, trillium, icx14, bug]
status: historical (icx14 cancelled, D25)
updated: 2026-10-15
---

# icx14 job 2: restarted from scratch (resume bug); R-PLA appears at ~epoch 440

> **Historical.** D25 (2026-10-17) reversed the 14-class schema; the icx14 run was cancelled and
> `trillium/icx4` trains the 4-class model with the same recipe. These numbers are the record. icx14's
> LM/LAD/LCx/RCA Dice are 14-class *trunk* scores (side branches are separate classes), so they are
> not directly comparable with icx4's territory classes, which include the side branches.
> The resume fix below is carried into `trillium/icx4/lib/job_body.sh`.

Results: `trillium-results/icx14/job2/results/` (both training logs, slurm logs, progress.png).
Follows [[icx14 - interim check after job 1 (446 epochs), side branches not yet learned]].

**What happened.** Job 2 (1078871) ran its full 23.3 h but printed `training from scratch` and began again
at epoch 0 with learning rate 0.01. It stopped cleanly at epoch 455. Job 1's 446 epochs were overwritten,
so about 23 GPU-hours were lost.

**Cause.** nnU-Net v2 deletes `checkpoint_latest.pth` when it writes `checkpoint_final.pth`
(`nnUNetTrainer.on_train_end`). The resume test in `trillium/icx14/lib/job_body.sh`
(`ls checkpoint_{latest,final}.pth`) required **both** files, so after a clean deadline stop it found
nothing to resume. The CPU self-test runs only one chunk, so it never exercised a resume.
**Fix:** resume when either file exists. Job 3 would otherwise have restarted a third time.

**Second run, epoch 455** (no class weights; the `class-weighted CE` line is absent from the log):

| | LM | LAD | LCx | RCA | R-PLA | other 9 side branches |
|---|---|---|---|---|---|---|
| job 1, ep 446 | 0.89 | 0.91 | 0.83 | 0.93 | 0 | 0 |
| job 2, ep 455 | 0.90 | 0.90 | 0.86 | 0.93 | **0.73** (non-zero from ~ep 440) | 0 |

Side branches unlock one at a time, as the main vessels did, but slowly. 545 epochs remain (about 27 h,
two chunks). **Recommendation:** fix the resume test, enable `$W/ce_class_weights.json` (weight 4 on the ten
side branches), and then release jobs 3 and 4.

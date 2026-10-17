---
aliases: [icx14 interim]
tags: [plans, experiment, trillium, icx14]
status: in progress
updated: 2026-10-13
---

# icx14 interim check after job 1 (446 of 1000 epochs)

Results: `trillium-results/icx14/results/` (training log, plans, label census). Job 1 ran 23.2 h, 181 s/epoch,
stopped cleanly at epoch 446 before its walltime as designed; jobs 2–4 of the chain continue it (`--c`).
No predictions or test scores yet (those come after epoch 1000).

**Validation pseudo-Dice (mean of the last 20 epochs):** LM 0.91, LAD 0.91, LCx 0.85, RCA 0.93 — and
**exactly 0 for all ten side-branch classes** (D1, D2, OM1, OM2, IM, R-PDA, R-PLA, L-PDA, L-PLA, Other) in
every one of the 446 epochs, although D1 is present in 631 of 640 training cases.

Classes "unlock" one at a time: LAD and LCx at ~epoch 50, RCA by ~100, LM by ~200. So the model learns the
four territories and labels every side branch as its parent vessel.

**Not a data bug.** nnU-Net's own resampling to 0.5 mm keeps every class (e.g. case 1: D1 2,839 → 1,598
voxels, LM 1,985 → 1,120); side branches are about as large as LM, which the model did learn. The difficulty
is that a side branch is indistinguishable from its parent locally — only its position in the tree names it —
and the cross-entropy majority (the parent) wins early.

**Plan.**
1. Check the live log of job 2 (~epoch 600+): if side-branch Dice has started to rise, let the chain finish.
2. If still 0, switch on class-weighted cross-entropy for the next chunk without restarting:
   `$W/ce_class_weights.json` = background and the four main vessels 1, every side branch 4 (the trainer reads
   it at the start of each chunk; tested on CPU). Continue to epoch 1000.
3. If side branches still fail by ~epoch 800, fall back to a two-stage prelabel: this model's four
   territories (Dice 0.85–0.93) split into the 14 classes by a second model or by the rule namer
   (`segtrain.namer`), so annotators still get 14-class starting points.
4. The four-territory quality already supports prelabelling: annotators would at least get correct LM/LAD/
   LCx/RCA territories to subdivide.

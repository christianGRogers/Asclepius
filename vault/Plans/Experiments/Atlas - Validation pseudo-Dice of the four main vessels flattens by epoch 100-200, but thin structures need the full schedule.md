---
aliases: [Atlas R9 curves]
tags: [plans, experiment, round9, schedule, fir, icx4]
author: Atlas
round: 9
status: done
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
---

# Validation pseudo-Dice of the four main vessels flattens by epoch 100–200, but thin structures need the full schedule

**Question.** icx4 trains for 1000 epochs, about 52 GPU-h on Trillium and possibly more on Fir (see
[[Atlas - On Fir's 12-core share nnU-Net's loader may set the pace]]). Could a shorter schedule do as well?

**Method.** `experiments/Atlas/r9_curves.py` parses every nnU-Net training log returned from Trillium and reports
per-class validation pseudo-Dice as 20-epoch means. Output: `experiments/Atlas/r9_curves.json`. The logs:

- run 1: thick proxy, 4 classes, a **complete** 412-epoch poly schedule;
- run 2 B: 368 of 412 epochs;
- run 3 F0: warm start, 200 epochs;
- icx14 jobs 1 and 2: ImageCAS-X, 14 classes, stopped at epochs 446 and 455 with the LR still about 0.006.

For icx14, the LM/LAD/LCx/RCA columns are the 14-class main segments, without their side branches.

**Result** (20-epoch mean of val pseudo-Dice ending at that epoch):

| Run | ep 100 | ep 200 | ep 400 | final | epoch reaching 98 % of final (LM/LAD/LCx/RCA) |
|---|---|---|---|---|---|
| run 1 (412, complete) | .897/.830/.765/.828 | .898/.838/.771/.828 | .904/.847/.780/.833 | .903/.846/.778/.833 | 36 / 94 / 75 / 51 |
| run 2 B (368 of 412) | .893/.826/.762/.829 | .901/.838/.770/.831 | — | .908/.844/.778/.835 | 51 / 79 / 80 / 49 |
| icx14 job 1 (446) | –/.899/.819/.916 | .898/.905/.833/.924 | .906/.908/.847/.928 | .907/.910/.847/.929 | 153 / 80 / 158 / 83 |
| icx14 job 2 (455) | –/.900/.828/.921 | .898/.904/.834/.923 | .901/.909/.837/.926 | .903/.902/.833/.925 | 192 / 61 / 79 / 78 |

(– : that class was still at 0 when the window closed. In icx14 the LM "unlocks" late: at epoch ~130 in job 1 and
~170 in job 2.)

- **The 4-class runs gain little after epoch 100.** Run 1's complete schedule added +0.006 (LM), +0.016 (LAD),
  +0.013 (LCx) and +0.005 (RCA) from epoch 100 to 412. The LR tail did that, not the high-LR plateau: run 1 and run
  2 B are level at epoch 200.
- **icx14's main segments flattened by epoch ~200 with the LR still at 0.006.** In job 2 they did not rise between
  epochs 250 and 455.
- **The two icx14 runs differ by up to 0.014 on the same epoch range** (LCx, final 20). That is training noise of
  the size A22's σ_seed (0.013) describes.

**Why the plan still keeps 1000 epochs.**

1. **Pseudo-Dice is a patch-level foreground overlap.** It is dominated by the thick proximal vessel and is nearly
   blind to distal tips and gaps, which are what tF1 scores.
2. **The only measured from-scratch nnU-Net comparison of schedule length** (nnFoundation, arXiv:2609.26924, Table
   F30) shows thin tubes losing the most at 150 vs 1000 epochs: hepatic vessel 0.638 vs 0.669, inferior alveolar
   canal 0.560 vs 0.713, heart 0.925 vs 0.927
   ([[Atlas - The external evidence for a 4-class nnU-Net on ImageCAS-X, checked against the source texts]]).
3. **Fir has no hard deadline** (7-day jobs, a resumable chain), so the extra epochs cost queue time, not a
   decision.
4. **1000 epochs is what icx4 was built and tested with,** and what D25 sends to Fir.

**What it changes.**

- The schedule stays at 1000 epochs. `ICX4_EPOCHS=500` is kept as the **pre-registered fallback** if Fir's
  measured epoch time puts 1000 epochs beyond 5 chained jobs (5 × 23.6 h = 118 h less ~6 h of preprocessing and prediction, i.e. > 400 s/epoch). Jobs inherit the
  submitting shell's environment, so it needs no code change.
- The 0.014 job-to-job spread in icx14 is one more reason to run a **second seed** before any retrained decision
  (A22). [[Atlas v11]] §6 makes that Job B.

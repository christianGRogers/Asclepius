---
tags: [plans/experiment, bridge, janus-1f, icx14, D9, D25, round1]
author: Bridge
track: Janus 1-F
round: 1
updated: 2026-11-11
issue: christianGRogers/Asclepius#303
---

# In the cancelled 14-class run, no branch class was ever predicted, and classes appeared in order of size

## Question

The project already tried a direct 14-class network on ImageCAS-X (D9/D10, `trillium/icx14`) before D25 reversed it.
What did that run learn about branch classes before it was cancelled?

## Setup

- **No new compute.** `experiments/Bridge/j1f_r1/icx14_emergence.py` reads the two nnU-Net training logs returned from
  Trillium (`trillium-results/icx14/results/` and `job2/results/`) and the run's label census.
- **The run:**
  - nnU-Net v2 ResEnc, `nnUNetResEncUNetPlans_60G_iso05`, 0.5 mm, patch 256³, batch 2, mirroring off;
  - ImageCAS-X 14 classes as drawn, train 560 + val 80;
  - a 1000-epoch poly schedule.
- **Job 1 and job 2:** job 1 ran 446 epochs. Job 2 restarted from scratch after the resume fix and ran 456 epochs.
  D25 cancelled the chain there, so each attempt reached about 45 % of its schedule (about 23 GPU-h each).
- **The quantity:** the first epoch at which each class's validation pseudo-Dice (nnU-Net's per-epoch estimate on
  sampled val patches) is above 0.
  - 0.0 means the class was in the sampled patches and no voxel of it was predicted.
  - NaN means it was absent from the patches.

## Result (`experiments/Bridge/j1f_r1/icx14_emergence.json`)

| Class | Cases with it (of 640) | First epoch > 0, job 1 | First epoch > 0, job 2 | Pseudo-Dice at the last epoch, job 2 |
|---|---|---|---|---|
| LAD | 640 | 27 | 21 | 0.90 |
| LCx | 640 | 34 | 21 | 0.86 |
| RCA | 640 | 61 | 58 | 0.93 |
| LM | 630 | 130 | 172 | 0.90 |
| R-PLA | 589 | never | 424 (32 of 456 epochs > 0) | 0.73 |
| D1 | 631 | never | never | 0.00 |
| R-PDA | 594 | never | never | 0.00 |
| OM1 | 558 | never | never | 0.00 |
| D2 | 380 | never | never | 0.00 |
| OM2 | 243 | never | never | 0.00 |
| IM | 147 | never | never | 0.00 |
| Other | 76 | never | never | 0.00 |
| L-PLA, L-PDA | 59, 38 | never | never | 0.00 / NaN |

## What it shows, and what it does not

- **Classes emerge in order of voxel share, not case frequency:**
  - the large trunks emerge by epoch 20–60 and the short, thick LM by about 150;
  - one branch class appears only at epoch 424;
  - D1 is in 99 % of cases and never appears.
- In a from-scratch 18-way softmax, the trunks absorb their branches first, and separating the branches is late
  learning.
- **It does not show that branches cannot be learned.** The schedule was cut at 45 %, and R-PLA was just appearing.
  It shows that a from-scratch multi-class run spends **more than 23 GPU-h before its first branch class**. That
  attempt was paid twice.

## What it changes (Bridge v1, Janus 1-F)

- **Warm-start from Janus 0:** the trunks are already learned.
- **Initialise each branch channel from its parent's channel**, so a branch starts as "vessel" and learns only "which
  one".
- **Pool the ordinals into types** (DIAG = D1 + D2 + D3), which raises each type's voxel share. The ordinal is assigned
  by origin order afterwards (see
  [[Bridge - On the 620 training cases ImageCAS-X's ordinal branch names follow origin order along the parent]]).
- **Print per-type pseudo-Dice in `status`.** A type still at 0 by epoch 100 of a warm start is reported, rather than
  discovered at the end.

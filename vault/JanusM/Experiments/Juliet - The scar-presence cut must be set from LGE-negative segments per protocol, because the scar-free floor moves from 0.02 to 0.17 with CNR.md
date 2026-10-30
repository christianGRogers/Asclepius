---
tags: [janus-m, experiment, scar, lie, threshold, phantom, path-b]
author: Juliet
round: 2
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#143
code: experiments/JanusM/Juliet/scar_head.py
---

# E7: the scar-presence cut must be set from LGE-negative segments per protocol, because the scar-free floor moves from 0.02 to 0.17 with CNR

## Question

The scar head is two stages:
1. **Presence:** segment scar-present if its transmural extent T ≥ τ.
2. **Kim bin:** on T, if present.

Juliet R1 E3 found that scar-free walls read 4–12 % transmural and suggested τ ≈ 0.15. With the depth-binned extent
of E6, what does a scar-free segment read, and what τ should the head use?

## Method

Re-scoring only. `scar_head.py` reads `e6_registration.json` and opens no case; `guard_r2.gate()` runs first.
Output: `e7_scar_head.json`.
- For each registration method and condition, all segments are pooled over 4 seeds: 72 segments, 16 of them scarred.
- τ ∈ {0.03, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20}.
- Reported: sensitivity, specificity, bin accuracy on scarred segments, and quadratic-weighted κ (5 classes).
- The 99th percentile of T in truly scar-free segments (the "floor") is reported too.

## Result

Heart-masked registration (R2), or no registration at d = 0. "Floor" is the p99 of T in scar-free segments.
Sensitivity / specificity are shown at τ = 0.10 and τ = 0.15.

| Condition | Floor | MAE of T, scarred | τ 0.10 | τ 0.15 | Best τ in grid |
|---|---|---|---|---|---|
| C 60, noise 15, d 0, R0 | 0.03 | 0.02 | 0.94 / 1.00 | 0.75 / 1.00 | 0.05–0.08: 1.00 / 1.00 |
| C 60, noise 15, d 4, R2 | 0.03 | 0.03 | 1.00 / 1.00 | 0.81 / 1.00 | 0.05–0.10: 1.00 / 1.00 |
| C 60, noise 15, d 8, R2 | 0.03 | 0.03 | 1.00 / 1.00 | 0.75 / 1.00 | 0.05–0.10: 1.00 / 1.00 |
| C 40, noise 20, d 0, R0 | 0.10 | 0.03 | 1.00 / 0.98 | 0.81 / 1.00 | 0.10–0.12 |
| C 40, noise 20, d 0, R2 | 0.17 | 0.03 | 1.00 / 0.84 | 0.88 / 0.95 | 0.15: 0.88 / 0.95 |
| C 40, noise 20, d 4, R2 | 0.10 | 0.04 | 1.00 / 0.98 | 0.88 / 1.00 | 0.12: 1.00 / 1.00 |
| C 40, noise 20, d 8, R2 | 0.10 | 0.04 | 1.00 / 0.98 | 0.94 / 1.00 | 0.12–0.15 |
| C 60, noise 15, 5 % phase change, R2 d 4 | 0.12 | 0.07 | 0.69 / 0.96 | 0.69 / 1.00 | none: bins on scarred segments 0.38–0.56 at every τ |

1. **The floor is a property of the protocol, not a constant.** It is 0.02–0.05 at C = 60 HU with noise 15 HU, and
   0.10–0.17 at C = 40 HU with noise 20 HU. The depth-binned extent removes most of R1 E3's 4–12 % spill floor at
   good CNR, but not at poor CNR.
2. **A fixed τ = 0.15 loses 6–25 % of the smallest (1–25 %) scars** even with perfect registration (sensitivity
   0.75–0.94). The best τ sits just above the floor: 0.05–0.10 at good CNR, 0.12–0.15 at poor CNR.
3. **Given presence, the bins are right.** MAE of T on scarred segments is 0.02–0.04 under R2 without a phase
   change. The bin errors seen are all near-misses of the 1–25 % scars at the presence step.
4. **A phase mismatch defeats every τ** (E6). It is handled by the data requirement, not by the head.

## What it changes

- **Stage 1 of the scar head:** τ = the 99th percentile of T over **LGE-negative segments** of the calibration
  third, computed per scanner protocol (energy mode and delay) when a protocol has ≥ 15 calibration patients, and
  pooled otherwise. τ is then fixed, and the validation third is scored once.
- **Stage 2:** Kim bin of T, with no further tuning.
- **The learned head stays conditional** (Juliet v2 §8.3). The rule head misses only the smallest scars at the
  presence step, and that is a calibration problem.
- **Limits.** 16 scarred segments per condition, so these are point estimates on a phantom. The real floor depends
  on beam hardening, partial volume at the apex and microvascular obstruction, which the phantom lacks.

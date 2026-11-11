---
tags: [plans/experiment, janus1-l, D45, locked100, power, non-inferiority]
author: Bridge
round: 1 (track 1-L)
updated: 2026-11-11
issue: christianGRogers/Asclepius#302
code: experiments/Bridge/j1l_r1/locked100_power.py
---

# On the locked 100 a paired decision resolves 0.011–0.020 tF1, so 60 more cases cannot be shown to help, and Janus 1-L is adopted on non-inferiority

**Question.** Janus 1-L is decided on the 100 locked cases (D45) by a paired comparison with Janus 0. How small a
difference can 100 cases resolve? How large a gain should 560 → 620 training cases give? And how often does a
pre-registered rule adopt a model that is equal, better or worse?

## Data

No new scoring. Everything is already in the repository, on ImageCAS val 80, with the A1c-pinned tF1 and
TotalSegmentator aortas.

- **The shape of "a new model minus its parent", per case and class:**
  - atlas2 B − run 1: two from-scratch trainings (`trillium-results/round6/atlas2`);
  - atlas3 F1 − F0: two warm fine-tunes from one checkpoint (`trillium-results/round7/atlas3`).

  Both are D0-era (thick-reference) models, so only their **shape** is used. Each is centred to mean 0, per class
  and per case macro, then shifted by a chosen true effect.
- **Replicate noise (a2 − a1):** F1 − F0 on the same case. It is the only measured warm replicate.
- **Scaling to Janus 0's spread.** Janus 0's per-case SDs are recovered from its CIs (Round 10: LM 0.121, LAD 0.126,
  LCx 0.135, RCA 0.079). Each class column is scaled by Janus 0's SD over run 1's (LM 1.49, LAD 1.61, LCx 1.22,
  RCA 1.00).
- **Four scenarios,** by the SD of the per-case macro Δ:

  | Scenario | SD of per-case macro Δ |
  |---|---|
  | optimistic: warm-replicate shape | 0.038 |
  | central: scratch-pair shape | 0.041 |
  | pessimistic: scratch shape × Janus 0 spread | 0.051 |
  | harsh: Atlas's Round 10 upper bound | 0.072 |

- **Simulation:** n = 100 cases drawn with replacement from the 80 rows, percentile bootstrap (B = 1000), 2000
  simulated studies per cell.

**The rule simulated** (Bridge v1 §4):
- **L1:** the lower 95 % bound of macro Δ(a1 − Janus 0) is above −m.
- **L2:** no class's mean Δ is below −0.03.
- **L4:** the replicate a2's macro Δ point estimate is above −m.
- **ADOPT** = L1, L2 and L4.
- **BETTER** = ADOPT, and the lower bound is above 0.

L3 (centreline recall) and L5 (FP) are not simulated: the old files lack some of their rows.

## Results

**Minimum detectable effect** (paired, 80 % power, two-sided 5 %, n = 100): 0.011 (optimistic), 0.011 (central),
0.014 (pessimistic), 0.020 (harsh).

**What 60 more cases should buy.** Suppose decisive error 1 − tF1 follows a power law in training-set size.
Hestness et al. 2017 (arXiv:1712.00409) measure exponents between −0.07 and −0.35 across domains, and −0.309 for
ImageNet top-1 error (§ image classification, Figure 4). Going from 560 to 620 cases at Janus 0's error of 0.091
then gives:

| Exponent | −0.07 | −0.128 | −0.309 | −0.5 (the classical rate) |
|---|---|---|---|---|
| Expected gain in macro tF1 | 0.0006 | 0.0012 | 0.0028 | 0.0045 |

**Operating characteristics at m = 0.015** (share of simulated studies; full grid for m = 0.010 / 0.015 / 0.020 in
`locked100_power.json`):

| True effect | ADOPT: optimistic | central | pessimistic | harsh | BETTER: central | pessimistic |
|---|---|---|---|---|---|---|
| −0.03, all classes | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| −0.02 | 0.000 | 0.002 | 0.000 | 0.002 | 0.000 | 0.000 |
| −0.01 | 0.279 | 0.245 | 0.151 | 0.090 | 0.000 | 0.000 |
| 0 | **0.980** | **0.940** | **0.760** | 0.466 | 0.034 | 0.018 |
| +0.005 (the high end of data scaling) | 0.997 | 0.995 | 0.938 | 0.730 | **0.265** | **0.146** |
| +0.01 | 1.000 | 0.999 | 0.992 | 0.881 | 0.684 | 0.451 |
| +0.02 | 1.000 | 1.000 | 0.999 | 0.986 | 0.995 | 0.945 |
| LCx alone −0.05 (macro −0.0125) | 0.007 | 0.014 | 0.029 | 0.031 | 0.000 | 0.000 |

At zero true effect, BETTER fires in 1.6–3.4 % of studies, close to its nominal 2.5 %. The simulation is
calibrated.

**Other margins:**
- **m = 0.010** fails a neutral model too often: it adopts it only 0.42–0.82 of the time outside the harsh case.
- **m = 0.020** adopts a model that is truly −0.01 worse in 0.24–0.81 of studies.
- **m = 0.015** is the one margin that adopts a neutral or slightly better model at least 0.76 of the time in
  every scenario but the harsh one. It almost never adopts a model that is −0.02 worse.

## What it changes

1. **"Better than Janus 0" cannot be the adoption test for a 620-case model.** Even at the generous end of data
   scaling (+0.005), the locked 100 shows superiority in only 15–28 % of studies. A superiority gate would keep
   Janus 0 most of the time even when Janus 1-L is better. That outcome would read as "Janus 1-L failed" when it had
   not.
2. **Adoption is non-inferiority with a margin of 0.015, guarded per class (−0.03) and by a replicate.**
   - Janus 1-L's training set is a superset of Janus 0's, so there is a prior reason to prefer it.
   - The locked 100 is asked the question it can answer: is it detectably worse?
   - **"Better" is reported only when the lower bound clears 0.** This follows the CONSORT reporting rule for
     non-inferiority designs: margin and analysis pre-specified, and superiority claimed only from the same CI
     (Piaggio et al. 2012, JAMA 308:2594, doi:10.1001/jama.2012.87802).
3. **The class guard catches a single-class regression.** If LCx alone loses 0.05, the macro falls only 0.0125,
   inside the margin. L2 still stops adoption in 97–99 % of studies.
4. **The harsh case is the plan's weak point.** If Janus 1-L's per-case Δ against Janus 0 is as wide as 0.072 SD, a
   neutral model is adopted only half the time. The two measured pairs put the SD at 0.038–0.041, so this is a
   bound, not an expectation. The decision job reports the measured SD of Δ, so Round 2 knows which column it was
   in.
5. **Effects under about 0.01 are not tested on the locked 100 at all:** epochs, LR arm, augmentation details, a
   loss tweak. Each such recipe choice is fixed by a pre-registered default, not by a look at the 100.

## Limits

- The difference shapes come from D0-era models scored against the thick reference. Only their spread is carried
  over, and it is bracketed by four scenarios.
- The 80 rows are resampled to 100. The 20 open-36 cases in the locked set may be a little easier (Janus 0: 0.919
  on open-36 against 0.909 on val), which narrows the spread slightly.
- The power-law gain is a prior from other domains. Nothing in this repository measures a segmentation learning
  curve.
- `--janus0`-style exact rows would replace the scaled SDs. Janus 0's per-case file is on Fir
  (`$SCRATCH/icx4/r9_tf1_val.json`), not in the repository. The decision job measures the real SD of Δ in any case.

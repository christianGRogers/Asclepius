---
tags: [plans/experiment, round10, A10, D6, D27, A31, D35, A22, power, janus0]
author: Delta
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# On Janus 0's own spread, a 150-patient seal passes a human-level model 80 % of the time, and the correlation between model and reads matters more than f or k

**Question.**
1. Re-powered on Janus 0's per-case val spread (A31.1), is a 150-patient seal enough for A10 (D6: per class, all four, margin 0.05), or should it grow toward 200–250 (D27)?
2. What does a D35 decision set of n patients resolve in a paired fine-tune comparison under A22's seed term?

**Method.** `experiments/Delta/r10/power_r10.py` (CPU, about 10 s; output in `power_r10.json`).

- **Janus 0's per-case val tF1 is on Fir, not in the repository.** The script therefore builds a **surrogate**:
  - start from run 1's real per-case shape (atlas2 `per_case_run1.json`, unflagged, which keeps the heavy tail);
  - map it per class to Janus 0's decisive mean;
  - scale it to the SD implied by Janus 0's 95 % bootstrap CI, SD = width × √n / 3.92 (#43).
- The result: LM 0.121, LAD 0.126, LCx 0.135, RCA 0.079. Run 1 had 0.081, 0.078, 0.111, 0.079.
- `--real $SCRATCH/icx4/r9_tf1_val.json` gives the exact answer from the lead's file (command in Delta v10 §8).
- **A10 is Bridge's simulation, unchanged** (`experiments/Bridge/wave1/power.py`). The same code on run 1's spread reproduces Bridge's 0.97 at n = 150.
- **Added: ρ.** In Bridge's model a patient's model-vs-read and inter-read are independent draws (ρ = 0). A mixture copula reuses the case index with probability ρ.
- **The decision set:** MDE = 2.8 · √(SD²_pair/n + σ²_seed/seeds). SD_pair = 0.041 macro is the real paired SD of two retrained models (atlas2 B − run 1, 80 val cases). σ_seed = 0.013 (A22).

## Result 1: the seal

P(all four classes pass | the model is exactly as good as a second reader), scorable share as on Janus 0's val (LM 0.975, RCA 0.94):

| Spread | k | n = 150 | 175 | 200 | 228 | 250 |
|---|---|---|---|---|---|---|
| Run 1 (Bridge, Round 9) | 1 | 0.97 | | 0.99 | | |
| **Janus 0, f = 1** | 1 | **0.80** | 0.88 | 0.93 | 0.96 | 0.98 |
| Janus 0, f = 1 | 1.2 | 0.70 | 0.80 | 0.87 | 0.92 | 0.94 |
| Janus 0, f = 1.2 | 1 | 0.56 | 0.67 | 0.77 | 0.84 | 0.88 |
| Janus 0, f = 1.5 | 1 | 0.26 | 0.35 | 0.46 | 0.53 | 0.60 |
| Janus 0, f = 1, **ρ = 0.3** | 1 | **0.95** | 0.97 | 0.99 | 0.995 | 1.00 |
| Janus 0, f = 1.2, ρ = 0.3 | 1 | 0.80 | 0.87 | 0.92 | 0.96 | 0.98 |
| Janus 0, f = 1, ρ = 0.5 | 1 | 0.99 | | 1.00 | | |

- Per class at f = k = 1 and n = 150, LCx is the binding class (0.905), then LM (0.924).
- At δ = −0.02 (the model 0.02 worse than a reader), P is 0.16 at 150 and 0.38 at 228. A10 then becomes a test that only a model better than a reader is sure to pass.
- **Janus 0 is a better model than run 1 with a wider per-case spread.** Its mean is higher, but a few cases score near 0 (a cut LM, a missed LCx). That tail is what costs power: on Janus 0's spread, Bridge's own model puts 150 exactly at the 0.80 line.
- **ρ moves power more than f or k do.** ρ = 0.3, which is plausible if the patients that are hard for the model (poor contrast, a tiny LM) are also hard for two readers, buys about as much as going from 150 to 228 patients. ρ is not measured anywhere yet. Wave 1 measures it, together with f and k, the moment it scores the contrast d = model-vs-read − inter-read per patient.

## Result 2: the decision set (macro tF1, 80 % power, two-sided 0.05)

| n (decision patients) | Case term only | A22, one seed per arm | A22, two seeds per arm | σ_seed halved (warm fine-tune, assumed), one seed |
|---|---|---|---|---|
| 25 | 0.023 | 0.043 | 0.035 | 0.029 |
| **35** | 0.019 | **0.041** | **0.032** | 0.027 |
| 50 | 0.016 | 0.040 | 0.030 | 0.024 |
| 80 | 0.013 | 0.039 | 0.029 | 0.022 |

With f = 1.5, every entry rises by 0.003–0.010.

- **Seed noise, not decision-set size, is what limits a fine-tune decision.** Going from 35 to 50 patients buys 0.001–0.002. A second seed per arm buys 0.009.
- This is a macro, paired, retrained-arm question, so the macro paired SD is the right quantity here. That is unlike Round 9's seal sizing, where Delta v9 used it wrongly for a per-class A10 contrast (Round 9 scorecard). For per-class A10 the right quantity is the contrast d, above.
- Fine-tunes from one base may have a smaller σ_seed than from-scratch training. That is unmeasured; the first fine-tune decision measures it (A22, D28's fallback).

## What it changes

- **150 is not safely enough on Janus 0's spread, but whether to extend depends on ρ, which wave 1 measures.**
  - Extending now, on the ρ = 0 assumption, would spend 50–78 training patients against a risk that one measured number could remove.
  - Delta v10 therefore keeps the seal at 150 until wave 1. It then re-powers on the measured per-patient contrast (`repower_contrast.py`), weighted to the seal's source mix.
  - It extends to the smallest of 175/200/228 whose lower 80 % bootstrap bound of P(pass | human level) is at least 0.80.
  - This would replace Bridge's "f or k > 1.2" trigger, which fires by chance 54 % of the time at 50 patients and cannot see ρ. That is the judge's call. Until the judge rules, A31.1 applies as written, and both are reported.
- **D35 = 35 patients is enough.** Decisions with effects under about 0.03 need two seeds per arm, as A22 already says.

## Limits

- The surrogate takes Janus 0's per-class SD from bootstrap CI widths computed under the expert ostia (Delta's run). Under A1's TotalSegmentator ostium the macro SD is wider (0.117 against 0.093), because the left-ostium residual adds tail. So the left-class SDs here are, if anything, low, and power at 150 slightly high.
- The `--real` run on Fir settles this exactly.
- Inter-read spread (k) and ρ are scenarios until wave 1.

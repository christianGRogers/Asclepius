---
aliases: [Kilo E6]
tags: [janus-m, experiment, power, paired-cohort, lge, transmurality, kilo, paired-scar]
status: done
round: 2
path: jm/paired-scar
updated: 2026-10-30
code: experiments/JanusM/Kilo/e6_power.py
---

# Kilo E6: a paired CT–LGE cohort needs about 120 patients, and weighted kappa over all segments cannot size it

**Question** (Round 1 ruling §6 item 8). Path B validates CT scar against CMR LGE segment by segment: scar presence,
then the Kim transmurality bin (0; 1–25; 26–50; 51–75; 76–100 %). How many paired patients does that need, which
statistic should set the size, and how much does the CT grading error matter?

**Method.** `e6_power.py`, a CPU simulation with no image. Seed 20261030; 200 cohorts per cell, each with a 200-draw
patient bootstrap.

- **Cohorts:** N patients × 17 AHA segments.
  - 70 % of patients have one chronic infarct in one territory of the standard AHA map: LAD 50 %, RCA 30 %, LCx 20 %.
    The map is verified from secondary sources only (JA14).
  - An infarct covers 1 + Binomial(n_territory − 1, 0.45) segments of that territory.
  - True LGE transmurality is Beta(1.6, 1.6).
- **CT detection:**
  - It is logistic in the true transmurality, so small scars are missed.
  - The false-positive rate is set so segment sensitivity is **0.84** and specificity **0.98**. These are the pooled
    LIE-vs-LGE values (Gatti 2025: 0.86 / 0.98, 14 studies, 526 patients).
  - A patient random effect (SD 0.8 on the logit) clusters errors within a patient.
- **CT grading of a detected scar:** T + b_patient (SD 0.05) + e_segment.
  - **sd_s** is the transmurality-measurement error, the quantity registration and border error set (E5). Grid: 0.08,
    0.13, 0.20.
- **Statistics, each with a 95 % patient (cluster) bootstrap CI.** Segments within a patient are not independent
  (Dixon 2016, a design-effect method for clustered kappa).
  - Linear-weighted kappa over all segments.
  - Segment sensitivity and specificity for presence.
  - **Kim-bin agreement among segments scarred on both CT and LGE ("transmurality agreement").**
- **Targets:**
  - weighted-kappa lower bound > 0.61 (Gerber 2006's segmental κ for late-enhancement CT vs CE-MR);
  - sensitivity lower bound > 0.75;
  - transmurality agreement known to ± 0.10.

Output: `results_e6_power.json`.

**Result.**

Large-cohort values (20 000 patients) by grading error:

| sd_s | weighted κ | sens | spec | exact bin, all segments | **transmurality agreement** |
|---|---|---|---|---|---|
| 0.08 | 0.856 | 0.846 | 0.982 | 0.934 | **0.734** |
| 0.13 | 0.833 | 0.843 | 0.982 | 0.922 | **0.630** |
| 0.20 | 0.804 | 0.846 | 0.981 | 0.909 | **0.520** |

Power and precision by cohort size, at sd_s = 0.13. At sd_s 0.08 and 0.20 the CI half-widths change by ≤ 0.015.
Power for transmurality ± 0.10 at 40 patients is 0.62 / 0.40 / 0.30 for sd_s 0.08 / 0.13 / 0.20, and sensitivity
power at 60 patients is 0.80 / 0.72 / 0.74.

| N patients | scarred segments | κ CI ± | P(κ lb > 0.61) | sens CI ± | P(sens lb > 0.75) | transmurality CI ± | P(± ≤ 0.10) |
|---|---|---|---|---|---|---|---|
| 20 | 45 | 0.065 | 0.99 | 0.106 | 0.37 | 0.148 | 0.07 |
| 40 | 91 | 0.045 | 1.00 | 0.076 | 0.62 | 0.104 | 0.40 |
| 60 | 136 | 0.039 | 1.00 | 0.065 | 0.72 | 0.085 | 0.88 |
| 80 | 183 | 0.032 | 1.00 | 0.054 | 0.89 | 0.074 | 1.00 |
| **120** | **272** | 0.027 | 1.00 | 0.045 | **0.95** | 0.061 | 1.00 |
| 160 | 361 | 0.023 | 1.00 | 0.039 | 0.99 | 0.053 | 1.00 |
| 240 | 543 | 0.019 | 1.00 | 0.032 | 1.00 | 0.043 | 1.00 |

**What it shows.**
1. **Weighted κ over all 17 segments is the wrong sizing statistic.** About 87 % of segments are scar-free and
   agree, so κ clears 0.61 with 20 patients at any grading error. It also barely moves when the transmurality
   error grows 2.5-fold (0.86 → 0.80). A study sized on it would be underpowered for the question that matters.
2. **Transmurality agreement among scarred segments is the statistic that responds to grading error.** It falls from
   0.73 to 0.52 as sd_s goes from 0.08 to 0.20. It is the primary scar metric on path B, with presence first.
3. **Segment sensitivity sets the size.** A lower bound above 0.75 with 95 % power needs **about 120 patients**
   (≈ 84 with infarct, ≈ 270 scarred segments). About 80 patients suffice to know transmurality agreement to ± 0.10.
4. **Within-patient clustering is weak in this model** (ICC of the CT-positive indicator 0.03). If real data clusters
   more, the cluster bootstrap widens the CIs and the size grows. The size is therefore re-powered on the first
   40 paired patients (Kilo v2 §4.4).

**Limits.**
- The LGE reference is treated as truth. LGE's own reader variability adds to the observed disagreement.
- Scar geometry and prevalence are assumptions (70 % infarct patients, one territory). A cohort with more scar-free
  patients needs more patients for the same number of scarred segments, so the requirement is stated in **scarred
  segments (≥ 270)** as well as in patients.
- Non-ischaemic (mid-wall, epicardial) scar is not modelled.

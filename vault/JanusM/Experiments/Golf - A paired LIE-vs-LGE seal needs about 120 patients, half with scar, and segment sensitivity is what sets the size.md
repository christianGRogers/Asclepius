---
tags: [janus-m, experiment, scar, LGE, LIE, power, sample-size, round2, paired-scar]
author: Golf
round: 2
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#143
code: experiments/JanusM/Golf/cohort_power.py
data: experiments/JanusM/Golf/cohort_power.json
---

# A paired LIE-vs-LGE seal needs about 120 patients, half with scar; segment sensitivity sets the size

## Question

Round 1 ruling §6 item 8 asks for the minimum size of a paired cohort for segment-level transmurality agreement
against LGE, and its power. Segments of one patient are not independent: one patient's image quality, heart rate
and scar pattern affect all 16 of their segments together. So the size must be counted in **patients**, and every
CI must be a patient bootstrap.

## Method

Monte Carlo, CPU, about 15 minutes. `cohort_power.py`; every number is in `cohort_power.json`.

**One simulated study:**
- **N patients.** A share `enrich` has LGE scar.
- **Scar patients.** Each has K = 1 + Poisson(λ) contiguous LGE-positive segments, out of 16 (segment 17 left out).
  Each positive segment's Kim bin is drawn over bins 1–4 with weights 0.30 / 0.25 / 0.25 / 0.20.
- **Grader (Janus-M on LIE).**
  - **Detection.** Detects a scar segment with probability 0.70 / 0.88 / 0.93 / 0.97 for bins 1–4. That is about
    0.84 pooled, close to the meta-analytic segment sensitivity of 0.86 (Gatti 2025: 14 studies, 526 patients,
    5758 segments; specificity 0.98).
  - **False calls.** Calls a scar-free segment positive with probability 0.02.
  - **Clustering.** A patient random effect with SD τ on the logit clusters errors within patients.
  - **Grading.** A detected segment is graded in its true bin with probability 1 − q, and one bin off otherwise.

**Endpoints, each judged once, on the lower bound of a 95 % patient bootstrap (400 resamples):**

| Endpoint | Passes if the lower bound is ≥ |
|---|---|
| Segment sensitivity for scar presence | 0.75 |
| Segment specificity | 0.93 |
| Linear-weighted kappa of the Kim bin over all segments | 0.60 |

**Power** is the share of 400 simulated studies that pass all three. Base case: enrich 0.5, λ 3, τ 0.7, q 0.25. The
Monte Carlo SE of each power figure is about ±0.02–0.03.

## Result

**Power to pass all three endpoints.** Specificity and kappa pass in ≥ 98 % of studies from N = 60 in every
condition except strong clustering. Sensitivity alone sets the size.

| N patients | enrich 0.3 | **enrich 0.5 (base)** | enrich 0.7 | base, τ 0 | base, τ 1.2 | base, λ 1.5 | base, q 0.40 |
|---|---|---|---|---|---|---|---|
| 30 | 0.34 | 0.46 | 0.53 | | | | |
| 40 | 0.41 | 0.56 | 0.67 | | | | |
| 60 | 0.44 | 0.62 | 0.82 | 0.85 | 0.36 | 0.53 | 0.71 |
| 80 | 0.60 | **0.80** | 0.87 | 0.92 | 0.45 | 0.65 | 0.79 |
| 100 | 0.66 | 0.87 | 0.94 | 0.97 | 0.52 | 0.69 | 0.85 |
| 120 | 0.78 | **0.89** | 0.98 | 0.98 | 0.57 | 0.79 | 0.91 |
| 160 | 0.83 | 0.97 | 0.99 | | | 0.88 | 0.95 |

**Point estimates (median over studies, base):** sensitivity 0.84, specificity 0.975, weighted kappa 0.85.

**One noise check.** q does not enter sensitivity, so columns "base" and "q 0.40" should agree. They do within the
Monte Carlo error at N = 80–160 (0.80 vs 0.79, 0.87 vs 0.85, 0.89 vs 0.91, 0.97 vs 0.95). At N = 60 they differ by
0.09, which shows how noisy a single cell is near the steep part of the curve. Read the table to about ±0.05.

## What it implies

1. **Sensitivity is the binding endpoint, so the number of scar segments decides the size.** A typical study in
   the meta-analysis has about 38 patients (526 / 14). Under these assumptions that gives roughly a coin-flip chance
   of a lower sensitivity bound ≥ 0.75. **A single-study-sized cohort cannot carry a seal claim.**
2. **Recommended paired seal: 120 patients, about half with LGE scar.**
   - That gives 0.89 power in the base case, and 0.79 if infarcts are small (λ 1.5).
   - **80 is the minimum for any seal claim** (0.80 base).
   - Below 80 the cohort is development-only, and scar outputs stay research outputs.
   - A **development set of ≥ 40 more patients** is added for calibration (Golf v2 §6.3), so the target total is
     **about 160**.
3. **Enrichment matters more than size.**
   - At 30 % scar patients, even 160 reaches only 0.83.
   - At 70 %, 60 patients reach 0.82.
   - The cohort should be enriched for prior infarction, but must keep at least 30 % scar-free patients, because
     specificity and the Stage A normal ranges need them.
4. **Clustering is the main unknown.**
   - If a patient's LIE quality varies strongly between patients (τ 1.2), sensitivity falls to 0.82 and power to
     0.57 at N = 120.
   - τ can be measured on the development set. The seal size is then **re-powered from the development set's
     measured τ and K before any seal patient is graded**, by rerunning this script with those values. It may grow
     and never shrinks, as on the trunk (JA6).
5. **Kim-bin kappa ≥ 0.60 is easy** (point estimate 0.85), so it is not what sizes the cohort. The harder question
   is whether the **LGE readers themselves** reach that agreement. Their inter-reader kappa is reported as the
   ceiling (Golf v2 §6.2).

**Limits.**
- Every parameter is an assumption. The detection-by-bin profile is chosen to pool near Gatti 2025's 0.86, not
  measured.
- Scar segments are contiguous by AHA index, which only approximates a coronary territory.
- 400 studies per cell gives a Monte Carlo error of about ±0.02–0.03.

## References

- Gatti M, et al. Diagnostic accuracy of late iodine enhancement on cardiac CT for myocardial tissue
  characterization: a systematic review and meta-analysis. *Eur Radiol* 2025;35:3054-3067.
  doi:10.1007/s00330-024-11283-5. PMID 39702631. Abstract: 14 studies, 526 patients, 5758 segments; segment
  sensitivity 0.86 (0.79–0.91), specificity 0.98 (0.96–0.99); patient-level 0.96 / 0.95.

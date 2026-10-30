---
tags: [janus-m, experiment, scar, lge, power, cohort, path-b]
author: Juliet
round: 2
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#143
code: experiments/JanusM/Juliet/cohort_power.py
---

# E5: 60 validation patients, half of them post-MI, give 93 % power for segment-level scar agreement with LGE; sensitivity limits it

## Question

On path B the scar output is validated against CMR late gadolinium enhancement (LGE), per AHA segment. The question
is how many paired patients that validation needs (the Round 1 ruling, §6 item 8). It also matters which endpoint
limits power, and how much enrichment for prior MI buys.

## Method

This is a simulation; no case is opened. `guard_r2.gate()` runs first. Output: `e5_cohort_power.json`.

**Truth, per patient (17 AHA segments).**
- A share *f*<sub>MI</sub> ∈ {0.5, 0.8} has a prior MI: one scar patch of 2–7 contiguous segments in one territory,
  using the standard AHA artery map (Cerqueira 2002; the territory figure is verified from secondary sources only,
  JA14).
- The others carry an unrecognised scar with probability 0.10, over 2–3 segments. **This is an assumption.** ICELAND
  MI found unrecognised MI on CMR in 17 % of 936 adults aged 67–93 (Schelbert 2012,
  [10.1001/2012.jama.11089](https://doi.org/10.1001/2012.jama.11089), abstract). A younger referral cohort is
  assumed lower.
- Each scarred segment's Kim bin is drawn with weights 0.30 / 0.25 / 0.20 / 0.25 for 1–25 / 26–50 / 51–75 / 76–100 %.
  **This is an assumption.**

**CT read model.**
- **Presence:** per-segment sensitivity 0.86 and specificity 0.98, as pooled for late iodine enhancement (LIE)
  against LGE over 14 studies and 5758 segments (Gatti 2025,
  [10.1007/s00330-024-11283-5](https://doi.org/10.1007/s00330-024-11283-5), abstract).
- **Correlation within a patient:** a patient-level random effect (logit SD 0.8, "image quality") correlates
  segments of the same patient.
- **Bin, given a detected scar:** correct with *p*<sub>bin</sub>; otherwise mostly one bin off.
- **False positives** read bin 1, or bin 2 with probability 0.2.

**Scenarios.**

| Scenario | Sensitivity | Specificity | *p*<sub>bin</sub> | Role |
|---|---|---|---|---|
| "published" | 0.86 | 0.98 | 0.65 | the expected pipeline |
| "weak" | 0.72 | 0.95 | 0.45 | a pipeline that should fail; its pass rate is the rule's false acceptance |

**Endpoints and the proposed success rule.**
- The endpoints are quadratic-weighted κ over 5 classes (no scar plus the 4 Kim bins), and segment sensitivity and
  specificity for scar presence.
- Each gets a 95 % CI from a patient-cluster bootstrap (B = 400).
- **Success:** the lower bound of κ<sub>w</sub> ≥ 0.60, **and** the lower bound of sensitivity ≥ 0.70, **and** the lower
  bound of specificity ≥ 0.90.
- Pass rate is computed over 300 simulated cohorts per cell.

For context, two small studies report segment-level agreement between CT late enhancement and MRI:
- κ = 0.85 by segment, with κ = 0.82 for transmural and 0.52 for subendocardial infarct type (11 patients; Wang 2011,
  [10.1016/j.ejrad.2010.01.007](https://doi.org/10.1016/j.ejrad.2010.01.007));
- weighted κ = 0.878 for enhancement pattern (28 patients; Mahnken 2005,
  [10.1016/j.jacc.2005.03.035](https://doi.org/10.1016/j.jacc.2005.03.035)).

Both are abstracts and both are acute reperfused MI. Gerber 2006 found κ = 0.61 for late hyperenhanced regions
(37 patients; [10.1161/CIRCULATIONAHA.104.529511](https://doi.org/10.1161/CIRCULATIONAHA.104.529511), abstract).
The 0.60 bar sits at the lower end of these.

## Result

**Pass rate** (the share of cohorts meeting all three bounds) by number of validation patients:

| Scenario | *f*<sub>MI</sub> | 30 | 45 | **60** | 90 | 120 | 180 |
|---|---|---|---|---|---|---|---|
| published | 0.5 | 0.71 | 0.80 | **0.93** | 0.97 | 1.00 | 1.00 |
| published | 0.8 | 0.83 | 0.94 | **0.99** | 0.99 | 1.00 | 1.00 |
| weak | 0.5 | 0.03 | 0.03 | 0.05 | 0.03 | 0.03 | 0.02 |
| weak | 0.8 | 0.03 | 0.05 | 0.02 | 0.04 | 0.02 | 0.03 |

**Published scenario, *f*<sub>MI</sub> = 0.5:** median 95 % CI half-widths and the expected number of scarred segments.

| N | Scarred segments | κ<sub>w</sub> ± | Sensitivity ± | Specificity ± |
|---|---|---|---|---|
| 30 | 68 | 0.081 | 0.094 | 0.015 |
| 60 | 132 | 0.057 | 0.068 | 0.011 |
| 90 | 198 | 0.047 | 0.057 | 0.009 |
| 120 | 264 | 0.041 | 0.049 | 0.008 |

Mean point estimates were κ<sub>w</sub> 0.85, sensitivity 0.83 and specificity 0.97. Sensitivity sits below 0.86
because the random effect is applied on the logit scale.

1. **Sensitivity is the limiting endpoint.** κ<sub>w</sub> passes in ≥ 97 % of cohorts at every N, and specificity in
   100 %. All of the shortfall in power is the sensitivity bound. That bound is set by the number of *scarred
   segments*, so it depends on enrichment more than on N.
2. **60 validation patients, half with prior MI, give 93 % power. 45 patients at 80 % prior MI give 94 %.** Below
   about 130 scarred segments, power falls under 90 %.
3. **The rule's false acceptance is 2–5 % at every N.** The "weak" pipeline sits on the sensitivity bound
   (true 0.70), so its pass rate is the rule's one-sided α. The rule is not lenient at large N.
4. **Stress CTP against invasive FFR (secondary).** With 40 % positive vessels, a per-vessel AUC of 0.80 has a 95 %
   CI half-width of 0.12 at 60 vessels, 0.085 at 120 and 0.06 at 240 (Hanley–McNeil). Vessels cluster within
   patients, so these widths are optimistic.

## What it changes

- **The cohort spec asks for ≥ 60 validation patients with LIE + LGE, ≥ 50 % of them with a documented prior MI**
  (Juliet v2 §8.1). An enrichment share is a data requirement, not a request.
- **A calibration subset comes first and is kept apart.** The LIE threshold rule and the presence cut τ (E7) are
  fixed on a separate calibration third, at least 30 patients. So **the total is ≥ 90 LIE + LGE patients**. The
  validation third is scored once, in the same way the Janus-M seal is.
- **The deciding endpoint is the triple bound, with sensitivity named as the binding one.** The judge can lower N
  only by raising enrichment.
- **Limits.**
  - The read model is a parametric stand-in. Its correlation (logit SD 0.8) and bin-error shape are assumptions.
  - The pooled 0.86 / 0.98 mixes energy-integrating and photon-counting CT, and acute and chronic MI.
  - The simulation re-powers nothing. Section 8.1 of the candidate states the re-powering step: on the calibration
    third, measure the scarred-segment yield and the intraclass correlation, then fix N for validation before
    scoring.

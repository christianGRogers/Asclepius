---
tags: [janus-m, experiment, round3, paired-scar, power, LGE, transmurality]
author: Golf
round: 3
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#179
code: experiments/JanusM/Golf/power_ja32.py
results: experiments/JanusM/Golf/power_ja32.json, experiments/JanusM/Golf/power_ja32_sweep.json
---

# Golf E10: at the JA32 bars the transmurality endpoint, not sensitivity, sets the paired seal, and it needs CT bin agreement at least equal to the readers'

## Question

Round 2 paired-scar ruling §7 item 2. Merge the three power scripts (JA35 item 4) and re-run them at the JA32
bars:
- sensitivity ≥ 0.75;
- specificity ≥ 0.93;
- transmurality agreement ≥ the development LGE inter-reader agreement − 0.10, reported only if that agreement is
  < 0.60.

All three are judged on 95 % patient-bootstrap lower bounds, at one look. The questions are the seal size under
weak and strong clustering, and how many patients ≥ 270 ischaemic scarred segments needs at 50 % and 70 %
enrichment.

## Setup

No image is read; nothing is fitted to data.
- **Patients:** a share `enrich` has one territorial infarct. Its size is k = 1 + Binomial(n_territory − 1, 0.45)
  contiguous segments (Kilo R2) or 1 + Poisson(3) (Golf R2). Its true transmurality is T ~ Beta(1.6, 1.6).
- **Detection:** a patient effect u ~ N(0, τ) on the logit, shared by misses and false calls. P(detect) =
  expit(−0.2 + 5T − u) and P(false call) = expit(−4.3 + u) (Kilo R2's constants), giving sensitivity ≈ 0.84–0.86
  and specificity 0.98, the pooled LIE values (Gatti 2025).
- **CT extent:** T + N(0, 0.05) per patient + N(0, sd_s) per segment.
- **LGE:** two readers, each T + N(0, sd_r). The reference bin is the bin of their mean (an adjudication proxy).
  Reader agreement = the share of scarred segments where the two readers' Kim bins agree.
- **Study:** 40 development patients (65 % enriched) give the anchor; then the seal of N patients is scored.
  1000 studies per cell, 500 bootstrap draws.
- **Variant:** the anchor from every patient's double read (development + seal). It involves no CT value.

## Result

**Calibration** (20 000 patients): reader error 0.06 / 0.08 / 0.12 gives reader bin agreement 0.76 / 0.69 /
0.57. CT extent error 0.08 / 0.13 / 0.20 gives CT-vs-reference bin agreement 0.70 / 0.60 / 0.50 at reader error
0.08.

**Patients for ≥ 270 scarred segments:**

| | 50 % enrichment, median (p90) | 70 % |
|---|---|---|
| Kilo infarct size (mean 3.3 segments) | 167 (187) | 119 (130) |
| Golf R2 infarct size (mean 4) | 135 (155) | 97 (108) |

**Sensitivity alone** (power ≥ 0.80): N ≈ 80 under weak clustering (τ 0.4), ≈ 100 at base (τ 0.8), 200 under
strong clustering (τ 1.2) at 50 % enrichment, and 135 at 70 %. Specificity passes at ≥ 0.99 everywhere.

**Transmurality endpoint:** at CT extent error 0.13 and reader error 0.08, joint power is 0.07–0.29 at every N
from 60 to 200 and every clustering level. Over the sweep, joint power depends on the gap between the CT's and the
readers' agreement:

| Gap (point) | N 120, dev anchor | N 160, dev anchor | N 160, all-patient anchor |
|---|---|---|---|
| +0.07 | 0.83 | 0.91 | 0.93 |
| +0.04 | 0.76 | 0.86 | 0.94 |
| 0.00 | 0.61 | 0.71 | 0.79 |
| −0.04 | 0.40 | 0.50 | 0.50 |
| −0.09 | 0.17 | 0.20 | 0.11 |

**Reader error 0.12** (agreement 0.57): the development anchor is below 0.60 in 68–72 % of studies, so the
endpoint drops out. Joint power at extent error 0.13 is then 0.68–0.72 at 120, against 0.17 with better readers.

## What it changes

1. **Size:** JA28's seal is the largest of 120, the 270-segment N (≈ 170–190 at 50 % enrichment or ≈ 120–130 at
   70 %, with Kilo's infarct sizes) and the sensitivity N. Aim for 70 % enrichment.
2. **The deciding endpoint is transmurality, and patient numbers cannot rescue it.** At 160 patients it needs the
   CT's bin agreement with the reference to be at least the readers' own agreement. The −0.10 margin is spent on
   the lower bound's width and the 40-patient anchor's noise.
3. **The anchor:** taking it from every patient's double read discriminates better than development alone, and it
   leaks nothing about the CT. Below the 0.60 floor, the endpoint should also be reported against a fixed 0.50 bar,
   so poor readers do not pass the scar grade by default.
4. **Development go/no-go:** an extent measure whose development bin agreement is > 0.03 below reader agreement
   cannot be powered at any feasible size. That triggers Scar-1 on extent (JA31), even if presence passes.

## Limits

- The reader model is symmetric Gaussian error on a continuous share. Real readers may disagree more at bin edges
  or in thin scars.
- The adjudication proxy (the mean of two reads) is kinder to the CT than a third reader might be.
- Detection constants are Kilo R2's, calibrated to published readers (Gatti 2025), not to any Scar-0 rule.
  E8 measures what the rules achieve.

---
tags: [janus-m, experiment, power, scar, intention-to-diagnose, path-b, round3]
author: Juliet
round: 3
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#179
code: experiments/JanusM/Juliet/r3/itd_power.py
---

# E9: at a 2 % registration-failure rate, counting a failed patient's scar-free segments as false calls sinks the JA32 study at any size

## Question

The ruling asks for the merged power script, re-run at the JA32 bars (Round 2 §7 item 2). The script is #182, PR
#187: `janusm.scar.power` on the `janusm.scar.scoring` harness.

#187 found that JA29's intention-to-diagnose, as written, counts every LGE-negative segment of a not-graded patient
as a false call. That is about 15 false calls, all in one patient. It reported that a 2 % whole-patient
registration-failure rate keeps joint power below 80 % at every size up to 320, and asked the judge or PM to
decide.

This experiment measures that effect, and one alternative accounting, on #187's own engine.

## Method

Simulation only: no image, case or id is read. The engine is the code at PR #187's head `f5d2b56`, imported unchanged.
The cohort is #187's port of Golf's (`golf_cohort` with `JA32_BASE`: λ 3, q 0.25, specificity 0.98, bin_tau 1.0).
The grid:
- clustering weak (patient logit SD 0.7) or strong (1.2);
- 50 or 70 % of patients with scar;
- whole-patient failure p_fail ∈ {0, 0.02, 0.05, 0.10};
- N ∈ {120, 160, 200, 240, 320};
- 400 studies per cell, each with a 400-replicate patient-cluster bootstrap.

The bars are JA32's: lower bounds of sensitivity ≥ 0.75, specificity ≥ 0.93, and transmurality ≥ anchor − 0.10
(anchor 0.70). Both accountings use the **same cohorts and the same bootstrap replicates**.

| Accounting | A not-graded patient's LGE-positive segments | Its LGE-negative segments | Extra bar |
|---|---|---|---|
| **segment** (JA29 as written; #187) | misses | false calls | — |
| **split** (proposed) | misses (sensitivity charged in full) | leave the specificity denominator | not-graded patient rate: exact (Clopper–Pearson) upper 95 % bound ≤ **0.10**, JA29's own development stop |

## Result

The smallest N with joint power ≥ 0.80 (from that N up), and joint power at N = 240:

| Clustering | Scar share | p_fail | segment: N / power at 240 | split: N / power at 240 |
|---|---|---|---|---|
| weak | 50 % | 0 | 120 / 0.995 | 120 / 0.995 |
| weak | 50 % | **0.02** | **none ≤ 320** / 0.645 | **200** / 0.910 |
| weak | 70 % | **0.02** | **none ≤ 320** / 0.682 | **160** / 0.965 |
| weak | 50 % | 0.05 | none / 0.022 | none / 0.490 |
| strong | 70 % | 0 | 160 / 0.922 | 160 / 0.922 |
| strong | 70 % | 0.02 | none / 0.310 | none (0.79 at 320) / 0.680 |
| any | any | 0.10 | none / ≤ 0.03 | none / ≤ 0.03 |

**Median specificity point estimate,** weak clustering, 50 % scar:

| p_fail | segment rule | split rule |
|---|---|---|
| 0 | 0.975 | 0.975 |
| 0.02 | 0.957 | 0.975 |
| 0.05 | 0.926 | 0.975 |
| 0.10 | 0.877 | 0.975 |

1. **With no failures, the two rules are identical.** This reproduces #187: joint power 0.91 at 120 with weak
   clustering and 50 % scar.
2. **At a 2 % failure rate, the segment rule never reaches 80 % with weak clustering.** The reason is the
   specificity: 15 false calls in each failed patient move its point estimate from 0.975 to 0.957 and widen its
   cluster CI. The split rule needs 200 patients (50 % scar) or 160 (70 % scar).
3. **At 5 %, neither rule passes.** Under the split rule this is by design: a true 5 % failure rate rarely gives an
   upper bound ≤ 0.10, and the failed patients' scar still counts as missed. At 10 %, the rate at which JA29 stops
   seal grading, nothing passes either way.
4. **With strong clustering and 2 % failure, neither rule reaches 0.80 by 320.** The split rule gets to 0.79.

## What it changes

- **Proposed amendment (Juliet v3 §10).** A not-graded patient's LGE-positive segments stay misses, and its
  LGE-negative segments leave the specificity denominator. The not-graded patient rate becomes a fourth deciding
  bar: upper 95 % ≤ 0.10.
  - The pipeline is still charged for every scar it fails to grade.
  - The failure rate is bounded in the open, not hidden in specificity.
  - A pipeline that fails more than 10 % of patients still fails the study.
- **The seal size depends on the failure rate more than on clustering or enrichment.** The JA28 re-powering on
  development must therefore measure p_fail (development registration failures) and feed it to `seal_size()`.
  #187's grid already has `p_fail`.
- **Limits.**
  - Golf's cohort model.
  - Whole-patient failure only (no partial-heart failure).
  - The not-graded bar uses an exact binomial bound, not the cluster bootstrap. A patient-level rate needs no
    clustering.
  - #187 has since merged into `jm/paired-scar`. `power.py` and `scoring.py` there are byte-identical to `f5d2b56`,
    so these numbers are the merged engine's.
- **Kilo's E9 asks the same question on the same engine** (#179) and proposes graded-only accuracy plus a yield bar,
  with a selective-failure guard. "Split" sits between Kilo's "no call" and "graded-only":
  - like "no call", it charges a failed patient's scar as missed;
  - like "graded-only", it keeps the failed patient's scar-free segments out of specificity;
  - it bounds the failure rate in its own bar.

  At 2 % failure with weak clustering, Kilo reports joint power 0.88–1.00 for graded-only and 0.65–0.96 for "no
  call". "Split" gives 0.69–0.97 here. Graded-only is the most powerful, and "split" is the most conservative of the
  three that pass.

---
aliases: [Kilo E9]
tags: [janus-m, experiment, power, intention-to-diagnose, registration, transmurality, kilo, paired-scar, round3]
status: done
round: 3
path: jm/paired-scar
updated: 2026-10-30
code: experiments/JanusM/Kilo/e9_engine_ja32.py
issue: christianGRogers/Asclepius#179
---

# Kilo E9: on the merged engine, worst-case counting of registration failures sinks specificity, and a yield endpoint fixes it

**Questions** (Round 2 ruling §7 item 2; the design problem the PM posted on #179 with the merged engine, #187):

- **A.** E7 found the transmurality endpoint binding; the engine's default grid says it never binds. Who is right, on
  the engine itself?
- **B.** JA29 counts a not-graded segment as a miss if LGE-positive and a false call if LGE-negative. What does that
  do to the JA32 endpoints at realistic failure rates, and what rule works?

**Answers.**

- **A. Both are right, about different CTs.** On the engine's own Golf cohort, the endpoint binds as soon as CT
  exact-bin agreement on scar-on-both segments falls from 0.73 to 0.66.
  - At q = 0.25 (agreement 0.81, the engine's default): joint power 0.95–0.99.
  - At q = 0.35 (0.73): 0.88–0.99 with a fixed anchor of 0.72, and 0.79–0.89 with E7's noisy development anchor.
  - At q = 0.45 (0.66): 0.23–0.35.
  - At q = 0.55 (0.58): ≈ 0.
  - Round 2 E5's two-threshold rule measured 0.70 [0.62, 0.76]. That sits on the cliff.
- **B. Worst-case counting fails the study at 2 % failure.** At 2 % whole-patient failure, JA29's rule drops
  specificity power to 0.44–0.67 and joint power to 0.37–0.66 (120–240 patients). At 5 % joint power is ≈ 0.03 at
  any N. The cause: one failed LGE-negative patient adds ≈ 15 false calls.
  - **"No call"** (a not-graded segment is scored as no scar called) restores specificity. Failures then cost
    sensitivity only: joint power 0.65–0.96 at 2 % and 0.32–0.60 at 5 %.
  - **Graded-only accuracy plus a yield endpoint** (not-graded patient share, upper 95 % bound ≤ 0.10, deciding):
    0.88–1.00 at 2 %, 0.63–0.89 at 5 % (the yield bound binds), and ≤ 0.08 at 10 %. That matches JA29's own
    stop-at-10 % on development.

## Method

- **Engine:** `janusm.scar.power.golf_cohort` and `janusm.scar.scoring` (#187), unchanged. The engine is imported, not
  copied.
- **Cohort:** enrich 0.5 (A, B) or 0.7 (B), lam 3, tau 0.7 (weak clustering), bin_tau 0, 16 segments.
- **Runs:** 300 studies per cell, 300-draw patient bootstrap.
- **Part A:**
  - q (Golf's one-bin-off error rate) ∈ {0.25, 0.35, 0.45, 0.55}; N ∈ {120, 160, 240}; p_fail 0;
  - the anchor is 0.72 (E7's two-reader agreement), either fixed or drawn per study from N(0.72, 0.05), the spread of
    a 40-patient development estimate in E7;
  - JA32 bars on lower bounds; an anchor < 0.60 makes transmurality report-only.
- **Part B:**
  - p_fail ∈ {0, 0.02, 0.05, 0.10}, whole-patient not graded (the engine's ITD model);
  - three resolutions, all scored by the engine's `patient_stats` and `cluster_bootstrap`:
    - worst = the engine's `intention_to_diagnose` (JA29);
    - no-call = not graded → bin 0;
    - graded-only = the not-graded segments masked out;
  - the yield endpoint = the patient-bootstrap upper 95 % bound of the not-graded patient share ≤ 0.10, applied
    jointly with the JA32 bars in the "+ yield" columns.

## Results

### A. Transmurality on the engine (50 %, weak clustering)

| q | CT exact-bin agreement (scar on both) | Joint power at N = 120 / 160 / 240, fixed anchor 0.72 | Noisy anchor |
|---|---|---|---|
| 0.25 | 0.81 | 0.95 / 0.97 / 0.99 | 0.94 / 0.97 / 0.99 |
| 0.35 | 0.73 | 0.88 / 0.95 / 0.99 | 0.79 / 0.84 / 0.89 |
| 0.45 | 0.66 | 0.23 / 0.24 / 0.35 | 0.31 / 0.36 / 0.43 |
| 0.55 | 0.58 | 0.00 / 0.00 / 0.00 | 0.04 / 0.06 / 0.07 |

Sensitivity power is 0.91–0.99 in every row. Once CT agreement is ≤ anchor − 0.06, more patients barely help. The
anchor's development noise costs up to 0.1 in power when the CT is near the bar. It slightly helps when the CT is
below the bar, because a low draw lowers the bar.

### B. Registration failure: joint power at the JA32 bars (transmurality not binding: q = 0.25)

50 % enrichment:

| p_fail | N | Worst case (JA29) | No call | Graded-only + yield | Yield bound ≤ 0.10 alone |
|---|---|---|---|---|---|
| 0 | 120 / 160 / 240 | 0.93 / 0.96 / 1.00 | 0.94 / 0.96 / 1.00 | 0.93 / 0.96 / 0.99 | 1.00 |
| 0.02 | 120 / 160 / 240 | 0.39 / 0.50 / 0.61 | 0.65 / 0.78 / 0.91 | 0.88 / 0.95 / 0.99 | 1.00 |
| 0.05 | 120 / 160 / 240 | 0.03 / 0.03 / 0.02 | 0.32 / 0.38 / 0.49 | 0.63 / 0.74 / 0.89 | 0.69 / 0.77 / 0.89 |
| 0.10 | 120 / 160 / 240 | 0.00 | 0.05 / 0.07 / 0.08 | 0.06 / 0.05 / 0.03 | 0.03–0.09 |

70 % enrichment:

| p_fail | N | Worst case | No call | Graded-only + yield |
|---|---|---|---|---|
| 0.02 | 120 / 160 / 240 | 0.37 / 0.48 / 0.66 | 0.74 / 0.88 / 0.96 | 0.95 / 0.99 / 1.00 |
| 0.05 | 120 / 160 / 240 | 0.05 / 0.03 / 0.03 | 0.40 / 0.47 / 0.60 | 0.68 / 0.74 / 0.88 |

Median point estimates at 5 % failure:
- worst case: sensitivity 0.80, specificity 0.93;
- no call: 0.80 / 0.98;
- graded-only: 0.84 / 0.98.

## What it changes

1. **Replace JA29's worst-case rule in the primary analysis** with **graded-only accuracy + a deciding yield endpoint**
   (not-graded patient share, upper 95 % bound ≤ 0.10).
   - The yield endpoint is what intention-to-diagnose was protecting: failures cannot be hidden, because too many of
     them fail the study.
   - The worst-case and no-call analyses are reported beside it.
2. **A pre-registered guard against selective failure.** Graded-only could flatter the pipeline if failures fall on
   hard, scarred hearts. So: if the LGE-positive segment share among not-graded patients is ≥ 1.5× that among graded
   patients (patient bootstrap, lower bound > 1), **no-call becomes the primary analysis**. It still counts every
   missed scar.
3. **Planning failure rate ≤ 2 %.** At 5 %, even the yield-based rule loses 0.1–0.3 of power. Development measures the
   failure rate (JA29's stop at > 10 % stands), and the engine re-sizes the seal on it.
4. **Transmurality:** whether it can be powered is decided on development, from the measured CT bin agreement against
   the anchor (Kilo v3 §4.2), not assumed from a default q.

**Limits.** Failures are whole-patient and independent of scar here (the engine's model). A failure process that
targets scarred hearts is exactly what item 2's guard is for. The engine's Golf cohort has no reader noise in the
reference, and E7 adds it.

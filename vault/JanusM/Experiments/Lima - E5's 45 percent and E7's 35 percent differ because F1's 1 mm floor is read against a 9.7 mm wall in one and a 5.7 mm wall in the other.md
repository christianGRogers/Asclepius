---
tags: [janus-m, experiment, round4, rest-ccta, calibration, thinning, ja40, detectable-depth, simulation]
author: Lima
round: 4
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#205
---

# Lima E6: E5's 45 % and E7's 35 % differ because F1's 1 mm floor is read against a 9.7 mm wall in one and a 5.7 mm wall in the other

**Question (#205 item 2; Round 3 ruling §1.2 (5), §8 item 2).** Lima E5 printed a detectable depth of 45 % and Hotel
E7 35 % for nominally the same inputs (cv_n 0.088, Lima's shape). Explain the gap on one seed with the shipped
`janusm.calibrate`, and say which median wall is right for JA40.

**Setup** (`experiments/JanusM/Lima/r4/e6_depth_decomposition.py` → `e6_depth_decomposition.json`; a simulation of
16 segment thicknesses per heart, no image or case opened; the guard is called first on an empty list).
- **Engine:** the shipped S3 functions (`population`, `rule_c_scores`, `calibrate_c`, `territory_flags`,
  `f1_deviation`) with JA40's design: 4 populations of 2000 per depth, depths 0.10–0.60, prevalence 0.1, mixed phase
  40 / 40 / 20, the seed sequence from `E7_SEED` (31000).
- **Four switches, all 16 combinations, on the same random draws.** The median only rescales the hearts, and
  σ_m = 0 still draws its zero-SD noise, so every combination sees identical patients.

  | Switch | E7 (JA40) | E5 |
  |---|---|---|
  | median wall passed to `population` | 9.668 mm (Lima's self-test median) | 5.7 mm (Chen 2025, CT end-diastole) |
  | added error σ_m | 0 | 0.5 mm |
  | F1 floor | 1.0 mm | 1.96 · √2 · σ_m / √k: 0.57 (LAD) / 0.62 (RCA, LCx) mm at σ_m 0.5; 0 at σ_m 0 |
  | F1 deviation | Hotel's, shape-corrected (`f1_deviation`, JA42) | raw: remote median − territory mean |

- **E5's own `detectable_depth`** (one population of 4000 per depth, depths from 0.15, one generator for the sweep),
  unchanged, on seeds 0–19.
- **JA40's function** (`janusm.calibrate.detectable_depth`, σ_m 0, F1 1.0 mm) at four medians on five seeds
  (31000, `jm0r_decide.DEPTH_SEED` 20261030, 1, 2, 3).

**Result.**

1. **The median alone moves JA40's depth from 0.35 to 0.45.** On E7's seed, with everything else as JA40 fixes it:

   | median (mm) | rule C alone | rule C + F1 1.0 mm |
   |---|---|---|
   | 9.668 | 0.30 | **0.35** |
   | 5.7 | 0.30 | **0.45** |

   Sensitivity at 0.30 / 0.35 / 0.40: 0.79 / 0.90 / 0.94 at 9.668 mm, 0.53 / 0.67 / 0.76 at 5.7 mm. Rule C is the
   same at both medians, because it works on thickness ÷ the patient's own median. **All of the gap is the F1 floor.**
   The floor is in mm, so the same 1.0 mm is 10 % of a 9.7 mm wall and 18 % of a 5.7 mm one.
2. **The full factorial (depth on E7's seed; max false-flag share in brackets):**

   | median | σ_m | Hotel dev, 1.0 mm | Hotel dev, E5 floor | raw dev, 1.0 mm | raw dev, E5 floor |
   |---|---|---|---|---|---|
   | 9.668 | 0 | **0.35** (0.006) | 0.30 (0.019) | 0.35 (0.014) | 0.30 (0.020) |
   | 9.668 | 0.5 | 0.35 (0.012) | 0.35 (0.020) | 0.35 (0.017) | 0.35 (0.022) |
   | 5.7 | 0 | **0.45** (0.002) | 0.30 (0.019) | 0.45 (0.006) | 0.30 (0.020) |
   | 5.7 | 0.5 | 0.50 (0.005) | 0.40 (0.018) | 0.50 (0.011) | **0.40** (0.025) |

   From E7 (top left) to E5's settings (bottom right):
   - median 9.668 → 5.7: **+10 points**;
   - σ_m 0 → 0.5 at 5.7 mm: +5 points;
   - E5's smaller floor (≈ 0.6 mm in place of 1.0): −10 points;
   - the raw deviation in place of Hotel's: no step, but about twice the false flags. Hotel's deviation is the right
     one, as JA42 ruled.

   So E5's settings, run on JA40's design, give **0.40**, not 0.45.
3. **E5's printed 45 % was a tail seed.** E5's own function gives 0.40 on 18 of 20 seeds and 0.45 on 2 (seeds 2
   and 8). Its single population per depth gives the 5-point jitter the judge noted ("a first run gave 40 %").
   JA40's four replicates remove it. JA40's function returns the same depth on all five seeds tried at 9.668 and
   5.7 mm.
4. **The 9.668 mm is used twice over.** `population` multiplies its `median_mm` by the patient scale and the phase
   factor (1.00 / 1.14 / 1.40). The simulated population's median wall is **1.109 ×** `median_mm`. 9.668 mm is
   already a measured median over mixed-phase studies, so E7 (and `detectable_depth`'s default) simulates a median
   wall of about **10.7 mm**. The anchor that reproduces a measured 9.668 mm is 8.72 mm. It also gives 0.35 on all
   five seeds.

   | `median_mm` passed | what it means | depth on 5 seeds |
   |---|---|---|
   | 9.668 | the default; measured median used as the anchor | 0.35 × 5 |
   | 8.72 | anchor reproducing a measured 9.668 mm | 0.35 × 5 |
   | 5.7 | Chen 2025's end-diastolic mean as the anchor (simulated median 6.3 mm) | 0.45 × 5 |
   | 5.141 | anchor reproducing a measured 5.7 mm | 0.45, 0.50 × 3, 0.45 |

**Which median is right for JA40.** The F1 floor and JA42's RC are in mm on the walls the table measures. So the
simulation's wall must be **the measured median wall of the population that fills the table, on the same thickness
definition**: JM-0R's `thickness_median_mm`, divided by 1.109 to give the anchor `population` expects. The 9.668 mm
is not that number, for three reasons:
- **It fails the plan's own sanity window.** It comes from 1.5 mm model-made labels on 23 public non-CCTA studies, and
  is outside JA43 R3's 4.2–8.0 mm. The decision script, run on those very aggregates, rejects it at R3 (the
  definition must be aligned before any thinning flag ships), while R9 uses it by default. A median the plan refuses
  for F3 cannot set the page's depth.
- **Its labels are thick.** The same self-test reads the epicardial half-maximum offset at +0.64 mm (the label
  reaches into the fat).
- **It is counted twice.** Used as the anchor, its phase factor is applied a second time (10.7 mm simulated).

**Until JM-0R reports, 5.7 mm is right.** It is the CT end-diastolic anchor `population` was written for, it sits
inside R3's window, and it is the conservative choice JA40 asks for ("conservative until measured"). Under JA40's
own procedure, unchanged, it gives **0.45**.

**What it changes.**
- **JA40's provisional print should be 45 %, not 35 %.** That is JA40's procedure with a median that passes R3. It
  matches E5's printed figure only by coincidence (E5's settings give 0.40 on this design). At 45 % the page's
  "above 40 %" sentence shows.
- **JA41's gate (≤ 0.50) still passes at 0.45,** with one step to spare. At σ_m 0.5 (a cv_n from another model's
  labels, JA40), 5.7 mm reaches 0.50, the gate's edge.
- **`jm0r_decide` R9 must pass the median** (spec in [[Lima v3]] §2, G1). Today it calls
  `detectable_depth(cv_n, shape, rc, sig_m, seed)`, and the depth is always simulated at the 9.668 mm default
  whatever JM-0R measures. A JM-0R median of 6, 7 or 8 mm would print 35 %, where JA40's procedure gives
  0.45, 0.40 and 0.40 (anchors 5.41, 6.31, 7.22 mm; `DEPTH_SEED`).
- **Nothing in S3's code is wrong.** Its E7 reproduction tests stay valid as regression tests at an explicit
  `median_mm=9.668`; only the default and R9's call change.

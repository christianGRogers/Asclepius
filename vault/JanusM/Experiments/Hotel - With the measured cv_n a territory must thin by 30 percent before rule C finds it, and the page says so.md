---
tags: [janus-m, experiment, thinning, calibration, rule-c, detectable-depth, path-rest-ccta]
author: Hotel
round: 3
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#167
---

# With the measured cv_n, a territory must thin by 30 percent before rule C finds it, and the page says so

Round 2 ruling §7 item 3 (JA18): re-run Lima's E3 with the measured `cv_n` and segment shape, and fix the
detectable depth that the page prints instead of a sensitivity.

## What was run

The run is a simulation; **no case was opened**. Script: `experiments/JanusM/Hotel/r3/e7_detectable.py`, output
`e7_detectable.json`.

- **Lima's own functions, imported unchanged** from `experiments/JanusM/Lima/calibrate_sim.py`:
  - `population` (lognormal patient size, unknown phase, segment shape, normal variation `cv_n`, 2–4 contiguous
    thinned segments in one territory);
  - `rule_c_scores` (patient-relative, shape-corrected, scaled from the right half);
  - `calibrate_c` (the cut that leaves ≤ 5 % of mirror-null patients with any territory flag);
  - `territory_flags` (≥ 2 contiguous segments).
- **Measured inputs.** The 16-segment shape, `cv_n` = **0.088** and the median thickness (9.67 mm) come from
  `experiments/JanusM/Lima/local_check_summary.json`. That is Lima's guarded self-test on the 23 allowed public
  hearts, with 1.5 mm model-made labels. They are the only measured values before JM-0R.
- **The script reads JM-0R's keys** (`rel_thickness_by_segment_mean_sd`, `rel_thickness_shape_corrected_sd`,
  `median_thickness_mm`), so the same command reruns on the lead's JM-0R summary with `--inputs`.

**Three changes from Lima's E3:**
1. **No double count.**
   - `cv_n` measured on Janus-M 0's borders already contains Janus-M 0's own measurement error. Patients are
     measured by the same model, so the primary run adds **no further error** (`sig_m` = 0).
   - Lima's E3 added `sig_m` on top of a `cv_n` that already held it. That is kept only as a sensitivity
     (`sig_m` 0.25 and 0.5 mm).
2. **A finer grid with replicates.**
   - Relative depth runs from 0.10 to 0.60 in 0.05 steps.
   - Each condition uses 4 independent populations of 2000.
   - Prevalence is 0.1 or 0.3. The phase mix is either all end-diastole, or mixed (40 / 40 / 20 % ED / MD / systole).
   - **Detectable depth** = the smallest depth whose mean territory sensitivity is ≥ 0.80.
3. **Hotel's F1 floor (JA18).**
   - A rule-C territory flag shows only if the territory's shape-corrected mean thinning, in mm against the
     patient's remote segments, exceeds RC_terr.
   - RC_terr is swept over 0, 0.35, 0.7 and 1.0 mm. E4 (Hotel R2) gives 0.74 mm per segment at 0.25 mm read
     noise, about 0.33 mm for a five-segment mean.

`cv_n` 0.06, 0.12 and 0.15 are run as a lookup for JM-0R's value.

## Results

Detectable depth (relative thinning of the affected territory), mixed phase, prevalence 0.1, with the replicate
range of sensitivity at that depth:

| `cv_n` | Extra error | RC_terr 0 | 0.35 mm | 0.7 mm | 1.0 mm | Max false-flag rate |
|---|---|---|---|---|---|---|
| **0.088 (measured)** | **none (primary)** | **0.30** (0.86–0.91) | **0.30** (0.84–0.90) | **0.30** (0.81–0.88) | 0.35 (0.89–0.91) | ≤ 0.019 |
| 0.088 | `sig_m` 0.25 mm (Lima-style) | 0.30 | 0.30 | 0.35 | 0.35 | ≤ 0.022 |
| 0.088 | `sig_m` 0.5 mm (Lima-style) | 0.35 | 0.35 | 0.35 | 0.35 | ≤ 0.025 |
| 0.06 | none | 0.20 | 0.25 | 0.25 | 0.30 | ≤ 0.029 |
| 0.12 | none | 0.40 | 0.40 | 0.40 | 0.40 | ≤ 0.013 |
| 0.15 | none | 0.45 | 0.45 | 0.45 | 0.45 | ≤ 0.010 |

- **The detectable depth at the measured `cv_n` is 30 %.** It does not depend on:
  - the phase mix (all-ED gives the same 0.30), because the rule is patient-relative;
  - prevalence (0.30 at 0.3).
- **Hotel's F1 floor costs nothing up to 0.7 mm.** At 1.0 mm it moves the depth to 35 %. It also halves the
  false-flag rate.
- **Lima's double count matters only at `sig_m` 0.5 mm**, where it moves the depth from 30 to 35 %.
- **`cv_n` drives everything:** 0.06 → 20–25 %, 0.12 → 40 %, 0.15 → 45 %. JM-0R's value decides the printed
  number.
- **The calibrated null is conservative.** The cut is set for ≤ 5 % of mirror-null patients, and the realised
  false-flag rate among simulated infarct-free patients is ≤ 3 %.

**Limits.**
- The shape and `cv_n` come from 1.5 mm model-made labels on 23 public hearts. Native ImageCAS may differ, which
  is why the number is re-run on JM-0R.
- Thinning in the model is relative and confined to 2–4 contiguous segments of one AHA-default territory.
- **The composite pattern's population rate** (§7 item 3, second half) needs Janus-M 0 outputs on the reference
  population (LQ12), which do not exist yet. It cannot be measured this round, and nothing here estimates it.

## What it changes

**The sentence printed on every page** (Table B footer, JA18/JA19) is fixed now, with its numbers filled from JM-0R
by this script:

> "Thinning: a territory is flagged only when its wall is thinner than the patient's other walls by more than
> this population's normal variation allows. In simulation, a territory thinned by **≥ 30 %** is flagged in
> ≥ 80 % of cases. Thinner changes are usually not flagged. This is not a sensitivity for scar, which this
> table cannot measure."

**The pre-registered rule.** When JM-0R posts `cv_n` and the shape, the lead's output is run through
`e7_detectable.py --inputs`, and the printed depth is replaced by its primary-row value (mixed phase,
prevalence 0.1, RC_terr from the decision reads, rounded up to the 0.05 grid). If that depth is **> 0.40**, the
thinning flag is still computed but the page says "thinning of less than {depth} is not detectable in this
population". No rule is loosened to make it smaller.

---
tags: [janus-m, experiment, round2, rest-ccta, calibration, thinning, stage-a, simulation]
author: Lima
round: 2
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#142
---

# Lima E3: without a scar reference, thinning can be calibrated for specificity per territory, and a borrowed 5.5 mm cut flags 57–89 % of normal hearts

**Question (Round 1 ruling §6 item 9).** On path A there is no scar reference. Can a Stage A sign still get a
threshold whose false-flag rate is known, and how much thinning can it then find?

**Setup.** A simulation; no image is read (`experiments/JanusM/Lima/calibrate_sim.py`, results in
`calibrate_sim.json`). Each population has 2000 hearts with 16 segment thicknesses each. Every condition is one draw
from seed 20261030.

| Factor | Values | Source / status |
|---|---|---|
| Patient scale | 5.7 mm × lognormal, CV 0.12 | 5.7 mm: CT end-diastolic global mean (Chen 2025); CV assumed |
| Phase | end-diastole ×1.00; mid-diastole ×1.14; systole ×1.40 | ×1.14 from Chen 2025 (5.7 vs 6.5 mm); systolic factor **assumed**. Mixes: all end-diastolic, or 40/40/20 |
| Segment shape | septum ×1.12–1.29, apex ×0.76–0.83 (all 16 values in the code) | measured by Lima's self-test on the 23 allowed public hearts (1.5 mm model-made labels); Job JM-0b measures it on native CCTA. An earlier run with a flatter placeholder shape gave the same conclusions |
| Normal segment variation `cv_n` | 0.06, 0.10, 0.15 | swept; the self-test measured 0.088 (shape-corrected SD); JM-0b measures it |
| Infarct | 2–4 contiguous segments of one AHA-default territory, thinned by 20–50 % | prevalence 10 % or 30 % |
| Segment-thickness error `sig_m` | 0.25, 0.5, 1.0 mm | JA8's co-primary; Lima E2 maps it to border ASSD |

**Rules compared.** Each is calibrated on the unlabelled population, infarcts included, as a real one would be.
- **A.** The CMR end-diastolic cut, thickness ≤ 5.5 mm (Shah 2013), borrowed as is.
- **B.** The per-segment population 2.5th percentile of absolute thickness.
- **C (Lima).** A patient-relative, shape-corrected score per segment:

  z = (thickness / patient's own median − segment shape) / segment scale

  - Shape and scale come from the population itself.
  - The scale is taken from the right half only, which thinning cannot reach.
  - A **territory** (AHA default map) is flagged when ≥ 2 contiguous segments in it fall below the cut.
  - The cut is set so that ≤ 5 % of *null* patients carry any flag. The null is the mirror image of the pooled
    right half, sampled as 20 000 sixteen-segment hearts. **No label is used.**

  Three versions failed before this one and are kept in the record:
  - a Gaussian null fitted by MAD;
  - a log ratio;
  - one pooled scale for all segments.

  Each let patient-level false flags reach 12–16 % at 1 mm error: symmetric millimetre error becomes a skewed,
  segment-dependent relative error on thin walls. The linear ratio with per-segment scales fixed this.

**Result 1: false flags in infarct-free patients**, over the whole grid of 144 conditions:

| Rule | Patient false-flag rate | By phase (40/40/20 mix): end-diastole / mid-diastole / systole |
|---|---|---|
| A, ≤ 5.5 mm | **0.57–0.89** | 0.85–0.91 / 0.53–0.70 / 0.04–0.25 |
| B, population p2.5 | 0.00–0.04 | — |
| **C, relative per territory** | **0.003–0.056** (mean 0.023 at 10 % prevalence, 0.019 at 30 %) | 0.004–0.08 / 0.002–0.06 / 0.00–0.02 |

- A's rate depends on the phase and on the assumed 5.7 mm end-diastolic mean, so its exact value is not the point.
  **An absolute cut cannot be borrowed when the reconstruction phase is unrecorded.** That is ImageCAS's case
  (JA11).
- C's rate holds near its target whatever the phase mix, because the patient's own median cancels the global
  scale.

**Result 2: territory sensitivity**, 40/40/20 phase mix, 10 % prevalence. Each cell is rule C / rule B:

| `cv_n` | error | 20 % thinning | 30 % | 40 % | 50 % |
|---|---|---|---|---|---|
| 0.06 | 0.25 mm | 0.62 / 0.17 | **0.98** / 0.48 | 1.00 / 0.71 | 1.00 / 0.89 |
| 0.06 | 0.5 mm | 0.33 / 0.14 | 0.77 / 0.24 | **0.98** / 0.58 | 0.99 / 0.79 |
| 0.06 | 1.0 mm | 0.16 / 0.08 | 0.29 / 0.14 | 0.57 / 0.29 | **0.82** / 0.45 |
| 0.10 | 0.25 mm | 0.27 / 0.19 | 0.75 / 0.36 | **0.95** / 0.52 | 1.00 / 0.81 |
| 0.10 | 0.5 mm | 0.17 / 0.14 | 0.55 / 0.29 | **0.84** / 0.52 | 0.99 / 0.70 |
| 0.10 | 1.0 mm | 0.08 / 0.06 | 0.22 / 0.14 | 0.53 / 0.28 | 0.77 / 0.46 |
| 0.15 | 0.25 mm | 0.04 / 0.12 | 0.22 / 0.20 | 0.65 / 0.44 | **0.94** / 0.75 |
| 0.15 | 0.5 mm | 0.06 / 0.09 | 0.25 / 0.22 | 0.55 / 0.38 | **0.84** / 0.63 |
| 0.15 | 1.0 mm | 0.09 / 0.06 | 0.14 / 0.09 | 0.31 / 0.24 | 0.59 / 0.39 |

**Thinning needed for 80 % sensitivity under rule C** (40/40/20, 10 %):

| `cv_n` | 0.25 mm error | 0.5 mm | 1.0 mm |
|---|---|---|---|
| 0.06 | 30 % | 40 % | 50 % |
| 0.10 | 40 % | 40 % | > 50 % |
| 0.15 | 50 % | 50 % | > 50 % |

**What it changes (for Lima v1).**
1. **Thinning is reported per territory, from the patient's own median, with a false-flag rate calibrated on the
   unlabelled Janus-M population.** No absolute cut is borrowed. The AHA-default territory is used for calibration
   and the patient-specific one for reporting. This settles the calibration half of §6 item 9: **specificity is
   calibrated now; sensitivity stays unknown without a reference, and is reported as the simulated detectable
   depth.**
2. **What makes thinning useful is segment-thickness error ≤ 0.5 mm.** At 1 mm, only walls thinned by about half are
   found reliably. At the measured `cv_n` (≈ 0.09 on public labels), 0.25–0.5 mm error finds 40 % thinning 84–95 % of
   the time. This is the clinical reason to keep JA8's co-primary bar at read-vs-read + 0.5 mm.
3. **Normal segment variation matters as much as border error.** At `cv_n` 0.15 even near-perfect borders need about
   50 % thinning. JM-0b measures `cv_n` (the shape-corrected SD of relative thickness) and the segment shape on 40
   native CCTA. The simulation is then re-run with those two numbers, before any table ships.
4. **The same procedure applies to the other Stage A signs.**
   - Guarded subendocardial HU relative to the patient's own median gives hypoattenuation.
   - Fat is flagged when a core cluster passes a cut-off. The cut-off is set so that ≤ 5 % of null hearts carry a
     cluster. This is the data-driven fat cut that JA11 asks for.

**Limits.**
- This is a simulation. The systolic factor and the infarct geometry are assumptions; the segment shape and `cv_n`
  come from 1.5 mm model-made labels.
- The patient median includes the infarct's own segments. Very large infarcts (> 8 segments) would pull it down,
  and rule C would under-call them.
- Real phase effects are regional, not one global factor.
- Sensitivity is only simulated. Path A has no way to measure it (by construction); path B does.

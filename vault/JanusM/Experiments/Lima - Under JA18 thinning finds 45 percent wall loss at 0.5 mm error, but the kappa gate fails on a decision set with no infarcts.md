---
tags: [janus-m, experiment, round3, rest-ccta, calibration, thinning, ja18, kappa, simulation]
author: Lima
round: 3
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#167
---

# Lima E5: under JA18, thinning finds 45 % wall loss at 0.5 mm error, but the κ gate fails on a decision set with no infarcts

**Question (Round 2 ruling §7 item 3).** Re-run Lima's E3 with the measured `cv_n` and segment shape, under the
thinning rule JA18 actually adopted: rule C, plus Hotel's F1 floor, plus the κ ≥ 0.6 gate. Fix the detectable depth
printed on the page, and measure the composite pattern's population rate.

**Setup** (`experiments/JanusM/Lima/r3/e5_ja18.py`, results in `e5_ja18.json`; a simulation, no image).
- **E3's generator,** with these inputs:
  - mixed phase (40 % end-diastole, 40 % mid-diastole, 20 % systole);
  - 10 % infarct prevalence in the 2000-heart reference population;
  - infarcts of 2–4 contiguous segments in one territory.
- **The measured inputs.** The segment shape and `cv_n` = **0.088** come from Lima's self-test on the 23
  guard-allowed public hearts (`local_check_summary.json`). These are 1.5 mm model-made labels, so they are the best
  measurement available until Job JM-0R reports. `cv_n` 0.06 and 0.15 bracket it.
- **The flag under test.** Rule C's territory flag (≤ 5 % of mirror-null patients), then **F1**: the territory mean
  must lie below the patient's remote median by more than RC = 1.96 · √2 · σ_r / √k (Bland & Altman 1986), with
  σ_r the single-read segment error and k the territory's segment count.
- **The κ gate.** A 40-patient decision set read twice, with independent read errors σ_r = σ_m, at decision-set
  infarct prevalences of 0, 10 and 30 %. 400 draws per condition give P(κ ≥ 0.6).
- **A prevalence-robust alternative to κ.** ICC (absolute agreement, two raters; Shrout & Fleiss 1979) of the
  continuous territory deviation between the two reads, giving P(ICC ≥ 0.75).
- **The composite pattern's null rate.** Three correlated per-segment null scores (correlation ρ): thinning, fat and
  hypoattenuation. Each is calibrated alone to ≤ 5 % of patients. The composite is thinning **and** (fat **or**
  hypoattenuation) in one territory.

**Result 1: F1 costs little at small error and a lot at large error.** All values below are at `cv_n` 0.088,
reference prevalence 10 %. Cells are territory sensitivity, with the patient false-flag rate in brackets.

| Thickness error | Thinning | Rule C alone | Rule C + F1 |
|---|---|---|---|
| 0.25 mm | 30 % | 0.81 (0.014) | 0.76 (0.013) |
| 0.25 mm | 40 % | 0.99 (0.023) | 0.95 (0.020) |
| 0.5 mm | 40 % | 0.93 (0.026) | 0.80 (0.017) |
| 0.5 mm | 50 % | 1.00 (0.018) | 0.96 (0.013) |
| 1.0 mm | 50 % | 0.84 (0.045) | 0.68 (0.013) |

Rule C already holds false flags under 5 %. F1 lowers them further, to 1–2 %, at the price of 4–16 points of
sensitivity. That is what JA18 asked for: specificity first.

**Result 2: the detectable depth for the page** (JA18 + F1, 80 % of territories found):

| Segment-thickness error | 0.25 mm | 0.5 mm | 1.0 mm |
|---|---|---|---|
| Thinning detected | **35 %** | **45 %** | **65 %** |

At the 0.5 mm the JA16 co-primary allows, the page line (`e5_ja18.page_line`) reads:
> *Thinning flags in this population find a territory thinned by 45 % or more with 80 % probability (simulated;
> segment-thickness error 0.5 mm; this is not a sensitivity for scar).*

It is re-printed from JM-0R's `cv_n` and shape and the decision set's measured error by
`e5_ja18.detectable_depth()` (§7 item 1 procedure). A first run of the same grid gave 35 / 40 / 60 %. The 5-point
steps are therefore within run-to-run noise at 4000 hearts, and the line is printed from one fixed seed.

**Result 3: the κ gate measures the decision set's infarct prevalence, not the sign.**
P(gate passes) on a 40-patient decision set, at `cv_n` 0.088 and 40 % thinning:

| Error | Prevalence 0 % | 10 % | 30 % | Rule C + F1 sensitivity (range over the three draws) |
|---|---|---|---|---|
| 0.25 mm | κ: **0.05** · ICC: 0.99 | κ: 0.82 · ICC: 1.00 | κ: 1.00 · ICC: 1.00 | 0.95–0.98 |
| 0.5 mm | κ: **0.01** · ICC: 0.00 | κ: 0.59 · ICC: 0.25 | κ: 0.88 · ICC: 0.92 | 0.80–0.85 |
| 1.0 mm | κ: 0.00 · ICC: 0.00 | κ: 0.15 · ICC: 0.00 | κ: 0.09 · ICC: 0.01 | 0.32–0.40 |

- **With no infarcts in the decision set, κ fails at every error level**, including 0.25 mm, where the sign finds 95 %
  of 40 % thinning. Both reads then flag only chance territories, and chance flags do not agree. ImageCAS-X training
  cases are referrals for CCTA, so their infarct prevalence is unknown and may be low.
- **ICC passes or fails by measurement error, mostly.** At 0 % prevalence it passes 99 % of the time at 0.25 mm and
  never at 0.5 mm: normal patient-to-patient variation gives the reads something to agree on. It still rises with
  prevalence.
- **The detectable depth (Result 2) depends on no prevalence at all.** It needs only the read error, which F1 already
  measures.

**Result 4: the composite pattern is rare under the null.** Each sign is calibrated to about 5 % of patients:

| Correlation ρ of the three null scores | 0 | 0.3 | 0.6 | 0.9 |
|---|---|---|---|---|
| Any single sign flagged | 13.7 % | 13.4 % | 12.5 % | 9.4 % |
| Composite (thinning and fat-or-hypoattenuation) | **0.14 %** | 0.42 % | 1.2 % | 2.8 % |

- One patient in seven carries some single-sign flag by chance. This is Hotel's multiplicity argument, now at
  territory level.
- The composite stays below 3 % even for strongly correlated signs. Its **measured** rate on the reference population
  (JA18) is what the page reports. A rate above 5 % would mean the signs share an artefact.

**What it changes (Lima v2 proposals).**
1. **Replace JA18's κ ≥ 0.6 gate with a prevalence-free one.** A sign is shown as a flag only if its detectable depth
   (Result 2), computed with the decision set's *measured* read error, is ≤ 50 %. Otherwise it is a number only.
   κ and ICC stay reported. As written, the κ gate would turn a working sign into "number only" whenever the
   decision set happens to hold few infarcts.
2. **The page line is 45 % at 0.5 mm**, re-printed from JM-0R and the reads.
3. **The composite is reported as a pattern, with its measured rate.** It needs no two-segment rule unless that rate
   exceeds 5 %, as Hotel proposed.

**Limits.**
- This is a simulation. The read error is assumed equal to the model error and independent per segment.
- `cv_n` and the shape come from 1.5 mm model-made labels.
- The composite null treats fat as a continuous score, whereas the real fat sign is a cluster count.
- RC is taken as known. From 20 reads its SD estimate has a 95 % CI of about ×0.76–1.46, so the configuration uses
  the upper bound (Lima v2 §4).

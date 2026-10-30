---
aliases: [India - R4 E11 Lima's 45 percent and Hotel's 35 percent differ by the wall median, not the F1 code]
tags: [janus-m, experiment, india, round-4, path-rest-ccta, thinning, detectable-depth, calibrate]
status: done
round: 4
path: jm/rest-ccta
advocate: India
updated: 2026-10-30
issue: christianGRogers/Asclepius#205
---

# India R4 E11: Lima's 45 % and Hotel's 35 % differ by the wall median, not the F1 code

**Question** (#205 item 2; Round 3 ruling §1.2 (5), §8 item 2). For nominally the same inputs (cv_n 0.088,
Lima's 16-segment shape, mixed phase, prevalence 0.1), Lima E5 printed a detectable depth of 45 % and Hotel E7 35 %.
Why? And which wall median is right for JA40?

Used by [[India v4]]. Code: `experiments/JanusM/India/r4/e11_f1_reconcile.py`. Numbers:
`experiments/JanusM/India/r4/e11_f1_reconcile.json`.

## Setup

- **CPU simulation only.** No case, image or label was opened. `janusm.guard.refuse([])` is called first, as a
  record. There is nothing to open.
- **Every row uses the shipped `janusm.calibrate`** (`CALIBRATE_VERSION` 1.0.0), with the same parts each time:
  - the population (`population`);
  - rule C (`rule_c_scores`), the mirror-null cut (`calibrate_c`) and territory flags;
  - the same seed sequence (E7's: first seed 31000, population seed s, null seed s + 1);
  - the same read-out (JA40): 4 replicates of 2000, depths 0.10–0.60, the smallest depth with mean territory
    sensitivity ≥ 0.80.
- **One factor changes at a time** between Hotel E7 and Lima E5:

| Factor | Hotel E7 (S3 as shipped) | Lima E5 (`Lima/r3/e5_ja18.py`) |
|---|---|---|
| `median_mm` (the population's median wall, before phase) | 9.668 mm (Lima's own self-test on 23 public hearts, 1.5 mm model-made labels) | 5.7 mm (Chen 2025, end-diastolic CT) |
| F1 deviation | shape-corrected: remote level × shape − segment, mean over the territory | raw: remote median − territory mean |
| F1 floor | 1.0 mm (JA40's provisional) | RC = 1.96 × √2 × σ_m / √k = 0.26–0.31 mm at σ_m 0.5 |
| σ_m added | 0 | 0.5 mm |
| Read-out | 4 × 2000 per depth, from 0.10 | 1 × 4000 per depth, from 0.15, one shared stream |

## Result

Detectable depth (mean territory sensitivity at that depth in brackets), cv_n 0.088, seed 31000:

| Row | median_mm | F1 deviation | F1 floor | σ_m | Depth | Simulated median wall |
|---|---|---|---|---|---|---|
| A: Hotel E7 as shipped | 9.668 | Hotel | 1.0 | 0 | **0.35** (0.90) | 10.69 mm |
| B: A at 5.7 mm | 5.7 | Hotel | 1.0 | 0 | **0.45** (0.85) | 6.31 mm |
| C: A + σ_m 0.5 | 9.668 | Hotel | 1.0 | 0.5 | 0.35 (0.86) | 10.71 mm |
| D: B + σ_m 0.5 | 5.7 | Hotel | 1.0 | 0.5 | 0.50 (0.87) | 6.33 mm |
| E: D with Lima's floor | 5.7 | Hotel | Lima RC | 0.5 | 0.40 (0.84) | 6.33 mm |
| **F: Lima E5's procedure** | 5.7 | Lima | Lima RC | 0.5 | **0.40** (0.82) | 6.33 mm |
| G: F with a 1.0 mm floor | 5.7 | Lima | 1.0 | 0.5 | 0.50 (0.83) | 6.33 mm |
| H: F at 9.668 mm | 9.668 | Lima | Lima RC | 0.5 | 0.35 (0.87) | 10.71 mm |
| I: rule C alone | 5.7 | — | none | 0.5 | 0.40 (0.90) | 6.33 mm |
| J: rule C alone | 9.668 | — | none | 0 | 0.30 (0.90) | 10.69 mm |
| K: population median 5.7 after phase | 5.122 | Hotel | 1.0 | 0 | 0.50 (0.82) | 5.67 mm |
| L: R3 window, low end | 4.2 | Hotel | 1.0 | 0 | 0.60 (0.81) | 4.65 mm |
| M | 6.5 | Hotel | 1.0 | 0 | 0.40 (0.82) | 7.19 mm |
| N: R3 window, high end | 8.0 | Hotel | 1.0 | 0 | 0.35 (0.86) | 8.85 mm |
| O: population median 9.668 after phase | 8.688 | Hotel | 1.0 | 0 | 0.35 (0.88) | 9.61 mm |

Every row's largest false-flag share is ≤ 0.039 (≤ 0.025 with F1). The shipped `detectable_depth` returns
row A (0.35) and row B (0.45) exactly. The phase mix multiplies the median by 1.113 (simulated median ÷
`median_mm`, 200 000 hearts).

**Lima's own read-out, by seed** (row F's procedure with one population of 4000 per depth): 0.40 on 19 of 21
seeds, and 0.45 on 2. At 0.40, row F's sensitivity is 0.815, just above the 0.80 line. Lima's E5 table agrees: 0.80
at 40 % and σ_m 0.5.

## What it means

1. **The 35 % vs 45 % gap is the wall median, not the F1 code.**
   - At the same median, Hotel's and Lima's deviations give the same depth (E against F: 0.40 and 0.40; D against
     G: 0.50 and 0.50).
   - F1's floor is in millimetres, but thinning is relative. At a 1.0 mm floor a thinned territory clears it at a
     depth about 1.7 times smaller on a 9.67 mm wall than on a 5.7 mm wall. Rows A, B and L–N show the trend: 0.60 at
     4.2 mm, 0.45 at 5.7 mm, 0.35 at 8.0 mm and above.
   - Lima's two other differences pull in **opposite directions** and nearly cancel:
     - σ_m 0.5 adds 0.05 (B → D);
     - Lima's lower floor (0.26–0.31 mm in place of 1.0 mm) takes 0.10 off (D → E).
   - Lima's printed 45 % is the high draw of a single-population read-out whose typical value is 40 %. Its
     procedure on E7's replicated seeds gives 0.40.
   - **So JA40's procedure stands** (§8 item 2): S3 exposes no error in Hotel's F1. It exposes an input that the
     ruling did not fix.
2. **The median is as strong an input as cv_n.** Across R3's own plausible window (4.2–8.0 mm), the printed depth
   runs from 60 % to 35 %. cv_n's range (0.06–0.15) moves it from 20–25 % to 45 % (Hotel E7).
3. **Which median is right for JA40: not 9.668 mm.** Three reasons:
   - **It fails the plan's own check.** 9.668 mm is outside JA43 R3's window (4.2–8.0 mm). The plan would call a
     measured median of 9.668 a thickness-definition failure, and would ship no thinning flag on it.
   - **It is the wrong labels.** It is the median of 1.5 mm model-made TotalSegmentator labels on 23 hearts.
     `Lima/local_check.py` says those absolute numbers "describe those labels, not CCTA truth".
   - **Phase is counted twice.** `population()` multiplies `median_mm` by the phase factor (1.00 / 1.14 / 1.40). That
     is right for an end-diastolic anchor (5.7 mm), which is how Lima built it. A median measured over mixed phases
     is already phase-mixed, so E7's simulated population has a 10.7 mm median wall.
4. **Before JM-0R:** the conservative, JA40-consistent provisional input is Lima's end-diastolic anchor, **5.7 mm**,
   with the phase mix. That gives **45 %**. The page then also carries JA40's "> 40 %" sentence.
5. **After JM-0R:** the median must be JM-0R's own `thickness_median_mm`, measured on the borders of the model that
   fills the table. It should enter so that the **simulated** population median equals it (`median_mm` =
   measured ÷ 1.113), because the measured value is already phase-mixed. Today neither caller does this:
   - **`jm0r_decide.py` R9 passes no median**, so it always uses 9.668 mm, whatever JM-0R measures;
   - **`janusm.reference`** passes the measured `median_level` directly, so it multiplies a mixed-phase median by
     the phase mix again (about +11 %, the lenient direction; rows A and O both give 0.35, so the effect is small
     at 9.7 mm, but at 5–6 mm one step is likely: compare B, K and M).

   [[India v4]] §3 writes both as `role:swe` specs.

## Limits

- **One seed sequence** for the factor rows. The 0.05-step grid makes a one-step move between neighbouring
  conditions within seed noise when sensitivity is near 0.80 (rows E, F, K and M are within 0.02 of the line).
  The median trend holds across five medians.
- **The 1.113 factor holds for cv_n 0.088 and this phase mix.** It should be computed, not hard-coded (the
  spec says so).
- **Every number is a simulation of segment thicknesses**, not a sensitivity for scar.

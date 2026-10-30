---
aliases: [India - R3 E9-E10 estimators validated, detectable depth, and the JM-0R rules]
tags: [janus-m, experiment, india, round-3, path-rest-ccta, estimators, bias-guard, thinning]
status: done
round: 3
path: jm/rest-ccta
advocate: India
updated: 2026-10-30
issue: christianGRogers/Asclepius#167
---

# India R3 E9–E10: the JA15 estimators validated, detectable depth, and the JM-0R rules

**Questions** (ruling R2 §7):
- **Item 2:** do the ASSD, signed-bias and thickness implementations recover a known border shift to within ±0.05 mm
  (JA16), which decides a 0.3 or 0.5 mm bias guard?
- **Item 3:** what thinning depth does Lima's rule C detect with a measured segment shape and cv_n, at the
  measurement error of a model on JA8's edge?
- **Item 1:** what exactly happens to JM-0R's numbers?

Used by [[India v3]]. Code: `experiments/JanusM/India/` (`e9_estimators.py`, `summarise_e9.py`,
`e10_detectable_depth.py`, `jm0r_rules.py`). Numbers: `results/e9_estimators.json`,
`results/e10_detectable_depth.json`.

## Data and the guard

- **Public TotalSegmentator v1 masks fetched in Round 2** after the twin rule (299 heart-covering subjects; Round 2
  note). No Round 1 list was reused (JA22).
- **Every case** went through `janusm.guard.refuse_one(sid, source="TotalSegmentator")` (the shared guard) before any
  byte was read, and then through India's R2 guard in the loader. The two agree on all 299: 0 refused.
- No CT was read in Round 3, and no held-out subject, twin, ImageCAS or pool case was opened.
- **QC** as in Round 2 (LV crop inside the field of view, cavity enclosed). E9 used the first 24 that passed of 46
  tried, and E10 the first 22 of 40.

## E9: estimators against exact and continuum truth

**Method.** Binary masks only, as a read or a model gives them.

1. **Spheres (exact truth):** 40 spheres, pool radius 15–25 mm, wall 6–11 mm, random sub-voxel centre, 0.5 mm grid.
   One radius is moved by b ∈ {−0.5, −0.3, +0.3, +0.5} mm. The truth is a signed bias of b, an ASSD of |b|, and a
   thickness change of −b (endocardium) or +b (epicardium).
2. **Real walls (continuum truth):** 24 public hearts on JA15's 0.5 mm grid (Golf's half-voxel SDF zoomed from the
   1.5 mm labels).
   - **The shift:** one border's SDF is moved by a nominal b, alone or with independent random fields (RMS 0.25 mm,
     8 mm) on both borders.
   - **The truth:** the mean outward displacement of the zero level set, measured on the continuous fields, as
     ΔV / A by the coarea formula with a one-voxel occupancy ramp (`continuum_bias`).
   - **Why not b itself:** the zoomed SDF's slope is not 1 (median |∇| = 1.05 in the border band), so b is not the
     shift. The thickness truth is the difference of the two borders' continuum shifts; that is only approximate for a
     segment median.

**Estimators tested:**
- **bias:**
  - voxel centres (India R2): the mean SDF of the test object at the reference surface voxels;
  - symmetrised voxel centres;
  - **volume**: the signed voxel-count change in a 2 mm band around the myocardium-facing border, divided by the
    mean area of the two borders (marching cubes on each mask smoothed by 1 voxel).
- **ASSD:** surface-voxel ASSD on the myocardium-facing border; `segtrain.metrics.surface_distances` on the whole
  object.
- **Thickness:** d_endo + d_epi − h per segment, aggregated three ways (median over voxels, as JA8; mean; mid-wall
  0.4 ≤ u ≤ 0.6), then the median over segments 1–16.

**Result 1: signed bias, error = estimate − truth (mm).** Median, with the share of cases within ±0.05 in brackets:

| | Voxel centres | Symmetrised | **Volume ΔV / Ā** |
|---|---|---|---|
| Spheres, ±0.5 (worst of 4) | 0.12 (0 %) | 0.04 (100 %) | **0.001 (100 %)** |
| Spheres, ±0.3 (worst of 4) | 0.11 (0 %) | 0.03 (100 %) | **0.001 (100 %)** |
| Real, endo in 0.5 | −0.07 (0 %) | +0.01 (100 %) | **−0.02 (96 %)** |
| Real, endo out 0.5 | −0.13 (0 %) | −0.05 (63 %) | **−0.03 (100 %)** |
| Real, epi in 0.5 | −0.08 (0 %) | −0.01 (100 %) | **−0.02 (100 %)** |
| Real, epi out 0.5 | −0.11 (0 %) | −0.02 (100 %) | **−0.01 (100 %)** |
| Real, endo out 0.3 | −0.13 (0 %) | −0.07 (25 %) | −0.05 (58 %) |
| Real, epi in 0.3 | −0.18 (0 %) | −0.09 (0 %) | −0.09 (0 %) |
| Real, epi out 0.3 | −0.16 (0 %) | −0.08 (0 %) | −0.04 (88 %) |
| Real, 0.5 + random 0.25 (worst) | −0.15 (0 %) | −0.08 (0 %) | −0.08 (4 %) |

- **JA16's test passes with the volume estimator.** A known 0.5 mm shift, in each direction, on each border, is
  recovered to within ±0.05 mm in ≥ 96 % of real walls and in every sphere.
- **Its residual error is one-sided:** 0.01–0.09 mm too far inward on real walls. So outward biases read up to about
  0.05 mm low, and inward biases read high, which makes the guard fire early.
- **India R2's voxel-centre estimator fails everywhere** (it is the one the ruling flagged); it must not be used.

**Result 2: ASSD (no random field), error vs |truth|.**
- Spheres: +0.04 at 0.5 mm, +0.06 at 0.3 mm, for both implementations (the surface-voxel offset).
- Real walls: +0.04 to +0.09 (band) and +0.04 to +0.07 (`segtrain`) at 0.5 mm.

The offset is common to model-vs-read and read-vs-read, and so largely cancels in JA8's d.

**Result 3: thickness change, error (mm).**
- Spheres: all three variants ≤ 0.007.
- Real walls, against the approximate truth: the JA8 median-over-voxels variant is within 0.07 at 0.5 mm and 0.11 at
  0.3 mm. The mean and mid-wall variants are no better.

**Result 4: realised vs nominal.** A nominal SDF shift realises 0.94–0.99 of itself on the endocardium and 0.84–0.90
on the epicardium. E5's (Round 2) bias rows were nominal; JA15 indexes by realised ASSD, so no ruling depends on it.

**What it changes:**
- the signed-bias guard is 0.3 mm (JA16's condition met), measured by ΔV / Ā;
- JA15's one ASSD is `segtrain.metrics.surface_distances`;
- JA8's thickness definition stays;
- E9's cases become the module's fixture tests ([[India v3]] §6.1).

## E10: Lima's E3 with a measured shape and cv_n

**Method.**
- **Measured on 22 public hearts, JA15's 0.5 mm walls:**
  - segment thickness (median over each segment's voxels);
  - the shape (median over hearts of thickness ÷ the heart's median);
  - cv_n (robust SD of log relative thickness after the shape);
  - under U at σ 0.25 and 0.5 (realised ASSD ≈ 0.21 and 0.36 mm, Round 2 E5), the per-segment thickness-error SD
    (sig_m).
- **Simulation:** Lima's `calibrate_sim.py`, imported unchanged (population, rule C, mirror-null calibration), run
  with these inputs at depths 0.15–0.60.

**Result.**
- **Shape:** r = 0.97 against Lima's 1.5 mm self-test shape (largest difference 0.08).
- **cv_n = 0.053.**
- **sig_m:** 0.24 mm at ASSD 0.21 mm; 0.43 mm at ASSD 0.36 mm.
- The median public-label thickness is 9.0 mm (v1 labels, as in Rounds 1–2). The simulation keeps Lima's 5.7 mm
  end-diastolic scale, which makes the result conservative.

| cv_n | depth for 80 % territory sensitivity, sig_m 0 / 0.24 / 0.43 mm | max null false-flag rate |
|---|---|---|
| 0.053 | 20 % / 25 % / **30 %** | 3.6 % |
| 0.06 | 20 % / 25 % / 30 % | 3.5 % |
| 0.10 | 35 % / 35 % / 40 % | 3.5 % |

- Mixed-phase and all-end-diastolic populations give the same depths, and so do the measured and Lima's shapes.
- **Provisional page sentence:** "finds about 80 % of territories thinned by 30 % or more, in simulation; not a
  sensitivity".
- JM-0R's cv_n and shape replace these inputs (rule R9), and the reads' RC replaces sig_m.

**Limits.** cv_n on model-made labels is neither an upper bound (label error adds to it) nor a lower bound (model
smoothing removes from it). The simulated infarct is Lima's: 2–4 contiguous segments of one territory.

## The JM-0R rules (item 1)

`jm0r_rules.py` applies R1–R10 ([[India v3]] §3) to JM-0R's aggregate JSON, or to the three fallback add-ons via
`merge_fallback`. The fallback reconciles signs: Hotel's endocardial offset is + into the blood and is negated.

**Tested on:**
- a synthetic JM-0R JSON, for every decision path;
- synthetic Lima and Hotel aggregates in their committed key layouts.

No real JM-0 output exists yet; the script was written before any.

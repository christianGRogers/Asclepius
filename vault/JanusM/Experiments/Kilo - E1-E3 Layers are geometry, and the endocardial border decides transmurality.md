---
aliases: [Kilo E1-E3]
tags: [janus-m, experiment, layers, transmurality, aha17, tpr, kilo]
status: done
round: 1
updated: 2026-10-30
---

# Kilo E1–E3: layers are geometry, and the endocardial border decides transmurality

**Questions.**
- E1: Can the myocardial layers, wall thickness and the AHA 17 segments be computed from a wall mask alone, and
  with how many voxels across the wall?
- E2: How does an error in the wall's borders propagate to the layers and to a scar's segmental
  transmurality? Does Dice see it?
- E3: Is rest transmural attenuation (TPR) stable enough to report?

**Data.**
- 40 public TotalSegmentator v1 cases (Zenodo 6802614, CC BY 4.0) with study type "ct heart", "ct coronary
  arteries" or "ct aortic valve", fetched by HTTP range (`fetch_ts_cardiac.py`).
- **Before any download, every TotalSegmentator id in a held-out list was refused in code** (`heldout.py`): the
  pool seal, the pool list, the reserve, every Round 10 D35 draw (Atlas, Bridge, Crucible, Delta, Foxtrot) and
  the ImageCAS-X seal. That is 16 ids, and 0 of the 40 match.
- 39 cases were analysed. s0597 has no LV in its mask. 29 have a contrast-enhanced LV cavity (median > 150 HU;
  median 299 HU); 10 are non-contrast and are left out of E3 only.
- **Caveats:**
  - the masks are TotalSegmentator's own model-made labels;
  - the grid is 1.5 mm isotropic;
  - many cases are not ECG-gated CCTA, and the phase is unknown.

  So the anatomy is real, but neither its accuracy nor its phase is that of the project's CCTA. E2 measures how
  an error propagates, not the labels' accuracy.

**Method.** Code is `experiments/JanusM/Kilo/layers.py` and `exp_layers.py`; numbers in `results_e123_grid05.json`
and `summary_e123_grid05.json` (`summarise.py`). CPU, 4 cores, about 100 min.
- **Layers.** Transmural depth t comes from Laplace's equation on the wall (sparse CG). Endocardium = faces
  touching the LV cavity; no-flux at the left atrium and aorta. Thirds come from t; thickness = d_endo + d_epi − one
  voxel. AHA 17 segments come from the long axis (principal axis, oriented by the LA) and the RV centroid
  direction (§1.2 of [[Kilo v1]]).
- **E2.** Each case's signed distance fields are resampled to a **0.5 mm grid**, which is CCTA-like, and the
  reference is recomputed there. The endocardial and the outer (wall + cavity) surfaces are then perturbed by:
  - smooth random displacement fields (Gaussian, 10 mm correlation length, RMS σ = 0.5 / 1.0 / 1.5 mm; two
    repetitions);
  - or a uniform 1 mm endocardial shift, inward (the wall grows into the cavity) or outward.

  Everything is recomputed on each perturbed wall. **Virtual scars:** in each segment 1–16, the reference voxels
  with t < τ, for τ = 0.15 / 0.40 / 0.65 / 0.90 (the centres of Kim's bins). They are fixed in the image. Each
  scar's segmental transmurality is its share of the segment's wall, measured inside the reference wall and
  inside the perturbed wall. **STA** = the share of the 64 scars whose bin (0, 1–25, 26–50, 51–75, 76–100 %)
  agrees.
- **E3.** On the native 1.5 mm grid, TPR = mean HU of the subendocardial third / mean HU of the subepicardial
  third, per segment (George 2009's definition), with and without a 1-voxel guard band. It is repeated under
  σ = 1 mm random boundary error.

## E1: the geometry runs, and the wall is about 19 voxels thick at 0.5 mm

Values are medians [IQR] over the 39 cases.

| Quantity | Value |
|---|---|
| LV myocardial volume | 144 ml [110, 175] |
| Wall thickness, voxel-wise p10 / p50 / p90 | 7.1 / 9.6 / 12.6 mm |
| Voxels across the wall at 1.5 mm | 6.4 [5.8, 6.6] |
| Voxels across the wall at 0.5 mm | 19.7 [17.8, 20.3] |
| Same third by Laplace and by distance ratio | 0.876 [0.871, 0.879] |

Segmental median thickness follows known anatomy: the mid septum is thickest (segments 8–9: 12.2–12.3 mm), the
apical segments thinner (13–16: 7.6–8.5 mm) and the apex cap thinnest (17: 6.4 mm). These walls are thicker than
CMR end-diastolic norms (mid-cavity means 5.3 / 6.3 mm in women / men; Kawel 2012). Three reasons, which
cannot be separated here:
- the phase is unknown (systolic walls are thicker);
- the measures differ: a voxel-wise d_endo + d_epi is not a short-axis chord;
- partial volume at 1.5 mm.

Job M0 measures the same thing on sub-millimetre CCTA. **The two depth definitions disagree on 12 % of voxels.**
The definition must be fixed, and Kilo fixes Laplace (Jones 2000), since it is the one with nested,
non-crossing iso-surfaces.

## E2: the endocardial border decides transmurality, and Dice does not see it

Values are medians [IQR] over 39 cases. "Bin flip" = 1 − STA, overall and per scar depth τ.

| Boundary error | Myo Dice | Dice: subendo / mid / subepi third | Voxels changing third | Segment thickness MAE | Bin flip, all | Bin flip, τ = 0.40 / 0.65 / 0.90 |
|---|---|---|---|---|---|---|
| random, 0.5 mm | **0.980** | 0.939 / 0.958 / 0.960 | 2.7 % | 0.20 mm | **3.9 %** | 9.4 / 6.2 / 0.0 % |
| random, 1.0 mm | 0.960 | 0.873 / 0.915 / 0.916 | 5.4 % | 0.42 mm | 12.5 % | 18.8 / 21.9 / 9.4 % |
| random, 1.5 mm | 0.927 | 0.792 / 0.850 / 0.854 | 9.8 % | 0.73 mm | 28.9 % | 40.6 / 40.6 / 31.2 % |
| endocardium 1 mm outward (cavity grows) | **0.979** | 0.827 / 0.897 / 0.969 | 6.7 % | 0.48 mm | **12.5 %** | **37.5** / 18.8 / 0.0 % |
| endocardium 1 mm inward (wall grows) | 0.977 | 0.816 / 0.893 / 0.970 | 6.8 % | 0.52 mm | 7.8 % | 12.5 / 18.8 / 6.2 % |

τ = 0.15 never flipped bin. Mean signed transmurality errors are in the summary file. For example, an outward
endocardial shift removes 3.5–4.1 percentage points from shallow scars; this is the scar lying against the
endocardium.

**Readings.**
1. **Dice is blind to the error that matters.** A 1 mm outward endocardial bias and 0.5 mm random noise give the
   same myocardium Dice (0.979 vs 0.980). The bias flips **three times** as many scar bins (12.5 % vs 3.9 %),
   and four times as many mid-depth scars (37.5 % vs 9.4 %; the IQRs do not overlap). A model selected on Dice can carry
   a systematic endocardial bias unnoticed. **Hence STA as the deciding metric, with an endocardial-bias guard.**
2. **The subendocardial third is where the errors land.** Its Dice falls fastest in every row (0.82–0.83 under a
   1 mm endocardial bias, while the subepicardial third stays at 0.97). The subendocardium is exactly where
   ischaemic scar starts (Reimer 1977) and where fat sits (94 %; Ichikawa 2009). **A per-third Dice is the wrong
   score for a layer; a per-third error budget on the endocardium is the right one.**
3. **Published accuracy is not yet enough.**
   - The CCTA myocardium models in the literature report Dice 0.91–0.92 (Zreik 2018, Baskaran 2020). That is
     worse than the σ = 1.5 mm row (0.927), where **29 % of segmental scar bins flip**.
   - For transmurality bins to agree in ≥ 90 % of segments, the wall must be in the σ ≤ 0.5–1.0 mm regime with
     no systematic endocardial bias.
   - This sets Janus-M's accuracy bar above "a good Dice", and it is why Kilo v1's acceptance is relative to
     inter-read STA, measured on the seal.
4. **0.5–0.6 mm is a sufficient grid.** At 0.5 mm random error, layers and thickness barely move (2.7 % of voxels
   change third; 0.2 mm thickness error). A 0.6 mm training grid (about 16 voxels across the wall) is a
   reasonable cost point; 0.4 mm would buy little.
5. **The seal's power.** The per-patient SD of STA is 0.13 under random 1 mm error and 0.035–0.04 under a
   uniform bias. The spread is mostly within-patient randomness: two repetitions on the same case differ with
   SD 0.10. On 20 patients, the minimum detectable unpaired STA difference (2.8 × SD / √20) is therefore about
   **0.08**. A paired comparison of two models on the same reads will do better. A 20-patient seal can tell a
   biased wall from a good one (0.87 vs 0.93), not a 0.02 refinement.

## E3: rest transmural attenuation is not reportable at this resolution

On 29 contrast cases (1.5 mm), per-segment rest TPR has median **1.93 [1.04, 2.90]**. With a 1-voxel guard band
it is 1.54 [1.11, 2.33]. The within-patient SD across segments is 4.2 [2.6, 11.5], so ratios explode where the
subepicardial mean nears 0 HU. 24 % of segments fall below 0.99 in patients not selected for ischaemia. Under
1 mm random boundary error, **48 % of segments move by more than 0.05**; the median shift is 0.045.

**Reading.**
- At 1.5 mm, rest TPR is dominated by partial volume: blood pool in the subendocardium, epicardial fat in the
  subepicardium. It is not physiology. George 2009 used stress CTP at 0.5 mm, with a reference standard.
- **Kilo v1 keeps A4 (rest attenuation per layer) as report-only, and makes no rest-ischaemia claim.**
- Round 2 repeats E3 on sub-millimetre CCTA once M0 returns. If within-patient SD there is still much larger than
  any plausible effect, A4 is dropped.

## What it changes

- **Layers are computed, not learned** (Kilo v1 §1.2): the geometry works on every analysable case and is
  anatomically plausible.
- **Deciding metric: STA, with an endocardial signed-bias guard** (§6.2), because Dice does not separate a wall
  that keeps transmurality from one that does not.
- **Grid 0.6 mm** (§6.1).
- **Rest TPR: report-only** (A4).
- **Not shown here:**
  - real CCTA geometry at native resolution (Job M0);
  - the labels' accuracy against a human read (the seal's double reads);
  - patient-specific territories (needs Janus's tree on the same volumes; Job M2).

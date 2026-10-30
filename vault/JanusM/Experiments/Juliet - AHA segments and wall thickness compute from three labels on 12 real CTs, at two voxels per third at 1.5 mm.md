---
tags: [janus-m, experiment, aha-17, thickness, totalsegmentator, real-labels]
author: Juliet
round: 1
updated: 2026-10-30
---

# AHA segments and wall thickness compute from three labels on 12 real CTs, at two voxels per third at 1.5 mm

## Question

Juliet v1's network outputs borders only. Can the AHA 17-segment model, wall thickness and transmural depth be
computed automatically, on real anatomy, from the LV cavity, LV myocardium and RV cavity (plus the LA and aorta for
the valve plane)? And what does a public myocardium label set at 1.5 mm give per transmural third?

## Method

`experiments/JanusM/Juliet/real_labels.py`, output `real_labels.json`.

- **Data.** The TotalSegmentator v1 dataset (Wasserthal 2023, [10.1148/ryai.230024](https://doi.org/10.1148/ryai.230024);
  Zenodo [10.5281/zenodo.6802614](https://doi.org/10.5281/zenodo.6802614), **CC BY 4.0**, 1204 CT). It is the only
  open release with `heart_myocardium`; v2 dropped the heart-chamber classes. Twelve subjects were pulled by HTTP
  range from the zip (labels only; images not used).
- **Selection (pre-registered, salted).** Eligible: study types "ct heart", "ct coronary arteries", "ct aortic valve"
  and "ct heart-thorakale aorta" (103 subjects). The 16 subject ids the coronary pool holds
  (`TotalSegmentator-cardiac`) are excluded. Ranked by sha256(`janusm-juliet-r1:` + id); the first 12 are used
  (s0424, s0877, s1230, s0935, s1190, s1018, s0452, s0349, s1248, s0338, s0439, s0834). Every label is on a 1.5 mm
  isotropic grid.
- **Pipeline** (all computed, no learning):
  - **Valve plane:** LV-cavity voxels within 3 mm of the LA or aorta.
  - **Long axis:** from the valve plane to the farthest myocardial voxel. Rings are the thirds of the axis, plus an
    apical cap above 0.9 (Cerqueira 2002, [10.1161/hc0402.102975](https://doi.org/10.1161/hc0402.102975)).
  - **Circumferential:** angle around the axis, 0° at the RV centroid (septum centre), signed towards the patient's
    anterior. Six 60° sectors at base and mid, four 90° sectors at the apex.
  - **Depth and thickness:** depth = d_endo / (d_endo + d_epi); thickness = d_endo + d_epi at mid-wall.
- **Not measured.** No reference segmentation of segments exists for these subjects, so this is a plausibility and
  resolution check, not an accuracy measurement.

## Result

- **All 12 subjects processed without manual input.** LV long axis 78–96 mm. Median wall thickness per subject
  8.0–10.7 mm (10th–90th percentile range 6.0–14.5 mm).
- **Pattern by segment** (median of the 12 subjects' segment medians):
  - **Septum thickest:** basal anteroseptal 12.9 mm, basal inferoseptal 11.4, mid anteroseptal 11.1, mid
    inferoseptal 12.0.
  - **Basal and mid free wall 8.1–10.3 mm.**
  - **Apical segments thinnest, 7.2–7.9 mm.**

  This is the expected anatomical order; a wrong axis or a wrong septum direction would scramble it.
- **Voxels per third at 1.5 mm: median 1.8–2.4 per subject.**
- **Mid-wall voxels under 5.5 mm: 1.2–6.5 % per subject.** E1 shows a −0.5 to −0.7 mm thickness bias at 1.5 mm, so
  these flags are unreliable at this grid.

## What it changes

1. **The segment and layer outputs need no learned classes.** Janus-M's network outputs four labels; segments,
   depth and thickness are deterministic code that runs per case in seconds. The code goes to a `role:swe` issue as
   a versioned module.
2. **TotalSegmentator v1 labels (1.5 mm) are pretraining or seed material, not a layer reference.** Two voxels per
   third with a −0.5 mm thickness bias is too coarse for thinning flags. Janus-M trains and reports at 0.5 mm, the
   grid Atlas showed loses no image content on ImageCAS
   ([[Atlas - Resampling to 0.5 mm isotropic loses nothing measurable, 0.7-0.8 mm does]]).
3. **Job M0 repeats this on ImageCAS at native resolution.** It runs TotalSegmentator `heartchambers_highres` on 40
   training cases and the same pipeline (`experiments/JanusM/Juliet/fir/`). It also compares patient-specific
   coronary territories, from ImageCAS-X labels, with the AHA default. That is the first real number for how often
   the default assignment is wrong on this cohort. On MRI, Ortiz-Pérez 2008 found 23 % of infarcted segments
   discordant ([10.1016/j.jcmg.2008.01.014](https://doi.org/10.1016/j.jcmg.2008.01.014), abstract).
4. **Limits.**
   - TotalSegmentator's myocardium convention (where trabeculae and papillary muscles go) is the model's own, not a
     human protocol.
   - The cardiac phase of these scans is unknown, so thickness is not end-diastolic.
   - 12 subjects; no reader truth.

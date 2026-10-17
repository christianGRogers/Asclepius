---
tags: [plans, experiment, fp-gate, census, roi, a20, round8]
author: Foxtrot
round: 8
updated: 2026-10-11
---

# On atlas2's val FPs the heart-and-aorta ROI rule removes nothing, because the FPs sit on the heart

## Question

A20 condition 2, pre-registered in [[Round 6]]: do **≥ 25 %** of run 1's raw FP components lie more than
25 mm from the TotalSegmentator heart ∪ aorta? If so, what does the d = 25 mm rule do to FP/case and tF1?
In particular, where are the 79 % `confident_other` components?

## Method

**Inputs (read-only).**

- `trillium-results/round6/atlas2/results/census_run1.json` and `census_b.json`.
- `per_case_run1.json`.
- Run 1's 80 val segmentations (`$SCR/round6/atlas/.../fold_0/validation/`).
- atlas2's 80 TotalSegmentator aortas (`$SCR/round6/atlas2/aorta/`).

**Val CTs cached locally: 17 of 80.** They are c0001, c0038, c0133, c0163, c0225, c0252, c0288, c0368,
c0400, c0560, c0606, c0613, c0717, c0744, c0848, c0950 and c0956. No CT was downloaded.

- These 17 hold **26 of run 1's 119** raw FP components, 1.53 per case against 1.49 overall.
- The other 63 cases have no heart mask. They are **unknown**, bounded below, and not counted as passing.

**A. Exact, on the 17 cases.** Script: `experiments/Foxtrot/fp_roi_val.py`.

1. Run TotalSegmentator fast (3 mm) `heart, aorta` on the CT. This is the same procedure as the A20
   reference check.
2. For each raw predicted component (`raw_prediction`, 26-connected, ≥ 100 voxels), take its minimum
   distance to the ROI, using the 1 mm EDT.
3. Match FP components to census rows by voxel count, which gives their category; the match was unique in
   every case.
4. Apply the A20 rule (d = 25 mm; disabled if the heart mask has < 5000 voxels at 3 mm).
5. Re-score with atlas2's own `score.a1_score`, imported read-only: frozen metric copy, A1 ostium from
   atlas2's aorta and the CT, same crop.

The reference is the projected proxy, rebuilt with atlas2's `lib/proxy.make_label` from the Girder mask and
ImageCAS-X. It was deleted after use.

**Check.** Before the rule, all 17 cases reproduce atlas2's `per_case_run1.json` **exactly** (tF1 and FP
count). Summary: `experiments/Foxtrot/summarise_fpval.py`.

**B. Bound, on all 80 cases and both arms.** Script: `experiments/Foxtrot/fp_roi_bound.py`, from the census
columns alone. A component can be more than 25 mm from heart ∪ aorta only if:

- `dist_to_aorta_mm` > 25 (the aorta is in the ROI); and
- `dist_to_ref_mm` > 25 − R, by the triangle inequality, where R is the case's maximum reference-to-ROI
  distance.

I take R = 16.5 mm, the maximum over the 92 non-sealed cases measured
([[Foxtrot - The ImageCAS reference lies wholly within 17 mm of a TotalSegmentator heart-and-aorta ROI]]).
This is an assumption for the 63 val cases not measured, so a sensitivity analysis is given.

## Result

**A. Exact (17 cases, 26 FP components: 22 `confident_other`, 3 `icx_vessel`, 1 `low_confidence`)**

| Quantity | Value |
|---|---|
| FP minimum distance to heart ∪ aorta | 10/25/50/75/90 % = 0.0 / 0.0 / 1.7 / 3.0 / 5.7 mm; **max 12.8 mm** |
| FP components beyond 25 mm | **0 of 26 (0 %)**; beyond 15 mm: 0; beyond 10 mm: 2 |
| `confident_other` (22) distance bins | ≤ 0 mm (inside the mask): 8; 0–5: 10; 5–10: 2; 10–15: 2; > 15: 0 |
| Rule effect | 0 components deleted; FP/case 1.529 → 1.529; tF1 and decisive tF1 unchanged in all 17 cases |
| Reference-to-ROI max on these cases | 16.4 mm (A20 condition 1 holds here too) |

`dist_to_ref` and `dist_to_aorta` are misleading on their own. The component in c0288 is 41.8 mm from the
reference but **6.4 mm** from the heart. Several are > 25 mm from the aorta and lie on the heart surface.
The FPs are **epicardial**, so the heart mask itself absorbs them.

**B. Upper bound, all 80 cases**

| Census | All FP: may lie beyond 25 mm (upper bound) | `confident_other` |
|---|---|---|
| run 1 (119 components) | ≤ 20 (**≤ 16.8 %**) | ≤ 13 of 94 (≤ 13.8 %) |
| B, default window (104) | ≤ 20 (**≤ 19.2 %**) | ≤ 15 of 78 (≤ 19.2 %) |

Sensitivity to R (run 1 / B): R = 18 mm gives ≤ 17.6 % / ≤ 25.0 %; R = 20 mm (A20's allowed limit) gives
≤ 25.2 % / ≤ 29.8 %. The bound is far from tight: on the 17 measured cases it allows 4 components, and 0
qualify.

**Where `confident_other` lies, all 80 (run 1).**

- `dist_to_ref`: median 3.4 mm, p75 8.5, p90 14.7. Bins < 2 / 2–5 / 5–8.5 / 8.5–15 / 15–25 / > 25 mm hold
  25 / 36 / 9 / 15 / 6 / 3 components.
- `dist_to_aorta`: median 31.8 mm.

So two-thirds of the confident FPs are within 5 mm of the reference tree. The rest lie on the heart surface.

## What it implies

1. **A20 condition 2 fails.** On the 17 measured cases, 0 % of FP components lie beyond 25 mm (needed:
   ≥ 25 %). For all 80, the bound is below 25 % in both arms at R ≤ 16.5 mm, and in run 1 also at 18 mm.
   F3 removes nothing and changes nothing on val. **I withdraw F3** ([[Foxtrot v3]]).
2. **The confident FPs are not background clutter.** They sit on the epicardium and, for the most part,
   within a few millimetres of the tree. This fits vessel the reference does not contain (veins, side
   branches beyond the mask, distal pieces cut off by the mask's extent) better than it fits lung or
   chest-wall hallucinations. The ROI / two-stage literature lever (TopCoW) targets the latter, so it does
   not transfer here. This is a hypothesis about cause, not a measurement. Telling vein from branch-beyond-mask
   needs a look or the ImageCAS-X overlap. Most of these are *not* ImageCAS-X vessel, since `icx_frac` is 0
   by category, which points at veins or at branches neither reference labels.
3. **No other post-hoc geometric filter can remove them safely.** Components at 1–5 mm from the reference
   are where real-but-unlabelled vessel would also sit. A deletion rule tight enough to catch them breaks
   the "removes no reference vessel" guarantee F3 was built on.

## Limits

- The exact part covers 17 of 80 cases (26 of 119 FP components); the rest is a bound. The bound uses
  R = 16.5 mm, measured on other cases; the sensitivity analysis is given above.
- Arm B's segmentations are not local, so only its census bound is available.
- The heart mask comes from the fast 3 mm model (about ±2 mm), the same model that froze the rule.
- The distance is the component's *minimum* distance, which is what the rule uses.

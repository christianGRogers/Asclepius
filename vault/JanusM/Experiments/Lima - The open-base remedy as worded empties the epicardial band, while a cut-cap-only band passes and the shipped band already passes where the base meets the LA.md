---
tags: [janus-m, experiment, round5, rest-ccta, harness, signed-bias, ja37, ja61, phantom]
author: Lima
round: 5
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#223
---

# Lima E1–E2: the open-base remedy as worded empties the epicardial band, while a cut-cap-only band passes and the shipped band already passes where the base meets the LA

**Question (#223 item 2).** R4-S4's open-base validation failed (epi ±0.5 mm: 0.068 mm on India's open phantom;
0.0504 mm on the cut capsule), so the bias guard is 0.5 mm (JA61). The #219 engineer proposed a remedy: also exclude
≤ 3 mm of any pool **or myocardium** face that adjoins label 0, because the cut basal cap adds area with no volume
change. Does that pass on the same phantoms, and is it safe on a read?

**Setup.** `experiments/JanusM/Lima/r5/e1_open_base_remedy.py` and `e2_la_capped_heart.py` use analytic phantoms
only. The guard is called first. Shipped code is unchanged: the variants live in the experiment.

Bands:
- **shipped** — `harness.ja37_band` as merged in #219;
- **literal** — the remedy as worded;
- **cap_plane** — a least-squares plane through the open pool faces, then drop ≤ 3 mm of the solid faces adjoining
  label 0 that lie within one voxel of that plane (only the cut cap);
- **slab** — the shipped band, less everything within 3 mm of that plane or beyond it.

Phantoms:
1. **India's open E6 phantom**, from the test file's helpers: two grids × three walls × both borders × ±0.3 / ±0.5 mm
   (24 rows per border). The truth is the mean normal displacement in the band.
2. **`validate_bias_estimator(open_base=True)`** at its defaults (3 offsets, 144 rows), with the band patched for
   the call.
3. **`harness.phantom()`**, the control: the base opens into the LA, the RV sits over the septum, and label 0 is
   everywhere else. Two grids × three walls × two offsets × both borders × ±0.3 / ±0.5 mm (48 rows per border),
   against the exact shift.

**Result** (worst |error|, mm; the tolerance is 0.05):

| Band | India open, epi | Cut capsule, epi | LA-capped, epi | LA-capped epi band kept | Endo, every phantom |
|---|---|---|---|---|---|
| shipped | 0.068 ✘ | 0.0504 ✘ | **0.017 ✔** | 100 % | ≤ 0.024 ✔ |
| literal | **empty, 24 / 24 rows** | **NaN in 72 / 72 rows** | 0.052 ✘ | 18 % | ≤ 0.024 ✔ |
| cap_plane | **0.016 ✔** | **0.0195 ✔** | 0.017 ✔ | 100 % | ≤ 0.024 ✔ |
| slab | 0.016 ✔ | 0.0195 ✔ | 0.017 ✔ | 100 % | ≤ 0.024 ✔ |

The shipped numbers reproduce #219 exactly (0.0678 and 0.05036). `cap_plane` and `slab` give the same 144 capsule
rows: worst 0.0238 mm overall (endo), so `passed` and a supported guard of 0.3 mm.

**Closed-shell control (E4, radii 12 and 21 mm, ±0.3 / ±0.5).** Shipped, `cap_plane` and `slab` are identical, within
0.004 mm on both borders: nothing is open, so the cap rules do nothing. `literal` keeps only 3 % of the epicardial
band, which has no faces left, so it gives NaN in 8 / 8 rows. It also trims 25–29 % of the endocardial band (the
voxels within 3 mm of the epicardium), though the endo still passes.

**What it changes.**
- **The remedy as worded cannot be adopted.** On a read, label 0 includes fat, pericardium and aorta, so the
  epicardium adjoins label 0 almost everywhere, and the rule removes the border it measures. An empty band makes
  `signed_bias` NaN, and `transfer_check` raises on it.
- **The failure comes from the phantom's cut to label 0.** Where the base meets the LA, as the mitral plane does on a
  read, the shipped band passes on both borders.
- **A cut-cap-only band** passes the open phantom and is a no-op on the LA-capped heart. It is a candidate for a later,
  pre-registered validation that also includes an aortic opening. Until then the guard stays 0.5 mm, as JA61 ruled.

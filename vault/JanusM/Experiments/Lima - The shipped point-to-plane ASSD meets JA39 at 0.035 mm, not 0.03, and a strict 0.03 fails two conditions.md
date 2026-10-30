---
tags: [janus-m, experiment, round4, rest-ccta, harness, assd, point-to-plane, ja39, phantom]
author: Lima
round: 4
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#205
---

# Lima E7: the shipped point-to-plane ASSD meets JA39 at 0.035 mm, not 0.03, and a strict 0.03 fails two conditions

**Question (#205 item 6, first note).** #198 reports that JA39's "0.03 mm" is Hotel E6's 0.032 rounded, and that a
strict 0.03 fails one condition. How close is the shipped `janusm.harness` pp to JA39, and what should the tolerance
say?

**Setup** (`experiments/JanusM/Lima/r4/e7_pp_tolerance.py` → `e7_pp_tolerance.json`; analytic phantoms only, no
case; the guard is called first on an empty list).
- The 72 conditions of `tests/test_janusm_harness.py::test_e6_pp_within_ja39_tolerances`:
  - two grids (0.5 mm isotropic; 0.4 × 0.4 × 0.5 mm);
  - three walls (axis-aligned, oblique, rough oblique);
  - both borders;
  - shifts ±0.25, ±0.5, ±1.0 mm.
- The test's own phantom and truth helpers, imported unchanged. The raw |error| of `assd_pp` and `signed_bias_pp` is
  recorded, not the test's `round(|error|, 2)`.

**Result.**

| Tolerance | Worst raw error (assd / bias) | Where | Strict fails |
|---|---|---|---|
| 0.03 mm (to 0.5 mm) | 0.0322 / 0.0322 | 0.4 mm grid, rough oblique, endo, −0.5 mm | **2 of 48** |
| 0.07 mm (at 1.0 mm) | 0.0669 / 0.0670 | 0.4 mm grid, rough oblique, endo, −1.0 mm | 0 of 24 |

- **A strict 0.03 fails two conditions, not one:**
  - the 0.4 mm grid's rough oblique endocardium at −0.5 mm (0.0322);
  - the 0.5 mm grid's rough oblique epicardium at −0.5 mm (0.030003, over by 3 µm).
- **The 1.0 mm row has 0.003 mm to spare.**
- **Every error grows with inward shift on the rough wall.** It is the only place where pp comes near either bound.
- **The test passes because it rounds.** `round(e, 2) <= 0.03` accepts any e below 0.035. So the shipped tolerance is
  0.035 mm in effect, but it is written as 0.03.

**What it changes.**
- **JA39's fixture tolerance should be stated as what is enforced: 0.035 mm up to 0.5 mm, 0.07 mm at 1.0 mm,** on the
  raw error with no rounding. A tolerance set at the measured worst (0.032) is not a tolerance. A rounding rule hides
  where the line is: a future change that moved the worst to 0.0349 would pass, and one at 0.0351 would fail, with
  no way to tell from the code.
- **No decision moves.** JA8's margin is 0.25 mm; the difference is 0.005 mm.
- **The spec (G3 in [[Lima v3]] §2):**
  - `PP_ASSD_TOLERANCE_MM = {0.5: 0.035, 1.0: 0.07}`;
  - the test compares `abs(e) <= tol`, without `round`;
  - the comment names E6's worst (0.032) and E7's (0.0322, 0.0669).

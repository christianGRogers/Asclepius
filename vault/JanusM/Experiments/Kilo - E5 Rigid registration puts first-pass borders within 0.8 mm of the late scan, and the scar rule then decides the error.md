---
aliases: [Kilo E5]
tags: [janus-m, experiment, registration, late-iodine-enhancement, scar, transmurality, kilo, paired-scar]
status: done
round: 2
path: jm/paired-scar
updated: 2026-10-30
code: experiments/JanusM/Kilo/e5_lie_registration.py, experiments/JanusM/Kilo/e5_hybrid.py
---

# Kilo E5: rigid registration puts first-pass borders within 0.8 mm of the late scan, and the scar rule then decides the error

**Question** (Round 1 ruling §6 item 8: the LIE-to-CCTA registration method and the scar head). On path B, scar is
graded inside the first-pass borders after registering them to the late-iodine (LIE) scan (JA11; Golf E3).
- Which registration is enough?
- How much do registration error and the grading rule each cost the per-segment scar call and its Kim bin?

**Data.** The 13 contrast-enhanced cardiac CTs that the shared JA12 guard (#145, `janusm.guard.refuse`) allows:
s0391, s0414, s0435, s0653, s0702, s0832, s0877, s1018, s1022, s1262, s1305, s1310, s1332. They are public
TotalSegmentator v1 cases (Zenodo 6802614, CC BY 4.0) with model-made heart masks at 1.5 mm.
- Every case passes `janusm.guard.refuse` and then my `heldout.check_public` inside the worker, before any file is
  opened.
- The run refuses outright if a refused id is on disk.
- Two other allowed cases (s0085, s0452) have no contrast and were skipped by the code. Held-out cases opened:
  **none**.

**Disclosure: one twin was opened, and the result is re-run without it.** The first run used 14 cases, chosen
by my v1-only twin rule before #145 reached this branch. The shared guard applies the rule over v1 ∪ v2 ages. It
refuses **s1237** as a possible twin of held-out s0980, which my rule missed.
- What was read: s1237's public CT and masks, for the synthetic-LIE simulation. s1237 is not itself a held-out
  patient, and no coronary quantity was computed.
- Clean-up: the local copy is deleted, and the run is repeated on the 13 allowed cases. The numbers below are the
  re-run's. The first run's figures moved by ≤ 0.03.
- s0335 and s0532 are also refused by the shared guard. They were downloaded but never opened, because the run
  skips unenhanced cases before reading the image. Disclosed on #143.

**Method** (`e5_lie_registration.py`; 3 draws per case, seed by case number; 39 draws, 621 segments, 194 with scar).

1. **First pass:** the real CT and its masks. Segments come from `layers.aha17` and depth from `distance_depth`.
   - Five segments of 1–16 get a subendocardial scar: wall with depth < τ, τ ∈ {0.15, 0.40, 0.65, 0.90, U(0.05, 1)}.
   - The reference (the LGE analogue) is each segment's scar volume share, binned by Kim (0; 1–25; 26–50; 51–75;
     76–100 %).
2. **A synthetic LIE of the same patient.** It is the CT, moved by a known motion:
   - rigid, for a second breath-hold: rotation N(0, 3°) and translation N(0, 4 mm) per axis;
   - plus a smooth non-rigid field, RMS 1.5 mm with 20 mm correlation, for phase.
   - **LIE contrast:**
     - blood 110 HU, remote myocardium 85 HU, scar 150 HU;
     - other soft tissue compressed toward 40 HU; lung and air unchanged;
     - blur 0.6 voxel; noise SD 18 HU, so voxel CNR ≈ 3.6 (Palmisano 2020: detected scars 3.54, missed 2.33).
3. **Registration** of the CT (moving) to the LIE (fixed), SimpleITK, Mattes MI, on a heart crop with a 30 mm margin:
   - R0 none;
   - R1 rigid;
   - R2 rigid + affine;
   - R3 rigid with the metric masked to the first-pass heart (+10 mm);
   - R4 R3 + B-spline (≈ 50 mm mesh);
   - plus the oracle (true motion), which isolates the rule's own error.
4. **Grading inside the warped wall,** after 1-voxel Gaussian smoothing.
   - **Remote** = core wall voxels (≥ 1 voxel inside both borders) of the 6 lowest-median segments, with median and
     robust SD.
   - **Rules:** G2, G3 and G5 (remote + n SD), and GF (FWHM: remote + ½ (99th percentile of the brightest segment's
     core − remote)).
   - **Presence:** a segment is scar if ≥ 5 % of its voxels pass.
   - **E5b** (`e5_hybrid.py`, from the saved shares, no image re-read): presence by GF, extent by G3.
   - CIs are a 2000-draw patient bootstrap.

**A bug found and fixed before the run.** The first version took remote statistics from all wall voxels. Edge voxels
blurred toward lung inflated the SD so much that no rule found any scar, even with perfect borders. The core-voxel,
robust-SD remote above is the fix. It is also the standard practice of drawing a remote ROI mid-wall.

**Result 1: registration.** Medians, with the 90th percentile in brackets:

| Method | Endocardial ASSD (mm) | Wall ASSD (mm) | Wall Dice | Wall voxels that are blood | Seconds |
|---|---|---|---|---|---|
| R0 none | **2.88** [5.03] | 2.62 | 0.67 | **16 %** [35 %] | 0 |
| R1 rigid | **0.80** [0.91] | 0.76 | 0.92 | 4 % | 3.3 |
| R2 affine | 0.78 [0.90] | 0.77 | 0.92 | 4 % | 6.8 |
| R3 rigid, heart-masked | 0.78 [0.91] | 0.77 | 0.92 | 4 % | 2.7 |
| R4 masked + B-spline | 0.82 [0.98] | 0.77 | 0.92 | 4 % | 95 |

**Result 2: scar call, by rule** (pooled segments; sensitivity / specificity / transmurality agreement among segments
scarred on both; E5b CIs for R1):

| Borders | G3 (remote + 3 SD) | G5 | GF (FWHM) | **GF presence + G3 extent** |
|---|---|---|---|---|
| Oracle | 0.97 / **0.84** / 0.78 | 0.80 / 0.99 / 0.60 | 0.83 / 1.00 / 0.62 | **0.83 / 1.00 / 0.78** |
| R0 none | 0.49 / 0.78 / 0.32 | 0.31 / 0.94 / 0.37 | 0.91 / 0.59 / 0.38 | 0.91 / 0.59 / 0.28 |
| R1 rigid | 0.95 / 0.84 / 0.73 | 0.75 / 0.98 / 0.45 | 0.83 / 0.986 / 0.57 | **0.83 [0.78, 0.88] / 0.986 [0.97, 1.00] / 0.70 [0.62, 0.76]** |
| R3 masked | 0.95 / 0.82 / 0.70 | 0.75 / 0.97 / 0.46 | 0.82 / 0.98 / 0.55 | 0.82 / 0.98 / 0.68 |

Transmurality error (CT share − reference share) among scar-on-both segments, after R1, as mean / SD:
- G3: 0.00 / 0.12;
- GF: −0.11 / 0.09;
- hybrid: −0.01 / 0.12.

G2 is not usable: specificity 0.38–0.48.

**What it shows.**
1. **Registration is necessary, and rigid is enough** when the LIE is phase-matched.
   - Without registration, a sixth of the "wall" is blood and transmurality agreement falls to about 0.3.
   - Rigid gets within 0.8 mm. Affine, masking and B-spline do not improve on it here, and B-spline costs about
     30× the time.
2. **After rigid registration, the rule's own error is the larger term.** With perfect borders the best transmurality
   agreement is 0.78; rigid costs 0.04–0.08 of it.
3. **No single threshold is both specific and accurate.**
   - Remote + 3 SD measures extent without bias but calls blood spill at the endocardium scar: specificity 0.84 even
     with perfect borders.
   - FWHM is specific but understates transmurality by 10 points.
   - **Presence by FWHM, extent by 3 SD** keeps both: sensitivity 0.83, specificity 0.986, agreement 0.70. That is
     the pooled LIE-vs-LGE level for presence (0.86 / 0.98; Gatti 2025).
4. **E6's sizing holds for this rule.** Its transmurality error SD (0.12) is E6's middle scenario (sd_s 0.13).

**Limits.**
- The LIE is synthetic. Anatomy and motion are real-scale, but the intensities are assigned by label, the blood is
  darker than scar (Golf's hard case, blood = scar, is not run), and there is no beam hardening or motion blur.
- The masks are 1.5 mm model-made labels, not reads. The scars are idealised subendocardial shells.
- Heart-masking cannot show a benefit here: the synthetic chest moves with the heart. A second breath-hold need not
  do that.
- The numbers **rank** registrations and rules. They do not predict accuracy on the paired cohort, which the
  development set measures (Kilo v2 §4.4).

**What it changes** (Kilo v2):
- Registration is rigid MI on a heart crop. The masked and B-spline arms are tested on development only if QC fails.
- S0 is the two-threshold rule.
- A2 requires the LIE at the same gating and phase as the CCTA.
- The registration QC flag is the share of the registered wall brighter than the LIE blood pool, set on development.
- Golf's bright-blood case becomes a development check (§8).

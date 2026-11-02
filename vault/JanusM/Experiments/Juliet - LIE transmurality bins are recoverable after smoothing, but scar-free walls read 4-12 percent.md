---
tags: [janus-m, experiment, scar, lie, transmurality, phantom]
author: Juliet
round: 1
updated: 2026-10-30
---

# LIE transmurality bins are recoverable after smoothing, but scar-free walls read 4–12 % transmural

## Question

Viability is read from the **transmural extent** of late enhancement. On MRI, 78 % of dysfunctional segments without
hyperenhancement improved after revascularisation, against 1 of 58 with > 75 % transmural hyperenhancement (Kim 2000,
[10.1056/NEJM200011163432003](https://doi.org/10.1056/NEJM200011163432003), abstract; its intermediate bins are in a
figure not checked here). On CT, late iodine enhancement (LIE) detects scar with per-segment sensitivity 0.86 and
specificity 0.98 against MRI LGE (meta-analysis of 14 studies, 5758 segments; Gatti 2025,
[10.1007/s00330-024-11283-5](https://doi.org/10.1007/s00330-024-11283-5), abstract).

If Janus-M supplies the borders (from a co-registered CCTA, because on LIE the blood pool and the scar are both
bright), how well can a simple threshold recover the transmurality bins, and what dominates the error?

## Method

Synthetic only. `experiments/JanusM/Juliet/phantom.py` (E3), `results.json` → `E3`.

- **Image.** LIE-like values:
  - remote myocardium 90 HU;
  - blood pool 130 HU;
  - scar 90 + C HU, with C ∈ {30, 50, 80};
  - fat −90 HU;
  - 30 HU outside.
- **Scar.** Subendocardial, transmurality T ∈ {0, 0.2, 0.4, 0.6, 0.9}, in a 60° sector of a 10 mm wall.
- **Blur and noise.** PSF FWHM 1.0 mm, 0.5 mm voxels. Noise SD ∈ {8, 15, 25} HU. The literature puts LIE noise at
  about 6–10 HU (Takafuji 2025, [10.1007/s11604-025-01760-2](https://doi.org/10.1007/s11604-025-01760-2)) and
  infarct–remote CNR at about 6 (Hamdy 2019, [10.1007/s10554-018-1513-z](https://doi.org/10.1007/s10554-018-1513-z)),
  both abstracts.
- **Smoothing.** None, or a 1.5 mm Gaussian.
- **Borders.** Exact, or with 0.5 mm RMS error (the E1 error model).
- **Rule.** A voxel is scar if it is above a threshold set on a remote mid-wall ROI (depth 0.25–0.75):
  - `sd2` / `sd3`: mean + 2 / 3 SD;
  - `half`: half-way from the remote mean to the sector's 99th percentile.
- **Measure.** Transmurality = mean over 1° radial chords of the fraction of chord voxels that are scar. Kim's bins
  (0, 1–25, 26–50, 51–75, 76–100 %). 8 seeds.

## Result

Summary at 0.5 mm border error: mean absolute error of T over the scarred conditions (T > 0) / bin accuracy over
T > 0 / transmurality read in the **scar-free** sector.

| Contrast | Noise | Smoothing | sd2 | sd3 | half |
|---|---|---|---|---|---|
| 30 HU | 8 HU | none | 0.04 / 1.00 / 0.05 | 0.16 / 0.41 / 0.02 | 0.15 / 0.47 / 0.07 |
| 30 HU | 8 HU | 1.5 mm | 0.06 / 0.81 / 0.12 | 0.04 / 0.91 / 0.09 | 0.06 / **1.00** / 0.05 |
| 30 HU | 15 HU | none | 0.27 / 0.25 / 0.03 | 0.44 / 0.25 / 0.01 | 0.28 / 0.25 / 0.11 |
| 30 HU | 15 HU | 1.5 mm | 0.04 / 0.91 / 0.10 | 0.02 / **1.00** / 0.06 | 0.07 / 0.97 / 0.05 |
| 50 HU | 15 HU | 1.5 mm | 0.05 / 0.84 / 0.10 | 0.03 / 0.91 / 0.06 | 0.04 / **1.00** / 0.05 |
| 50 HU | 25 HU | none | 0.28 / 0.25 / 0.03 | 0.45 / 0.25 / 0.00 | 0.28 / 0.25 / 0.12 |
| 50 HU | 25 HU | 1.5 mm | 0.04 / 0.91 / 0.08 | 0.02 / **1.00** / 0.04 | 0.05 / **1.00** / 0.06 |
| 80 HU | 25 HU | 1.5 mm | 0.05 / 0.84 / 0.08 | 0.03 / 0.97 / 0.04 | 0.04 / **1.00** / 0.06 |

The full grid of 180 rows (3 contrasts × 3 noise levels × 2 smoothings × 2 border errors × 5 T) is in `results.json`.

1. **Unsmoothed voxels at 15–25 HU noise lose half the transmurality.** At C ≤ 50 HU the 2–3 SD threshold sits above
   most scar voxels, so a 90 % transmural scar reads about 0.4.
2. **With 1.5 mm smoothing, the half-way rule bins T > 0 correctly in every run in 8 of the 9 contrast × noise
   conditions.** The exception is C = 30 HU with noise 25 HU, where it falls to 0.69. The SD rules are weakest at the
   *lowest* noise: after smoothing, 2–3 SD is a small margin and blood-pool spill passes it. Their range is sd3
   0.75–1.00 and sd2 0.69–0.97. No rule wins everywhere.
3. **A scar-free wall reads 4–12 % transmural** under every rule. This is blood-pool spill into the sub-endocardium,
   which smoothing makes worse. A segment-level **scar-present rule** (for example T̂ ≥ 0.15) must come before the
   bins, or every segment falls into 1–25 %.
4. **Border error of 0.5 mm changes T̂ by ≤ 0.02.** Transmurality is a fraction of the chord, so it is robust to the
   borders. LIE needs the borders mainly to place the chords and the remote ROI.

## What it changes

- **Scar output = scar presence + transmurality bin per AHA segment**, computed from a smoothed LIE image on borders
  transferred from the same session's CCTA. It is not a learned scar class. No public CT scar dataset exists to learn
  one from (Juliet v1 §4).
- **The threshold rule is a calibration question for paired LIE + MRI LGE data**, not for a phantom. The phantom only
  shows that the error is controllable: smooth, threshold, call presence first. The project holds no LIE data, so
  this waits on the lead's data decision (Juliet v1, lead's question M-Q5).
- **Limits.** Homogeneous scar and remote; no microvascular obstruction; no motion or misregistration between the
  CCTA and LIE acquisitions (misregistration shifts the chords; Round 2 can add it).

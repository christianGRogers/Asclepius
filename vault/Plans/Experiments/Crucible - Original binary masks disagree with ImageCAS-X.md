---
tags: [plans, experiment, labels, label-noise, imagecas-x, binary-masks]
author: Crucible
round: 1
updated: 2026-10-04
---

# Our Girder binary masks are 3.6× the ImageCAS-X lumen, and most of the excess is not lumen

## Question

Every plan that "trains a binary model now on the 1000 existing masks" assumes
those masks are a usable lumen target. The ImageCAS-X paper reports that the
original ImageCAS labels agree with its re-annotation at only DSC 41.8. Are our
Girder masks those original labels, how exactly do they differ, and what are
the extra voxels? Also: how much of the ICX lumen is side branches, which our
4-class protocol does not name?

## Method

- Cases: 200 ICX cases (every 4th ICX id in ascending order: 1, 5, 9, …),
  each paired with Girder case `c{id-1}` (header match re-checked per case with
  `np.allclose`, see [[Crucible - ImageCAS-X is real and its 800 cases are our cases c(id-1)]]).
- Per case: Dice of our mask vs ICX merged lumen (labels > 0); coverage either
  way; fraction of our mask within 1 voxel of ICX lumen; fraction farther than
  5 voxels (~1.75 mm); connected components; per-ICX-class voxel share and
  coverage by our mask. Script `experiments/Crucible/compare_icx.py`, summary
  `summarize.py compare`.
- HU check on the 32 cached CTs that have ICX labels
  (`experiments/Crucible/hu_disagreement.py`): median HU of voxels in both
  masks, ICX-only, ours-only within 1.5 voxels of ICX ("shell"), ours-only at
  1.5–5 voxels ("near"), and ours-only beyond 5 voxels ("far").

## Result

**Agreement (200 cases):**

| Measure | mean | median | p10 |
|---|---|---|---|
| Dice, ours vs ICX merged lumen | **0.412** | 0.411 | 0.318 |
| ICX lumen covered by our mask | 0.917 | 0.928 | 0.855 |
| Our mask covered by ICX lumen | **0.268** | 0.264 | 0.195 |
| Our mask within 1 voxel of ICX lumen | 0.445 | 0.443 | 0.347 |
| Our mask > 5 voxels from any ICX lumen | 0.172 | 0.161 | 0.079 |
| Volume ratio ours / ICX | **3.58** | 3.41 | 2.71 |
| Connected components (ours / ICX) | 3.7 / 2.1 | 3 / 2 | |

Our Dice of 0.412 reproduces the paper's 41.8 ± 6.7 (original ImageCAS labels
vs ICX) — **our Girder masks are the original ImageCAS labels**, unmodified.

**HU of the disagreement (32 CT cases):**

| Voxel group | share of our mask | median of per-case median HU | mean p10 / p90 HU |
|---|---|---|---|
| In both masks (agreed lumen) | 25.7 % | **372** | 194 / 511 |
| ICX only (lumen we miss) | (2.4 % of our volume) | 191 | 105 / 412 |
| Ours only, ≤ 1.5 vox from ICX ("shell") | 27.2 % | 116 | 6 / 239 |
| Ours only, 1.5–5 vox ("near") | 29.2 % | **16** | −70 / 120 |
| Ours only, > 5 vox ("far") | 17.9 % | **38** | −78 / 207 |

Contrast-filled lumen sits at ~370 HU; the 47 % of our mask that lies more than
1.5 voxels from the ICX lumen has median HU 16–38 — fat, myocardium and vessel
wall, not contrast. Only the 1-voxel shell is plausibly partial-volume lumen.

So the original masks contain nearly all of the ICX lumen, wrapped in a thick
layer of non-contrast tissue (vessel wall, peri-vascular fat, partial volume),
plus ~17 % of their volume in structures that ICX does not trace at all
(more components: 3.7 vs 2.1).

**Side branches are 27 % of the vessel.** Share of ICX lumen voxels by class
(200 cases; present = cases containing the class):

| Class | present | share of lumen | covered by our mask (mean / p10) |
|---|---|---|---|
| LM | 197/200 | 5.3 % | 0.875 / 0.739 |
| LAD | 200 | 22.3 % | 0.963 / 0.874 |
| LCx | 200 | 15.3 % | 0.913 / 0.750 |
| RCA | 200 | 30.5 % | 0.978 / 0.954 |
| **Main four together** | | **73.4 %** | |
| D1 | 199 | 5.2 % | 0.786 / 0.212 |
| D2 | 104 | 1.8 % | 0.686 / 0.111 |
| OM1 | 175 | 4.6 % | 0.713 / 0.101 |
| OM2 | 82 | 2.3 % | 0.714 / 0.096 |
| IM (ramus) | 46 | 1.0 % | 0.679 / 0.152 |
| R-PDA | 185 | 4.6 % | 0.725 / 0.149 |
| R-PLA | 182 | 6.0 % | 0.778 / 0.305 |
| L-PDA | 10 | 0.2 % | 0.575 / 0.000 |
| L-PLA | 20 | 0.4 % | 0.402 / 0.026 |
| Other | 26 | 0.5 % | 0.822 / 0.568 |
| **Side branches together** | | **26.6 %** | |

The original masks miss whole side branches that ICX traced in a sizable
minority of cases (p10 coverage 0.10–0.30 for D1, OM1, PDA, PLA).

## What it implies

1. **Training "binary first on the 1000 existing masks" learns the wrong
   target.** A model fitted to these masks is rewarded for painting ~2.6 extra
   voxels of non-lumen tissue for every lumen voxel; its "calibration against
   82.96 %" is calibration against labels that a 4-analyst, double-read
   re-annotation of the same scans contradicts. [[Training plan]] §3.1 proposes
   exactly this, and then proposes using that model's predictions as the
   presegmentation seeds annotators correct. That would anchor the labelling
   team to the thick convention (the pre-annotation bias Shwartzman et al.
   describe in [[Seeding annotation with model predictions and label efficiency]]).
2. **Use the ICX lumen, not the Girder mask, wherever ICX exists (800/1000).**
   For the 200 non-ICX cases the Girder mask is still useful as a *superset
   prior* — it covers 92 % of true lumen — e.g. as a region-of-interest, an
   ignore-outside mask, or an HU-thresholded "inside the mask and contrast-
   bright" pseudo-lumen, never as a voxel-exact target.
3. **The side-branch convention is not a detail: it decides the fate of 27 %
   of vessel voxels.** Our project protocol (hints: "follow the anterior
   interventricular groove", "left AV groove") never says whether a diagonal
   belongs to LAD or to background. Until the team writes it down, a model
   should be trained so that either answer can be read out (14-class training
   collapsed at inference, or side branches as ignore) — see [[Crucible v1]].
4. The labelling team must be told which lumen convention to draw. If they
   correct seeds derived from the Girder masks, their labels will sit between
   the two conventions and every metric we report will mix them.

## Limits

- 200 of 800 ICX cases (first 200 of every-4th by id); no reason to expect id
  order to correlate with label quality, but it is not a random draw.
- ICX is itself a convention (tight lumen, side branches > 1 mm traced only
  when clearly connected). "Not lumen" for the excess voxels rests on the HU
  evidence, not on ICX being right by definition.
- HU medians are per-case medians averaged; partial-volume voxels at the
  lumen edge legitimately fall between lumen and tissue HU.

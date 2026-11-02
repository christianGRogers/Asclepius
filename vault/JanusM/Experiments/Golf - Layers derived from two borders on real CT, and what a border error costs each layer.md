---
tags: [janus-m, experiment, myocardium, layers, transmural, AHA-17, metric, round1]
author: Golf
round: 1
updated: 2026-10-30
issue: christianGRogers/Asclepius#130
code: experiments/JanusM/Golf/fetch_ts.py, layers_ts.py, aha_check.py, summarise_e2.py, heldout.py
---

# Layers derived from two borders on real CT, and what a border error costs each layer

## Question

Should Janus-M learn the myocardial "layers" (transmural thirds, AHA segments) as classes? Or should it learn only
the myocardium, meaning its endocardial and epicardial borders, and compute the layers from them? Four sub-questions:

1. How many voxels does a third hold at CT resolution?
2. Does the choice of transmural coordinate matter?
3. Can AHA segments be derived automatically?
4. For a given border error, how much worse is a layer than the whole myocardium?

## Data

- **24 contrast cardiac CTs** from TotalSegmentator v2.0.1 (University Hospital Basel; CC BY 4.0,
  doi:10.5281/zenodo.10047292), fetched from the Hugging Face mirror that `tools/ccta/ingest_totalseg.py` uses.
- **Selection:** the 101 "gated_like" ids (`tools/ccta/totalseg_cardiac_ids.json`) that are **not** in
  `configs/segqueue14/pool-2026-10.txt` and pass `heldout.py`. The guard checks pool seal, reserve, every D35
  draw and A14, by real patient. The first 24 were taken by `sha256('janusm-golf-r1:' + id)`.
- **Who they are:** aged 47–84; study types aortic valve, heart and thoracic aorta, left atrium. Cardiac phase not
  recorded.
- **Labels used:** the released left atrium, LV myocardium, LV blood pool and RV blood pool, all at 1.5 mm
  isotropic. These are TotalSegmentator's model-assisted labels, not an expert reference.
- **What was held out:** no case was a pool volume. No sealed, reserve or D35 patient was opened. s0597's release
  has no LV label, so 23 cases were analysed.

## Method (`layers_ts.py`, CPU, about 2 min per case)

**A. Attenuation.** Medians of LV blood HU, eroded-myocardium HU and myocardial MAD-SD.

**B. Thickness.** The median of d_endo + d_epi over myocardial voxels more than 5 mm from the LA. Summing two
centre-to-centre Euclidean distance transforms counts one voxel too many, so `summarise_e2.py` subtracts one voxel.
That correction cancels in every comparison between two masks on the same grid.

**C. Thirds by two coordinates:**
- equal-thickness depth u = d_endo / (d_endo + d_epi);
- the Laplace potential, 0 at the endocardium and 1 at the epicardium, solved by CG.

**D. AHA 17 segments:**
- the long axis by PCA of the LV, pointing base to apex;
- the base is the mitral plane: LV voxels within 3 mm of the LA;
- basal, mid and apical are thirds of base → cavity tip, and segment 17 lies beyond the tip;
- angle zero is the anterior RV insertion (an end of the RV-contact arc);
- the septum spans the measured arc.

Orientation checks: septum towards the RV centroid, lateral wall away, segment 1 anterior of segment 4.
`aha_check.py` then compares two rules for picking the anterior insertion: A, anterior (+y); and B,
anterior-superior (+y +z). The stricter check requires segment 1 to be both anterior and superior of segment 4.

**E. Sensitivity on a 0.5 mm grid.** Signed distances of the epicardial and endocardial surfaces are interpolated
from 1.5 mm, with the surface placed half-way between voxel centres. Each gets a smooth random displacement field
with an 8 mm correlation length and RMS σ of 0.25, 0.5 or 1.0 mm, 2 draws per case. Systematic 0.5 mm biases are
also run. The layers are re-derived each time and compared with the unperturbed reference.

## Results (23 cases; `layers_ts.json`, `layers_ts_summary.json`, `aha_check.json`)

Values are median [IQR] across cases.

| Quantity | Value |
|---|---|
| LV blood / myocardium HU | 306 [228, 401] / 99 [78, 127] |
| Blood–myocardium CNR | 5.7 [3.7, 6.7] |
| Wall thickness, 1.5 mm grid (corrected) | **9.7 mm [8.9, 10.0]**; range 8.1–11.6 |
| Wall thickness, 0.5 mm grid | 9.9 mm [9.1, 10.2] |
| Voxels per third at 1.5 mm | **2.2** [2.0, 2.2] |
| Volume share of the thirds (subendo / mid / subepi), equal thickness | 25 / 37 / 37 % |
| Same, Laplace potential | **21 / 34 / 45 %** |
| Voxel agreement, equal-thickness vs Laplace thirds | **0.878** [0.872, 0.879] |
| AHA derivation ran / all 17 segments non-empty | 23 of 23 / 22 of 23 |
| Orientation correct, as run (rule A, loose check) | 19 of 23 (misses: s0624, s0684, s0919, s0653) |
| Strict check, rule A / rule B | 17 / **19** of 23 |
| Septal (RV-contact) arc | **164°** [152, 184]; AHA expects 120° |
| Segment share CV (segments 1–16) | 0.27 [0.21, 0.52]; septal segments 2, 3, 8, 9 hold 7.7–8.7 % each |

**Border error against layer error** (0.5 mm grid; median [IQR] over 23 cases × 2 draws, or 23 for the biases):

| Perturbation | Myocardium Dice | Subendocardial Dice | Mid-wall Dice | Subepicardial Dice | Thickness error (mm) | AHA mean Dice |
|---|---|---|---|---|---|---|
| Random, σ 0.25 mm | 0.982 | 0.952 | 0.956 | 0.954 | −0.04 [−0.12, 0.03] | 0.963 |
| Random, σ 0.5 mm | 0.963 | 0.909 | 0.916 | 0.903 | −0.10 [−0.22, 0.03] | 0.923 |
| Random, σ 1.0 mm | 0.921 | 0.808 | 0.832 | 0.799 | −0.04 [−0.23, 0.15] | 0.830 [0.45, 0.87] |
| Epicardium 0.5 mm out | 0.967 | 0.976 | 0.922 | **0.881** | **+0.40** | — |
| Endocardium 0.5 mm in | 0.977 | **0.876** | 0.920 | 0.979 | **+0.44** | — |
| Both (wall 1 mm thicker) | 0.945 | 0.900 | 0.943 | 0.904 | **+0.85** | — |

## What it implies

1. **The layers are a harder target than the myocardium for the same border error.** Layer Dice loses about twice
   what myocardium Dice loses: 0.909 against 0.963 at σ 0.5 mm. The layer error is fully set by the border error,
   so learning thirds as classes adds a noisier target and no new information. **Derive the layers; score the
   borders.**
2. **The deciding metric must be in millimetres and must see bias.**
   - Random border error barely moves the median thickness (|error| ≤ 0.10 mm).
   - A 0.5 mm systematic shift moves it by 0.40–0.44 mm while myocardium Dice stays at 0.967–0.977.
   - So Dice would accept a model that biases every thickness and every transmural fraction.
   - Golf v1 §7.3 therefore decides on per-segment thickness error against reads, with border ASSD.
3. **The transmural coordinate must be fixed in the protocol.** Laplace and equal-thickness thirds disagree on
   12 % of voxels. The Laplace subepicardial third is 45 % of the wall's volume. The clinical definitions are
   fractions of thickness (George 2009; Mushtaq 2023), and Cobiveco reports normalised distance more linear than
   Laplace (Schuler 2021). So: **equal thickness**.
4. **Resolution.** 1.5 mm, TotalSegmentator's released grid, leaves 2.2 voxels per third, which is too coarse to
   score a layer. At `heartchambers_highres`'s about 0.73 × 0.72 × 1.0 mm a third holds about 4–5 voxels.
5. **AHA segments can be derived automatically, but two rules need fixing before anything ships:**
   - The **anterior insertion** should be the end pointing anterior-superior (19 vs 17 of 23).
   - The **septal arc** from a 3 mm RV-contact band is 164°, not 120°. Septal segments come out oversized: 8 %
     against about 5 % of the mass. Use six fixed 60° sectors from the anterior insertion.
   - M2 measures the failure rate on 800 ImageCAS cases.
6. **Thickness depends on the label convention.** 9.7 mm is far above the 5.7 mm CT norm at end-diastole
   (Chen 2025). That fits older valve and aorta patients and an unknown phase, and possibly trabeculae inside the
   label. A model trained on one label source inherits its thickness. Hence team reads, a stated papillary and
   trabecular convention (Golf v1 Q3), and thickness against reads as the deciding metric.

**Limits:**
- the labels are TotalSegmentator's, not an expert's;
- the 0.5 mm grid is interpolated from 1.5 mm, so fine anatomy is smooth;
- the perturbation is synthetic, a smooth isotropic field;
- 23 cases.

None of these changes the direction of findings 1–3, which follow from geometry.

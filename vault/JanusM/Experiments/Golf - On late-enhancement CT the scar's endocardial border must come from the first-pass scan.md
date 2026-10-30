---
tags: [janus-m, experiment, scar, transmurality, late-iodine-enhancement, simulation, round1]
author: Golf
round: 1
updated: 2026-10-30
issue: christianGRogers/Asclepius#130
code: experiments/JanusM/Golf/transmural_sim.py
---

# On late-enhancement CT the scar's endocardial border must come from the first-pass scan

## Question

Scar transmurality is graded in bins: 0, 1–25, 26–50, 51–75 and 76–100 % of the wall. The bins come from
[[#Kim2000]]'s MRI work: dysfunctional segments without enhancement recovered in 78 %, but only 1 of 58 with more
than 75 % did. Can those bins be read on late-iodine-enhancement (LIE) CT, and what does that require? Three parts:

1. What scar-to-remote contrast-to-noise ratio (CNR) per voxel is needed?
2. Does voxel size matter at a wall of 8–11 mm?
3. Can the endocardial border be found on the LIE image itself, or must it come from the first-pass (CCTA) phase?

Part 3 decides the model's design. If the LIE image cannot carry its own borders, the myocardium model is trained
on first-pass CCTA and LIE scar is graded inside its borders after registration.

## Method

The simulation is synthetic and runs on CPU in about 1 minute. Each AHA segment is modelled as 150 transmural
profiles of a wall 8 or 11 mm thick; E2 measured 8.1–11.6 mm on real CT. Subendocardial scar fills 0, 15, 35, 60
or 90 % of the wall, which puts each case in the middle of a Kim bin, with ±5 % jitter across the segment.

**Intensities,** in units of the scar–remote contrast:

| Tissue | Value |
|---|---|
| Remote myocardium | 0 |
| Scar | 1 |
| Epicardial fat | −2 |
| Blood pool, "bright" (as bright as scar: the hard case on LIE) | 1 |
| Blood pool, "dark" | 0.3 |

**Image formation:**
- Gaussian PSF, FWHM 0.6 or 1.0 mm;
- box-sampled at 0.5, 1.0 or 1.5 mm voxels, with a random grid phase;
- white noise with SD 1/CNR, where CNR (1.5, 2, 3, 5) is measured at the analysis voxel.

**Grading:**
- scar = voxel > remote mean + k·SD, with k = 2, 3 or 5;
- the remote reference comes from a scar-free segment of the same image;
- transmurality = scar voxels / wall voxels;
- the reported row uses the best k for each condition.

**Borders:**
- **G (given):** endocardium and epicardium are known, as from the registered first-pass CCTA.
- **S (self):** the endocardium is found on the LIE profile itself. It is placed at the first two voxels that
  leave the blood level by half the smaller of the blood–remote and blood–scar steps.

There are 288 conditions, with 40 segments per condition. Outputs are the Kim-bin accuracy and the mean absolute
transmurality error in percentage points (pp).

## Result

PSF FWHM 0.6 mm. Each cell is Kim-bin accuracy (MAE in pp). Chance-level grading ("all zero") scores 0.20.
Everything is in `transmural_sim.json`.

| Voxel | CNR | Bright blood, borders given | Bright blood, self | Dark blood, given | Dark blood, self |
|---|---|---|---|---|---|
| 0.5 mm | 2 | 0.40 (34) | 0.20 (22) | 0.40 (34) | 0.40 (36) |
| 0.5 mm | 3 | 0.60 (6) | 0.23 (39) | 0.55 (7) | 0.40 (12) |
| 0.5 mm | 5 | **0.88 (2)** | **0.20 (37)** | 1.00 (2) | 0.80 (5) |
| 1.0 mm | 3 | 0.57 (7) | 0.25 (32) | 0.60 (7) | 0.40 (11) |
| 1.0 mm | 5 | **0.93 (3)** | **0.20 (36)** | 0.97 (2) | 0.80 (4) |
| 1.5 mm | 3 | 0.60 (8) | 0.23 (33) | 0.60 (8) | 0.38 (11) |
| 1.5 mm | 5 | **1.00 (3)** | **0.20 (35)** | 0.93 (3) | 0.80 (5) |

At PSF FWHM 1.0 mm and CNR 3, with bright blood and given borders, accuracy is 0.68 / 0.65 / 0.43 at 0.5 / 1.0 /
1.5 mm voxels.

## What it implies

1. **When the blood pool is as bright as scar, an LIE-only reader loses subendocardial scar at every CNR.** Its
   accuracy stays at 0.20–0.25, the "everything is zero" level: the scar is read as cavity. Bright blood is the
   regime that matters, because 94 % of post-infarct fat and most infarct scar is subendocardial
   ([[#Ichikawa2009]]). With the borders taken from the first-pass phase, the same images grade at 0.88–1.00 once
   CNR reaches 5. **So Janus-M learns the myocardial borders on first-pass CCTA, and LIE is graded inside them after
   registration.** It does not train an LIE-only border model. Mahnken et al. did exactly this fusion of CCTA with
   late CT ([[#Mahnken2010]]).
2. **CNR per voxel decides more than voxel size between 0.5 and 1.5 mm.** A k·SD threshold needs scar contrast above
   k·noise. At CNR 2 every method fails; at CNR 5 it works. The resolution penalty appears only with a 1.0 mm PSF on
   a 1.5 mm grid (0.43 versus 0.68). A protocol question for the lead follows: LIE should be acquired or
   reconstructed for CNR (low-keV dual-energy, denoising), not for the thinnest slice. In the meta-analysis of
   [[#Gatti2025]], pooled segment-level LIE sensitivity was 0.86, and 0.93 in the dual-energy studies.
3. **Grading needs real data to validate it, and the project has none.** The simulation shows what is possible, not
   what scanners deliver. No openly downloadable CT scar dataset with labels was found; the Monzino and Penso 2023
   records on Zenodo are restricted. So scar grading stays a **conditional phase**, tied to an institutional cohort
   with CMR late gadolinium enhancement as the reference.

**Limits:**
- one-dimensional profiles with white noise; real CT noise is correlated and has beam-hardening bands;
- a fixed bright or dark blood level;
- the threshold reader is deliberately simple, and a learned reader could do better at low CNR.

The conclusion about borders does not depend on the reader. Once blood and scar are equally bright, no intensity
rule on the LIE image alone can place the endocardium.

## References

- <a id="Kim2000"></a>Kim RJ, Wu E, Rafael A, et al. The use of contrast-enhanced magnetic resonance imaging to identify
  reversible myocardial dysfunction. *N Engl J Med* 2000;343:1445-1453. doi:10.1056/NEJM200011163432003 (abstract:
  78 % of 329 non-enhanced dysfunctional segments improved vs 1 of 58 with > 75 % transmural enhancement).
- <a id="Ichikawa2009"></a>Ichikawa Y, Kitagawa K, Chino S, et al. Adipose tissue detected by multislice computed
  tomography in patients after myocardial infarction. *JACC Cardiovasc Imaging* 2009;2:548-555.
  doi:10.1016/j.jcmg.2009.01.010 (abstract: fat in 62 % of prior-MI patients, 94 % subendocardial).
- <a id="Mahnken2010"></a>Mahnken AH, et al. The culprit lesion and its consequences: combined visualization of the
  coronary arteries and delayed myocardial enhancement in dual-source CT: a pilot study. *Eur Radiol*
  2010;20:2834-2843. doi:10.1007/s00330-010-1864-x.
- <a id="Gatti2025"></a>Gatti M, et al. Diagnostic accuracy of late iodine enhancement on cardiac CT for myocardial
  tissue characterization: a systematic review and meta-analysis. *Eur Radiol* 2025;35:3054-3067.
  doi:10.1007/s00330-024-11283-5 (abstract: segment level sensitivity 0.86, specificity 0.98; dual-energy subgroup 0.93).

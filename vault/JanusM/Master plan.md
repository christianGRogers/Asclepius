---
aliases: [Janus-M master plan]
tags: [janus-m, plans, master-plan]
status: living
updated: 2026-10-30
---

# Janus-M master plan

**In force from Round 1 (2026-10-30):** [[Juliet v1]] with amendments JA1–JA14 ([[Janus-M Round 1]],
`Judgements/Round 1.md`). The line forks at LQ1 into two paths, `jm/rest-ccta` and `jm/paired-scar` (M2). This page
is the shared trunk both paths start from. Each path's own plan lives on its branch.

## The plan in one paragraph

**Janus-M learns four borders on rest CCTA and computes the layers.** It segments the LV myocardium, LV blood pool
(with papillary muscles and trabeculae), RV blood pool and LA blood pool. Versioned code then computes:
- the transmural depth (equal thickness) and its thirds, or halves in thin walls;
- the AHA 17 segments, from the RV insertion points and the mitral plane;
- each segment's coronary territory, from Janus's LAD, LCx and RCA, with the AHA default beside it.

The deliverable is a table of 17 segments × layers per patient, tagged by territory and placed beside Janus's
stenosis in the same artery.

## What is learned, what is computed (JA1–JA4)

| Learned (classes) | Computed (no label) |
|---|---|
| 1 LV myocardium; 2 LV blood pool (papillary muscles and trabeculae included); 3 RV blood pool; 4 LA blood pool | Depth u = d_endo / (d_endo + d_epi) and its thirds (halves where < 4 voxels per third or the wall is < 5 mm); thickness; AHA 17 segments with fixed 60°/90° sectors from the anterior RV insertion; territories by nearest vessel; mass per territory |

## Data, seal and decision set (JA5, JA6)

- **Images: ImageCAS-X train 560**, used for the seal, the decision set, Job JM-0 and training, plus the **180
  non-sealed quality-0 cases** for training only.
- **Never:**
  - the A14 sealed 100;
  - the ImageCAS-X test split (open 36, dev 44);
  - val 80;
  - any coronary pool-seal, reserve or D35-draw patient;
  - PLOS-Peng2016.
- **Janus-M seal: 60. Decision set: 40.** Drawn by `experiments/JanusM/Juliet/fir/draw_m0.py` (salts
  `asclepius-janusm-seal-r1:`, then `asclepius-janusm-decision-r1:`) from the train list of `splits.json`. That list
  must match the committed `trillium-results/icx14/results/splits.json` (sha256 prefix `a53bd426cddc`).
  - The draw is frozen in `configs/janusm/sealed-r1.json` by a `role:swe` PR before any Janus-M read.
  - The seal is scored once.
  - The size is re-powered on the first 20 decision double reads; it may grow from the pre-registered extension and
    never shrinks after a read.
- **External, report-only:** adult, good-spacing volumes on the Janus-M allowed list (Kilo's census, re-derived by
  the shared guard); public TotalSegmentator v1 cardiac cases after the guard; ImageCHD (paediatric, licence
  uncertain).
- **One guard** (JA12) refuses every coronary hold-out by patient, including TotalSegmentator "twins", in every
  Janus-M step.

## Reference standard and metric (JA7, JA8)

- **Reads.** Two independent border reads on every seal and decision case. They follow a written protocol with the
  half-maximum border rule, which code checks. Seeds are `heartchambers_highres`, coarsened to 2 mm; 10 seal cases
  are read from blank; anchoring is reported each wave.
- **Primary metric:** endocardial and epicardial ASSD, measured as model-vs-read minus read-vs-read.
- **Co-primary:** median per-segment thickness error.
- **Guards:** signed bias |·| ≤ 0.5 mm; ASSD ≤ 1.0 mm.
- **Reported:** STA, Dice, AHA agreement, territory discordance.
- **Acceptance on the seal:** the upper 95 % bound of d is ≤ 0.25 mm per border, and the thickness error is
  ≤ read-vs-read + 0.5 mm. Both margins are provisional and are re-set once before any seal read.

## Models and compute (JA9, JA10; Fir, `def-aso22`; the lead runs every job)

| Step | What | GPU-h | When |
|---|---|---|---|
| **Job JM-0** | Juliet v1 §7's commands as committed: the draw, plus `heartchambers_highres` and geometry on 40 ImageCAS-X train cases. Send back the aggregate JSON only | ≤ 1 | **Now** |
| Seeds on seal + decision | 100 cases, for the reads | ≈ 2 | After the freeze PR |
| **Janus-M 0** | `heartchambers_highres` + the geometry module. No training | 0 | Scored on the decision set when reads exist |
| Janus-M 1 | nnU-Net v2 ResEnc `3d_fullres`, 4 classes, 0.5 mm, mirroring off; **only if Janus-M 0 fails** | ≈ 12 (seeds) + ≈ 55 | Conditional |
| Second seed | only if a seed claim is needed | ≈ 55 | Conditional |

**Committed ≤ 3 GPU-h; conditional ≈ 67; ceiling ≈ 125.**

## Outputs (JA11)

- **Stage A, rest CCTA, all labelled "research, not validated":**
  - thickness and thinning (phase recorded; ImageCAS phase-uncertain; no CMR cut-off borrowed until calibrated);
  - intramyocardial fat (core sample, −180 to 0 HU window, cut-off set on data);
  - rest attenuation and TPR, report-only with a 1 mm guard band;
  - mass per territory.
- **Stage B:** late-enhancement transmurality inside first-pass borders, stress TPR and ECV. They need paired data.
  **They are the fork:**
  - `jm/rest-ccta` assumes none;
  - `jm/paired-scar` assumes the lead pursues an institutional paired cohort (LQ1).

## Open questions for the lead (carried as assumptions; full text in the ruling, §5)

| Question | Status |
|---|---|
| LQ1 | **The fork:** rest-CCTA only, or paired scar data |
| LQ2 | LV only |
| LQ3 | `heartchambers_highres` licence |
| LQ4 | ImageCAS-X training cases |
| LQ5 | Reader time |
| LQ6 | MM-WHS |
| LQ7 | Released coronary patients |
| LQ8 | s0655 and D27 |

## Shipping (JA13; `role:swe`, opened by the PM)

1. The geometry module.
2. The single held-out guard.
3. The seal freeze.
4. The border read protocol and queue.
5. The nnU-Net dataset builder (only if Janus-M 1 is triggered).

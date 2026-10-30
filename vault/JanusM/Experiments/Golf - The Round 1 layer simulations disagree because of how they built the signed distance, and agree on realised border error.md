---
tags: [janus-m, experiment, layers, perturbation, harness, STA, round2, paired-scar]
author: Golf
round: 2
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#143
code: experiments/JanusM/Golf/harness.py
data: experiments/JanusM/Golf/harness.json
---

# The Round 1 layer simulations disagree because of how they built the signed distance, and agree on realised border error

## Question

Round 1 ruling §6 item 2: at a nominal border error of 0.5 mm RMS, four advocates reported four subendocardial-third
Dice values:

| Advocate | Reported |
|---|---|
| Golf | 0.909 |
| India | 0.927 |
| Kilo | 0.939 |
| Hotel | 0.975 |

The judge could therefore not set an absolute bar. Why do they disagree, and what one error model should every later
round use?

## Method

**What differs between the four codes.** Golf read each advocate's committed perturbation code. They differ in four
ways:

| | Signed distance | Computed on | Grid | Field correlation |
|---|---|---|---|---|
| Golf (`layers_ts.sdf`) | surface half-way between voxel centres (slope 1) | analysis grid | 0.5 mm, masks through interpolated distances | 8 mm |
| India (`lvgeom.perturb_borders`) | half-way (slope 1) | analysis grid | 0.5 mm, masks by trilinear interpolation | 8 mm |
| Kilo (`exp_layers.sdf`) | `edt(~m) − edt(m)` (jumps two voxels across the border) | **native 1.5 mm, then interpolated to 0.5 mm** | 0.5 mm | 10 mm |
| Hotel (`layers_from_borders.perturb`) | `edt(~m) − edt(m)` | analysis grid | 0.75 mm (1.5 mm upsampled ×2) | 6 mm |

**What the harness runs.** `harness.py` applies each of these four recipes, plus three controls, to the same
hearts:
- correlation length 6 mm and 10 mm with Golf's distance;
- the plain distance at 0.5 mm.

Each recipe gets nominal RMS 0.25, 0.5 and 1.0 mm, two repetitions each.

**Data.** 6 public TotalSegmentator v2.0.1 gated-like cardiac CTs, each passing `guard_r2`, with their released
labels: s0032, s0230, s0391, s0403, s0414, s0435.

**What it measures:**
- **the realised error:** the ASSD between the perturbed and the reference border;
- myocardium and subendocardial-third Dice;
- **Kim-bin flips** of a fixed synthetic subendocardial scar. Each of 18 sectors gets a scar at a Kim-bin midpoint
  depth; the scar stays fixed in space while the borders move. This is the core of Kilo's STA.

CPU, about 25 min per case.

## Result

Medians over 6 cases × 2 repetitions.

| Recipe | Nominal RMS | **Realised ASSD (endo / epi, mm)** | Myocardium Dice | **Subendocardial Dice** | R1 reported |
|---|---|---|---|---|---|
| Golf | 0.5 | **0.32 / 0.34** | 0.962 | **0.902** | 0.909 |
| India | 0.5 | 0.34 / 0.33 | 0.961 | 0.890 | 0.927 |
| Kilo | 0.5 | **0.21 / 0.19** | 0.980 | **0.949** | 0.939 |
| Hotel | 0.5 | **0.06 / 0.05** | 0.995 | **0.983** | 0.975 |
| Hotel | 0.25 | 0.00 / 0.00 | 1.000 | 1.000 | |
| control: Golf, corr 6 | 0.5 | 0.34 / 0.35 | 0.961 | 0.894 | |
| control: Golf, corr 10 | 0.5 | 0.32 / 0.33 | 0.961 | 0.893 | |
| control: plain distance, 0.5 mm | 0.5 | 0.15 / 0.12 | 0.986 | 0.961 | |
| Golf | 1.0 | 0.66 / 0.67 | 0.917 | 0.784 | 0.808 |
| Kilo | 1.0 | 0.37 / 0.39 | 0.955 | 0.886 | |
| Hotel | 1.0 | 0.42 / 0.37 | 0.955 | 0.860 | |

**One curve.** Over all 21 recipe × RMS rows:
- **Against the realised ASSD**, the subendocardial Dice falls on one line: 1.002 − 0.314 × ASSD (mm). The residual
  SD is **0.007** and the maximum residual 0.019.
- **Against the nominal RMS**, the residual SD is 0.032 and the maximum 0.063. That is the Round 1 disagreement.

**Kim-bin flips (an STA proxy)** stay ≤ 0.09 of sectors at every level, and ≤ 0.03 at realised ASSD ≤ 0.35 mm.

## What it implies

1. **The disagreement is the signed distance, not the field and not the anatomy.**
   - The plain `edt(~m) − edt(m)` distance jumps by two voxels across the border. So a smooth field moves the border
     only where it exceeds about a voxel, and it halves every move.
   - Hotel computes it on a 0.75 mm grid, so its "0.5 mm" moves the border **0.06 mm**, and at "0.25 mm" not at all.
   - Kilo computes it at 1.5 mm and interpolates, so its "0.5 mm" moves the border 0.2 mm.
   - Correlation length between 6 and 10 mm changes nothing (0.893–0.902).
2. **Golf, Kilo and Hotel's reported numbers are reproduced within 0.01** by their own recipes on these hearts.
   - **India's is not:** its recipe gives 0.890 here, against 0.927 reported.
   - The harness does not explain that gap. It may lie in India's cases (64 v1 hearts against these 6 v2.0.1 hearts)
     or in steps outside the perturbation, and it is reported as open.
   - India's recipe realises the same error as Golf's, so the disagreement that matters here is Hotel's and Kilo's.
3. **The shared error model for every later round (ruling item 2, settled):**
   - borders perturbed through a **half-voxel signed distance computed on the analysis grid**;
   - a smooth normal field, correlation 8 mm;
   - **every result reported against the realised ASSD**, never against the nominal RMS alone.

   The JA8 margins are already in realised ASSD, because they are measured between reads. So the simulation and the
   acceptance rule now use the same unit.
4. **What a border error costs a layer, in that unit:** each 0.1 mm of realised ASSD costs about 0.03 of
   subendocardial Dice. The JA8 margin of 0.15–0.35 mm (Golf v2 §4.5) therefore corresponds to a subendocardial Dice of
   about 0.89–0.95.
5. **Bin flips are rare at these errors.** That fits Juliet R1 E3: border error of 0.5 mm moves transmurality by
   ≤ 0.02, because transmurality is a fraction of the wall. **Border error is not what threatens the scar grade. The
   registration of the late scan is** (E5).

**Limits:**
- 6 hearts;
- the reference borders are model-made labels at 1.5 mm, interpolated;
- sectors stand in for AHA segments in the flip count;
- the Dice-vs-ASSD line is fitted on medians.

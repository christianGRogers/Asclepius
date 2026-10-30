---
aliases: [India - R2 E5-E8 one error model, depth, sectors, rest TPR and the twin guard]
tags: [janus-m, experiment, india, round-2, path-rest-ccta, perturbation, sta, tpr, guard]
status: done
round: 2
path: jm/rest-ccta
advocate: India
updated: 2026-10-30
issue: christianGRogers/Asclepius#142
---

# India R2 E5–E8: one error model, depth, sectors, rest TPR, and the twin guard

**Questions** (Round 1 ruling §6): why did the four Round 1 border-error simulations disagree, and what single model
replaces them (item 2)? Equal-thickness or Yezzi–Prince depth, fixed or arc-proportional sectors, at 0.5 mm (item 3)?
Is rest TPR measurable at 0.5 mm with a guard band (item 6)? How is the seal re-powered (item 5)? What does the JA12
twin rule refuse (item 7)?

Used by [[India v2]]. Code: `experiments/JanusM/India/` (`guard_r2.py`, `fetch_r2.py`, `harness_r2.py`,
`e6_depth_sectors.py`, `e7_tpr_phantom.py`, `e8_repower.py`, `summarise_r2.py`; `fir/jm0_addon.py` for the lead).
Numbers: `results/summary_r2.json`, `results/guard_r2.json`, `results/guard_r2_variants.json`,
`results/e8_repower_table.json`.

## Data and the guard (run first)

1. **The twin guard** (`guard_r2.py`), built from the two public TotalSegmentator `meta.csv` tables (v1, Zenodo
   6802614; v2.0.1, Zenodo 10047292; sha256 in `guard_r2.json`), before any image was requested:
   - held out: the 16 TotalSegmentator s-numbers named by the pool list, the pool seal or any Round 10 draw
     (India v1's `pool_subjects()`); all 16 are present in both releases;
   - twins (ruling §4): any subject of either release with the same sex and institute as a held-out subject of that
     release, age within ±5 years, any study type (missing sex or age counts as a match);
   - **692 twins** of 1,228 subjects (624 in v1, 656 in v2.0.1). Of the 130 v1 cardiac-protocol subjects, 15 are held
     out, 92 are twins and **23 are allowed**.
   - All 16 held-out subjects are from one v1 institute (H). Variants, for the judge (counts only, not used): same
     scanner model in v2.0.1 → 258 twins, 52 cardiac allowed; age ±2 y in v1 → 465 twins, 49 cardiac allowed.
2. **Universe:** allowed v1 subjects whose study covers the heart (cardiac, thorax, polytrauma, whole body): **299**.
   `fetch_r2.py` calls `refuse()` on every id before requesting a byte; it fetched the five heart masks of each (CT
   only for the 23 cardiac ones). E5–E7 use masks only: they need heart shapes, not contrast.
3. **QC** (`harness_r2.load_masks`): LV myocardium and cavity ≥ 2,000 voxels; the LV crop (+14 mm) inside the field of
   view; ≥ 85 % of the cavity's shell is myocardium, LA or aorta.
4. **Disclosure.** No held-out subject or twin was opened. One allowed cardiac CT (s0032) was read, only to smoke-test
   `fir/jm0_addon.py` with a fake coronary tree; no number from it is reported. **49 of the 64 subjects India's Round 1
   experiments used are twins under this rule** (none is held out); the Round 1 numbers stay as recorded.

**The labels** are TotalSegmentator v1's model-assisted, reviewed masks at 1.5 mm, with v1's known myocardium
misalignment. They are shapes, not a border reference; E5–E7 measure geometry and simulated error on them.

## E5: one harness for the four Round 1 error models

**Method** (`harness_r2.py`). For each case, each advocate's committed perturbation is re-implemented as written:

| Model | Working grid | SDF | Field correlation |
|---|---|---|---|
| Golf (`layers_ts.py`) | 0.5 mm | surface half-way between voxel centres (±0.25 mm at the first voxel), native SDF zoomed | 8 mm |
| India v1 (`lvgeom.py`) | 0.5 mm | masks resampled, SDF ±0.375 mm at the first voxel | 8 mm |
| Kilo (`exp_layers.py`) | 0.5 mm | plain `edt(~m) - edt(m)` on the native 1.5 mm grid (±1.5 mm), zoomed | 10 mm |
| Hotel (`layers_from_borders.py`) | 0.75 mm | masks upsampled ×2, plain SDF on that grid (±0.75 mm) | 6 mm |

All four use one field generator (Gaussian-smoothed white noise drawn on a 4× coarser grid, rescaled to RMS σ) and
JA2's equal-thickness depth, so only the SDF, grid and correlation differ. Per model and σ ∈ {0.5, 1.0}: myocardium
and third Dice; the **realised** endocardial and epicardial ASSD between the unperturbed and perturbed walls; and how
far a uniform 0.5 mm field moves the endocardium. Then one model **U** (Golf's slope-1 SDF on 0.5 mm, correlation 8 mm;
4 and 16 mm as sensitivity), σ 0.25 / 0.5 / 1.0, and 0.5 mm endocardial in / out and epicardial out biases, with
realised ASSD and signed bias, per-segment thickness error and STA (Kilo v1 §6.2: scars at τ 0.15/0.40/0.65/0.90 in
segments 1–16 on the reference wall; share whose Kim bin agrees).

**Cases:** 37 passed QC of 59 tried (18 LV crops touched the field of view, 3 had no LV, 1 open cavity).

**Result 1: the four models, same cases** (median; p10–p90 in `summary_r2.json`):

| Model | Subendo Dice σ 0.5 (Round 1) | Realised endo ASSD σ 0.5 | Subendo Dice σ 1.0 | Realised endo ASSD σ 1.0 | Uniform 0.5 mm moves the endocardium |
|---|---|---|---|---|---|
| Golf | 0.897 (0.909) | 0.35 mm | 0.786 | 0.70 mm | 0.53 mm |
| India v1 | 0.929 (0.927) | 0.22 mm | 0.803 | 0.59 mm | 0.51 mm |
| Kilo | 0.944 (0.939) | 0.21 mm | 0.891 | 0.37 mm | 0.27 mm |
| Hotel | 0.977 (0.975) | 0.08 mm | 0.866 | 0.41 mm | **0.00 mm** |

- The harness reproduces every Round 1 value to within 0.012, in the same order.
- **The order is the width of the dead zone**: the SDF value at the first voxel off the surface (Golf 0.25, India
  0.375, Kilo ≈ 0.5 after zooming, Hotel 0.75 mm). A field smaller than that moves no voxel. Hotel's 0.5 mm field is
  almost all inside it.
- **Indexed by realised ASSD, the curves agree:** at 0.21–0.22 mm, subendocardial Dice 0.929 / 0.942 (U σ 0.25) /
  0.944; at 0.35–0.41 mm, 0.897 / 0.896 (U σ 0.5) / 0.891 / 0.866. Spread ≈ 0.03 at matched ASSD vs 0.08 at matched σ.

**Result 2: model U** (37 cases, median, p10 in brackets where useful):

| Condition | Endo / epi ASSD (mm) | Endo / epi signed bias (mm) | Myo Dice | Subendo Dice | STA | Segment thickness error (mm) |
|---|---|---|---|---|---|---|
| random σ 0.25, 8 mm | 0.21 / 0.19 | −0.06 / −0.09 | 0.980 | 0.942 | 1.00 (0.98) | 0.16 |
| random σ 0.5, 4 mm | 0.38 / 0.39 | −0.05 / −0.11 | 0.956 | 0.888 | 0.95 (0.75) | 0.24 |
| random σ 0.5, 8 mm | 0.36 / 0.36 | −0.08 / −0.08 | 0.961 | 0.896 | 0.94 (0.72) | 0.32 |
| random σ 0.5, 16 mm | 0.31 / 0.32 | −0.09 / −0.12 | 0.966 | 0.917 | 0.97 (0.72) | 0.32 |
| random σ 1.0, 8 mm | 0.70 / 0.71 | −0.12 / −0.03 | 0.913 | 0.782 | 0.61 (0.38) | 0.65 |
| endo 0.5 mm in | 0.54 / 0 | −0.54 / 0 | 0.975 | 0.856 | 1.00 (0.98) | 0.49, all thicker |
| endo 0.5 mm out | 0.53 / 0 | +0.37 / 0 | 0.978 | 0.870 | 1.00 (1.00) | 0.43, all thinner |
| epi 0.5 mm out | 0 / 0.52 | 0 / +0.34 | 0.965 | 0.975 | 1.00 (0.98) | 0.42, all thicker |

- **STA responds to random error but is blind to a 0.5 mm bias** (1.00 in every bias row: a scar centred in a Kim bin
  survives a uniform shift). Kilo's Round 1 12.5 % flips were at a 1 mm bias.
- **Segment thickness sees every bias** (0.42–0.49 mm with one sign), which the myocardium Dice (0.965–0.978) does
  not. This supports JA8's thickness co-primary and signed-bias guards.
- The signed-bias estimator under-reads outward shifts (+0.34 to +0.37 for a 0.5 mm shift) because it is evaluated
  on voxel centres; ASSD is exact to ±0.03 mm here. The plan uses ASSD and thickness to decide.

**What it changes:** one error model (U), indexed by realised ASSD; no absolute bar read from any σ curve; STA
reported, not a guard; thickness co-primary confirmed.

## E6: depth and sectors at 0.5 mm

⟨E6⟩

## E7: rest TPR phantom at 0.5 mm

⟨E7⟩

## E8: the seal re-powering rule

`e8_repower.py` fixes the JA8 margins and the seal size as code (rule in [[India v2]] §3.5). The table below is the
probability that the seal's upper 95 % bootstrap bound of mean d is ≤ 0.25 mm, resampling a synthetic 20-case
observation centred on the stated mean (`results/e8_repower_table.json`):

| per-patient SD of d | true mean d | n = 60 | 80 | 100 | 120 |
|---|---|---|---|---|---|
| 0.15–0.25 | 0.00–0.10 | 1.00 | 1.00 | 1.00 | 1.00 |
| 0.25 | 0.15 | 0.92 | 0.97 | 0.99 | 1.00 |
| 0.35 | 0.10 | 0.90 | 0.96 | 0.98 | 1.00 |
| 0.35 | 0.15 | 0.61 | 0.66 | 0.76 | 0.84 |

Resampling one 20-case observation understates the spread of a new 20-case sample; the rule is conservative only
because it is applied to Janus-M 0's own decision-set d, before any seal read. **The seal size is set by Janus-M 0's
mean excess more than by its spread.**

## Limits

- 1.5 mm public shapes, upsampled; v1 labels; non-gated, mixed-phase studies. Geometry and error-model conclusions
  are about shapes and grids; absolute thickness and HU are not normal values.
- E7's PSF and noise are assumptions; JM-0's add-on block E measures native TPR on real CCTA.
- Territories need a coronary tree; no allowed public case has one. They are measured by the JM-0 add-on.

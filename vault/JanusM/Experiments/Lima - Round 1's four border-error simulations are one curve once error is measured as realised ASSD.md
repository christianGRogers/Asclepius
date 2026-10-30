---
tags: [janus-m, experiment, round2, rest-ccta, perturbation, harness, assd, sta, yezzi-prince, territories]
author: Lima
round: 2
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#142
---

# Lima E2: Round 1's four border-error simulations are one curve once error is measured as realised ASSD

**Question (Round 1 ruling §6 item 2).** At "0.5 mm" border error, Round 1 reported a subendocardial-third Dice of
0.909 (Golf), 0.927 (India), 0.939 (Kilo) and 0.975 (Hotel). Is that a disagreement about how layers degrade, or
about what "0.5 mm" meant? And what single error model should later rounds use?

**Setup** (`experiments/JanusM/Lima/harness.py`, `summarise_e2.py`; results in `e2_summary.json`).
- **Cases.** The 23 public TotalSegmentator v1 cardiac subjects that Lima's guard allows (E1). Their 1.5 mm
  model-made masks were taken to a 0.5 mm grid through half-voxel-corrected signed distances. Median wall 9.8 mm,
  6.5 voxels per third. No held-out subject or twin was requested.
- **Error models.** Each advocate's model was re-implemented from their committed code, all on the same walls:

  | Model | Signed distance the noise is added to | Grid | Correlation length |
  |---|---|---|---|
  | Golf | half-voxel corrected | 0.5 mm | 8 mm |
  | India | ±0.75 voxel at the border | 0.5 mm | 8 mm |
  | Kilo | plain, at 1.5 mm, then zoomed | 0.5 mm | 10 mm |
  | Hotel | plain | 0.75 mm | 6 mm |

  Each model uses independent fields per border, at nominal σ 0.25, 0.5 and 1.0 mm. Lima's model (`lima_c8`) is
  Golf's, with correlation lengths of 4, 8 and 16 mm. Uniform 0.5 mm shifts of each border were also run.
- **What is measured on every perturbed wall:**
  - the **realised** endocardial and epicardial ASSD and signed bias against the reference wall (JA8's units);
  - myocardium Dice, and the Dice of each equal-thickness third;
  - the median segment-thickness error;
  - STA, Kilo's definition: 16 segments × 4 virtual scar depths, Kim bins.

**Result 1: the harness reproduces Round 1's spread.** Median subendocardial-third Dice at nominal σ 0.5:

| | Golf | India | Kilo | Hotel |
|---|---|---|---|---|
| Round 1, own cases | 0.909 | 0.927 | 0.939 | 0.975 |
| This harness, the same 23 walls | 0.897 | 0.930 | 0.936 | 0.982 |

**Result 2: the nominal σ is not the error that happens.** Realised mean border ASSD ÷ nominal σ:

| | Golf | India | Kilo | Hotel | Lima (8 mm) |
|---|---|---|---|---|---|
| at σ 0.5 | 0.70 | 0.47 | 0.45 | **0.13** | 0.68 |
| at σ 1.0 | 0.69 | 0.58 | 0.38 | 0.39 | 0.69 |

The mechanism:
- A plain `edt(~m) − edt(m)` jumps by two voxels across the border. That halves every displacement, and on a coarse
  grid it adds a dead zone: Hotel's noise had to exceed 0.75 mm before one voxel flipped.
- India's half-voxel term was halved twice, which leaves a ±0.75-voxel step.
- Golf's corrected distance moves the border by the field. For a smooth Gaussian field, mean |d| is ≈ 0.8 σ, which
  discretisation lowers to 0.7.

**Result 3: against realised error, the four models are one curve.** Pooling every random-field wall:
- the fit is subendocardial Dice ≈ 1.001 − 0.314 · ASSD + 0.0007 · ASSD²;
- the residual SD is **0.018**, against a total SD of 0.071;
- the mean residual per model is ≤ **0.0015** (Golf −0.0005, Hotel +0.0001, India −0.0015, Kilo +0.0006,
  Lima +0.0013).

**Round 1 did not disagree about layers. It disagreed about units.**

| Realised mean ASSD (mm) | Walls | Subendo Dice | STA | Segment-thickness error (mm) |
|---|---|---|---|---|
| 0.0–0.1 | 73 | 0.989 | 1.000 | 0.02 |
| 0.1–0.2 | 77 | 0.960 | 1.000 | 0.12 |
| 0.2–0.3 | 35 | 0.925 | 1.000 | 0.20 |
| 0.3–0.4 | 72 | 0.897 | 0.984 | 0.32 |
| 0.4–0.5 | 20 | 0.869 | 0.938 | 0.41 |
| 0.5–0.7 | 49 | 0.807 | 0.891 | 0.59 |
| 0.7–1.0 | 19 | 0.778 | 0.859 | 0.51 |

**Result 4: the correlation length matters little; bias matters a lot.**
- **Correlation length.** At σ 0.5 with Lima's model, 4 / 8 / 16 mm give subendocardial Dice 0.889 / 0.898 / 0.913,
  realised ASSD 0.36 / 0.34 / 0.31 mm and STA 0.98 / 0.98 / 0.95.
- **Uniform 0.5 mm shifts** keep myocardium Dice at 0.95–0.97, but:

  | Shift | Subendo Dice | STA | Segment-thickness error |
  |---|---|---|---|
  | endocardium inward | 0.83 | 0.97 | 0.64 mm |
  | endocardium outward | 0.82 | 0.98 | 0.63 mm |
  | epicardium outward | 0.94 | 0.95 | 0.64 mm |

**What it changes.**
1. **One error model for the project** (Round 1 §6 item 2): `harness.py` model `lima_c8`. Every result is reported
   against **realised** ASSD and bias, never nominal σ. A later simulation that reports only σ is not comparable and
   should not be weighed.
2. **JA8's ASSD margin of 0.25 mm is final, not provisional.** 0.25 mm of realised error keeps STA at 1.00–0.98 and
   adds about 0.25 mm of thickness error. The margin is a clinical bar, so the first reads have no reason to move it.
3. **JA8's bias guard should be 0.3 mm, not 0.5.** A 0.5 mm bias alone costs 0.63 mm of thickness error, more than
   E3's 0.5 mm usefulness bar for thinning.
4. **STA adds no independent information**, as the ruling said. It is a monotone function of realised ASSD here
   (1.00 up to 0.3 mm). It stays reported, not deciding.

## Self-test of the JM-0b read-out on the same 23 public hearts (a 1.5 mm baseline)

`local_check.py` runs `lima_geom.analyse`, the code Job JM-0b runs on ImageCAS, on 1.5 mm model-made labels
resampled to 0.5 mm. Results are in `local_check_summary.json`. These numbers describe public v1 labels, **not**
CCTA truth. JM-0b repeats every one on native ImageCAS.

| Item | Public baseline (23 hearts) |
|---|---|
| AHA frame | 23 / 23 ok; orientation checks pass in 23 / 23 (fixed and arc sectors); 1 case with an empty segment |
| Wall, median | 9.7 mm (p10–p90 8.5–10.5) |
| Voxels per third at 0.5 mm, per segment | median 6.3; p5 4.4 |
| Segments needing halves (JA2) | 1.6 % (4 cases) |
| Thirds agreement with equal thickness | **Yezzi–Prince 0.973** (p10 0.953); Laplace potential 0.884 |
| Volume share of the thirds (sub-endo / mid / sub-epi) | equal thickness 27 / 34 / 39 %; Yezzi–Prince 28 / 32 / 40 %; Laplace 23 / 32 / 45 % |
| Septal (RV-contact) arc | median 140° (p10–p90 123–157°) |
| Myocardium relabelled by arc-proportional vs fixed sectors | median 14 % (p10–p90 3–27 %) |
| Half-maximum offset, case medians (+ = mask outward) | endocardium −0.45 mm (p10–p90 −1.22 to +0.05); **epicardium +0.64 mm** (+0.07 to +1.29) |
| Rest TPR per segment, 1 mm guard / no guard | median 1.66 / 1.78; 16 % of guarded segments in 0.99–1.25 |
| Hearts with a core fat cluster ≥ 20 mm³ at −50 HU | 96 % |
| Relative segment thickness (thickness ÷ patient median) | septum 1.12–1.29, apex 0.76–0.83; shape-corrected SD **0.088** |
| Territories (synthetic coronaries: wiring test only) | Euclidean and geodesic both reproduce the AHA map (0.3 % of segments discordant); voxel agreement 0.987 |

Reading:
- **Yezzi–Prince confirms equal thickness.** Both measure a fraction of the local wall; Laplace's potential does not.
- **The epicardial offset reproduces Hotel's v1 finding.** Hotel measured +0.86 mm; Lima's method gives +0.64 mm.
- **Rest TPR and fat are uninterpretable at 1.5 mm.** Partial volume and the outward epicardium put fat-range HU into
  the "core". Both go to native data, as the ruling expected.
- **The arc rule relabels a seventh of the wall.** The choice between fixed and arc-proportional sectors matters
  enough to be decided on JM-0b's reference trees.

---
tags: [janus-m, experiment, scar, lie, registration, benchmark, path-b, round3]
author: Juliet
round: 3
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#179
code: experiments/JanusM/bench_lie/
---

# E8: on the shared LIE benchmark, P-K and P-G are struck under JA29 registration; a 4 mm mask with a cavity-rim check fixes registration and catches phase mismatch

## Question

Round 2 §7 item 1 asks for one shared synthetic-LIE benchmark on which every JA29–JA30 menu item runs. A candidate
that fails on it is struck before development, and the spill share of Golf's core rule must be measured. Item 5 asks
how the registration QC cuts are set, and whether a truth-free check catches a phase mismatch.

Golf and Kilo agreed on #179 that Juliet builds the benchmark and that all three use it. **The strike rules were
pre-registered on #179 before any result,** with Kilo's 1a–1c and Golf's scar mix accepted by all three.

## Method

**Code.** `experiments/JanusM/bench_lie/`:
- `fetch.py`, `bench.py`: the generator;
- `menu.py`: reference implementations of the JA29/JA30 text;
- `run.py`: the grid;
- `score.py`: the tables and strikes.

**Data.**
- `results.jsonl.gz`: every per-segment value for every arm and image.
- `scores.json`: the tables.

**Hearts.**
- The 23 public TotalSegmentator v2.0.1 cardiac CTs that are the union of Golf's 22 and Kilo's 15 (CC BY 4.0).
  `janusm.guard.refuse` runs on the whole list before the first byte is fetched, and again per heart: 0 refused.
- Three were skipped for no LV contrast. That leaves **20 real hearts plus Juliet's R2 phantom**.

**Images.**
- **First pass:** the real CT and its labels (JA1), at 1 mm.
- **LIE:**
  - synthetic inside the heart (myocardium 90 HU, scar 150 HU);
  - blood *below* (120), *equal to* (150) or *above* (180) scar;
  - the real chest outside, remapped to a late phase;
  - PSF FWHM 1 mm;
  - noise SD = 60 / CNR, with **CNR 3 or 5**.
- **Three LIEs per case, with the same noise:** the full image, its scar-free twin, and blood set to remote.

**Scar (Golf's mix).** Every segment of one territory draws its subendocardial depth from {0, 15, 35, 60, 90 %}.

**Motion.**

| Name | What moves | How |
|---|---|---|
| none | — | — |
| rigid | the heart + a 4 mm shell, against a **static chest** | 4 mm, 2° |
| scale | as rigid | + 3 % scale |
| phase | as rigid | + a 5 % cavity shrink (wall thickens; non-rigid) |
| nonrigid (Kilo R2 E5) | the **whole image** | rotation N(0, 3°), translation N(0, 4 mm), + a 1.5 mm RMS smooth field |

**Truth** is reported as volume share and as depth extent. Seeds are hashed from (heart, blood, CNR, motion).

**Arms.**
- **oracle:** the true borders.
- **R0.**
- **rigid and affine:** Mattes MI (SimpleITK), FP moving, masked to classes 1–4 dilated 10 mm (JA29).
- **rigid_m4:** the same with a 4 mm mask (a variant).
- **The JA29 chain**, emulated: stop at R0 if all QC values are ≤ their cut (the 95th percentile of R0 on aligned cases, fitted on the other half of the hearts by salted hash); else rigid; affine if it lowers the QC.
- **Variants:** `chain_m4` (rigid_m4 instead of rigid) and `chain_m4_rim` (also `rim_dark` in QC).

**Menu (JA30), as fixed.**
- **Presence:** P-K, P-J (τ fitted on the other half of the hearts, per arm, blood level and CNR, from scar-free segments and twins), P-G.
- **Extent:** E-V, E-D.

**Strike rules (pre-registered).** On the JA29 chain, at CNR 5, with motion none or rigid, at any blood level:
- **a presence rule is struck** if sensitivity < 0.75, or specificity < 0.93, or specificity on scar-free hearts
  (the twin graded with its own constants) < 0.93, or spill share > 0.25;
  - spill share = (sens_full − sens_blood→remote) / sens_full;
  - if every presence rule is struck, none is (1c);
- **an extent rule is struck** if its exact Kim-bin agreement on scar-on-both is < 0.60 under both truths.

## Result

> **Correction (13:28 UTC, Golf on #179).** In the first run (**v1**), `menu.py`'s P-G kept wall voxels with
> `edt ≥ 1.0` from the cavity. That drops no wall voxel, so **v1's P-G lacked JA30's 1 mm endocardial exclusion**.
> P-G numbers in §1–§4 are v1's. The fix uses `edt − 0.5 ≥ 1.0 mm`, from the surface. **§5 gives v2's P-G (final):
> the verdict is unchanged.** P-K, P-J, E-V, E-D, the
> registration and the QC results don't depend on it. v1's data stay committed as `results_v1.jsonl.gz` /
> `scores_v1.json`.

### 1. Strikes (JA29 chain, CNR 5, motion none or rigid; ranges over the three blood levels)

| | Sensitivity | Specificity | Specificity, scar-free hearts | Spill | Verdict |
|---|---|---|---|---|---|
| **P-K** | 0.94–1.00 | 0.61–1.00 | **0.006–0.31** | 0.00–0.09 | **struck** |
| **P-G** | 0.96–1.00 | **0.78–1.00** | **0.81–1.00** | 0.00–0.02 | **struck** (motion "rigid" only) |
| **P-J** | **0.76–0.84** | 0.96–1.00 | 0.97–1.00 | 0.00–0.08 | **survives** |

| Extent (on P-J's scar-on-both) | Volume truth | Depth truth | Verdict |
|---|---|---|---|
| E-V | 0.899 | 0.939 | survives |
| E-D | 0.885 | 0.925 | survives |

- **P-K fails by construction.** Its threshold is half-way to the brightest segment's p99. On a heart with no scar that
  is noise, so 70–99 % of segments are called. With oracle borders the scar-free specificity is still 0.006–0.056.
- **P-G fails only through registration.** With oracle borders its specificity is 0.99–1.00.
- **P-J survives, but misses thin scars.** Its bin-1 sensitivity on the chain is 0.00–0.30. τ is fitted on the chain's
  own scar-free segments, so it absorbs the registration error.
- **The spill share of Golf's core rule (P-G) is 0.00–0.02** in the striking conditions, and ≤ 0.09 anywhere. P-G's
  sensitivity is not blood spill.

### 2. Registration: residual (mm), median / p90 over 126 cases per motion

| Motion | R0 | rigid (10 mm) | affine | rigid (4 mm) | JA29 chain | **chain, 4 mm + rim_dark** |
|---|---|---|---|---|---|---|
| none | 0 / 0 | 0.09 / 0.14 | 0.12 / 0.28 | 0.17 / 0.28 | 0.00 / 0.08 | 0.00 / 0.21 |
| rigid | 4.11 / 4.57 | **1.24 / 2.56** | 1.35 / 2.30 | **0.30 / 0.44** | 1.33 / 3.65 | **0.30 / 0.44** |
| scale | 4.26 / 4.74 | 2.19 / 3.31 | 1.26 / 2.12 | 1.54 / 2.30 | 1.69 / 3.44 | 1.54 / 2.30 |
| phase | 4.19 / 4.60 | 1.28 / 2.68 | 1.30 / 2.18 | 0.30 / 0.47 | 1.30 / 3.67 | 0.30 / 0.47 |
| nonrigid | 6.81 / 10.4 | 1.73 / 2.16 | 1.64 / 2.03 | 1.82 / 2.36 | 1.65 / 2.10 | 1.82 / 2.36 |

- **The 10 mm mask admits static chest**, which pulls rigid MI back toward R0. A 4 mm mask cuts the median residual
  from 1.24 to 0.30 mm. On Juliet's R2 phantom, with little static tissue near the heart, the gap was small. On real
  chests it is not.
- **The JA29 QC trio lets R0 through on 14 of 126 moved cases per motion (11 %).** That is the 3.65 mm p90 of the
  chain. With `rim_dark` added, **0 of 504** moved cases keep R0, and 76 of 126 aligned cases still do.
- **Affine** helps only the scale motion (1.26 against 2.19 mm). It lowers the QC values against rigid in 43–68 % of
  moved cases.

### 3. QC checks: AUC

| Check | Misregistration (R0, moved vs aligned) | Phase vs rigid, after the chain (below / equal / above blood) | Phase vs non-rigid |
|---|---|---|---|
| fat_like (Juliet) | 0.819 | 0.52 / 0.43 / 0.50 | 0.48 / 0.44 / 0.51 |
| blood_like (Juliet) | 0.803 | 0.51 / 0.33 / 0.18 | 0.49 / 0.47 / 0.07 |
| above_blood (Kilo) | 0.691 | 0.56 / 0.36 / 0.32 | 0.53 / 0.53 / 0.12 |
| **rim_dark** (new) | **0.988** | **0.989 / 0.980 / 0.994** | **0.992 / 0.988 / 0.985** |

`rim_dark` is the share of the carried cavity's 2 mm inner rim that reads below (remote + blood median) / 2 on the
smoothed LIE.
- **It catches a phase mismatch.** When the LIE's cavity is smaller than the first pass's, the carried cavity's rim
  covers myocardium.
- **It catches misregistration**, because a shifted cavity's rim crosses the wall.
- **It needs blood brighter than myocardium on the LIE** (true at every level tested: 120–180 against 90 HU). It would
  fail where blood and remote myocardium are equal.

### 4. Reported, never striking

- **With the proposed registration (`chain_m4_rim`), at CNR 5 with motion none or rigid:**
  - P-G passes every bar: sensitivity ≥ 0.979, specificity ≥ 0.985, scar-free specificity 1.00;
  - P-J's sensitivity rises to ≥ 0.888;
  - P-K still fails on scar-free hearts (0.006–0.065).
- **At CNR 3 on `chain_m4_rim`:**
  - P-J holds sensitivity 0.99–1.00 and specificity ≥ 0.96;
  - P-G's sensitivity is 0.90–0.99, with bin-1 sensitivity down to 0.6.
- **Kilo's non-rigid motion defeats every rule after any rigid or affine registration:**
  - specificity 0.5–0.98, with 1.6–1.9 mm residual;
  - with oracle borders, P-G and P-J are clean (specificity ≥ 0.96).
- **Phase-mismatched patients,** even after the best registration, lose bin-1 sensitivity: 0.0–0.5 for P-G. This is
  why JA27 keeps them out of the primary analysis.

### 5. v2: P-G with JA30's endocardial exclusion (the re-run, final)

**The re-run.** Same 630 cases and seeds. It was interrupted once by a container restart and resumed heart by heart.
Every non-P-G number reproduces v1:
- no pooled sensitivity or specificity moves;
- scar-free specificity moves by ≤ 0.003;
- the only per-case differences are SimpleITK's multithreaded affine stage, in 18 of 630 cases (median 0.002 mm,
  max 0.2 mm).

`scores.json` / `results.jsonl.gz` are v2; v1 is kept as `*_v1`.

**P-G, v2, at CNR 5 with motion none or rigid:**

| Arm | Sensitivity | Specificity | Scar-free specificity | Bin-1 sensitivity | Spill | Verdict |
|---|---|---|---|---|---|---|
| **JA29 chain** | 0.875–0.979 | **0.80–1.00** (0.80–0.88 under motion) | **0.84–1.00** | 0.55–0.90 | 0.00–0.03 | **struck** (specificity under motion) |
| chain, 4 mm + rim_dark | 0.915–0.989 | ≥ 0.985 | 1.00 | 0.60–0.94 | 0.00 | passes |
| true borders | 0.921–0.979 | ≥ 0.989 | 1.00 | 0.72–0.90 | 0.00 | passes |

- **The exclusion does not change the verdict.** It lifts specificity under motion a little (0.78–0.86 in v1, 0.80–0.88
  in v2) and costs thin-scar sensitivity: bin 1 falls from 0.82–1.00 to 0.55–0.90 on the chain at CNR 5, and to
  0.25–0.67 at CNR 3 (0.19–0.42 with A2's registration or true borders).
- **The strike is still the registration's.** On true borders, and with A2's registration, P-G passes every bar.
- Golf's own E8 reports 0.75–0.81 sensitivity after affine, on a different generator and scar mix. The benchmark's
  numbers decide, as agreed on #179.

## What it changes

- **Menu after the benchmark, by the pre-registered rules:**
  - **P-K struck**, for the structural reason above;
  - **P-G struck** under JA29 as written;
  - **P-J** goes to development;
  - **E-V and E-D** both stay.

  Juliet v3 §10 asks the judge to reinstate P-G if the registration amendment below is adopted. The strike measures
  the registration, not the rule.
- **Registration amendment (proposed):**
  1. mask the MI metric to classes 1–4 dilated **4 mm**, not 10 mm;
  2. add `rim_dark` to the QC, with its cut set like the others on development.
- **Phase check (item 5):** `rim_dark`, with AUC ≥ 0.98 against both rigid and non-rigid misalignment. A
  development patient whose `rim_dark` stays above its cut after registration is the reader check's "wall thickness
  differs" case, and goes to the phase stratum.
- **Non-rigid misalignment of about 1.5 mm RMS is not gradable** with the JA29 chain. If development's measured
  residuals look like that, the B-spline development arm (JA29) is the next step.
- **Limits.**
  - Synthetic LIE inside real anatomy: homogeneous tissue, no MVO, no beam hardening.
  - One scar draw per heart and condition.
  - The QC cuts are emulated: the 95th percentile of aligned cases from the other half of the hearts.
  - SimpleITK's Mattes MI, not the shipped module. E10 repeats the mask test on the shipped module.
  - 20 real hearts, all from one public dataset.

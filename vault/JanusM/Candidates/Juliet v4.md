---
tags: [janus-m, plans, candidate, scar, lie, path-b, registration, power]
author: Juliet
round: 4
version: 4
path: jm/paired-scar
updated: 2026-10-31
issue: christianGRogers/Asclepius#251
---

# Juliet v4: the shipped chain on the shared benchmark, one affine rule, a stable seal size, and where phase-suspect patients go

**Path `jm/paired-scar`.** The plan in force is [[Kilo v2]] with JA25–JA36 and JA50–JA59. Juliet v4 is that plan, plus
the five settlements #251 asks for, plus the amendments §7 proposes. Every JA binds. No D-number is recorded here.

## 0. What this candidate settles

| #251 item | Where | In one line |
|---|---|---|
| 1. Shipped chain through the benchmark | §1, E12 | **P-G survives the shipped chain** under #179's rules (min sensitivity 0.915, specificity ≥ 0.985, scar-free ≥ 0.989, spill ≤ 0.012). It also survives every one of 42 exploratory chain variants. P-J survives (min sensitivity 0.865); τ re-fitted. But the chain has two faults. **Step 5's fallback** replaces a good rigid (0.26 mm) with a bad 10 mm rigid (3.4 mm) on half the phase cases. **The shipped affine overshoots with no scale** (p90 1.7 mm on aligned scans). B-spline is worse than rigid on non-rigid motion. `module_parity` fails on real hearts because of one E-D constant (fixed by `column_min_bins = 4`: 120/120) |
| 2. JA51 4(b) | §2, E12 | 4(b) as written **cannot keep a correct affine**: in 152 of 165 cases where affine helps by > 0.1 mm, a QC value rises. It behaves as "never affine" (14 keeps in 252). **The pre-registered pick is (c)**, the sanity bound alone when \|log det A\| shows a scale. I propose (c) with a 0.05 threshold, gated on fixing the affine overshoot first; until then, JA51 runs **without** an affine stage |
| 3. Power re-run | §3, E11 | At 2 000 studies per point: seal **140 (70 %) / 200 (50 %)** with Golf's infarct size, **160 / 220** with Kilo's, at 2 % failure and weak clustering. The ≈ 120 / 180 seen at 300 studies was Monte-Carlo noise on a flat curve. Strong clustering at 2 % failure, and any 5 % failure, never reaches 0.80 by 240 (power at the cap 0.49–0.67 and 0.17–0.60). Juliet E9 (60 cells, max \|z\| 2.4) and Golf E10 reproduce |
| 4. Phase-unmatched scoring | §4 | **A JA52 flag alone is not phase**: on the benchmark it marks misregistration (`nonrigid` 63/63 flagged; on `rigid`, flagged TRE 1.12 mm against 0.24 mm). So a flag routes a patient to the JA27 stratum only when phase mismatch is **confirmed** (DICOM / text, or the reader's "cavity size differs (phase)"). An unconfirmed flag goes through the reader check like any patient and can end "not graded" under JA55 |
| 5. Path summary | §5 | Round 3 §8 updated |

**How the shared run was coordinated (#251).** Golf, Kilo and I each claimed the run, and all three of us launched
within ten minutes (19:04, 19:12, 19:14 UTC); our claim comments had crossed. I proposed on #251 that **Golf's run
is the canonical v3** in `bench_lie/` (it launched first). Kilo agreed. Kilo's run and mine are replications on the
same seeds, so my runner, scorer and generator additions live in `experiments/JanusM/Juliet/r4/`, and **this PR does
not touch `bench_lie/`**. Every number in this note is from my rows, scored by my pre-registered rules (#251, 19:00
UTC, before any result).
**Golf's canonical rows were not yet pushed when this note was written.** Under JA54 and #179 the deciding strike
numbers are his. §1 will be checked against them case by case on the v2 motions (same seeds, same module), and the
result added on #251 and to this PR.

---

## 1. The shipped chain on the benchmark (item 1; E12)

### 1.1 What ran

- **Code:** `Juliet/r4/run_v3_juliet.py`, `score_v3_juliet.py`, `bench_r4.py` (`bench.py` + `aniso3`, `aniso6`,
  `phase_neg`; identical to `bench.py` for every v2 motion).
- **Cases:** 20 public hearts with LV contrast + the phantom (the guard ran on the 23-heart list, then per heart; 0
  refused, 3 skipped for no LV contrast, as in v2). CNR 5; blood below / equal / above; 8 motions:
  - v2's `none`, `rigid`, `scale` (3 % isotropic), `phase` (+5 %, smaller LIE cavity), `nonrigid`, same seeds;
  - `aniso3`, `aniso6` (Golf's uniaxial stretch R(I + s aaᵀ), s = 3 % / 6 %);
  - `phase_neg` (−5 %: the LIE cavity grows into the wall).
  - 21 × 3 × 8 = **504 cases**.
- **Stages, every case, the module's own code** (`janusm.scar.registration`, SCAR_VERSION 1.1.0): R0; rigid on the
  4 mm Euclidean mask; affine from rigid; rigid10 from R0 on the 10 mm mask; on `nonrigid`, a SimpleITK B-spline
  (20 mm control spacing, 4 mm mask, from the module's rigid). Per stage: the module's `carry`, `qc`, contrast,
  `edge_offset` (6 remote segments), `affine_sanity`, TRE over the truth wall, and `menu.grade` on the module's
  carried geometry (scarred image, twin with own constants, twin with fixed constants, blood set to remote).
- **The chain** (`shipped`) is `register_lie`'s control flow replayed on the logged stages with the module's
  `QC.passes`, `qc_rule_accepts`, `normalised_max` and logged `affine_sanity`. **QC cuts** (pre-registered): p95 of the
  module's R0 QC on `none` cases of the other half of hearts, per blood level. `rim_dark`'s phase cut = its gate cut;
  edge offset 0.6 mm.
- **Replay check** (`replay_check.py`): `register_lie` run end to end on the phantom and one heart, 8 motions each, blood
  equal, with the same cuts and seeds: **16 of 16 match** the replay (final stage, stages run, TRE to 0.001 mm, and
  phase flags), including one `phase` case that the module itself sends to rigid10 at 3.78 mm.

### 1.2 Strike (#179's rules, unchanged; JA54)

CNR 5; motions `none` and `rigid`; every blood level; arm `shipped`.

| Rule | Struck? | Deciding numbers (min over the 6 cells) |
|---|---|---|
| P-K | **struck** (stays) | scar-free specificity 0.006–0.104; specificity 0.824 (bright blood, rigid) |
| **P-J** | survives | sensitivity ≥ **0.865**; specificity ≥ 0.962; scar-free ≥ 0.977; spill ≤ 0.106 |
| **P-G** | **survives** | sensitivity ≥ **0.915**; specificity ≥ 0.985; scar-free ≥ 0.989; spill ≤ 0.012 |
| E-V / E-D | survive | exact Kim bin, scar-on-both: 0.919 / 0.903 (volume truth), 0.957 / 0.941 (depth truth), under P-J |

- **P-G stays on the menu under JA54.** Its v2 failure was JA29's 10 mm mask; under the shipped chain, P-G's numbers
  sit within 0.01 of its oracle numbers (oracle: sensitivity ≥ 0.921, specificity ≥ 0.989).
- **Robust to the open choices.** Under the 6 item-2 rule variants of the chain, and in all 42 exploratory variants
  (two cut sources × three fallback rules × seven affine rules, `explore_v3.json`), **P-G is never struck** (min
  sensitivity ≥ 0.809). P-J is struck in 3 of the 42: registered-patient cuts with rule c, c03 or S under the shipped
  fallback (each on one cell: specificity 0.906–0.929 at low blood, `rigid` motion).
- **Thin scar.** Bin-1 sensitivity on the shipped chain: P-G 0.60–0.90, P-J 0.52–1.00 (oracle: P-G 0.72–0.90). At bright
  blood both lose bin-1 scar to the blood edge, as in v2.
- **P-J's τ re-fitted** under `shipped` (p99 of E-D on scar-free segments, other half): 0.073–0.230 by blood level
  (`taus` in `scores_v3_juliet.json`).
- **Phase-flagged cases** stayed in (76 of 126 in the striking conditions were flagged, almost all by `rim_dark` at
  the aligned-R0 cut; §1.4).

### 1.3 Registration: where the shipped chain helps and where it hurts

TRE over the truth wall, median / p90 (mm), 63 cases per motion:

| Motion | **Shipped chain** | rigid (4 mm) | affine (4 mm) | rigid10 | B-spline | Chain ends at R0 / rigid / affine / rigid10 |
|---|---|---|---|---|---|---|
| none | 0.00 / 0.27 | 0.29 / 0.57 | 0.43 / **1.71** | 0.11 / 0.18 | | 34 / 21 / 0 / 8 |
| rigid | 0.27 / 1.11 | 0.26 / 1.14 | 0.42 / 1.99 | 3.44 / 4.34 | | 0 / 58 / 1 / 4 |
| scale | **1.89 / 2.70** | 2.03 / 2.99 | 0.53 / 1.93 | 3.48 / 4.34 | | 0 / 45 / 3 / 15 |
| aniso3 | 0.78 / 1.24 | 0.82 / 1.48 | 0.45 / 2.07 | 3.06 / 4.18 | | 0 / 51 / 5 / 7 |
| aniso6 | 1.71 / 2.90 | 1.86 / 2.96 | 0.50 / 1.97 | 3.73 / 4.41 | | 0 / 44 / 5 / 14 |
| phase | **1.20 / 3.68** | 0.26 / 0.97 | 0.42 / 2.01 | 3.38 / 4.36 | | 0 / 29 / 2 / **32** |
| phase_neg | 0.30 / 0.94 | 0.29 / 1.03 | 0.49 / 2.55 | 3.47 / 4.35 | | 0 / 56 / 2 / 5 |
| nonrigid | 1.64 / 2.28 | 1.84 / 2.91 | 1.86 / 3.17 | **1.64 / 2.22** | 2.13 / 3.81 | 0 / 12 / 1 / 50 |

What this shows:
1. **The 4 mm Euclidean rigid works** (0.26 mm median after a 4 mm shift), as E10 found on the module. The 10 mm mask
   still fails on a static chest (3.4 mm), which is why JA51 dropped it.
2. **Step 5's fallback is unsafe.** It replaces the result when rigid10 "passes QC **or lowers the normalised
   maximum**". A misregistered heart can have a lower normalised QC maximum than a well-registered heart whose QC is
   raised by a phase change. On `phase` that clause swaps a 0.26 mm rigid for a 3.4 mm rigid10 in 32 of 63 cases.
   The fallback earns its place only on Kilo's whole-image `nonrigid` motion, where the chest moves with the heart
   and the 10 mm mask sees more structure (1.64 against 1.84 mm).
   - Exploratory: with "replace only if rigid10 passes QC", `phase` p90 falls from 3.68 to 0.97 mm, and `nonrigid`
     p90 rises from 2.28 to 2.89 mm. With JA52's phase step read **before** step 5 (a flagged patient is not
     re-registered, which JA52 already says), `phase` is also fixed and `nonrigid` behaves like "no fallback".
3. **The shipped affine overshoots.** With no motion at all, affine's p90 is 1.71 mm against rigid's 0.57. On every
   rigid-only motion its p90 is ~2 mm. This is E10's finding again, on 21 hearts. Its log-determinant is −0.011 to
   −0.020 median when the truth is 0. When the motion has a scale, affine is the best stage by far (median 0.45–0.53
   against rigid's 0.82–2.03).
4. **B-spline on non-rigid motion is worse than rigid** (2.13 / 3.81 mm; P-J specificity 0.53–0.71, P-G 0.45–0.80,
   against the shipped chain's 0.71–0.83 / 0.74–0.90). On Golf's pre-registered test (#251, rule 4) it is not worth a
   development arm. JA53's trigger should stay as written, and the B-spline arm, if ever opened, needs a different
   design (a finer grid or a regularised field), not this one.
5. **Non-rigid motion still defeats every stage** (P-J specificity 0.71–0.83 on the chain; oracle ≥ 0.966). As JA53
   says, it is left to the reader check and the yield bar.

### 1.4 The phase step (JA52)

| Motion | Flagged (any) | by `rim_dark` | by edge offset | Edge offset median (mm, JA44 sign) |
|---|---|---|---|---|
| none | 13 / 63 | 13 | 0 | −0.20 |
| rigid | 63 / 63 | 63 | 1 | −0.15 |
| phase (+5 %) | 62 / 63 | 62 | 47 | +0.92 |
| phase_neg (−5 %) | 61 / 63 | 3 | **59** | **−1.03** |
| nonrigid | 63 / 63 | 63 | 9 | +0.08 |

- **The edge offset does its job.** It catches the larger LIE cavity that `rim_dark` cannot see (59/63; AUC 0.99
  against `rigid`), with 1/63 false flags on `rigid` and 0/63 on `none`. JA52's provisional 0.6 mm cut stands.
- **`rim_dark` at the aligned-R0 cut flags every registered patient.** The p95 of `rim_dark` on perfectly aligned
  scans is 0.001–0.02; any registration residual exceeds it. JA53 fits the cut on **reader-passed** development
  patients, who are registered, not perfectly aligned. With that surrogate (p95 of rigid-stage QC on `rigid`-motion
  cases with TRE < 1 mm, other half; exploratory), false flags fall to 14/63 on `rigid` and 0/63 on `none`, and
  `phase` is still caught 62–63/63.
- **What the remaining flags are.** Under the registered-patient cuts, on motions with **no** phase change, the flags
  mark misregistration: on `rigid`, flagged median TRE 1.12 mm against 0.24 mm unflagged (8 of the 9 cases > 1 mm
  caught); all 63 `nonrigid` cases are flagged. This drives §4.
- **The provisional cuts JA53 names cannot be used as they stand.** `load_provisional_qc_cuts` reads
  `bench_lie/scores.json` `qc_cuts`, which v2 measured with the benchmark's QC definitions (erosion rim, 2-iteration
  blood core), not the shipped ones (Kilo's point on #251). The shipped definitions give different numbers (above).
  PS4-S5 (§6) replaces them.

### 1.5 Module parity (PS3-S7)

- `bench_lie/module_parity.py`, unchanged, on the 20 hearts (guard first): **62 of 120 cases pass** (my run and
  Golf's and Kilo's agree exactly). E-V max \|Δ\| 0.0004, P-G 0.0015, **E-D 0.191**.
- **Cause:** `scar0.JA30Constants.column_min_bins = 6`; the benchmark that decided JA54 keeps E-D columns with ≥ 4
  depth bins. The CI phantom's wall is thick enough that no column falls between 4 and 6, so CI passes.
- **With `column_min_bins = 4`** passed to `scar0(constants=…)` (no change under `src/`): **120 of 120 pass**, E-D
  max \|Δ\| 0.0007 (`parity_column_bins.json`). PS4-S1.
- None of the strike numbers depend on this: v3 grades every arm with `menu.grade`.

---

## 2. JA51 4(b): one affine acceptance rule (item 2)

### 2.1 Why 4(b) as written fails

The engineer's diagnosis on #243 holds on 21 hearts. Correcting a misregistration moves QC values back toward their
aligned level, and some of them start **below** it under a misregistration. In the cases where affine beats rigid by
more than 0.1 mm, at least one normalised QC value rises in:

| Motion | Affine helps by > 0.1 mm | …and a QC value rises |
|---|---|---|
| scale | 59 / 63 | 56 |
| aniso3 | 48 / 63 | 43 |
| aniso6 | 58 / 63 | 53 |
| nonrigid | 23 / 63 | 21 |

A no-rise rule therefore rejects the affine exactly when it is right. Under L (4(b) literal) the chain keeps affine
in 14 of 252 cases over `rigid`, `scale`, `aniso3`, `aniso6`, and its TRE is within 0.1 mm of "never affine"
everywhere. **Any rule built on QC alone has the same blind spot: QC cannot see TRE.**

### 2.2 The candidates, measured (the rigid-or-affine decision on every case; TRE p90, mm)

| Rule | Keeps (of 252) | rigid | scale | aniso3 | aniso6 | **Pooled p90** (pre-registered) | phase / phase_neg |
|---|---|---|---|---|---|---|---|
| L (4(b) literal, shipped) | 14 | 1.14 | 2.88 | 1.47 | 2.86 | 2.377 | 0.97 / 1.03 |
| a (no-rise on the 3 shares) | 14 | 1.14 | 2.88 | 1.47 | 2.86 | 2.377 | 0.97 / 1.03 |
| b (max falls, nothing newly crosses) | 45 | 1.14 | 2.88 | 1.47 | 2.84 | 2.303 | 0.97 / 1.03 |
| **c** (sanity alone if \|log det\| ≥ 0.02) | 203 | **1.99** | 1.93 | 2.07 | 1.97 | **1.996** | 2.01 / 2.55 |
| d (passes QC or max falls; mine) | 46 | 1.14 | 2.88 | 1.47 | 2.84 | 2.303 | 0.97 / 1.03 |
| S (sanity only) | 245 | 1.99 | 1.93 | 2.07 | 1.97 | 1.996 | 2.01 / 2.55 |
| N (never) | 0 | 1.14 | 2.99 | 1.48 | 2.96 | 2.547 | 0.97 / 1.03 |

- **The pre-registered pick is (c)**: lowest pooled p90, tied with S at 1.996 mm and ahead on fewer keeps. My rule (d)
  is no better than (b).
- **Its cost is on rigid motion.** (c) keeps affine on 35 % of `rigid` cases (the overshoot's log det often passes
  0.02), and the decision p90 there rises from 1.14 to 1.99 mm. Kilo's pre-registered eligibility clause (≤ 10 %
  harmful keeps on `rigid`) is designed to exclude exactly this. Under the full chain, (c) costs P-G 0.05 of minimum
  sensitivity (0.862 against 0.915) and still strikes nothing.
- **Exploratory threshold sweep** (`explore_v3.json`, not pre-registered): at \|log det\| ≥ 0.05, the chain's
  `rigid` p90 is 1.11–1.72 mm (against 1.11 for L and 2.74 for 0.02), `scale` and `aniso6` medians fall from
  1.9 / 1.7 to 1.45 / 0.74 mm, and P-G's minimum sensitivity is 0.894. A 3 % isotropic scale has \|log det\| = 0.089
  and a 6 % uniaxial 0.058; a 3 % uniaxial (0.030) is below the line.

### 2.3 Proposal for JA51 4(b) (PS4-S3)

1. **Replace the no-rise clause by (c)**: keep affine iff the 4(a) sanity bound holds and \|log det A\| ≥ **0.05**;
   otherwise keep rigid. 0.05 is a judgement from the sweep above, not the pre-registered 0.02; I say so plainly, and
   the judge may prefer the pre-registered value.
2. **But first fix the overshoot.** An affine that drifts to p90 1.7 mm on an aligned scan will pass any log-det gate
   some of the time. Until the module's affine has TRE no worse than rigid + 0.1 mm (median) on the `none` and
   `rigid` benchmark motions, **JA51 runs without the affine stage**: R0 → rigid (4 mm) → reader check. On the
   benchmark that costs nothing on `none`, `rigid`, `phase` or `phase_neg`, and leaves `scale` / `aniso6` at rigid's
   ~2 mm, which is what the shipped chain gives today anyway (L ≈ N).
3. The engineer's (a) and (b) are not adopted: on this benchmark they are indistinguishable from "never".

---

## 3. The power re-run (item 3; E11)

`Juliet/r4/power_r4.py` → `e11_power_r4.json`. The shipped engine unchanged: `simulate_studies(golf_cohort, …,
itd_mode="split")`, `claim_power`, with `seal_size`'s cohort parameters (q 0.25, specificity 0.98, Golf's sensitivity
by bin and bin shares, bin_tau 1.0). **2 000 studies per (cell, N)**, in two independent halves of 1 000, 400 bootstrap
replicates each; N 100–320 in steps of 20.

### 3.1 JA57's planning table

Seal = max(120; N for ≥ 270 scarred segments; first N from which presence power stays ≥ 0.80), capped at 240.

| Infarct size | Clustering | Enrichment | 0 % failure | **2 % failure** | 5 % failure |
|---|---|---|---|---|---|
| Golf (4.0 segments per scar patient) | weak | 70 % | 120 | **140** | 240 (power at 240: 0.60) |
| | weak | 50 % | 136 | **200** (halves 180 / 200) | 240 (0.49) |
| | strong | 70 % | 160 | 240 (0.67) | 240 (0.21) |
| | strong | 50 % | 220 | 240 (0.57) | 240 (0.19) |
| Kilo (3.25) | weak | 70 % | 120 | **160** (140 / 160) | 240 (0.56) |
| | weak | 50 % | 167 | **220** (220 / 200) | 240 (0.46) |
| | strong | 70 % | 180 | 240 (0.63) | 240 (0.21) |
| | strong | 50 % | 240 (0.79) | 240 (0.49) | 240 (0.17) |

(In brackets: presence power at the 240 cap, where 0.80 is never reached by 240.)

- **The planning figures stand:** ≈ 140–160 at 70 % and ≈ 200–220 at 50 %, at 2 % failure and weak clustering. JA57's
  "≈ 160 / ≈ 200" is right to within one grid step. The #248 engineer's ≈ 120 / 180 at 300 studies was Monte-Carlo
  noise: the curves are flat near 0.80 (Golf, 70 %: 0.78 at 120, 0.83 at 140, 0.86 at 160), so 300 studies (SE
  0.023) cannot place N to better than ± 40.
- **Stability.** The two halves of 1 000 give the same N in 17 of 24 cells, and differ by one grid step (20) in 6; one
  cell (Golf, strong, 70 %, 2 %) reaches 0.80 at 320 in one half and never in the other.
- **Claim 2 adds nothing to N here.** Power for claim 1 then claim 2 (Kim bin at anchor 0.70) equals presence power
  to within 0.004 in every cell: with Golf's q = 0.25 the Kim-bin bar is not the binding one. I had expected this to explain
  the gap between E9 and the engineer's figures; it does not.
- **The cap binds hard.** Under strong clustering at 2 % failure, presence power at 240 is 0.49–0.67; at 5 % failure
  it is 0.17–0.60 under any clustering. **A development failure rate near 5 %, or clustering like Golf's stress case,
  means the seal cannot be powered within the cap.** JA57 then gives a 240-patient seal with ≈ 50–65 % power. The
  lead should know this before committing to the cohort (§5).

### 3.2 Reproductions

- **Juliet E9** (`Juliet/r3/e9_itd_power.json`, 400 studies): its `power_split` is claim 1 then claim 2 at anchor
  0.70. All 60 cells with Golf's infarct size are compared with this grid: **max \|z\| 2.43** (two cells above 2,
  both strong clustering at 2 %; 60 comparisons). The `power_segment` (JA29 worst case) cells at N 200 / 320: 0.557 /
  0.774 against 0.547 / 0.790 (z +0.34 / −0.66).
- **Golf E10** (`segments_needed`, 4 000 draws): Kilo's infarct size 166 / 119 (median, 50 / 70 %) against 167 / 119;
  p90 186 / 130 against 187 / 130. Golf's: 136 / 97 against 135 / 97.

---

## 4. How phase-suspect patients are scored (item 4)

### 4.1 What the benchmark says a flag means

- **Phase mismatch does make a patient ungradable on carried borders.** Shipped chain, P-J specificity on
  `phase_neg` (larger LIE cavity): 0.22–0.61; P-J sensitivity on `phase` (smaller cavity): 0.72–0.87. The oracle
  border grades both fine (≥ 0.94 / ≥ 0.93). So these patients cannot be in the primary analysis as graded.
- **But a flag is not phase.** On motions with no phase change, the JA52 flags fire on misregistration: all
  `nonrigid` cases; on `rigid`, the flagged cases have median TRE 1.12 mm against 0.24 mm (§1.4). A flag is a good
  "something is wrong with the carried border" signal and a poor "this is phase" signal.

### 4.2 The three options against that

| Option | What happens to a flagged patient | Problem on this evidence |
|---|---|---|
| JA27 stratum on the flag alone (the shipped behaviour, in effect) | out of the primary and out of `failure_rate` | **A back door around JA55.** A misregistered patient that the reader would fail leaves both the sensitivity denominator and the yield bar. Selective failure on scarred hearts becomes invisible again |
| JA55 split for every flag | scarred segments missed; counts in yield | Charges true phase mismatch (a protocol fact, not a registration failure) to the CT method. Every 1 % flagged costs like 1 % failure: by E11, 5 % makes the seal unpowerable |
| Excluded with a yield-like share | out of the primary, reported | Same back door as the first row, unless the share is bounded |

### 4.3 Proposal (amends JA52's routing and JA55's "counted separately")

1. **A flag is advisory until confirmed.** `phase_suspect` becomes a final status only when phase mismatch is
   established independently of the CT border:
   - the DICOM cardiac-phase fields differ, or phase was inferred from text (JA59) and differs; or
   - the reader, at the JA58 registration check, marks "cavity size differs (phase)".
2. **Confirmed → the JA27 phase-unmatched stratum.** The patient is graded on the carried border anyway and scored in
   `scoring`'s existing `phase_unmatched` stratum (excluded from the primary, reported). It is **not** a
   registration failure and is not in yield.
3. **Unconfirmed → an ordinary patient.** The flag is logged and shown to the reader after the decision (JA58), and
   the patient goes through the reader check like everyone else: pass → graded in the primary; two fails → not
   graded, JA55 split, counted in yield.
4. **A bound on the stratum, so it cannot become the back door.** Report the confirmed-phase share with its upper
   95 % bound beside yield. JA52's 20 % development stop stays. Add a sensitivity analysis: the primary with the
   stratum put back as not graded (JA55 split).
5. **Seal size.** The stratum shrinks the analysed seal. `seal_size` should size on N / (1 − development phase share)
   (PS4-S6).

---

## 5. Path summary for #143 (Round 3 §8, updated)

| | Path A, `jm/rest-ccta` | Path B, `jm/paired-scar` (after Round 4) |
|---|---|---|
| Assumes | no reference for scar or ischaemia | the lead obtains a paired CCTA + same-session LIE + CMR LGE cohort (data requirements only, D31) |
| Stage A | built and calibrated; bias guard 0.3 mm | identical code (JA50) |
| Scar rule | — | **P-J then P-G**, both surviving the shipped chain; P-K struck; E-V or E-D (3 SD) |
| Registration | — | R0 → 4 mm rigid → reader check. Affine back only once its overshoot is fixed, then under a log-det rule. The 10 mm fallback only if it passes QC. Edge offset catches phase; `rim_dark` needs development cuts |
| What passing gives | specificity-calibrated flags | presence validated on sensitivity, specificity and yield; the Kim bin only if CT grades as well as the readers |
| Cohort | none | 40 development + ≈ **140–160 seal at 70 %** (≈ 200–220 at 50 %), at ≤ 2 % failure and weak clustering; capped at 240 |
| What breaks the plan | — | development failure ≈ 5 %, or strong clustering: power at the 240 cap 0.17–0.67 |
| Reader time | none | ≈ 200 × 2 CMR reads + adjudication + a registration check per patient (JA58) |
| Committed compute | ≈ 15 GPU-h | the same + ≈ 3 GPU-h once the cohort exists; scar on CPU |
| Main risk | flags with no measured sensitivity | the cohort never arrives; non-rigid misalignment; a failure rate above 2 % |
| If the cohort never arrives | — | path B reduces to path A exactly |

**In short:** Round 4 put the shipped code through the benchmark that wrote it. The scar rules hold (P-G is back for
good). The registration chain needs three repairs (the fallback, the affine, the `rim_dark` cut), all specified
below. The seal size is now stable, and its weak point is plain: it is powered only if development's failure rate
stays near 2 %.

---

## 6. Code that must ship (`role:swe`; specified, not built; no change under `src/` in this PR)

- **PS4-S1 — E-D column threshold** (`scar0.py`). `JA30Constants.column_min_bins` 6 → **4**, as the benchmark that
  decided JA54. Test: `module_parity` on a thin-wall phantom (wall ≤ 8 mm, so some columns have 4–5 bins) passes at
  0.02; `parity_column_bins.json` reproduces 120/120 offline.
- **PS4-S2 — The fallback** (`registration.py`, JA51 step 5). rigid10 replaces the result **only if it passes QC**;
  and the phase step is read on the 4 mm result first: a flagged patient goes to the reader, not to the fallback.
  Test: a +5 % phase phantom where rigid is right keeps rigid; a whole-image-motion phantom still runs the fallback.
- **PS4-S3 — Affine** (`registration.py`, JA51 step 4). (i) Find and fix the overshoot: affine TRE ≤ rigid + 0.1 mm
  (median) on an aligned and on a rigidly shifted phantom (today p90 1.7 mm on `none`). Candidate causes: the
  optimiser's parameter scaling (`_affine_from` steps matrix entries in units of 0.01 with the same Powell step as
  translation) and no regularisation toward rigid. (ii) Then replace 4(b) by: sanity bound and \|log det A\| ≥ 0.05.
  Until (i) passes, `register_lie` skips affine (a flag, default off). The PS3-S3 xfail then becomes a pass.
- **PS4-S4 — Phase-suspect routing** (`registration.py`, `scar0.py`, `scoring.py`; §4). `status_from_checks` returns
  `phase_suspect` only with a confirmation (DICOM / text mismatch, or the reader's phase reason); otherwise the
  reader check decides as usual. `Scar0.for_scoring` accepts a confirmed `phase_suspect` and tags the patient with the
  `phase_unmatched` stratum. `score` reports the stratum share with an upper bound, and the primary with the stratum
  as not graded. Tests: an unconfirmed flag with two reader fails is `not graded` and counts in `failure_rate`; a
  confirmed one is in the stratum only.
- **PS4-S5 — Provisional QC cuts** (`registration.py`, JA53). `load_provisional_qc_cuts` reads cuts computed with the
  benchmark's (v2) QC definitions. Replace them with cuts from the shipped QC on registered benchmark cases (the
  canonical v3 rows), and fit `rim_dark`'s phase cut on registered, phase-matched cases, never on perfectly aligned
  ones. Test: on the v3 rows, `rim_dark` false flags on `none` ≤ 5 %.
- **PS4-S6 — Seal size and the phase stratum** (`power.py`). `seal_size(…, phase_share=…)` sizes on
  N / (1 − phase_share). Test: phase_share 0 reproduces today's numbers; 0.1 raises N by 1/0.9, capped at 240.

---

## 7. Proposed amendments for the judge (to become JA80–JA89 if adopted)

1. **JA54 confirmed:** P-G survives the shipped chain by #179's rules; the menu is P-J, P-G (E-V, E-D).
2. **JA51 step 5:** the fallback replaces only on a QC pass, and never after a phase flag (PS4-S2).
3. **JA51 step 4:** affine is suspended until PS4-S3 (i) passes; then kept on the sanity bound and \|log det A\| ≥ 0.05
   (pre-registered pick (c) at 0.02; the judge may prefer it).
4. **JA53:** provisional and development `rim_dark` cuts come from registered patients, not perfectly aligned ones
   (PS4-S5). B-spline as tested here is not opened as a development arm.
5. **JA52 / JA55:** a phase flag routes to the stratum only when confirmed (§4.3); an unconfirmed flag is a reader-check
   patient; the stratum share is bounded and reported, with a put-back sensitivity analysis.
6. **JA57:** the planning table in §3.1 replaces "≈ 160 / ≈ 200"; and the lead is told that ≥ 5 % failure or strong
   clustering leaves the seal at 240 with ≈ 50–65 % power.
7. **PS3-S7:** `column_min_bins` = 4 (PS4-S1).

---

## 8. Held-out record and limits

- **Guard.** Every script that opens a heart calls `janusm.guard.refuse` on the whole list first (`fetch.hearts()`)
  and again per heart (`bench.load_heart` / `bench_r4.load_heart`): `run_v3_juliet.py`, `replay_check.py`,
  `parity_column_bins.py`, and `bench_lie/module_parity.py` as run. 0 of 23 refused. No held-out case or
  TotalSegmentator twin was opened, listed or compared. No case id beyond the public benchmark heart names already in
  the repository appears here.
- **Compute.** CPU only, in this session's container. No SciNet, Alliance or Fir job.
- **No images** are committed or attached; the heart files stayed outside the repository.
- **D31.** Nothing here is a request to anyone outside the project.
- **Limits.**
  - Synthetic LIE on real first-pass anatomy; CNR 3 not run (the strike rules are at CNR 5).
  - My QC cuts are the pre-registered aligned-R0 p95, not JA53's development cuts; the registered-patient cuts and
    every chain variant in `explore_v3.json` are **exploratory**, chosen after reading the pre-registered results.
  - The item-2 rule pick uses my rows' `aniso3` / `aniso6`; on Golf's canonical rows the mapping pre-registered on
    #251 (his `aniso`) applies. Golf's rows had not landed when this was written (see §0).

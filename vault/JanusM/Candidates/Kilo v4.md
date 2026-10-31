---
tags: [janus-m, candidate, round4, paired-scar, lie, registration, affine, phase, power, kilo]
author: Kilo
round: 4
version: 4
path: jm/paired-scar
updated: 2026-10-31
issue: christianGRogers/Asclepius#251
---

# Kilo v4 (path `jm/paired-scar`): the shipped chain keeps P-G, the affine rule should be (b), and the phase check needs cuts fitted after motion

## 0. In one paragraph

**Kilo v4 is Kilo v2 as amended by JA25–JA36 and JA50–JA59.** It settles items 1–5 of #251.

- **Item 1: the shipped chain through the shared benchmark.**
  - **P-G survives** the #179 strike rules under JA51's chain as shipped (§1.3). P-J survives, and P-K stays
    struck. This holds on Golf's canonical rows (441 cases at CNR 5; P-G worst sensitivity 0.915, specificity
    0.985), and on my rows and Juliet's replication. The three runs agree case by case (§1.3).
  - The shipped module fails parity on 58 of 120 real-heart cases, on **E-D only**. The cause is one constant:
    `column_min_bins` 6 against the benchmark's 4 (§1.5, PS4-K1).
  - **The phase check is the weak link (§1.4).** Both the provisional cuts and cuts fitted on aligned (`none`)
    cases put `rim_dark` far below what a *correctly* registered moved heart reads. The flag fires on 100 % of
    rigid-motion cases that have no phase change. Most of this is how the cuts are fitted, not the measure. Cut
    against the true geometry after motion, the false flags fall to 18 %. The edge offset works as JA52 hoped: it
    flags 92 % of `phase_m5` (larger LIE cavity) and 0 % of rigid cases.
- **Item 2: the affine rule (§2).** On my pre-registered criterion, **(b)** wins at both cut sets: the normalised
  maximum falls, and no value newly crosses its cut.
  - (c) is ineligible: it keeps a worse affine on 8 of 10 rigid cases (p90 TRE 3.7 mm).
  - My own (k) does no better than JA51 as written, so I withdraw it.
  - Every QC rule still rejects most of the affines that fix a 6 % stretch. The QC values cannot see a scale well.
  - JA51's 10 mm fallback stays: it rescues non-rigid cases. Its one bad case, a phase change, is handled by
    grading phase-unmatched patients on the 4 mm stage.
- **Item 3: the power re-run (§3).**
  - At 2 % failure and weak clustering, the seal is **140 at 70 % and 180 at 50 %** (Golf's infarct size), or 160
    and 220 (Kilo's).
  - The ruling's ≈ 160 / ≈ 200 were Juliet E9's 40-patient grid steps.
  - N is stable at 2 × 2000 simulations (23 of 24 cells agree) and not at 300.
  - Claim 2 never binds at the base extent error.
- **Item 4: the phase-unmatched stratum (§4).** A JA27 stratum, graded and reported, outside the primary claim and
  outside the yield bar. The truth-free flag routes a patient there only with the reader's mark, or when its phase is
  inferred. The code to do this does not exist yet (PS4-K4).
- **Item 5: the path summary for #143 (§5).**

**What I did not do.** I opened no held-out case or twin. Every heart went through `janusm.guard.refuse` first:
`fetch.hearts()` on the whole list, then `bench.load_heart` per heart. I ran no Fir, SciNet or Alliance job and
changed nothing under `src/`. No image is committed, and nothing here is a request to anyone outside the project.

---

## 1. Item 1: the shipped chain through the shared benchmark

### 1.1 One benchmark, and what is mine

- **Our three claims to run the benchmark crossed** (Golf 19:04, Juliet 19:12, Kilo 19:14 UTC, 2026-10-30). By
  agreement on #251, **Golf's run is the canonical v3**: `bench_lie/run_v3.py`, `results_v3.jsonl.gz`,
  `scores_v3.json`, from Golf's PR.
- **Mine is a replication**, entirely in `experiments/JanusM/Kilo/r4/`:
  - `run_shipped.py`;
  - `bench_kilo_r4.py`: `bench.py` at 93c9380 plus my `phase_m5`, `aniso3` and `aniso6`, exactly as run;
  - output: `results_kilo_r4.jsonl.gz`.
- **To free CPU for item 3, I cut my replication** before reading any of its results:
  - `none` is complete (63 cases);
  - `rigid` is half done (33 cases, 11 hearts);
  - `aniso3`, `aniso6` and `phase_m5` are complete (63 each);
  - `scale`, `phase` and `nonrigid` are left to the canonical rows.
- **Scoring.** `score_shipped.py` scores both row sets under the rules I pre-registered on #251 (18:56 and about
  19:04 UTC, before any result). `golf_rows.py` maps Golf's rows into it.
- **Disclosure.** I saw a 3-case phantom smoke test (stage TREs only) after posting rule (k) and the cut handling.

### 1.2 How the chain is run

- **The chain.** `janusm.scar.registration` as shipped (SCAR_VERSION 1.1.0, Euclidean masks, its own Mattes MI and
  Powell search). Each case runs once with QC forced to fail, so every stage exists: R0 → rigid (4 mm) → affine
  (4 mm) → rigid10 (10 mm, from R0).
- **The replay.** The chain is replayed offline at a cut set and an affine rule. A stage never starts from a QC
  decision, so the forced stages are exactly the stages the chain would compute.
- **The replay check.** One un-forced `register_lie` call per heart, at (equal, CNR 5, rigid) and the provisional
  cuts. It picks the replay's final stage in **11 of 11** hearts.
- **Two cut sets:**
  - **prov:** JA53's provisional cuts, `load_provisional_qc_cuts`, from `bench_lie/scores.json`;
  - **fit:** p95 of the shipped QC at R0 on `none` cases, on the other half of the hearts, per blood level.
    Development would fit cuts this way, and Golf's and Juliet's chains use them.
- **Grading.** `menu.grade` grades every arm, as v2 did, so the #179 strike rules read the same scorer.

### 1.3 The strike (P-G under JA54)

**Deciding, under the #179 rules (CNR 5; none and rigid; every blood level), on Golf's canonical `chain`:**
- **P-G is not struck. P-J is not struck. P-K is struck.** Golf's rows (`bench_lie/results_v3.jsonl.gz` at 370fbbd)
  give 441 cases at CNR 5. Golf's own scorer and my `golf_rows.py` agree.

  | Rule | worst sensitivity | worst specificity | worst scar-free specificity | worst spill |
  |---|---|---|---|---|
  | P-G | 0.915 | 0.985 | 0.989 | 0.012 |
  | P-J | 0.888 | 0.958 | 0.972 | 0.125 |
  | P-K | struck: specificity 0.885 (above/rigid); scar-free specificity 0.006–0.115 | | | |

- **The same verdict holds** on my `chain_ja51_prov` and `chain_ja51_fit`, on (a), (b) and (k) at both cut sets,
  and on oracle.
- **Under (c) at the provisional cuts, P-G *is* struck** (specificity 0.929, below/rigid). At the fit cuts the
  whole menu fails, so rule 1c applies.
- **Determinism.** On the 96 cases my rows share with Golf's, every stage TRE agrees exactly and the QC values agree
  to 5 × 10⁻⁵. Golf's chain TREs on the v2 motions equal Juliet's to the third decimal. The three containers
  produce the same benchmark.

**On my rows, `chain_ja51_prov` (the deciding arm of my pre-registration):**

| Rule | struck | worst sensitivity | worst specificity | worst scar-free specificity | worst spill |
|---|---|---|---|---|---|
| P-K | **yes** (scar-free specificity 0.006–0.13; specificity 0.906 above/rigid) | — | — | — | — |
| P-J | no | 0.888 (above/none) | 0.948 (equal/rigid) | 0.973 | 0.114 |
| P-G | no | 0.894 (above/rigid) | 0.978 (equal/rigid) | 0.978 | 0.024 |

- **The same verdict holds on every other arm I scored:**
  - `chain_ja51_fit`;
  - (a), (b) and (k) at both cut sets;
  - the 4 mm rigid stage alone;
  - oracle.
- **The exception is (c), and it is a second reason not to adopt it.** Under (c) the chain keeps bad affines on
  rigid motion. On my rows that strikes **P-G** (specificity 0.87–0.91), P-J (sensitivity 0.65) and P-K together.
  Rule 1c ("the menu never goes empty") then sends P-J to development with Scar-1 expected. On Juliet's rows, (c)
  strikes P-G at specificity 0.929, at both cut sets. It is reported, not striking, but adopting (c) would undo
  JA54's P-G.
- **P-G's numbers are close to oracle's.** Oracle gives 0.921–0.980 sensitivity and specificity ≥ 0.978. The
  shipped 4 mm chain loses at most 0.04 sensitivity against exact borders.
- **P-J's τ re-fitted under the shipped chain** (p99 of E-D on scar-free segments, other half, none + rigid): 0.074–0.077
  below, 0.131–0.149 equal, 0.169–0.220 above. Round 3's JA29 10 mm chain needed τ 0.22–0.34 at CNR 5
  (`bench_lie/scores.json`). The 4 mm chain's smaller residual roughly halves τ at blood "below" and "equal", which is
  what lets P-J keep its bin-1 sensitivity (JA54's "τ absorbs registration error").

**Caveat.** My `rigid` set has 11 hearts per blood level, so the canonical rows (20 hearts + the phantom) decide.

### 1.4 Registration by motion, and the phase check

**Stage TRE, median / p90 mm (my rows, CNR 5, all blood levels):**

| Motion | R0 | rigid 4 mm | affine 4 mm | rigid 10 mm | chain JA51, prov | chain (b), fit |
|---|---|---|---|---|---|---|
| none | 0 / 0 | 0.29 / 0.57 | 0.43 / 1.71 | 0.11 / 0.18 | 0 / 0.14 | 0 / 0.27 |
| rigid (11 hearts) | 4.21 / 4.57 | 0.27 / 1.14 | 0.37 / 1.99 | 3.73 / 4.41 | 0.27 / 1.14 | 0.27 / 1.14 |
| aniso3 | 4.18 / 4.66 | 0.82 / 1.48 | 0.45 / 2.07 | 3.06 / 4.18 | 0.78 / 1.24 | 0.75 / 1.24 |
| aniso6 | 4.30 / 4.90 | 1.86 / 2.96 | 0.50 / 1.97 | 3.73 / 4.41 | 1.71 / 2.76 | 1.47 / 2.90 |
| phase_m5 | 4.12 / 4.58 | 0.29 / 0.98 | 0.43 / 2.16 | 3.42 / 4.29 | 0.29 / 1.06 | 0.32 / 1.21 |

What the table says:
- **4 mm rigid recovers a 4 mm heart shift** (0.27 mm median), as E10 found.
- **Affine at 4 mm overshoots when there is no scale** (p90 2.0 mm against 1.1). **It wins clearly when there is
  one:** 6 % uniaxial, 0.50 against 1.86 mm.
- **The 10 mm fallback is worse on average whenever the heart moved** (3–4 mm), but **mostly not when the chain
  picks it.**
  - It replaces a result almost always through "lowers the normalised maximum", not through "passes": 0–1 of 1–14
    replacements per motion pass QC.
  - Most of those are cases where the 4 mm result was itself bad. On my rows, allowing it in only when it passes
    would make the p90 worse on `aniso3` (1.24 → 1.47 mm) and on `none` at the fitted cuts (0.27 → 0.41 mm), and
    better on `phase_m5` (1.06–1.21 → 0.97 mm).
  - Juliet's rows add `scale`, `phase` and `nonrigid`. There it rescues `nonrigid` (2.75 → 2.23 mm) but badly
    hurts `phase` (+5 %): it replaces a good 0.26 mm rigid result in about half the cases, p90 0.97 → 3.68 mm.
    Juliet and Golf saw the same.
  - So JA51 step 5 stays as written. The phase cost is handled where it arises: phase-unmatched patients are
    graded on their last 4 mm stage (§2.3, §4).
- On `none`, rigid10 beats rigid4 (0.11 against 0.29 mm). The static chest anchors it when nothing moved, which
  is not the case that matters.

**The phase check (JA52), on the final stage of the shipped chain:**

| Motion | flagged, prov | flagged, fit | by `rim_dark` | by edge offset |
|---|---|---|---|---|
| none | 0 % | 21 % | 0 % / 21 % | 0 % |
| rigid (no phase change) | **100 %** | **100 %** | 100 % | 0 % |
| aniso3 / aniso6 (no phase change) | 86 % / 95 % | 95 % / 100 % | as left | 0 % / 6–8 % |
| phase_m5 (LIE cavity 5 % larger) | 98 % | 98 % | 8–10 % | **92 %** |

- **`rim_dark`'s cut is unattainable after any motion.** On the *true* geometry, `rim_dark` is 0.001–0.015
  (median) when the heart does not move. After any motion it is 0.029–0.041. Resampling the truth labels and
  interpolating the image leave a sub-voxel offset at the cavity border.
  - Both cut sets were measured on aligned, un-resampled cases: provisional 0.003–0.026, fit 0.001–0.019. So the
    first moved heart fails, however well it is registered.
  - Real patients are always resampled, so a development cut fitted on reader-passed patients would not have this
    problem.
- **Re-cut on the truth after motion** (post-hoc, reported only): p95 of the oracle's `rim_dark` over rigid,
  aniso3 and aniso6 is 0.037–0.050. At that cut, rigid-motion false flags fall from 100 % to **18 %**.
  - On Juliet's rows, which have the +5 % `phase` motion, that cut flags **100 % of `phase`**, 14–24 % of `rigid`
    and 5–14 % of `none`.
  - It also flags **100 % of `nonrigid`**. So `rim_dark` detects misregistration of the cavity border in general,
    not phase in particular. Juliet reached the same reading on #251.
- **The edge offset works as JA52 hoped.**
  - Median −1.01 to −1.03 mm on `phase_m5`, against −0.18 to −0.21 mm on rigid.
  - AUC 0.99–1.00 for the larger LIE cavity against rigid.
  - Flags 92 % of `phase_m5` and 0 % of rigid. `rim_dark` sees `phase_m5` 8–10 % of the time, as expected: it is
    blind to a larger cavity by construction.
- **Consequences:**
  - `load_provisional_qc_cuts` must not be used for the phase step as it stands (PS4-K3).
  - JA53's development fit stands (p95 over reader-passed development patients), because real data carry the
    resampling.
  - JA52's > 20 % development stop would fire at once if the provisional cuts were used.

### 1.5 Module parity (PS3-S7)

- **The shipped script, run unchanged, guard first, on the 20 usable hearts (120 cases):** **62 pass.**
  - E-V and P-G agree everywhere (max differences 0.0004 and 0.0015).
  - **E-D** differs by up to **0.191**, in all 58 failing cases.
  - Golf's run gives the same figures. My copy is `Kilo/r4/module_parity_replication.json`, and the canonical
    `bench_lie/module_parity.json` is Golf's.
- **The cause.** `scar0.JA30Constants.column_min_bins = 6`, while `bench.depth_extent` keeps columns with ≥ 4 depth
  bins.
- **K2 (`k2_parity_columns.py` → `k2_parity_columns4.json`):** with that constant set to 4 in-process (`src/`
  unchanged), **120 of 120 pass**, E-D max 0.0007.
- **Why CI missed it.** The CI parity test runs on the phantom only, whose wall is thick enough that no column falls
  between 4 and 6 bins.
- **The fix, PS4-K1:** the module follows the benchmark, as JA54 already made P-G's denominator do.

### 1.6 B-spline (JA53's arm)

- **On my rows (`rigid`, the harm check; started from the as-shipped final stage), the B-spline arm makes things
  worse:**
  - TRE median / p90 1.74 / 4.59 mm, against 0.27 / 1.14 for 4 mm rigid;
  - P-G specificity 0.40–0.88, against ≥ 0.97 on the chain.
- **On `nonrigid`** (Juliet's rows; Golf's B-spline set-up: from rigid4, 20 mm, 4 mm mask), it is worse than the
  chain:
  - TRE 2.13 / 3.81 mm, against the chain's 1.64 / 2.28;
  - P-J specificity 0.33–0.75 and P-G 0.45–0.80, against the chain's 0.71–0.83 and 0.74–0.90.
- **My reading:** B-spline stays out of the chain, and JA53's development arm should not be opened on its current
  trigger. A non-rigid residual is left to the reader check and the yield bar, as JA53 already says for the
  non-rigid case.

---

## 2. Item 2: JA51 4(b), the affine acceptance rule

### 2.1 The candidates (as pre-registered on #251)

Every rule includes 4(a), the sanity bound, and every NaN rejects. "Normalised" means divided by the cut.
- **JA51 as written:** no normalised value rises, and the maximum falls.
- **(a):** no rise on the three wall shares; the maximum (over all four values) falls.
- **(b):** the maximum falls, and no value that was ≤ its cut at rigid is > its cut at affine.
- **(c):** if |log det A| ≥ 0.03, keep affine; otherwise use JA51 as written.
- **(k), mine:** the maximum falls, and every value that rises ends ≤ its cut.

**The criterion:**
- choose the lowest pooled p90 final TRE over `rigid`, `scale`, `aniso3` and `aniso6` (Golf's `aniso` on his rows);
- a rule is ineligible if it keeps affine on more than 10 % of rigid cases where affine is worse by > 0.25 mm;
- the choice is made on the **fit** cuts.

### 2.2 Results

**My rows** (`scale` is not in them; Juliet's rows add it below). Pooled p90 is over rigid, aniso3 and aniso6:

| Rule | pooled p90, fit (prov) | rigid: affine kept when worse | aniso6: kept when better | aniso6 final TRE median / p90 | wrong decisions (fit) |
|---|---|---|---|---|---|
| JA51 as written | 2.49 (2.38) | 0 / 10 | 5 / 57 | 1.71 / 2.90 | 88 |
| (a) | 2.49 (2.38) | 0 / 10 | 5 / 57 | 1.71 / 2.90 | 88 |
| **(b)** | **2.26 (2.20)** | 0 / 10 | **19 / 57** | **1.47 / 2.90** | **73** |
| (c) | 3.02 (2.79), **ineligible** | **8 / 10** | 56 / 57 | 0.72 / 2.76 | 40 |
| (k) | 2.49 (2.38) | 0 / 10 | 9 / 57 | 1.69 / 2.90 | 82 |

**Juliet's 504 rows** (with `scale`; pooled over rigid, scale, aniso3, aniso6):

| Rule | pooled p90, fit (prov) | rigid: kept when worse | wrong decisions (fit) |
|---|---|---|---|
| JA51 as written | 2.40 (2.38) | 0 % | 152 |
| (a) | 2.40 (2.38) | 0 % | 152 |
| **(b)** | **2.35 (2.30)** | 0 % | 126 |
| (c) | 2.86 (2.78), **ineligible** | 61 % (59 % prov) | 78 |
| (k) | 2.38 (2.36) | 0 % | 141 |

**Golf's canonical rows** (pooled over rigid, scale and Golf's `aniso` (3 / 3 / 6 %, random sign), as
pre-registered):

| Rule | pooled p90, fit (prov) | rigid: kept when worse | wrong decisions (fit) |
|---|---|---|---|
| JA51 as written | 3.53 (3.53) | 0 % | 109 |
| (a) | 3.53 (3.53) | 0 % | 109 |
| **(b)** | **2.98 (2.98)** | 0 % | **75** |
| (c) | 3.46 (3.46), **ineligible** | 61 % (59 % prov) | 69 |
| (k) | 3.06 (3.06) | 0 % | 86 |

**The choice is (b) on all three row sets, at both cut sets.** On Golf's `aniso`, (b) halves the chain's median
TRE (1.44 against JA51's 2.80 mm).

- **(a) = JA51 on every case here.** `rim_dark` is not what blocks affine on these hearts. The wall shares are.
- **(b) is the best eligible rule at both cut sets,** and it never keeps a worse affine on rigid motion. It still
  rejects 38 of 57 aniso6 affines that are better by > 0.25 mm.
- **(c) is what the scale cases want, but not the rigid ones.**
  - Under rigid motion the 4 mm affine often finds a spurious |log det| ≥ 0.03, so (c) keeps it 8 times in 10 when
    it is worse (rigid p90 3.68 mm).
  - That is E10's overshoot, and why (c) fails eligibility. It would also strike P-G (§1.3).
  - On `phase_m5` it keeps a worse affine 8–9 times. Registration cannot fix phase, and (c) tries.
- **(k) adds nothing over JA51 here,** so I withdraw it. Correcting a misregistration does not, on these hearts,
  push a value back up to its aligned level while staying under its cut. That was the case (k) was written for
  (#243's phantom).
- **The phantom (K1, `k1_phantom_rules.py`)** uses the shipped tests' static chest with their tight cuts (1.2 × the
  aligned values). Out of 9 correct scale fixes:

  | Rule | correct fixes kept |
  |---|---|
  | JA51 as written | 0 |
  | (a) | 0 |
  | (b) | 5 |
  | (k) | 4 |
  | (c) | 9 |

  None keeps the one worse affine. The phantom's tight cuts make every rule except (c) fragile, so the strict
  xfail would pass under (b) on some seeds and not on others.

### 2.3 Proposal

1. **JA51 4(b) becomes (b):** the normalised maximum falls, and no value newly crosses its cut, plus 4(a).
2. **JA51 step 5 (the 10 mm fallback) stays as written.** On Juliet's full motion set, "only if it passes" makes the
   p90 worse on `nonrigid` (2.23 → 2.75 mm), `scale` (2.66 → 2.88), `aniso3` (1.24 → 1.47) and `none` (0.27 →
   0.41). It is better only on `phase` (3.68 → 0.97 mm), and phase patients are routed out (§4). So instead, **a
   patient routed to the phase-unmatched stratum is graded on its last 4 mm stage, never on the fallback**
   (PS4-K4).
3. **The scale gap stays open, and is said so.** No truth-free QC rule here keeps more than a third of the affines
   that fix a 6 % stretch. The reader check is what catches it, so JA51's reader check on every patient stays.
4. **PS3-S3's test becomes:**
   - a rigid 4 mm shift rejects affine;
   - the 3 % scale keeps it on at least the seeds where (b) does in K1, at the tests' own tight cuts.

   Under those cuts (b) is seed-dependent (5 of 9 in K1), so the test should fix its seeds. Pinning a phantom test
   on a rule the cuts make fragile is the engineer's call; I say so rather than claim it passes.

---

## 3. Item 3: the power re-run

`Kilo/r4/p3_power_table.py` → `p3_power_table.json`. It uses the shipped `janusm.scar.power` / `scoring` (SCAR_VERSION
1.1.0) with JA55's split accounting and the yield bar.

- **Cells (24):** failure 0 / 2 / 5 %; clustering weak (τ 0.7) / strong (1.2); enrichment 50 / 70 %; infarct size
  Golf (1 + Poisson(3), 4.0 scarred segments per scar patient) / Kilo (3.25; entered as Golf's cohort with
  λ = 2.25, as `seal_size` does).
- **Everything else** is the engine's JA32 base: q 0.25, specificity 0.98, `bin_tau` 1.0, Golf's sensitivity by bin.
- **Runs:** N grid 100–240 in steps of 20; two independent seeds of 2000 simulations each (boot 400).
- **The seal** is `seal_size`'s rule: max(120; the 270-segment N; the first N from which power stays ≥ 0.80),
  capped at 240.

**Seal (claim 1), weak clustering:**

| Failure | 50 %, Golf | 50 %, Kilo | 70 %, Golf | 70 %, Kilo |
|---|---|---|---|---|
| 0 % | 136 (floor) | 167 (floor) | 120 (floor) | 120 (floor) |
| **2 %** | **180** | **220** | **140** | **160** |
| 5 % | 240 (cap) | 240 (cap) | 240 (cap) | 240 (cap) |

**Strong clustering:**

| Failure | 50 %, Golf | 50 %, Kilo | 70 %, Golf | 70 %, Kilo |
|---|---|---|---|---|
| 0 % | 220 / 240 (seeds differ) | 240 (cap) | 160 | 180 |
| 2 % | 240 (cap) | 240 (cap) | 240 (cap) | 240 (cap) |
| 5 % | 240 (cap) | 240 (cap) | 240 (cap) | 240 (cap) |

**Stability.**
- The two 2000-simulation seeds agree in 23 of 24 cells.
- At 300 simulations (10 seeds, 2 % / weak / Golf), N moves by one grid step: 180–200 at 50 % and 120–140 at 70 %.
  That is what the #248 engineer saw.

**Why the ruling said ≈ 160 / ≈ 200.** Juliet E9 sized on a grid of 120, 160, 200, 240 and 320, and its curves
cross 0.80 between grid points:
- at 70 %: 0.748 at N = 120, 0.865 at 160;
- at 50 %: 0.733 at 160, 0.848 at 200.

The first grid N past 0.80 is therefore 160 or 200. On a 20-patient grid the same model crosses at 140 and 180.
Kilo's smaller infarcts add one step.

**Claim 2 never binds** at anchor 0.70 and the base extent error. In every cell, claim-2 power equals claim-1 power:
whenever presence passes, the Kim-bin lower bound clears 0.60. So JA57's "claim 2 is powered if development shows it
can be" changes nothing at q = 0.25. It binds only if development's extent error is worse.

**Reproductions:**
- **Juliet E9:** all 80 split rows at 1000 simulations; max |z| 2.38 (pooled two-proportion z), 2 of 80 above 2.
  Both are 10 %-failure cells recorded at 0.000 and 0.005.
- **Golf E10:** `segments_needed` medians exact or within 1 (166 / 119 / 135 / 97 against 167 / 119 / 135 / 97), and
  p90s within 2.

**What it changes (JA57's planning figures):**
- **≈ 40 development + ≈ 140 seal at 70 %** (Golf's infarct size) or ≈ 160 (Kilo's), at 2 % failure and weak
  clustering. At 50 %: ≈ 180–220.
- The cap still binds under strong clustering at 2 %, and at 5 % failure.
- **Recommendation:** plan on **160 at 70 %**, Kilo's smaller infarcts being the conservative one. The 240 cap
  stands.

---

## 4. Item 4: how the phase-unmatched stratum is scored

**Proposal: a JA27 stratum, graded and reported, outside the primary claim and outside the yield bar.** The
selection risk is closed by reader confirmation and a reported comparison. Neither JA55's split nor "excluded with
yield" fits a property of the data that the method did not cause.

### 4.1 What the shipped code does now

- `registration.status_from_checks` returns `phase suspect` whenever the phase step flags, whatever the reader says.
- `scar0` refuses to grade any status outside `FINAL_STATUSES` (passed, re-registered, not graded). So a
  phase-suspect patient produces **no CT bins at all**.
- `scoring` already has a `phase_unmatched` stratum in `STRATA`, and it is in `EXCLUDED_FROM_PRIMARY`. Nothing
  can fill it, because no phase-suspect patient reaches scoring.
- JA52 routes a flagged patient with DICOM-matched phase to the stratum **only if the reader also marks** "cavity
  size differs (phase)". The code has no input for the DICOM phase source or the reader's mark. So a flagged,
  DICOM-matched patient whose reader does *not* confirm is left in limbo: not graded, not a failure, not in the
  stratum.

### 4.2 The rule

1. **Routing (JA52 and JA59, made executable).** A patient goes to the `phase_unmatched` stratum if any of these
   holds:
   - intake: the DICOM phase fields show different phases, and no reconstruction at the LIE's phase exists
     (JA59);
   - DICOM-matched phase, a JA52 flag, **and** the reader marks "cavity size differs (phase)";
   - phase inferred from text (JA59) and a JA52 flag.

   **A flag on a DICOM-matched patient that the reader does not confirm is a false flag.** The patient follows
   its reader check like any other (passed, re-registered, not graded) and stays in the primary analysis. The flag
   is logged.
2. **Grading.** A stratum patient is graded on its last 4 mm stage (rigid, or affine if kept), **never on the 10 mm
   fallback**: on a phase change the fallback replaces a 0.26 mm rigid result with a 3–4 mm one in about half of
   Juliet's `phase` cases (§1.4). It is never re-registered (JA52). It produces CT bins, and `scar0` labels it
   `phase_unmatched`.
3. **Scoring.**
   - **Primary claims (JA56):** the stratum is excluded, as `scoring` already does.
   - **Yield (JA55):** it is **not** in the yield numerator or denominator. Yield measures registration failure, and
     JA52 already says a phase-suspect patient is not one.
   - **Reported:** the stratum's own sensitivity, specificity and Kim-bin agreement, under the same JA55
     accounting; its size; and the LGE-positive share in the stratum against the primary set.
4. **Guards.**
   - JA52's development stop stands: a phase-unmatched share over 20 % is reported to the lead before any seal read.
   - **New, on the seal:** if the stratum holds more than 10 % of seal patients, or its LGE-positive share differs
     from the primary's by more than 15 points, the primary endpoints are **also** reported with the stratum
     included under JA55 split accounting. This is a reported sensitivity analysis, never deciding. It shows
     whether excluding the stratum moved the claim.

### 4.3 Why not the other two

- **JA55 split** (LGE-positive segments missed, LGE-negative out of specificity) charges the method for a scan that
  was acquired at a different phase. It contradicts JA52's "not a registration failure".
- **Including them in the primary would also be wrong.** Graded through the chain, a larger LIE cavity
  (`phase_m5`, my rows, fit cuts) puts blood inside the carried wall. Specificity then falls badly, while on the
  true borders the same cases score ≥ 0.93:

  | Rule | specificity on the chain | on the true borders |
  |---|---|---|
  | P-J | 0.23–0.56 | ≥ 0.93 |
  | P-G | 0.55–0.94 | ≥ 0.99 |

  So these patients must be outside the claim, not inside it under some accounting.
- **Excluded, with yield** puts an acquisition property inside a deciding bar. At a 5 % phase-unmatched rate, half
  of the 0.10 yield budget would be spent before any registration fails. Yield then stops measuring what JA55
  built it for.
- **The stratum** is what JA27 and JA59 already name, and `scoring` already implements it. What's missing is the
  route in and the grading (spec PS4-K4).

### 4.4 The risk, measured

- **The edge offset:** 0 % false flags on rigid motion (no phase change) and 92 % detection of `phase_m5`, at the
  provisional 0.6 mm (§1.4).
- **`rim_dark` false flags:**
  - **100 %** on rigid motion at either benchmark cut set: the cuts were fitted on un-resampled aligned cases
    (§1.4);
  - still **18 %** at a cut referenced to the true geometry after motion;
  - 100 % detection of `phase` (+5 %), but also 100 % of `nonrigid` misregistration (Juliet's rows, §1.4).

So a `rim_dark` flag alone is not reliable enough to route an *inferred*-phase patient out without a reader:
1. **For phase inferred from text, only the edge-offset flag routes alone.** A `rim_dark` flag needs the reader's
   "cavity size differs (phase)" mark, as for DICOM-matched patients.
2. This tightens JA52's "with phase inferred from text, it goes there on the flag alone". The development fit of
   `rim_dark`'s phase cut (JA53) can relax it again: if development shows `rim_dark`'s false-flag rate on
   reader-passed, phase-matched patients ≤ 5 %, the flag alone routes again.

---

## 5. Item 5: path B against path A, for the lead (Round 3 §8, updated)

| | Path A, `jm/rest-ccta` | Path B, `jm/paired-scar` (after Round 4) |
|---|---|---|
| Assumes | no reference for scar or ischaemia | the lead obtains a paired CCTA + same-session LIE + CMR LGE cohort (data requirements only, D31) |
| Stage A | built and calibrated; bias guard 0.3 mm (JA71) | **identical code** (JA50) |
| Scar rule | — | **P-J or P-G, both surviving the shipped chain**; P-K struck; E-V or E-D (3 SD), once the module's E-D column rule matches the benchmark (PS4-K1) |
| Registration | — | R0 → QC gate → 4 mm rigid (0.27 mm median after a 4 mm shift) → affine only if sane and (b) holds → 10 mm fallback as JA51 step 5 → reader check on every patient |
| Phase | — | the edge offset finds a larger LIE cavity (AUC ≥ 0.99). `rim_dark` needs development-fitted cuts: the benchmark's flag every moved heart. Phase-unmatched patients form a graded, reported stratum outside the claim |
| What passing gives | specificity-calibrated flags | **presence** validated on sensitivity, specificity and yield; the **Kim bin** if CT grades as well as the readers (not binding at the base extent error) |
| Cohort | none | 40 development + **≈ 140–160 seal at 70 %** (≈ 180–220 at 50 %), at 2 % failure; never more than 240 |
| Reader time | none | ≈ 200 × 2 CMR reads + adjudication + a registration check per patient (to be replaced by measured time) |
| Committed compute | ≈ 15 GPU-h | the same + ≈ 3 GPU-h once the cohort exists; scar on CPU |
| Main risk | flags with no measured sensitivity | the cohort never arrives; a non-graded rate ≥ 5 % (the seal then hits the cap and power falls to ≈ 0.4); scale misregistration that QC cannot see |
| If the cohort never arrives | — | path B reduces to path A exactly |

---

## 6. What must ship (`role:swe` specs; code on `jm/paired-scar`, nothing in `src/` changed here)

Each item is one issue for the judge's shipping list. Tests run on phantoms in CI. Real hearts are used only in
offline scripts that call the guard first.

- **PS4-K1 — E-D's column rule follows the benchmark** (`scar0.py`; JA54; PS3-S7).
  - **Wrong:** `JA30Constants.column_min_bins = 6`. The benchmark that decided the menu (`bench.depth_extent`)
    keeps columns spanning ≥ 4 depth bins. `module_parity.json` passes 62 of 120 real-heart cases, failing on E-D
    only (max difference 0.191). E-V and P-G agree to ≤ 0.0015.
  - **Correct:** `column_min_bins = 4`. With that one change, all 120 cases pass, E-D max difference 0.0007 (K2,
    `k2_parity_columns4.json`; Golf and Juliet found the same on #251).
  - **Test:**
    - the CI parity test gains a thin-wall phantom (wall ≤ 6 voxels deep in at least one segment), where 4 and 6
      give different E-D. It must pass with 4;
    - the offline `module_parity.py` summary is re-committed with `n_pass == n_cases`.
- **PS4-K2 — The affine acceptance rule** (`registration.py`; JA51 step 4; #243).
  - **Wrong:** JA51 4(b) as written rejects most correct affines (#243). On my rows it keeps 5 of 57 affines that
    fix a 6 % stretch.
  - **Correct:** rule (b): affine is kept iff 4(a) holds, the normalised maximum falls, and no value that was ≤ its
    cut at rigid is > its cut at affine. Any NaN rejects.
  - **Test:**
    - unit cases for each clause;
    - the 4 mm rigid shift rejects affine;
    - PS3-S3's 3 % scale: under the tests' tight cuts, (b) keeps affine on 5 of 9 seeded cases (K1). So the test
      fixes its seeds to ones where (b) keeps it, or the engineer loosens the phantom's cuts toward a JA53-style
      p95. The strict xfail is lifted only with that choice made and written down (§2.3 item 4).
- **PS4-K3 — Provisional cuts measured on the shipped QC** (`registration.load_provisional_qc_cuts`; JA53).
  - **Wrong:** the loader reads `bench_lie/scores.json` `qc_cuts`. Those were measured with the benchmark's QC
    definitions: an erosion rim, and the blood median inside a 2-iteration erosion. The module's are a 2 mm
    Euclidean rim and a ≥ 2 mm Euclidean core. More important, they were fitted on un-resampled aligned cases. On
    real-like moved hearts, the JA52 `rim_dark` flag then fires on 100 % of correctly registered patients (§1.4).
  - **Correct:**
    - provisional cuts are p95 of the **shipped** QC on the **true geometry after motion** (benchmark v3 oracle
      rows, non-phase motions), keyed by blood and CNR;
    - the loader refuses a file that does not declare `qc_definitions: "janusm.scar.registration <SCAR_VERSION>"`;
    - the phase step does not run on provisional cuts. Until JA53's development fit exists, `phase_step` logs its
      values and flags only on the edge offset.
  - **Test:** loading v2's `scores.json` raises; a phantom moved 4 mm and registered exactly is not flagged by
    `rim_dark` at the new provisional cuts.
- **PS4-K4 — The phase-unmatched route and its grading** (`registration.py`, `scar0.py`, `scoring.py`; JA52, JA59;
  §4 here).
  - **Wrong:** `status_from_checks` makes every flagged patient `phase suspect`, whatever the reader says. `scar0`
    refuses to grade it. `scoring`'s `phase_unmatched` stratum can never be filled. A flagged, DICOM-matched patient
    whose reader does not confirm is in limbo.
  - **Correct:**
    - `register_lie` (or the status function) takes `phase_source ∈ {"dicom_matched", "dicom_unmatched",
      "inferred"}` and the reader's "cavity size differs (phase)" mark;
    - `phase suspect` is a final status only when §4.2's routing holds; otherwise a flag is logged and the reader
      check decides;
    - `scar0` grades a `phase suspect` patient on its last 4 mm stage, not the 10 mm fallback. `for_scoring` returns its bins with
      `strata={"phase_unmatched"}`;
    - `scoring` reports the stratum (§4.2 item 3) and the guarded sensitivity analysis (§4.2 item 4);
    - `failure_rate` and the yield ignore the stratum, as they already ignore `phase suspect`.
  - **Test:** one synthetic patient per routing row; the limbo case (flagged, DICOM-matched, not confirmed) ends
    `passed`; the stratum appears in `score()`'s output and not in the primary counts.

---

## 7. Files

`experiments/JanusM/Kilo/r4/`:

| File | What |
|---|---|
| `run_shipped.py`, `bench_kilo_r4.py` → `results_kilo_r4.jsonl.gz` | The replication: the shipped chain with every stage forced, plus oracle QC and one live check per heart |
| `score_shipped.py` → `scores_kilo_r4.json` | Kilo's pre-registered scoring: strike, the five affine rules × two cut sets, phase flags |
| `golf_rows.py` → `scores_kilo_on_golf_v3.json`, `scores_kilo_on_juliet_v3.json` | The same scoring on Golf's canonical v3 rows (370fbbd) and on Juliet's replication rows (`main_juliet`) |
| `k1_phantom_rules.py` → `k1_phantom_rules.json` | The affine rules on the shipped tests' phantom |
| `k2_parity_columns.py` → `k2_parity_columns4.json` | `module_parity` with `column_min_bins = 4` (in-process) |
| `module_parity_replication.json` | `bench_lie/module_parity.py` run unchanged (replicates Golf's canonical file) |
| `p3_power_table.py` → `p3_power_table.json` | Item 3 |

Reproduce (CPU; hearts fetched by `bench_lie/fetch.py`, guard first):
`PYTHONPATH=src python experiments/JanusM/Kilo/r4/run_shipped.py DATA --procs 4` (about 4–6 min per case on one core),
then `score_shipped.py`; `p3_power_table.py --sims 2000` (about 3 core-hours).

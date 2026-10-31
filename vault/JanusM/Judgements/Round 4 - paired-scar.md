---
aliases: [Janus-M Round 4 paired-scar]
tags: [janus-m, plans, judgement, round4, path-paired-scar, myocardium, scar, lie, lge, registration, power]
author: Janus-M Round 4 judge (path jm/paired-scar)
round: 4
path: jm/paired-scar
status: ruling
updated: 2026-10-31
issue: christianGRogers/Asclepius#251
---

# Janus-M Round 4, path `jm/paired-scar`: the judgement

**Ruling in one paragraph.** Round 4 ran the shipped code (SCAR_VERSION 1.1.0) through the benchmark that wrote it.
- **The scar rules hold.** P-G survives JA51's chain as shipped, so JA54's conditional reinstatement becomes final:
  the menu is **P-J then P-G for presence, E-V or E-D for extent**, and P-K stays struck. The module's E-D must keep
  columns of ≥ 4 depth bins, as the benchmark does (JA80).
- **The chain needs four repairs:**
  1. **The affine rule becomes Golf's (g)** (JA81). It is sane, it does not raise the worst normalised QC value,
     and it either passes QC or shows a scale. It wins the pre-registered choice under Golf's criterion and under
     Kilo's, and keeps no worse affine on rigid motion.
  2. **A phase flag stops the 10 mm fallback** (JA82).
  3. **Provisional QC cuts come from registered cases, not aligned ones** (JA83).
  4. **The edge offset becomes the phase flag that routes**; `rim_dark` becomes advisory (JA84).
- **Phase-unmatched patients** go to the JA27 stratum only on confirmation. An unconfirmed flag that routes anyway
  is charged to yield (JA85).
- **Seal size.** The planning figure stays **≈ 40 + 160 at 70 %**, and becomes ≈ 200 at 50 % (range 180–220).
  `seal_size` must state the power it delivers. When the 240 cap binds, no seal patient is graded until the lead has
  seen that power (JA86, LQ40).

**Base:** the path plan stays **[[Kilo v2]] with JA25–JA36 and JA50–JA59**, now amended by **JA80–JA87**. **Golf v4 and
Kilo v4 tie at 18/20**; Juliet v4 scores 17. **No fork** (§6). **No Round 5 is needed on this path** (§7). It now waits only on the
lead: LQ1 (a paired cohort and access to it) and Job JM-0.

**Rules kept.** The judge ran no experiment, ran no registration, opened no image, downloaded nothing and read no
held-out case or twin list. The checks below read committed JSON and code on `jm/paired-scar` at `857f5af` and issues
#251, #243 and #179. Where a figure existed only in a note, the judge re-tabulated it from the committed v3 rows with
the committed `score_v3.py` decision functions. That is arithmetic on logged stages, with no new arm, motion or
stage; it is marked "judge's re-tabulation" each time it is used. No case id is reproduced here.

---

## 1. What was checked

### 1.1 The canonical benchmark (`experiments/JanusM/bench_lie/`, v3)

**Which run decides.** All three advocates launched a v3 run within ten minutes, because their claims crossed. By
agreement on #251 (Juliet 19:33, Kilo 19:44, Golf 07:07 UTC), **Golf's run is the canonical v3**: `run_v3.py`,
`score_v3.py`, `results_v3.jsonl.gz`, `scores_v3.json`. Kilo's and Juliet's runs are replications, kept in their own
`r4/` folders. Kilo's and Juliet's pre-registrations name Golf's `chain` arm as the deciding arm for the strike. The
judge holds them to that.

**Strike under #179's rules** (CNR 5; motion none or rigid; every blood level; JA51 literal; `scores_v3.json` →
`strike`):

| Rule | Struck | Min sensitivity | Min specificity | Min scar-free specificity | Max spill | PM's note |
|---|---|---|---|---|---|---|
| P-K | **yes** | 0.977 | 0.885 | **0.006** | 0.074 | ✓ |
| P-J (τ re-fitted under the chain) | no | 0.888 | 0.958 | 0.972 | 0.125 | ✓ |
| **P-G** | **no** | **0.915** | **0.985** | **0.989** | 0.012 | ✓ |
| E-V / E-D (exact bin, scar-on-both, P-J, volume / depth truth) | no | 0.924 / 0.960; 0.906 / 0.943 | | | | ✓ |

- **All three scorers agree.** Kilo's `scores_kilo_on_golf_v3.json` gives the same verdicts and the same minima.
  Juliet's replication (`scores_v3_juliet.json`) gives P-G 0.915 / 0.985 / 0.989 and P-J 0.865 (sensitivity) on her own
  rows.
- **Determinism.** Kilo reports identical stage TREs on the 96 cases his rows share with Golf's. The judge did not
  repeat that row-by-row match. The chain TREs Golf and Juliet report for `rigid`, `scale`, `phase` and `nonrigid` agree
  to the third decimal, which is consistent with it.
- **The replay is the module.** Golf's `chain_parity.json` (9 / 9) and Juliet's `replay_check.json` (16 / 16) run
  `register_lie` end to end and land on the assembled chain's final stage with identical TRE. Kilo: 11 / 11.
- **One ungradable arm** in 518 cases (a diverged B-spline arm, CNR 3). It is disclosed on #251 and touches no striking
  condition.

### 1.2 Module parity (PS3-S7)

| File | n pass / cases | E-V max \|Δ\| | P-G max \|Δ\| | E-D max \|Δ\| |
|---|---|---|---|---|
| `bench_lie/module_parity.json` (as shipped) | **62 / 120** | 0.0004 | 0.0015 | **0.191** |
| `Kilo/r4/k2_parity_columns4.json` (`column_min_bins = 4`, in-process) | **120 / 120** | 0.0004 | 0.0015 | 0.0007 |

- **The cause is confirmed in code.** `scar0.JA30Constants.column_min_bins = 6` (`scar0.py:111`, used at line 152).
  The benchmark keeps E-D columns of ≥ 4 depth bins.
- JA54's E-D verdict was reached at ≥ 4. As JA54 did for P-G's denominator, **the module follows the benchmark**
  (JA80).

### 1.3 Registration claims (`scores_v3.json` → `registration`, `phase`; judge's re-tabulation where marked)

| Claim | Source | Re-read | Match |
|---|---|---|---|
| The provisional cuts gate nothing: rigid passes QC on 0 / 63 rigid-motion cases (Golf) | `qc_cuts` = p95 of R0 on aligned `none`; `rim_dark` cut 0.001–0.056 | as stated | ✓ |
| `rim_dark` flags every correctly registered moved heart (Kilo PS4-K3; Juliet) | `phase["literal|rigid"]`: 74 / 74 flagged, all by `rim_dark` | ✓ | ✓ |
| Edge offset: 1 / 148 false flags on phase-matched cases; 70 / 74 larger cavity; 58 / 74 smaller (Golf) | `phase` none 0 / 74, rigid 1 / 74; `phase_neg` 70; `phase` 58 | ✓ | ✓ |
| Phase AUCs | `phase_auc`: edge offset 0.994 (larger cavity), `rim_dark` 0.999 (smaller), `rim_dark` 0.024 (larger) | ✓ | ✓ |
| The fallback hurts phase (Golf, Juliet) | judge's re-tabulation, chain (g), CNR 5, `phase`: with the shipped fallback 1.20 / 3.68 mm (median / p90); fallback only on a QC pass 0.26 / 0.97 | ✓ | ✓ |
| The fallback helps whole-image motion (Kilo) | same, `nonrigid`: 1.64 / 2.23 against 1.84 / 2.87 | ✓ | ✓ |
| The affine overshoots with no scale (Juliet) | `registration`: affine4 p90 1.55 (none) and 2.26 (rigid) against rigid4 0.55 / 1.13 | ✓ | ✓ |
| B-spline fails Golf's rule 4 | nonrigid 2.06 / 4.18 against the chain's 1.65 / 2.26; it raises rigid's median by 1.9 mm | ✓ | ✓ |
| Affine's sanity bound fails on 11 / 74 true 3–6 % scales (Golf) | `affine_sane` counts | ✓ | ✓; an optimiser issue (PS4-S7) |

### 1.4 The affine rule (#251 item 2): each advocate held to its own pre-registered criterion

**Golf** (pre-registered 2026-10-30 18:56). The lowest pooled chain p90 over `scale`, `aniso`, `phase` and
`phase_neg`, among rules no worse than never-affine (+0.05 mm) on `none` and `rigid` and causing no new strike. Ties
within 0.02 mm go to fewer clauses. `scores_v3.json` → `affine_rule`:

| Rule | Pooled p90 | Qualifies |
|---|---|---|
| literal / (a) | 3.761 | yes |
| (b) | 3.463 | yes |
| (c) at 0.02 | 3.679 | **no**: rigid p90 up to 3.47 against 1.12; new strikes P-J and P-G |
| **(g)** | **3.428** | yes → **pick** |
| always | 3.679 | no |
| never | 4.072 | reference |

- **(g) beats (b) by 0.035 mm, outside the 0.02 tie margin.** Golf's criterion picks (g) by its own rule.
- (g) is Golf's own rule, and the margin is thin. Golf says both, and the judge weighs the other criteria for that
  reason.

**Kilo** (pre-registered 18:56 and ≈ 19:04). The lowest pooled p90 over `rigid`, `scale` and `aniso`, at the fit
cuts. A rule is ineligible if it keeps a worse affine (by > 0.25 mm) on > 10 % of such rigid cases.
- **On Kilo's candidate set, (b) wins on all three row sets and at both cut sets.** On Golf's rows: (b) 2.982, JA51
  3.528, (k) 3.055; (c) at 0.03 is ineligible, keeping 61 % of worse affines (`scores_kilo_on_golf_v3.json` →
  `item2`). Confirmed.
- **(g) was not in Kilo's set.** Golf scored it under Kilo's criterion in the note, with no committed script or JSON
  behind the number. **The judge re-tabulated it from the committed rows and code** (CNR 5, Golf's cuts):

  | Rule | Pooled p90 (median) | Worse affines kept on rigid | Helpful affines kept on scale + aniso |
  |---|---|---|---|
  | literal | 3.528 (1.737) | 0 / 23 | 16 / 115 |
  | (b) | 2.982 (1.115) | 0 / 23 | 49 / 115 |
  | (c) at 0.02 | 3.460 (0.505) | **17 / 23** | 107 / 115 |
  | **(g)** | **2.908** (0.928) | **0 / 23** | **53 / 115** |
  | never / always | 4.112 / 3.460 | 0 / 23; 23 / 23 | 0; 107 / 115 |

  Golf's 2.91, 2.98, 3.46 and 3.53 reproduce exactly. **Under Kilo's own criterion, (g) leads and is eligible.**

**Juliet** (pre-registered 19:00). The lowest pooled p90 of the rigid-or-affine decision over `rigid`, `scale`,
`aniso3` and `aniso6` (`aniso` on Golf's rows); ties go to fewer keeps.
- **On her rows the pick is (c)**: 1.996 mm, tied with S (sanity only), against L 2.377 and (b) 2.303. Confirmed in
  her note's table.
- **On Golf's rows, under her pre-registered mapping, the pick is also (c).** Judge's re-tabulation: (c) and always
  2.31, (g) 2.88, (b) 2.91, literal 3.28, never 3.44.
- **Her criterion has no harm screen,** and (c) is what it buys. (c) keeps 17 of 23 worse affines on rigid motion and
  raises the rigid p90 from 1.14 to 1.99 mm (Juliet's own number). It re-strikes P-G under Golf's constraint, and
  under Kilo's scorer at the provisional cuts (specificity 0.929).
- Juliet reports this plainly. She then proposes (c) at **0.05**, a threshold from a sweep run after the results
  (disclosed), and **suspends affine** until the overshoot is fixed. Neither is her pre-registered pick.

**What the evidence supports: (g).**
- It is the pick under two of the three pre-registered criteria (Golf's, and Kilo's once (g) is admitted).
- It keeps no worse affine on rigid motion, and keeps the most helpful affines of any safe rule (53 / 115).
- It is the only safe rule that keeps the correct affine on the PS3-S3 phantom. `Golf/r4/ruleg_ps3_s3.json` shows (b)
  rejects it at the test's seed. Kilo's K1 finds (b) seed-dependent (5 / 9) under the test's tight cuts.
- (b) is a close second and also safe. Choosing (b) would not be wrong; it is narrowly worse on every measure here.
- (c) at any threshold rests on the log-det alone, and the overshoot's log-det reaches 0.02 on rigid motion.
- Suspending affine (Juliet) gives up scale correction the safe rules already deliver: on `aniso` the chain's median
  falls from 2.79 (literal, ≈ never) to 1.04 mm under (g).

**The open scale gap is real and stays open.** No safe QC rule keeps more than about half of the helpful affines. QC
cannot see TRE (Juliet §2.1). JA51's reader check on every patient carries the rest.

### 1.5 The PS3-S3 test's sign (Golf)

**Golf is right.**
- `Transform` (`registration.py:475`) maps fixed LIE points to the moving first pass: `p_moving = matrix (p_fixed −
  centre) + …`.
- `chest.scale(1.03)` (`tests/janusm_synth.py:218`) enlarges the LIE heart by 3 %.
- The correct matrix is therefore ≈ I / 1.03, with log det ≈ −0.089. Golf measured −0.081.
- The test's last line, `log_det > 0.03` (`test_janusm_scar_registration.py:268`), asserts the wrong sign. Under rule
  (g) every other assertion in the test passes (`ruleg_ps3_s3.json`).

### 1.6 Power (#251 item 3; JA57)

| Claim | Source | Re-read | Match |
|---|---|---|---|
| Kilo: 2 % failure, weak clustering: 140 / 160 (70 %, Golf / Kilo infarct size), 180 / 220 (50 %); 2 × 2 000 sims; 23 / 24 cells stable | `Kilo/r4/p3_power_table.json` | as stated; 50 % / Golf seed A crosses at exactly 0.800 at N 180 | ✓ |
| Golf: interpolated N80 128 (119–137), 145 (138–152) at 70 %; 182 (172–191), 196 (189–208) at 50 % | `Golf/r4/power_r4_table.json` | as stated | ✓ |
| Juliet: 140 / 160 (70 %), 200 / 220 (50 %); halves disagree by one step in 6 / 24 cells | `Juliet/r4/e11_power_r4.json` | as stated; E9 reproduction max \|z\| 2.43 | ✓ |
| Power at the cap, 5 % failure or strong clustering: 0.17–0.67 (Juliet) | Kilo's table: 2 % strong 0.51–0.68; 5 % weak 0.44–0.60; 5 % strong 0.17–0.22 | ✓ |
| Golf: the seal tolerates ≈ 3 % failure at 240 (weak, 70 %) | `power_fail_tolerance.json`: 0.86–0.87 at 3 %, 0.72–0.76 at 4 % | ✓ |
| Claim 2 never binds at q = 0.25 | Kilo: claim-2 power = claim-1 power in every cell; Golf, Juliet the same | ✓ |

**Reading.** The three tables agree within one 20-patient grid step, which is the Monte-Carlo noise of a flat curve
(≈ +0.02–0.04 power per 20 patients). Kilo's "grid artefact" explanation of Round 3's 160 / 200 holds for Golf's
infarct size. With Kilo's smaller infarcts, 160 at 70 % is the grid value anyway. **`seal_size`'s default of 400 sims
is too few to place N** (PS4-S8).

### 1.7 Phase-unmatched patients (#251 item 4)

- **The code today.** `FINAL_STATUSES = (PASSED, REREGISTERED, NOT_GRADED)` (`scar/__init__.py:42`). `scar0` refuses any
  other status (`scar0.py:238`). `status_from_checks` returns `phase suspect` on any flag, whatever the reader says.
  `scoring.STRATA` and `EXCLUDED_FROM_PRIMARY` already hold `phase_unmatched`. **Kilo's "limbo" reading is correct:**
  nothing can reach the stratum, and a flagged DICOM-matched patient whose reader does not confirm has no status.
- **What a flag means on the benchmark.**
  - `rim_dark` at the shipped cut flags misregistration in general: 74 / 74 `rigid` and 74 / 74 `nonrigid`.
  - The edge offset is specific: 1 / 148 phase-matched, 10 / 74 `nonrigid`.
- **A phase-mismatched heart cannot be scored in the primary.** On `phase_neg` (larger LIE cavity), P-J specificity
  on the chain is 0.21–0.54 (`phase_stratum_presence`). Sensitivity there stays 0.94–0.99, so charging these patients
  as JA55 failures would charge the method for a reconstruction fact.

### 1.8 Held-out handling

- The guard runs first, on the whole list and then per heart, in every script that opens a heart. The judge read the
  call sites in `bench_lie/fetch.py`, `bench.load_heart`, `run_v3.py`, `module_parity.py`, `Kilo/r4/run_shipped.py` and
  `Juliet/r4/run_v3_juliet.py`.
- No candidate note names a held-out subject or a twin match. The committed JSON names only the public benchmark hearts
  already in the repository; this ruling reproduces none.
- The judge opened, listed and compared no held-out case or twin list.

---

## 2. Scorecards

Scale 1–5:
- **(a)** reasoning;
- **(b)** evidence;
- **(c)** fit to path B and to obtainable data;
- **(d)** risk and cost (5 = low risk, cheap).

### Golf v4: the canonical run, one affine rule, and what failure rate the seal can afford

| | Score | Why |
|---|---|---|
| (a) Reasoning | **5** | Ran the canonical benchmark to a pre-registration and scored its own rule under a rival's criterion. Found the PS3-S3 sign error (confirmed in code, §1.5). Showed why the provisional cuts gate nothing, and turned the cap into a stated-power decision rather than a silent underpowered seal. Disclosed the CNR cut made after a look, and the post-hoc arms |
| (b) Evidence | **4** | 518 cases; chain parity 9 / 9; every committed number re-reads. Deducted: the deciding cross-criterion number (2.91) was in the note only, with no committed script (the judge reproduced it, §1.4); §3.2's table pools CNR 3 with CNR 5, so its `phase` row (0.88 / 3.75) differs from the CNR 5 figure (1.20 / 3.68); the JA53-style cuts were added after an interim look |
| (c) Fit | **5** | Registered-patient cuts, edge-offset routing, and flag-only routing charged to yield all fit JA52–JA55 without new machinery |
| (d) Risk / cost | **4** | CPU only. Leaves the fallback's phase cost in place ("known cost") |

### Kilo v4: P-G survives, the affine rule should be (b), and the phase check needs cuts fitted after motion

| | Score | Why |
|---|---|---|
| (a) Reasoning | **5** | Withdrew its own (k) on its own evidence. Explained why `rim_dark` fails: sub-voxel resampling after any motion puts the oracle at 0.03–0.04 against aligned cuts of 0.001–0.02. That makes it a cut problem, not a measure problem. Found the "limbo" status in code and the grid origin of Round 3's 160 / 200 |
| (b) Evidence | **5** | The best power evidence (2 × 2 000 sims, a 300-sim stability check, both reproductions). Scored all three row sets with one unchanged scorer. Determinism check on 96 shared cases. Its replication was cut short (rigid on 11 hearts) before any result was read, and it says so |
| (c) Fit | **4** | The routing table is executable and closes the limbo. Keeping the fallback and grading routed patients on their 4 mm stage treats the symptom and leaves unrouted phase patients exposed. Its (c) used 0.03, not #243's 0.02, which makes cross-reading harder |
| (d) Risk / cost | **4** | CPU only. (b) is safe but fragile on the phantom (5 / 9), which Kilo states |

### Juliet v4: the shipped chain on the benchmark, an affine rule, a stable seal size, and confirmed-only phase routing

| | Score | Why |
|---|---|---|
| (a) Reasoning | **4** | Found the fallback mechanism ("a misregistered heart can have a lower normalised maximum") and proposed reading phase before step 5. Named a likely cause of the overshoot (matrix entries and translation share one Powell step). The strongest argument against an unconfirmed-flag back door around JA55. Deducted: the pre-registered criterion has no harm screen, and the proposal departs from its own pick (0.05, post-hoc) |
| (b) Evidence | **4** | 504 cases, replay 16 / 16, 42 exploratory variants labelled as such; every number re-reads. Deducted: the note was written before the canonical rows existed, and never checked against them; the 50 % figure (200) sits one grid step above the other two (noise, §1.6) |
| (c) Fit | **5** | Confirmed-only routing, a bounded stratum, a put-back analysis and `seal_size` sized on analysed patients all fit JA27, JA52 and JA55 |
| (d) Risk / cost | **4** | Suspending affine would give up scale correction the safe rules already deliver |

**Totals (of 20):** Golf 18, Kilo 18, Juliet 17. Round 4 asks no candidate to replace the base. The path plan stays
Kilo v2 + JA25–JA36 + JA50–JA59, now amended by JA80–JA87.

---

## 3. Rulings where they disagree

| Item | Golf v4 | Kilo v4 | Juliet v4 | **Ruling** |
|---|---|---|---|---|
| Menu | P-J, P-G | P-J, P-G | P-J, P-G | **P-J then P-G, final; P-K struck** (JA80) |
| E-D column minimum | 4 | 4 | 4 | **4** (JA80) |
| Affine rule (JA51 4(b)) | (g) | (b) | (c) at 0.05; suspend affine until the overshoot is fixed | **(g)** (JA81) |
| PS3-S3 log-det sign | wrong; \|log det\| | — | — | **wrong; assert the sign the convention implies** (JA81, PS4-S3) |
| Affine overshoot | optimiser note | — | fix first, gate on it | **engineering issue, not a gate; (g) contains it** (PS4-S7) |
| 10 mm fallback | keep (known cost) | keep; grade routed patients on 4 mm | only on a QC pass; phase first | **keep, but a 4 mm edge-offset flag skips it** (JA82) |
| Provisional QC cuts | registered cases (`qc_cuts_registered`) | oracle after motion; phase step on edge offset only | registered cases | **registered cases, shipped QC definitions, declared in the file** (JA83) |
| B-spline | not as configured | not; trigger not opened | not as configured | **not opened as configured; JA53's trigger opens a proposal for a different method** (JA83) |
| Primary phase flag | edge offset | edge offset; `rim_dark` needs development cuts | edge offset; `rim_dark` registered cuts | **edge offset routes; `rim_dark` advisory** (JA84) |
| Phase-unmatched routing | flag → stratum; flag-only charged to yield | confirmed, or inferred + edge flag; outside yield | confirmed only | **confirmed → stratum, outside yield; inferred + edge flag → stratum, charged to yield; unconfirmed DICOM-matched flag → ordinary patient** (JA85) |
| Stratum grading | chain | last 4 mm stage | carried border | **last 4 mm stage** (JA85) |
| Seal size and phase share | — | — | N / (1 − phase share) | **adopted: power on analysed patients, enrolment inflated, cap on enrolment** (JA86) |
| Planning figure, 70 % | ≈ 150 | 160 | 140–160 | **≈ 160** (JA86) |
| When the cap binds | state power; the lead is told before grading | — | the lead should know | **stated power; no seal grading below 0.80 until the lead answers LQ40** (JA86) |
| `seal_size` sims | ≥ 1 000 | 2 000 stable | 2 000 | **2 000 default; interpolated N80 and MC band logged** (JA86) |

---

## 4. Binding amendments (JA80–JA87; path `jm/paired-scar`)

- **JA80 — The final Scar-0 menu.** (Settles JA54's condition; amends JA30.)
  - **Presence: P-J, then P-G.** P-G survived the shipped chain under #179's rules (§1.1), so JA54's "struck before
    development if Round 4 strikes it" does not apply; P-G is on the menu without condition. **P-K stays struck.**
  - **Extent: E-V, E-D**, E-D on remote + 3 SD (JA54).
  - **E-D keeps columns spanning ≥ 4 depth bins**, as the benchmark that decided JA54 does (`column_min_bins = 4`).
    The module and the benchmark then agree on all 120 real-heart cases (§1.2).
  - **P-J's τ** under the shipped chain is 0.073–0.214 by blood level (CNR 5, `scores_v3.json` → `taus`), within
    0.013 of τ on true borders. It is re-fitted on development by JA54's procedure.
  - **Reported, unchanged:** sensitivity by LGE bin and the bin-1 share (bin-1 sensitivity on the chain: P-J
    0.52–1.00, P-G 0.60–0.90).
- **JA81 — The affine acceptance rule.** (Replaces JA51 4(b). 4(a), the sanity bound, is unchanged.)
  - **Affine is kept iff all hold:**
    - **(a)** |log det A| ≤ 0.15, and every singular value and shear term within ± 15 % of identity (unchanged);
    - **(b′)** the normalised QC maximum (over the gated values, each divided by its cut) for affine is **≤** the same
      for rigid;
    - **(c′)** **and either** the affine result passes QC, **or** |log det A| ≥ 0.02.
  - Any NaN rejects.
  - **The sign convention is written down.** `Transform` maps the fixed LIE to the moving first pass. A LIE heart
    larger by s gives log det ≈ −3 log s. (c′) reads |log det| and does not depend on the sign.
  - **Why (g):** §1.4. It is the pre-registered pick under Golf's criterion, and under Kilo's once (g) is admitted.
    It keeps 0 / 23 worse affines on rigid motion and 53 / 115 helpful ones on scale. It keeps the PS3-S3 phantom's
    correct affine.
  - **Not adopted:** the literal rule and (a), which behave as "never affine"; (c) at 0.02 or 0.05, which rests on a
    log-det the overshoot reaches; suspending affine (Juliet), which gives up the scale correction (g) delivers safely.
  - **The scale gap stays open:** about half of helpful affines are still refused. The reader check on every patient
    (JA51 step 6) stays.
- **JA82 — The phase check runs before the fallback.** (Amends JA51 step 5 and JA52's timing.)
  - After step 4, the edge offset (JA84) is computed on the result so far, which is the **last 4 mm stage**.
  - **If it is evaluable and flags,** the patient is phase-flagged: step 5 is skipped, and the last 4 mm stage is the
    final stage. JA52 already says registration cannot fix phase.
  - **Otherwise step 5 runs as JA51 states.** One 10 mm rigid replaces the result if it passes QC or lowers the
    normalised maximum. It earns its place on whole-image motion (`nonrigid` p90 2.23 against 2.87 mm without it).
  - The phase step (JA84) runs again on the final stage, and a flag there also counts.
  - **Why:** the fallback swaps a 0.26 mm rigid result for a 3–4 mm one on about half the smaller-cavity cases
    (Golf, Juliet, Kilo; §1.3). "Only on a QC pass" (Juliet) fixes that but costs non-rigid motion 0.6 mm of p90.
    Gating on the 4 mm edge offset targets the phase case. That flag is rare on non-rigid motion (10 / 74).
  - **This combination is unmeasured.** PS4-S5 replays it on the committed v3 rows before it ships. If the replay
    misses PS4-S5's acceptance numbers, the shipped JA51 step 5 stays, and the question returns to the next judge on
    this path.
- **JA83 — Provisional QC cuts, and the B-spline arm.** (Amends JA53.)
  - **Provisional cuts until development** are p95 of the **shipped** QC over **registered** benchmark cases:
    `bench_lie/scores_v3.json` → `qc_cuts_registered` (rigid4 with TRE < 1 mm on `none` and `rigid`, other half, per
    blood × CNR). They are not `scores.json` → `qc_cuts`: those were measured with v2's QC definitions on un-resampled
    aligned images, and gate nothing (0 / 63, §1.3).
  - **A cut file declares the QC definitions it was measured with** (`janusm.scar.registration` and its
    SCAR_VERSION). The loader refuses any other.
  - **JA53's development fit is unchanged:** p95 over reader-passed development patients, indexed by contrast, with
    the drop rule. Real patients are always resampled, so a development cut does not have the aligned-image problem
    (Kilo).
  - **B-spline is not opened as configured.** Round 4's arm (20 mm, 4 mm mask, from rigid4) is worse than the chain
    on non-rigid motion (all three advocates), and raises rigid's median by 1.5–1.9 mm (Golf, Kilo). If JA53's trigger fires on
    development, it opens a **proposal** for a different non-rigid method (regularised, or a finer grid), benchmarked
    on `nonrigid` and `rigid` before it is used. Until then non-rigid residual is left to the reader check and the
    yield bar, as JA53 says.
- **JA84 — The phase flags.** (Amends JA52.)
  - **The routing flag is the edge offset**, |offset| > 0.6 mm over the 6 remote segments (JA52's definition and
    sign). It sees both directions: 70 / 74 larger-cavity and 58 / 74 smaller-cavity cases, with 1 / 148 false flags.
  - **`rim_dark` is advisory.** It stays a QC gate value, is logged after the final stage, and is shown to the reader
    after the decision (JA58). **On its own it routes no patient.** Its flags mark misregistration in general
    (74 / 74 `nonrigid`).
  - **Not evaluable** stays as JA52 states (contrast < 2 robust SD).
  - **Development may restore `rim_dark` as a routing flag.** This happens only if, at its development-fitted phase
    cut (JA53), its false-flag rate on reader-passed, phase-matched patients is ≤ 5 % (Kilo). That would be recorded
    in the JA28 freeze.
- **JA85 — Where a phase-flagged patient goes, and how it counts.** (Amends JA52's routing and JA55; settles #251
  item 4.)

  | Phase source (JA59) | Edge-offset flag | Reader marks "cavity size differs (phase)" | Status and route | Primary | Yield |
  |---|---|---|---|---|---|
  | DICOM phases differ (no reconstruction at the LIE's phase) | any | any | `phase_suspect` → `phase_unmatched` stratum | out | **not counted** |
  | DICOM-matched or inferred | any | **yes** | `phase_suspect` → stratum (confirmed) | out | **not counted** |
  | Inferred from text | **yes** | no | `phase_suspect` → stratum (**flag only**) | out | **counted** in numerator and denominator |
  | DICOM-matched | yes | no | **ordinary patient**: the flag is logged; the reader check decides (passed / re-registered / not graded under JA55) | in | as JA55 |
  | any | no | no | ordinary patient | in | as JA55 |

  - **Grading.** A stratum patient is graded on its **last 4 mm stage** (rigid, or affine if kept), never on the 10 mm
    fallback. It is never re-registered.
  - **Reported, never deciding:**
    - the stratum's own sensitivity, specificity and Kim-bin agreement under JA55 accounting;
    - its share with an upper 95 % bound;
    - its LGE-positive share against the primary set;
    - the primary endpoints with the stratum **put back** under JA55 split accounting (Juliet, Kilo).
  - **Stops.**
    - JA52's > 20 % development report stands.
    - On development, a flag-only share > 3 % is also reported to the lead. At that rate it would spend the seal's
      failure budget (Golf E12b).
  - **Why.** A flag alone is not phase (§1.7), so unconfirmed routing would be a back door around JA55 (Juliet). True
    phase mismatch is a reconstruction fact, not a registration failure, so it is kept out of yield (Kilo).
    Inferred-phase patients cannot be confirmed from DICOM. Routing them on the flag alone is allowed, but charged, so
    no algorithm removes patients for free (Golf).
- **JA86 — Seal size, its stability, and what happens when the cap binds.** (Amends JA57; LQ27, LQ40.)
  - **The rule is unchanged:** max(120; N for ≥ 270 scarred segments; N for ≥ 80 % power on claim 1), from development
    inputs, under JA55 accounting, capped at 240, and it only grows.
  - **Stability.** `seal_size` runs **2 000 simulated studies per N by default**. It logs the interpolated N80 and its
    ± 2 MC-SE band beside the grid N.
  - **Phase share.** Power is computed on **analysed** patients. Enrolment is analysed / (1 − development
    phase-unmatched share), and the 240 cap applies to enrolment (Juliet).
  - **Stated power.** `seal_size` returns `power_at_seal` and `underpowered = power_at_seal < 0.80`.
  - **When the cap binds and power at 240 is < 0.80, no seal patient is graded until the lead has answered LQ40.** The
    lead receives the measured failure rate, the clustering, the phase share and the power at 240. JA29's > 10 % stop
    stays the hard floor.
  - **Planning figures for the lead** (2 % failure, weak clustering; §1.6):
    - **≈ 40 + 160 at 70 % enrichment** (Golf's infarct size 130–140, Kilo's 145–160);
    - **≈ 40 + 200 at 50 %** (range 180–220).
  - **Where the plan breaks.** A failure rate above ≈ 3 %, or strong clustering, leaves even 240 below 0.80. At 5 %
    failure, power at 240 is 0.44–0.60 (weak) and 0.17–0.22 (strong). Development's measured failure rate is the
    number that decides whether the seal can be powered.
  - **Claim 2** does not bind at the base extent error (q = 0.25). JA57's claim-2 clause stands for a worse development
    q.
- **JA87 — The benchmark is closed, and the record.**
  - **No further synthetic-LIE round is needed on this path.** Every Round 3 §7 item is settled. The two remaining
    unknowns (the scale gap and non-rigid residual) can only be measured on real paired data.
  - **Record:**
    - the PS3-S3 test's `log_det > 0.03` has the wrong sign (§1.5);
    - Golf's cross-criterion 2.91 was uncommitted; the judge reproduced it from committed rows and code (§1.4);
    - Golf v4 §3.2 pools CNR 3 with CNR 5; the CNR 5 `phase` chain is 1.20 / 3.68 mm;
    - Kilo's (c) is at |log det| ≥ 0.03, Golf's and Juliet's at 0.02. The two pooled p90s on Golf's rows happen to
      agree (3.46);
    - the motion names `phase` and `phase_neg` mean a **smaller** and a **larger** LIE cavity. Notes disagree on the ±
      label, so later notes say "smaller" or "larger";
    - Juliet v4 was written before the canonical rows existed; its strike numbers are a replication;
    - JA36's held-out rule was kept by every note this round.

---

## 5. Questions for the lead (each with a recommendation; none is a fork)

**Carried as assumptions:**
- LQ2–LQ18 and LQ25–LQ28, with their rulings' recommendations, except as updated here.
- **LQ27 (a)** now reads: 70 % enrichment, planning ≈ 40 + 160 (≈ 200 at 50 %), cap 240, with stated power (JA86).

### LQ40 — What happens when development shows the seal cannot be powered within 240

- **When it arises:** development's measured failure rate, clustering or phase share make claim 1's power at 240 less
  than 0.80. On Round 4's engine this happens at failure above ≈ 3 % (weak clustering) or ≈ 1 % (strong).
- **Options:**
  - (a) proceed with the 240 seal at the stated power, accepting a higher chance that a working method ends "not
    validated";
  - (b) hold seal grading, and reduce the failure rate first: development's reader re-check and the JA83 non-rigid
    proposal, then re-measure on extended development. Proceed when power at 240 is back to ≥ 0.80, or move to (a)
    in writing;
  - (c) lift the cap.
- **Recommendation: (b).** The seal is scored once (JA32). Spending that look at 0.5–0.7 power risks the cohort on
  noise. Failure rate is the one input development can change, and the seal tolerates about 3 % at 240 (Golf E12b).
  (c) chases power that clustering may never give: at strong clustering and 2 % failure, power is 0.64–0.69 at 240 and
  only 0.76–0.77 at 320 (Golf E12).

---

## 6. Forking question: **no fork**

The cap would allow one (2 of 4 paths active). No open question changes this path's structure:
- **JA80–JA86** settle a rule, a flag, a route or a size on evidence;
- **LQ40** is about whether a future seal is graded, not about what the path builds;
- **the real fork, whether a paired cohort exists at all,** is LQ1, which created this path.

---

## 7. What the next round must settle: nothing. The path now waits only on the lead

**No Round 5 on this path.** The shipped chain has been through the benchmark, the menu is final, and the power engine
is stable. What is left is engineering (§9, PS4-S1–S9), which the PM opens as `role:swe` issues. **One exception:** if
PS4-S5's replay misses its acceptance numbers, JA82's fallback question alone returns to a judge on this path.

**The path waits on the lead for:**
- **LQ1:** whether a paired CCTA + same-session LIE + CMR LGE cohort is pursued, and access to it (D19, outside the
  repository; D31: no request text anywhere);
- **Job JM-0 and JM-0R:** Stage A numbers, shared with path A (JA50);
- **LQ40**, only once development numbers exist.

---

## 8. Path B against path A, for the lead (Round 3 §8, updated; for #143)

| | Path A, `jm/rest-ccta` | Path B, `jm/paired-scar` (after Round 4) |
|---|---|---|
| Assumes | no reference for scar or ischaemia | the lead obtains a paired CCTA + same-session LIE + CMR LGE cohort (data requirements only, D31) |
| Stage A | built and calibrated; bias guard 0.3 mm (JA71) | **identical code** (JA50) |
| Scar rule | — | **P-J then P-G, final** (both survive the shipped chain: P-G ≥ 0.915 / 0.985, P-J ≥ 0.888 / 0.958); P-K struck; E-V or E-D (3 SD, ≥ 4-bin columns) |
| Registration | — | R0 → QC (cuts from registered patients) → 4 mm rigid → affine if sane, no worse on QC, and passing or scaled → edge-offset phase check → 10 mm fallback unless phase-flagged → reader check on every patient |
| Phase | — | the edge offset routes (1 / 148 false flags); `rim_dark` is advisory; confirmed mismatch goes to a graded, reported stratum outside the claim; unconfirmed routing is charged to yield |
| What passing gives | specificity-calibrated flags | **presence** validated on sensitivity, specificity and yield; the **Kim bin** if CT grades as well as the readers (not binding at the base extent error) |
| Cohort | none | 40 development + **≈ 160 seal at 70 %** (≈ 200 at 50 %); never more than 240 |
| What breaks it | — | a registration-failure rate above ≈ 3 %, or strong clustering: power at 240 then 0.17–0.69, and the lead decides before any seal grading (LQ40) |
| Reader time | none | ≈ 200 × 2 CMR reads + adjudication + a registration check per patient (to be replaced by measured time, JA58) |
| Committed compute | ≈ 15 GPU-h | the same + ≈ 3 GPU-h once the cohort exists; scar on CPU |
| Built so far | Stage A tooling | Stage A (shared) + `src/janusm/scar/` (registration, scar0, power, scoring; SCAR_VERSION 1.1.0) + the shared LIE benchmark v1–v3 |
| Main risk | flags with no measured sensitivity | the cohort never arrives; non-rigid misalignment (≈ 1.6 mm on the benchmark) or a scale QC cannot see raising failures on real data |
| If the cohort never arrives | — | path B reduces to path A exactly. Nothing further can be learned on synthetic LIE |

---

## 9. Shipping (`role:swe`, labelled `jm/paired-scar`; code on `jm/paired-scar` in `src/janusm/scar/` unless stated)

Each item is one issue. "Test" names the check that proves it. No item reads a held-out case. Tests run on synthetic
phantoms in CI. Real hearts are used only in offline scripts that call the guard first, on the whole list and per heart.
After PS4-S1–S6, SCAR_VERSION becomes 1.2.0.

### `scar0.py`

- **PS4-S1 — E-D's column minimum follows the benchmark** (JA80).
  - **Wrong:** `JA30Constants.column_min_bins = 6` (`scar0.py:111`). The benchmark keeps ≥ 4.
    `bench_lie/module_parity.json` passes 62 / 120 real-heart cases, failing on E-D only (max |Δ| 0.191).
  - **Correct:** `column_min_bins = 4`.
  - **Test:**
    - a CI thin-wall phantom with at least one segment whose columns span 4–5 depth bins, where 4 and 6 give
      different E-D; the parity test on it passes at 0.02 with 4;
    - re-run `bench_lie/module_parity.py` offline (guard first) and re-commit `module_parity.json` with
      `n_pass == n_cases == 120`. Kilo's `k2_parity_columns4.json` is the expected result.
- **PS4-S2 — Grading a routed phase patient** (JA85).
  - **Wrong:** `FINAL_STATUSES` (`scar/__init__.py:42`) excludes `phase_suspect`, and `scar0` refuses it
    (`scar0.py:238`). The `phase_unmatched` stratum can never be filled.
  - **Correct:**
    - `PHASE_SUSPECT` joins `FINAL_STATUSES`;
    - `scar0` grades such a patient on the carried geometry of its **last 4 mm stage**, which `Registration` exposes
      as `graded_stage` (PS4-S5);
    - `for_scoring()` returns `strata ⊇ {"phase_unmatched"}` and `phase_route ∈ {"confirmed", "flag_only"}`.
  - **Test:** a synthetic registration whose final stage is `rigid10` but which is `phase_suspect` is graded on its
    rigid stage; `for_scoring` carries the stratum and the route.

### `registration.py`

- **PS4-S3 — The affine rule, and #243's xfail** (JA81).
  - **Wrong:** `qc_rule_accepts` (line 322) requires no normalised value to rise. It rejects most correct affines,
    which is why `test_ps3_s3_a_3_percent_scale_keeps_affine` is a strict xfail (#243). That test's last line
    asserts `log_det > 0.03`; the convention makes it −0.08.
  - **Correct:**
    - `affine_accepted(matrix, affine_qc, rigid_qc, cuts)` = `affine_sanity(matrix)["ok"]` and
      `normalised_max(affine) <= normalised_max(rigid)` and (`affine_qc.passes(cuts)` or `abs(log_det) >= 0.02`).
      Any NaN rejects. The constant is `AFFINE_SCALE_LOG_DET = 0.02`;
    - `Transform`'s docstring states the sign: a LIE heart larger by s gives log det ≈ −3 log s.
  - **Test:**
    - remove the xfail marker; the test passes with its last line changed to `assert aff.info["sanity"]["log_det"] <
      -0.03` (the 3 % enlargement found with its correct sign);
    - `test_ps3_s3_affine_that_increases_tre_is_rejected` still passes;
    - `test_ps3_s3_affine_rule_units`: replace the "one normalised value rises" case, which (g) keeps by design, with
      unit cases per clause: the maximum rises → reject; the maximum is flat, fails QC and log det 0.01 → reject;
      the maximum is flat and log det 0.03 → keep; fails QC but passes after affine with log det 0 → keep;
    - offline (report only): Kilo's K1 phantom seeds (`k1_phantom_rules.py`) under (g); report how many of the 9
      correct scale fixes are kept.
- **PS4-S4 — Phase flags and routing status** (JA84, JA85).
  - **Wrong:**
    - `phase_step` (line 765) flags on `rim_dark` or the edge offset alike;
    - `status_from_checks(checks, phase_suspect)` (line 840) returns `phase suspect` on any flag, whatever the reader
      says, so a flagged, DICOM-matched patient the reader does not confirm has no final status.
  - **Correct:**
    - `PhaseCheck` separates `routing_flags` (the edge offset only) from `advisory_flags` (`rim_dark`);
      `suspect` reads `routing_flags`;
    - `status_from_checks(checks, *, phase_flag, phase_source ∈ {"dicom_unmatched", "dicom_matched", "inferred"},
      reader_phase_mark)` follows JA85's table. It returns the route (`confirmed`, `flag_only` or none) alongside the
      status;
    - `failure_rate` and `phase_suspect_share` keep ignoring / counting `phase_suspect` as today.
  - **Test:**
    - one synthetic case per JA85 row;
    - the limbo case (DICOM-matched, edge flag, no reader mark, check passes) ends `passed`;
    - a `rim_dark`-only flag never yields `phase_suspect`;
    - the existing PS3-S4 phantoms still flag (+5 % by `rim_dark` as advisory and −5 % by the edge offset as
      routing).
- **PS4-S5 — The phase check before the fallback** (JA82).
  - **Wrong:** `register_lie` (line 1033) runs the 10 mm fallback on any patient whose 4 mm result fails QC. On a phase
    mismatch the "lowers the normalised maximum" clause swaps a 0.26 mm result for a 3–4 mm one in about half the
    benchmark's smaller-cavity cases.
  - **Correct:**
    - after step 4, compute `edge_offset` on the current carried geometry. If evaluable and above the cut, skip step
      5, and set `graded_stage` to that last 4 mm stage;
    - otherwise run step 5 as now, with `graded_stage` = the final stage;
    - `phase_step` runs on the final stage as now. The 4 mm check and the final check are both logged.
  - **Test:**
    - a static-chest phantom with a 5 % smaller LIE cavity and a 4 mm shift ends on the 4 mm stage, with no
      `rigid10` in `stages`;
    - a mocked whole-image-motion case (no flag) still runs the fallback (extend
      `test_ps3_s1_fallback_runs_only_when_the_4mm_stage_fails_qc`).
  - **Acceptance replay (offline, before merge):** add a report-only chain to `bench_lie/score_v3.py`. It is JA81 (g)
    with the JA82 skip, using the logged per-stage edge offsets on the committed `results_v3.jsonl.gz`. Commit its
    numbers. **Merge only if, at CNR 5:**
    - the #179 strike verdicts are unchanged;
    - the `phase` chain p90 is ≤ 1.2 mm;
    - the `nonrigid` p90 is within 0.3 mm of the shipped chain's (2.23 mm).

    Otherwise report to the PM and leave step 5 as shipped (JA82).
- **PS4-S6 — Provisional cuts from registered cases** (JA83).
  - **Wrong:** `load_provisional_qc_cuts` (line 1399) reads `bench_lie/scores.json` → `qc_cuts`. Those were measured
    with v2's QC definitions on aligned, un-resampled images. On v3 they pass rigid on 0 / 63 rigid-motion cases, and
    `rim_dark` flags 74 / 74.
  - **Correct:**
    - the loader reads `bench_lie/scores_v3.json` → `qc_cuts_registered` (shipped QC, rigid4 with TRE < 1 mm on
      `none` and `rigid`, keyed `half|blood|cnr`);
    - `max_rim_dark_phase` is set from `rim_dark_phase_cuts_ja53` (advisory only, JA84);
    - the file carries `qc_definitions: "janusm.scar.registration <SCAR_VERSION>"`, and the loader refuses a file
      without a matching declaration. A one-line `score_v3.py` change writes the key; the cuts themselves do not
      change.
  - **Test:**
    - loading v2's `scores.json` raises;
    - on the committed v3 rows, the benchmark phantom's `rigid` case at CNR 5 passes the loaded cuts at its rigid4
      stage and fails them at R0, at every blood level (judge's re-tabulation: TRE 0.16–0.22 mm, passes in 3 / 3).
- **PS4-S7 — The affine optimiser's scaling** (engineering, report only; not a gate on JA81).
  - **Wrong:** `_affine_from` (line 597) steps the nine matrix entries in units of 0.01 with the same Powell step as
    the translations (Juliet). On the benchmark the affine stage overshoots with no scale (p90 1.55–2.26 mm against
    rigid 0.55–1.13). Its sanity bound fails on 11 / 74 true 3–6 % scales (Golf).
  - **Correct:** an optional, default-off variant, behind a parameter and not used by `register_lie` by default:
    - a scale-only stage before the full affine, or separate step sizes for the linear part;
    - optionally a penalty toward rigid.
  - **Test:**
    - on the aligned and the 4 mm-shift phantoms, the variant's affine TRE median is ≤ rigid's + 0.1 mm;
    - on the 3 % scale phantom it keeps the sanity bound and lowers TRE;
    - the default path's results are byte-identical to today's.

    Adoption needs a later ruling, with a v3 replay.

### `power.py`

- **PS4-S8 — `seal_size`: stability, stated power, phase share** (JA86).
  - **Wrong:** `seal_size` (line 398) defaults to `sims=400`. At 300–400 sims the grid rule moves N by 20–40 between
    seeds (Kilo's 300-sim check). It returns no power at the seal and no phase-share inflation.
  - **Correct:**
    - `sims=2000` by default;
    - return `n80_interp` and `n80_mc_band` (± 2 SE, `Golf/r4/power_r4_table.py`'s method) beside the grid N;
    - return `power_at_seal` and `underpowered`;
    - a `phase_share` argument: power on analysed N, `seal_enrolled = ceil(N / (1 − phase_share))`, capped at 240;
    - `seal_grading_allowed(...)` in `registration.py` also returns False when `underpowered` is True and no LQ40
      answer is recorded (a `lead_override` argument).
  - **Test:**
    - two seeds at 2 % failure, weak clustering, 70 %, Golf size give seals within one grid step (140 expected);
    - 2 % failure, strong clustering, 70 % gives `seal = 240`, `underpowered = True`, power 0.63–0.69;
    - `phase_share = 0.1` raises enrolment by 1 / 0.9, capped at 240;
    - `phase_share = 0` reproduces the default.

### `scoring.py`

- **PS4-S9 — The phase-unmatched stratum, and flag-only routing in yield** (JA85).
  - **Wrong:** `score` excludes `phase_unmatched` from the primary (line 478), but nothing reaches it. Nothing
    charges unconfirmed routing to yield, and there is no put-back analysis.
  - **Correct:**
    - a patient with `phase_route == "flag_only"` counts as not-graded in the yield numerator and stays in its
      denominator, while still leaving primary accuracy;
    - a `confirmed` patient leaves primary accuracy and yield;
    - `score` reports the stratum's share with a patient-bootstrap upper 95 % bound, its LGE-positive share against
      the primary, its own JA55 accuracy, and the primary endpoints with the stratum put back under JA55 split
      accounting (reported, never in `decide`);
    - the development report flags a flag-only share > 3 % and a phase share > 20 % (JA52) for the lead.
  - **Test:** a hand-built study with one confirmed and one flag-only phase patient: both leave primary sensitivity
    and specificity; only the flag-only patient moves yield; the put-back analysis treats both as not graded under
    split accounting; `decide`'s output is unchanged by the put-back.

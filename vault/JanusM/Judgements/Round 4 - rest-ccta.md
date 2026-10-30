---
aliases: [Janus-M Round 4 rest-ccta]
tags: [janus-m, plans, judgement, round4, path-rest-ccta, myocardium, build-check]
author: Janus-M Round 4 judge (path jm/rest-ccta)
round: 4
path: jm/rest-ccta
status: ruling
updated: 2026-10-30
issue: christianGRogers/Asclepius#205
---

# Janus-M Round 4, path `jm/rest-ccta`: the judgement

**Ruling in one paragraph.** The built Stage A (S1–S7, #197–#200) follows JA37–JA48 on most clauses. Each enforcing
test the advocates named exists, and the suite passes (375 tests, reported by all three advocates). But the build
has **seven defects that print a wrong number or make a guard, a flag or a read check more lenient than ruled**.
The judge confirmed each one in the code (§1.2).
- The plan's structure does not change, and **the base stays [[Hotel v3]]** as amended.
- **JA60–JA69** fix the defects and close the clauses the code showed could not be built as written:
  - JA42's log branch;
  - JA37's band;
  - JA39's 0.03 mm;
  - the blank-read mitral check.
- **The provisional detectable depth becomes 45 %** (JA60).
- **The reference population is 360** (JA69).
- **One consolidated shipping list** (§7, R4-S1 … R4-S26), grouped by module.
- **No fork.**
- **The path now waits only on the lead's JM-0 / JM-0R and on §7's fixes** (§8).

Rules kept:
- The judge ran no experiment, opened no image, downloaded nothing and read no held-out case.
- Checks read committed code, tests and JSON on `jm/rest-ccta` at `9e782d9`, and issue #205.
- No twin or held-out id was read or printed.

---

## 1. What was checked

### 1.1 The advocates' numbers against their committed JSON: all match

| Advocate | Claim | File | Match |
|---|---|---|---|
| Hotel | R9 as shipped prints 0.35 at 4.2–9.668 mm; with the wall passed: 0.60 / 0.60 / 0.45 / 0.40 / 0.40 / 0.35; K = 1.109 | `Hotel/r4/e9_r9_median.json` | yes (K 1.1093, seed 20261030) |
| Hotel | Seed 31000: Hotel F1 at 9.668 → 0.35, at 5.7 → 0.45; rule C alone 0.30 at both | `Hotel/r4/e8_e5_vs_e7.json` | yes |
| India | Whole-mask `signed_bias` on open masks: error +0.119 / +0.071 / −0.069 / −0.113 mean at −0.5 / −0.3 / +0.3 / +0.5 mm; pp in the ROI worst ≤ 0.032 | `India/r4/s1_open_base_vol.json` | yes |
| India | Pooled RC with n = values: coverage 0.972 / 0.940 / 0.883 at within-patient ρ 0 / 0.5 / 0.8, against ≥ 0.989 with n = patients; ratio 1.198 | `India/r4/s367_rc_checks.json` | yes |
| Lima | E7's sequence (9.668, σ 0, Hotel, 1.0 mm) → 0.35; E5's floor 0.57–0.62 mm | `Lima/r4/e6_depth_decomposition.json` | yes |
| Lima | pp worst 0.0322 at 0.5 mm; two strict failures of 0.03 | `Lima/r4/e7_pp_tolerance.json` (and India `s1_ja39_strict.json`) | yes |

### 1.2 The PM's notes, verified in the code

1. **R9 / S6 never pass the measured wall to the detectable-depth simulation (all three).** **True.**
   - `jm0r_decide.py` line 386 calls `fn(cv_n, segment_shape, rc_terr_mm, sig_m=…, seed=…)` with no `median_mm`.
     So `calibrate.detectable_depth` uses its default, `LIMA_MEDIAN_MM = 9.668` (`calibrate.py` 63, 305).
   - `reference.gate` (line 528) passes the measured `median_level` as `median_mm`. `population()` then multiplies it
     by the phase factor again (`calibrate.py` 101–104; K ≈ 1.109).
   - **Effect:** R9 prints 35 % on any wall. On walls inside R3's own window, the procedure gives 40–60 % (Hotel E9).
2. **The pooled JA42 RC uses n = values (≤ 60) instead of patients (20) (all three).** **True.**
   - `reference.py` line 410: `n_pool = len(alld)`. That one n feeds both the pooled RC and step 3's χ² switch bound.
   - The factor √((n−1)/χ²₀.₀₂₅,ₙ₋₁) is 1.220 at 60 and 1.461 at 20, so the RC is 16–17 % low.
   - When a patient's territory differences correlate, coverage falls to 88 % (India).
3. **The JA42 log-scale rule cannot fire, or its level is wrong.** **True, both halves.**
   - D is a signed deviation (`calibrate.f1_deviation`: expected − measured, centred near 0), so `repeatability`'s
     "D positive throughout" test (lines 393–397) never holds for thinning or hypoattenuation. The branch is dead for
     the two signs it was written for.
   - Fat could take it, but `report.py` line 198 passes `level = 1.0` for fat. The floor becomes (e^RC − 1) × 1 mm³:
     0.35 mm³ at RC 0.3 (Hotel), ≈ 1.3 mm³ on India's design. F1 is then vacuous for fat.
   - The non-fat level is the wall, not the level of D (Hotel H4-5).
4. **`signed_bias` ignores JA37's band (India); the transfer check is not built (Lima, Hotel, India).** **True.**
   - `harness.signed_bias(ref, test, spacing, smooth_vox)` (line 293) has no ROI. `compare(roi=)` restricts only pp,
     and a test asserts that it does.
   - No function builds the band.
   - `signed_bias_pp` has no caller outside the harness, so no transfer check exists.
   - India's open-mask table (§1.1) shows the effect: a true bias near 0.38–0.40 mm reads 0.30 and passes the 0.3 mm
     guard. That is larger than JA37's disclosed real-wall error.
5. **The JA46 (a) mitral check misses pool outside the fitted disc, and on blank reads fits its plane to the read it
   judges (all three).** **True.**
   - `checker.pool_above_mitral_mm` keeps only `inplane <= radius` (line 351), with no margin, although the docstring
     says "plus the gap".
   - `server/girder_janusm/check.py` passes `seed_path` only when `case.seedFileId` exists. `populate.py` uploads no
     seed for blank cases (line 112), so a blank read's plane comes from its own gap.
   - The hinge-point fallback exists in `mitral_plane`, but no caller passes hinge points.
   - When no plane can be fitted, the checker only warns (line 399).
6. **Read-queue holes (Lima G6–G11).** **True** as stated:
   - `adminThirdReads` (`rest.py` 342–359) opens a third read on any accepted seeded case, any number of them. The
     JA47 draw is computed in `anchoring.third_read_cases`, but it is not enforced.
   - `changed_share` (`anchoring.py` 82–87) divides by the seed ∪ read foreground. JA47 says seed voxels.
   - A crash returns the read (`check.decide`, line 55), but `attempts` was already incremented at submit
     (`models.py` 195). The next genuine failure is then accepted and flagged, although the reader never saw a real
     check.
   - `PROTOCOL_VERSION = 1` (`src/janusm_reads/__init__.py`), so a 0.1.0 client can claim and draw a whole read
     before it is refused at submit.

**Further checks:**
- `case_state`'s silent fall-back to the AHA map exists (lines 248–251), and fat's D is on the AHA-default map
  (`fat_territory_volume`, line 211) (Lima G16).
- Step 4a tests the **pooled** mean Δ when a territory uses the pooled SD (line 428), so opposite territory offsets
  cancel (Lima G14).
- `build_reference.py` has no R8 input (Lima G24, India IG17).
- `report.py` never reads the LM grade (India IG12, Lima G19).

### 1.3 The agreed points, checked

- **The 45 % vs 35 % gap is the wall median.** All three advocates find this independently, on the shipped
  `janusm.calibrate`:
  - rule C alone is 0.30 at both medians;
  - F1's 1.0 mm floor is 10 % of a 9.67 mm wall but 18 % of a 5.7 mm wall.
  - At an equal median, Hotel's and Lima's F1 code give the same depth (India E11: 0.40 = 0.40).
  - Lima's printed 45 % was a tail seed: its own procedure gives 0.40 on 18 of 20 seeds.
  - **JA49's "unexplained" is closed.** S3 exposes no error in JA40's procedure, only an input the ruling never
    fixed.
- **9.668 mm fails R3's 4.2–8.0 mm window.** The table that flags thinning can therefore never have it, and E7's
  population was in fact simulated at 10.7 mm (9.668 × K).
- **Reference population 360.** `derive_cases` gives 560 − 60 − 40 − 40 − 60. The guard refuses the extension under
  every purpose but `seal_scoring`, and `test_derived_population_excludes_every_janusm_list` asserts 360.
- **JA39 is enforced at 0.035 mm** (`round(abs(err), 2) <= 0.03`).
- **cv_n = 0 prints no NOT DECIDABLE.** R9's `except ValueError` branch (line 387) appends nothing to `missing`.
  JA44's acceptance test passes only because 40 identical rows give cv_n = 0 (India IG5).
- **No JM-0 / JM-0R aggregate is posted** on #205 (two comments, neither an aggregate). R0–R10 have no plan value
  yet.

### 1.4 Disclosures

- **Held-out cases.** All three advocates disclose that no case or image was opened. India's one id-touching step
  read committed lists through `guard.refuse` and printed counts only. No committed Round 4 file names a held-out
  or twin id (checked by file listing, not by opening any list).
- **No outside-request text** in any candidate (D31).

---

## 2. Scorecards

Scale 1–5:
- **(a)** reasoning;
- **(b)** evidence;
- **(c)** fit to the path and how ready the specs are;
- **(d)** risk and cost (5 = low risk, cheap).

### Hotel v4: the build is faithful except where it prints a number the plan cannot yet see

| | Score | Why |
|---|---|---|
| (a) | **5** | Found the phase factor applied twice (K), the wrong level in the log conversion, with correct algebra for all three bands, the crash that spends the return, and both mitral failure modes. Concedes its own 420 cleanly |
| (b) | **4** | E8, E9 and E10 are small, committed and decisive. Deducted: names JA37's band gap but does not measure its size on open masks (India did); missed the pooled-mean cancellation in step 4a and fat's AHA map |
| (c) | **5** | 13 items, each one issue with a test |
| (d) | **4** | H4-8 orders hinge points first on blank reads: reader time on every blank read, and a reader-placed reference |

### India v4: the shipped Stage A checked against the ruling

| | Score | Why |
|---|---|---|
| (a) | **5** | The only candidate that **measured the size** of every lenient gap: open-mask bias (24 % under-read), RC coverage (88 %), blank-read mitral leniency, and fat's floor. Found that JM-0R's acceptance test is vacuous (cv_n = 0). Retires its own R3 clause (JA42's log branch) as ill-posed |
| (b) | **5** | Seven committed scripts with JSON; every table row traces to a file |
| (c) | **4** | Deducted: the client refusal by header is more code than bumping the wire version; it withdraws the hinge fallback outright; it pre-registers a distal-mass definition no ruling needs yet |
| (d) | **4** | The server-held check seed (IG9) adds a populate step, but costs readers nothing |

### Lima v3: the depth is simulated on the wrong wall, and the pooled RC on the wrong n

| | Score | Why |
|---|---|---|
| (a) | **5** | Findings the others missed: step 4a's pooled mean cancels opposite offsets; fat's D is on the AHA map; `sealed_r1.load()` returns a frozenset, so "the first 20" has no order; the third-read draw is not enforced; read 1 / read 2 must be fixed per reader |
| (b) | **3** | E6 and E7 are clean and committed. Deducted: several probes quoted in the text (the LV–RV contact sweep, the radius 5.7 → 10.3 mm refit, the 4 mm-gap blank read) have no committed script or JSON |
| (c) | **4** | 27 items, the most complete list; some reach past the ruling (G26's export scope) |
| (d) | **4** | Cheap; G7's "fit from the LA-side gap" still fits the plane to the read being judged |

**Totals (of 20):** Hotel 18, India 18, Lima 16.

- This round audits the build. It does not choose between plans, so **no candidate replaces the base**: the master
  plan stays Hotel v3 + JA37–JA49, now + JA60–JA69.
- On the tie, **India v4 is the round's lead audit**, because it measured what each gap costs. The amendments take
  from all three.

---

## 3. Rulings where they disagree

| Item | Hotel | India | Lima | **Ruling** |
|---|---|---|---|---|
| Wall input to S3 | `wall_median_mm` ÷ K, K from the run's seed | `population_median_mm`, factor solved from the same population | `measured_median_mm` ÷ `population_factor`, deterministic (200 000 hearts, seed 7) | **Lima's deterministic factor; India's no-default rule** (JA60) |
| Provisional print | 45 % | 45 % | 45 % | **45 %** (JA60) |
| cv_n = 0 | NOT DECIDABLE; provisional; no thinning flag | NOT DECIDABLE; provisional | NOT DECIDABLE; numbers only; footer labelled placeholder | **NOT DECIDABLE; the thinning sign shows numbers only; the footer prints 45 % labelled as the placeholder** (JA60) |
| JA37 band | ±3 mm; minus ≤ 3 mm of LA and an optional aorta mask | ±3 mm; minus LA and aorta, or the base plane | ±3 mm (judge to confirm); minus LA and aortic plane | **±3 mm; minus ≤ 3 mm of label 4 or of any LV-pool face open to background (the outflow)** (JA61) |
| `signed_bias` in the band | yes | yes, plus an open-base validation; fail → 0.5 | — | **yes, with India's open-base validation** (JA61) |
| Scorer / record producer | one tool (H4-2 + H4-12) | one tool (IG16) | two tools that share a loop (G4, G25) | **one lead-run tool** (JA62) |
| Step 4 n | patients | patients | patients | **patients, also in step 3's switch bound** (JA63) |
| Step 4a mean | — | — | the territory's own | **the territory's own** (JA63) |
| Step 4b | log; level = median pair mean of D; in practice fat only | relative RC on Δ ÷ patient level; fat on differences | log(expected ÷ observed); fat never | **relative RC on Δ ÷ expected level for depth signs; fat on differences; (e^RC − 1) deleted** (JA64) |
| JA39 tolerance | 0.035 | 0.035 | 0.035 | **0.035 mm, unrounded** (JA65) |
| Blank-read mitral plane | hinge points first | a server-only check seed | fit from the LA-side gap; hinge points wired | **the server-only seed; hinge points stay only as a code fallback** (JA66; LQ31) |
| Footprint | max(fit radius, LA extent 0–10 mm) | radius + 3 mm | radius + 3 mm | **max(fit radius + 3 mm, LA extent 0–10 mm above the plane)** (JA66) |
| No plane | — | warn | error | **"could not be checked": handled as a crash** (JA66) |
| Old clients | wire `PROTOCOL_VERSION` 2 | header, refused at claim | wire `PROTOCOL_VERSION` 2 | **wire version 2** (JA67) |
| 4B and LM | 4B on LM only; 3 / 4A not on LM | 4B on LM only; LM feeds LAD / LCx | the same; three-vessel 4B derived | **LM: 0, 1, 2, 4B, 5, N; others: 0, 1, 2, 3, 4A, 5, N; LM feeds LAD and LCx**. No derived patient-level row (JA67) |
| Rule 2 denominator / draw | seed; draw enforced | union "slightly conservative", kept | seed; draw enforced; third reads exported apart | **seed; draw enforced; third reads exported apart** (JA68) |
| Crash and the return | count real returns only | decide on attempts − crashes | the same | **a crash never counts** (JA68) |
| Reference size | 360 | 360 | 360 | **360** (JA69) |
| Septal-arc column | build | build | build | **build** (JA69) |
| Distal mass | defer; spec ready | defer; pre-register the definition | defer; label "not computed" | **defer; labelled "not computed (report v1)"; no definition ruled** (JA69) |
| JA48.1 "PINNED" | move into `PINNED` | same effect, record only | same effect, say so | **`guard.REFERENCE_SHA256` satisfies JA48.1; the text is amended; no code** (JA69) |

---

## 4. Binding amendments (JA60–JA69; path `jm/rest-ccta`)

- **JA60 — The detectable depth is simulated on the measured wall; provisional print 45 %.** (Amends JA40, JA41,
  JA43 R9.)
  - **The input.** `calibrate.detectable_depth` takes the measured median wall, `measured_median_mm`, of the
    population whose table it prints. In R9 that is JM-0R's `thickness_median_mm`. In `reference.gate` it is the
    reference population's `median_level`.
  - **The conversion.** S3 converts the measured median to its anchor by `measured ÷ population_factor(phase_mix,
    shape, cv_n)`. The factor is a deterministic function (Lima G1: 1.1087 at Lima's inputs), so the simulated
    population's median equals the measured one.
  - **The default.**
    - `median_mm` stays only for E7's regression tests.
    - Passing both inputs is an error.
    - With neither, the anchor is `ED_MEDIAN_MM` = 5.7 mm.
  - **Hypoattenuation** (a relative HU level) is simulated with `phase_mix = {"ED": 1.0}`. Phase does not scale HU.
  - **Provisional print until JM-0R: 45 %.** That is JA40's procedure at the 5.7 mm anchor, F1 1.0 mm, cv_n 0.088,
    seed 31000. Above 0.40, so the page carries JA40's warning sentence. It is within JA41's 0.50 gate by one step.
    - 9.668 mm is never a plan input: it fails R3, it comes from 1.5 mm model labels on non-CCTA studies, and as an
      anchor it was phase-scaled twice.
  - **R9's branches:**
    - **A missing `thickness_median_mm`** → "NOT DECIDABLE: thickness_median_mm", and the provisional print.
    - **S3 refuses its inputs** (for example cv_n = 0):
      - R9 prints "NOT DECIDABLE: cv_n (S3 refused: <reason>)";
      - the thinning sign shows numbers only until JM-0R is rerun (JA41 cannot be evaluated);
      - the footer prints the 45 % labelled "provisional (JA40), not computed on this population".
    - **R3 fails** → R9 still computes, and its line adds "on an unaligned thickness definition; no thinning flag
      ships before R3's alignment".
  - **JA44's acceptance test** is rebuilt on rows with seeded per-segment jitter, so that R9 computes a depth. The
    identical-rows case becomes its own test, asserting the NOT DECIDABLE line.
  - **JA49's "45 % vs 35 % unexplained" is closed** (§1.3).
- **JA61 — JA37's band, built and applied to the guard's estimator.** (Amends JA37, JA39.)
  - **The band.** For each border of the reference read:
    - keep the voxels within ±3.0 mm of that border;
    - remove the voxels within 3.0 mm of label 4 (LA);
    - remove the voxels within 3.0 mm of any LV-pool face adjoining label 0 (the outflow and the aortic opening,
      which the labels mark only by being open).

    This needs no aorta label. It is one function, `harness.ja37_band`.
  - **The estimators in the band.** `signed_bias` counts ΔV in the band, and each marching-cubes area counts only
    the faces whose centroids lie in it. Both terms of JA8's d (pp ASSD) and the 1.0 mm guard use the same band.
    The voxel ASSD is reported on whole masks.
  - **Read-vs-read.** The reference is read 1, fixed per reader (JA62).
  - **Validation.** `validate_bias_estimator(open_base=True)` repeats JA37's check on `exact_shift_phantom` cut by a
    fixed base plane, with the band (India E6-style open phantom, two grids, three walls, both borders, ±0.3 and
    ±0.5 mm).
    - **Pass is |error| ≤ 0.05 mm:** the guard stays 0.3 mm.
    - **If it fails,** the guard is 0.5 mm from the freeze PR on, and the judge of the next round is told.
  - **Record.** The whole-mask `signed_bias` under-reads by ≈ 24 % on open masks (India IG1). The shipped guard has
    never been applied to a real case, so no decision was taken on it.
- **JA62 — One lead-run decision-scoring tool.** (Implements JA8, JA37's transfer check, JA39, and JA42's input;
  #199 deferral (c).)
  - **The tool.** `tools/janusm/score_decision.py` is the only code that opens decision reads.
  - **Running.** Without `--run` it prints the Fir command. It runs only under Slurm.
  - **Guard first.** It calls `guard.refuse(decision, purpose="decision_scoring")` before opening any file.
  - **Order** is the **list order** of `configs/janusm/sealed-r1.json`'s `decision` (not `sealed_r1.load()`'s set). So
    "the first 20" means the first 20 cases in that order with two accepted `border_protocol: 1` reads. Third reads
    are excluded.
  - **Read 1 and read 2** are fixed per reader by a stable key that is never written out.
  - **Per case:**
    - `features.case_features` for each read, with **one** reference coronary tree for both reads;
    - `harness.compare(…, roi="ja37")` for model-vs-read and read-vs-read: pp ASSD, d, the 1.0 mm guard, `signed_bias`
      and `signed_bias_pp`; voxel ASSD beside them.
  - **The transfer check** (`harness.transfer_check`) runs on the first 20:
    - median |vol − pp| per border;
    - > 0.05 mm → the guard is 0.5 mm before any seal read;
    - the count of cases over 0.05 mm is reported (no ids in the output).
    - Fewer than 20 → an error, never a default.
  - **Output.** One anonymous JSON (`reads`, `assd_pp`, `transfer_check`) through `reference.assert_anonymous`, with
    its sha256. `build_reference.py` takes `reads` as its decision read records.
- **JA63 — JA42 steps 1, 3 and 4 as written.**
  - **Steps 3 and 4: n is the number of patients** with at least one pair. It is used in the pooled RC and in step 3's
    χ² switch bound. `n_patients` and `n_values` are both reported.
  - **Step 4a.** Each territory's **own** mean Δ_T is tested against 0.5 × the SD it uses (pooled or own), and added
    if larger. A pooled mean can cancel opposite offsets (Lima G14).
  - **Step 1, fat.** Fat's D is the core cluster volume per **patient-map** territory. Rule C's fat flag stays on the
    AHA map, as calibrated.
  - **Any fall-back** to the AHA map, for any sign, is counted in `rc["decisions"]` and in the report header. It is
    never silent.
- **JA64 — JA42 step 4b replaced: a relative RC for depth signs, differences for fat.**
  - **For thinning and hypoattenuation:**
    - each read's territory has an expected level E_T = the remote level × the territory's mean shape (the term D is
      measured against in `f1_deviation`);
    - if Spearman ρ(|Δ_T|, mean of the two reads' E_T) > 0.4, and E_T > 0 for every pair, the RC is computed on
      Δ_T ÷ Ē_T (relative), and applied as RC_rel × E_T;
    - E_T is the patient's own in the report. In `gate()` it is the population's median wall × the territory's mean
      shape;
    - otherwise the RC stays on differences, with the decision recorded.
  - **Fat's RC is always on differences, in mm³.**
  - **The (e^RC − 1) × level conversion is deleted.** No level of 1.0 remains anywhere. The gate and the report call
    one function for the floor in mm.
  - **Why:** a log ratio of a signed deviation is undefined. Applying a relative RC at the case's own D is no floor
    at all (Hotel). For the small RCs expected, RC_rel × E is within a few per cent of either log-band edge.
- **JA65 — JA39's fixture tolerance, unrounded.**
  - pp ASSD and pp bias are within **0.035 mm** up to 0.5 mm and **0.07 mm** at 1.0 mm (E6 worst 0.032 and 0.067),
    compared without rounding.
  - No decision moves: 0.035 mm is a seventh of JA16's 0.25 mm margin.
- **JA66 — JA46 (a), final.**
  - **Blank cases** are checked against a **check seed held by the server and never served to readers**
    (`checkSeedFileId`). It is the same `heartchambers_highres` seed the anchoring gap already compares blank reads
    against. The reader sees the check's verdict and the height, never the seed.
  - **The plane's sources, in order:**
    1. the seed's (or check seed's) 2–4 interface;
    2. the read's own gap, only when no seed exists;
    3. hinge points, kept in code as a last fallback. No form field is added.
  - **The footprint** is max(fit radius + 3 mm, the in-plane extent of label 4 between 0 and 10 mm above the plane).
    Inside it, label 2 > 3 mm above the plane is an error. Outside it, it is a warning.
  - **No fittable plane** is "could not be checked". It takes JA68's crash path: returned, not counted, and the PM is
    alerted. It is never a pass.
  - **The check report** records the plane's source and radius.
- **JA67 — The read form under CAD-RADS 2.0; old clients refused at claim.** (Amends JA46 (d), JA48.3.)
  - **Allowed grades.** On the **LM** row: 0, 1, 2, 4B, 5 and N. In CAD-RADS 2.0, LM ≥ 50 % is 4B, so 3 and 4A are not
    LM grades. On **LAD, LCx and RCA**: 0, 1, 2, 3, 4A, 5 and N (4B is patient-level).
  - **The protocol text** attributes branches to vessels: diagonals → LAD; obtuse marginals and ramus → LCx; PDA and
    PLB → the dominant artery.
  - **Table B.** LAD and LCx take the worse of their own grade and LM's (0 < 1 < 2 < 3 < 4A < 4B < 5; N only if
    both are N or absent). The row notes "LM <grade>" when LM is the source.
  - **Lesion points** stay on grades 1–5 only, and are refused outside the CT's world bounding box.
  - **The wire `PROTOCOL_VERSION` becomes 2,** because the submission schema changed. 0.1.0 clients get 426 at
    `next`, before they claim a case. `border_protocol` stays 1 and separate.
- **JA68 — JA47 and the return, as written.**
  - **Rule 2's share** is the number of differing voxels (within seed ∪ read) ÷ the number of **seed** foreground
    voxels.
  - **`adminThirdReads`** takes a wave and opens third reads only if:
    - that wave's report has `rule2.flagged`;
    - the list equals `anchoring.third_read_cases(wave, seeded)`.

    Third reads are exported apart, with `reference: false`.
  - **Rule 1's gap** is computed from read-level means, bootstrapped by case. A test pins independence, the 0.95
    quantile and `BOOTSTRAP_SEED`.
  - **A checker crash** (or JA66's "could not be checked") never counts toward the one return. Only a genuine failed
    check counts.
- **JA69 — Record and small rulings.** JA14, JA24 and JA49 stand. Added:
  - **Reference population: 360** (560 − seal 60 − decision 40 − JM-0 40 − seal extension 60). This supersedes
    "420" in JA18, LQ12 and Hotel v3 §4.1. Releasing the unused extension tail later would need a new config version
    by PR, never a refit of r1, and it is not planned.
  - **#199's deferrals:**
    - (a) the arc-proportional septal column is built, with one `arc_segments` in `janusm.geometry`;
    - (b) mass distal to a lesion point stays deferred, and prints "not computed (report v1)". No definition is ruled;
    - (c) the decision read records come from JA62's tool;
    - (d) the (e^RC − 1) conversion is retired (JA64).
  - **#200's defaults:**
    - (i) the vessels stay LM / LAD / LCx / RCA with JA67's rules;
    - (ii) lesion points stay on grades 1–5;
    - (iii) the footprint is changed (JA66);
    - (iv) old clients are refused at claim (JA67).
  - **JA48.1** is met by `guard.REFERENCE_SHA256`. The ruling's word "PINNED" is read as "pinned in the guard".
  - **JM-0R's `lima.ja20_septal_arc_column_kept`** (pooled share) is labelled "reported; R7 uses the case median".
  - **Seven build defects** were found and confirmed (§1.2); none had yet acted on a real case.
  - **No JM-0 / JM-0R aggregate** was posted by this ruling.

---

## 5. Questions for the lead (each with a recommendation; none is a fork)

**Carried unchanged, as assumptions:** LQ2–LQ12 and LQ19–LQ22, with their recommendations, except that LQ12's
"420" reads 360 (JA69).

### LQ30 — Order of work: what waits for the Round 4 fixes?

- **The facts:**
  - JM-0 does not touch any defect.
  - JM-0R's own code is correct; only its consumer (R9) is wrong.
  - The read-queue and harness defects would act on the first read wave and on decision scoring. Once a wave is
    read, they can only be audited.
- **Options:**
  - (a) run JM-0 and JM-0R now; hold `jm0r_decide.py`'s run until R4-S1–S3 merge; hold the freeze PR and the first
    read wave until the read-queue items (R4-S17–S23) and the harness items (R4-S4–S6) merge;
  - (b) run everything now and patch after;
  - (c) hold JM-0 as well.
- **Recommendation: (a).**

### LQ31 — Blank seal cases checked against a hidden model seed

- **The facts:** JA66 checks the 10 blank seal cases' mitral plane against a model seed that readers never see. The
  reader learns only "pool N mm above the plane", and only on a failed read. The alternative is reader-placed hinge
  points on every blank read: about a minute each, and a reference the reader chooses.
- **Options:**
  - (a) hidden check seed (JA66);
  - (b) reader hinge points;
  - (c) leave blank reads fitted to their own gap (an intrusion under ≈ 9 mm passes; India IG9).
- **Recommendation: (a).** The seed is already the anchoring gap's reference, and a returned read's basal plane is
  a small part of the whole-border ASSD.

### LQ32 — Reference population 360 instead of 420

- **The facts:**
  - The 60 seal-extension cases may still become seal cases (JA6, JA16).
  - Using them costs an ≈ 8 % larger SE on the cut, and an unchanged false-flag rate (India: 1.40 % vs 1.33 %).
  - LQ12's seeds job shrinks slightly (≈ 10 instead of ≈ 12 GPU-h).
- **Options:**
  - (a) 360, as built;
  - (b) 420, which needs a second guard path that JA12 forbids;
  - (c) 360 now, with the unused tail added by a new config version after the seal size is final.
- **Recommendation: (a).**

### LQ33 — Path A will likely ship thinning as a number, not a flag

- **The facts:**
  - With the wall simulated as measured (JA60), the depth is 45 % provisionally.
  - It is 60 % on walls ≤ 5 mm (Hotel E9), which fails JA41's 0.50 gate.
  - JA63 raises the RC by ≈ 20 %, which raises the depth too.
  - Only a measured RC well under 1.0 mm brings thinning back under the gate.
- **Options:**
  - (a) accept, as LQ21 (a): numbers, percentiles and the stated depth;
  - (b) a gate at 0.60;
  - (c) count it against path A in the path choice.
- **Recommendation: (a).** (b) trades specificity for display. (c) is the lead's to weigh with path B's summary,
  once JM-0R reports.

### LQ34 — Pause this path's rounds until JM-0 / JM-0R report?

- **The facts:** after this ruling, nothing on the path can be argued without data (§8). The R4-S items are
  engineering work.
- **Options:**
  - (a) pause: Round 5 opens when JM-0 / JM-0R aggregates are posted;
  - (b) another build-check round when the R4-S items merge;
  - (c) keep iterating.
- **Recommendation: (a)**, with the PM checking each R4-S item against its test spec at merge. Under M2 the PM may
  instead choose (b); in that case Round 5 is a test-by-test check only.

---

## 6. Forking question: **no fork**

The cap would allow one (2 of 4 paths active). Nothing open on this path changes its structure:
- JA60–JA69 fix measurement and code;
- LQ30–LQ34 are timing, reader time, a population count and display.

The one structural question, path A against path B, is still LQ1, answered by the lead's path choice. LQ33 informs
it.

---

## 7. Shipping (`role:swe`; one issue each; label `path:jm-rest-ccta`; cite this ruling and #205)

This list consolidates and replaces Hotel H4-1…H4-13, India SW-1…SW-6 (IG1–IG23) and Lima G1–G27. Shared Stage A
code goes on **`dev`** and is synced to both paths. Items are grouped by module, so each group can go to one
engineer. **"Blocks"** says what must wait for an item.

### Group A — the detectable depth (`src/janusm/calibrate.py`, `experiments/JanusM/fir/jm0r_decide.py`, `jm0r_readout.py`)

- **R4-S1 — S3 takes the measured wall (JA60).** *Blocks R4-S2 and R4-S11.*
  - **Wrong:** `detectable_depth` / `detectable_depths` default `median_mm` to 9.668 mm and treat any median as an
    anchor that `population()` multiplies by the phase factor again.
  - **Correct:**
    - add `population_factor(phase_mix, shape, cv_n)`: deterministic, 200 000 hearts, seed 7;
    - add `measured_median_mm=` (anchor = measured ÷ factor); passing both it and `median_mm` raises;
    - with neither, the anchor is `ED_MEDIAN_MM` (5.7);
    - add a `phase_mix=` argument;
    - record `measured_median_mm`, the anchor and the factor in `inputs`;
    - `CALIBRATE_VERSION` 1.1.0.
  - **Tests:**
    - E7's rows reproduce with `median_mm=9.668`;
    - `detectable_depth(0.088, LIMA_SHAPE, 1.0, seed=31000)` returns 0.45;
    - at `measured_median_mm=6.3` the simulated median is 6.3 ± 1 %;
    - both inputs raise;
    - `population_factor` at Lima's inputs is 1.109 ± 0.002.
- **R4-S2 — R9 as ruled (JA60).** *Blocks running `jm0r_decide.py` on posted aggregates.*
  - **Wrong:**
    - no median is passed (line 386);
    - `PROVISIONAL_DEPTH = 0.35`;
    - S3's refusal prints no NOT DECIDABLE;
    - R3's failure is ignored;
    - the docstring says S3 is unmerged.
  - **Correct:**
    - pass `measured_median_mm=x["thickness_median_mm"]`, and add it to R9's inputs and missing list;
    - `PROVISIONAL_DEPTH = 0.45`;
    - in the `except ValueError` branch, append `cv_n (S3 refused: <reason>)`; the thinning sign shows numbers only,
      and the footer is labelled "provisional";
    - add R3's note to R9's line when R3 fails;
    - fix the docstring; `DECIDE_VERSION` "2".
  - **Tests:**
    - a recording `depth_fn` receives JM-0R's median;
    - a missing median → NOT DECIDABLE;
    - the cv_n = 0 case prints the NOT DECIDABLE line;
    - an R3 failure adds the note;
    - the provisional string reads 45 %;
    - JM-0R's acceptance test (`test_the_decision_script_on_the_synthetic_summary_is_decidable`) uses jittered rows
      and asserts `depth is not None`.
- **R4-S3 — JM-0R's duplicate septal-arc flag (JA69).**
  - **Wrong:** `lima.ja20_septal_arc_column_kept` uses the pooled share, while R7 uses the case median, and nothing
    says which decides.
  - **Correct:** the key is renamed `…_pooled_reported`, with a docstring saying R7 decides on the case median.
  - **Test:** pooled and median shares straddling 0.10; `decision_inputs` follows the median.

### Group B — the harness (`src/janusm/harness.py`, `tests/test_janusm_harness.py`)

- **R4-S4 — JA37's band in the guard's estimator (JA61).** *Blocks the freeze PR.*
  - **Wrong:** `signed_bias` has no ROI, and no function builds the band. On open masks it under-reads by ≈ 24 %.
  - **Correct:**
    - `ja37_band(ref_labels, spacing, border)` per JA61;
    - `signed_bias(…, roi=None)` restricts ΔV and both areas (faces by centroid);
    - `compare(roi="ja37")` builds the band and passes it to `signed_bias`, `signed_bias_pp` and `assd_pp`;
    - `validate_bias_estimator(open_base=True)`;
    - remove the test that asserts `signed_bias` ignores `roi`;
    - write JA37's disclosed real-wall error into the docstring;
    - `HARNESS_VERSION` 1.2.0.
  - **Tests:**
    - India's open-base phantom (two grids, three walls, both borders, ±0.3 / ±0.5 mm) within 0.05 mm with the band;
    - E4's closed shells stay within ±0.01;
    - a change made only within 3 mm of label 4 gives bias 0 ± 0.01;
    - the band excludes every voxel ≤ 3 mm from label 4 and from an open pool face.
  - **If the open-base check cannot pass at 0.05 mm,** `BIAS_GUARD_VALIDATED_MM` falls back to 0.5, and the issue
    says so.
- **R4-S5 — The transfer check (JA37, JA62).**
  - **Wrong:** not built.
  - **Correct:** `transfer_check(rows, *, n_first=20, limit_mm=0.05)` returns:
    - the median |`bias_*` − `bias_pp_*`| per border;
    - `passed`;
    - `bias_guard_mm` (0.3 or 0.5);
    - `n_over_limit`.

    Fewer than 20 rows raises `ValueError`; rows after the 20th are ignored.
  - **Tests:** a median of 0.04 → 0.3; 0.06 → 0.5; 19 rows → error; row 21 ignored.
- **R4-S6 — JA39's tolerance and one voxel ASSD (JA65).**
  - **Wrong:** `PP_ASSD_TOLERANCE_MM[0.5] = 0.03`, compared after rounding. `surface_assd` re-implements
    `segtrain.metrics.surface_distances`.
  - **Correct:** `{0.5: 0.035, 1.0: 0.07}`, compared as `abs(err) <= tol`, with a comment citing E6 (0.032) and Lima
    E7 (0.0322). `surface_assd` calls `segtrain.metrics.surface_distances`.
  - **Tests:** `test_e6_pp_within_ja39_tolerances` without rounding; `surface_assd` equals segtrain on the phantom
    (0.47283).

### Group C — reference population and table (`src/janusm/reference.py`, `report.py`, `features.py`, `geometry.py`, `tools/janusm/build_reference.py`)

- **R4-S7 — JA42 steps 3 and 4 (JA63).** *Blocks the reference population.*
  - **Wrong:**
    - `n_pool = len(alld)` (values, ≤ 60) in the pooled RC and the switch bound;
    - step 4a uses the pooled mean when pooled.
  - **Correct:**
    - `repeatability` receives the case index with each pair;
    - n = distinct cases with ≥ 1 pair;
    - each territory tests its own mean Δ_T against 0.5 × the SD in use;
    - report `n_patients`, `n_values`.
  - **Tests:**
    - 20 patients × 3 territories gives a factor of 1.4606 (χ²₀.₀₂₅,₁₉ = 8.907);
    - rewrite `test_rc_is_the_upper_95_bound_pooled_by_default`;
    - offsets +0.4 (LAD) and −0.4 (LCx) add to LAD and LCx, not RCA;
    - a 14-vs-15 territory boundary.
- **R4-S8 — JA42 step 4b (JA64).** *Blocks the reference population.*
  - **Wrong:**
    - the log branch is dead for signed D;
    - `rc_abs` multiplies by the wall;
    - `report.py` uses level 1.0 for fat.
  - **Correct:**
    - `case_state` carries E_T per read and territory;
    - the relative branch per JA64, only where E_T > 0 for every pair;
    - fat is always on differences;
    - one `rc_floor_mm(rc, territory, E)`, used by both `gate()` (population E) and `report.build` (patient E);
    - delete the (e^RC − 1) conversion and `level = 1.0`.
  - **Tests:**
    - proportional thinning noise switches to "relative", and the floor at E equals RC_rel × E;
    - multiplicative fat noise stays on differences in mm³;
    - the gate and the report produce the same floor for the same E;
    - signed D with ρ > 0.4 but E ≤ 0 stays on differences, with the decision recorded.
- **R4-S9 — JA42 step 1 for fat; no silent fall-back (JA63).**
  - **Wrong:**
    - `fat_territory_volume` sums on the AHA-default territories;
    - `case_state` falls back to AHA silently.
  - **Correct:**
    - `features.case_features` stores fat clusters per patient-map territory as well;
    - fat's D uses them;
    - every fall-back sets `map: "aha_fallback"`, counted in `rc["decisions"]` and the header.
  - **Test:** a fat-bearing segment that changes territory moves D; a forced fall-back is counted.
- **R4-S10 — The gate's wall (JA60).** *Depends on R4-S1.*
  - **Wrong:** `gate()` passes `median_mm=blk["median_level"]`.
  - **Correct:** pass `measured_median_mm=`; hypoattenuation passes `phase_mix={"ED": 1.0}`.
  - **Test:** a recording S3 sees `measured_median_mm` and, for hypoattenuation, the ED-only mix.
- **R4-S11 — Config provenance.**
  - **Wrong:**
    - the config's `geometry_version` and `features_version` are never compared with the running ones;
    - `CALIBRATE_VERSION` is not recorded;
    - the file is written in the locale encoding, while the sha is computed on UTF-8;
    - there is no golden config.
  - **Correct:**
    - `report.build` raises `ReportError` on a version mismatch;
    - `build_config` records `calibrate_version`;
    - write UTF-8 bytes and hash the bytes written;
    - `tests/fixtures/janusm/reference_synth.json` from a 300-heart synthetic population (seed 11), with a
      regeneration flag.
  - **Tests:** a monkeypatched version is refused; the sha matches under `LC_ALL=C`; the golden config is
    byte-identical.
- **R4-S12 — R8 wired (JA43 R8).**
  - **Wrong:** `build_reference.py` has no R8 input, so "shared" is never marked.
  - **Correct:**
    - `--geodesic-shared yes|no`, required with `--run`;
    - `features.case_features` adds the geodesic segment majority (`geometry.territories(method="geodesic")`);
    - `report.build` marks "shared" every segment whose two majorities differ, when the config says so.
  - **Tests:** a one-segment phantom is "shared" only with the flag on; `--run` without it is refused.
- **R4-S13 — Table B grades (JA67).**
  - **Wrong:**
    - `report.build` never reads LM;
    - nothing maps the read form's `cadrads` and `lesionPoints` to the report's input;
    - distal mass prints nothing.
  - **Correct:**
    - `territory_grade()` with LM feeding LAD and LCx, and a `grade_source` note;
    - `grades_from_read_record(rec)`;
    - rows with a lesion point print "distal mass: not computed (report v1)".
  - **Tests:**
    - `{"LM": "4B", "LAD": "0", "LCx": "0", "RCA": "0"}` → LAD and LCx significant, RCA not;
    - a round trip from an export record;
    - the distal-mass label.
- **R4-S14 — The arc-proportional septal column (JA69, #199 (a)).**
  - **Wrong:** the column prints empty while R7 keeps it (its missing-input default is "kept").
  - **Correct:**
    - move `jm0r_readout.arc_segments` into `janusm.geometry.arc_segments`, and JM-0R imports it;
    - `features.case_features` adds the arc wall and arc relative subendocardial HU for segments 2, 3, 8 and 9 (None
      below JM-0R's 0.995 agreement guard);
    - `reference` adds their percentiles;
    - `report` fills `septal_arc_value` there, "—" elsewhere, and omits the column when R7 drops it.
  - **Tests:**
    - at 120° the arc values equal the fixed values (±0.01);
    - at 180° the expected share moves;
    - JM-0R and geometry agree on the phantom;
    - the goldens are regenerated.
- **R4-S15 — Boundary tests (no code change).**
  - Depth 0.50 passes and 0.55 fails (monkeypatched S3).
  - κ with 4 and 5 flagged units; a pass with κ None; κ status "not estimable" when pe = 1.
  - The fat gate with and without an RC.
  - Spearman exactly 0.4.
  - Rule C passes with D ≤ RC → a number.
  - D on the patient map, not AHA.
  - `halves_note` in `test_header_fields`.

### Group D — the read queue (`src/janusm_reads/`, `server/girder_janusm/`, `slicer/JanusMRead/`, `docs/JANUSM-READ-PROTOCOL.md`)

All of group D **blocks the first read wave**.

- **R4-S16 — Mitral check (JA66).**
  - **Wrong:**
    - the footprint is the fitted points' radius, with no margin;
    - blank reads fit the plane to themselves;
    - no plane → a warning (a pass).
  - **Correct:**
    - `populate.py` uploads each blank case's seed to a reader-unreadable folder as `checkSeedFileId`;
    - `check.py` passes `seedFileId or checkSeedFileId`;
    - `downloadSeed` and `readInfo` never touch `checkSeedFileId`;
    - the footprint is per JA66, with `CheckConfig.mitral_footprint_margin_mm = 3.0` and `la_shadow_height_mm = 10.0`;
      outside it, > 3 mm warns;
    - no plane → "could not be checked" (R4-S17's path);
    - the report records the plane's source and radius;
    - fix the docstring.
  - **Tests:**
    - Hotel E10 A and India's ring at 6.2–8.7 mm fail;
    - India's +4 mm and +6 mm blank reads fail with the check seed;
    - the exact phantom read passes;
    - Mongo: a blank case's seed is never served (4xx, `hasSeed: false`), while its report says "fitted to the
      seed";
    - a plane-less read is returned uncounted.
- **R4-S17 — A crash never spends the return (JA68).**
  - **Wrong:** `attempts` counts every submission, so after a crash a genuine failure is accepted and flagged.
  - **Correct:** count `returns` only on a genuine RETURNED, and flag on the next failure once `returns ≥ 1`. Crashes
    and "could not be checked" are counted separately (`crashes`) and reported.
  - **Tests (Mongo):** crash, then a failure → RETURNED, unflagged, with its profile; a further failure → flagged.
- **R4-S18 — Rule 2 as written (JA68).**
  - **Wrong:**
    - `changed_share` divides by seed ∪ read;
    - `adminThirdReads` opens any list;
    - third reads are exported into `reads/`.
  - **Correct:**
    - divide by `(seed > 0).sum()`;
    - `adminThirdReads(wave, cases)` refuses unless the wave is flagged and `cases == third_read_cases(wave,
      seeded)`;
    - `export.py` writes third reads under `third/` with `reference: false`;
    - update protocol doc §7.
  - **Tests:**
    - a read adding < 5 % of the union but ≥ 5 % of the seed is not "following";
    - exactly 5 % is not "following";
    - exactly half the reads does not flag;
    - an arbitrary list, 4 of 5, or 6 names → 400;
    - no `reads/` record is a third read.
- **R4-S19 — Rule 1 pinned (JA68).**
  - **Wrong:**
    - the gap uses case-level means, while the report shows read-level means;
    - the test does not pin the bootstrap.
  - **Correct:** gap from read-level means, bootstrapped by case.
  - **Tests:**
    - recompute the bound with `default_rng(BOOTSTRAP_SEED)`, independent draws, the 0.95 quantile, and assert
      equality;
    - a shared-index draw differs;
    - a case with one `None` ASSD gives `rule1.gap == seedVsReadBlank − seedVsReadSeeded`.
- **R4-S20 — Read form and wire version (JA67).**
  - **Wrong:**
    - every grade is allowed on every vessel;
    - lesion points are not bounds-checked;
    - `PROTOCOL_VERSION = 1`.
  - **Correct:**
    - `read_form_problems` allows LM {0, 1, 2, 4B, 5, N} and LAD / LCx / RCA {0, 1, 2, 3, 4A, 5, N};
    - the error text names N for lesion points;
    - `rest.submit` refuses a point outside the CT's world bounding box;
    - `PROTOCOL_VERSION = 2`;
    - doc §4.4 states the branch attribution;
    - the Slicer module offers only the allowed grades per row.
  - **Tests:**
    - 4B on LAD, and 3 on LM, are refused;
    - a point 1 m away is refused;
    - protocol 1 at `next` → 426 and no read is created; update `test_protocol_refuses_missing_or_old_client`.
- **R4-S21 — Export scope (S5.8).**
  - **Wrong:**
    - no wave field;
    - non-protocol-1 reads are exported;
    - seed offsets are off by default;
    - `seconds` covers only the last attempt;
    - the form is cleared when a returned read is reopened.
  - **Correct:**
    - `JanusMCase.wave`, with `export --wave` (an empty wave is refused);
    - skip and list reads without `border_protocol == 1`;
    - seed offsets on by default;
    - `seconds` summed over attempts, with the Slicer timer kept across reopening;
    - the form restored on reopen.
  - **Tests:** one per change (Mongo and the read module).
- **R4-S22 — Checker boundaries and the septal sign (tests, one code change).**
  - LV–RV contact at ≈ 0.4 % passes and ≈ 0.6 % fails.
  - The above-plane height at 3.0 mm passes and 3.5 mm fails, on a seed-fitted plane.
  - An unmeasurable **endocardial** plateau becomes an error, not a skip (code change in `checker.py` ≈ 516; the
    epicardium may still skip with a warning).
  - `phantom.move_border` gains "septal"; myocardium grown 1 mm into the RV reads +1.0 mm.

### Group E — decision scoring (`tools/janusm/score_decision.py`; new)

- **R4-S23 — The one lead-run decision-scoring tool (JA62).** *Depends on R4-S4 and R4-S5. Blocks decision scoring,
  the seal size, the RC and the reference population.*
  - **Wrong:** nothing computes JA8's d or the transfer check, or produces the decision read records.
  - **Correct:** as JA62:
    - guard first;
    - the list order of `sealed-r1.json`;
    - a stable reader key, never written;
    - one coronary tree for both reads;
    - `compare(roi="ja37")`;
    - `transfer_check` on the first 20;
    - anonymous output with a sha256;
    - the Fir command printed without `--run`; it runs only under Slurm.
  - **Tests:**
    - synthetic pairs on `exact_shift_phantom` give a known d and transfer verdict;
    - order is kept, and a one-read case is skipped, so `reads[:20]` are the first 20 complete cases;
    - third reads are dropped;
    - a seal, extension or JM-0 id is refused before anything is opened;
    - the same coronary array is used for both reads;
    - an id in the output is refused;
    - `build_reference.py` accepts the output, and refuses a mismatched `features_version` or `guard_mm`.

### Conditional

- **R4-S24 — `build_reference.py --model jm0|jm1`**, recorded in the config. **Only if Janus-M 1 is trained**
  (LQ12; India IG21).
- **R4-S25 — The seal scorer takes the frozen seal size**, and refuses the unused extension tail under
  `seal_scoring`. Today `seal_scoring` admits all 120. **Only once JA16's sizing PR exists** (Lima §4).
- **R4-S26 — Snap tool (Round 3 S8),** unchanged: only if R4 fires.

**Not adopted:**
- Hotel H4-8 (hinge points first): superseded by JA66.
- India IG15 (client header): superseded by the wire version.
- India IG23 (the distal-mass definition) and Hotel H4-11 (b) (its spec): deferred without a definition.
- Hotel H4-6's `PINNED` move: JA69 rules the existing pin sufficient.
- Lima's derived three-vessel 4B row: a patient-level category is not a Table B field.

---

## 8. What the next round on this path must settle

**The path waits only on the lead's Job JM-0 / JM-0R and on §7's fixes.** Nothing else is open to argument. If
LQ34 (a) is taken, Round 5 opens when JM-0 / JM-0R aggregates are posted. It then:
1. **Runs `jm0r_decide.py` (after R4-S1, R4-S2 and R4-S10 merge) on the posted aggregates**, and records each R0–R10
   outcome as the plan's value. R9's depth replaces the provisional 45 %.
2. **Checks that each R4-S item merged with the test this ruling names**, test by test, before the freeze PR. Any
   item whose test could not be written as specified comes back with the reason.
3. **Records R4-S4's open-base validation result.** If it failed, the bias guard is 0.5 mm from the freeze PR on
   (JA61).

After that, everything is mechanical and needs no further round:
- the decision reads;
- R4-S23's scoring (d, the transfer check, the seal size, the RC);
- κ / ICC;
- the reference population (360) and the table.

## Path summary for the lead (for #205)

- **Path A** delivers a reproducible rest-CCTA geometry table: 17 segments × layers, with a roll-up per artery beside
  the reader's CAD-RADS 2.0 grade, and LM now feeds LAD and LCx.
- **The build** follows the ruling on most clauses. Round 4 found seven defects; none had touched a real case:
  - a printed depth computed on the wrong wall;
  - an RC computed on the wrong n;
  - a dead log branch;
  - a bias guard that ignores its band;
  - two read-check holes;
  - read-queue bookkeeping.

  They are fixed by 23 issue-ready items (R4-S1 … R4-S23) plus three conditional ones.
- **The page now says 45 %** is the thinning depth it cannot reliably see, until JM-0R measures the wall. On walls
  ≤ 5 mm, thinning is likely a number only (LQ33).
- **Waiting on:** Job JM-0 / JM-0R, the R4-S fixes, and the reads.
- **Against `jm/paired-scar`:** unchanged. Path B adds a scar reference this path never has; everything here is its
  Stage A.

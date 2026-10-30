---
tags: [janus-m, plans, candidate, round4, path-rest-ccta, myocardium, audit, calibration, protocol]
author: Hotel
round: 4
version: 4
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#205
---

# Hotel v4: rest CCTA only. The build is faithful to the ruling except where it prints a number the plan cannot yet see

**The position in one line.** S1–S7 implement JA37–JA48 almost clause for clause, and all 375 Janus-M tests pass.
But four defects would change a printed number or a decision:
- **R9 never passes the measured wall to S3** (E9). It prints 35 % whatever JM-0R measures, while walls inside R3's
  own window need 40–60 %.
- **The provisional 35 % rests on a 9.668 mm wall** that the plan's R3 would reject (E8). Under JA40's own rules
  the provisional figure is **45 %**.
- **F1's pooled RC uses n = territory-pairs (60), not patients (20)**, so it is about 16 % too small. On the log
  scale it is also multiplied by the wrong level.
- **The mitral check misses pool above the plane outside a small disc, and on blank reads it fits the plane to the
  error** (E10).

Each becomes a `role:swe` item below (H4-1 … H4-13). Nothing else needs a new rule.

**Base.** The master plan on this path: [[Hotel v3]] + JA37–JA49 ([[Janus-M Round 3 rest-ccta|Round 3 ruling]]).
Hotel v4 changes no structure and re-argues no threshold. It settles #205 items 1–7.

**Branch state checked.** `jm/rest-ccta` at `8efa84c` merged with `origin/dev` at `dd7864a`, because PR #203 was not
yet merged. That brings in #197–#200 (S1–S7). `pytest tests/test_janusm*.py`: 375 passed. `ruff check .`: clean.

**New evidence this round** (CPU, synthetic only; code in `experiments/JanusM/Hotel/r4/`):
- **E8 / E9** [[Hotel - Lima's 45 percent and Hotel's 35 percent differ by the wall the F1 floor is measured against, and R9 never passes the measured wall]]
- **E10** `e10_mitral_footprint.py`: the shipped JA46 (a) check on `janusm_reads.phantom.heart` (§1.5; no separate note,
  the result is four rows).
- Code audits of S5 (read queue) and S6/S7 (reference, report). Two delegated reviewers did them; I verified every
  finding used here against the code at the line cited.

**Held-out cases.** No case of any kind was opened. E8 and E9 are simulations, and E10 is the queue's own synthetic
phantom. Each script calls `janusm.guard.refuse([])` first by rule, naming nothing. Item 3's seal-extension facts
were taken from `configs/janusm/sealed-r1.json` **by count only**; no id was printed. There is nothing to disclose.

---

## 1. Item 1 — S1–S7 against JA37–JA48, test by test

Key: ✓ = the code matches the ruling and a test enforces it; **gap** = it differs, or nothing tests it. Test files:
H = `test_janusm_harness.py`, R = `test_janusm_jm0r_readout.py`, D = `test_janusm_jm0r_decide.py`,
C = `test_janusm_calibrate.py`, Q = `test_janusm_reads.py`, M = `test_janusm_read_module.py`,
RF = `test_janusm_reference.py`, RP = `test_janusm_report.py`, S = `test_segqueue_server_janusm.py` (Mongo).

### 1.1 S1 — harness (JA37, JA38, JA39, JA45)

| Clause | Test | Status |
|---|---|---|
| JA37 estimator = `signed_bias` (ΔV / mean smoothed MC area) | H::test_ja16_the_estimator_recovers_a_known_half_millimetre_shift, H::test_e4_exact_shells_signed_bias_within_a_hundredth | ✓ |
| JA37 guard 0.3, fallback 0.5 | H::test_ja16_guard_falls_back_when_the_check_fails | ✓ (`BIAS_GUARD_VALIDATED_MM`) |
| JA37 **region**: band around the reference border, excluding ≤ 3 mm from LA and aorta | H::test_compare_restricts_pp_to_the_roi | **gap.** Only pp takes `roi`; `signed_bias`, the guard's estimator, uses the whole masks. The test asserts this (`none["bias_endo"] == full["bias_endo"]`). No function builds the JA37 band. → **H4-1** |
| JA37 **transfer check** (median \|vol − pp\| on the first 20 decision pairs > 0.05 → guard 0.5) | none | **gap.** It is named in the harness docstring (line 30), but no code computes it. No S-item owns the decision-set scorer. → **H4-2** |
| JA38 nominal and realised side by side; results indexed by realised | H::test_rows_are_indexed_by_what_was_realised | ✓ |
| JA38 exact-shift phantom public | H::test_exact_shift_phantom_moves_the_closed_surface_by_the_shift | ✓ |
| JA39 pp ASSD for both terms of d, and the absolute ≤ 1.0 mm guard | none | **gap**, same owner as JA37's transfer check: nothing calls `assd_pp` outside the harness. → **H4-2** |
| JA39 fixture tolerances 0.03 / 0.07 | H::test_e6_pp_within_ja39_tolerances | ✓ as written, but by rounding the error to two decimals (item 6) |
| JA45 `compare()` keys, `run()`, version 1.1.0 | H::test_compare_on_itself_is_all_zero, H::test_harness_version_is_1_1 | ✓ |

### 1.2 S2 — JM-0R v2 (JA44)

| Clause | Test | Status |
|---|---|---|
| Endocardium negated; + = bounded region beyond the half-maximum | R::test_a_moved_endocardium_moves_the_offset_by_that_distance (+1.0) | ✓ |
| Epicardium unchanged | R::test_a_moved_epicardium_reads_plus_when_the_label_reaches_into_the_fat | ✓ |
| `SCRIPT_VERSION` bumped | (constant "2") | ✓ |
| `decision_inputs`: every JA44 key, None when not measured | R::test_decision_inputs_has_every_ja44_key_on_the_synthetic_case, R::test_decision_inputs_marks_what_is_not_measured_as_none | ✓ |
| Acceptance: the JA43 script prints no NOT DECIDABLE on it | R::test_the_decision_script_on_the_synthetic_summary_is_decidable | ✓ |

No gap.

### 1.3 S3 — `janusm.calibrate` (JA40)

| Clause | Test | Status |
|---|---|---|
| Hotel's loop on Lima's sim; mixed 40/40/20, prev 0.1, 4 × 2000 | C::test_e7_primary_rows_reproduce, C::test_e7_every_replicate_reproduces | ✓ |
| ≥ 0.80 mean sensitivity, rounded up to 0.05 | C::test_the_depth_is_on_the_grid_and_rounded_up | ✓ |
| cv_n plain SD; σ_m 0 by default | C::test_inputs_are_explicit_and_the_median_matters | ✓ |
| F1 floor 1.0 mm until RC | (decide's `F1_FLOOR_MM`) | ✓ |
| Page warns above 0.40 | C::test_page_line_fills_the_depth_and_warns_above_forty_percent | ✓ |
| **The wall the floor is measured against** | C::test_inputs_are_explicit_and_the_median_matters | **gap.** The default `median_mm` is 9.668 mm, and it is used as an ED anchor that `population()` inflates by K = 1.109 (E9). → **H4-3** |
| **Provisional print 35 %** | D::test_r9_without_s3_is_not_decidable | **gap**: it should be 45 % (§2). → **H4-3** |

### 1.4 S4 — `jm0r_decide.py` (JA43)

All R0–R10 thresholds match JA43's table (`MIN_USABLE` 36, `AHA_FAIL` 0.10, `HALVES_NOTE` 0.25, `THICK_WINDOW`
4.2–8.0, `SNAP_READS` 0.5, `SNAP_TPR` 0.25, edge 1.5 / 2.0, TPR 0.99–1.15, the fat grid in order, `ARC_DROP` and
`GEO_SHARED` 0.10). Each branch has a D:: test, and R0 stops on 23 cases (D::test_r0_stops_on_23_cases_and_prints_it).
The fallback mappers negate Hotel R2's endocardium (D::test_hotel_fallback_negates_the_endocardium).

| Clause | Status |
|---|---|
| **R9 with JM-0R's cv_n and shape** | **gap.** `decide()` passes cv_n and shape but not `thickness_median_mm`. E9: R9 prints 0.35 for walls of 4.2, 5.0, 6.0, 7.0, 8.0 and 9.668 mm. Passed through, it prints 0.60, 0.60, 0.45, 0.40, 0.40 and 0.35. At 4.2–5.0 mm thinning fails JA41's 0.50 gate, but the shipped script reports 35 %. → **H4-3** |
| R9 when R3 fails | **gap (wording).** R9 prints a depth even when R3 says no thinning flag ships. The outcome should say so. → **H4-3** |
| R9 when S3 refuses cv_n = 0 | ✓ conservative branch, but see item 6(b) |

### 1.5 S5 — read queue to protocol v1 (JA46, JA47)

105 tests pass. ✓ unless listed:
- S5.1 window: M::test_a_case_opens_on_the_border_window_and_800_300_is_only_on_request.
- S5.2 / JA46(c) 0.5 mm median, octants warn: Q::test_the_tolerance_is_half_a_millimetre_and_octants_only_warn.
- S5.4 no 2–4 face: Q::test_labels_2_and_4_never_share_a_face.
- S5.5 offsets in the report.
- S5.7 text: Q::test_protocol_v1_conventions_are_written_down.
- S5.8 export: S::test_export_feeds_the_anchoring_report.
- S5.9 `border_protocol` separate: Q::test_border_protocol_is_its_own_number.
- JA47 rule 1, two-sample bootstrap, 2000 draws, 0.2 mm: Q::test_rule1_is_a_two_sample_bootstrap_with_a_0p2_mm_margin.
- Third reads blank, fresh reader, never in the reference standard: S::test_third_reads_are_blank_by_a_fresh_reader_and_never_reference.

| Clause | Status |
|---|---|
| **JA46 (a) label 2 ≤ 3 mm above the plane** | **gap.** `pool_above_mitral_mm` (`checker.py` ~342–352) looks only within the radius of the fitted points (5.7 mm on the phantom), not over the LA (8 mm). **E10 A:** pool voxels 4–8 mm above the plane just outside that disc report 1.09 mm (seeded) or 2.81 mm (blank) against a true 7.59 mm, and raise no error. The test (Q::test_the_lv_pool_reaches_at_most_3_mm_above_the_seeds_mitral_plane) places its violation only inside the disc. → **H4-7** |
| **JA46 (a) blank reads** | **gap.** With no seed, the plane is fitted to the read's own gap, so an intrusion lifts its own plane. **E10 B:** a 4.6 mm intrusion is caught on the seeded read and passes on the same blank read (1.43 mm). The hinge-point fallback exists, but no client sends hinge points and `check_files` / `checkRead` never pass them. → **H4-8** |
| S5.3 return once | **gap.** `attempts` counts every submission (`models.py` ~195), so a checker crash spends the one return. Then a real failure is accepted and flagged though the reader never saw a check. → **H4-9** |
| **JA47 rule 2 "< 5 % of seed voxels"** | **gap.** `changed_share` (`anchoring.py:80–85`) divides by voxels labelled in seed **or** read. That denominator is ≥ the seed's, so shares read low and waves flag more often than the ruling says (conservative, but not the rule). → **H4-10** |
| JA47 rule 2 draw | Partly. `wave_report` uses only hash-drawn cases, but `adminThirdReads` accepts any seeded case and any number. → **H4-10** |
| JA46 (b) LV–RV ≤ 0.5 % | ✓ code; the test never probes the boundary (test-only, **H4-13**) |
| JA44 sign of the septal (RV) border | untested: `phantom.move_border` has no septal option (test-only, **H4-13**) |
| JA46 (d) read form | ✓ grades and required fields; see item 5 for the CAD-RADS 2.0 rules |

### 1.6 S6 / S7 — reference builder and table writer (JA41, JA42, JA48)

57 tests pass. ✓ unless listed:
- JA41 rule C: RF::test_rule_c_fit_reproduces_calibrate_c.
- JA41 depth ≤ 0.50: RF::test_gate_fails_without_rc_or_above_half.
- JA41 κ / ICC reported, κ not estimable < 5: RF::test_kappa_not_estimable_below_five_and_icc_agrees.
- JA42 step 3 pooling direction: RF::test_rc_uses_a_noisy_territorys_own_sd.
- JA42 step 4 offset: RF::test_rc_adds_a_systematic_reader_offset.
- JA42 step 4 Spearman 0.4: RF::test_rc_switches_to_log_ratios….
- JA48.3 Lima's phrase table with "not graded": RP::test_phrase_table and 3 more.
- JA48.4 no per-segment flag: RP::test_table_a_never_carries_a_flag.
- JA48.5 header: RP::test_header_fields.
- JA48.6 refusals: RF::test_refuses_any_seal_decision_or_jm0_case.
- JA48's six test kinds are all present: golden, phrase, changed config, forbidden word, byte-identical, guard first.

| Clause | Status |
|---|---|
| **JA42 step 4, n = the number of patients** | **gap.** `repeatability()` sets `n_pool = len(alld)`, which is every territory-pair: up to 60 from 20 patients. The χ² factor √((n−1)/χ²₀.₀₂₅,ₙ₋₁) is 1.461 at n = 20 and 1.220 at n = 60, so the pooled RC is about 16 % too small. RF::test_rc_is_the_upper_95_bound_pooled_by_default hard-codes the pair count. Per-territory n_T is per patient already. → **H4-4** |
| **JA42 log scale** | **gap.** `rc_abs(rc, t, level)` turns a log RC into mm as (e^RC − 1) × level. But the gate passes the population's median wall, the report the patient's median wall, and fat passes 1.0, while D is a thinning deviation or a cluster volume. At RC 0.3 the thinning floor becomes ≈ 3.4 mm (the sign is disabled), and fat's floor becomes 0.35 mm³ (F1 vacuous). → **H4-5** (item 4 (d)) |
| JA42 log fallback | Not ruled and untested: "ρ > 0.4 but D not positive → differences". For thinning and hypoattenuation D is signed, so the log branch can fire only for fat. → **H4-5** |
| **JA41 depth gate's wall** | **gap**, the same as R9's: `gate()` passes `median_level` (a measured median) as S3's `median_mm`, which S3 inflates by K. → **H4-3** |
| JA48.1 sha256 "in the guard's PINNED" | Letter only: the pin is `guard.REFERENCE_SHA256`, not a `PINNED` entry. → **H4-6** |
| Depth exactly 0.50; patient vs AHA map in D; `halves_note` in the header test | untested (test-only, **H4-13**) |

---

## 2. Item 2 — Lima E5 45 % against Hotel E7 35 % (E8)

On one seed (31000), with S3, every F1 read on the same hearts:

| | Rule C alone | Hotel F1 1.0 mm | Lima F1 |
|---|---|---|---|
| 9.668 mm, σ 0 (E7) | 0.30 | **0.35** | 0.30 |
| 5.7 mm, σ 0 | 0.30 | **0.45** | 0.35 |
| 5.7 mm, σ 0.5 (Lima's inputs) | 0.40 | 0.50 | **0.40** |

- **The median alone moves E7 from 35 to 45 %**, at every seed tried (31000–34000). The F1 floor is in millimetres
  and rule C is scale-free. Scaling the floor with the wall returns 0.35.
- **Lima's 45 %** = σ_m 0.5 added on top of a cv_n that already holds the model's error (which JA40 excludes; it
  alone lifts rule C 0.30 → 0.40) + a seed step. Lima's own design gives 0.40 at four of five seeds, 0.45 at one.
- **Neither F1 implementation is wrong.**

**Which median is right for JA40:** the measured wall of the population the table is computed on, in the same
thickness definition as the F1 floor, entered as `median_mm = M / K` with K = 1.109. That is JM-0R's
`thickness_median_mm`, later the reference population's. **Until JM-0R: 5.7 mm.**
- 9.668 mm fails the plan's own R3 window (4.2–8.0), so no table that flags thinning can have it.
- JA40 asks for the conservative input.
- E7's "9.668 mm" population actually had a 10.7 mm median wall (K).

**Proposed for the record:** JA40's provisional print becomes **45 %**. That is above 0.40, so the page's warning
sentence prints. It is still within JA41's 0.50 gate.

## 3. Item 3 — reference population, 360 or 420

**360. The 60 seal-extension cases stay out.** I concede Hotel v3's 420.

- **What ships.** `reference.derive_cases` takes train minus seal, decision, JM-0 and seal extension:
  560 − 60 − 40 − 40 − 60 = 360. That is counted on the committed `sealed-r1.json`. Its 7 skipped extension
  entries are already in decision / JM-0, so nothing is counted twice.
- **The guard** refuses extension cases under every purpose except `seal_scoring`.
- **Why they must stay out.** JA6 lets the seal grow only from the extension, and JA16 sizes it at 60 / 80 / 100 /
  120 after the first 20 decision reads. Until that sizing is committed, any extension case may become a seal case.
  Fitting the reference constants (rule C cut, percentiles, cv_n) on them would fit the table on cases later scored
  once. That breaks JA48.6.
- **What 420 would buy.** Little:

  | | 360 | 420 |
  |---|---|---|
  | Hearts above p95 | 18 | 21 |
  | SE of a 5 % share | 1.15 pp | 1.06 pp |
  | Rule C mirror null, z values | 5,760 | 6,720 |

  The cut's SE improves ≈ 8 %.
- **If the lead wants the unused tail later,** only the following is safe, and it is not worth building now: after
  the JA16 sizing PR, pin `extension_released = seal_extension[seal_size − 60:]`; the guard stops refusing exactly
  those cases under `any`; then `derive_cases` adds them.

## 4. Item 4 — #199's deferrals

**(a) The arc-proportional septal column.**
- JA20 and R7 keep the column unless < 10 % of mass changes segment, and keep it when the input is missing. It is
  needed.
- JM-0R already implements the sectors (`jm0r_readout.arc_segments`). → **H4-11 (a):**
  - move that function into `janusm.geometry.arc_segments` as the one implementation, imported by JM-0R;
  - `features` adds arc-sector wall and subendocardial HU for segments 2, 3, 8, 9;
  - the report fills `septal_arc_value` there and "—" elsewhere.
  - Tests: at a 120° arc the arc values equal the fixed values (±0.01); at 180° mass moves between 2/3 and 1/4;
    JM-0R and geometry agree on the phantom.

**(b) Mass distal to a lesion point.**
- Defer it until the decision reads exist; it stays labelled unvalidated. The lesion point is optional (JA46 (d)),
  and no ruling makes this column part of the table.
- The spec, so it is ready → **H4-11 (b):**
  - `geometry.distal_mass(labels, coronary, affine, vessel, point_mm, radius_mm=2.0)`;
  - snap the point to the vessel (> 5 mm → "point not on vessel");
  - cut a sphere from the 26-connected vessel graph; distal = disconnected from the root (nearest the LM for
    LAD / LCx; nearest the aorta for the RCA, else "not computed");
  - mass = myocardium whose nearest territory seed is distal × 1.05 g/ml.
  - Tests: a Y tree gives the branch's Voronoi mass; a root point gives the whole territory.

**(c) Who produces the anonymous decision read records.**
- Nobody yet: the builder documents the format, and no producer exists.
- The producer is the same piece that the decision-set scorer H4-2 needs, and the same Fir job → **H4-12:**
  `tools/janusm/decision_read_features.py`. It:
  1. calls `guard.refuse(decision, purpose="decision_scoring")` and refuses any seal, extension or JM-0 name before
     opening anything;
  2. walks the decision list in draw order, keeping cases with two accepted `border_protocol: 1` reads;
  3. runs `features.case_features` per read;
  4. writes `{features_version, guard_mm, reads: [...]}` with no ids.
- The builder refuses a mismatched `guard_mm` or `features_version`.
- Tests: draw order; a one-read case is skipped, so `reads[:20]` are the first 20 complete cases; `assert_anonymous`;
  a seal name is refused before any read.
- It is a Fir command for the lead, never run here.

**(d) The log-scale conversion (e^RC − 1) × level.**
- **The algebra.** If |ln(D₁/D₂)| ≤ RC, then from a level L:
  - the other read lies within L(e^RC − 1) above;
  - or L(1 − e^−RC) below;
  - or 2m·tanh(RC/2) about the pair mean m.
- At RC 0.3 these are 0.350 / 0.259 / 0.298 × L. **(e^RC − 1) is the most conservative, so keep it.**
- **The level is the error.** It must be the level of D itself, not the wall. → **H4-5:**
  - store `level_T` = the median pair mean of D per territory beside each log-scale RC;
  - floor = `level_T` × (e^RC − 1), the same in the gate and the report;
  - the log branch applies only where D > 0 throughout (in practice fat); otherwise differences, with the decision
    string recorded.
- Applying the RC at a case's own D would be no floor at all: D > D(e^RC − 1) holds whenever RC < ln 2.

## 5. Item 5 — #200's defaults

| Default | Verdict | Change |
|---|---|---|
| Vessels LM / LAD / LCx / RCA | **Keep**, with CAD-RADS 2.0's own constraints. 4B is a patient-level category (LM ≥ 50 % or three-vessel ≥ 70 %), so per vessel it is valid only on the LM. On the LM any ≥ 50 % stenosis is 4B, so 3 and 4A are not LM grades. | **H4-6 (form):** `read_form_problems` refuses 4B on LAD / LCx / RCA and 3 / 4A on LM. Doc §4.4 states the branches: diagonals → LAD; OM and ramus → LCx; PDA / PLB → the dominant artery |
| Lesion points only on grades 1–5 | **Keep.** Grade 0 has no lesion, and N has none established. | The error text names N as well |
| Mitral check over the plane's own footprint | **Change.** The footprint is the fitted points' disc, smaller than the LA (E10 A). Some limit is right, because the LVOT under the aortic valve must stay exempt. | **H4-7:** footprint radius = max(fit radius, in-plane extent of label-4 voxels 0–10 mm above the plane); outside it, > 3 mm is a warning |
| JanusMRead 0.1.0 refused at submit | **Change to refuse at claim.** A 0.1.0 reader can claim a case and draw a whole read on 800 / 300, then cannot submit it, and the slot stays held. | **H4-6 (client):** bump the wire `PROTOCOL_VERSION` to 2 (S5.9 keeps `border_protocol` separate), so `nextRead` returns 426 for old clients |

## 6. Item 6 — #198's notes

**(a) JA39's "0.03 mm" is E6's 0.032.**
- The test passes by rounding the error to two decimals, which is a strict bound of < 0.035.
- **Restate the tolerance as 0.035 mm up to 0.5 mm** (E6's worst 0.032, rounded up), compare without rounding, and
  keep 0.07 at 1.0 mm. → **H4-13**
- No decision moves: pp scores d against a 0.25 mm margin, and 0.005 mm is 2 % of it.

**(b) cv_n = 0 is refused, so R9 prints the provisional 35 %.**
- Refusing is right: with no normal variation rule C has no scale.
- But a JM-0R cv_n of exactly 0 is a measurement defect, not a small number. R9 should:
  - print `NOT DECIDABLE: cv_n (0: JM-0R defect)`;
  - take the conservative branch: the provisional 45 %, and no thinning flag until JM-0R is rerun.
- → **H4-3**

## 7. Item 7 — JM-0 / JM-0R aggregates

**None have been posted** (checked: issue #205 has no comments, and no `summary.json` exists on the branch or in
any issue). R0–R10 cannot be recorded this round.
- When they are posted, run `python experiments/JanusM/fir/jm0r_decide.py --jm0r summary.json --out decisions.json`
  **after H4-3 merges**. Otherwise R9 reports 35 % whatever the wall.
- If it must run before H4-3, read R9 from `e9_r9_median.py`'s method with the posted `thickness_median_mm`.

---

## 8. `role:swe` items for the PM (one issue each; label `path:jm-rest-ccta`; shared Stage A code on `dev`)

Ordered by what they change. H4-3, H4-4, H4-5 and H4-7 change a printed number or a decision; the rest are fidelity
and tests.

1. **H4-3 — The wall in the detectable depth (S3, S4, S6).**
   - `calibrate`:
     - add `wall_median_mm` (the measured median), converted internally to `median_mm = wall / K`;
     - K is computed by `population()` at depth 0 on the run's seed (E9: 1.109 for Lima's shape and mix), and
       reported;
     - the default becomes `ED_MEDIAN_MM` (5.7);
     - the E7 reproduction tests pass `median_mm=9.668` explicitly.
   - `jm0r_decide.decide`:
     - R9 passes `x["thickness_median_mm"]`; a missing median → NOT DECIDABLE and the provisional print;
     - `PROVISIONAL_DEPTH = 0.45`;
     - if R3 fails, R9's outcome adds "no thinning flag ships (R3)";
     - cv_n == 0 → NOT DECIDABLE (6 (b)).
   - `reference.gate`: pass `wall_median_mm=blk["median_level"]`.
   - Tests:
     - E9's table at seed 20261030: 6.0 → 0.45, 4.2 → 0.60;
     - R9 inputs include the median;
     - the provisional string reads 45 %.
2. **H4-4 — Pooled RC n = patients (S6).**
   - `reference.repeatability` takes the case index with each pair;
   - `n_pool` = distinct cases with ≥ 1 pair; report `n` and `n_pairs`.
   - Test: 20 patients × 3 territories gives factor 1.4606 (χ²₀.₀₂₅,₁₉ = 8.907); fix
     RF::test_rc_is_the_upper_95_bound_pooled_by_default.
3. **H4-5 — Log-scale level (S6, S7).**
   - `repeatability` stores `territory[t]["level"]` (median pair mean of D) when `scale == "log"`;
   - `rc_abs(rc, t)` uses it, and the callers in `reference.gate` and `report` drop their own level;
   - the log branch only where D > 0 throughout, with the fallback decision tested.
   - Tests: gate floor == report floor; fat floor scales with the mm³ level; signed D with ρ > 0.4 stays on
     differences.
4. **H4-1 — JA37's region (S1).**
   - `harness.ja37_roi(ref_labels, spacing, aorta=None)`: a band ±3 mm around the reference border, minus voxels
     ≤ 3 mm from label 4 (LA) and from the aorta mask;
   - `signed_bias(ref, test, spacing, roi=None)` restricts ΔV and both areas to the ROI.
   - Test: on `phantom()` with a basal-only change (inside 3 mm of the LA), bias with the ROI ≈ 0 and without it
     ≠ 0; exact shells unchanged with a full ROI.
5. **H4-2 — The decision-set scorer (JA8 / JA37 / JA39; owned by no S-item).**
   - `janusm.score.decision_pairs(pairs)` computes, per pair:
     - d = pp(model, read) − pp(read, read);
     - the absolute pp ASSD ≤ 1.0 mm guard;
     - the `signed_bias` guard in the H4-1 ROI;
     - `signed_bias_pp`, with the transfer check (median |vol − pp| over the first 20 pairs > 0.05 → guard 0.5;
       pairs > 0.05 listed);
     - the voxel ASSD reported beside.
   - It reads only guard-passed decision reads, through H4-12's producer.
   - Tests on `exact_shift_phantom` pairs with a known d.
6. **H4-7 — Mitral footprint (S5).** `checker.mitral_plane`'s radius = max(fit radius, in-plane extent of label 4 at
   0–10 mm height), with `CheckConfig.la_shadow_height_mm = 10`; outside it, > 3 mm warns. Fix the docstring
   "(plus the gap)". Test: E10 A on `phantom.heart(mitral_gap_mm=2.0)` raises the mitral error.
7. **H4-8 — Hinge points reachable (S5).**
   - `ReadSubmission.hingePoints` (RAS mm, ≥ 3), stored on the read and passed by `checkRead` and `check_files`.
   - **On a blank read, the plane comes from hinge points when given, before the read's own gap.** This changes
     JA46 (a)'s order for blank reads only, so it is for the judge (E10 B).
   - Tests: E10 B on a blank read with hinges is refused; a gap-less read with hinges reports source "hinge points".
8. **H4-9 — One real return (S5).** Count `returns` only on a non-crash RETURNED, and flag at `returns ≥ 1` on the
   next failure. Test: crash, then failure → RETURNED, not flagged.
9. **H4-10 — Rule 2 as written (S5).**
   - `changed_share` divides by `(seed > 0).sum()`.
   - `adminThirdReads` refuses more than 5 cases per wave, and names not equal to `third_read_cases(wave, seeded)`.
   - Tests: 4 % extra voxels reads 0.04; exactly 5 % is not "following"; exactly half the reads does not flag;
     6 names are refused.
10. **H4-6 — Small fidelity (S5, S6).**
    - Read-form CAD-RADS 2.0 rules (item 5).
    - Wire `PROTOCOL_VERSION` 2 (old clients refused at claim).
    - The reference sha256 kept in `guard.PINNED` (`REFERENCE_SHA256 = PINNED.get(...)`).
11. **H4-11 — #199 (a) now, (b) when the decision reads exist** (item 4).
12. **H4-12 — Decision read producer** (item 4 (c); a Fir command for the lead).
13. **H4-13 — Tests only.**
    - JA39's 0.035 mm stated plainly.
    - The septal-border sign (+1.0 for myocardium grown 1 mm into the RV; `phantom.move_border` gains "septal").
    - LV–RV contact at 0.4 % passes and 0.6 % fails.
    - Depth gate 0.50 passes and 0.55 fails.
    - D on the patient map, not AHA.
    - `halves_note` in RP::test_header_fields.

## 9. Lead questions, carried as stated assumptions

LQ2–LQ12 and LQ19–LQ22 with the Round 3 recommendations. One addition for the judge, not the lead:
- **H4-8's order change.** For blank reads, hinge points come before the read's own gap. It is a protocol detail
  inside JA46 (a), with E10 as evidence.

The provisional print moving from 35 to 45 % (§2) is an amendment to JA40's number, not a new question. LQ21's
"no flag at all" becomes likelier on thin walls (E9: 0.60 at ≤ 5 mm). Its recommendation (a) stands.

## 10. What would change this plan

- **JM-0R's `thickness_median_mm`:**
  - ≥ 7 mm brings the depth back to 0.35–0.40;
  - ≤ 5 mm makes thinning a number only at F1 1.0 mm.
- **A measured RC well below 1.0 mm** would lower the depth for any wall (E8: the floor matters only as a share of
  the wall).
- **If the judge keeps blank reads fitted to their own gap,** H4-8 reduces to wiring the fallback, and blank-read
  intrusions stay uncaught.

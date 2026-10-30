---
tags: [janus-m, plans, candidate, round4, rest-ccta, myocardium, audit, calibration, specification]
author: Lima
round: 4
version: 3
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#205
---

# Lima v3: the shipped Stage A follows the ruling almost everywhere, but the depth is simulated on the wrong wall, and the pooled RC on the wrong n

**Path:** `jm/rest-ccta` (LQ1 option A). **Base:** the plan in force, [[Hotel v3]] + JA37–JA49 (Round 3 ruling).
Lima v3 proposes no change of structure. It checks the build (ruling §8 item 3), explains the 45 % / 35 % gap (§8
item 2), and settles #205 items 3–7.

## 0. In one paragraph

S1–S7 are built, and **all 375 Janus-M tests pass** on `jm/rest-ccta` + `dev` (`pytest tests/test_janusm_*.py`). Read
clause by clause against JA37–JA48, the code matches the ruling except in these places (§1, §2):

- **Two errors, both lenient:**
  1. **The detectable depth is simulated on the wrong wall.**
     - `janusm.calibrate` defaults to 9.668 mm. R9 never passes JM-0R's median, and S6 passes the population median
       as the anchor that the phase mix multiplies again.
     - The 9.668 mm median fails the plan's own R3 window (E6).
  2. **The pooled RC uses the number of differences (≤ 60) as n, not the number of patients (20).** JA42 step 4 says
     patients. The pooled RC comes out ≈ 16 % too small.
- **One rule that cannot fire:** JA42's log-ratio rule never applies to thinning or hypoattenuation, because their D
  is signed. For fat, if it did apply, it converts at a level of 1 mm³.
- **Two pieces of JA37 with no code and no owner:** the vol–pp transfer check and the scoring band.
- **A set of read-queue holes:**
  - a blank read with no fittable mitral plane passes;
  - a crashed check uses up the one return;
  - the third-read draw is not verified;
  - Rule 2's share is over seed ∪ read, not over the seed;
  - JanusMRead 0.1.0 is refused only at submit, after the reader has drawn the whole case.

**Item 2 (E6).** The 45 % / 35 % gap is the F1 floor read against two different walls: 1.0 mm is 10 % of 9.7 mm and
18 % of 5.7 mm. On one seed the median alone moves JA40's depth from 0.35 to 0.45. E5's own settings on JA40's design
give 0.40, and E5's printed 45 % was a tail seed (2 of 20). **The right median is JM-0R's measured
`thickness_median_mm`, converted to the anchor; until then 5.7 mm, which gives 45 %.** JA40's provisional print
should be **45 %**.

**Other items:**
- **Item 3: 360,** not 420.
- **Item 4:**
  - build the septal-arc column;
  - leave distal mass deferred;
  - a new lead-run tool produces the decision read records;
  - (e^RC − 1)·L is conservative for deficits, but is applied to the wrong quantity.
- **Item 5:** keep LM/LAD/LCx/RCA (with an LM rule and a per-vessel 4B rule); keep points on grades 1–5; widen and
  fix the mitral footprint; refuse 0.1.0 before claim.
- **Item 6:** JA39 is enforced at 0.035 mm in effect, so say so; refusing cv_n = 0 should be NOT DECIDABLE, not a
  silent provisional 35 %.
- **Item 7:** no JM-0 / JM-0R aggregates are posted (checked 2026-10-30), so R0–R10 have no value yet.

**New evidence** (CPU; `experiments/JanusM/Lima/r4/`):
- **E6** [[Lima - E5's 45 percent and E7's 35 percent differ because F1's 1 mm floor is read against a 9.7 mm wall in one and a 5.7 mm wall in the other]];
- **E7** [[Lima - The shipped point-to-plane ASSD meets JA39 at 0.035 mm, not 0.03, and a strict 0.03 fails two conditions]].

No case or image was opened (§9).

---

## 1. Item 1: S1–S7 against JA37–JA48, test by test

Verdicts: **✓** matches; **≈** matches with a gap that does not change a decision today; **✗** does not match the
ruling. G-numbers point to §2. File paths are on `jm/rest-ccta` after #203.

### JA37: signed bias (S1)

| Clause | Enforcing test | Code | Verdict |
|---|---|---|---|
| The estimator is `harness.signed_bias` (ΔV ÷ mean smoothed marching-cubes area) | `test_janusm_harness.py::test_signed_bias_is_signed_outward_and_antisymmetric`, `::test_e4_exact_shells_signed_bias_within_a_hundredth` | `harness.py:293` | ✓ |
| `validate_bias_estimator()` passes at 0.05 mm and returns the 0.3 mm guard; falls back to 0.5 | `::test_ja16_the_estimator_recovers_a_known_half_millimetre_shift`, `::test_ja16_guard_falls_back_when_the_check_fails` | `harness.py:600–678` | ✓ |
| Round 2 estimators never used for a guard | `::test_the_round2_estimator_under_reads_where_this_one_does_not` (documents it) | none of them is imported by S1–S7 | ✓ |
| **Transfer check:** vol vs pp on the first 20 decision double reads; median \|vol − pp\| > 0.05 → guard 0.5 before any seal read; list the cases | **none** | **not built anywhere**: `signed_bias_pp` has no caller outside `harness.py` | **✗ (G4)** |
| **Region:** a band around the reference read's border, excluding ≤ 3 mm from the LA and aorta | `::test_compare_restricts_pp_to_the_roi` (an ROI argument exists) | `compare(roi=…)` accepts a mask; **nothing builds the band** | **✗ (G4)** |

### JA38: nominal vs exact shifts (S1)

| Clause | Test | Code | Verdict |
|---|---|---|---|
| `run()` records nominal and realised bias side by side | `::test_rows_are_indexed_by_what_was_realised` | `harness.py:425–466` | ✓ |
| Fixtures use exact analytic shifts; a public exact-shift phantom | `::test_exact_shift_phantom_moves_the_closed_surface_by_the_shift` | `exact_shift_phantom`, `harness.py:567` | ✓ |
| Round 2's "0.5 mm" rows realised ≈ 0.64 mm; ≈ 1 mm of thickness per mm of bias stands | `::test_a_constant_model_bias_costs_about_its_own_size_in_thickness` | — | ✓ |

### JA39: point-to-plane ASSD for JA8 (S1)

| Clause | Test | Code | Verdict |
|---|---|---|---|
| pp ASSD and pp bias, one implementation | `::test_pp_is_zero_on_itself_antisymmetric_and_nan_when_empty`, `::test_pp_does_not_depend_on_the_padding_around_the_heart` | `assd_pp`, `signed_bias_pp`, `harness.py:237–273` | ✓ |
| Within 0.03 mm up to 0.5 mm and 0.07 mm at 1.0 mm, on both grids, oblique and rough walls | `::test_e6_pp_within_ja39_tolerances` (slow), `::test_e6_pp_on_a_smooth_random_field` | `PP_ASSD_TOLERANCE_MM = {0.5: 0.03, 1.0: 0.07}`. The test compares `round(err, 2)`, so 0.035 is what is enforced. E7: worst 0.0322, two strict failures | **≈ (G3; item 6)** |
| JA8's d (both terms) and the ≤ 1.0 mm guard use pp; voxel ASSD reported beside it | `compare()` returns both (`::test_compare_on_itself_is_all_zero`) | **no decision scorer computes d yet** | ≈ (G4; due before the decision reads are scored) |
| Read checks and anchoring keep the voxel ASSD | `test_janusm_reads.py::test_rule1_*` | `anchoring.py` uses voxel ASSD | ✓ |
| Thickness unchanged (equal thickness, median over 1–16) | `::test_thickness_error_is_the_median_over_segments_1_to_16` | `thickness_error`, `harness.py:337` | ✓ |

### JA40: the detectable depth (S3)

| Clause | Test | Code | Verdict |
|---|---|---|---|
| One function: Lima's simulation with Hotel's loop | `test_janusm_calibrate.py::test_e7_primary_rows_reproduce`, `::test_e7_every_replicate_reproduces`, `::test_e7_lookup_rows_reproduce` | `calibrate.py` | ✓ |
| Settings: mixed 40 / 40 / 20; prevalence 0.1; 4 × 2000; first depth with mean sensitivity ≥ 0.80, rounded up to 0.05 | `::test_the_depth_is_on_the_grid_and_rounded_up`, `::test_false_flags_stay_under_the_calibration_target` | constants `calibrate.py:63–76` | ✓ |
| cv_n is the plain SD; robust log SD reported only | `test_janusm_jm0r_decide.py::test_r9_calls_detectable_depth_with_cv_n_shape_and_the_f1_floor` | R9 passes `cv_n` and lists `cv_n_robust_log` as an input only | ✓ |
| No added error when cv_n is on the table's model | R9 default `sig_m=0.0` | `jm0r_decide.py:386` | ✓ |
| F1 floor 1.0 mm until the reads exist | `F1_FLOOR_MM = 1.0` | — | ✓ |
| **The F1 floor (mm) is simulated on the table's wall** (implied: JA40 "conservative inputs") | `::test_inputs_are_explicit_and_the_median_matters` shows that the median moves the depth, but **nothing ties it to the measured median** | default `median_mm = LIMA_MEDIAN_MM = 9.668` (`calibrate.py:242`). **R9 never passes `thickness_median_mm`** (`jm0r_decide.py:386`). S6 passes the measured `median_level` **as the anchor**, which `population` multiplies by 1.109 (`reference.py:528`) | **✗ (G1)** |
| Printed provisionally: 35 % | `PROVISIONAL_DEPTH = 0.35` | `jm0r_decide.py:88` | ✓ as ruled. E6 says it should be 45 % (§3) |
| Above 0.40 the page says so | `test_janusm_calibrate.py::test_page_line_fills_the_depth_and_warns_above_forty_percent` | `page_line` | ✓ |

### JA41: the flag gate (S6, S7)

| Clause | Test | Code | Verdict |
|---|---|---|---|
| A flag needs rule C ∧ F1 ∧ depth ≤ 0.50 (inclusive) | `test_janusm_report.py::test_thinned_lad_is_flagged_only_in_its_territory`, `test_janusm_reference.py::test_gate_fails_without_rc_or_above_half` | `reference.py:531` (`<=`), `report.py:195–203` | ≈: right code; **no test at 0.50 or for "rule C passes, D ≤ RC"** (G21) |
| Depth by JA40 at the population's cv_n, shape and measured RC | `::test_gate_equals_s3_detectable_depth_at_the_same_seed` | largest territory RC, conservative (`reference.py:526`) | ✓, apart from the median (G1) |
| κ and ICC (two-rater, absolute agreement) reported; κ "not estimable" when either read has < 5 flagged units; neither gates | `::test_kappa_not_estimable_below_five_and_icc_agrees` | `reference.py:457–503`; `min(sum) < 5` | ✓; **no 4-vs-5 boundary test, and none that κ = None still passes** (G21). Edge: when every unit is flagged in both reads, κ is None but its status says "estimated" (G21) |
| Fat: F1 plus κ reported, no depth gate | none | `reference.py:517–521` | ≈ (G21) |

### JA42: F1's repeatability coefficient (S6)

| Step | Test | Code | Verdict |
|---|---|---|---|
| 1. Patient-specific Euclidean map; segments from each read's own frame | none | thinning and hypoattenuation default to `"patient"`, with a **silent** fallback to AHA (`reference.py:245–251`); **fat D uses the AHA-default territory** (`reference.py:211–218`) | **✗ for fat (G16)** |
| 2. D = Hotel's shape-corrected deviation; fat D = core cluster volume | indirect | `calibrate.f1_deviation` | ✓ |
| 3. Per territory if n_T ≥ 15, else pooled; pooled unless SD_T > the pooled 95 % χ² bound | `::test_rc_uses_a_noisy_territorys_own_sd` | `RC_PER_TERRITORY_MIN_N = 15` | ✓; no 14-vs-15 test (G21) |
| 4. RC = 1.96·SD·√((n − 1)/χ²₀.₀₂₅,ₙ₋₁), **n = patients** | `::test_rc_is_the_upper_95_bound_pooled_by_default` **asserts n = 60** | `n_pool = len(alld)`, the count of differences (`reference.py:410`). The factor is 1.220 at 60 and 1.461 at 20, so the pooled RC is 16 % low; the three territories' differences within a patient correlate 0.64–0.91 on synthetic reads | **✗ (G13)** |
| 4a. Add \|mean Δ\| if > 0.5·SD_T | `::test_rc_adds_a_systematic_reader_offset` | while the RC is pooled, the **pooled** mean is tested, so offsets of +0.4 in LAD and −0.4 in LCx cancel and nothing is added | **✗ (G14)** |
| 4b. Spearman ρ(\|Δ\|, mean D) > 0.4 → log ratios | `::test_rc_switches_to_log_ratios…`, on positive levels only | needs every D > 0. Thinning and hypoattenuation D are signed, so **the branch never runs**; fat would take it at level 1.0 (`report.py:198`) | **✗ (G15; item 4d)** |
| 5. Report the point, bound, n and every decision | partial | the map decision is not recorded; `n` is differences | ≈ (G13, G16) |

### JA43: one decision procedure (S4)

| Rule | Test | Verdict |
|---|---|---|
| Script moved beside JM-0R; reads `decision_inputs` or the JA23 fallback; Lima and India mappers ported; Hotel R2's endocardium negated | `test_janusm_jm0r_decide.py::test_from_jm0r_reads_the_block_or_the_bare_block`, `::test_hotel_fallback_negates_the_endocardium`, `::test_lima_fallback`, `::test_merge_fallback_order_and_sources` | ✓ |
| Missing → NOT DECIDABLE, conservative branch, no default | `::test_r*_missing*` (R0–R9) | ✓, except R9 when S3 refuses its inputs: no NOT DECIDABLE line, and the provisional figure is printed (G2; item 6b) |
| R0 ≥ 36 of 40; stops on 23 | `::test_r0_usable_cases`, `::test_r0_stops_on_23_cases_and_prints_it` | ✓ |
| R1 > 10 % → frame fix | `::test_r1_aha_frame`, `::test_r1_missing_takes_the_fix` | ✓ |
| R2 > 25 % → header note; never halves everywhere | `::test_r2_halves` | ✓ |
| R3 median in 4.2–8.0 mm → F3 | `::test_r3_thickness_definition` | ✓. R9 ignores R3's input (G1) |
| R4 snap > 0.5; TPR snap > 0.25; guard forecast > 0.3, printed only | `::test_r4_seed_offsets` | ✓ |
| R5 rest TPR branches | `::test_r5_rest_tpr`, `::test_r5_the_1mm_guard_stands_in_only_where_it_is_the_adaptive_band` | ✓ |
| R6 grid order, then patient rule, else number only | `::test_r6_the_least_strict_grid_cell`, `::test_r6_patient_rule_then_number_only`, `::test_r6_missing_grid_or_cell_is_never_defaulted` | ✓ |
| R7 < 10 % → dropped; missing → kept | `::test_r7_*` | ✓ |
| R8 Euclidean primary; ≥ 10 % → "shared" | `::test_r8_*` | ✓ in the script; **S6's CLI has no R8 input, so `geodesic_shared` is always False** (G24) |
| R9 detectable depth | `::test_r9_*` | **✗ (G1, G2)** |
| R10 reported only | `::test_r10_reported_only` | ✓ |
| One line per rule; `decisions.json` | `::test_main_prints_one_line_per_rule_and_writes_decisions_json` | ✓. The docstring still says S3 is unmerged (G2) |

### JA44: JM-0R canonical sign and output contract (S2)

| Clause | Test | Verdict |
|---|---|---|
| Endocardium negated; moved endocardium reads +1.0 mm; epicardium unchanged | `test_janusm_jm0r_readout.py::test_a_moved_endocardium_moves_the_offset_by_that_distance`, `::test_a_moved_epicardium_reads_plus_when_the_label_reaches_into_the_fat` | ✓ |
| `SCRIPT_VERSION` bumped | `::test_decision_inputs_has_every_ja44_key_on_the_synthetic_case` asserts "2" | ✓ |
| Flat `decision_inputs`, every JA44 key, aggregates only, None not default | `::test_decision_inputs_has_every_ja44_key_…`, `::test_decision_inputs_marks_what_is_not_measured_as_none` | ✓ |
| Acceptance: the JA43 script on JM-0R's synthetic output prints no NOT DECIDABLE | `::test_the_decision_script_on_the_synthetic_summary_is_decidable` (S3 now merged, so it asserts none) | ✓ |
| Canonical sign in the checker, export and table header | checker `test_janusm_reads.py::test_a_border_off_by_more_than_half_a_millimetre_fails_in_the_canonical_sign`; export writes `offsetSign`; the table header takes the caller's offsets unchecked | ≈ (G17 covers the header) |

One note, no gap: JM-0R's own `lima.ja20_septal_arc_column_kept` uses the pooled mass share, while
`decision_inputs.septal_arc_mass_changed_median` and R7 use the case median, as JA43 says. Only R7 decides. The pooled
flag is a reported duplicate that could disagree, and should be labelled "reported, not R7".

### JA45: harness API (S1)

| Clause | Test | Verdict |
|---|---|---|
| `signed_bias`, `signed_bias_pp`, `assd_pp`, `surface_assd`, `segment_thickness`, `thickness_error`, public exact-shift phantom | the tests above | ✓ |
| `compare()` returns `assd_pp_*`, `assd_voxel_*`, `bias_*`, `bias_pp_*` per border | `::test_compare_on_itself_is_all_zero` | ✓ |
| `HARNESS_VERSION` 1.1.0 | `::test_harness_version_is_1_1` | ✓ |
| E6 conditions with JA39's tolerances; E4 shells ±0.01 mm to 1 mm | `::test_e6_pp_within_ja39_tolerances`, `::test_e4_exact_shells_signed_bias_within_a_hundredth` | ≈ (G3) |

### JA46: border protocol v1 (S5)

| Clause | Test | Code | Verdict |
|---|---|---|---|
| (a) Mitral plane: label-2 voxels within 3 mm of label 4 (the gap); in the seed, its 2–4 interface; else annular hinge points | `test_janusm_reads.py::test_the_mitral_gap_phantom_passes_and_its_plane_is_fitted`, `::test_the_lv_pool_reaches_at_most_3_mm_above_the_seeds_mitral_plane` | `checker.py:292–339` | **✗ (G6, G7):** hinge points are accepted by `mitral_plane` but **nothing passes them** (`check_files`, `server/girder_janusm/check.py:75`, Slicer). A blank read with no fittable plane therefore passes, with a warning only (probe: a 4 mm gap). The footprint is the fitted points' own radius, with no margin, and on a blank read the reader's own label-2 voxels refit and enlarge the plane they are judged against |
| "Labels 2 and 4 never share a face" | `::test_labels_2_and_4_never_share_a_face` | `checker.py:391–396` | ✓ |
| (b) LV–RV contact ≤ 0.5 % | `::test_lv_rv_contact_stays_at_half_a_percent` (constant and the truth phantom only) | `checker.py:381–388`; a probe at 0.09 / 0.22 / 0.63 / 1.04 % gave pass / pass / fail / fail | ≈ (G12: no boundary test) |
| (c) Octants > 1.0 mm warn only; the whole-border median ≤ 0.5 mm decides | `::test_the_tolerance_is_half_a_millimetre_and_octants_only_warn`, `::test_a_local_border_error_is_a_warning_not_a_failure` | `checker.py:63–65`, `:523–532` | ✓. A border whose plateau cannot be measured is skipped with a warning, on either border (`:516–518`; G12) |
| (d) Per-vessel CAD-RADS 2.0 (0, 1, 2, 3, 4A, 4B, 5, N) and an optional world-mm lesion point; never shown to the other reader | `::test_read_form_is_per_vessel_cadrads_2_with_an_optional_lesion_point`, `test_janusm_read_module.py::test_the_read_form_is_checked_before_anything_is_uploaded`, `::test_a_read_carries_nothing_but_what_a_reader_may_see` | `protocol.py:80–118`; `ReadInfo` carries no form fields | ✓ (item 5) |
| Written into `docs/JANUSM-READ-PROTOCOL.md` as protocol v1 | `::test_protocol_v1_conventions_are_written_down` | — | ✓ |

### JA47: anchoring as code (S5)

| Clause | Test | Code | Verdict |
|---|---|---|---|
| Gap = mean seed-vs-read ASSD on blank reads − on seeded reads | `::test_rule1_on_a_wave` | case-level means (`anchoring.py:141–164`); the report's `seedVsRead*` are read-level means | ≈: the two agree unless a read lacks an ASSD (G10) |
| Rule 1: upper 95 % bound of (gap − mean seeded inter-read ASSD) ≤ 0.2 mm; two-sample bootstrap, 2000 draws, fixed seed | `::test_rule1_is_a_two_sample_bootstrap_with_a_0p2_mm_margin` | `anchoring.py:52–56`, `:164–170`. Probe: equals an independent two-sample computation exactly (0.2713) | ✓; **the test does not pin independence, the quantile or the seed** (G10) |
| Rule 2: > half of seeded reads change < 5 % **of seed voxels** → flagged | `::test_rule2_flags_a_wave_that_follows_the_seed_and_draws_five_third_reads` | `changed_share` divides by **seed ∪ read** voxels (`anchoring.py:82–87`) | **✗ (G9)** in the strict sense; the error flags waves slightly more often |
| 5 seeded cases by salted hash get a third read from blank by a fresh reader | same test, and `test_segqueue_server_janusm.py::test_third_reads_are_blank_by_a_fresh_reader_and_never_reference` (Mongo; runs in CI) | draw `anchoring.py:176–185`; fresh reader `models.py:125–141`. **`adminThirdReads` opens any list** of cases (`rest.py:342–359`) | **✗ (G8):** the draw is computed but not enforced |
| Third reads never enter the reference standard | the server test above | `export.py:90–115` keeps `thirdRead` apart, but writes it into the same `reads/` folder | ≈ (G8; G25 must drop them) |

### JA48: reference population and table writer (S6, S7)

| Item | Test | Verdict |
|---|---|---|
| 1. `configs/janusm/reference-r1.json`, sha256-pinned, written by `tools/janusm/build_reference.py` | `test_janusm_reference.py::test_config_path_is_the_guards`, `::test_load_refuses_unpinned_changed_and_accepts_pinned` | ≈: the pin is `guard.REFERENCE_SHA256`, not a `PINNED` entry; it behaves the same, and the text should say so. The file is written in the locale encoding, but the sha is printed from UTF-8 bytes (G18) |
| 2. `gate[sign]` = depth, pass, κ, ICC; `rc` per JA42 | `::test_config_is_byte_identical_on_rerun_and_carries_no_id` | ✓ form; the content carries the JA42 gaps |
| 3. Concordance phrase by Lima v2's table, with "not graded" | `test_janusm_report.py::test_phrase_table`, `::test_missing_grade_prints_not_graded`, `::test_one_phrase_per_territory_end_to_end` | ≈: **an LM grade is never read** (`report.py:215`), and the report's grade input does not match the read form's `cadrads` / `lesionPoints` (G19) |
| 4. No per-segment flag in Table A | `::test_table_a_never_carries_a_flag` | ✓ |
| 5. Header: offsets, halves note, `HARNESS_VERSION`, `GEOMETRY_VERSION`, config sha256, `guard_version` | `::test_header_fields`, goldens | ≈: the config's geometry and features versions are **never compared** with the running ones, and `CALIBRATE_VERSION` is not recorded (G17) |
| 6. The builder refuses seal, decision, JM-0 (and extension) cases before any read | `test_janusm_reference.py::test_refuses_any_seal_decision_or_jm0_case`, `::test_cli_run_refuses_a_held_out_case_before_opening_anything`, `test_janusm_report.py::test_guard_hit_refuses_before_any_read` | ✓ |
| Tests: golden outputs | `::test_golden_output` (report) | ≈: **no golden config** (G22) |
| Tests: one per phrase, a changed config refused, forbidden words, byte-identical reruns, guard hit first | as named | ✓ |
| S6: Fir command printed; runs only in Slurm; only after LQ12's seeds | `::test_cli_prints_the_fir_command_and_runs_nothing`, `::test_cli_run_refuses_outside_slurm` | ✓ (the LQ12 condition is written, not enforced: acceptable) |
| S7: the S3 footer sentence | `::test_footer` | ✓ |

**Totals.** Of the JA37–JA48 clauses above:
- **✗ (does not match): 11**:
  - JA37 ×2 (transfer check, band);
  - JA40 median;
  - JA42 ×4 (fat map, n, step 4a, step 4b);
  - JA43 R9;
  - JA46 (a);
  - JA47 Rule 2's denominator;
  - JA47's third-read draw.
- Each has a G-spec, and none needs a new ruling except where §2 marks "judge".

---

## 2. Gaps as `role:swe` specifications (for the PM; not built here)

Each item names the file, the function, the change and the test. **Before the freeze PR:** G1, G2, G4, G6, G7,
G8, G9, G13, G14, G15, G16. The rest can follow.

### S1 / S3 / S4

- **G1. Simulate the depth on the measured wall** (JA40; E6). `src/janusm/calibrate.py`, `experiments/JanusM/fir/jm0r_decide.py`, `src/janusm/reference.py`.
  - **`calibrate.population_factor(phase_mix=PHASE_MIX, shape=…, cv_n=…)`:** the simulated population's median wall ÷
    `median_mm`, computed deterministically. It is 1.1087 at Lima's inputs, from 200 000 hearts at seed 7 (E6).
  - **`detectable_depth(..., measured_median_mm=None)`:**
    - when given, the anchor is `measured_median_mm / population_factor(...)`;
    - otherwise the default anchor is `ED_MEDIAN_MM` (5.7), not `LIMA_MEDIAN_MM`;
    - `median_mm` stays, for E7's regression tests;
    - it is an error to pass both;
    - it records `measured_median_mm` and the anchor in `inputs`.
  - **R9:** pass `measured_median_mm=x["thickness_median_mm"]`, and add `thickness_median_mm` to R9's inputs and
    missing list. If R3 failed (F3 does not hold), R9 still computes, but its line says "on an unaligned thickness
    definition; no thinning flag ships before R3's alignment".
  - **S6 `gate()`:** pass `measured_median_mm=blk["median_level"]`, not `median_mm=`.
  - **`CALIBRATE_VERSION` → 1.1.0.**
  - **Tests:**
    - E7's rows still reproduce at `median_mm=9.668`;
    - `detectable_depth(0.088, LIMA_SHAPE, 1.0, seed=31000)` returns 0.45 (the default anchor);
    - `measured_median_mm=9.668` returns 0.35;
    - R9's call carries the measured median (update `test_r9_calls_detectable_depth_with_cv_n_shape_and_the_f1_floor`);
    - S6's gate passes `measured_median_mm`.
- **G2. R9 when S3 refuses its inputs** (item 6b). `jm0r_decide.py` `decide()`, R9's `except ValueError`.
  - Append `"cv_n (refused by S3: <reason>)"` to `missing`, so a NOT DECIDABLE line prints.
  - Set `depth=None` and `gate_input="not computable"`. The outcome reads "the sign is shown as numbers only (JA41
    cannot be evaluated); the page prints the provisional <P> % only as the JA40 placeholder".
  - Fix the module docstring (S3 is merged).
  - Set `PROVISIONAL_DEPTH` to the judge's figure (Lima: 0.45, §3).
  - **Test:** update `test_r9_prints_the_provisional_depth_when_s3_cannot_compute_it` to expect the NOT DECIDABLE line.
- **G3. JA39's tolerance as enforced** (item 6a; E7). `src/janusm/harness.py`, `tests/test_janusm_harness.py`.
  - `PP_ASSD_TOLERANCE_MM = {0.5: 0.035, 1.0: 0.07}`.
  - The test compares `abs(err) <= tol`, without `round`.
  - The comment cites E6's worst (0.032) and E7's (0.0322 at 0.5 mm, 0.0669 at 1.0 mm).
- **G4. JA37's transfer check, its band and JA39's d: one decision scorer** (new; no S-item owns it).
  - **`janusm.harness.scoring_band(ref_labels, affine, half_width_mm=3.0, exclude_mm=3.0)`:**
    - voxels within ±`half_width_mm` of either border of the reference read;
    - minus those ≤ `exclude_mm` from label 4 (LA) or from the aortic plane (the label-2 voxels nearest the aorta, as
      `checker` finds them);
    - returns a bool ROI;
    - the half-width is the judge's to confirm, since JA37 names no width.
  - **`tools/janusm/score_decision.py`, run by the lead on Fir:**
    - calls `guard.refuse(decision_ids, purpose="decision_scoring")` first;
    - for each decision case with two accepted protocol-1 reads and the model's prediction, computes `compare()`
      within the band, giving pp model-vs-read and read-vs-read and JA8's d;
    - computes the voxel ASSD beside it;
    - runs the **transfer check** on the first 20 cases (by `sealed-r1.json` list order): median \|bias − bias_pp\|
      per border; > 0.05 mm → `guard_mm = 0.5`, plus the list of cases with \|vol − pp\| > 0.05 (aggregate count,
      no ids in the output).
  - **Output:** aggregate JSON only.
  - **Tests:**
    - synthetic reads on `harness.phantom`: a known shift gives d and the transfer verdict;
    - a band phantom excludes the LA and aortic zone;
    - a seal id refuses before anything is opened.
- **G5 (minor).** `jm0r_readout.py`: label `lima.ja20_septal_arc_column_kept` "reported; R7 uses the case median",
  or remove it. **Test:** none needed beyond the key's presence.

### S5 (read queue)

- **G6. No mitral plane is not a pass; wire the hinge points** (JA46 (a)).
  - `src/janusm_reads/checker.py` `check_conventions`: "no plane could be fitted" becomes an **error**, unless hinge
    points are given.
  - Add `hinge_points_mm` to `check_files`, `ReadSubmission` (`protocol.py`), `server/girder_janusm/check.py`
    `checkRead`, and a Slicer markups list "Mitral hinge points".
  - **Test:** a blank read with a 4 mm gap and no hinge points fails; the same read with three hinge points is
    fitted.
- **G7. The mitral footprint** (item 5c). `checker.py` `pool_above_mitral_mm`, `mitral_plane`.
  - Add `CheckConfig.mitral_footprint_margin_mm = 3.0`, and use `inplane <= radius + margin`, as the docstring
    already says ("plus the gap").
  - On a blank read, fit the plane before the height test, from the gap points **nearest the LA** (label-2 voxels
    within 3 mm of label 4 and within 3 mm of the LA-side extreme along the fitted normal), so that above-plane
    voxels cannot refit it. Or use the case's seed when the server holds one.
  - **Test:** label 2 at radius + 1 mm, 4 mm above, no 2–4 face → error, for both the seed-fitted and the read-fitted
    plane.
- **G8. The third-read draw is enforced and kept apart** (JA47 Rule 2).
  - `server/girder_janusm/rest.py` `adminThirdReads` takes `wave` and refuses unless:
    - the wave's anchoring report has `rule2.flagged: true`;
    - the list equals `anchoring.third_read_cases(wave, the wave's seeded cases)` (5, or all if fewer).
  - `export.py` writes third reads to `third/` with `reference: false`.
  - **Tests:** an arbitrary list, or 4 of 5, → 400; no `reads/*` record is a third read.
- **G9. Rule 2's denominator** (JA47). `anchoring.py` `changed_share`:
  - divide by `(seed > 0).sum()`;
  - update `docs/JANUSM-READ-PROTOCOL.md` §7.
  - **Test:** a read that only adds voxels outside the seed, with a share < 5 % of the union but ≥ 5 % of the seed, is
    not "following".
- **G10. Pin Rule 1's bootstrap, and compute the gap on reads** (JA47).
  - `test_janusm_reads.py`: a new test recomputes the bound with `default_rng(BOOTSTRAP_SEED)` and independent
    `integers` draws for blank and seeded, at the 0.95 quantile, and asserts equality. It also asserts that a
    shared-index draw differs at equal n.
  - `anchoring.py`: compute the gap from read-level means, bootstrapped by case.
  - **Test:** a case with one `None` ASSD gives `rule1.gap == seedVsReadBlank − seedVsReadSeeded`.
- **G11. A crashed check does not use up the return** (S5.3). `server/girder_janusm/check.py` `checkRead`:
  - on `crashed`, decrement `attempts`, or count `failedChecks` separately and decide on that.
  - **Test:** a crash on attempt 1, then a genuine failure → RETURNED, unflagged, with its profile.
- **G12. Checker boundary tests** (no code change). In `test_janusm_reads.py`:
  - LV–RV contact ≈ 0.2 % passes and ≈ 0.6 % fails;
  - the above-plane check at 3.0 mm passes and 3.5 mm fails on a read-fitted plane;
  - an unmeasurable **endocardial** plateau is an error, not a skip (the docs allow skipping the epicardium only).
- **G26. Export scope and fields** (S5.8):
  - `JanusMCase.wave`, with `export --wave` filtering on it and refusing an empty wave;
  - skip reads without `border_protocol == 1`, and list them;
  - seed offsets on by default (`--no-seed-offsets` to turn them off);
  - `seconds` accumulated over attempts, with the Slicer timer kept across reopening a returned read;
  - the read form restored (not cleared) when a returned read is reopened.
  - **Tests:** one per change, on the Mongo server suite.
- **G27. Refuse JanusMRead 0.1.0 before it claims a case** (item 5d). `src/janusm_reads/__init__.py`:
  - `PROTOCOL_VERSION = 2`, since the submission schema changed (`cadrads` is required);
  - `border_protocol` stays separate.
  - **Test:** protocol 1 on `next` → 426; update `test_protocol_refuses_missing_or_old_client`.

### S6 / S7 (reference and table)

- **G13. JA42 step 4: n = patients.** `reference.py` `repeatability`:
  - `n_pool` = the number of cases with at least one pair, used in the switch bound and the pooled RC;
  - report `n_patients` and `n_differences`.
  - **Tests:**
    - rewrite `test_rc_is_the_upper_95_bound_pooled_by_default` for n = 20;
    - a 14-vs-15 territory boundary.
- **G14. JA42 step 4a under pooling.** `repeatability`: when a territory uses the pooled SD, still test its **own**
  \|mean Δ_T\| against 0.5 × the SD in use, add it if larger, and record the decision.
  - **Test:** territory offsets of +0.4 / −0.4 add to LAD and LCx, not to RCA.
  - (Lima reads "mean Δ" in step 4a as the territory's; judge to confirm.)
- **G15. JA42 step 4b on a positive quantity; never for fat** (item 4d). `reference.py` `case_state`,
  `repeatability`, `rc_abs`, `gate`; `report.py` `build`:
  - per read and territory, carry `expected_T` (the remote level × the territory's mean shape) and `observed_T`;
  - the ρ test and the log ratios use log(expected_T / observed_T);
  - the threshold in mm is `expected_T · (e^RC − 1)` (judge: or the exact `1 − e^−RC`), and the gate and the report
    use the same `expected_T`;
  - fat never takes the log branch;
  - remove `level = 1.0`.
  - **Tests:**
    - heteroscedastic fat stays on differences;
    - heteroscedastic thinning switches to log;
    - the gate and the report use the same RC in mm.
- **G16. JA42 step 1 for fat; record any fallback.** `src/janusm/features.py` `fat_cluster_volumes` and
  `case_features`; `reference.py` `fat_territory_volume`:
  - cluster volume per **patient-map** territory, while rule C's fat flag stays on the AHA map;
  - the state carries `"map": "patient" | "aha_fallback"`, counted in `rc["decisions"]`.
  - **Test:** a fat-bearing segment that changes territory moves D, and the fallback is counted.
- **G17. Refuse a config built under other versions.** `report.py` `build`:
  - raise `ReportError` if the config's `geometry_version` or `features_version` differs from the running one;
  - `reference.build_config` records `calibrate.CALIBRATE_VERSION` (needed once G1 bumps it).
  - **Test:** a monkeypatched version refuses.
- **G18. UTF-8 config.** `tools/janusm/build_reference.py` `main`:
  - `write_bytes(text.encode("utf-8"))`, then print the sha of the bytes written.
  - **Test:** the sha matches under `LC_ALL=C`.
- **G19. The LM grade and a read-form adapter** (item 5a). `report.py`:
  - `territory_grade(grades, t)`: LAD and LCx take the worse of (vessel, LM) in CAD-RADS order, and record
    `grade_source`;
  - `grades_from_form(cadrads, lesionPoints)`.
  - **Test:** `{"LM": "4A", "LAD": "0"}` with a pattern gives the significant-grade phrase in LAD and LCx.
- **G20. Septal-arc column** (item 4a):
  - move `arc_segments` from `jm0r_readout.py:330–350` into `janusm.geometry`, and JM-0R imports it;
  - `features.case_features` adds the arc wall for the septal segments {2, 3, 8, 9}, None below JM-0R's 0.995
    agreement guard;
  - `reference.pooled` adds its percentiles;
  - `report.build` fills `septal_arc_value` for those segments, and "fixed sector" elsewhere.
  - **Tests:** at a 120° arc the arc values equal the fixed ones; at 150° they differ; regenerate the goldens.
- **G21. Missing boundary tests** (no code change):
  - depth 0.50 passes and 0.55 fails (monkeypatched S3);
  - κ with 4 and 5 flagged units;
  - a pass with κ None;
  - the fat gate with and without RC;
  - ρ at 0.4;
  - rule C passes with D ≤ RC → a number;
  - κ status "not estimable" when pe = 1.
- **G22. A golden config.** `tests/fixtures/janusm/reference_synth.json` from `build_config` on a 300-heart
  synthetic population (seed 11), with a regeneration flag like the report goldens.
- **G23 (minor).** Label distal mass "not computed (report v1)" on every row that has a lesion point (item 4b).
- **G24. R8 input to the builder.** `build_reference.py`: `--geodesic-shared yes|no` (required, from R8's decision),
  passed through.
  - **Test:** the CLI's missing-argument check lists it.
- **G25. The decision read-record producer** (item 4c). A new `tools/janusm/decision_read_features.py`, run by the
  lead on Fir:
  - `guard.refuse(decision_ids, purpose="decision_scoring")` first, refusing anything outside `sealed-r1.json`'s
    `decision`;
  - its JSON **list order** (not `sealed_r1.load()`'s frozenset);
  - accepted protocol-1 reads only, no third reads;
  - `read_1` / `read_2` fixed per reader by a stable key that is never written out;
  - `features.case_features` with the ImageCAS-X reference tree;
  - output `{"reads": [...]}` through `reference.assert_anonymous`, plus a sha256.
  - It can share the case loop with G4.
  - **Tests:** synthetic exports; order kept; third reads dropped; a seal id refuses before anything is opened; reader
    assignment stable.

---

## 3. Item 2: Lima E5 45 % against Hotel E7 35 %, on one seed

Full note: E6. On E7's seed (31000), with the shipped `janusm.calibrate`:

| Change from E7's primary row (9.668 mm, σ_m 0, Hotel's deviation, F1 1.0 mm) | depth |
|---|---|
| none | **0.35** |
| median 5.7 mm | **0.45** |
| + σ_m 0.5 mm | 0.50 |
| + E5's floor (1.96 · √2 · σ_m / √k ≈ 0.57–0.62 mm) | 0.40 |
| + E5's raw deviation (= E5's settings, on JA40's design) | 0.40 (false flags up from 0.018 to 0.025) |
| E5's own function (one population of 4000, depths from 0.15), seeds 0–19 | 0.40 × 18, 0.45 × 2 |

- **Rule C alone is 0.30 at both medians.** It is scale-free.
- **The whole gap is F1's floor:** a fixed 1.0 mm, against walls of different thickness.
- **E7's 0.35 needs 9.668 mm, as #205 notes.** E5's 45 % was its tail seed; its settings give 0.40.

**Which median is right for JA40: the measured median wall of the population that fills the table, on the table's
thickness definition**, converted to the simulation's end-diastolic anchor (÷ 1.109). In practice that is JM-0R's
`thickness_median_mm` for R9 and the reference population's median for S6 (G1).

**Not 9.668 mm:**
- it fails R3's own 4.2–8.0 mm window (`jm0r_decide --lima local_check_summary.json` rejects it at R3, while R9
  prints 35 % on it);
- it comes from 1.5 mm model-made labels on non-CCTA studies, whose epicardium sits +0.64 mm into the fat;
- used as the anchor, its phase is applied twice (10.7 mm simulated).

**Until JM-0R: 5.7 mm**, Chen 2025's CT end-diastolic mean, the anchor the simulation was written for. That is what
JA40's "conservative until measured" asks.

**Proposal for the judge:** JA40's provisional print becomes **45 %**: JA40's procedure, unchanged, with a median that
passes R3. The page then carries its "above 40 %" sentence. JA41's gate (≤ 0.50) still passes, with one step to
spare.

**What this costs.** If JM-0R measures 6–8 mm, the printed depth will be 0.40–0.45 (anchors 5.41 / 6.31 / 7.22 mm
on `DEPTH_SEED` give 0.45 / 0.40 / 0.40). The 35 % was never reachable on a CCTA wall with a 1 mm floor. The real
remedy is a smaller RC, which the reads will measure (JA42).

---

## 4. Item 3: reference population, 360 or 420

**360.** The 420 in Hotel v3 §4.1, Lima v2 §3 item 4a, JA18 and LQ12 is 560 − seal 60 − decision 40 − JM-0 40.
Nobody subtracted the pre-registered **seal extension** (JA6: "the next 60 by the seal salt"; the seal "may grow only
from the extension"; JA16 sizes it at 60–120 on the first 20 decision reads). `configs/janusm/sealed-r1.json` holds
all four lists, disjoint inside train (counted, no id printed), so 560 − 200 = 360. The guard loads the extension as
`"extension"` and refuses it under every purpose except `seal_scoring` (`guard.py:275–278`, `:410`). The shipped
builder derives 360, and `test_derived_population_excludes_every_janusm_list` asserts it.

**They should not be in it:**
1. **Any extension case may still become a seal case** (after JA16's sizing, or a Janus-M 1 re-power). Calibrating
   cuts, scales and percentiles on future test cases breaks "never refitted on seal cases" (Hotel v3 §4.1).
2. **The cost is small.** The extension is a salted-hash random draw, so excluding it adds no bias. Precision falls by
   √(420/360) ≈ 1.08. Rule C's null still pools 360 × 16 = 5 760 scores.
3. **Including them needs a second guard path** (a purpose or an exclude mode), which JA12's one-guard rule forbids.
4. **Releasing the unused tail later** (once the seal size is frozen) is possible, but buys ≤ 8 % for a second guard
   change and a second build. Not recommended.

**For the judge:** correct "420" to 360 in JA18 / LQ12's text. Separately, note that `seal_scoring` admits all 120
seal + extension cases whatever size the seal is frozen at. The seal scorer should take the frozen size and refuse
the unused tail (a `role:swe` item once JA16's sizing exists).

---

## 5. Item 4: #199's deferrals

1. **The arc-proportional septal column: build it before the freeze (G20).**
   - JA20 keeps the column unless R7 finds < 10 % of mass changing segment, and R7's missing-input branch is
     "kept". So the likely page has an empty column.
   - The only implementation is JM-0R's `arc_segments`. Moving it into `janusm.geometry` gives one implementation per
     quantity (Hotel v3 §4.1).
2. **Mass distal to a lesion point: leave deferred (G23 labels it).**
   - JA19 and Hotel v3 §4.3 call it optional and unvalidated.
   - The point exists only on seal and decision cases (JA46 (d)), never on a reference or routine case.
   - It needs a centreline graph with an ostium and arclength, which `janusm.geometry` lacks.
   - Nothing gates on it.
3. **Who produces the anonymous decision read records: a new lead-run Fir tool (G25),** on the `decision_scoring`
   path.
   - Order comes from `sealed-r1.json`'s list. The shipped `sealed_r1.load()` returns a frozenset, which has no
     order, so "the first 20" would be undefined.
   - `read_1` / `read_2` must be fixed per reader. Otherwise JA42 step 4a's reader offset and ICC's rater term are
     diluted.
   - The lead runs it after the decision reads are accepted and before S6, in Hotel v3 §4.2's order.
4. **The log-scale conversion (e^RC − 1) × level.**
   - **The maths.** If the read-to-read log ratio is bounded by RC, then at a true level L the readings fall in
     [L·e^−RC, L·e^RC]:
     - a **deficit** (thinning, hypoattenuation) beyond read noise is L(1 − e^−RC);
     - an **excess** (fat) beyond read noise is L(e^RC − 1).
   - **For deficits, the shipped (e^RC − 1)·L is conservative,** larger by e^RC (at RC 0.3: 0.350·L vs 0.259·L).
     Keeping it errs high, as JA40 does elsewhere.
   - **But it is applied to the wrong quantity.** D is a deviation centred near 0. Log ratios of D are undefined, so
     the code (rightly) refuses them, and the branch is dead for the two signs it was written for.
   - **The rule only makes sense on a positive level:** observed_T against expected_T = the remote level × the
     territory's mean shape. F1 then reads D > expected_T · (e^RC − 1) (or · (1 − e^−RC)).
   - **For fat at L = 1 mm³, the threshold is a fraction of a mm³:** lenient, and meaningless. Fat stays on
     differences.
   - **Proposal (judge):** JA42 step 4b on log(expected_T / observed_T); keep (e^RC − 1) as the stated conservative
     conversion; the gate and the report use the same expected_T; never log for fat (G15).

---

## 6. Item 5: #200's defaults

1. **Vessels LM / LAD / LCx / RCA: keep, and add two rules.**
   - It is the SCCT vessel-level reading, and JA46 (d) says only "per vessel".
   - (i) **LM feeds LAD and LCx** in the concordance phrase: the territory takes the worse grade (G19). Today an LM
     grade is collected and never read.
   - (ii) **4B is a patient-level category in CAD-RADS 2.0** (left main ≥ 50 %, or three-vessel obstructive disease).
     Recommendation:
     - the form accepts 4B on the **LM row only**;
     - LAD / LCx / RCA take 0–4A, 5 and N;
     - three-vessel 4B is derived from three ≥ 4A rows and printed as such.
     - This is the judge's to rule, since JA46 lists 4B without saying where.
   - **Ramus and posterior branches:** write the attribution into the protocol text (ramus → LCx; PDA / PL by
     dominance), with no code change.
2. **Lesion points only on grades 1–5: keep.**
   - A point marks the worst lesion. 0 has none, and N has no graded worst lesion.
   - A point with 0 or N refuses the whole submission (400), which is better than silently dropping it.
   - Optional UI nicety: clear the point when the grade changes to 0 or N.
3. **The mitral-plane check over the plane's own footprint: change it (G6, G7).**
   - JA46 (a) sets no footprint. Some restriction is right (it keeps the LVOT out of the test), but the shipped one has
     three faults:
     - it has no margin, although the docstring says "plus the gap";
     - on a blank read the reader's own label-2 voxels refit and enlarge the plane (probe: an error moved the radius
       5.7 → 10.3 mm and passed);
     - no plane at all passes.
   - **Fix:** footprint = radius + 3 mm; fit before testing, from the LA-side gap; no plane = error unless hinge points
     are given, and wire the hinge points.
4. **JanusMRead 0.1.0 refused at submit: refuse it before claim (G27).**
   - Today the refusal is a side effect of the missing `cadrads`. A 0.1.0 reader can claim a case, draw it under the
     pre-v1 50 HU window, and upload a file that is then orphaned, with a message the 0.1.0 UI cannot satisfy.
   - The submission schema did change, so the wire `PROTOCOL_VERSION` should be 2. `border_protocol` stays separate,
     as S5.9 requires. The existing 426 path then refuses the client at `next`.

---

## 7. Item 6: #198's notes

1. **"0.03 mm" is E6's 0.032 rounded.** E7 reproduces it exactly: the worst is 0.0322. **A strict 0.03 fails two
   conditions, not one** (the second, the 0.5 mm grid's rough oblique epicardium at −0.5 mm, is over by 3 µm). The
   shipped test passes by rounding to two decimals, so it enforces < 0.035. **Proposal:** JA39 reads "0.035 mm up to
   0.5 mm, 0.07 mm at 1.0 mm, raw error", and the code says so (G3). The 1.0 mm row has 0.003 mm to spare. Nothing
   in JA8 moves: its margin is 0.25 mm.
2. **cv_n = 0 refused, so R9 prints the provisional 35 %.**
   - Refusing is right: cv_n = 0 (with σ_m = 0) has no normal variation, so rule C has no scale.
   - But a measured cv_n of 0 means JM-0R's shape statistic failed. It is not a reason to print a depth measured on
     another population.
   - Today R9 prints the placeholder **without** a NOT DECIDABLE line, which breaks JA43's own rule ("a missing input
     prints NOT DECIDABLE").
   - **Proposal (G2):**
     - NOT DECIDABLE: cv_n, with S3's reason;
     - the thinning sign is numbers only until a valid cv_n exists (JA41 cannot be evaluated);
     - the page's footer prints the JA40 placeholder, labelled as such.

---

## 8. Item 7: JM-0 / JM-0R aggregates

**Not posted.** On 2026-10-30 neither #205 nor any Janus-M issue carries JM-0 or JM-0R aggregates. R0–R10 therefore
have no plan value this round.

For the record, `experiments/JanusM/Lima/r4/dryrun_selftest_decisions.json` is a **dry run** of `jm0r_decide.py` on
Lima's R2 self-test aggregate (23 public hearts). It is not JM-0R and not a plan value:
- R0 stops (23 < 36);
- R3 would reject the 9.668 mm median;
- R9 would print 35 % on that same median (G1).

When the lead posts JM-0R's `summary.json`, the command is
`python experiments/JanusM/fir/jm0r_decide.py --jm0r summary.json --out decisions.json`, after G1 and G2 merge.

---

## 9. Held-out disclosure

- **No case or image was opened.** E6 is a simulation of segment thicknesses, and E7 uses analytic phantoms.
- **Both scripts call `janusm.guard.refuse([])` first,** so they fail closed if the guard's pins are broken.
- **Read-only checks of `configs/janusm/sealed-r1.json` counted list sizes only.** No id was printed or committed.
- **The dry run reads a committed aggregate JSON** (no ids).

---

## 10. Carried assumptions

- **LQ2–LQ12 and LQ19–LQ22** are taken with their rulings' recommendations, as Hotel v3 and the Round 3 ruling state.
- **LQ22 (a)** was overridden by the PM under M2, to check the build.
- **No new lead question** is proposed. The judge items in §2–§6 are ruling choices:
  - the 45 % print;
  - the scoring-band width;
  - step 4a's "mean Δ";
  - step 4b's level;
  - LM and 4B placement;
  - 360.

## 11. Risks

- **G1 moves the printed depth up by 5–10 points.** That is the cost of simulating the wall the table measures. If
  the judge keeps 35 %, the page states a figure that JA40's procedure does not produce on a CCTA wall.
- **G13 and G14 raise the RC, and therefore the depth.** Together with G1, a JM-0R cv_n near 0.12 could push
  thinning past JA41's 0.50 (LQ21's numbers-only outcome becomes likelier).
- **The S5 holes (G6, G8, G11) are cheap to fix,** and must close before the first read wave. After it, they can only
  be audited, not fixed.
- **Mongo-backed server tests** were not run here (no Mongo). CI runs them and fails if they skip.

## 12. References

- Bland JM, Altman DG. Statistical methods for assessing agreement between two methods of clinical measurement.
  *Lancet* 1986;327(8476):307–310.
- Chen 2025, *Clin Imaging* 118:110390 (the CT end-diastolic wall anchor; as cited in the Round 3 ruling).
- Cury RC et al. CAD-RADS 2.0 – 2022 Coronary Artery Disease–Reporting and Data System. *J Cardiovasc Comput Tomogr*
  2022;16(6):536–557 (4B as left main ≥ 50 % or three-vessel obstructive disease).
- Shrout PE, Fleiss JL. Intraclass correlations: uses in assessing rater reliability. *Psychol Bull*
  1979;86(2):420–428.

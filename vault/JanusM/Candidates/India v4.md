---
aliases: [India v4]
tags: [janus-m, plans, candidate, round-4, india, myocardium, path-rest-ccta, build-check]
status: submitted
round: 4
path: jm/rest-ccta
advocate: India
updated: 2026-10-30
issue: christianGRogers/Asclepius#205
---

# India v4: the shipped Stage A checked against the Round 3 ruling

**Advocate:** India. **Round:** 4, path `jm/rest-ccta` (LQ1 option A). **Base:** the master plan in force:
[[Hotel v3]] with JA37–JA49 ([[Janus-M Round 3 rest-ccta]]). **What was checked:** the code on
`jm/rest-ccta` with `dev` merged (#197–#200 and #198's `janusm.calibrate`; `dev` at `dd7864a`).
**Evidence:**
- [[India - R4 E11 Lima's 45 percent and Hotel's 35 percent differ by the wall median, not the F1 code]] (item 2);
- the CPU checks in `experiments/JanusM/India/r4/`:
  - `s1_open_base_vol`, `s1_ja39_strict` (S1);
  - `s24_acceptance` (S2, S4);
  - `s5_mitral_plane` (S5);
  - `s367_rc_checks`, `s367_refpop_size` (S3, S6, S7).

**Suite run.** `pytest tests/test_janusm_*.py`: **375 passed** (CPU, 7.5 min). The Mongo-backed
`test_segqueue_server_janusm.py` runs in CI.

**Rules kept.**
- No case, image or label was opened.
- The one id-touching step reads the committed id lists, calls `janusm.guard.refuse` on each id, and prints counts
  only. It is in `s367_refpop_size.py`, part 1.
- Every other check is a synthetic phantom or a simulation. E11 calls `janusm.guard.refuse([])` first, as a record.
- No Fir, SciNet or Alliance job was run. No text to anyone outside the project.

## 1. The plan in one paragraph

India v4 changes nothing structural.
- **What the build gets right.** It is faithful to the ruling on almost every clause: 23 of JA44's keys, R0–R10,
  JA46 (b)–(d), JA47, every JA48 test, and E7's rows reproduced exactly. Each clause's enforcing test is named in §3.
- **What it gets wrong.** It has **five gaps that make a guard or a flag more lenient than the ruling**. Each has a
  measured size:
  1. the 0.3 mm bias guard's estimator ignores JA37's band. On open (real) masks it reads a 0.5 mm shift as about
     0.38 mm, so a true bias near 0.4 mm passes (S1);
  2. R9 never passes JM-0R's measured wall median, so the printed depth always uses 9.668 mm. That is one or two
     5-point steps too optimistic for any wall thinner than that (S4, E11);
  3. the pooled F1 repeatability bound uses n = territory values (about 60) where JA42 says patients (20). It comes
     out 17 % too small (S6);
  4. fat's F1 floor on the log scale is about 1.3 mm³, so F1 is effectively off for fat (S6, S7);
  5. on the 10 blank seal cases, the mitral-plane check fits its plane to the read it is judging. A pool 4–6 mm into
     the atrium passes (S5).
- **Item 2 is settled by E11.** The 35 % vs 45 % gap is the wall median, not the F1 code. So JA40's procedure stands,
  but its provisional input must change: **print 45 %**, from the 5.7 mm end-diastolic anchor.
- **The fixes.** Every gap is written as a `role:swe` spec for the PM (§10), grouped into six issues. None is built
  here.

## 2. What is unchanged

JA1–JA49 as ruled, Hotel v3 as amended. No threshold is re-argued. Where India proposes a wording change to a ruling
(§11), it is because the shipped code shows the clause cannot be implemented as written (JA42's log branch; JA39's
0.03 mm), not to move a number.

## 3. Item 1: S1–S7 against JA37–JA48, test by test

"Matches" means the code does what the clause says and the named test would fail if it did not. Gaps are numbered
**IG1–IG23** and specified in §10.

### 3.1 S1, the harness (JA37, JA38, JA39, JA45; `src/janusm/harness.py`, `tests/test_janusm_harness.py`)

| Clause | Enforcing test | Matches? | Gap |
|---|---|---|---|
| JA37 estimator: ΔV ÷ mean of two marching-cubes areas, smoothed 1 voxel | `test_signed_bias_is_signed_outward_and_antisymmetric`, `test_surface_area_matches_the_analytic_capsule` | yes (`signed_bias`, `surface_area(smooth_vox=1.0)`) | — |
| JA37 validated on exact phantoms → guard 0.3 mm, else 0.5 | `test_ja16_the_estimator_recovers_a_known_half_millimetre_shift`, `test_ja16_guard_falls_back_when_the_check_fails` | yes, on **closed** capsules only | **IG1** |
| JA37 region: a band round the reference border, ≤ 3 mm from LA and aorta excluded | `test_compare_restricts_pp_to_the_roi` (only that `roi` reaches pp) | **partly**: `compare(roi=)` restricts pp; `signed_bias`, the guard's estimator, ignores it (the test asserts so); nothing builds the band | **IG1, IG2** |
| JA37 transfer check: first 20 decision double reads, median \|vol − pp\| > 0.05 → guard 0.5, list the cases | none | **no code**: `compare()` returns `bias_pp_*`, but nothing takes the median or returns a guard | **IG3** |
| JA37 disclosed real-wall error, "recorded, not corrected" | none | not recorded in the module | in IG1 |
| JA37 Round 2 estimators retired | — | yes (none in `src/`) | — |
| JA38 `perturb()` nominal, realises ≈ 1.3× | `test_a_constant_model_bias_costs_about_its_own_size_in_thickness` (0.5 < realised < 0.7) | yes | — |
| JA38 rows report and are indexed by the realised bias and ASSD | `test_rows_are_indexed_by_what_was_realised` | yes (`run()`: `bias_*_nominal`, `bias_*_realised`, `assd_pp_*`, `assd_voxel_*`) | — |
| JA38 exact analytic shifts for fixtures | `test_exact_shift_phantom_moves_the_closed_surface_by_the_shift` | yes (`exact_shift_phantom`, public) | — |
| JA39 pp for both terms of d and the 1.0 mm guard, one implementation | `test_pp_is_zero_on_itself_antisymmetric_and_nan_when_empty`, `test_pp_does_not_depend_on_the_padding_around_the_heart` | yes in the harness (one `_pp`). **No scorer that computes d exists yet** | in **IG16** |
| JA39 voxel ASSD reported beside | `test_rows_are_indexed_by_what_was_realised` | yes in value; `surface_assd` re-implements `segtrain.metrics.surface_distances` (equal: 0.47283 on the phantom) | IG22 (cosmetic) |
| JA39 fixture tolerances 0.03 / 0.07 mm | `test_e6_pp_within_ja39_tolerances` | **only after rounding to 2 dp** (`round(abs(err), 2) <= tol`) | **IG19**, §8 |
| JA39 thickness unchanged | `test_thickness_error_is_the_median_over_segments_1_to_16` | yes | — |
| JA45 API, `compare()` keys, `run()` side by side, `HARNESS_VERSION` 1.1.0 | `test_compare_on_itself_is_all_zero`, `test_harness_version_is_1_1` | yes | — |
| JA45 E4 shells: `signed_bias` ± 0.01 mm to 1 mm | `test_e4_exact_shells_signed_bias_within_a_hundredth` | yes (worst 0.006) | — |

**IG1 measured** (`s1_open_base_vol.json`; Hotel E6's open-base phantom: 2 grids × 3 walls × 2 borders, 12 per
shift):

| True shift | Whole-mask `signed_bias` error, mean / worst | pp in the 6 mm-off-base ROI, worst |
|---|---|---|
| −0.5 mm | +0.119 / +0.134 | 0.032 |
| −0.3 mm | +0.071 / +0.080 | 0.019 |
| +0.3 mm | −0.069 / −0.078 | 0.015 |
| +0.5 mm | −0.113 / −0.129 | 0.025 |

- **The direction.** The error always points toward zero, about 24 % of the shift. The cut face counts in the area
  but does not move, so ΔV ÷ area is diluted.
- **Why it matters.** Every real LV mask is open at the mitral and aortic planes, so a **true bias of about
  0.38–0.40 mm reads 0.30 and passes the 0.3 mm guard**. That is larger than JA37's disclosed 0.05 / 0.09 mm, and
  `validate_bias_estimator()` never meets an open mask. Hotel E6's "vol worst 0.019" was measured with the band; the
  shipped function does not apply one.

### 3.2 S2, JM-0R v2 (JA44; `experiments/JanusM/fir/jm0r_readout.py`, `tests/test_janusm_jm0r_readout.py`)

| Clause | Enforcing test | Matches? | Gap |
|---|---|---|---|
| Canonical sign, endocardium (+1.0 for the moved-endocardium case) | `test_a_moved_endocardium_moves_the_offset_by_that_distance` | yes (asserts +1.0) | — |
| Canonical sign, epicardium | `test_a_moved_epicardium_reads_plus_when_the_label_reaches_into_the_fat` | yes | — |
| `SCRIPT_VERSION` bumped | `test_decision_inputs_has_every_ja44_key_on_the_synthetic_case` | yes ("2") | — |
| Flat `decision_inputs`, all 23 keys, aggregates only, no id | same test (key set equals `jm0r_decide.KEYS`, an id regex) | yes | — |
| Unmeasured → None, never a default | `test_decision_inputs_marks_what_is_not_measured_as_none` | yes | — |
| `cv_n` = plain SD of thickness ÷ shape | same test (equals Lima's `cv_n_shape_corrected_sd`) | yes (`np.std`, ddof 0; immaterial) | — |
| `cv_n_robust_log` reported, never used | none on its value | yes in code | minor |
| TPR medians over pooled free-wall segments | per-case test only | yes in code | minor |
| `septal_arc_mass_changed_median` | per-case test | yes; but the same summary's `ja20_septal_arc_column_kept` uses the **pooled** share | **IG20** |
| Acceptance: decide on JM-0R's synthetic output prints no NOT DECIDABLE | `test_the_decision_script_on_the_synthetic_summary_is_decidable` | passes, **but only because** 40 identical rows give cv_n = 0, S3 refuses, and the refusal is silent; R9 never computes a depth | **IG5** |

### 3.3 S4, the decision script (JA43; `experiments/JanusM/fir/jm0r_decide.py`, `tests/test_janusm_jm0r_decide.py`)

| Rule | Enforcing tests | Matches? | Gap |
|---|---|---|---|
| Missing → "NOT DECIDABLE: <key>" + conservative branch, no default | `test_r*_missing*` for R0–R9 | yes for R0–R8, R10 | IG5 (R9 refusal) |
| R0 ≥ 36 of 40, stop on 23 | `test_r0_usable_cases`, `test_r0_stops_on_23_cases_and_prints_it`, `test_r0_missing_stops` | yes | — |
| R1 AHA > 10 % → frame fix | `test_r1_aha_frame`, `test_r1_missing_takes_the_fix` | yes | — |
| R2 halves > 25 % → header note, never everywhere | `test_r2_halves`, `test_r2_missing_states_the_layer_count` | yes | — |
| R3 4.2–8.0 mm | `test_r3_thickness_definition`, `test_r3_missing…` | yes | — |
| R4 \|offset\| > 0.5 → snap; \|endo\| > 0.25 → TPR snapped; > 0.3 printed | `test_r4_seed_offsets`, `test_r4_missing` | yes. Missing → "no snap decision" (JA43 states no missing branch) | minor |
| R5 TPR branch order | `test_r5_rest_tpr` (parametrised), three missing tests, `test_r5_the_1mm_guard_stands_in…` | yes | — |
| R6 fat grid order, then patient rule, else number | `test_r6_*` (3) | yes | — |
| R7 < 10 % dropped, missing kept | `test_r7_*` | yes | — |
| R8 Euclidean primary; ≥ 10 % "shared" | `test_r8_geodesic`, `test_r8_missing` | yes in the script; **not wired downstream** | **IG17** |
| R9 JA40 with JM-0R's cv_n and shape | `test_r9_calls_detectable_depth_with_cv_n_shape_and_the_f1_floor` + 4 | **partly**: no `median_mm` passed, so S3 uses 9.668 mm | **IG4** |
| R10 reported only | `test_r10_reported_only` | yes | — |
| Fallback mappers (Lima, India, Hotel; Hotel's endocardium negated) | `test_hotel_fallback_negates_the_endocardium`, `test_lima_fallback`, `test_merge_fallback_order_and_sources` | yes. The port maps Hotel's 1 mm *pooled-segment* TPR median, not India R3's *patient* median. That is closer to JA44 | — |
| `decisions.json`, one line per rule with its source | `test_main_prints_one_line_per_rule_and_writes_decisions_json` | yes | — |

**IG4 measured** (`s24_acceptance.json`). Synthetic rows with seeded jitter give cv_n 0.0905 and a median of 7.73 mm.
- R9 as shipped prints **30 %**.
- With the median passed, it prints **35 %**.

### 3.4 S3, the detectable depth (JA40; `src/janusm/calibrate.py`, `tests/test_janusm_calibrate.py`)

| Clause | Enforcing test | Matches? | Gap |
|---|---|---|---|
| One function; mixed 40/40/20, prevalence 0.1, 4 × 2000 | `test_the_single_function_matches_the_sweep` | yes | — |
| Smallest depth with mean sensitivity ≥ 0.80, grid 0.10–0.60, rounded up | `test_the_depth_is_on_the_grid_and_rounded_up` | yes | — |
| Reproduces E7: 0.30 at RC 0, 0.35 at RC 1.0; lookup rows | `test_e7_primary_rows_reproduce`, `test_e7_every_replicate_reproduces`, `test_e7_lookup_rows_reproduce` | yes, exactly (E11 re-confirms) | — |
| > 0.40 → the page says so | `test_page_line_fills_the_depth_and_warns_above_forty_percent` | yes | — |
| cv_n plain SD; no added error on own-model borders | — | yes | — |
| The population's median wall | `test_inputs_are_explicit_and_the_median_matters` | **the ruling never fixed it**; S3 defaults to 9.668 mm and multiplies it by the phase mix again (§4) | **IG4** |

### 3.5 S6, the reference population (JA41, JA42, JA48; `src/janusm/reference.py`, `tools/janusm/build_reference.py`, `tests/test_janusm_reference.py`)

| Clause | Enforcing test | Matches? | Gap |
|---|---|---|---|
| JA41 flag = rule C ∧ F1 ∧ depth ≤ 0.50 | `test_gate_fails_without_rc_or_above_half`, `test_gate_equals_s3_detectable_depth_at_the_same_seed` | yes (largest territory RC, conservative) | IG4 (median input) |
| JA41 κ / ICC reported, "not estimable" < 5, never gating | `test_kappa_not_estimable_below_five_and_icc_agrees` | yes | — |
| JA41 fat: F1 + κ, no depth gate | `gate()` fat branch | yes in structure; F1 is effectively off on the log scale | **IG7** |
| JA42-1 patient map, each read's own frame, same tree for both | none (reads arrive as features) | D is on the patient map. "Same tree" belongs to the producer, which does not exist | **IG16** |
| JA42-2 D = `f1_deviation`; fat D = core cluster volume | `test_f1_deviation_reads_a_known_thinning` | yes | — |
| JA42-3 per territory if n_T ≥ 15, else pooled; χ² check | `test_rc_uses_a_noisy_territorys_own_sd` | yes, but the bound inherits IG6's n | IG6 |
| JA42-4 RC upper 95 % bound with **n = patients** | `test_rc_is_the_upper_95_bound_pooled_by_default` **asserts n ≈ 60 (values)** | **no**: `n_pool = len(alld)` | **IG6** |
| JA42-4 add \|mean Δ\| > 0.5 SD | `test_rc_adds_a_systematic_reader_offset` | yes | — |
| JA42-4 Spearman > 0.4 → log ratios | `test_rc_switches_to_log_ratios_when_error_grows_with_the_level` | as written; **the clause is ill-posed** for a signed D (India v3's own text) | **IG8**, §11 |
| JA42-5 point, bound, n, every decision reported | `test_rc_is_the_upper_95_bound_pooled_by_default` | yes | — |
| JA48-1 `reference-r1.json`, pinned, written by the builder | `test_config_path_is_the_guards`, `test_load_refuses_unpinned_changed_and_accepts_pinned` | yes. The pin is `guard.REFERENCE_SHA256`, not a `PINNED` entry; it has the same effect | record only |
| JA48-2 `gate[sign]`, `rc` | `test_config_is_byte_identical_on_rerun_and_carries_no_id` | yes | — |
| JA48-6 refuses seal, extension, decision, JM-0 | `test_refuses_any_seal_decision_or_jm0_case` (4 params), `test_cli_run_refuses_a_held_out_case_before_opening_anything` | yes | — |
| JA48 builder on "whichever model passes" (LQ12) | none | Janus-M 0 masks only | IG21 (conditional) |

**IG6 measured** (`s367_rc_checks.json`, 20 patients × 3 territories):
- the shipped pooled RC is 17 % smaller than JA42's;
- its coverage of the true 1.96 σ falls to **88 %** when a patient's three territory differences are correlated
  (ρ 0.8), against 99 % with n = patients.

**IG7 measured.** On the shipped log test's design (5–200 mm³, 25 % multiplicative read noise):
- the fat F1 floor is 1.3 mm³;
- the SD of the read-to-read difference is 3.5–53 mm³.

### 3.6 S7, the table writer (JA48; `src/janusm/report.py`, `tests/test_janusm_report.py`)

| Clause | Enforcing test | Matches? | Gap |
|---|---|---|---|
| Lima's phrase table, including "not graded" | `test_phrase_table`, `test_one_phrase_per_territory_end_to_end`, `test_pattern_without_a_significant_grade`, `test_missing_grade_prints_not_graded` | yes | LM grade unused (**IG12**) |
| No per-segment flag in Table A | `test_table_a_never_carries_a_flag` | yes | — |
| Header: canonical offsets, halves note, versions, config sha256, guard version | `test_header_fields` | yes | — |
| Golden outputs, byte-identical reruns, forbidden words, guard refusal first | `test_golden_output`, `test_byte_identical_reruns`, `test_no_forbidden_word_outside_the_footer`, `test_guard_hit_refuses_before_any_read` | yes | — |
| Refused changed or unpinned config | `test_changed_reference_config_is_refused`, `test_unpinned_reference_is_refused` | yes | — |
| Footer sentence from S3 | via `calibrate.page_line` | yes | the number is IG4's |
| Fat F1 | — | `report.py` passes level 1.0 on the log scale | IG7 |
| Septal-arc column (R7 keep) | — | printed blank | **IG18** (item 4 (a)) |
| Read-record lesion points → `reader_grades` | none | no adapter | **IG13** |

### 3.7 S5, the read queue (JA46, JA47; `src/janusm_reads/`, `server/girder_janusm/`, `slicer/JanusMRead/`, `docs/JANUSM-READ-PROTOCOL.md`)

| Clause | Enforcing test | Matches? | Gap |
|---|---|---|---|
| JA46 (a) plane on label-2 voxels ≤ 3 mm of label 4; seed: its 2–4 interface | `test_janusm_reads.py::test_the_mitral_gap_phantom_passes_and_its_plane_is_fitted` | yes on seeded cases; **on blank cases the plane is fitted to the read being judged** | **IG9** |
| JA46 (a) fallback: annular hinge points | the same test, with points passed by hand | the function takes them; **nothing supplies them** (no form field; `check.py` passes none) | **IG11** |
| JA46 (a) labels 2 and 4 never share a face | `test_labels_2_and_4_never_share_a_face` | yes | — |
| S5.4 label 2 ≤ 3 mm above the plane | `test_the_lv_pool_reaches_at_most_3_mm_above_the_seeds_mitral_plane` (seeded only) | yes on seeded cases; the footprint has no margin, although the docstring says "plus the gap" | IG9, **IG10** |
| JA46 (b) LV–RV ≤ 0.5 % | `test_lv_rv_contact_stays_at_half_a_percent` | yes | — |
| JA46 (c) median ≤ 0.5 mm decides; octants > 1.0 mm warn | `test_the_tolerance_is_half_a_millimetre_and_octants_only_warn`, `test_a_border_off_by_more_than_half_a_millimetre_fails_in_the_canonical_sign`, `test_a_local_border_error_is_a_warning_not_a_failure` | yes | — |
| JA44 canonical sign in the checker | `test_a_moved_endocardium_reads_plus_one_millimetre` | yes | — |
| JA46 (d) per-vessel CAD-RADS 2.0 + optional lesion point; never shown to the other reader | `test_read_form_is_per_vessel_cadrads_2_with_an_optional_lesion_point`; `test_janusm_read_module.py::test_the_read_form_is_checked_before_anything_is_uploaded`, `::test_it_never_asks_for_or_names_the_read_set_or_the_other_read`; Mongo refusals | yes | IG12, IG13 |
| JA47 rule 1: two-sample bootstrap, 2 000, fixed seed, 0.2 mm, voxel ASSD | `test_rule1_is_a_two_sample_bootstrap_with_a_0p2_mm_margin`, `test_rule1_on_a_wave` | yes | — |
| JA47 rule 2: > half change < 5 % → flag; 5 salted-hash third reads, blank, a fresh reader, never reference | `test_rule2_flags_a_wave_that_follows_the_seed_and_draws_five_third_reads`, `test_rule2_pending_third_reads_leave_the_verdict_open`; Mongo `test_third_reads_are_blank_by_a_fresh_reader_and_never_reference` | yes. The change share divides by the union of foreground (slightly conservative) | — |
| S5.1 window: level at the half-maximum, width 1.5 × \|p₁ − p₂\|; 800/300 on request | `test_thresholds_are_halfway_between_plateaus`, `test_a_case_opens_on_the_border_window_and_800_300_is_only_on_request` | yes | — |
| S5.3 return once; second failure accepted and flagged; profile sent | Mongo `test_two_independent_reads_and_the_read_check`, `test_a_returned_read_fixed_on_its_second_try_is_accepted_unflagged`; `test_return_once_then_accept_and_flag_is_on_the_wire` | yes, but a checker **crash** spends the reader's one return | **IG14** |
| S5.5 seed and read offsets in the anchoring report | `test_seed_and_read_half_maximum_offsets_go_into_the_report` | yes | — |
| S5.7 protocol text | `test_protocol_v1_conventions_are_written_down` | yes | — |
| S5.8 export fields | Mongo `test_export_feeds_the_anchoring_report` | yes | — |
| S5.9 `border_protocol: 1` apart from the wire version | `test_border_protocol_is_its_own_number` | yes | — |

**IG9 measured** (`s5_mitral_plane.json`, `janusm_reads.phantom.heart(mitral_gap_mm=2.0)`, 0.5 mm grid). The LV pool
is pushed h mm into the LA, keeping a myocardium rim, so no 2–4 face exists. The limit is 3 mm.

| Read | Seeded case: pool above plane / fails? | Blank case: pool above plane / fails? |
|---|---|---|
| exact | 1.09 mm / no | 1.09 mm / no |
| +4 mm | 3.59 / **yes** | 1.10 / **no** |
| +6 mm | 5.59 / **yes** | 1.83 / **no** |
| +10 mm | 9.59 / yes | 3.66 / yes |
| +10 mm, ring outside the 5.7 mm footprint | 1.09 / **no** | 5.31 / yes |

- **On blank cases** the plane follows the read, so overreach under about 9 mm passes. That covers all 20 reads of
  the 10 blank seal cases.
- **Outside the footprint** nothing is checked, on any case.

### 3.8 Summary of item 1

- **Faithful:** JA38, JA41, JA43 (R0–R8, R10), JA44, JA45, JA46 (b)–(d), JA47 and JA48 are built as ruled, each with
  an enforcing test.
- **Partly built:**
  - JA37: band and transfer check missing (IG1–IG3);
  - JA39: rounding (IG19);
  - JA40: the median input (IG4);
  - JA42: n, fat, and the log branch (IG6–IG8);
  - JA43 R8 (IG17) and R9 (IG4, IG5);
  - JA46 (a): blank cases, hinge points and margin (IG9–IG11).
- **Not built, and needed before decision scoring:** the producer of the decision read records, the JA8 d scorer and
  the transfer check's caller (IG16).

## 4. Item 2: Lima E5's 45 % against Hotel E7's 35 % (E11)

E11 runs both F1 implementations on one seed sequence (E7's) with the shipped `janusm.calibrate`, changing one factor
at a time. Full table in the note; the rows that decide it:

| | median_mm | F1 | σ_m | Depth |
|---|---|---|---|---|
| Hotel E7 as shipped | 9.668 | Hotel, 1.0 mm | 0 | **0.35** |
| the same at 5.7 mm | 5.7 | Hotel, 1.0 mm | 0 | **0.45** |
| Hotel F1, Lima's median and error | 5.7 | Hotel, 1.0 mm | 0.5 | 0.50 |
| … with Lima's RC floor (0.26–0.31 mm) | 5.7 | Hotel, Lima RC | 0.5 | 0.40 |
| **Lima E5's procedure** | 5.7 | Lima raw, Lima RC | 0.5 | **0.40** |
| Lima's procedure at 9.668 | 9.668 | Lima raw, Lima RC | 0.5 | 0.35 |
| Hotel, R3's window: 4.2 / 6.5 / 8.0 mm | — | Hotel, 1.0 mm | 0 | 0.60 / 0.40 / 0.35 |

**The explanation.**
1. **The median, not the F1 code.** At an equal median, Hotel's shape-corrected deviation and Lima's raw deviation
   give the same depth (0.40 = 0.40; 0.50 = 0.50). The floor is in millimetres and the thinning is relative, so a
   9.67 mm wall clears a 1.0 mm floor at a depth about 1.7× smaller than a 5.7 mm wall does.
2. **Lima's other two differences nearly cancel.** The added σ_m 0.5 costs +0.05. Lima's lower floor gains −0.10.
3. **Lima's printed 45 % was a high draw.** On E7's replicated seeds the procedure gives 0.40. Lima's own
   single-population read-out gives 0.40 on 19 of 21 seeds, and its sensitivity at 0.40 is 0.815, just above the
   0.80 line.
4. **So S3 exposes no error in JA40's procedure.** It exposes an input the ruling never fixed: the wall median. That
   median moves the depth as much as cv_n does (0.60 → 0.35 across 4.2–8.0 mm).

**Which median is right for JA40: not 9.668 mm.**
- **It fails JA43 R3's own window (4.2–8.0 mm).** If JM-0R measured it, the plan would call it a definition failure
  and ship no thinning flag.
- **It comes from 1.5 mm model-made labels on 23 public hearts.** Lima's own `local_check.py` says those absolute
  numbers "describe those labels, not CCTA truth".
- **The phase mix is counted twice.** `population()` multiplies `median_mm` by the phase factor, so E7's simulated
  population has a **10.7 mm** median wall.

**Recommendation for JA40:**
- **Before JM-0R:** the provisional input is Lima's end-diastolic anchor, **5.7 mm**, with the phase mix, as Lima
  built it. The provisional print becomes **45 %**, and the page carries JA40's "above 40 %" sentence. This is the
  conservative reading JA40 asks for. The 9.668 mm rows stay only as S3's E7-reproduction fixture.
- **After JM-0R:** the median is JM-0R's `thickness_median_mm`, entered so that the **simulated** population median
  equals it. The measured value is already phase-mixed, so `median_mm` = measured ÷ the phase factor (1.113 at
  cv_n 0.088; computed, not hard-coded). The same applies to the reference population's `median_level` (IG4).
- **For hypoattenuation,** whose level is in HU, no phase factor applies at all (IG4).

## 5. Item 3: reference population, 360 or 420

**360. The 60 seal-extension cases must not be in it.**
- **Where the numbers come from.** 420 = 560 training − 60 seal − 40 decision − 40 JM-0 (Hotel v3 §4.1).
  `sealed-r1.json` also freezes a 60-case `seal_extension` inside those 420. `reference.derive_cases()` removes it,
  giving 360 (`test_derived_population_excludes_every_janusm_list`).
- **The guard.** It refuses all 60 under `purpose="any"` and allows them only for seal scoring
  (`s367_refpop_size.json`; counts only).
- **Why not 420.**
  - JA6 lets the seal grow only from the extension, re-powered on the first 20 decision double reads.
  - LQ12 (a) runs the reference population after that look. So when the builder runs, an extension case may still
    become a seal case.
  - A threshold fitted on a case later scored as seal is calibration on the test set. The config promises "never
    refitted on seal cases".
- **What it costs: nothing measurable** (40 simulated populations):

  | n | rule C k | False flags on 20 000 fresh normals (mean, p95) |
  |---|---|---|
  | 360 | 1.759 ± 0.042 | 1.40 %, 1.83 % |
  | 420 | 1.760 ± 0.034 | 1.33 %, 1.76 % |

- **Record.** Hotel v3 §4.1's 420 (and its `reference-r3.json` name) is superseded by JA48's r1 config and 360. If
  the unused extension remainder is later released after the seal is final, that is a new config version by PR, never
  a refit of r1. No lead question is needed.

## 6. Item 4: #199's deferrals

| Deferral | Finding | Recommendation |
|---|---|---|
| **(a) Arc-proportional septal column** | R7's default when JM-0R is missing is "keep", so every table now prints an **empty** column. JM-0R already implements `arc_segments` (septal pair split by the measured arc, clipped to 60–240°) | **Build now** (IG18): move `arc_segments` into `janusm.geometry`, have JM-0R import it back, and fill the column |
| **(b) Mass distal to a lesion point** | Unvalidated by ruling (JA19, JA24). Lesion points exist only on seal and decision reads, so no table needs it yet | **Keep deferred, pre-register the definition now** (IG23): geodesic distance along the vessel's class mask from the ostium; myocardium whose nearest vessel voxel, on the territory map, is of that class and distal to the point. Research export and the unvalidated column only; never a flag or a phrase |
| **(c) Who produces the anonymous decision read records** | Nothing does; only `build_reference.py`'s docstring defines the format. The same path must also give JA8's d (pp), JA37's transfer check and JA42's RC | **One tool, run by the lead on Fir** (IG16): `tools/janusm/decision_features.py`, guard `purpose="decision_scoring"` on exactly the frozen decision list, the same reference tree for both reads, output anonymous |
| **(d) Log-scale conversion (e^RC − 1) × level** | A log RC gives the band L·e^{±RC}: L(e^RC − 1) above, L(1 − e^−RC) below. For thinning (downward) the shipped form is conservative by a factor e^RC (1.22 at RC 0.2). But it multiplies a ratio of *deviations* by the wall *level*, which is not a band on anything. For thinning the branch cannot fire (32 % of cases have D > 0 on both reads); for fat the level is 1.0 (IG7) | **Retire it** (IG7, IG8): fat RC on differences in mm³; depth signs use a relative RC, Δ ÷ the patient's level, applied as RC_rel × level (§11 P3) |

## 7. Item 5: #200's defaults (protocol v1)

| Default | What shipped | Finding | Recommendation |
|---|---|---|---|
| **(i) Vessels LM / LAD / LCx / RCA** | `protocol.VESSELS`, "each with its branches"; territories are seeded from LAD, LCx and RCA only | The four vessels match the coronary map that defines the territories. **LM is graded but used nowhere**: `report.build` reads LAD/LCx/RCA, so a significant LM lesion never reaches Table B. CAD-RADS 2.0's 4B is patient-level (LM ≥ 50 %, or three-vessel ≥ 70 %), so per vessel it is meaningful only on LM | **Keep the four.** Add "a branch is graded with the vessel the coronary map labels it". LM's grade feeds LAD and LCx (IG12). **4B on LM only**; on LAD/LCx/RCA ≥ 70 % is 4A, enforced in `read_form_problems` (§11 P5). No Table B class changes |
| **(ii) Lesion points only on grades 1–5** | `LESION_GRADES = {1, 2, 3, 4A, 4B, 5}`; refused on 0 and N, in the module and the server | Right: 0 has no lesion; N invites a guessed location that a future distal-mass column would treat as real | **Keep.** Add a bounds check: a point outside the CT is refused (IG13) |
| **(iii) Mitral check over the plane's own footprint** | Footprint = the largest in-plane radius of the fitted points, no margin; with no gap and no hinge points it warns | Excluding the outflow tract is right: the aorto-mitral continuity sits beside the annulus, so a plane-wide check would fail correct reads. **But** blank cases fit to the read (IG9), the hinge fallback is unreachable (IG11), and the code and docstring disagree on the margin (IG10). An exact read already uses 1.09 mm of the 3 mm | **Keep the footprint rule.** Before any blank seal read: a server-only seed for blank cases (IG9) and a 3 mm margin (IG10). With IG9 built, drop the hinge fallback from the doc (§11 P6) |
| **(iv) JanusMRead 0.1.0 refused at submit** | The wire protocol stayed 1, so 0.1.0 logs in, claims, downloads, and is refused at submit ("Grade every vessel…") | The refusal is clean but late. The reader does the whole read in a client that has no form; each retry leaves an orphan upload. The module already sends `X-JanusM-Client`, and the server ignores it | **Refuse below 0.2.0 at claim time** by that header, with an "update" message, and keep the submit refusal as a backstop (IG15). Nothing is released yet, so this is cheap insurance |

## 8. Item 6: #198's notes

**(1) JA39's "0.03 mm" is E6's 0.032 rounded.**
- **The shipped test.** It passes only by rounding: `round(abs(err), 2) <= 0.03` lets anything under 0.035 through.
- **Strictly, two conditions fail**, not one (`s1_ja39_strict.json`, 72 conditions re-run on the shipped code):
  - 0.4 mm grid, oblique rough endocardium, −0.5 mm: **0.0322** (the one #198 named);
  - 0.5 mm grid, oblique rough epicardium, −0.5 mm: **0.0300027**, over by 3 × 10⁻⁶ mm.
- **E6's own JSON agrees:** worst 0.0322; three rows above 0.03 strictly.
- **Recommendation: restate JA39 as "within 0.035 mm to 0.5 mm and 0.07 mm at 1.0 mm (E6 worst 0.032 and 0.067),
  unrounded"** (IG19). 0.035 mm is a seventh of JA8's 0.25 mm margin, so no decision moves.

**(2) cv_n = 0 is refused, so R9 prints the provisional 35 %.**
- **Is 35 % a substituted default?** No. JA40 pre-states the provisional print, so it is the pre-registered branch
  for "not computable".
- **Two things are wrong with how it is reached:**
  - **It is silent** (IG5). A measured cv_n of 0 over 40 hearts is a broken measurement, and JA43 says missing or
    unusable inputs print NOT DECIDABLE. The JA44 acceptance test passes only because of this silence, and it never
    exercises S3.
  - **35 % is the provisional only at 9.668 mm** (§4). At the 5.7 mm anchor the same inputs give 45 %.
- **Recommendation:**
  - print `NOT DECIDABLE: cv_n (S3 refused: …)` and keep the provisional outcome;
  - rebuild the acceptance test on jittered rows, so that R9 computes a depth;
  - make the provisional figure 45 % (§4).

## 9. Item 7: JM-0 / JM-0R aggregates

**Not posted.** As of 2026-10-30, no JM-0 or JM-0R aggregate is posted on #205, #167 or #142, so R0–R10 cannot
be recorded. When they are, run:

```sh
python experiments/JanusM/fir/jm0r_decide.py --jm0r <JM-0R summary.json> --out decisions.json
```

Run it after IG4 and IG5 merge. Otherwise R9 prints a depth at 9.668 mm, whatever JM-0R measured. If the aggregates
arrive first, the judge should read R9's line together with the jittered check in `s24_acceptance.json`, or recompute
R9 with `median_mm` set as in §4. Every other rule's line stands as printed.

## 10. `role:swe` specs for the PM (not built; label `path:jm-rest-ccta`; cite #205 and the Round 3 ruling)

Grouped into six issues, ordered by what blocks first. Each item names the file, the change, the test and when it is
done. Full working notes for each are in the r4 check scripts' JSON.

### SW-1 Harness: the bias guard on real masks (JA37, JA39; dev). Blocks the freeze PR

- **IG1 — `signed_bias` honours a band ROI.**
  - **Change.** In `src/janusm/harness.py`, `signed_bias(ref, test, spacing, smooth_vox=1.0, roi=None)` counts ΔV
    inside `roi`. Each area is the marching-cubes area of the faces whose centroids fall in `roi`. `compare(roi=)`
    passes `roi` to `signed_bias` (remove the test assertion that it does not).
  - **Validation.** Add `validate_bias_estimator(open_base=True)`: the same grid, on `exact_shift_phantom` cut by a
    fixed base plane, with the band. Record JA37's disclosed real-wall error in the docstring.
  - **Tests.** On E6's open phantom (two grids, three walls, both borders) at ±0.3 and ±0.5 mm, the error is within
    0.05 mm of the truth. E4's closed shells stay at ±0.01.
  - **Version.** `HARNESS_VERSION` 1.2.0.
  - **Done when** `s1_open_base_vol.py`, re-run with the ROI, shows |err| ≤ 0.05. If it cannot pass, the guard
    returns to 0.5 mm (JA16) and the judge is told.
- **IG2 — the JA37 band.**
  - **Change.** `bias_roi(ref_labels, spacing, *, band_mm=3.0, exclude_mm=3.0) -> (roi_endo, roi_epi)`: voxels within
    `band_mm` of each reference border, minus those within `exclude_mm` of the LA and of the aorta (or, with no aorta
    label, the AHA base plane; the docstring says which). `compare(roi="ja37")` builds it.
  - **Tests.** The ROI excludes every voxel ≤ 3 mm from the LA. A change made only in the basal 3 mm gives bias 0 ±
    0.01 with `roi="ja37"`.
- **IG3 — the transfer check.**
  - **Change.** `transfer_check(rows, *, n_first=20, limit_mm=0.05)` takes the first 20 decision double reads'
    `compare()` rows and returns:
    - the median |`bias_*` − `bias_pp_*`| per border;
    - `passed`;
    - `bias_guard_mm` (0.3 if passed, else 0.5);
    - `cases_over_limit`.

    Fewer than 20 rows raises `ValueError`, never a default. Both estimators use the JA37 band.
  - **Tests.** A median of 0.04 → 0.3; 0.06 → 0.5 and the listed rows; 19 rows → error; row 21 ignored.
- **IG19 — JA39 unrounded** (after the judge's wording, §11 P2).
  - **Change.** `PP_ASSD_TOLERANCE_MM = {0.5: 0.035, 1.0: 0.07}`, and `abs(err) <= tol` in
    `test_e6_pp_within_ja39_tolerances`.
- **IG22 (cosmetic).** `surface_assd` calls `segtrain.metrics.surface_distances`.

### SW-2 Depth inputs: R9 and the reference gate use the measured wall (JA40, JA43, JA44; dev). Blocks R9

- **IG4 — the wall median.**
  - **`janusm.calibrate`.**
    - `detectable_depth(s)` takes `median_mm` with **no default**. Add
      `population_median_mm=` as an alternative, solved so that the simulated population median equals it (the
      phase factor is computed from the same population, not hard-coded).
    - A `phase_mix=` argument: hypoattenuation passes `{"ED": 1.0}`, since HU does not scale with phase.
    - A `PROVISIONAL_MEDIAN_MM = 5.7` constant (the end-diastolic anchor, §4). `CALIBRATE_VERSION` 1.1.0.
  - **`jm0r_decide.py` R9.**
    - Pass `population_median_mm=x["thickness_median_mm"]`.
    - Add `thickness_median_mm` to R9's missing list and inputs.
    - Use the provisional 45 % (after the judge's ruling, §11 P1), and print the median in the outcome.
    - `DECIDE_VERSION` "2".
  - **`janusm.reference.gate`.** Pass `population_median_mm=blk["median_level"]` for thinning. Hypoattenuation uses
    the ED-only mix.
  - **Tests.**
    - The E7 fixture stays at `median_mm=9.668`.
    - A recording `depth_fn` sees JM-0R's median.
    - A missing median prints NOT DECIDABLE.
    - At `population_median_mm=5.7` the simulated median is 5.7 ± 0.05.
    - The jittered `s24_acceptance` rows print 35 %.
- **IG5 — the S3 refusal is loud.**
  - **Change.** In R9's `except ValueError` branch, append `"cv_n (S3 refused: <message>)"` to `missing`.
  - **Tests.**
    - The test for the case where S3 cannot compute a depth asserts that line.
    - The JA44 acceptance test (`test_the_decision_script_on_the_synthetic_summary_is_decidable`) builds its 40 rows
      with seeded per-segment jitter, and asserts both no NOT DECIDABLE and `depth is not None`. The identical-rows
      case becomes its own test, asserting the line.
- **IG20 — one septal-arc statistic.** In `jm0r_readout.py`, the summary's `ja20_septal_arc_column_kept` uses the
  per-case median (the `decision_inputs` key). The pooled share stays as a reported number.
  - **Test.** Pooled and median shares straddling 0.10: the flag follows the median.

### SW-3 Reference RC (JA42, JA43 R8; dev). Blocks the reference population

- **IG6 — n = patients.**
  - **Change.** In `reference.repeatability`, n in `bound()` is the number of distinct cases with at least one pair,
    for the pooled RC and step 3's χ² bound alike. Report `n_patients` and `n_values`.
  - **Tests.** `test_rc_is_the_upper_95_bound_pooled_by_default` asserts n = 20 (for 20 cases × 3 territories).
- **IG7 — fat RC on differences.** `repeatability(..., allow_log=False)` for fat; `report.py`'s fat F1 uses the mm³
  RC.
  - **Test.** Multiplicative fat noise stays `scale: "difference"`.
- **IG8 — the relative branch for depth signs** (after the judge's wording, §11 P3).
  - **The test statistic.** ρ(|Δ|, L̄), where L̄ is the mean of the two reads' patient level.
  - **The branch.** If ρ > 0.4, RC is computed on Δ ÷ L̄ and applied as RC_rel × L: the patient's level in the
    report, the population median in `gate()`. Delete the (e^RC − 1) conversion.
  - **Test.** Proportional noise switches to `"relative"`, and the floor at L equals RC_rel × L.
- **IG17 — R8 "shared" wired.**
  - **CLI.** `build_reference.py --geodesic-shared yes|no`, required with `--run`.
  - **Features.** `features.case_features` adds a geodesic segment majority (`geometry.territories(method=
    "geodesic")`).
  - **Report.** `report.py` marks "shared" every segment whose two majorities differ, when the config says so.
  - **Tests.** A one-segment phantom: "shared" only with the flag on. `--run` is refused without it.
- **IG21 (conditional: only if Janus-M 1 is trained).** `build_reference.py --model jm0|jm1 --masks DIR`, with the
  model recorded in the config.

### SW-4 Read queue: protocol v1 gaps (JA46 (a); dev). IG9 and IG10 block blank seal reads

- **IG9 — a server-only seed for blank cases.**
  - **Upload.** `server/girder_janusm/populate.py` uploads each blank case's seed to a reader-unreadable folder,
    `JanusM/check-seeds`, as `case.checkSeedFileId` (never `seedFileId`).
  - **Check.** `check.py` passes `seedFileId or checkSeedFileId` to `checker.check_files(seed_path=...)`.
  - **Never served.** `rest.downloadSeed` and `readInfo` never touch `checkSeedFileId`.
  - **Tests.** Mongo: a blank case's seed is never served (4xx, `hasSeed: false`), while its check report says
    "fitted to the seed". Checker: E-S5's +4 and +6 mm reads fail with the seed.
- **IG10 — footprint margin.**
  - **Change.** `pool_above_mitral_mm` uses `inplane <= radius + cfg.mitral_footprint_margin_mm` (default 3.0). The
    check report includes the plane's `radius` and `source`. Doc §4 states that an exact read sits about 1 mm above
    the fitted plane.
  - **Test.** The E-S5 ring at 6.2–8.7 mm fails with the margin.
- **IG11 — hinge points.** With IG9 built, delete step 3 from `docs/JANUSM-READ-PROTOCOL.md` §4 and from the
  `mitral_plane` docstring. A case with no seed and no gap warns (§11 P6).
  - **Test.** That warning.
- **IG14 — a crash does not spend the return.** In `check.py` `checkRead`, on `crashed`, record `crashes` and decide
  on `attempts − crashes`.
  - **Test (Mongo).** Crash, then a genuine failure → returned, unflagged, with a profile. A further failure →
    flagged.
- **IG15 — old clients refused at claim.**
  - **Change.** `rest.getProject` and `rest.nextRead` parse `X-JanusM-Client`. Below `MIN_JANUSMREAD = "0.2.0"` they
    return 426, `ERR_CLIENT_TOO_OLD`, "Update JanusMRead to 0.2.0: protocol v1 needs the read form". The bare Python
    client and an absent header pass. The submit refusal stays.
  - **Tests (Mongo).** `JanusMRead-0.1.0` is refused at `next` and no read is created; 0.2.0 passes.
- **4B on LM only** (after §11 P5). `protocol.read_form_problems` refuses 4B on LAD, LCx and RCA.
  - **Test.** That refusal.

### SW-5 Table writer: grades and columns (JA48, JA20; dev)

- **IG12 — LM feeds LAD and LCx.**
  - **Change.** In `janusm.report.build`, the grade used for LAD and for LCx is the worse of its own and LM's (order
    0 < 1 < 2 < 3 < 4A < 4B < 5; N only if both are N or absent). Table B notes "LM <grade>" when LM is the source.
  - **Test.** `{"LM": "4B", "LAD": "0", "LCx": "0", "RCA": "0"}` → LAD and LCx significant, RCA not.
- **IG13 — one adapter.** `report.grades_from_read_record(rec)` maps `cadrads` and `lesionPoints` (from
  `export.readRecord`) to what `build` reads. `rest.submit` refuses a lesion point outside the CT's world bounding
  box.
  - **Tests.** A round trip; a point 1 m away is refused.
- **IG18 — the septal-arc column.**
  - **Change.** Move `jm0r_readout.arc_segments` into `janusm.geometry`, and have JM-0R import it.
    `features.case_features` adds `wall_mm_arc` and `rel_subendo_hu_arc` for segments 2, 3, 8 and 9.
    `build_reference` adds their percentiles. The column prints them when R7 keeps it.
  - **Tests.** A 120° arc reproduces the fixed sectors. A 180° arc moves the expected share. The column is absent
    when R7 drops it.
- **IG23 — mass distal to a lesion point: definition only.** Write §6 (b)'s definition into `report.py`'s
  "unvalidated column" docstring and into the research-export schema. No code until a ruling asks for it.

### SW-6 Decision scoring, one tool (JA8, JA37, JA41, JA42; dev; run by the lead on Fir). Blocks decision scoring

- **IG16 — `tools/janusm/decision_features.py`.**
  - **Running.** Without `--run` it prints the Fir command. It runs only under `SLURM_JOB_ID`.
  - **Guard.** `janusm.guard.refuse(cases, purpose="decision_scoring")` on exactly the frozen decision list, before
    any file is opened.
  - **Inputs.** The read-queue export: two accepted reads, `border_protocol: 1`, third reads excluded.
  - **Per case:**
    - `features.case_features` for each read, with **one** reference coronary tree passed for both reads;
    - harness `compare()` with `roi="ja37"`, for model-vs-read and read-vs-read, in the frozen draw order;
    - `transfer_check` on the first 20.
  - **Output.** `{"reads": [...], "assd_pp": [...], "transfer_check": {...}}`, passed through
    `reference.assert_anonymous`. Any id-bearing side file stays on Fir.
  - **Tests.**
    - A synthetic pair gives the documented format.
    - A seal or JM-0 case is refused before anything opens.
    - The same coronary array is used for both reads.
    - An id in the output is refused.

## 11. Proposed amendments, for the Round 4 judge (to be numbered from JA60)

- **P1 (JA40) — the wall median.**
  - The detectable depth is computed at a population whose simulated median wall equals the measured one: JM-0R's
    `thickness_median_mm`, then the reference population's.
  - Until JM-0R, the input is the 5.7 mm end-diastolic anchor with the phase mix. **The provisional print is 45 %**,
    with JA40's "above 40 %" sentence.
  - The 9.668 mm figure is only S3's E7-reproduction fixture. JA49's "45 % vs 35 % unexplained" is closed by E11.
- **P2 (JA39) — unrounded tolerance.** pp ASSD and pp bias are within **0.035 mm** to 0.5 mm and 0.07 mm at 1.0 mm,
  compared unrounded.
- **P3 (JA42 step 4) — the relative RC.** Replace "Spearman ρ(|Δ|, mean D) > 0.4 → log ratios, applied
  multiplicatively" with:
  - "for thinning and hypoattenuation, if ρ(|Δ|, mean patient level) > 0.4, RC is computed on Δ ÷ level and applied
    as RC_rel × level";
  - "fat's RC is always on differences (mm³)".

  This was India v3's clause. As written it cannot act.
- **P4 (JA37) — the band is part of the estimator.** The guard's vol estimator is evaluated in the JA37 band. JA37's
  validation is repeated on an open-base phantom. If it does not pass at 0.05 mm, the guard is 0.5 mm.
- **P5 (JA46 (d)) — 4B on LM only.** 4B is allowed on LM only; per vessel, ≥ 70 % stenosis on LAD, LCx or RCA is 4A.
  LM's grade feeds the LAD and LCx territories in Table B.
- **P6 (JA46 (a)) — blank cases get a check seed.** Blank cases are checked against a seed that readers are never
  served. The hinge-point fallback is withdrawn. The footprint carries a 3 mm margin.
- **P7 (JA48) — 360 cases.** The reference population is the derived **360**, seal extension excluded.

**No lead question.** None of P1–P7 changes the plan's structure. P1 changes a printed number in the conservative
direction, as JA40 already demands.

## 12. Disclosures and limits

- **E11 uses one seed sequence.** Rows near the 0.80 line (within 0.02) could move one 0.05 step on another seed. The
  median trend holds across five medians.
- **The S5 phantom checks** use `janusm_reads.phantom` only. The blank-case leniency on real reads depends on
  how far a real mitral gap sits from where an overreaching read places it; the phantom shows the mechanism, not the
  rate.
- **IG1's 24 % under-read** is measured on Hotel E6's open phantom. On a real LV mask the share of non-moving surface
  (the valve planes) sets its size.
- **What India did not run:** the Mongo integration suite (CI runs it) and the Slicer self-test (by hand only).
- **India's own R3 clause** (JA42's log branch) is the one shown ill-posed here (IG8, P3).

---
aliases: [India v5]
tags: [janus-m, plans, candidate, round-5, india, myocardium, path-rest-ccta, build-check]
status: submitted
round: 5
path: jm/rest-ccta
advocate: India
updated: 2026-10-30
issue: christianGRogers/Asclepius#223
---

# India v5: the Round 4 fixes checked test by test, and the cap remedy for the open-base guard

**Advocate:** India. **Round:** 5, path `jm/rest-ccta` (LQ1 option A), under LQ34 (b): only Round 4 §8
items 2–3, plus item 1 if JM-0 / JM-0R aggregates are posted. **Base:** the plan in force, [[Hotel v3]]
with JA37–JA49 and JA60–JA69 ([[Janus-M Round 4 rest-ccta]]). **What was checked:** `jm/rest-ccta` with
`origin/dev` merged (#221 was still open; `dev` at `e5d3c9a`, carrying #216–#220).

**Evidence:** the CPU checks in `experiments/JanusM/India/r5/`:
- `b1_band_remedy` (item 2): the shipped band, the remedy as worded, and the remedy scoped to the cut cap,
  on the shipped open-base phantoms, the closed shells, and the label-4 phantom;
- `b2_cap_sensitivity` (item 2): the scoped remedy over its two free parameters;
- `a1_phase_mix` (item 3): S3 called with JA60's ED-only mix.

**Suite runs (CPU), per group:**

| Group | Files | Result |
|---|---|---|
| A | `test_janusm_calibrate`, `_jm0r_decide`, `_jm0r_readout` | 112 passed |
| B | `test_janusm_harness` (all 44, including every `slow` one) | 44 passed |
| C | `test_janusm_reference`, `_report`, `_features`, `_geometry` | 125 passed |
| D | `test_janusm_reads`, `_read_module`, `test_segqueue_server_janusm` | 140 passed, 20 skipped here |
| E | `test_janusm_score_decision` | 17 passed |

Group D's 20 skips:
- 19 need MongoDB. CI's "Server against a real MongoDB" job runs them, and turns any skip into a failure.
- 1 needs girder. It skips in every job; its behaviour is covered by the Mongo job's twin.

All of #220's check runs are green.

**Rules kept.**
- No case, image or label was opened.
- Each script calls `janusm.guard.refuse([])` first, which records that nothing is opened.
- Every input is a synthetic phantom built in code.
- No SciNet, Alliance or Fir job was run.
- `score_decision.py` was never run with `--run`.
- No shipped code was changed.
- No outside request is drafted (D31).

---

## 1. Summary

- **Item 1: every R4-S1…S23 item merged with its named test, and every named test passes.**
  - **Three code defects** against the ruling:
    - **S3 crashes on JA60's own hypoattenuation mix** `{"ED": 1.0}` (`KeyError: 'MD'`). Shipped callers are
      unaffected only because `reference.py` passes all three keys.
    - **The mitral plane falls through to the read's own gap** when a seed exists but cannot be fitted.
      JA66 allows that only "when no seed exists".
    - **The lesion-point bounds check fails open** when the CT header cannot be read. JA67 says outside points
      are refused.
  - **Twelve named tests are weaker than ruled** (§2.6).

  None of these has touched a real case. Each becomes a `role:swe` spec (§6).
- **Item 2: the remedy as worded cannot be adopted.** "Any pool or myocardium face that adjoins label 0"
  includes the whole epicardium, so it empties the epicardial band.
  - **Scoped to the cut cap, it passes JA61's check with margin.** A cap face is a solid face on label 0
    that faces the same way as the nearest open pool face.
  - **The numbers:** E6-open worst falls from **0.068** to **0.015** mm, and the cut capsule from
    **0.0504** to **0.024** mm. Closed shells and the label-4 phantom are unchanged.
  - **Proposed as an amendment (§3.5).** It would return the guard to 0.3 mm at the freeze PR, still subject
    to the transfer check on real reads.
- **Item 3: of the eleven judgement calls, nine are accepted, one is accepted with a fix and one is rejected**
  (§4). The rejected one is "`calibrate.population` raises on a phase_mix that omits phases". It raises by
  accident, and on the input JA60 rules.
- **Item 4: not applicable.** No JM-0 / JM-0R aggregate has been posted (none in #205, none in the repo), so
  R0–R10 are not recorded, and R9 keeps the provisional 45 %.

---

## 2. Item 1: each R4-S item against its named test (Round 4 §7)

**Columns:**
- **Test:** the function that implements the ruled test.
- **As ruled?:**
  - **yes:** it checks what the ruling says;
  - **weaker:** it checks less, and the cell says how;
  - **changed:** the test had to change, and the cell gives the reason.
- **Result:** the local run. "CI" means it skips here but ran and passed in a CI job that refuses skips.

### 2.1 Group A, the detectable depth (#217; `calibrate.py`, `jm0r_decide.py`, `jm0r_readout.py`)

| Item | Ruled test | Test | As ruled? | Result |
|---|---|---|---|---|
| S1 | E7 rows reproduce with `median_mm=9.668` | `test_janusm_calibrate::test_e7_primary_rows_reproduce`, `::test_e7_every_replicate_reproduces`, `::test_e7_lookup_rows_reproduce` | yes (4 dp, every replicate) | pass |
| S1 | `detectable_depth(0.088, LIMA_SHAPE, 1.0, seed=31000)` → 0.45 | `::test_ja60_default_anchor_is_the_ed_median_and_gives_the_provisional_45` | yes (`== 0.45`, anchor 5.7, version 1.1.0, warning) | pass |
| S1 | `measured_median_mm=6.3` → simulated median 6.3 ± 1 % | `::test_ja60_measured_median_is_the_simulated_median` | weaker: it calls `anchor_mm` + `population()` directly, not `detectable_depth`. The wiring is pinned separately by `::test_ja60_detectable_depth_simulates_on_the_anchor_of_the_measured_wall` (mocked `simulate`) | pass |
| S1 | both inputs raise | `::test_ja60_both_walls_raise` | yes (both functions) | pass |
| S1 | `population_factor` at Lima's inputs 1.109 ± 0.002 | `::test_ja60_population_factor_at_limas_inputs` | yes (1.10873) | pass |
| S2 | a recording `depth_fn` receives JM-0R's median | `test_janusm_jm0r_decide::test_r9_calls_detectable_depth_with_cv_n_shape_the_f1_floor_and_the_measured_wall` | yes | pass |
| S2 | missing median → NOT DECIDABLE | `::test_r9_missing_median_is_not_decidable` | yes (exact line; S3 not called; 45 %) | pass |
| S2 | cv_n = 0 prints the NOT DECIDABLE line | `::test_r9_s3_refusal_prints_not_decidable` (real S3) | yes | pass |
| S2 | R3 failure adds the note | `::test_r9_r3_failure_adds_the_note` | yes | pass |
| S2 | the provisional string reads 45 % | `::test_r9_provisional_print_reads_45_percent` | yes | pass |
| S2 | acceptance test on jittered rows, `depth is not None` | `test_janusm_jm0r_readout::test_the_decision_script_on_the_synthetic_summary_is_decidable`; identical rows: `::test_the_decision_script_on_identical_rows_prints_s3s_refusal` | yes, both as JA60 splits them | pass |
| S3 | pooled and median shares straddle 0.10; `decision_inputs` follows the median | `test_janusm_jm0r_readout::test_septal_arc_pooled_flag_is_reported_and_r7_follows_the_case_median` | yes, both directions | pass |

**Code bullets.** All present:
- `population_factor` (`calibrate.py` 150–175);
- `_anchor` (305–320);
- `phase_mix=` (332, 414);
- `inputs` (382–388);
- version 1.1.0 (53);
- `jm0r_decide.py`: median passed (387–388), refusal branch (389–392), R3 note (402–403), 0.45 (93),
  `DECIDE_VERSION` "2" (55).

**Two deviations:**
- **S3's "docstring" is a comment** (`jm0r_readout.py` 594–597). The substance is as ruled.
- **A defect `test_ja60_…phase_mix` hides.** The test passes `{"ED": 1.0}` but mocks out `simulate`, the code
  that crashes on it. See §4.2 and SW5-A1.

### 2.2 Group B, the harness (#219; `harness.py`)

| Item | Ruled test | Test | As ruled? | Result |
|---|---|---|---|---|
| S4 | India's open-base phantom (2 grids, 3 walls, both borders, ±0.3 / ±0.5) within 0.05 mm with the band | `test_janusm_harness::test_open_base_india_phantom_with_the_band` | changed, because the check fails. It asserts that the band beats the whole mask on all 48 rows, that the endocardium and every ±0.3 row are within 0.05, that the check fails (`assert not passed`), and that the guard is 0.5. It does not pin the worst value (0.068 is in a comment only) | pass |
| S4 | `validate_bias_estimator(open_base=True)` | `::test_validate_bias_estimator_open_base` | weaker: it runs with `n_offsets=1` (the default is 3) and accepts either verdict (`worst ≤ 0.06`, guard follows `passed`). It does not reproduce the 0.0504 the code comment cites | pass |
| S4 | E4's closed shells within ±0.01 | `::test_e4_closed_shells_stay_within_a_hundredth_in_the_band` (r 12, 21) | yes (endocardial band) | pass |
| S4 | a change only within 3 mm of label 4 → bias 0 ± 0.01 | `::test_a_change_within_3mm_of_label_4_moves_the_banded_bias_by_nothing` | yes; also shows that the whole mask sees the change | pass |
| S4 | the band excludes every voxel ≤ 3 mm from label 4 and from an open pool face | `::test_ja37_band_excludes_label_4_and_open_pool_faces` | yes (brute-force face centres, both borders) | pass |
| S5 | median 0.04 → 0.3 | `::test_transfer_check_median_under_the_limit_keeps_0_3` | yes; also `bias_guard_applied_mm == 0.5` | pass |
| S5 | 0.06 → 0.5 | `::test_transfer_check_median_over_the_limit_gives_0_5` | yes | pass |
| S5 | 19 rows → error | `::test_transfer_check_refuses_fewer_than_20_rows` | yes; also NaN or a missing key | pass |
| S5 | row 21 ignored | `::test_transfer_check_ignores_row_21` | yes | pass |
| S6 | `test_e6_pp_within_ja39_tolerances` unrounded | `::test_e6_pp_within_ja39_tolerances`, `::test_ja65_tolerances_are_0035_and_007` | yes (`abs(err) <= tol`) | pass |
| S6 | `surface_assd` equals segtrain (0.47283) | `::test_surface_assd_is_segtrains` | yes | pass |

**Code bullets.** All present:
- `ja37_band` (`harness.py` 351–389);
- `signed_bias(roi=)` (316–348), with faces by centroid in `surface_area` (287–313);
- `compare(roi="ja37")` passes the band to `signed_bias`, `signed_bias_pp` and `assd_pp` (489–497);
- `validate_bias_estimator(open_base=True)` (712–819);
- the old test asserting that `signed_bias` ignores its ROI is removed (030a911);
- JA37's real-wall disclosure is in the docstring (322–330);
- 1.2.0 (74);
- the failure and its cause are recorded at 84–91, and in #219's body ("the issue says so" is met).

**One small deviation.** The module docstring (56–58) still says Hotel E6 was validated "within 0.03 mm". JA65
says 0.035.

**R4-S4's result (Round 4 §8 item 3), recorded.**
- **FAIL:**
  - India E6-open, worst 0.068 mm (epicardium, ±0.5);
  - cut capsule, worst 0.0504 mm (epicardium);
  - the endocardium is within 0.015 / 0.024 mm.
- **Under JA61, the bias guard is 0.5 mm from the freeze PR on.** `BIAS_GUARD_VALIDATED_MM = 0.5`, and the
  scorer's `bias_guard_mm` is never below it (d1913f3).
- §3 proposes how to recover 0.3 mm.

### 2.3 Group C, reference population and table (#218)

| Item | Ruled test | Test | As ruled? | Result |
|---|---|---|---|---|
| S7 | 20 patients × 3 territories → 1.4606 (χ² 8.907) | `test_janusm_reference::test_chi2_factor_at_20_patients`, `::test_rc_is_the_upper_95_bound_pooled_by_default` | yes (n_patients 20, n_values 60) | pass |
| S7 | rewrite `test_rc_is_the_upper_95_bound_pooled_by_default` | same, plus `::test_rc_counts_patients_by_the_case_index` | yes | pass |
| S7 | +0.4 LAD / −0.4 LCx add to LAD and LCx, not RCA | `::test_rc_adds_each_territorys_own_offset` | yes | pass |
| S7 | 14-vs-15 territory boundary | `::test_rc_own_sd_needs_15_patients[14/15]` | yes (patients) | pass |
| S8 | proportional thinning noise → relative; floor = RC_rel × E | `::test_rc_switches_to_relative_when_error_grows_with_e` | weaker: the d and E arrays are built by hand, not by `case_state` | pass |
| S8 | multiplicative fat noise stays on differences (mm³) | `::test_fat_multiplicative_noise_stays_on_differences` | yes | pass |
| S8 | gate and report give the same floor for the same E | `test_janusm_report::test_the_gate_and_the_report_produce_the_same_floor_for_the_same_e` | yes (a spy on `rc_floor_mm`) | pass |
| S8 | ρ > 0.4 with E ≤ 0 stays on differences, recorded | `test_janusm_reference::test_rc_stays_on_differences_when_e_is_not_positive` | yes; it also pins the per-read rule (§4.3) | pass |
| S9 | a fat segment that changes territory moves D | `::test_a_fat_segment_that_changes_territory_moves_d` | weaker: it uses hand-edited cluster dicts, not `case_features` on a changed patient map | pass |
| S9 | a forced fall-back is counted | `::test_a_forced_fallback_is_counted` | weaker: it covers `rc["decisions"]` only. The report header's note (`report.py` 332–334) is untested | pass |
| S10 | a recording S3 sees `measured_median_mm`, and for hypoattenuation the ED-only mix | `::test_gate_gives_s3_the_measured_wall[thinning/hypo]` | yes, with the three-key ED mix (§4.3) | pass |
| S11 | a monkeypatched version is refused | `test_janusm_report::test_a_version_mismatch_is_refused[G/F]` | yes | pass |
| S11 | sha matches under `LC_ALL=C` | `test_janusm_reference::test_config_sha_matches_under_the_c_locale` | yes (subprocess, non-ASCII bytes present) | pass |
| S11 | golden config byte-identical | `::test_golden_config_is_byte_identical` | yes (300 hearts, seed 11, regen flag) | pass |
| S12 | one-segment phantom "shared" only with the flag on | `test_janusm_report::test_one_segment_is_shared_only_with_r8_on` | weaker: the geodesic majority is monkeypatched, not produced by geometry | pass |
| S12 | `--run` without `--geodesic-shared` refused | `test_janusm_reference::test_cli_run_without_geodesic_shared_is_refused` | yes | pass |
| S13 | LM 4B → LAD and LCx significant, RCA not | `test_janusm_report::test_lm_feeds_lad_and_lcx`, `::test_lm_grade_in_the_table` | yes | pass |
| S13 | round trip from an export record | `::test_grades_round_trip_from_an_export_record` | weaker: the record is hand-written to mirror `export.readRecord`, which is never called | pass |
| S13 | distal-mass label | `::test_distal_mass_label` | yes | pass |
| S14 | at 120° arc = fixed (±0.01) | `test_janusm_features::test_arc_values_at_120_degrees_equal_the_fixed_values` | yes | pass |
| S14 | at 180° the share moves | `::test_arc_at_180_degrees_moves_the_septal_share` | yes (1/3 → 1/2) | pass |
| S14 | JM-0R and geometry agree | `::test_jm0r_and_geometry_agree_on_the_phantom` | yes (same object, frozen copy) | pass |
| S14 | goldens regenerated | `test_janusm_report::test_golden_output[*]` | yes | pass |
| S15 | depth 0.50 passes, 0.55 fails | `test_janusm_reference::test_depth_050_passes_and_055_fails` | yes | pass |
| S15 | κ with 4 and 5 flagged units | `::test_kappa_with_4_and_5_flagged_units` | yes | pass |
| S15 | a pass with κ None | `::test_a_pass_with_kappa_none` | yes | pass |
| S15 | κ "not estimable" when pe = 1 | `::test_kappa_not_estimable_when_chance_agreement_is_one` | yes | pass |
| S15 | fat gate with and without an RC | `::test_fat_gate_with_and_without_an_rc` | yes | pass |
| S15 | Spearman exactly 0.4 | `::test_spearman_exactly_04_stays_on_differences` | yes | pass |
| S15 | Rule C, D ≤ RC → a number | `test_janusm_report::test_rule_c_and_gate_pass_with_d_at_most_rc_is_a_number` | yes | pass |
| S15 | D on the patient map | `test_janusm_reference::test_d_is_on_the_patient_map_not_aha` | yes | pass |
| S15 | `halves_note` in `test_header_fields` | `test_janusm_report::test_header_fields` | yes | pass |

**Code bullets.** All present (`reference.py`):
- the case index (449, 609);
- n = distinct cases (474), used in the bound and the switch (506, 524);
- each territory's own mean (525–530);
- the relative branch (485–504);
- `rc_floor_mm` (539), used by `gate` (664) and the report (`report.py` 152);
- no exp conversion or level 1.0;
- fall-backs counted (611–614);
- S10 (633–640);
- `calibrate_version` (710);
- UTF-8 bytes hashed (`build_reference.py` 114–119);
- `--geodesic-shared` required (143–146);
- `territory_grade` / `grades_from_read_record` (`report.py` 109, 127);
- `geometry.arc_segments`, imported by JM-0R.

**One gap in substance.** JA63 says any fall-back is "counted", but fall-backs are counted only over the 20 RC
cases (`reference.py` 611). Reads 21–40, which feed κ and ICC, are not counted (SW5-C1).

### 2.4 Group D, the read queue (#220)

| Item | Ruled test | Test | As ruled? | Result |
|---|---|---|---|---|
| S16 | Hotel E10 A fails | `test_janusm_reads::test_r4s16_hotel_e10_a_fails` | yes | pass |
| S16 | India's ring 6.2–8.7 mm fails | `::test_r4s16_india_ring_at_6p2_to_8p7_mm_fails` | yes | pass |
| S16 | India's +4 / +6 mm blank reads fail with the check seed | `::test_r4s16_india_blank_overreach_fails_with_the_check_seed` | yes; also shows that both pass when fitted to their own gap | pass |
| S16 | the exact phantom read passes | `::test_r4s16_the_exact_phantom_read_passes` | yes | pass |
| S16 | Mongo: a blank seed is never served (4xx, `hasSeed: false`); report "fitted to the seed" | `test_segqueue_server_janusm::test_r4s16_a_blank_read_is_checked_against_the_hidden_check_seed` | yes | CI |
| S16 | a plane-less read is returned uncounted | `::test_r4s16_a_plane_less_read_is_returned_uncounted`; `test_janusm_reads::test_r4s16_a_plane_less_read_could_not_be_checked_and_never_passes` | yes | CI / pass |
| S17 | Mongo: crash then failure → RETURNED unflagged; next failure → flagged | `test_segqueue_server_janusm::test_r4s17_a_crash_never_spends_the_return` | yes | CI |
| S18 | adds < 5 % of the union but ≥ 5 % of the seed → not "following" | `test_janusm_reads::test_r4s18_the_changed_share_is_over_seed_voxels` | yes | pass |
| S18 | exactly 5 % is not "following" | same | weaker: it asserts that the share is 0.05 but never runs it through `wave_report`. The code's `<` (`anchoring.py` 263) is right | pass |
| S18 | exactly half does not flag | `::test_r4s18_exactly_half_the_reads_following_does_not_flag` | yes | pass |
| S18 | arbitrary list, 4 of 5, 6 names → 400 | `test_segqueue_server_janusm::test_r4s18_third_reads_open_only_on_a_flagged_waves_draw` | yes, plus a duplicate, a substitute and a wrong wave | CI |
| S18 | no `reads/` record is a third read | `::test_export_feeds_the_anchoring_report` | yes | CI |
| S19 | bound recomputed with `default_rng(BOOTSTRAP_SEED)`, 0.95 quantile, equal | `test_janusm_reads::test_r4s19_the_bound_is_pinned` | yes (1e-12) | pass |
| S19 | a shared-index draw differs | same | weaker: it compares two hand-built computations and never calls the implementation. Independence is in fact pinned by the equality above | pass |
| S19 | one `None` ASSD → `gap == seedVsReadBlank − seedVsReadSeeded` | `::test_r4s19_rule1s_gap_is_the_reports_read_level_difference` | yes | pass |
| S20 | 4B on LAD and 3 on LM refused | `::test_r4s20_each_vessel_offers_only_its_cadrads_2_grades`; server: `test_two_independent_reads_and_the_read_check` | yes | pass / CI |
| S20 | a point 1 m away refused | server: `test_two_independent_reads_…`; unit: `test_janusm_reads::test_r4s20_a_point_a_metre_away_is_outside_the_ct` | yes | CI / pass |
| S20 | protocol 1 at `next` → 426, no read; update `test_protocol_refuses_missing_or_old_client` | `test_segqueue_server_janusm::test_r4s20_a_protocol_1_client_is_refused_at_next_before_any_claim`; `test_janusm_reads::test_protocol_refuses_missing_or_old_client` | yes | CI / pass |
| S21 | one test per change (Mongo and read module) | `test_r4s21_export_refuses_an_empty_wave`, `…skips_and_lists_…`, `test_export_feeds_…`; `test_janusm_read_module::test_r4s21_a_reopened_read_gets_its_form_back`, `…reading_clock_is_kept_across_reopening` | yes for the server. The read-module tests check source order only, and behaviour rests on the Slicer CI self-test | CI / pass |
| S22 | LV–RV contact ≈ 0.4 % passes, ≈ 0.6 % fails | `test_janusm_reads::test_r4s22_lv_rv_contact_at_0p4_pct_passes_and_0p6_pct_fails` | yes | pass |
| S22 | 3.0 mm passes, 3.5 mm fails on a seed-fitted plane | `::test_r4s22_the_pool_may_reach_3p0_mm_above_a_seed_fitted_plane_not_3p5` | yes | pass |
| S22 | unmeasurable endocardium → error; epicardium may skip | `::test_r4s22_an_unmeasurable_endocardium_is_an_error_and_the_epicardium_may_skip` | yes | pass |
| S22 | `move_border("septal")`, +1 mm reads +1.0 | `::test_r4s22_myocardium_grown_1_mm_into_the_rv_reads_plus_1_mm` | yes (±0.25) | pass |

**Code bullets.** All present:
- check seed uploaded to a reader-unreadable folder (`populate.py` 143–162);
- `seedFileId or checkSeedFileId` (`models.py` 102–105, `check.py` 84);
- reader routes never touch it (`rest.py` 55–67, 212–222, plus an AST test);
- the JA66 footprint (`checker.py` 87–91, 367–382);
- `returns` / `crashes` (`check.py` 61–74);
- the seed denominator (`anchoring.py` 87–94);
- `adminThirdReads` checks (`rest.py` 395–417);
- `third/` export (`export.py` 134–139);
- per-vessel grades;
- the bounds check (`rest.py` 242–252);
- `PROTOCOL_VERSION = 2`;
- doc §4.4 / §7;
- wave and export scope;
- the endocardium error (`checker.py` 608–612).

**Two defects against the ruling:**
- **JA66's plane order is not kept when a seed is unfittable** (`checker.py` 330–342).
  - When a seed or check seed exists but yields no fittable 2–4 interface (no LA in it, or too few points),
    the code falls through to the read's own gap.
  - JA66 says the read's gap is used "only when no seed exists". In that case the check is "could not be
    checked".
  - A blank case populated before #220 has no `checkSeedFileId`, so it is silently fitted to its own read.
    This is the hole JA66 closed, reopened for any case not re-populated. Nothing alerts the PM.
  - **This blocks the first read wave** (SW5-D1).
- **The lesion-point bounds check fails open** (`rest.py` 247–250, `niftihead.py` 118).
  - If the CT header cannot be read, `ctWorldBounds` is `None`, `points_outside(…, None)` returns `[]`, and the
    point is accepted with a server log line.
  - JA67 says outside points are refused. An unknown bound should refuse, not accept (SW5-D2).

### 2.5 Group E, the decision scorer (#216, d1913f3; `tools/janusm/score_decision.py`)

| Item | Ruled test | Test | As ruled? | Result |
|---|---|---|---|---|
| S23 | synthetic pairs on `exact_shift_phantom` give a known d and transfer verdict | `test_janusm_score_decision::test_known_d_and_transfer_verdict_on_exact_shift_phantom`, `::test_transfer_fails_to_half_mm_when_vol_and_pp_disagree` | weaker. The two reads are identical, so read-vs-read is 0, and d's subtraction and its average over two different reads are never exercised. The phantom only gives a "pass" verdict; "fail" is tested with a fake `compare` | pass |
| S23 | order kept; a one-read case skipped; `reads[:20]` are the first 20 complete | `::test_order_kept_and_one_read_case_skipped` | yes (reversed manifest) | pass |
| S23 | third reads dropped | `::test_third_reads_and_other_protocols_are_dropped` | weaker. The export puts third reads under `thirdRead` / `thirdReadRecord`, which `select_pairs` never reads, so the test passes by structure. The in-code filter (`rec.get("third")`, 187) is never exercised | pass |
| S23 | a seal, extension or JM-0 id refused before anything is opened | `::test_seal_extension_or_jm0_id_refused_before_anything_is_opened` | yes for "nothing opened" (the loader is never called). It does not check which error gave rc 3; by probe, all three give `HeldOutError` | pass |
| S23 | the same coronary array for both reads | `::test_same_coronary_array_for_both_reads` | yes (`is`) | pass |
| S23 | an id in the output is refused | `::test_an_id_in_the_output_is_refused` | yes | pass |
| S23 | `build_reference.py` accepts the output and refuses a mismatched `features_version` or `guard_mm` | `::test_build_reference_accepts_the_output_and_refuses_mismatches` | yes. A wrong per-read `guard_mm` inside the file is not tried | pass |

**Code bullets.** All present:
- **Guard first** (`main` 341–347). `guard.refuse(order, purpose="decision_scoring")` runs before any image,
  mask, read or layout loader.
  - The only files read before it are `sealed-r1.json` (hash-checked) and the manifests, which are where the
    names come from.
  - That is the only reading of "before opening any file" that can work.
- **List order** (122, 181).
- **Reader key** = sha256(salt + reader), never passed to `score()` (155–157, 194).
- **One coronary tree** (209–210).
- **`compare(roi="ja37")`** for model-vs-read 1, model-vs-read 2 and read 1-vs-read 2 (211–213).
- **`transfer_check`** on `rows[:20]` (222–236).
- **`assert_anonymous`** and the sha256 (268, 273, 366–368).
- **The Fir command without `--run`, and Slurm only** (331–337).

**Untested.** No test asserts that the reader id or key is absent from the output, despite a test's name; there
is no test of the sha256 or of a successful `--run` write (SW5-E1).

### 2.6 Summary of item 1

| Group | Items | Named tests | Weaker than ruled | Changed (with reason) | Code defects |
|---|---|---|---|---|---|
| A | S1–S3 | 12 | 1 (S1, 6.3 mm) | 0 | 1: S3 rejects `{"ED": 1.0}` (§4.2) |
| B | S4–S6 | 11 | 1 (`validate_bias_estimator(open_base=True)`) | 1 (S4's India test asserts the FAIL) | 0 (one stale docstring) |
| C | S7–S15 | 31 | 5 (S8 relative, S9 ×2, S12, S13) | 0 | 0 (fall-backs uncounted on reads 21–40) |
| D | S16–S22 | 24 | 3 (S18 5 %, S19 shared draw, S21 read module) | 0 | 2: JA66 plane order; bounds check fails open |
| E | S23 | 7 | 2 (d on two reads; third-read filter) | 0 | 0 |

- **Every named test exists and passes.** The one test that could not be written as specified (S4's "within
  0.05 mm") comes back with its reason: the check fails, and the test pins the failure and the 0.5 mm guard.
- **Before the freeze PR,** SW5-B1 (the cap band, if §3.5 is adopted) and SW5-D1 must merge. The rest are test
  hardening, plus SW5-A1, which only bites a future caller.

---

## 3. Item 2: R4-S4's open-base result and the #219 remedy

### 3.1 What failed, and why

- **The failure:** on India's E6-open phantom the shipped band brings the endocardium within 0.015 mm, but the
  epicardium misses at ±0.5 mm (worst 0.068 mm).
- **The cause, as #219's engineer found it:**
  - The cut basal cap of the myocardium adjoins label 0, but it is not an LV-pool face, so JA61's band keeps it.
  - When the epicardium moves, the cap ring widens but no volume is gained through it. Its area enters the
    denominator of `signed_bias` with no matching ΔV, so the estimate under-reads by ≈ 8–13 %.

### 3.2 The remedy as worded cannot be adopted

The remedy as worded: "also exclude ≤ 3 mm of any pool or myocardium face that adjoins label 0".

- **The problem:**
  - On every phantom, and on most of a real read, the epicardium is itself a myocardium face adjoining label 0
    (fat, lung, pericardium are unlabelled).
  - So "any" removes the epicardial band entirely, along with the closed shells' epicardium.
- **What `b1` measures (the `literal` band):**
  - on E6-open, the capsule and both E4 shells, no usable epicardial band remains. The few voxels left hold no
    surface, so the truth and the estimate are undefined;
  - on the label-4 phantom, it removes 82 % of the epicardial band (303 392 → 55 156 voxels), though that phantom has no open cap
    at all.
- **The remedy needs a qualifier:** which solid faces on label 0 are the cut cap?

### 3.3 The scoped remedy: cap faces only

**Definition (the `cap` band in `b1_band_remedy.py`).** Keep JA61's band, and also remove the voxels within 3 mm
of every **cap face**. A cap face is a solid (pool ∪ myocardium) voxel face adjoining label 0 that meets both
conditions:
1. it lies within **20 mm** (more than any LV wall) of an open pool face;
2. its outward normal (the gradient of the solid smoothed by one voxel) is within **45°** of that nearest open
   pool face's outward normal.

**Why this picks out the cap:**
- the cut cap faces the way the opening faces, because it is the same cut;
- the lateral epicardium is perpendicular to the opening;
- the apex faces away from it.

**What it needs:** no base plane, no aorta label and no new input. It is one more step in `ja37_band`.

**When it changes nothing:**
- where no pool face opens to label 0 (closed shells; a pool that opens into the LA, label 4);
- for the endocardial band, except the 3 mm next to the rim, which JA61 already removes.

### 3.4 Results (the same phantoms the shipped tests use; JA61's pass is |error| ≤ 0.05 mm on every row)

| Phantom set | Rows | Shipped band (JA61) | Remedy as worded | Cap-scoped remedy |
|---|---|---|---|---|
| E6-open, endocardium ±0.3 / ±0.5 | 12 / 12 | 0.0086 / 0.0150 | 0.0086 / 0.0150 | 0.0086 / 0.0150 |
| E6-open, epicardium ±0.3 / ±0.5 | 12 / 12 | 0.0422 / **0.0678** | no usable band | 0.0103 / 0.0146 |
| **E6-open, verdict** | 48 | **FAIL** (0.0678) | **cannot be scored** | **PASS** (0.0150) |
| Cut capsule, endocardium ±0.3 / ±0.5 | 36 / 36 | 0.0238 / 0.0196 | 0.0238 / 0.0196 | 0.0238 / 0.0196 |
| Cut capsule, epicardium ±0.3 / ±0.5 | 36 / 36 | 0.0404 / **0.0504** | no usable band | 0.0192 / 0.0116 |
| **Cut capsule, verdict** (3 offsets, as the validator's default) | 144 | **FAIL** (0.0504) | **cannot be scored** | **PASS** (0.0238) |
| E4 closed shells r 12 / r 21, both borders | 8 / 8 | 0.0038 / 0.0019 | epicardium empty | 0.0038 / 0.0019 (identical) |
| Label-4 phantom (`harness.phantom`), band voxels | endo / epi | 149 660 / 303 392 | 149 660 / **55 156** | identical to shipped (bit for bit) |

All cells give the worst |error| in mm. The shipped column reproduces #219's numbers exactly (0.068 and 0.0504).
- **Remedy as worded:** a few voxels survive, 1–4 % of the shipped epicardial band, but none of them lies on the
  surface, so neither the truth nor the estimate is defined.
- **Cap-scoped remedy, what it costs:**
  - it keeps 83–85 % of the shipped epicardial band on the upright walls, and 59–74 % on the 23° oblique and
    rough walls;
  - it keeps ≥ 98 % of the endocardial band;
  - I did not isolate which extra faces the oblique and rough walls lose. Accuracy is unaffected (every row
    passes), but SW5-B1 should report the kept share.

**Sensitivity (`b2`).** The scoped remedy's two free parameters were varied: reach 12 / 20 / 30 mm and angle
30 / 45 / 60°. The table gives the worst |error| on E6-open (0.5 mm grid, three walls) and the capsule (0.5 mm
grid, three walls), and the smallest share of the shipped epicardial band each setting keeps:

| Reach (mm) | Angle | E6-open worst | Capsule worst | Epicardial band kept (min) |
|---|---|---|---|---|
| 12 | 30° | 0.0430 | 0.0238 | 0.897 |
| 12 | 45° | 0.0145 | 0.0238 | 0.785 |
| 12 | 60° | 0.0142 | 0.0238 | 0.761 |
| 20 | 30° | 0.0390 | 0.0238 | 0.845 |
| **20** | **45°** | **0.0145** | **0.0238** | **0.622** |
| 20 | 60° | 0.0142 | 0.0238 | 0.547 |
| 30 | 30° | 0.0391 | 0.0238 | 0.843 |
| 30 | 45° | 0.0152 | 0.0238 | 0.561 |
| 30 | 60° | 0.0149 | 0.0238 | 0.399 |

- **Every setting passes at 0.05 mm,** so the verdict does not depend on a tuned value.
- **The angle matters more than the reach.** At 30°, part of the oblique cap escapes, and the E6 worst rises to
  ≈ 0.04 mm, which is inside the tolerance but with little margin. At 45° and 60° it is ≈ 0.015 mm.
- **A wider angle or reach gives up more band for no gain.**
- **The proposed setting is 20 mm / 45°.**
  - 45° is the smallest angle with full margin.
  - 20 mm is the reach that covers a cap on any LV wall.
  - 12 mm does as well here only because the phantom walls are ≤ 14 mm, and the outer edge of the cap matters
    little.

### 3.5 Proposed amendment (for the Round 5 judge, from JA70)

- **P1, JA61's band excludes the cut cap.**
  - `ja37_band` also removes the voxels within 3 mm of every cap face (§3.3: a solid face on label 0, within
    20 mm of an open pool face, with its normal within 45° of that face's normal).
  - The remedy as worded ("any … face that adjoins label 0") is not adopted: it empties the epicardial band.
  - **Re-run JA61's check with the new band** (`validate_bias_estimator(open_base=True)` at its default three
    offsets, and India's E6-open):
    - **if it passes at 0.05 mm,** `BIAS_GUARD_VALIDATED_MM` returns to 0.3 mm from the freeze PR on;
    - **otherwise it stays 0.5 mm.**
  - **The transfer check on the first 20 decision reads stays the last word on real walls,** under JA37 and
    JA62. A failure there still sets 0.5 mm.
  - `HARNESS_VERSION` 1.3.0.
  - **Why:**
    - the failure is a phantom artefact of a fixed cap with no counterpart in ΔV, not an estimator error on
      moving walls;
    - excluding it is the same reasoning JA37 applied to the LA and the aortic opening;
    - on real reads most of the myocardial base adjoins label 4 and is already excluded, so the change is small
      there, and it can only remove area that does not move.
- **P2, the open-base tests pin numbers.** Whatever P1's outcome:
  - `test_validate_bias_estimator_open_base` runs the default three offsets and asserts the verdict that sets
    `BIAS_GUARD_VALIDATED_MM`;
  - India's test asserts the worst error to ±0.005 mm, so a later change cannot move the guard silently.
- **Not proposed:** changing the 0.05 mm tolerance. A tolerance relaxed to fit the miss would be the wrong fix.

---

## 4. Item 3: the engineers' judgement calls

### 4.1 #217 (Group A)

- **`numbers_only=True` whenever no depth is computed: accepted, with a fix to the record.**
  - **Where:** `jm0r_decide.py` 407 (`numbers_only = not computed or depth is None`).
  - **What JA60 says:** numbers only on S3's refusal, which is as ruled.
  - **The extensions:**
    - **depth not reached by 0.60:** also numbers only. This agrees with `calibrate.page_line`, which prints
      "numbers only";
    - **missing median:** JA60 says "NOT DECIDABLE … and the provisional print". Shipping a thinning flag on a
      depth never computed on this population is what JA41 forbids, so numbers only is the safe reading.
  - **The record contradicts itself:** for a missing median, R9's outcome text still says the page "prints the
    provisional 45 % … until it can be computed" (378–381), while `numbers_only` is true.
  - **Fix (SW5-A2):** the missing-median outcome text names numbers only and keeps the 45 % as the footer
    label, as the refusal branch does.
  - **Note:** nothing consumes `numbers_only` yet; it is metadata in `decisions.json`.

### 4.2 `calibrate.population` raises on a phase_mix that omits phases: rejected

- **The evidence:** `a1_phase_mix.json`:
  - `detectable_depth(0.088, LIMA_SHAPE, 1.0, seed=31000, measured_median_mm=6.3, phase_mix={"ED": 1.0})`
    raises `KeyError: 'MD'`;
  - the same call with `{"ED": 1.0, "MD": 0.0, "SYS": 0.0}` returns 0.45;
  - `population_factor({"ED": 1.0}, …)` works (0.9952), because `_phase_key` fills missing phases with 0.
- **Why it is rejected:**
  - **It contradicts the ruling.** JA60 rules hypoattenuation "with `phase_mix = {"ED": 1.0}`", and calibrate's
    own docstring (433) says the same.
  - **It contradicts the module itself.** One function accepts the mix, and the next crashes on it.
  - **It raises by accident.** The error is an unhandled `KeyError` (`population`, 118), not a designed
    `ValueError`. R9's `except ValueError` (decide 389) would not catch it, so a future ED-only caller would
    crash `jm0r_decide.py` instead of printing NOT DECIDABLE.
  - **The test hides it.** `test_ja60_…` passes `{"ED": 1.0}` with `simulate` mocked out.
- **Fix (SW5-A1):** `population` normalises the mix through `_phase_key` (missing phases = 0). It raises
  `ValueError` only on an unknown key, a negative weight, or a sum ≠ 1. The test runs unmocked.

### 4.3 #218 (Group C)

- **The full phase-mix dict is passed to S3: accepted.**
  - `reference.HYPO_PHASE_MIX = {"ED": 1.0, "MD": 0.0, "SYS": 0.0}` gives the same distribution as JA60's
    `{"ED": 1.0}`. It is the engineer's correct workaround for §4.2.
  - Once SW5-A1 merges it is redundant but harmless.
- **The relative RC needs E_T > 0 per read: accepted.**
  - **Where:** `reference.py` 493–494 requires both reads' E_T > 0, and not `None`, for every pair.
  - **It matches JA64's text.** JA64 defines E_T per read ("each read's territory has an expected level"), so
    "E_T > 0 for every pair" means both members of the pair.
  - **It is stricter than Ē > 0.** One read with E ≤ 0 keeps that whole sign on differences, with the decision
    recorded.
  - **It is safe.** A relative RC on a read whose expected level is ≤ 0 has no meaning; JA64's own reason (a
    ratio of a signed level is undefined) applies.
- **The septal-arc cell shows two values: accepted.**
  - The cell shows the arc wall with its percentile, then the arc relative subendocardial HU with its
    percentile, e.g. "7.52 (p52); 1.00 (p50)", under the header "thickness mm; rel. subendo HU".
  - R4-S14 tells `features` to add both quantities and `reference` both percentiles. The ruling does not say
    one value.
  - R7 still keeps or drops the whole column.
- **An LM lesion point labels both LAD and LCx: accepted.**
  - This is JA67's "LM feeds LAD and LCx" carried to the distal-mass note (`report.py` 313).
  - The note says only "not computed (report v1)", so no number moves.
  - When R4-S13 (b)'s definition is ruled, the judge should say whether LM's distal mass is split or shared.

### 4.4 #216 (Group E)

- **The transfer check runs per comparison, and any failure gives 0.5 mm: accepted.**
  - **What runs:** `transfer_check` runs on the first 20 rows of each of model-vs-read 1, model-vs-read 2 and
    read-vs-read (`score_decision.py` 80, 222–236).
  - **How the guard is set:** `passed` = all three; the guard = max(the three, `BIAS_GUARD_VALIDATED_MM`).
  - **Against JA62:** it says `compare` runs "for model-vs-read and read-vs-read" and that the transfer check
    sets 0.5 mm when the median exceeds 0.05 mm, without naming which rows. Every comparison is real walls, so
    each one is evidence on whether the volume estimator transfers. Taking the worst can only raise the guard.
  - **Today it is a no-op:** the guard is already 0.5 mm.
  - **If P1 restores 0.3 mm,** a read-vs-read failure alone would hold the model's guard at 0.5. That is
    conservative, and I keep it.
  - **Untested:** no test makes a single comparison fail (SW5-E1).

### 4.5 #220 (Group D)

- **`phantom.heart()` defaults to a 2 mm mitral gap: accepted.**
  - Under JA66 a gap-less phantom has no fittable plane and is "could not be checked". Without the default,
    every test expecting the default phantom to pass would have broken.
  - The old shape stays available as `mitral_gap_mm=None`. That test now asserts an error, which JA66 requires.
  - No numeric expectation was loosened.
- **`adminThirdReads` takes the anchoring report: accepted, with a recorded limit.**
  - **What the server computes itself:**
    - the seeded set, from the wave's accepted double reads;
    - the draw, `third_read_cases(wave, seeded)`;
    - it refuses any `cases` not exactly equal to the draw.
  - **What the report supplies:** only the wave, `rule2.flagged` and its seeded rows, which must match.
  - **The limit:** `flagged` is self-attested JSON. An admin could open third reads on an unflagged wave, but
    only on the server's own draw, never on chosen cases.
  - **Why it is accepted:** JA68 says "takes a wave", and the server stores no report, so passing the report is
    the practical stand-in. The residual risk is admin-only and cannot pick cases.
  - **SW5-D3 (low priority):** store the report's sha256 at export, and accept only that report.
- **A new `POST admin/wave`: accepted.**
  - It is admin-only, and sets `JanusMCase.wave` on named, existing cases. R4-S21's `export --wave` needs a
    setter. It is documented in §7.
  - Moving cases after a report changes the seeded set, so `adminThirdReads` refuses: it fails closed.
- **The 0.3.0 bump, with 426 for 0.2.x clients: accepted.**
  - These are two numbers:
    - the plugin and client package version 0.2.0 → 0.3.0;
    - the wire `PROTOCOL_VERSION` 1 → 2, with `MIN_CLIENT_PROTOCOL = 2`.
  - The 426 is keyed on the wire protocol. Both 0.1.0 and 0.2.0 clients send protocol 1, so both are refused
    at `next`, `getProject` and `submit`, before any claim.
  - The ruling's "0.1.0 clients get 426" understated it, since 0.2.0 merged before the ruling and also speaks
    protocol 1. The engineer's wording is the accurate one, and this matches JA67.

### 4.6 Tally

| Call | Verdict |
|---|---|
| #217 `numbers_only` when no depth | accepted, with a fix to the record (SW5-A2) |
| `population` raises on an omitted phase | **rejected** (SW5-A1) |
| #218 full phase-mix dict to S3 | accepted |
| #218 E_T > 0 per read | accepted |
| #218 two values in the septal-arc cell | accepted |
| #218 LM point labels LAD and LCx | accepted |
| #216 transfer check per comparison, any failure → 0.5 | accepted |
| #220 2 mm mitral gap default | accepted |
| #220 `adminThirdReads` takes the report | accepted (SW5-D3, low priority) |
| #220 `POST admin/wave` | accepted |
| #220 0.3.0, 426 for 0.2.x | accepted |

---

## 5. Item 4: JM-0 / JM-0R

**Not applicable this round.**
- **No aggregate has been posted:** none in #205's comments, and no `thickness_median_mm` aggregate in the
  repository other than synthetic test rows.
- **So `jm0r_decide.py` was not run,** and R0–R10 are not recorded.
- **R9's page keeps the provisional 45 %** (JA60).

**When aggregates are posted:**
- R4-S1, S2 and S10 are merged, so `jm0r_decide.py` can run as Round 4 §8 item 1 says.
- If a future caller passes JA60's ED-only mix, SW5-A1 must merge first.

---

## 6. `role:swe` specs for the PM (not built; label `path:jm-rest-ccta`; cite #223 and the Round 4 ruling)

### SW5-A1 — S3 takes an ED-only mix (`src/janusm/calibrate.py`; dev)
- **Wrong:** `population()` indexes `phase_mix[k] for k in PHASES` (118). `{"ED": 1.0}` (JA60) raises
  `KeyError`, which R9's `except ValueError` does not catch.
- **Correct:**
  - normalise through `_phase_key` (missing phases = 0);
  - raise `ValueError` on an unknown key, a negative weight, or a sum ≠ 1;
  - `CALIBRATE_VERSION` 1.1.1.
- **Tests:**
  - unmocked `detectable_depth(…, phase_mix={"ED": 1.0})` equals the three-key call (0.45 at
    `measured_median_mm=6.3`);
  - `{"ED": 0.5}` raises `ValueError`;
  - `{"XX": 1.0}` raises `ValueError`.

### SW5-A2 — R9's missing-median record (`experiments/JanusM/fir/jm0r_decide.py`)
- **Wrong:** the outcome text says the page prints 45 %, while `numbers_only` is true.
- **Correct:** the text says "numbers only; 45 % provisional (JA40)" as the refusal branch does.
- **Test:** the string, in `test_r9_missing_median_is_not_decidable`.

### SW5-B1 — The cut cap in JA37's band (`src/janusm/harness.py`; only if P1 is adopted). Blocks the freeze PR
- **Correct:**
  - `ja37_band` removes the voxels within 3 mm of cap faces (§3.3: reach 20 mm, angle 45°);
  - re-run JA61's check, and set `BIAS_GUARD_VALIDATED_MM` from its verdict;
  - `HARNESS_VERSION` 1.3.0;
  - regenerate the report goldens' version line.
- **Tests:**
  - India's E6-open and `validate_bias_estimator(open_base=True)` (three offsets) within 0.05 mm, worst values
    pinned to ±0.005 mm;
  - E4's shells unchanged;
  - the label-4 phantom's band unchanged (bit-identical);
  - a lateral epicardial face on label 0 is never a cap face.
- **Reference implementation:** `experiments/JanusM/India/r5/b1_band_remedy.py` (`cap_faces`, `band_cap`).

### SW5-B2 — Open-base tests pin their numbers (`tests/test_janusm_harness.py`; whether or not P1 is adopted)
- `test_validate_bias_estimator_open_base` runs the default three offsets, and asserts `passed` equals the
  verdict behind `BIAS_GUARD_VALIDATED_MM`.
- India's test pins the worst error to ±0.005 mm.
- Fix the module docstring's "0.03 mm" to JA65's 0.035.

### SW5-C1 — Fall-backs on every read (`src/janusm/reference.py`, `report.py`)
- Count AHA fall-backs over all 40 decision cases (κ / ICC reads 21–40 included), not only the 20 RC cases.
- Test the report header's note.
- Make S9's territory-change test and S12's "shared" test end to end through `case_features` on a phantom
  whose patient map really differs.
- S13's round trip calls `export.readRecord` where girder is importable, and skips with a reason otherwise.

### SW5-D1 — JA66's plane order when a seed is unfittable (`src/janusm_reads/checker.py`, `check.py`, `populate.py`). Blocks the first read wave
- **Wrong:**
  - a seed or check seed that exists but yields no fittable 2–4 interface falls through to the read's own gap
    (330–342);
  - a blank case with no `checkSeedFileId` is silently fitted to itself.
- **Correct:**
  - the read's gap is used only when the case has no seed and no check seed;
  - an unfittable seed is "could not be checked" (JA68's crash path: returned, not counted, PM alerted);
  - `check.py` refuses to check a blank case that lacks `checkSeedFileId`, and alerts;
  - `populate.py --backfill-check-seeds` is documented in the protocol doc.
- **Tests:**
  - a seed without label 4 gives "could not be checked", never the read's gap;
  - a blank case without a check seed is refused, not fitted to itself.

### SW5-D2 — The lesion-point bounds check fails closed (`server/girder_janusm/rest.py`, `niftihead.py`)
- **Wrong:** an unreadable CT header gives `None` bounds, and every point is accepted.
- **Correct:** `None` bounds with any lesion point → 400 "CT bounds unavailable; lesion points cannot be
  checked". The PM is alerted.
- **Test (Mongo):** a case whose CT header cannot be parsed refuses a point, and accepts a form without points.

### SW5-D3 — Third reads only on the exported report (low priority)
- `export` records the anchoring report's sha256 on the wave.
- `adminThirdReads` accepts only a report with that hash.
- **Test:** a hand-made report with `flagged: true` is refused.

### SW5-D4 — Test hardening (`tests/test_janusm_reads.py`)
- S18's exact 5 % runs through `wave_report`.
- S19's shared-draw contrast calls the implementation with a shared-index stub and asserts that the bound
  differs.

### SW5-E1 — Scorer tests (`tests/test_janusm_score_decision.py`)
- d on two different reads (read 2 shifted 0.3 mm), with the expected d computed.
- A phantom whose volume and pp estimates disagree gives a transfer "fail".
- A third read in the real export shape (`thirdRead`, `thirdReadRecord`) never enters `pairs`.
- The reader id and key are absent from the output bytes.
- The sha256 file matches the output.
- A single comparison failing (read-vs-read alone) flips `passed`.

---

## 7. Disclosures and limits

- **How item 1 was gathered:**
  - per-group audits ran in parallel, under my supervision;
  - each table row was read against the test source;
  - the three code defects were reproduced:
    - SW5-A1 by `a1_phase_mix`;
    - SW5-D1 and SW5-D2 from the code paths cited.
- **Item 2 uses phantoms only.**
  - **How far the scoped remedy reaches:** its definition of a cap (a face facing the way the opening faces) is
    validated on cuts that are flat or 23° oblique.
  - **Untested on a real outflow:** a real LV outflow tract is curved. There, the transfer check (JA37, JA62) is
    still what decides on real walls.
- **No D-number is recorded, and no decision of the lead's is taken.**

---
tags: [janus-m, plans, candidate, round5, rest-ccta, myocardium, audit, harness, specification]
author: Lima
round: 5
version: 4
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#223
---

# Lima v4: the Round 4 fixes merged with every test the ruling names, but one fix crashes on the ruling's own input, and the open-base remedy as worded empties the epicardial band

**Path:** `jm/rest-ccta` (LQ1 option A). **Base:** the plan in force: [[Hotel v3]] + JA37–JA49 + JA60–JA69 (Round 4
ruling). Lima v4 proposes no change of structure. Under LQ34 (b) it settles only #223 items 1–4: Round 4 §8 items 2–3,
plus item 1 if aggregates had been posted (they have not).

## 0. In one paragraph

All five fix groups (#216–#220) are on this branch through `origin/dev` (#221 was still open, so I merged `dev` in).
**On the merged branch, 492 Janus-M tests pass and 0 fail** (`pytest tests/test_janusm_*.py
tests/test_segqueue_server_janusm.py`). 20 tests skip here: 19 need Mongo and 1 needs girder. CI ran the Mongo set
green on #220.

- **Item 1.** Every one of the 23 items merged with a shipped test for **each** test bullet in §7. None came back as
  unwritable. Read test by test (§1):
  - **One bug:** R4-S1's `phase_mix=` crashes on JA60's own `{"ED": 1.0}` (`KeyError: 'MD'`). The only test of it
    mocks the simulation. #218 works round it by naming every phase.
  - **One "Correct" bullet not done:** R4-S4's docstring does not carry JA37's disclosed real-wall error. It says
    the error "is not known".
  - **One open-base test cannot fail:** `test_validate_bias_estimator_open_base` runs one offset, where the cut
    capsule **passes** (0.0467 mm, guard 0.3). It then asserts the guard equals whatever the run gives.
  - **One test never runs in CI** (R4-S17's `decide()` unit test).
  - **Of the 86 test bullets, 78 are ✔ and 8 are weaker than the wording.** None of the eight hides a wrong number
    today. Every gap becomes a spec, L4-1 … L4-22 (§5).
- **Item 2.** The remedy as worded ("also exclude ≤ 3 mm of any pool or myocardium face adjoining label 0") **should
  be rejected** (§2):
  - On every read, the epicardium adjoins label 0 almost everywhere (fat, pericardium, aorta). On India's open phantom
    the remedy **empties the epicardial band in all 24 rows**, so `signed_bias` is NaN and the transfer check raises.
  - On the harness's LA-capped heart it keeps 18 % of the band, and that 18 % fails (0.052 mm). **The shipped band
    passes there** (0.017 mm).
  - A narrow reading — drop only the cut cap, the solid faces on the plane of the pool's opening — passes both
    phantoms (India 0.016 mm). It is a no-op where the base meets the LA. I offer it to the judge as a candidate
    amendment (P1).
  - **The guard stays 0.5 mm for the freeze PR.** JA61 ruled the fallback, and a remedy found after the fact is not
    a pass.
- **Item 3.** Of the twelve judgement calls, I **accept ten, accept one with a reservation, and reject one**
  (`population` raising on an omitted phase). See §3.
- **Item 4.** No JM-0 / JM-0R aggregates are posted (checked 2026-10-30), so `jm0r_decide.py` was not run and R0–R10
  have no value. R9 stays at the provisional 45 %.

No case, image or held-out id was opened (§6).

---

## 1. Item 1: each R4-S item against its named test

Verdicts:
- **✔** — the shipped test checks what §7 says.
- **≈** — present, but weaker than the wording. The weakness does not change a number today.
- **✘** — missing or wrong.

L4-n points to §5. Tests are in `tests/`. A "Correct" row is listed only where it is not ✔.

### Group A (#217): the detectable depth

| Item | §7 test | Shipped test | Verdict |
|---|---|---|---|
| R4-S1 | E7's rows reproduce with `median_mm=9.668` | `test_janusm_calibrate.py::test_e7_primary_rows_reproduce`, `::test_e7_every_replicate_reproduces`, `::test_e7_lookup_rows_reproduce` (0.30 / 0.35, sensitivities to 4 places) | ✔ |
| | `detectable_depth(0.088, LIMA_SHAPE, 1.0, seed=31000)` = 0.45 | `::test_ja60_default_anchor_is_the_ed_median_and_gives_the_provisional_45` (I reproduced 0.45, anchor 5.7, `ed_default`) | ✔ |
| | `measured_median_mm=6.3` → simulated median 6.3 ± 1 % | `::test_ja60_measured_median_is_the_simulated_median` (`rel=0.01`, 200 000 hearts) + `::test_ja60_detectable_depth_simulates_on_the_anchor_of_the_measured_wall` (I got 6.298) | ✔ |
| | both inputs raise | `::test_ja60_both_walls_raise` | ✔ |
| | `population_factor` at Lima's inputs = 1.109 ± 0.002 | `::test_ja60_population_factor_at_limas_inputs` (I got 1.10873) | ✔ |
| | *Correct: "add a `phase_mix=` argument"* | `calibrate.py:114` `phase_mix[k]` → **`KeyError('MD')`** for `{"ED": 1.0}`, JA60's and R4-S10's literal form. The only test of that form mocks `simulate`. `_phase_key` and `population_factor` accept the omission. | **✘ (L4-1)** |
| R4-S2 | a recording `depth_fn` receives JM-0R's median | `test_janusm_jm0r_decide.py::test_r9_calls_detectable_depth_with_cv_n_shape_the_f1_floor_and_the_measured_wall` (calls `== [(0.088, 16, 1.0, 0.0, SEED, 6.1)]`) | ✔ |
| | a missing median → NOT DECIDABLE | `::test_r9_missing_median_is_not_decidable` | ✔ |
| | cv_n = 0 prints the NOT DECIDABLE line | `::test_r9_s3_refusal_prints_not_decidable` (real S3), `test_janusm_jm0r_readout.py::test_the_decision_script_on_identical_rows_prints_s3s_refusal` | ✔ |
| | an R3 failure adds the note | `::test_r9_r3_failure_adds_the_note` (9.668 and 3.9) | ✔ |
| | the provisional string reads 45 % | `::test_r9_provisional_print_reads_45_percent` (and "35 %" absent) | ✔ |
| | the acceptance test uses jittered rows, `depth is not None` | `test_janusm_jm0r_readout.py::test_the_decision_script_on_the_synthetic_summary_is_decidable` | ✔ |
| R4-S3 | pooled and median straddle 0.10; `decision_inputs` follows the median | `test_janusm_jm0r_readout.py::test_septal_arc_pooled_flag_is_reported_and_r7_follows_the_case_median` (both directions) | ✔ |
| | *Correct: "a docstring saying R7 decides on the case median"* | a code comment (`jm0r_readout.py:595-597`), not a docstring | ≈ (L4-2) |

### Group B (#219): the harness

| Item | §7 test | Shipped test | Verdict |
|---|---|---|---|
| R4-S4 | India's open-base phantom within 0.05 mm with the band | `test_janusm_harness.py::test_open_base_india_phantom_with_the_band`: asserts `not passed` and the 0.5 mm constant, as §7's fallback clause requires. Endo and every ±0.3 row are held to 0.05. **The failing epi ±0.5 rows have no upper bound**, so a regression to 0.2 mm stays green. | ≈ (L4-3) |
| | (JA61) `validate_bias_estimator(open_base=True)` | `::test_validate_bias_estimator_open_base` runs **`n_offsets=1`**. There the capsule **passes** (worst 0.0467 mm → guard 0.3). The default 3 offsets fail at 0.0504 (Group B's audit; E1 reproduces it). It allows a worst of 0.06 and asserts `bias_guard_mm == (0.3 if passed else 0.5)`, a tautology. **This test cannot see the failure the constant cites.** | ≈ (L4-4) |
| | E4's closed shells stay within ±0.01 | `::test_e4_closed_shells_stay_within_a_hundredth_in_the_band` (endo only, one jitter) | ≈ (L4-5) |
| | a change only within 3 mm of label 4 → bias 0 ± 0.01 | `::test_a_change_within_3mm_of_label_4_moves_the_banded_bias_by_nothing` | ✔ |
| | the band excludes every voxel ≤ 3 mm from label 4 and from an open pool face | `::test_ja37_band_excludes_label_4_and_open_pool_faces` (brute-force face centres) | ✔ |
| | *Correct: "write JA37's disclosed real-wall error into the docstring"* | `signed_bias` says "the error is not known from phantoms alone". JA37 disclosed India E9: up to 0.05 mm low outward and 0.09 mm high inward near 0.3 mm. | **✘ (L4-6)** |
| | *If the check fails, the guard is 0.5 and the issue says so* | `BIAS_GUARD_VALIDATED_MM = BIAS_GUARD_FALLBACK_MM` (`harness.py:91`); #219's body says FAIL | ✔ |
| R4-S5 | 0.04 → 0.3; 0.06 → 0.5; 19 rows → error; row 21 ignored | `::test_transfer_check_median_under_the_limit_keeps_0_3`, `::…_over_the_limit_gives_0_5`, `::…_refuses_fewer_than_20_rows`, `::…_ignores_row_21` | ✔ (no mixed-border or exactly-0.05 case: L4-7) |
| R4-S6 | `test_e6_pp_within_ja39_tolerances` unrounded | same, `abs(err) <= tol`, 0.035 / 0.07 | ✔ |
| | `surface_assd` equals segtrain (0.47283) | `::test_surface_assd_is_segtrains` | ✔ |

### Group C (#218): reference population and table

| Item | §7 test | Shipped test (`test_janusm_reference.py` = TR, `_report` = TP, `_features` = TF) | Verdict |
|---|---|---|---|
| R4-S7 | 20 × 3 → factor 1.4606 (χ² 8.907) | TR::`test_chi2_factor_at_20_patients`, TR::`test_rc_is_the_upper_95_bound_pooled_by_default` (`n_patients == 20`, `n_values == 60`) | ✔ |
| | rewrite the pooled-by-default test | the same test, rewritten | ✔ |
| | +0.4 LAD / −0.4 LCx add to LAD and LCx, not RCA | TR::`test_rc_adds_each_territorys_own_offset` | ✔ |
| | a 14-vs-15 boundary | TR::`test_rc_own_sd_needs_15_patients[14, 15]` | ✔ (no SD between the values bound and the patients bound: L4-8) |
| R4-S8 | proportional thinning → "relative"; floor = RC_rel × E | TR::`test_rc_switches_to_relative_when_error_grows_with_e` | ✔ |
| | multiplicative fat stays on differences, mm³ | TR::`test_fat_multiplicative_noise_stays_on_differences` | ✔ |
| | the gate and the report give one floor for one E | TP::`test_the_gate_and_the_report_produce_the_same_floor_for_the_same_e` | ✔ |
| | signed D, ρ > 0.4, E ≤ 0 → differences, recorded | TR::`test_rc_stays_on_differences_when_e_is_not_positive` | ✔ |
| R4-S9 | a fat segment that changes territory moves D | TR::`test_a_fat_segment_that_changes_territory_moves_d` | ✔ |
| | a forced fall-back is counted | TR::`test_a_forced_fallback_is_counted` counts it in `rc["decisions"]`; **the header's count** (`report.py:332-334`) is untested | ≈ (L4-9) |
| R4-S10 | a recording S3 sees `measured_median_mm`; hypo the ED-only mix | TR::`test_gate_gives_s3_the_measured_wall[thinning, hypoattenuation]` | ✔ |
| R4-S11 | a monkeypatched version is refused; sha under `LC_ALL=C`; the golden config is byte-identical | TP::`test_a_version_mismatch_is_refused[…]`, TR::`test_config_sha_matches_under_the_c_locale`, TR::`test_golden_config_is_byte_identical` | ✔ |
| R4-S12 | a one-segment phantom is "shared" only with the flag on | TP::`test_one_segment_is_shared_only_with_r8_on`: the geodesic majority is **injected** by monkeypatching `case_features`. No phantom produces it. | ≈ (L4-10) |
| | `--run` without the flag is refused | TR::`test_cli_run_without_geodesic_shared_is_refused` | ✔ |
| R4-S13 | LM 4B → LAD and LCx significant, RCA not | TP::`test_lm_feeds_lad_and_lcx`, TP::`test_lm_grade_in_the_table` | ✔ |
| | a round trip from an export record | TP::`test_grades_round_trip_from_an_export_record` **hand-builds** the record. It never calls `export.readRecord`. | ≈ (L4-11) |
| | the distal-mass label | TP::`test_distal_mass_label` | ✔ |
| R4-S14 | 120° arc = fixed ± 0.01; the 180° share moves; JM-0R = geometry; goldens | TF::`test_arc_values_at_120_degrees_equal_the_fixed_values`, TF::`test_arc_at_180_degrees_moves_the_septal_share` (1/3 → 1/2), TF::`test_jm0r_and_geometry_agree_on_the_phantom` (`is G.arc_segments`, plus a frozen copy), TP::`test_golden_output[*]` | ✔ |
| R4-S15 | depth 0.50 / 0.55; κ at 4 and 5; a pass with κ None; pe = 1; the fat gate ± RC; Spearman 0.4; D ≤ RC → number; D on the patient map; `halves_note` | TR::`test_depth_050_passes_and_055_fails`, TR::`test_kappa_with_4_and_5_flagged_units`, TR::`test_a_pass_with_kappa_none`, TR::`test_kappa_not_estimable_when_chance_agreement_is_one`, TR::`test_fat_gate_with_and_without_an_rc[*]`, TR::`test_spearman_exactly_04_stays_on_differences`, TP::`test_rule_c_and_gate_pass_with_d_at_most_rc_is_a_number`, TR::`test_d_is_on_the_patient_map_not_aha`, TP::`test_header_fields` | ✔ (`halves_note` is tested True only) |

### Group D (#220): the read queue

TR = `test_janusm_reads.py`. TS = `test_segqueue_server_janusm.py`, Mongo; skipped here, green in CI on #220. TM =
`test_janusm_read_module.py`. ST = the Slicer self-test, CI only.

| Item | §7 test | Shipped test | Verdict |
|---|---|---|---|
| R4-S16 | Hotel E10 A and India's 6.2–8.7 mm ring fail | TR::`test_r4s16_hotel_e10_a_fails`, TR::`test_r4s16_india_ring_at_6p2_to_8p7_mm_fails[6, 10]` (the ring pinned to 6.2 / 8.7) | ✔ |
| | India's +4 / +6 mm blank reads fail with the check seed | TR::`test_r4s16_india_blank_overreach_fails_with_the_check_seed[4, 6]`; TS: +6 only | ✔ |
| | the exact phantom read passes | TR::`test_r4s16_the_exact_phantom_read_passes` | ✔ |
| | Mongo: a blank seed is never served (4xx, `hasSeed: false`); the report says "fitted to the seed" | TS::`test_r4s16_a_blank_read_is_checked_against_the_hidden_check_seed` (404, `source == "seed"`) | ✔ |
| | a plane-less read is returned uncounted | TS::`test_r4s16_a_plane_less_read_is_returned_uncounted`, TR::`…could_not_be_checked_and_never_passes`. JA66's "PM alerted" is not asserted. | ✔ (alert ≈, L4-13) |
| R4-S17 | (Mongo) crash, then a failure → RETURNED, unflagged; a further failure → flagged | TS::`test_r4s17_a_crash_never_spends_the_return` (`(returns, crashes, attempts) == (1, 1, 2)`, then flagged) | ✔ |
| | (no §7 bullet) "could not be checked" **after** a genuine return | TR::`test_r4s17_a_crash_or_an_unchecked_read_never_spends_the_return` skips without girder. **It runs in no CI job** (the main job has no girder; the Mongo job lists other files, `ci.yml:205`). | **✘ (L4-12)** |
| R4-S18 | < 5 % of the union but ≥ 5 % of the seed is not "following"; exactly 5 %; exactly half does not flag | TR::`test_r4s18_the_changed_share_is_over_seed_voxels`, TR::`test_r4s18_exactly_half_the_reads_following_does_not_flag` | ✔ |
| | an arbitrary list, 4 of 5, 6 names → 400 | TS::`test_r4s18_third_reads_open_only_on_a_flagged_waves_draw` | ✔ |
| | no `reads/` record is a third read | TS::`test_export_feeds_the_anchoring_report` | ✔ |
| R4-S19 | the bound recomputed with `default_rng(BOOTSTRAP_SEED)`; a shared-index draw differs; one `None` ASSD | TR::`test_r4s19_the_bound_is_pinned` (two-read cases only), TR::`test_r4s19_rule1s_gap_is_the_reports_read_level_difference` | ✔ |
| R4-S20 | 4B on LAD and 3 on LM refused; a point 1 m away; protocol 1 → 426, no read | TR::`test_r4s20_each_vessel_offers_only_its_cadrads_2_grades`, TR::`test_r4s20_a_point_a_metre_away_is_outside_the_ct`, TS::`test_r4s20_a_protocol_1_client_is_refused_at_next_before_any_claim`, TR::`test_protocol_refuses_missing_or_old_client` (now with 1) | ✔. The bounds check fails open on a non-NIfTI header, untested (L4-15). |
| R4-S21 | one test per change (Mongo and the read module) | TS::`test_export_feeds_the_anchoring_report`, TS::`test_r4s21_export_refuses_an_empty_wave`, TS::`test_r4s21_export_skips_and_lists_reads_not_under_border_protocol_1`; TM::`test_r4s21_the_reading_clock_is_kept_across_reopening`, TM::`test_r4s21_a_reopened_read_gets_its_form_back` | ✔ (the TM tests check source text; the behaviour is in ST) |
| R4-S22 | LV–RV 0.4 / 0.6 %; 3.0 / 3.5 mm on a seed plane; endocardial plateau → error; septal +1.0 mm | TR::`test_r4s22_lv_rv_contact_at_0p4_pct_passes_and_0p6_pct_fails`, TR::`…3p0_mm_above_a_seed_fitted_plane_not_3p5`, TR::`…unmeasurable_endocardium_is_an_error…`, TR::`test_r4s22_myocardium_grown_1_mm_into_the_rv_reads_plus_1_mm` | ✔ |

### Group E (#216): the decision scorer

`test_janusm_score_decision.py`: 17 tests pass. #216's body says 18.

| §7 test | Shipped test | Verdict |
|---|---|---|
| synthetic pairs on `exact_shift_phantom` give a known d and transfer verdict | `::test_known_d_and_transfer_verdict_on_exact_shift_phantom`: read 2 **is** read 1, so read-vs-read is 0 and d's subtraction is never exercised. Only row 0 is checked. The 0.5 verdict is shown on fake rows. | ≈ (L4-16) |
| order kept; a one-read case is skipped, so `reads[:20]` are the first 20 complete | `::test_order_kept_and_one_read_case_skipped` takes the order from `S.decision_order()`, the function under test. It never compares it with `sealed-r1.json`'s list. | ≈ (L4-17) |
| third reads dropped | `::test_third_reads_and_other_protocols_are_dropped`: the fixture's third read sits under `thirdRead`, which the code never reads. The in-list `third` branch (`score_decision.py:187`) is untested. | ≈ (L4-18) |
| a seal, extension or JM-0 id is refused before anything is opened | `::test_seal_extension_or_jm0_id_refused_before_anything_is_opened[*]` (spies on `_loader`) | ✔. `main` reads the manifests before `guard.refuse` (l.344 vs l.346). They hold ids, not images. JA62 says "any file" (L4-19). |
| one coronary array for both reads | `::test_same_coronary_array_for_both_reads` | ✔ |
| an id in the output is refused | `::test_an_id_in_the_output_is_refused` | ✔ |
| `build_reference.py` accepts it, refuses a mismatched `features_version` / `guard_mm` | `::test_build_reference_accepts_the_output_and_refuses_mismatches` | ✔ |
| (Correct) a stable reader key, **never written** | `::test_reader_key_fixes_read_1_and_is_never_written` asserts nothing about "never written" | ≈ (L4-20) |

**Tally of the 86 §7 test bullets** (A 12, B 10, C 32, D 25, E 7): **78 ✔, 8 ≈, 0 ✘**. The eight ≈ are L4-3, L4-5,
L4-9, L4-10, L4-11, L4-16, L4-17 and L4-18. Beyond the bullets:
- 2 "Correct" clauses are ✘: L4-1 and L4-6.
- 1 test is ✘ for never running in CI: L4-12.
- 3 more items are ≈: L4-2, the JA61 capsule test (L4-4) and the reader-key test (L4-20).

---

## 2. Item 2: R4-S4's open-base result, and the #219 remedy

**The result stands: FAIL, guard 0.5 mm.** E1 reruns #219's checks unchanged:

| Check (band as shipped) | Endo worst | Epi worst | Verdict |
|---|---|---|---|
| India's open E6 phantom (48 rows) | 0.015 | **0.068** (every epi ±0.5 row, 0.056–0.068) | fail |
| `validate_bias_estimator(open_base=True)`, 3 offsets (144 rows) | 0.024 | **0.0504** (epi +0.5) | fail, by 0.0004 mm |

The epicardium reads 11–13 % low on India's phantom. #219's diagnosis is right: the cut myocardial cap adjoins label
0, is no pool face, stays in the band, and adds area but no volume change.

**The remedy, tested** (`experiments/JanusM/Lima/r5/e1_open_base_remedy.py`, `e2_la_capped_heart.py`). The variants
live in the experiment folder; no shipped code changed. Four bands:
- **shipped** — `ja37_band` as merged.
- **literal** — the remedy as worded: also drop ≤ 3 mm of every pool **or myocardium** face adjoining label 0.
- **cap_plane** — fit a plane to the open pool faces' centres, and drop ≤ 3 mm of the solid faces adjoining label 0
  that lie within one voxel of that plane. That is only the cut cap.
- **slab** — drop everything within 3 mm of that plane, or beyond it.

E1 is India's open phantom plus the cut capsule. E2 is the harness's own `phantom()`: the base opens into the LA, the
RV sits over the septum, and label 0 is everywhere else, as on a read. It uses two grids, three walls, two offsets,
both borders and ±0.3 / ±0.5 mm (48 rows per border), against the exact shift.

| Band | India open, epi worst | Cut capsule, epi worst | LA-capped heart, epi worst | LA-capped epi band kept | Endo (all three) |
|---|---|---|---|---|---|
| shipped | 0.068 ✘ | 0.0504 ✘ | **0.017 ✔** | 100 % | ≤ 0.024 ✔ |
| literal | **empty in 24 / 24 rows** (NaN) | **NaN in 72 / 72 rows** | 0.052 ✘ | **18 %** | ≤ 0.024 ✔ |
| cap_plane | **0.016 ✔** | **0.0195 ✔** | 0.017 ✔ | 100 % (no-op) | ≤ 0.024 ✔ |
| slab | 0.016 ✔ | 0.0195 ✔ | 0.017 ✔ | 100 % (no-op) | ≤ 0.024 ✔ |

On the cut capsule, `cap_plane` and `slab` pass all 144 rows (worst 0.0238 mm, endo). On E4's closed shells:
- shipped, `cap_plane` and `slab` are identical, within 0.004 mm on both borders;
- `literal` keeps 3 % of the epicardial band and gives NaN in 8 / 8 rows.

The phantom does not decide the case for or against the remedy. The labels do:
1. **The remedy as worded cannot be adopted.** In JA1's labels, fat, pericardium and aorta are all label 0
   (`docs/JANUSM-READ-PROTOCOL.md` §2), so the epicardium adjoins label 0 over nearly its whole surface. The rule
   removes the border it is meant to measure:
   - on the open phantom, nothing is left;
   - on the LA-capped heart, it keeps the 18 % next to the RV and LA, and that remnant fails.

   On a real read, an empty epi band makes `signed_bias` NaN. `transfer_check` then raises on non-finite values, and
   decision scoring stops (R4-S5).
2. **The failure is the phantom's cut, not the band.** Where the base meets label 4, as the mitral plane does on a
   read, the shipped band passes on both borders, within 0.018 mm.
3. **A cap rule that is narrow enough is safe.** `cap_plane` fixes the open phantom and changes nothing on the
   LA-capped heart. It is a candidate amendment (P1), with two untested points:
   - a read has two openings (LVOT/aortic and any mitral gap that is not labelled), so the plane needs fitting **per
     connected opening**;
   - neither phantom has an aortic opening beside an LA.
4. **The guard stays 0.5 mm for the freeze PR.** JA61 ruled: "if it fails, the guard is 0.5 mm from the freeze PR
   on". A band chosen after seeing the failure would need a fresh, pre-registered validation before it could restore
   0.3. Even then, 0.3 also needs JA37's transfer check to pass on the first 20 decision reads, which no phantom can
   replace.

---

## 3. Item 3: the engineers' judgement calls

| # | Call | Verdict | Reason |
|---|---|---|---|
| 1 | #217: `numbers_only=True` whenever no depth is computed (`jm0r_decide.py:407`) | **Accept** | §7 mandates it for an S3 refusal and is silent on the missing median and on a depth not reached by 0.60. In both, JA41 cannot be evaluated. `calibrate.page_line` already prints "numbers only" when the depth is None, so the record agrees with the page. Tested in `test_r9_missing_median_is_not_decidable` and `test_r9_above_0p40_says_so_and_none_is_not_demonstrated`. |
| 2 | `calibrate.population` raises on a phase_mix that omits phases | **Reject** | It contradicts JA60 and R4-S10, which both write `{"ED": 1.0}`. It raises a bare `KeyError`, not a checked error. The module contradicts itself: `_phase_key` and `population_factor` treat an omitted phase as 0, and `detectable_depth`'s docstring advertises the short form. Fix: L4-1. |
| 3a | #218: the full phase-mix dict `{"ED": 1, "MD": 0, "SYS": 0}` is passed to S3 | **Accept** | It is the same distribution as `{"ED": 1.0}`, `_phase_key` gives both the same key, and the test pins it. It is a workaround for call 2. Once L4-1 lands it may stay. |
| 3b | #218: the relative RC needs E_T > 0 per read | **Accept** | JA64 defines E_T per read and asks for "E_T > 0 for every pair". A pair has two reads, so per read is the literal reading. It is also the conservative one, and it guarantees a positive divisor. Recorded in `decisions` and tested. |
| 3c | #218: the septal-arc cell shows two values | **Accept** | R4-S14 has the features carry both the arc wall and the arc relative subendocardial HU, and the reference their percentiles. One cell with both values, named in the header, adds no column the ruling did not name. |
| 3d | #218: an LM lesion point labels both LAD and LCx | **Accept** | JA67: LM feeds LAD and LCx, and Table B has no LM row. Mass distal to an LM point lies in both territories. Only the "not computed (report v1)" label prints, so nothing is over-claimed. |
| 4 | #216: the transfer check runs per comparison (model-vs-read 1, model-vs-read 2, read-vs-read; 20 rows each); any failure gives 0.5 mm | **Accept** | Each call is R4-S5's contract unchanged (median per border, first 20). The median of a pooled set lies between its parts' medians, so this is never laxer than JA37's pooled reading. It is moot while the guard is 0.5. Two notes for the judge: (i) six medians fail spuriously more often than two, so ratify the reading before any round restores 0.3; (ii) JA62's "count of cases over 0.05 mm" is produced per comparison only, not as a union over cases (L4-21). |
| 5a | #220: `phantom.heart()` defaults to a 2 mm mitral gap | **Accept** | JA66 makes "no plane" never a pass, and R4-S16 needs the exact phantom read to pass. The old default has no plane. Hotel E10 and India S5 already pass `mitral_gap_mm=2.0` explicitly, and `None` keeps the old shape. |
| 5b | #220: `adminThirdReads` takes the anchoring report | **Accept, with a reservation** | The server stores no Rule 2 result, so the report must come in. The server recomputes the seeded set and the draw and requires an exact list (`rest.py:395-415`), which is the anti-cherry-picking half of R4-S18. The reservation: `rule2.flagged` is the admin's word (L4-22). |
| 5c | #220: a new `POST admin/wave` | **Accept** | R4-S21 requires `JanusMCase.wave` and `export --wave` but names no way to set it. The route is admin-only and refuses an empty or unknown case. It reassigns silently, though, and wave membership feeds the third-read draw. Hardening: L4-14. |
| 5d | #220: the 0.3.0 bump, 426 for 0.2.x | **Accept** | JanusMRead 0.1.0 and 0.2.0 both shipped `PROTOCOL_VERSION = 1` (`git show fdb10bf`, `1909e58`). So "0.2.x → 426" is exactly R4-S20's "protocol 1 → 426". The refusal comes before any claim (`rest.py:170`). |

---

## 4. Item 4: JM-0 / JM-0R aggregates

**None posted** as of 2026-10-30. I checked:
- `experiments/JanusM/fir/`, which holds only `jm0r_decide.py` and `jm0r_readout.py`;
- an issue search for JM-0 / JM-0R results;
- #205's and #223's comments.

So `jm0r_decide.py` was not run, and R0–R10 have no value. R9's page figure stays the provisional **45 %** (JA60).
Group A's merge means the script is ready: R4-S1, S2 and S10 are in, and the jittered acceptance test computes a
depth.

---

## 5. Gaps as `role:swe` specifications (for the PM; not built here)

Shipped code is unchanged. Each spec is one issue, labelled `path:jm-rest-ccta`. Each cites Round 4 §7 and #223.
**Before the freeze PR:** L4-1, L4-4, L4-6. **Before the first read wave:** L4-12, L4-14. **Before decision
scoring:** L4-16 to L4-21. The rest are test hygiene.

### Group A
- **L4-1 — `phase_mix` shorthand (bug).**
  - **Wrong:** `population()` (`calibrate.py:114`) indexes `phase_mix[k]`, so the short form crashes.
  - **Correct:** normalise once with `_phase_key`'s rule (an omitted phase = 0) in `detectable_depths`. Pass the
    full dict to `simulate` and record it. Draws for full-keyed mixes do not change, so E7 holds.
  - **Test:** unmocked, `detectable_depth(0.088, LIMA_SHAPE, 1.0, seed=1, measured_median_mm=6.3, phase_mix={"ED":
    1.0})` equals the full-dict call.
- **L4-2 — JA69's precedence in a docstring.** Move the comment at `jm0r_readout.py:595-597` into the module
  docstring.

### Group B
- **L4-3 — Pin the India failure.** In `test_open_base_india_phantom_with_the_band`, assert that every epi ±0.5 row
  has `0.05 < |err| <= 0.075`, and that the worst ≈ 0.068 (± 0.003).
- **L4-4 — Make the capsule test able to fail.** Run `validate_bias_estimator(open_base=True)` at its defaults
  (`n_offsets=3`, slow). Assert `passed is False`, worst ≈ 0.0504 (± 0.002), `epi_outward > 0.05`. Drop the 0.06
  allowance and the tautological guard assert.
  - Alternatively, derive `BIAS_GUARD_VALIDATED_MM` in a test from both open-base checks.
  - Either way, state in the constant's comment that the capsule's miss is 0.0004 mm and seed-dependent, and that
    India's 0.068 is the binding failure.
- **L4-5 — E4 in the band on the epicardium.** Shift the outer shell and use `ja37_band(lab, SP, "epi")`, with two
  centre jitters.
- **L4-6 — JA37's disclosure in `signed_bias`'s docstring.**
  - **Wrong:** "the error is not known from phantoms alone".
  - **Correct:** "on real walls near 0.3 mm it reads up to 0.05 mm low outward and 0.09 mm high inward (India E9), so a
    true outward bias up to ≈ 0.35 mm can pass".
  - **Test:** `"0.09" in H.signed_bias.__doc__`.
- **L4-7 — Transfer check boundaries.** Endo median 0.04 with epi 0.06 → fail, 0.5. A median of exactly 0.05 → pass.

### Group C
- **L4-8 — The step-3 switch counts patients.** 20 × 3 with LAD SD_T between `sd_pool × _chi2_factor(60)` and
  `sd_pool × _chi2_factor(20)`. Assert LAD stays pooled.
- **L4-9 — The fall-back in the header.** Build a report with `segment_territory` dropped. Assert `territory_map ==
  "aha_fallback"` and the note in the markdown.
- **L4-10 — "Shared" from a real geodesic difference.** A phantom in `tests/janusm_synth.py` whose
  `geometry.territories(method="geodesic")` majority differs on one segment.
- **L4-11 — The round trip through the real export.** In a server test, `export.readRecord` →
  `report.grades_from_read_record`. Or move the mapping into a girder-free helper that both use.

### Group D
- **L4-12 — Run R4-S17's `decide()` test in CI.**
  - Add a Mongo case: a genuine failure (returns = 1), then a plane-less submission → returned, unflagged, `returns
    == 1`, `crashes == 1`.
  - Then either add `tests/test_janusm_reads.py -k r4s17` to the Mongo job, or move `decide` into a girder-free
    module.
- **L4-13 — Assert the PM alert** ("COULD NOT BE CHECKED", ERROR log) for a plane-less read.
- **L4-14 — Freeze wave membership.** `POST admin/wave` refuses to move a case that already has another wave, or any
  case of a wave with a third read wanted, unless `force=true`. Log every change.
- **L4-15 — The bounds check on a non-NIfTI header.** Refuse (409), or test the logged error. Today the point is
  accepted unchecked.

### Group E
- **L4-16 — A non-trivial d on the phantom.** Read 2 = read 1 with epi +0.3 mm, exactly. Assert d on every row
  against mean(model-vs-read pp) − read-vs-read pp, within 0.035 mm. Drive the 0.5 verdict from phantom rows where
  vol and pp disagree.
- **L4-17 — Order against the config.** Assert `S.decision_order()` equals `sealed-r1.json["decision"]`, as a list
  in its order. No id is printed or written.
- **L4-18 — An in-list third read.** A `readRecords` entry with `third: True` is dropped, and the case still counts
  on its two reads.
- **L4-19 — Guard before any file, literally.**
  - Either move `guard.refuse` ahead of the manifest reads, or have the judge reword JA62 to "before any image, mask
    or read file".
  - Test with an `open` / `nib.load` spy, and assert that stderr names `HeldOutError`.
- **L4-20 — The reader key is never written.** Run `select_pairs` → `score` → `dumps`, and assert that no reader id
  or key digest appears in the text.
- **L4-21 — `n_cases_over_limit`.** The union over comparisons and borders, per JA62's "count of cases over 0.05 mm".
  No ids. Also: remove the dead stand-ins in the test file, test the `main --run` success path and its `.sha256`, and
  correct #216's "18 tests".
- **L4-22 (optional) — A verifiable Rule 2 flag.**
  - `janusm-export` records the manifest hash on the cases.
  - `anchoring` embeds the hash in the report.
  - `adminThirdReads` checks it.

**Minor, for the PM's discretion:**
- the Slicer reading clock restarts at submit, so time spent waiting for the check counts toward the next attempt;
- R4-S19's pinned bootstrap uses only two-read cases;
- `halves_note` is tested True only.

---

## 6. Held-out disclosure

- **No case, image or label was opened.** E1 and E2 build analytic phantoms only.
- **Each script calls `janusm.guard.refuse([])` first** (an empty list), so that it fails closed if the guard's pins
  are broken.
- **No held-out case or TotalSegmentator twin** was read, scored or used.
- **No SciNet, Alliance or Fir job** was run.
- **The Group E audit** read only `score_decision.py`'s code and its tests. It did not read `sealed-r1.json`'s
  contents.
- **No outside request is drafted** (D31).

## 7. Proposals for the judge (not lead questions)

- **P1 — The open-base band, for a later round only.**
  - Adopt `cap_plane` (fitted per connected opening) as JA61's band, **prospectively**.
  - Pre-register its validation on three phantoms: India's open phantom, the cut capsule, and an LA-capped heart with
    an aortic opening.
  - The guard stays 0.5 mm until that validation and JA37's transfer check both pass.
  - Reject the remedy as worded (§2).
- **P2 — Ratify #216's per-comparison transfer check** (§3 call 4) and L4-21's union count.
- **P3 — Reword JA62's "before opening any file"**, or keep it and require L4-19.

No new lead question. No fork.

## 8. Risks

- **The guard stays 0.5 mm.** A model whose true bias is 0.3–0.5 mm passes the guard. JA37's transfer check and
  JA8's d still bound it. This is JA61's ruled cost, not a new one.
- **L4-1 is latent.** No shipped caller passes the short form today (#218 names every phase). It bites the first
  script that follows JA60's text.
- **L4-12** leaves "could not be checked after a return" unproven in CI. It must close before the first read wave.
- **Mongo and Slicer tests** were not run here. CI ran them green on #220.

## 9. Evidence

- **Note:** [[Lima - The open-base remedy as worded empties the epicardial band, while a cut-cap-only band passes and the shipped band already passes where the base meets the LA]].
- **Experiment folder:** `experiments/JanusM/Lima/r5/` (README, E1, E2, JSON).

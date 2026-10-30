---
tags: [janus-m, plans, candidate, round5, path-rest-ccta, myocardium, audit, harness, protocol]
author: Hotel
round: 5
version: 5
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#223
---

# Hotel v5: rest CCTA only. The Round 4 fixes hold test by test; one prescribed input crashes, and the open-base remedy works only in a narrower form

**The position in one line.** Every R4-S1 … R4-S23 item merged with the tests the ruling names, and none is
missing. But:
- **One fix crashes on an input the ruling prescribes.** `calibrate.population` raises `KeyError: 'MD'` on
  JA60's own hypoattenuation mix `{"ED": 1.0}`. The test that seems to cover it stubs the sampler.
- **The #219 open-base remedy, taken literally, empties the epicardial band.** The label set has no aorta or
  pericardium, so the whole free epicardium adjoins label 0 (E11). A narrower form that excludes only the cut cap
  passes JA61's 0.05 mm on every phantom.
- **Two read-queue endpoints trust what they should check.** `POST admin/wave` can move a case with accepted reads
  to another wave. `adminThirdReads` takes `rule2.flagged` from the caller.
- **Nine named tests check something weaker than the ruling's sentence.** None hides a wrong number today.

Each becomes a `role:swe` item (§6, H5-1 … H5-7), or a candidate amendment for the judge (§3, P5-1).

**Base.** The master plan on this path: [[Hotel v3]] + JA37–JA49 + JA60–JA69
([[Round 4 - rest-ccta|Round 4 ruling]]). Hotel v5 re-argues no threshold. It settles #223 items 1–4. Under LQ34 (b),
this round is only Round 4 §8's items 2–3 (and item 1, if aggregates had been posted; they have not, §5).

**Branch state checked.** `exp/jm-r5-rest-ccta-hotel` is `jm/rest-ccta` at `fe6e285`, merged with `origin/dev` at
`e5d3c9a`, because PR #221 was not yet merged. That brings in #216–#220 (Groups A–E).
- `pytest tests/test_janusm_*.py tests/test_segqueue_server_janusm.py`: TESTRESULT.
- `ruff check .`: clean.

**New evidence this round** (CPU, synthetic only; code in `experiments/JanusM/Hotel/r5/`):
- **E11** `e11_open_base_remedy.py`: R4-S4's open-base check repeated with the #219 remedy and two narrower forms,
  on three phantoms (§3).
- A test-by-test audit of Groups A–E. Six delegated reviewers did it, one per group half. I did Group B myself, and
  re-checked by hand every finding used below: the `KeyError`, `admin/wave`, the unchecked lesion-point path, and
  the R9 phase-mix path.

**Held-out cases.** No case of any kind was opened. E11 uses only `janusm.harness` phantoms and Hotel E6's analytic
phantom. The script calls `janusm.guard.refuse([])` first, by rule, naming nothing. No id was read or printed. There
is nothing to disclose.

---

## 1. Item 1 — each R4-S item against its named test

Key:
- ✓ = the test exists and asserts what the ruling's sentence says.
- **weaker** = the test exists but would also pass on a wrong implementation (reason given).
- **gap** = a "Correct" clause with no code, or code that is wrong.

Test files:
- H = `test_janusm_harness.py`
- C = `test_janusm_calibrate.py`
- D = `test_janusm_jm0r_decide.py`
- R = `test_janusm_jm0r_readout.py`
- RF = `test_janusm_reference.py`
- RP = `test_janusm_report.py`
- F = `test_janusm_features.py`
- Q = `test_janusm_reads.py`
- M = `test_janusm_read_module.py`
- SD = `test_janusm_score_decision.py`
- S = `test_segqueue_server_janusm.py` (all Mongo-marked; CI runs it in "Server against a real MongoDB")
- ST = `slicer_selftest_janusm.py` (inside Slicer, `janusm-read.yml`)

Tests marked `slow` run in CI, because the main job does not deselect them.

### 1.1 Group A — the detectable depth (#217)

| Item | Ruling's test | Test | Status |
|---|---|---|---|
| S1 | E7's rows at `median_mm=9.668` | C::test_e7_primary_rows_reproduce, C::test_e7_every_replicate_reproduces | ✓ (4 d.p.) |
| S1 | `detectable_depth(0.088, LIMA_SHAPE, 1.0, seed=31000)` = 0.45 | C::test_ja60_default_anchor_is_the_ed_median_and_gives_the_provisional_45 | ✓ (also anchor 5.7, source, version, warning) |
| S1 | measured 6.3 → simulated median 6.3 ± 1 % | C::test_ja60_measured_median_is_the_simulated_median | ✓ (200 000 hearts, rel 0.01) |
| S1 | both inputs raise | C::test_ja60_both_walls_raise | ✓ (both entry points) |
| S1 | `population_factor` at Lima's inputs 1.109 ± 0.002 | C::test_ja60_population_factor_at_limas_inputs | ✓ (1.108726, re-run) |
| S1 | *(Correct clause)* "add a `phase_mix=` argument" | C:101–125 passes `{"ED": 1.0}` with `simulate` stubbed | **gap → H5-1.** Unstubbed, `detectable_depth(…, measured_median_mm=6.3, phase_mix={"ED": 1.0})` raises `KeyError: 'MD'` at `calibrate.py:118` (`phase_mix[k]` for every phase). `_phase_key` validates the mix and fills missing phases, but the raw dict goes on to `population()`. A `KeyError` would also slip past R9's `except ValueError`. Today nothing reaches it: R9 passes no mix, and `reference.py:630` sends all three phases ("S3's sampler needs them"). |
| S2 | a recording `depth_fn` gets JM-0R's median | D::test_r9_calls_detectable_depth_with_cv_n_shape_the_f1_floor_and_the_measured_wall | ✓ |
| S2 | missing median → NOT DECIDABLE | D::test_r9_missing_median_is_not_decidable | ✓ (S3 not called) |
| S2 | cv_n = 0 prints the NOT DECIDABLE line | D::test_r9_s3_refusal_prints_not_decidable; R::test_the_decision_script_on_identical_rows_prints_s3s_refusal | ✓ (real S3) |
| S2 | R3 failure adds the note | D::test_r9_r3_failure_adds_the_note | ✓ when S3 computes. **Small gap → H5-2:** when R3 fails *and* S3 refuses, the note is dropped (`jm0r_decide.py:402`) |
| S2 | provisional reads 45 % | D::test_r9_provisional_print_reads_45_percent | ✓ |
| S2 | acceptance test on jittered rows, `depth is not None` | R::test_the_decision_script_on_the_synthetic_summary_is_decidable | ✓ |
| S3 | pooled and median straddle 0.10; `decision_inputs` follows the median | R::test_septal_arc_pooled_flag_is_reported_and_r7_follows_the_case_median | ✓ (both directions). The "docstring" is a comment (`jm0r_readout.py:595`); cosmetic |

### 1.2 Group B — the harness (#219; my own audit)

| Item | Ruling's test | Test | Status |
|---|---|---|---|
| S4 | India's open-base phantom within 0.05 mm with the band | H::test_open_base_india_phantom_with_the_band | ✓. It records the **fail**: endocardium and ±0.3 mm within 0.05 mm, epicardium at ±0.5 mm worst 0.068 mm; every row beats the whole mask. It pins `BIAS_GUARD_VALIDATED_MM == 0.5` to that verdict |
| S4 | E4's closed shells within ±0.01 in the band | H::test_e4_closed_shells_stay_within_a_hundredth_in_the_band | ✓ (and the whole-mask E4 still passes) |
| S4 | a change only within 3 mm of label 4 → 0 ± 0.01 | H::test_a_change_within_3mm_of_label_4_moves_the_banded_bias_by_nothing | ✓ (and asserts the whole-mask estimator does see it) |
| S4 | the band excludes every voxel ≤ 3 mm from label 4 and an open pool face | H::test_ja37_band_excludes_label_4_and_open_pool_faces | ✓. Brute-force face centres, and the converse: whatever is left out is left out only for those reasons |
| S4 | `validate_bias_estimator(open_base=True)` | H::test_validate_bias_estimator_open_base | **weaker (H5-7 a).** It runs `n_offsets=1` and asserts `worst ≤ 0.06` and `bias_guard_mm == (0.3 if passed else 0.5)`. It never pins the verdict. The 0.0504 mm fail #219 reports is at the default 3 offsets, which no test runs. The guard constant is pinned by the India test alone |
| S4 | *(Correct)* remove the test asserting `signed_bias` ignores `roi`; disclose JA37's error in the docstring; 1.2.0 | H::test_compare_restricts_pp_and_the_guard_to_the_roi now asserts the opposite; `signed_bias` docstring; H::test_harness_version_is_1_2 | ✓ |
| S5 | median 0.04 → 0.3 | H::test_transfer_check_median_under_the_limit_keeps_0_3 | ✓ (and `bias_guard_applied_mm` 0.5) |
| S5 | 0.06 → 0.5 | H::test_transfer_check_median_over_the_limit_gives_0_5 | ✓ (and 8 of 20 over the limit with the median under: passes, count reported) |
| S5 | 19 rows → error | H::test_transfer_check_refuses_fewer_than_20_rows | ✓ (also NaN and missing keys) |
| S5 | row 21 ignored | H::test_transfer_check_ignores_row_21 | ✓ (30 extreme rows and a NaN row change nothing) |
| S6 | E6 within JA39 unrounded | H::test_e6_pp_within_ja39_tolerances | ✓ (`abs(err) <= tol`; both grids, three walls) |
| S6 | `surface_assd` = segtrain on the phantom (0.47283) | H::test_surface_assd_is_segtrains | ✓ (equality, plus a source check) |

**Item 3 (Round 4 §8) recorded:** R4-S4's open-base validation **FAILED**. The guard is **0.5 mm** from the freeze
PR on (JA61).

### 1.3 Group C — reference population and table (#218)

| Item | Ruling's test | Test | Status |
|---|---|---|---|
| S7 | factor 1.4606 at 20 patients | RF::test_chi2_factor_at_20_patients | ✓ |
| S7 | rewrite `test_rc_is_the_upper_95_bound_pooled_by_default` | RF:160 | ✓ (n_patients 20, n_values 60) |
| S7 | +0.4 LAD / −0.4 LCx go to LAD and LCx, not RCA | RF::test_rc_adds_each_territorys_own_offset | ✓ |
| S7 | 14-vs-15 boundary | RF::test_rc_own_sd_needs_15_patients | **weaker (H5-7 b).** Patients equal positions in the fixture, so it cannot show n_T counts patients. The χ² switch bound (`reference.py:506`) has no separate test |
| S8 | proportional noise → relative; floor = RC_rel × E | RF::test_rc_switches_to_relative_when_error_grows_with_e | ✓ |
| S8 | multiplicative fat noise stays on differences | RF::test_fat_multiplicative_noise_stays_on_differences | ✓ |
| S8 | gate and report give the same floor for the same E | RP::test_the_gate_and_the_report_produce_the_same_floor_for_the_same_e | ✓ (spy on `rc_floor_mm`) |
| S8 | signed D, ρ > 0.4, E ≤ 0 stays on differences, recorded | RF::test_rc_stays_on_differences_when_e_is_not_positive | ✓. Also no `rc_abs`, `expm1` or `level = 1.0` is left anywhere |
| S9 | a fat segment that changes territory moves D | RF::test_a_fat_segment_that_changes_territory_moves_d | **weaker (H5-7 c).** `case_state` is fed hand-made `fat_clusters_mm3_patient`. F:158 checks only that the keys exist, so the wiring in `features.py:209–212` has no value test |
| S9 | a forced fall-back is counted | RF::test_a_forced_fallback_is_counted | ✓ (`rc["decisions"]`). The header's fall-back line (`report.py:332`) is untested |
| S10 | recording S3 sees `measured_median_mm`, and ED only for hypoattenuation | RF::test_gate_gives_s3_the_measured_wall | ✓ |
| S11 | a monkeypatched version is refused | RP::test_a_version_mismatch_is_refused | ✓ |
| S11 | sha matches under `LC_ALL=C` | RF::test_config_sha_matches_under_the_c_locale | ✓ (the environment is really ASCII; the config has non-ASCII bytes) |
| S11 | golden config byte-identical | RF::test_golden_config_is_byte_identical | ✓ (300 hearts, seed 11; `JANUSM_REGEN_GOLDEN=1`) |
| S12 | one-segment "shared" only with the flag | RP::test_one_segment_is_shared_only_with_r8_on | **weaker (H5-7 d).** The "phantom" is a monkeypatched `case_features`. The real geodesic majority is tested only for its keys (F:158) |
| S12 | `--run` without the flag refused | RF::test_cli_run_without_geodesic_shared_is_refused | ✓ |
| S13 | LM 4B → LAD and LCx significant, RCA not | RP::test_lm_feeds_lad_and_lcx, RP::test_lm_grade_in_the_table | ✓ |
| S13 | round trip from an export record | RP::test_grades_round_trip_from_an_export_record | ✓ |
| S13 | distal-mass label | RP::test_distal_mass_label | ✓ (exact string) |
| S14 | 120° arc = fixed values ± 0.01 | F::test_arc_values_at_120_degrees_equal_the_fixed_values | ✓ |
| S14 | 180° moves the share | F::test_arc_at_180_degrees_moves_the_septal_share | ✓ (sector shares ⅓ → ½) |
| S14 | JM-0R and geometry agree | F::test_jm0r_and_geometry_agree_on_the_phantom | ✓ (same object, and equal to a frozen copy of the old code) |
| S14 | goldens regenerated | RP::test_golden_output | ✓ |
| S15 | 0.50 passes, 0.55 fails | RF::test_depth_050_passes_and_055_fails | ✓ |
| S15 | κ with 4 and 5 flagged; a pass with κ None; pe = 1 | RF::test_kappa_with_4_and_5_flagged_units, ::test_a_pass_with_kappa_none, ::test_kappa_not_estimable_when_chance_agreement_is_one | ✓ |
| S15 | fat gate with and without an RC | RF::test_fat_gate_with_and_without_an_rc | ✓ |
| S15 | Spearman exactly 0.4 | RF::test_spearman_exactly_04_stays_on_differences | ✓ (strict `>`) |
| S15 | Rule C with D ≤ RC → a number | RP::test_rule_c_and_gate_pass_with_d_at_most_rc_is_a_number | ✓ (0.8 → number, 0.81 → flag) |
| S15 | D on the patient map | RF::test_d_is_on_the_patient_map_not_aha | ✓ |
| S15 | `halves_note` in `test_header_fields` | RP:155 | ✓ |

### 1.4 Group D — the read queue (#220)

| Item | Ruling's test | Test | Status |
|---|---|---|---|
| S16 | Hotel E10 A fails | Q::test_r4s16_hotel_e10_a_fails | ✓ |
| S16 | India's ring at 6.2–8.7 mm fails | Q::test_r4s16_india_ring_at_6p2_to_8p7_mm_fails | ✓ |
| S16 | India's +4 / +6 mm blank reads fail with the check seed | Q::…_india_blank_overreach_fails_with_the_check_seed | ✓ (and a self-fitted plane misses them) |
| S16 | the exact phantom passes | Q::test_r4s16_the_exact_phantom_read_passes | ✓ (with the 2 mm gap; §4) |
| S16 | Mongo: blank seed never served; report "fitted to the seed" | S::test_r4s16_a_blank_read_is_checked_against_the_hidden_check_seed | ✓ (404, `hasSeed` false, source "seed") |
| S16 | plane-less read returned uncounted | S::test_r4s16_a_plane_less_read_is_returned_uncounted; Q:883 | ✓ |
| S16 | *(Correct)* footprint = max(fit radius + 3, LA extent 0–10 mm) | Q:856 asserts only `footprintMm ≥ radiusMm + 3` | **weaker (H5-7 e).** In the phantom, radius + 3 = 8.70 mm beats the 8.0 mm LA shadow, so deleting the shadow term (`checker.py:367–382`) passes every test |
| S17 | crash, then fail → RETURNED, unflagged; then flagged | S::test_r4s17_a_crash_never_spends_the_return | ✓ (returns, crashes, attempts = 1, 1, 2). The unit twin (Q:893) skips without girder; the Mongo test covers it |
| S18 | < 5 % of the union but ≥ 5 % of the seed is not "following" | Q::test_r4s18_the_changed_share_is_over_seed_voxels | **weaker (H5-7 f).** Pins `changed_share` (0.052), then asserts `not share < 0.05` *in the test*. It never goes through `wave_report`'s comparison (`anchoring.py:263`) |
| S18 | exactly 5 % is not "following" | same test | **weaker (H5-7 f).** Asserts only `share == 0.05`; changing `<` to `<=` at `anchoring.py:263` still passes |
| S18 | exactly half does not flag | Q::test_r4s18_exactly_half_the_reads_following_does_not_flag | ✓ (4/8 no, 5/8 yes) |
| S18 | arbitrary list, 4 of 5, 6 names → 400 | S::test_r4s18_third_reads_open_only_on_a_flagged_waves_draw | ✓ (also duplicates, a substitution, an unflagged report, the wrong wave) |
| S18 | no `reads/` record is a third read | S::test_export_feeds_the_anchoring_report | ✓ (`third/`, `reference: false`) |
| S19 | the bound recomputed with `default_rng(BOOTSTRAP_SEED)` | Q::test_r4s19_the_bound_is_pinned | **weaker (H5-7 g).** Equal to 1e-12, but every case has exactly two reads, so read-weighted and case-weighted means agree inside each draw |
| S19 | a shared-index draw differs | same test | ✓ |
| S19 | one `None` ASSD → `gap == blank − seeded` | Q::test_r4s19_rule1s_gap_is_the_reports_read_level_difference | ✓ (and ≠ the case-level value) |
| S20 | 4B on LAD, 3 on LM refused | Q::test_r4s20_each_vessel_offers_only_its_cadrads_2_grades; S:414 | ✓ |
| S20 | a point 1 m away refused | Q::test_r4s20_a_point_a_metre_away_is_outside_the_ct; S:418 | ✓. **Gap → H5-6:** if the CT header cannot be read, `ctWorldBounds` is None, `points_outside` returns `[]`, and `rest.submit` accepts the points with only a log line (`rest.py:246–250`, `niftihead.py:118`). JA67 says such points are refused; nothing tests this path |
| S20 | protocol 1 at `next` → 426, no read; update the old test | S::test_r4s20_a_protocol_1_client_is_refused_at_next_before_any_claim; Q:102 | ✓ |
| S20 | N named; doc §4.4; Slicer offers only allowed grades | Q:1030; M:522 (source text); ST:367 | ✓ (ST checks the real combo boxes) |
| S21 | wave field, `export --wave` | S::test_export_feeds_the_anchoring_report | **weaker (H5-7 h).** "Wave 1 only" does not discriminate: no accepted case sits in another wave when export runs, so an export with no filter would pass |
| S21 | empty wave refused | S::test_r4s21_export_refuses_an_empty_wave | ✓ |
| S21 | skip and list non-protocol-1 reads | S::test_r4s21_export_skips_and_lists_reads_not_under_border_protocol_1 | ✓ |
| S21 | seed offsets on by default | S:868, :879 | ✓ |
| S21 | `seconds` summed; timer kept on reopen | S:454, :853; M:540 (source text); ST:445 | ✓ server side. **Weaker (H5-7 i)** in Slicer: ST asserts `≥ 30` s after reopening, which the last attempt alone also meets |
| S21 | form restored on reopen | ST:440; M:530 | ✓ (ST compares the restored grades and point) |
| S22 | LV–RV 0.4 % passes, 0.6 % fails | Q:1102 | ✓ |
| S22 | 3.0 mm passes, 3.5 mm fails, seed plane | Q:1131 | ✓ |
| S22 | an unmeasurable endocardium is an error | Q:1153 (`checker.py:608–614`) | ✓ |
| S22 | `move_border("septal")` reads +1.0 mm | Q:1167 | ✓ (± 0.25; also −1 mm) |

### 1.5 Group E — decision scoring (#216)

| Ruling's test | Test | Status |
|---|---|---|
| synthetic pairs on `exact_shift_phantom`: known d and transfer verdict | SD::test_known_d_and_transfer_verdict_on_exact_shift_phantom | ✓ (d_endo 0.5 ± 0.035; transfer guard 0.3, in force 0.5). Now runs the real `compare(roi="ja37")` and `transfer_check` |
| order kept; a one-read case skipped; `reads[:20]` = first 20 complete | SD::test_order_kept_and_one_read_case_skipped | ✓ |
| third reads dropped | SD::test_third_reads_and_other_protocols_are_dropped | ✓ for the export's real format (`thirdRead` keys). The in-list `third: True` filter (`score_decision.py:187`) is never exercised (H5-7 j) |
| seal, extension or JM-0 id refused before anything is opened | SD::test_seal_extension_or_jm0_id_refused_before_anything_is_opened | ✓ (loader never called; rc 3) |
| one coronary array for both reads | SD::test_same_coronary_array_for_both_reads | ✓ (`is`) |
| an id in the output is refused | SD::test_an_id_in_the_output_is_refused | ✓ |
| `build_reference.py` accepts it, refuses a mismatched `features_version` / `guard_mm` | SD::test_build_reference_accepts_the_output_and_refuses_mismatches | ✓ |

All eight of JA62's "Correct" bullets are in the code (`score_decision.py:118–368`). Two are untested: the
`.sha256` file is written only under `--run`, and nothing asserts that the reader key is never written (H5-7 j).

### 1.6 Summary

| | Items | Named tests | ✓ | weaker | missing |
|---|---|---|---|---|---|
| Group A | S1–S3 | 12 | 12 | 0 | 0 |
| Group B | S4–S6 | 11 | 10 | 1 | 0 |
| Group C | S7–S15 | 27 | 24 | 3 | 0 |
| Group D | S16–S22 | 27 | 21 | 6 | 0 |
| Group E | S23 | 7 | 7 | 0 | 0 |

Every test the ruling names exists, so no item "comes back with the reason" under §8 item 2. Separately from the
tests, three **Correct-clause defects** come back as code fixes:
- H5-1, the phase-mix `KeyError`;
- H5-6, lesion points unchecked when the CT header cannot be read;
- H5-4, `admin/wave` reassignment (from item 3).

None has touched a case: no read wave has run, and R9 passes no phase mix.

---

## 2. Item 2 — R4-S4's open-base result

**Recorded:** FAIL. #219 measured India's E6 open-base phantom with the band at worst 0.068 mm (epicardium, ±0.5 mm),
and the cut capsule at 0.0504 mm. So `BIAS_GUARD_VALIDATED_MM` = 0.5 mm, and it applies from the freeze PR on (JA61).

## 3. The #219 engineer's remedy, tested (E11)

**The remedy as stated:** "also exclude ≤ 3 mm of any pool or myocardium face that adjoins label 0, because the cut
basal cap adds area with no volume change."

**Why it cannot be taken literally.** The label set is 0 / MYO / LV / RV / LA (`geometry.py:46`). It has no aorta,
RA, pericardium or fat label. So on a real read, the free epicardial wall adjoins label 0 everywhere it does not touch
the RV or LA. Excluding 3 mm of every myocardium face that adjoins label 0 removes the epicardial band, not just the
cap. The cause #219 diagnosed is right. The fix has to name the cap, not every face open to background.

**Variants tested** (each = `harness.ja37_band` minus a further exclusion, built in the script):
- `shipped` — JA61 as built.
- `literal` — the remedy as stated: minus ≤ 3 mm of every pool-or-myocardium face that adjoins label 0.
- `rim15` — minus ≤ 3 mm of the solid faces adjoining label 0 that lie within 15 mm (more than any LV wall) of an
  open pool face.
- `plane` — minus ≤ 3 mm of the solid faces adjoining label 0 that lie within 1 mm of the least-squares plane through
  the open pool faces. This is the cap and nothing else.

**Phantoms**, all at ±0.3 / ±0.5 mm on both borders:
- **A** — India's open-base E6 phantom (the fixture of H::test_open_base_india_phantom_with_the_band): two grids,
  three walls.
- **B** — the cut capsule of `validate_bias_estimator(open_base=True)`: two grids, three shapes, three offsets.
- **C** — a read-like phantom: `harness.phantom()`, with the LA over the base and the RV over the septum, and the LA
  removed over a 60° sector so that the base is open there, as at the outflow. Tilt 0° and 23°.

E11TABLE

**What E11 shows:**
- **The literal remedy is not a fix.** On A and B it leaves no epicardial band at all: every epicardial row is
  undefined. On C it keeps E11C_LIT_KEEP of the epicardial band: only the strip next to the RV and LA. That is a
  biased sample of the wall, and on a real read it would be the septal side.
- **The narrower forms pass.** `plane` and `rim15` bring every phantom within 0.05 mm on both borders: worst
  E11_PLANE_WORST mm (`plane`) and E11_RIM_WORST mm (`rim15`), against 0.0504–0.068 mm shipped. Neither changes the
  endocardium by more than 0.001 mm. `plane` keeps more of the band (A epicardium: E11A_PLANE_KEEP of the shipped
  band, against E11A_RIM_KEEP for `rim15`).
- **The shipped band already passes on the read-like phantom C** (worst E11C_SHIP_WORST mm). There, the LA covers
  most of the base, so the cap left in the band is small. This supports #219's remark that "on real reads, most of
  the myocardial base adjoins LA". The fail comes from phantoms whose whole base is open.

**Recommendation to the judge (P5-1, a candidate amendment to JA61; not built here):**
- Adopt the `plane` form: also remove the voxels within 3.0 mm of any solid face adjoining label 0 that lies within
  1.0 mm of the least-squares plane through the open LV-pool faces.
- Add a guard: if those open faces are not planar (RMS distance to their plane > 1.0 mm, for example a pool leaking
  to label 0 in two places), fall back to `rim15`, and record which form was used.
- **The guard stays 0.5 mm until the amended band ships and the full open-base check passes at 0.05 mm** (JA61
  unchanged), and the transfer check still runs on real reads.

Until the judge rules, nothing changes, and 0.5 mm is the conservative side. If P5-1 is adopted it becomes
`role:swe` item H5-3 (§6).

## 4. Item 3 — the engineers' judgement calls

| PR | Call | Verdict | Reason |
|---|---|---|---|
| #217 | `numbers_only=True` whenever no depth is computed | **Accept** | It hides nothing. A missing median still prints `NOT DECIDABLE: thickness_median_mm` (D:325). When S3 refuses or depth is None, JA41's 0.50 gate cannot be evaluated, and numbers only is what JA60 prescribes for that state. The record keeps `provisional_depth = 0.45` and the footer. It goes beyond JA60's text for the missing-median case, but on the conservative side |
| #217 | `calibrate.population` raises on a phase_mix that omits phases | **Reject** | JA60 prescribes `{"ED": 1.0}` for hypoattenuation, and calibrate's own docstring (`calibrate.py:432`) advertises it. `_phase_key` already turns that into a full mix, and `population_factor` uses the full one. The raise is an unguarded `KeyError`, not a validation, and the engineer's own test (C:121) passes `{"ED": 1.0}` with the sampler stubbed, so it was meant to work. Fix: pass `dict(_phase_key(mix))` down (H5-1) |
| #218 | the full phase-mix dict is passed to S3 | **Accept** | It is required by the H5-1 defect, not just harmless: `reference.py:630` sends `{"ED": 1, "MD": 0, "SYS": 0}`. `population_factor` gives the same 0.99523 for both forms. Thinning passes no mix, so S3 uses JA40's 0.4 / 0.4 / 0.2 for both the factor and the simulation, which matches the phase-uncertain reference population |
| #218 | relative RC needs E_T > 0 per read | **Accept** | It is stricter than "every pair": a pair mean can be positive with one read ≤ 0. `rc_floor_mm` applies RC_rel × E at one read's (or the population's) E, and returns None when E ≤ 0. So a relative RC fitted on pairs that contain a non-positive read would be applied where no floor exists. Any failure falls back to differences, and the decision is recorded |
| #218 | the septal-arc cell shows two values | **Accept** | R4-S14 has features produce both quantities (arc wall and arc relative subendocardial HU) and the reference their percentiles. One ruled cell carries both ("7.52 (p52); 1.00 (p50)"), and the header names them. Elsewhere "—" |
| #218 | an LM lesion point labels both LAD and LCx | **Accept** | JA67: LM feeds LAD and LCx; the mass distal to an LM lesion is in both territories. JA69 defines no distal mass, so the label asserts no number. RCA stays unlabelled (RP:372). Quirk: LAD/LCx show the label even when their own grade, not LM's, decided the row. It is harmless while the mass is "not computed" |
| #216 | the transfer check runs per comparison; any failure gives 0.5 mm | **Accept** | The comparisons are model–read 1, model–read 2 and read–read. JA37 names those pairs but does not say whether to pool them. Taken separately, a failure in any one gives 0.5, which is at least as strict as one pooled median and only ever raises the guard, the direction JA37 / JA62 allow. With the open-base fail, the guard in force cannot be 0.3 anyway (`max` with `BIAS_GUARD_VALIDATED_MM`). The check stays a recorded diagnostic, and it would decide again only if P5-1 restored the open-base pass |
| #220 | `phantom.heart()` defaults to a 2 mm mitral gap | **Accept** | Under JA66, a heart with no gap has no fittable plane and is "could not be checked", so the old default could no longer be a passing read. A real heart has the gap. The gapless case is kept explicitly (`mitral_gap_mm=None`, Q:417, :883, and the server's plane-less case), and the older tests now also run the mitral check, so coverage went up |
| #220 | `adminThirdReads` takes the anchoring report | **Accept, harden (H5-5)** | The server recomputes the seeded set and the draw from the database (`rest.py:398–407`), so the case list cannot be forged. But `rule2.flagged` is trusted as sent (:405): an admin could pass a hand-made report with `flagged: true`, which is what the happy-path test does. The route is admin-only. Cheap hardening: check the report's own consistency (more than half the seeded reads under 5 %, its draw = the server's draw), and store the report's sha256 on the wave |
| #220 | a new `POST admin/wave` | **Accept the endpoint; reject as written (H5-4)** | It is admin-only and idempotent, and it refuses an empty name and unknown cases. But it `$set`s `wave` on any case, including one already in another wave with accepted reads or third-read state (`rest.py:373`). That moves double reads between waves after a report, and changes `_seededDoubleRead(wave)` and therefore `third_read_cases` and Rules 1–2 |
| #220 | the 0.3.0 bump, with 426 for 0.2.x clients | **Accept** | The 426 checks the wire number only (`MIN_CLIENT_PROTOCOL = PROTOCOL_VERSION = 2`), never the package version. JanusMRead 0.1.0 and 0.2.0 both spoke protocol 1, so "0.2.x gets 426" is shorthand for protocol 1, as the doc says (line 19). `border_protocol` stays 1, separately |

## 5. Item 4 — JM-0 / JM-0R aggregates

**None has been posted.** Nothing is on #205, #223, `dev` or this branch. So `jm0r_decide.py` was not run, and R0–R10
keep no value. R9's provisional 45 % stands.

For when they are posted:
- R9 passes no phase mix, so H5-1 cannot crash it.
- R9 does pass `thickness_median_mm` (S2 ✓).
- H5-2 decides only one line of text.

## 6. `role:swe` items for the PM (one issue each; label `path:jm-rest-ccta`; shared code on `dev`)

None changes a threshold. H5-4, H5-5 and H5-6 block the first read wave, as Group D did.

- **H5-1 — `calibrate` takes a partial phase mix (JA60).**
  - **Wrong:** `population()` reads `phase_mix[k]` for every phase, so `{"ED": 1.0}` raises `KeyError: 'MD'`.
  - **Correct:** `detectable_depths` passes `dict(_phase_key(phase_mix))` to `simulate` and `population`;
    `population` normalises the same way. `CALIBRATE_VERSION` 1.1.1 (no number changes).
  - **Test:** unstubbed, `detectable_depth(0.088, LIMA_SHAPE, 1.0, seed=31000, measured_median_mm=6.3,
    phase_mix={"ED": 1.0})` returns a depth equal to the one for `{"ED": 1, "MD": 0, "SYS": 0}`.
- **H5-2 — R9 keeps R3's note when S3 refuses (JA60).**
  - **Correct:** append R3's note in the `except ValueError` branch as well.
  - **Test:** R3 fails and cv_n = 0 → both lines are printed.
- **H5-3 — the amended band (only if the judge adopts P5-1).**
  - **Correct:** `ja37_band` adds §3's `plane` exclusion, with the `rim15` fall-back and a recorded `band_form`;
    `HARNESS_VERSION` 1.3.0.
  - **Tests:**
    - E11's rows A–C reproduce (worst ≤ 0.05 mm);
    - the literal form's empty epicardial band is pinned as the reason it was not taken;
    - `validate_bias_estimator(open_base=True)` at its default 3 offsets, with the verdict pinned to
      `BIAS_GUARD_VALIDATED_MM`.
- **H5-4 — `admin/wave` cannot move a read case (JA68).**
  - **Correct:** refuse (409) a change of `wave` on a case whose wave is already set to another value and that has
    any accepted read, `thirdReadWanted`, or a third read open. Setting the same wave again stays allowed.
  - **Test (Mongo):** a case with an accepted read in wave 1 → 409 to wave 2; an unread case moves.
- **H5-5 — `adminThirdReads` checks the report it is given (JA68).**
  - **Correct:** refuse unless `rule2.flagged` agrees with the report's own counts (> half the seeded reads under
    5 %), and the report's third-read list equals the server's draw. Store the report's sha256 on the wave and in
    the export.
  - **Test (Mongo):** a report with `flagged: true` and counts that do not flag → 400.
- **H5-6 — a lesion point with no CT box is not accepted (JA67).**
  - **Correct:** when lesion points are present and `ctWorldBounds` is None, the read goes down R4-S17's "could not
    be checked" path: returned uncounted, a crash counted, the PM alerted. It is not accepted unchecked.
  - **Test (Mongo):** a case with an unreadable CT header plus a lesion point → not accepted; `crashes` = 1.
- **H5-7 — tests that check the ruling's sentence (no code change).**
  - a. `validate_bias_estimator(open_base=True)` at 3 offsets, with the verdict pinned.
  - b. S7: a fixture where patients ≠ positions, for both n_T and the χ² switch bound.
  - c. S9: a value-level test of `features.case_features`' patient-map fat clusters.
  - d. S12: the real geodesic majority on a phantom whose segment really changes territory.
  - e. S16: a phantom whose LA shadow beats radius + 3 mm, so the footprint equals the shadow.
  - f. S18: 4.94 % of the union / 5.2 % of the seed, and exactly 5 %, both through `wave_report`.
  - g. S19: cases with unequal read counts, so read-weighted and case-weighted bounds differ.
  - h. S21: export with a competing wave that has accepted reads.
  - i. S21: a Slicer reopen where the summed time exceeds the last attempt's.
  - j. S23: an in-list `third: True` record dropped; the `.sha256` file written; no reader key in any output.

## 7. Lead questions

None. P5-1 is for the judge; the guard stays 0.5 mm unless it is adopted and passes.

## 8. What would change this plan

- **Posted JM-0 / JM-0R aggregates:** run `jm0r_decide.py` (Round 4 §8 item 1); R9's depth replaces 45 %.
- **The judge rejects P5-1:** nothing changes. The guard stays 0.5 mm, and H5-3 is dropped.
- **A real read has no open pool face:** the band is the shipped one, and E11 C says the shipped band is already
  within 0.05 mm there. Only the transfer check measures real reads.

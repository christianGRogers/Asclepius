---
aliases: [Janus-M Round 3 rest-ccta]
tags: [janus-m, plans, judgement, round3, path-rest-ccta, myocardium]
author: Janus-M Round 3 judge (path jm/rest-ccta)
round: 3
path: jm/rest-ccta
status: ruling
updated: 2026-10-30
issue: christianGRogers/Asclepius#167
---

# Janus-M Round 3, path `jm/rest-ccta`: the judgement

**Ruling in one paragraph.** Path A's structure stays as Round 2 left it (Hotel v2 + JA15–JA24). Round 3 fixes how
every number is measured and decided before Job JM-0 reports.
- **Base: [[Hotel v3]].** It has the most complete decision procedure (with a stop rule), the correct
  no-double-count reading of the detectable depth, and the only evidence that the shipped voxel ASSD's offset does not
  cancel in JA8's d.
- **Amended by JA37–JA49**, which take:
  - from [[Lima v2]]: exact-shift fixtures and the harness's 1.3× shift finding; the prevalence-free flag gate in
    place of κ; the upper-bound RC; the two-sample anchoring bound;
  - from [[India v3]]: the real-wall validation of the volume estimator (with its disclosed error near 0.3 mm); the
    halves rule; the read-queue change list.
- **Signed-bias guard: 0.3 mm**, met by the volume ÷ mean-area estimator, which already ships as
  `janusm.harness.signed_bias` (JA37).
- **One decision script** (Hotel's, moved beside JM-0R and fed by a fixed JM-0R output block; JA43, JA44).
- **One read-queue change list** (JA46, JA47).
- **No fork.** **This path is plan-complete pending Job JM-0, JM-0R and the lead's answers** (§8).

Rules kept: the judge ran no experiment, opened no image, downloaded no data and read no held-out case. Checks read
committed JSON, committed code and tests, the twin config by count only, GitHub issue states, and Crossref
records.

---

## 1. What was checked

### 1.1 Key numbers against committed JSON: all match

| Advocate | Claim | File | Match |
|---|---|---|---|
| Hotel | vol bias worst 0.012 / 0.019 at ±0.5; pp 0.025 / 0.032; India R2 0.129 / 0.045; Lima R2 0.050 / 0.137; sym 0.067 / 0.079 | `Hotel/r3/e6_summary.json` | yes (0.0121 / 0.0194 …) |
| Hotel | voxel ASSD error +0.038 / +0.045 / +0.014 / −0.057 at 0.25 / 0.3 / 0.5 / 1.0 mm; pp ≤ 0.02 to 0.5 mm | recomputed from `e6_estimators.json` rows | yes |
| Hotel | thickness 0.468 / 0.474 for 0.5 mm, worst 0.057 | `e6_summary.json` | yes |
| Hotel | depth 0.30 at RC 0–0.7 mm, 0.35 at 1.0; Lima-style σ 0.5 → 0.35; cv_n 0.06 / 0.12 / 0.15 → 0.20–0.30 / 0.40 / 0.45; false flags ≤ 0.019 | `e7_detectable.json` | yes |
| Lima | volume_midarea ≤ 0.005 mm on 192 exact shells; inner_boundary +0.13 inward | `Lima/r3/e4.json` | yes |
| Lima | S − d rule realises 0.642–0.650 (d 0.5), 0.414–0.420 (d 0.3) | `e4_sdf_rule.json` | yes |
| Lima | κ passes 0.05 / 0.01 / 0.00 at 0 % prevalence | `e5_ja18.json` (Lima E5 table) | yes (table and note agree) |
| India | volume estimator 0.001 on spheres; real 0.5 mm: −0.022 (96 %), −0.029, −0.022, −0.006 (100 %) | `India/results/e9_estimators.json` | yes |
| India | cv_n 0.0527; σ_m 0.237 / 0.432; depth 20 / 25 / 30 % at cv 0.053; max false flag 0.036 | `e10_detectable_depth.json` | yes |

**One India number needs its context stated.** On real walls India's volume estimator fails ±0.05 mm near 0.3 mm:
- epicardium inward 0.3 mm: median −0.09, **0 %** within ±0.05;
- 0.5 mm plus random error, epicardium inward: −0.077, 4 % within.

India discloses the size ("−0.04 to −0.09 at 0.3 mm"), but its headline says it passes "JA16's test as written".
That holds only because JA16 names a 0.5 mm shift. Hotel E6 (worst 0.054 over 0.1–1.0 mm) and Lima E4 (≤ 0.005 on
exact shells) do not reproduce India's 0.3 mm error. India's truth on real walls is a continuum estimate on a
zoomed field whose slope is 1.05, so part of the gap may sit in the truth itself. JA37 records the error in the
conservative direction.

### 1.2 The PM's notes, verified

**(1) "Volume ÷ area recovers known shifts to ≤ 0.02 mm (Hotel E6, Lima E4, India E9, the #177 engineer)."**
**True on exact shifts, with one caveat.**
- Hotel: worst 0.019 at ±0.5 mm (0.054 at 1.0 mm).
- Lima: ≤ 0.005.
- India: ≤ 0.002 on spheres.
- **#177 already ships this estimator** as `janusm.harness.signed_bias`: ΔV over the mean of the two marching-cubes
  areas, each mask smoothed by one voxel. `tests/test_janusm_harness.py` asserts that `validate_bias_estimator()`
  passes at ≤ 0.05 mm and returns the 0.3 mm guard.
- **The caveat:** on India's real walls the error reaches 0.09 mm near 0.3 mm (§1.1).

**(2) "India's and Lima's R2 estimators miss by ~0.12 mm in opposite directions."** **True.**
- India R2 under-reads outward shifts (−0.116 mean, worst 0.129 at +0.5).
- Lima R2 under-reads inward shifts (+0.123 mean, worst 0.137 at −0.5).
- Lima E4 (+0.13 inward) and India E9 (−0.12 outward) agree.
- Cause: each samples one mask's surface voxels in the other's distance map.

**(3) "The JA15 harness's shift rule realises ~1.3 × d, so JA16's answer key is off."** **True for `perturb()`, not
for JA16's check as built.**
- `perturb()` (`src/janusm/harness.py`, lines 142–143) thresholds `corrected_sdf + field − bias < 0`. Lima E4
  measures that rule at 0.642–0.650 mm for a nominal 0.5 and 0.414–0.420 for a nominal 0.3. The cause is that the
  corrected distance takes coarse values near the border (0.25 mm at a face neighbour, 0.46 mm at a diagonal one).
- But `validate_bias_estimator()`, which decides JA16, compares voxelisations of **exact analytic** signed
  distances offset by the shift, not `perturb()`. **Its answer key is exact, and it passes.**
- What is off: any harness result labelled by the nominal `bias_endo` / `bias_epi`. That includes Round 2's
  "0.5 mm bias costs 0.63 mm of thickness", which realised ≈ 0.64 mm. The ≈ 1 mm-per-mm conclusion of JA16 stands.
- **India's "0.94–0.99 of nominal" is a different rule, not a contradiction.** India thresholds a continuous field
  interpolated from 1.5 mm labels, which has no coarse values. JA38 settles the wording.

**(4) "Voxel ASSD over-reads ~0.04 mm at 0.25–0.3 mm; Hotel proposes point-to-plane ASSD for JA8."** **True, and
all three data sets show why it matters.** The offset changes with the displacement in every set:

| Source | 0.1 mm | 0.25–0.3 mm | 0.5 mm | 1.0 mm |
|---|---|---|---|---|
| Hotel E6 | +0.014 | +0.038 / +0.045 | +0.014 | −0.057 |
| Lima E4 | +0.02 | +0.06 | +0.04 | −0.04 |
| India E9 (spheres) | — | +0.06 | +0.04 | — |

- Lima and India say it "largely cancels" in d = model-vs-read − read-vs-read. It cancels only if both terms sit at
  the same displacement.
- At a read-vs-read near 0.3 mm and a model-vs-read near 0.5 mm, the offsets differ by ≈ 0.02–0.03 mm, in the
  **lenient** direction. That is about a tenth of the 0.25 mm margin. JA39 adopts pp for scoring.

**(5) "Detectable thinning ≈ 30 % (Hotel E7); India E10: 80 % at ≈ 30 % with ≤ 3.6 % false flags. Reconcile."**
**They agree in number, for different reasons, and a third estimate (Lima, 45 %) disagrees.**

| | cv_n | Error added on top | F1 floor | Depth | Max false flags |
|---|---|---|---|---|---|
| Hotel E7 | 0.088 (plain SD) | none: cv_n is measured on the model's own borders | 0–0.7 mm / 1.0 mm | **30 % / 35 %** | 1.9 % |
| India E10 | 0.053 (robust SD of log) | σ_m 0.43 mm | none | **30 %** | 3.6 % |
| Lima E5 | 0.088 | σ 0.5 mm | RC from σ 0.5 (≈ 0.5–0.7 mm) | **45 %** | ≈ 1.7 % |
| Hotel E7, Lima-style row | 0.088 | σ 0.5 mm | 0.7 / 1.0 mm | 35 % / 35 % | 1.7–1.1 % |

- **India's 30 % and Hotel's 30 % coincide.** India's lower cv_n is offset by its added error.
- **India's cv_n is a different statistic.** It is a robust (MAD) SD of log relative thickness. Lima's self-test
  and JM-0R (`cv_n_shape_corrected_sd`) use the plain SD of thickness ÷ shape. The robust SD drops tail segments,
  so 0.053 vs 0.088 is partly definition, not anatomy. No advocate flagged this.
- **Hotel's double-count argument is correct** when cv_n is measured on the borders of the model that fills the
  table. JM-0R measures it on `heartchambers_highres`, which is Janus-M 0. India's cv_n came from TotalSegmentator v1
  labels, a different model, so adding error there was only partly a double count.
- **Lima's 45 % against Hotel's 35 %, for nominally the same inputs, is unexplained.** The two F1 implementations
  differ: Lima applies F1 to a territory mean minus the remote median, Hotel to a shape-corrected deviation. Lima also
  reports run-to-run steps of 5 points (a first run gave 40 %). The judge does not run code; Round 4 explains it
  (§8). JA40 fixes one procedure and prints the more conservative figure until JM-0R.
- **The dominant input is cv_n:** 0.06 → 20–25 %, 0.12 → 40 %, 0.15 → 45 % (Hotel lookup). JM-0R decides.

**(6) "The κ ≥ 0.6 gate rarely passes on an infarct-free decision set (Lima E5); Lima proposes a prevalence-free
gate."** **True; adopted with changes (JA41).**
- κ needs true positives to agree on. With none, both reads flag only chance territories, which do not agree. This
  is the known prevalence dependence of κ (Cohen 1960's statistic, checked).
- **Hotel's "κ not estimable below 5 flagged units → number only" makes it worse.** On an infarct-poor set it would
  turn every sign into a number, by construction.
- Reproducibility under the null is already enforced by F1, which needs the deviation to exceed read noise.

**(7) "JA21's paired anchoring bound cannot be paired."** **True.** The 10 blank seal cases are read blank by both
readers, and seeded cases are seeded for both. No case has a blank and a seeded read, so the bound is two-sample
(JA47). India v3 already specifies a two-sample bootstrap; Hotel's text still says "paired".

**(8) "Canonical half-maximum sign: + = the labelled region extends beyond the edge; Hotel's R2 add-on had the
endocardium reversed."** **True, and the merged JM-0R has the same reversal.**
- The JM-0R docstring defines s as pointing into the labelled myocardium, so for the endocardium + means "the label
  puts the border too far toward the blood".
- `tests/test_janusm_jm0r_readout.py::test_a_moved_endocardium_moves_the_offset_by_that_distance` grows the label's
  LV pool 1 mm past the edge and asserts **−1.0 mm**. Under the canonical sign that is **+1.0**.
- The epicardium agrees with the canonical sign. JA17 and every rule use |offset|, so no decision changes, but the
  sign reported and the direction of the snap tool would. JA44 fixes it before JM-0R runs.

**(9) "Three decision scripts exist; pick one or say how to merge."** **None of the three can read the merged
JM-0R's output.**
- JM-0R writes nested blocks (`hotel`, `lima`, `ja17_rest_tpr_gate`, …) with its own key names. Hotel expects
  `endo_offset_mm_median`, Lima `halfmax_endo_mm`, India `endo_halfmax_offset_mm_median`, all flat.
- Lima's script would exit on JM-0R's unknown keys; Hotel's and India's would mark every rule not evaluable.
- JA43 picks Hotel's script as the one to build on; JA44 makes JM-0R emit the block it reads.

**(10) "Read queue: Hotel lists 9 changes, India 6, including the checker accepting 1.0 mm where JA21 says
0.5 mm."** **True** (`src/janusm_reads/checker.py`: `tolerance_mm = 1.0`, and any octant fails). Three of the
change lists need correcting, checked against the code:
- **Window.** Lima says it is "already plateau-centred, keep". **Half right.** `halfmax.window_for` puts the level at
  the border's half-maximum, but the width is 50 HU (`BORDER_WIDTH_HU`), and the module opens at 800 / 300
  (`CT_WINDOW`, `CT_LEVEL`). Hotel v2 §5.4, the text JA21 adopted, sets the width at ≈ 1.5 × |p₁ − p₂| and opens on
  it.
- **LV–RV contact.** Hotel tightens it from ≤ 0.5 % to no shared face. **Rejected.** The membranous septum is
  fibrous, not labelled myocardium, so the two pools may legitimately meet there. JA21 did not ask for it.
- **The mitral-plane check contradicts JA21's own "labels 2 and 4 never touch".** India v2 meant a required
  mitral gap of label 0 or 1. A plane "fitted to the 2–4 interface" (Hotel, Lima, India v3) therefore has no
  interface to fit on a compliant read. JA46 fits it to the gap.

### 1.3 Further checks

- **Twin re-pin (JA22, #168): merged.** `configs/janusm/ts-twins-r1.json` now lists **710** twin keys (707 before).
  With the held-out 16 that makes **711 refused**, exactly what Round 2 inferred for Hotel's wider rule. This was
  counted by set size only; no id was printed.
- **Held-out disclosures.**
  - Hotel opened no case.
  - Lima opened only the 23 public cardiac subjects the shared guard allows.
  - India opened public v1 masks of guard-allowed subjects (0 of 299 refused), and no CT.
  - No committed Round 3 file names a held-out id.
- **Issues.** #168, #169 and #170 are closed (built). #142, the Round 2 issue, is closed, so the path summary for the
  lead goes on #167.
- **Citations (Crossref, this round).** All six resolve, with matching details:
  - Cohen 1960, *Educ Psychol Meas* 20(1):37–46;
  - Shrout & Fleiss 1979, *Psychol Bull* 86(2):420–428;
  - Lorensen & Cline 1987, *SIGGRAPH Comput Graph* 21(4):163–169;
  - Wasserthal 2023, *Radiol Artif Intell* 5(5):e230024;
  - Chen 2025, *Clin Imaging* 118:110390;
  - Bland & Altman 1986, *Lancet* 327(8476):307–310.

  No number is taken from them beyond the method.

---

## 2. Scorecards

Scale 1–5:
- **(a)** reasoning;
- **(b)** evidence;
- **(c)** fit to path A and to what the project can get;
- **(d)** risk and cost (5 = low risk, cheap).

### Hotel v3: measure the borders exactly, pre-register every decision, print what cannot be seen

| | Score | Why |
|---|---|---|
| (a) | **5** | Finds that a displacement-dependent ASSD offset does not cancel in d, and that cv_n on the model's own borders already holds its error. The only procedure with a stop rule (R0, ≥ 36 of 40 usable) and a pre-stated conservative branch for every missing input. Correct on the canonical sign and the R2 reversal |
| (b) | **4** | E6 is the round's most thorough estimator test (336 conditions, two grids, oblique and rough walls, five estimators, pass rule fixed before the run); E7 imports Lima's code unchanged, with replicates. Deducted: two rules unsupported by evidence (halves everywhere above 25 %; strict LV–RV contact); "paired" anchoring left as written; missed JM-0R's reversed sign |
| (c) | **5** | Specifications are issue-ready and map onto the merged code paths; the change list cites files and lines |
| (d) | **4** | pp is new code to ship and test; everything else is CPU and already costed |

### Lima v2: settle what can be settled before JM-0

| | Score | Why |
|---|---|---|
| (a) | **5** | Two findings no one else made: the harness's shift rule over-shifts by ≈ 1.3×, and the κ gate measures the decision set's prevalence, not the sign. Also found the paired-bound ambiguity. "No default for a missing number" is the right discipline |
| (b) | **4** | E4 on exact shells is the cleanest truth of the round; E5's κ grid is decisive. Deducted: E5's 45 % adds error to a cv_n already measured on model borders, and conflicts with Hotel's same-input 35 %, unexplained; a first run gave 40 %, so its page line moves by a step between seeds |
| (c) | **4** | Window change "already done" is half wrong (§1.2 (10)); keeps octants as failing checks, which JA21 did not ask for; its script cannot read JM-0R as merged |
| (d) | **4** | Cheap; L11's upper bound costs a few points of depth, which are printed |

### India v3: path A, ready to apply the moment JM-0 reports

| | Score | Why |
|---|---|---|
| (a) | **4** | Clear structure and a sound halves rule. Deducted: R3 invents a "≈ 100 training reads" request that no ruling pre-registered; LQ13 asks the lead to choose a parameter Round 2 already gave Round 3 to rule on |
| (b) | **4** | E9 is the only test on real walls with an independent (continuum) truth, and discloses its one-sided error. Deducted: the headline "passes" glosses over the 0.3 mm failure in its own data; its cv_n is a different statistic from JM-0R's, unflagged |
| (c) | **4** | Specifications usable; the change list is accurate on the window; its mitral plane ("LV voxels touching LA") contradicts its own never-touch rule |
| (d) | **4** | Cheap; R9 runs in the script |

**Totals (of 20):** Hotel 18, Lima 17, India 16. **Hotel v3 is the base.**

---

## 3. Rulings where they disagree

| Item | Hotel | Lima | India | **Ruling** |
|---|---|---|---|---|
| Bias estimator | vol; pp cross-check | volume_midarea | ΔV / Ā | **the shipped `harness.signed_bias` (same estimator); pp as the transfer check** (JA37) |
| Bias guard | 0.3 | 0.3 | 0.3 (with caveat) | **0.3 mm, error near the guard disclosed** (JA37) |
| Fixture shifts | exact phantom | exact, report the realised shift | continuum truth | **exact analytic shifts; harness rows report the realised shift** (JA38) |
| ASSD for JA8 | pp | voxel (cancels) | voxel (cancels) | **pp for both terms of d; voxel reported and kept for anchoring** (JA39) |
| Detectable depth | e7, σ_m 0, F1 swept: 30 % | e5, σ_m added, F1: 45 % | e10, σ_m added, no F1: 30 % | **one procedure (Hotel's), conservative inputs until JM-0R: print 35 %** (JA40) |
| κ gate | κ, "not estimable" → number only | replaced by depth ≤ 50 % | κ as JA18 | **depth gate; κ and ICC reported** (JA41) |
| F1 RC | AHA map, shape-corrected, pooled, point estimate, offset added | patient map, raw deviation, upper 95 % bound | own frames, point estimate, CI shown, heteroscedasticity | **merged** (JA42) |
| Decision script | `jm0r_decide.py` | `apply_r2_rules.py` | `jm0r_rules.py` | **Hotel's, moved and extended** (JA43) |
| Halves > 25 % | Table A halves everywhere | report | header states it | **JA2 per segment; the header states it** (JA43) |
| Seed offsets | ≥ 0.5 snap seeds; 0.25–0.5 TPR only | same (> 0.5) | > 0.5 request ≈ 100 training reads | **Hotel/Lima, > 0.5; India's request not adopted; its guard forecast printed** (JA43) |
| Geodesic ≥ 10 % | Euclidean + "shared" | Round 4 rules | lead rules (LQ13) | **ruled now: Euclidean primary; differing segments "shared"; geodesic mass in the research export** (JA43) |
| AHA > 10 % | fix before reference population | fix before any table | fix before any read | **fix before decision-set scoring, the reference population and any table; reads proceed** (JA43) |
| Fat candidate order | patient rule if "less strict" | grid only | grid, then patient rule | **grid in order, then the patient rule** (JA43) |
| Anchoring bound | paired | two-sample | two-sample | **two-sample** (JA47) |
| Wave re-read | 10 blank cases | 5 seeded cases re-read blank by a fresh reader | one blank case | **Lima's** (JA47) |
| Octant check | warning | 1.0 mm, fails | — | **warning only** (JA46) |
| LV–RV contact | strict | ≤ 0.5 % | ≤ 0.5 % | **≤ 0.5 %** (JA46) |

---

## 4. Binding amendments (JA37–JA49; path `jm/rest-ccta`)

- **JA37 — Signed bias: one estimator, guard 0.3 mm.**
  - **The estimator.** It is `janusm.harness.signed_bias`: volume change ÷ the mean of the two borders' marching-cubes
    areas, each mask smoothed by one voxel. It is the same estimator as Hotel's vol, Lima's volume_midarea and
    India's ΔV / Ā.
  - **Validation.** Three independent tests support it, and the shipped `validate_bias_estimator()` passes on exact
    phantoms. **JA16's condition is met: the guard is |bias| ≤ 0.3 mm** from the freeze PR on.
  - **Disclosed error.** On real walls, near 0.3 mm, it reads up to 0.05 mm low for outward biases and up to
    0.09 mm high for inward ones (India E9). So a true outward bias of up to ≈ 0.35 mm can pass. That is recorded,
    not corrected.
  - **Retired.** The Round 2 estimators (India `border_stats`, Lima `assd_and_bias` / `inner_boundary`) are never used
    for a guard.
  - **The transfer check.** On the first 20 decision double reads, the model-vs-read and read-vs-read bias is also
    computed with Hotel's pp. If the median |vol − pp| over those pairs exceeds 0.05 mm, the phantom validation has
    not transferred, and the guard returns to 0.5 mm before any seal read (Hotel v3 §10). Cases where vol and pp
    differ by > 0.05 mm are listed.
  - **Region.** On real cases the bias is taken in a band around the reference read's border, excluding ≤ 3 mm from
    the LA and the aorta (Hotel E6), so basal-limit differences never count as bias.
- **JA38 — Known shifts are exact; nominal shifts are labelled.**
  - `perturb()`'s `bias_endo` / `bias_epi` are **nominal**. The rule realises ≈ 1.3× (0.64 mm for 0.5; 0.41 for
    0.3; Lima E4).
  - Every harness result reports the realised signed bias and ASSD, and is indexed by them (JA15).
  - A fixture or validation that needs a known shift uses exact analytic signed distances, as
    `validate_bias_estimator()` already does.
  - **JA16's text is read as** "recover an exact ±0.5 mm shift of an analytic phantom".
  - **Round 2's record is corrected:** the "0.5 mm" bias rows realised ≈ 0.64 mm. The ≈ 1 mm of thickness per mm of
    bias stands.
- **JA39 — ASSD for JA8: point-to-plane.**
  - **Scoring.** JA8's d (model-vs-read and read-vs-read), and the absolute ASSD ≤ 1.0 mm guard, use Hotel's
    sub-voxel point-to-plane ASSD (pp), one implementation for both terms.
  - **Reported beside it:** the voxel ASSD (`segtrain.metrics.surface_distances`).
  - **Kept as is:** the read checks and JA21 anchoring keep the voxel ASSD, because they compare reads with reads
    against a 0.2 mm margin.
  - **Fixture tolerances (Hotel E6):** pp ASSD within 0.03 mm of the truth up to 0.5 mm and 0.07 mm at 1.0 mm, on
    both grids, oblique and rough walls.
  - **Thickness is unchanged:** `janusm.geometry` equal-thickness, median over segments 1–16. It is exact on shells
    (Lima, India) and shrinks changes by ≈ 6 % on Hotel's phantom.
- **JA40 — The detectable depth: one procedure, conservative until measured.**
  - **The procedure:** Hotel's `e7_detectable.py` logic on Lima's `calibrate_sim.py`, shipped as one function
    (Shipping S3), with these settings:
    - mixed phase (40 / 40 / 20), prevalence 0.1, 4 replicates of 2000;
    - depth = the smallest relative thinning with mean territory sensitivity ≥ 0.80, rounded **up** to 0.05.
  - **cv_n.** It is the **plain SD** of thickness ÷ shape (JM-0R's `cv_n_shape_corrected_sd`). India's robust log SD
    is reported beside it, never used. The plain SD is larger, so the printed depth errs high.
  - **No added error** when cv_n is measured on the borders of the model that fills the table. That is JM-0R for
    Janus-M 0, and the reference-population job for whichever model passes. Otherwise (for example cv_n from another
    model's labels), the measured segment error at JA8's edge is added.
  - **F1 floor.** It is 1.0 mm until the reads exist, then JA42's RC.
  - **Printed now, provisionally: 35 %** (cv_n 0.088, F1 1.0 mm; Hotel E7). Hotel's sentence is the page text,
    with the number filled in.
  - **Sensitivity rows, never the print:** Lima E5's 45 % and India E10's 30 %.
  - **If the depth exceeds 0.40,** the page says so, and nothing is loosened (Hotel).
- **JA41 — The flag gate: prevalence-free, replacing JA18's κ ≥ 0.6.**
  - **A sign shows as a flag only if all three hold:**
    1. its rule C cut;
    2. F1 (JA42);
    3. its detectable depth, computed by JA40 with the reference population's cv_n and shape and the measured RC,
       is **≤ 0.50**.
  - **Otherwise** it shows as a number with its percentile.
  - **κ and ICC** (two-rater, absolute agreement; Shrout & Fleiss 1979) are computed on the 40 decision cases per
    sign and reported. κ is marked "not estimable" when either read has < 5 flagged units. **Neither gates.**
  - **Why:** κ cannot pass on an infarct-poor set however good the sign (Lima E5: 1–5 % at 0 % prevalence), while
    read reproducibility is already enforced by F1. The 0.50 bound is Lima's. A depth gate at 0.40, the depth at
    which Hotel's page already warns, was considered; it would leave the sign dark at cv_n ≥ 0.12 although its
    specificity is unchanged.
  - **For fat** (a cluster count, not a thinning depth): the gate is F1 plus κ reported. The depth gate applies to
    thinning and hypoattenuation.
- **JA42 — F1's repeatability coefficient, one procedure.** Computed on the first 20 decision cases with two
  accepted reads, per sign s and territory T (LAD, LCx, RCA):
  1. **Map.** Use the patient-specific Euclidean territory map from the ImageCAS-X reference tree, the same tree for
     both reads (it is the map that is reported; Lima, India). Segments come from each read's own AHA frame, so
     frame jitter counts as read noise (India).
  2. **Deviation.** D_irT is Hotel's shape-corrected deviation (`f1_deviation` in `e7_detectable.py`), because it is
     the quantity the flag tests. For fat, D is the territory's core cluster volume.
  3. **Spread.** Take Δ_iT = D_i1T − D_i2T and SD_T over the cases.
     - Per territory if n_T ≥ 15, else pooled over territories.
     - The pooled value is used unless a territory's SD exceeds the pooled SD's 95 % χ² upper bound (Hotel).
  4. **RC_T** = 1.96 × SD_T × √((n − 1) / χ²₀.₀₂₅,ₙ₋₁), the upper 95 % bound (Lima L11), with n = the number of
     patients.
     - If |mean Δ| > 0.5 × SD_T, |mean Δ| is added (Hotel).
     - If Spearman ρ(|Δ|, mean D) > 0.4, RC is computed on log ratios and applied multiplicatively (India).
  5. **Reported:** the point estimate, the bound, n and the decision taken at each step.
- **JA43 — One pre-registered decision procedure.**
  - **The script.** Hotel's `jm0r_decide.py` is the one to build on. It moves to
    `experiments/JanusM/fir/jm0r_decide.py`, beside JM-0R. Lima's and India's scripts are retired: their fallback
    mappers are ported, and their dry runs stay as records.
  - **Inputs.** It reads JM-0R's `decision_inputs` block (JA44), or the JA23 fallback through ported mappers
    (Lima `from_lima_jm0b`, India `merge_fallback`, Hotel's own). The fallback mappers negate Hotel R2's endocardial
    sign.
  - **Missing inputs.** A missing input prints "NOT DECIDABLE: <key>" and takes the conservative branch below. No
    default value is ever substituted (Lima).

  | # | Rule | Decision |
  |---|---|---|
  | R0 | usable cases | ≥ 36 of 40 → proceed; else stop and apply nothing |
  | R1 | AHA frame (JA3) | failing cases show "AHA frame failed" and no segment table. > 10 % failing frame or orientation → a `role:swe` frame fix before decision-set scoring, the reference population and any table (reads proceed) |
  | R2 | halves (JA2) | per segment, as the module computes; > 25 % → Table A's header states the layer count per segment (India). Never halves everywhere |
  | R3 | thickness definition | median within 4.2–8.0 mm → F3 holds; else readers hand-measure 3 mid-ventricular segments on the first 20 decision cases, the definition is aligned before the reference population, and no thinning flag ships before that |
  | R4 | seed offsets (canonical sign) | either \|offset\| > 0.5 → the snap tool (S8) runs on the seeds before any read; \|endo\| > 0.25 → rest TPR needs snapped borders. Printed, never acted on: whether the seed is expected to fail the 0.3 mm guard (> 0.3; India) |
  | R5 | rest TPR (JA17) | edge > 2 → not computed; edge ≤ 1.5, \|endo\| ≤ 0.25 (or snapped) and the median adaptive-guard free-wall TPR in 0.99–1.15 → shown as a z-score; edge and TPR pass but offset fails → shown after snapping; else research export. Missing → not shown |
  | R6 | fat cut (JA18) | the least strict grid cell (c = 0, −30, −50, −100 HU, then V = 5, 20, 50 mm³ within each c) with ≤ 5 % of hearts; if none, Hotel's patient rule if ≤ 5 %; else fat is a number only. Provisional; fixed on the reference population |
  | R7 | septal-arc column (JA20) | median share of mass changing segment < 10 % → dropped; else kept. Missing → kept (a sensitivity column) |
  | R8 | geodesic (JA20) | **ruled now:** Euclidean is primary whatever the share. If ≥ 10 % of segments change majority, those segments are marked "shared" in Table A/B and geodesic mass goes to the research export. No lead question (India's LQ13 is not opened) |
  | R9 | detectable depth | JA40 with JM-0R's cv_n and shape; the page prints it |
  | R10 | equal thickness vs Laplace | reported only |

- **JA44 — JM-0R: canonical sign and output contract.**
  - **The canonical sign.** For every half-maximum offset (JM-0R, the read checker's report, the queue export, the
    table header): **+ = the region bounded by that border extends beyond the image half-maximum.** That region is
    the LV pool for the endocardium, and pool + myocardium for the epicardium.
  - **The fix.** JM-0R's endocardial offset is negated (epicardium unchanged), `SCRIPT_VERSION` is bumped, and the
    moved-endocardium test asserts +1.0 mm.
  - **A new block.** JM-0R adds one flat `decision_inputs` object to `summary.json`. It contains aggregates only,
    with these keys and units:
    - `n_cases`, `n_usable`;
    - `aha_frame_fail_share`, `aha_orientation_fail_share`;
    - `thickness_median_mm`, `halves_segment_share`;
    - `endo_halfmax_offset_mm_median`, `epi_halfmax_offset_mm_median` (canonical);
    - `endo_edge_10_90_mm_median`;
    - `tpr_guard1_freewall_median`, `tpr_guard_adaptive_freewall_median` (median over pooled free-wall segments,
      as JA17's gate already computes), `tpr_guard_adaptive_freewall_patient_median` (reported),
      `tpr_guard_adaptive_share_below_0p99` (reported);
    - `fat_grid` ({"c,V": share of hearts}), `fat_patient_rule_share`;
    - `septal_arc_mass_changed_median`, `geodesic_segments_changed_share`;
    - `et_laplace_third_agreement_median`;
    - `cv_n` (plain SD, JA40), `cv_n_robust_log`, `segment_shape` (16 floats), `rel_subendo_hu_sd`;
    - `script_version`.
  - **Acceptance.** The JA43 script, run on JM-0R's synthetic test output, prints no NOT DECIDABLE (Lima's test).
- **JA45 — The harness API.** `janusm.harness` exposes, one implementation each:
  - `signed_bias` (vol, as shipped);
  - `signed_bias_pp` and `assd_pp` (Hotel E6's pp, ported);
  - `surface_assd` (voxel, reported);
  - `segment_thickness` / `thickness_error`;
  - a public exact-shift phantom.

  `compare()` returns `assd_pp_*`, `assd_voxel_*`, `bias_*` and `bias_pp_*` per border. `run()` records the nominal
  and the realised bias side by side. `HARNESS_VERSION` → 1.1.0. Tests: E6's conditions with JA39's tolerances, and
  E4's exact shells for `signed_bias` (±0.01 mm up to 1 mm).
- **JA46 — Border protocol v1, final** (Hotel v3 §5.1, as amended here). It is written into
  `docs/JANUSM-READ-PROTOCOL.md` as "protocol v1 (JA21, JA46)". It changes Hotel's text in four places:
  - **(a) Mitral plane.** It is fitted by least squares to the label-2 voxels within 3 mm of label 4 (the mitral
    gap); in the seed, to its 2–4 interface. If neither exists, it is fitted to the annular hinge points. "Labels 2
    and 4 never share a face" stays: the gap is label 0 or 1.
  - **(b) LV–RV contact** stays ≤ 0.5 % of the LV-pool surface (not strict).
  - **(c) Octant offsets** (> 1.0 mm) are warnings only. The whole-border median ≤ 0.5 mm decides.
  - **(d) The read form** adds the per-vessel CAD-RADS 2.0 grade of the worst lesion (0, 1, 2, 3, 4A, 4B, 5, N) and
    an optional lesion point (world mm), on seal and decision cases. It is never shown to the other reader
    (LQ10 (a)).
- **JA47 — Anchoring, as code.** Per wave and per border:
  - **The gap:** gap = mean seed-vs-read voxel ASSD on blank-case reads − the same on seeded-case reads.
  - **Rule 1.** Seeded reads cannot accept a model if the upper 95 % bound of (gap − mean seeded inter-read ASSD)
    exceeds 0.2 mm. The bound comes from a **two-sample** bootstrap: blank and seeded cases are resampled
    independently, 2 000 draws, fixed seed.
  - **Rule 2.** If more than half of a wave's seeded reads change < 5 % of seed voxels, the wave is flagged. Then 5 of
    its seeded cases, drawn by salted hash, get a third read from blank by a reader who has not read them, and Rule 1
    is evaluated on them (Lima). Third reads never enter the reference standard.
- **JA48 — Reference population and table writer: one specification each.**
  - **The base:** Hotel v3 §4.1 (Issue A) and §4.3 (Issue B), with these changes:
    1. the config is named `configs/janusm/reference-r1.json`, sha256-pinned in the guard's `PINNED`, written by
       `tools/janusm/build_reference.py`;
    2. its gate fields follow JA41 (`gate[sign]`: depth, pass, κ, ICC) and its `rc` fields follow JA42;
    3. the concordance phrase is chosen by Lima v2 §3 item 4c's table, which handles "not graded";
    4. Table A prints no per-segment flag (JA18): flags are territory-level in Table B only;
    5. the header carries the canonical-sign offsets (JA44), the halves note (R2), `HARNESS_VERSION`,
       `GEOMETRY_VERSION`, the config sha256 and `guard_version`;
    6. the builder refuses any seal, decision or JM-0 case.
  - **Tests:** Hotel's, Lima's and India's lists, together: golden outputs, one test per phrase, a refused changed
    config, the forbidden-word test, byte-identical reruns, and a refused guard hit before any read.
- **JA49 — Record.** JA14 and JA24 stand. Added:
  - the twin re-pin is merged: 710 twin keys, **711 refused**;
  - JM-0R's endocardial sign was reversed until JA44;
  - Lima's "window already plateau-centred" is half right;
  - India's volume estimator fails ±0.05 mm near 0.3 mm on its own real walls, which it disclosed;
  - India's cv_n is a robust log SD, not JM-0R's statistic;
  - Lima's and Hotel's F1 implementations give 45 % vs 35 % on nominally equal inputs, unexplained;
  - Hotel's strict LV–RV check and "halves everywhere" are rejected;
  - the six new citations resolve.

---

## 5. Questions for the lead (each with a recommendation; none is a fork)

**Carried unchanged, as assumptions:** LQ2–LQ12, each with its recommendation (all three candidates assumed the
same). LQ23 and LQ24 are not used.

### LQ19 — Hold JM-0R until its sign and output fix (JA44) merges?

- **Options:**
  - (a) run Job JM-0 now; run JM-0R once S2 merges;
  - (b) run both now, and let the decision script's mapper negate the endocardial sign by `script_version`;
  - (c) wait for both fixes before JM-0 as well.
- **Recommendation: (a).** JM-0 does not depend on the fix. If JM-0 returns first and S2 is not merged, (b) is
  safe, because every rule uses |offset|.

### LQ20 — Reader time for anchoring third reads (JA47 rule 2)

- **The facts:** each flagged wave costs 5 extra blank reads (about 5 reader-cases), within LQ5's budget.
- **Options:**
  - (a) allow up to two flagged waves (10 reads) before the lead is asked again;
  - (b) one wave;
  - (c) none: a flagged wave stops seeded acceptance outright.
- **Recommendation: (a).**

### LQ21 — Accept that path A may ship with no flag at all

- **The facts:** under JA41, a sign flags only if its detectable depth is ≤ 50 % at the measured read noise. If
  JM-0R's cv_n is ≥ 0.15, or the reads are noisy, every sign can end up "number only". Path A would then deliver
  measurements, percentiles and territory mass, but no territory flag.
- **Options:**
  - (a) accept: the table ships with numbers only, and the page says why;
  - (b) lower the bar (for example a depth gate at 0.60);
  - (c) treat it as a reason to prefer path B.
- **Recommendation: (a).** (b) trades specificity for display, against JA18. (c) belongs to the lead's path choice
  and needs JM-0R's numbers first.

### LQ22 — Pause this path's rounds until JM-0 and JM-0R report?

- **The facts:** the plan is complete (§8). A further round before JM-0R would argue without data.
- **Options:**
  - (a) pause: Round 4 opens when the lead posts JM-0 / JM-0R aggregates, or when the S-items are merged for
    checking;
  - (b) keep iterating every round.
- **Recommendation: (a)**, to save advocate budget. The `role:swe` items proceed in the meantime.

---

## 6. Forking question: **no fork**

The cap allows one (2 of 4 paths active). Nothing open on this path changes its structure:
- JA37–JA48 are measurement rules;
- LQ19–LQ22 are timing, reader time and display;
- R8 (geodesic) is ruled now.

The one structural question left, path A against path B, is LQ1 itself, which the lead answers by choosing a path.

---

## 7. Shipping (`role:swe`; one issue each)

Code shared with path B (Stage A) goes on **`dev`** and is synced to both paths by the PM (as #183 did). Each issue
cites this ruling and #167, and is labelled `path:jm-rest-ccta`.

1. **S1 — Harness API (JA39, JA45; dev).**
   - Port Hotel E6's pp (`signed_bias_pp`, `assd_pp`) into `src/janusm/harness.py`.
   - Extend `compare()` and `run()` as JA45 states, and make the exact-shift phantom public.
   - Bump `HARNESS_VERSION`.
   - Tests: E6's conditions (two grids, oblique, rough) with JA39's tolerances; E4's exact shells for `signed_bias`.
   - Done when: `pytest`, `ruff` green; `validate_bias_estimator()` still passes.
2. **S2 — JM-0R v2 (JA44; dev).**
   - Negate the endocardial offset, and fix the docstring to state the canonical sign.
   - Add the `decision_inputs` block (JA44 keys), with `cv_n_robust_log`.
   - Bump `SCRIPT_VERSION`.
   - Tests: the moved-endocardium test reads +1.0; the block has every key on the synthetic case.
3. **S3 — The detectable-depth function (JA40; dev).**
   - `src/janusm/calibrate.py`: Lima's `calibrate_sim` (population, rule C, mirror-null `calibrate_c`, territory
     flags) and Hotel's e7 loop (F1 floor, replicates, round up).
   - Signature: `detectable_depth(cv_n, shape, rc_terr_mm, *, sig_m=0.0, seed) -> {depth, sens_range, false_flag}`,
     plus `page_line(...)`.
   - Tests: it reproduces Hotel E7's primary rows (0.30 at RC 0; 0.35 at RC 1.0; cv_n 0.088, Lima's shape) at fixed
     seeds.
4. **S4 — The decision script (JA43; dev).**
   - Move `Hotel/r3/jm0r_decide.py` to `experiments/JanusM/fir/jm0r_decide.py`.
   - Read `decision_inputs`; port Lima's and India's fallback mappers.
   - Apply R0–R10 as tabled in JA43; R9 calls S3.
   - Print one line per rule, with its number and source, and write `decisions.json`.
   - Tests: every branch on synthetic inputs; the S2 synthetic summary prints no NOT DECIDABLE; R0 stops on 23
     cases.
5. **S5 — Read queue to protocol v1 (JA46, JA47; dev; supersedes Hotel v3 §5.2 and India v3 §7's lists).** The
   consolidated list:
   1. Window: open on the border window. Level at the half-maximum (as now); width 1.5 × |p₁ − p₂| instead of 50 HU
      (`halfmax.py` `BORDER_WIDTH_HU`, `window_for`); 800 / 300 stays available, not the default (`JanusMRead.py`).
   2. Half-maximum: per-border median ≤ 0.5 mm (`checker.py` `tolerance_mm`). Octants > 1.0 mm become warnings.
      Update `tests/test_janusm_reads.py`.
   3. Return once: use `attempts` (`server/girder_janusm/models.py`). A second failure is accepted with
      `flagged: true` and reasons (`check.py`, `protocol.py`). Send the half-maximum profile plot with the return.
   4. New hard checks (`check_conventions`): no label 2–4 face; label 2 ≤ 3 mm above the JA46 (a) plane. LV–RV
      contact stays ≤ 0.5 %.
   5. Anchoring (`anchoring.py` `wave_report`): JA47's rule 1 (two-sample bootstrap, 0.2 mm) and rule 2 (wave flag,
      5 third reads from blank by a fresh reader, never in the reference standard). Seed and read half-maximum
      offsets go into the report.
   6. Read form (`protocol.py`, Slicer module): per-vessel CAD-RADS 2.0 and an optional lesion point (JA46 (d)).
   7. Protocol text (`docs/JANUSM-READ-PROTOCOL.md` §2, `labels.py` `CONVENTIONS`): trabeculae, LA appendage and
      pulmonary veins excluded beyond their ostia, aortic plane, RV extent, "myocardium above the annulus not
      labelled", the mitral gap.
   8. Export (`export.py`): reader, seeded or blank, seconds, attempts, flagged and reasons, offsets in the
      canonical sign, `border_protocol: 1`.
   9. Versioning: `border_protocol: 1` in every read record, apart from the wire `PROTOCOL_VERSION`. Replace §9's
      placeholder table.
6. **S6 — Reference-population builder and config (JA42, JA48; dev).** `tools/janusm/build_reference.py` writes
   `configs/janusm/reference-r1.json` per Hotel v3 §4.1 as amended (JA41 gates, JA42 RC), pinned in the guard.
   - Tests on synthetic populations (reproducing `calibrate_c` and S3 at fixed seeds); refusal of any seal,
     decision or JM-0 case; the Fir command printed for the lead.
   - It runs only after LQ12's seeds exist.
7. **S7 — The table writer (JA48; dev).** `janusm.report.build(...)` with `render_markdown` / `render_html`, per
   Hotel v3 §4.3 as amended: Lima's phrase table, no per-segment flags, the header fields, the footer sentence from
   S3.
8. **S8 — Half-maximum snap tool (conditional; dev).** Opened only if R4 fires (either |offset| > 0.5 mm, or
   |endo| > 0.25 mm with the TPR gate otherwise passing). It moves each border to its profile's half-maximum along
   the normal, with tests on `janusm_reads.phantom`.

---

## 8. What Round 4 on this path must settle

**This path is plan-complete pending the lead's Job JM-0 and JM-0R runs and the lead's answers (LQ2–LQ12,
LQ19–LQ22).** Every number the plan still needs comes from a pre-registered procedure applied to a measurement no
round can make without the lead. If LQ22 (a) is taken, Round 4 opens only when JM-0 / JM-0R aggregates are posted,
and then:

1. **Run `jm0r_decide.py` (S4) on the posted aggregates** and record each R0–R10 outcome as the plan's value. No
   threshold is re-argued.
2. **Explain Lima E5's 45 % against Hotel E7's 35 %** for the same nominal inputs, by running both F1
   implementations on one seed. JA40's procedure stands unless S3's test exposes an error in it.
3. **Check S1–S7 against JA37–JA48,** test by test, before the freeze PR.

After that, the decision-set reads (seal size, RC, κ / ICC, the vol–pp transfer check) and the reference population
are mechanical. They need no further round.

## Path summary for the lead (for #167)

- **Path A** delivers a reproducible rest-CCTA geometry table (17 segments × layers, and a roll-up per artery beside
  the reader's CAD-RADS grade).
- **Its flags** are specific by construction: calibrated on a reference population, above read noise, and only where
  the sign can see at least half-wall loss. Each page prints the thinning depth it cannot see (35 % provisionally).
- **Built or specified:** the guard, the seal freeze, the geometry module, the harness, JM-0R, the read queue, and
  now one decision script, one measurement set and one protocol v1.
- **Waiting on:** Job JM-0 / JM-0R and the reads.
- **Against `jm/paired-scar`:** path B adds a scar reference this path never has. Everything in path A is its
  Stage A, unchanged.

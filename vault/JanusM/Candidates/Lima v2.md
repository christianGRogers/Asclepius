---
tags: [janus-m, plans, candidate, round3, rest-ccta, myocardium, calibration, specification]
author: Lima
round: 3
version: 2
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#167
---

# Lima v2: settle what can be settled before JM-0, and make the rest a procedure that cannot drift

**Path:** `jm/rest-ccta` (LQ1 option A). **Base:** the path plan in force: [[Juliet v1]] + JA1–JA14 and [[Hotel v2]] +
JA15–JA24. Lima keeps it all except the three changes in §2, each with its evidence.

## 0. The plan in one paragraph

Round 2 fixed *what* path A delivers. Round 3 has to fix it **before Job JM-0 reports**, so that no number can steer
its own rule. Lima v2 does that for each §7 item it can settle:
- **Item 1: one procedure, as code.** `apply_r2_rules.py` applies every pre-registered JM-0 / JM-0R rule and prints
  each decision with its number. Its input list is the **JM-0R output schema that #169 must emit**, so the job and the
  rules cannot drift apart. It runs when the lead posts the outputs; a dry run on public labels shows it works.
- **Item 2: the harness's measurements, validated against exact truth** (E4):
  - thickness is exact to ±0.02 mm;
  - the voxel-surface ASSD (shared with the read queue) reads ≈ 0.04 mm high;
  - the Round 2 bias estimator fails JA16's ±0.05 mm. A volume ÷ smoothed-area estimator ⟨E4verdict⟩.
- **Item 3: E3 re-run under the rule JA18 actually adopted** (E5). At the measured `cv_n` (0.088) the page line is
  *"a territory thinned by 45 % or more, found with 80 % probability, at 0.5 mm error"*. E5 also shows **JA18's κ ≥ 0.6
  gate fails on a decision set with few infarcts, at any error level**. Lima proposes a prevalence-free gate in its
  place.
- **Item 4: the reference-population config and the table writer,** specified field by field, including F1's
  RC per territory, so that each can become a `role:swe` issue as written.
- **Item 5: protocol v1,** as a list of exact changes to `docs/JANUSM-READ-PROTOCOL.md` and `src/janusm_reads/`. It
  includes one ambiguity in JA21's anchoring rule that the builders need resolved.

**New evidence this round** (CPU; code in `experiments/JanusM/Lima/r3/`):
- **E4** [[Lima - Thickness and ASSD are right to 0.04 mm, but only a volume-over-area estimator can read signed bias to 0.05 mm]]
- **E5** [[Lima - Under JA18 thinning finds 45 percent wall loss at 0.5 mm error, but the kappa gate fails on a decision set with no infarcts]]

**Held-out cases: none opened** (§6). Every Round 3 script calls `janusm.guard.refuse(...)` before it opens a case
(JA22). The only cases opened are the 23 public TotalSegmentator cardiac subjects that both Lima's Round 2 guard and
the shared guard allow (checked again this round: 23 / 23 allowed; s0655 refused as a test).

## 1. What Lima keeps

The whole path plan: JA1–JA24 and Hotel v2, including:
- one error model and its units (JA15);
- final margins (JA16);
- the rest-TPR gate (JA17);
- rule C, F1, the fat-cut procedure and the composite (JA18);
- Tables A and B with the reader's CAD-RADS 2.0 grade (JA19);
- equal-thickness depth, fixed sectors and Euclidean territories (JA20);
- protocol v1 (JA21), the twin rule (JA22) and JM-0R (JA23).

## 2. What Lima changes (three proposals, each from this round's evidence)

| # | Change | Evidence |
|---|---|---|
| L9 | **The signed-bias estimator** for JA16's guard is ⟨E4est⟩, not Lima R2's inner-boundary mean. JA16's condition for the 0.3 mm guard is then ⟨E4verdict2⟩ | E4: on exact spheres and the 23 real walls |
| L10 | **JA18's κ ≥ 0.6 gate is replaced by a detectable-depth gate.** A sign shows as a flag only if its detectable depth, at the decision set's measured read error, is ≤ 50 %. κ and ICC are reported | E5: with no infarcts in the decision set, κ passes 1–5 % of the time even at 0.25 mm error, where the sign finds 95–98 % of 40 % thinning |
| L11 | **F1's RC uses the upper 95 % confidence bound of the read-difference SD** (χ² on n − 1 df), not the point estimate | 20 double reads give the SD to about ×0.76–1.46; specificity first (JA18) |

## 3. Round 2 §7, item by item

### Item 1 — the pre-registered decision procedure (runs when the lead posts JM-0 / JM-0R)

**The procedure is `experiments/JanusM/Lima/r3/apply_r2_rules.py`.** It reads one aggregate JSON and prints one line
per rule. Every rule was fixed in an earlier ruling, and none is re-tuned here:

| Rule | Source | Decision |
|---|---|---|
| AHA frame | JA3; Juliet v1, Lima v1 | > 10 % of cases fail the frame or the orientation checks → fix the frame before any table ships |
| Halves | JA2 | applied per segment by the module; the share is reported |
| Thickness definition | Hotel v2 §4.4 | median outside 4.2–8.0 mm (5.7–6.5 ± 1.5) → readers hand-measure 3 mid-ventricular segments on the first 20 decision cases, and the definition is aligned before the reference population is fitted |
| Seed half-maximum offset | JA17 cond. 2; JA21 read check | \|endo\| or \|epi\| > 0.5 mm → build the snap tool before reads; \|endo\| > 0.25 mm → rest TPR needs snapped borders |
| Rest TPR | JA17 | edge > 2 mm → not computed; edge ≤ 1.5 mm and \|endo\| ≤ 0.25 mm (or snapped) and free-wall guarded median 0.99–1.15 → shown as a patient-relative z; otherwise research export only |
| Fat cut | JA18 | the least strict (c, V), c ∈ {0, −30, −50, −100} HU then V ∈ {5, 20, 50} mm³, with ≤ 5 % of hearts carrying a cluster; none → fat is a number only |
| Septal-arc column | JA20 | kept if ≥ 10 % of mass changes segment, else dropped |
| Geodesic territories | JA20 | ≥ 10 % of segments change majority → Round 4 rules on it; else Euclidean, and geodesic is not built |
| Detectable depth | JA18; E5 | re-run `e5_ja18.detectable_depth` with JM-0R's `cv_n` and shape and the decision set's measured error; print its line |

- **The inputs are the JM-0R output schema** (`QUANTITIES` in the script, 15 named aggregates; §5 spec for #169).
- **With the JA23 fallback,** `--format lima_jm0b` maps Lima's committed `jm0b_readout.py` summary onto them. Two
  inputs, the endocardial 10–90 % edge width and the free-wall TPR, come only from Hotel's fallback script, so until
  then the TPR rule prints **NOT DECIDABLE**. No default is ever used for a missing number.
- **Dry run on public 1.5 mm labels** (`local_check_summary.json`; it decides nothing, because these labels are not
  CCTA):
  - frame accepted;
  - thickness definition **mismatch** (9.67 mm);
  - snap tool needed (endo −0.45, epi +0.64 mm);
  - TPR not decidable;
  - no fat candidate (96 % of hearts have clusters at 1.5 mm);
  - arc column kept (14 %);
  - Euclidean kept.

  The procedure runs end to end and fails safe.

### Item 2 — the JA15 harness as the geometry module's fixture, and JA16's ±0.05 mm

E4 (`r3/e4_estimators.py`) tests the three quantities against exact truth: spheres and shells whose perturbed border
is the exact sphere of radius R + d. It also tests them on the 23 real walls, shifted the JA15 way.

⟨E4table⟩

**Verdicts:**
- **Thickness** (`et_depth` median): exact to ±0.02 mm on analytic shells. Fit for the fixture.
- **ASSD** (`segtrain.metrics.surface_distances`, the same function as the read queue's
  `janusm_reads.anchoring.assd`): reads **≈ 0.04 mm high** at a true 0.5 mm shift (0.54) and at 0.3 mm (0.36). This is
  the voxel-centre surface definition. For JA8's d it cancels, because both terms carry it. For the absolute
  ASSD ≤ 1.0 mm guard it is conservative. The fixture records it as the expected value: 0.54 ± 0.01 for a 0.5 mm
  shift on a sphere of radius 12–20 mm at 0.5 mm.
- **Signed bias:** ⟨E4biasverdict⟩

### Item 3 — E3 re-run with the measured `cv_n` and shape (E5)

- **Inputs:** `cv_n` 0.088 and the 16-segment shape from the 23 public hearts. JM-0R replaces both by the item 1
  procedure.
- **Detectable depth, rule C + F1, 80 % of territories:** 35 % at 0.25 mm error, **45 % at 0.5 mm**, 65 % at 1.0 mm.
- **F1** halves the false flags (to 1–2 % of patients) and costs 4–16 points of sensitivity, most at 1.0 mm.
- **The composite's null rate is 0.14–2.8 % of patients** for correlations 0–0.9 among the three signs, against 9–14 %
  for "any single sign". The measured rate on the reference population is what the page states.
- **The κ gate (L10).** On a 40-patient decision set, P(κ ≥ 0.6) is:
  - with no infarcts: **0.05 / 0.01 / 0.00** at 0.25 / 0.5 / 1.0 mm error;
  - at 30 % prevalence: 1.00 / 0.88 / 0.09.

  κ needs true positives to agree on, and the decision set's prevalence is unknown and may be low (referrals for
  CCTA). ICC of the continuous territory deviation is more robust: at 0 % prevalence it passes 99 % of the time at
  0.25 mm and never at 0.5 mm. The detectable depth needs no prevalence at all, which is why L10 uses it.

### Item 4 — the table writer and the reference-population config (`role:swe` specifications)

**4a. `configs/janusm/reference-r1.json`.** Frozen by its own PR before any seal read, sha256-pinned in the table
writer, and never refitted on the seal (JA18).

| Field | Content | How it is computed |
|---|---|---|
| `version`, `created_from` | config version; git sha of `src/janusm/geometry.py`; the border model (`heartchambers_highres` version and label map, or Janus-M 1 run id) | — |
| `pins` | sha256 of `configs/janusm/sealed-r1.json`, `splits.json`, `ts-twins-r1.json` | — |
| `cases` | the 420 ImageCAS-X train ids = train − seal 60 − decision 40 − JM-0 40, **derived in code** from `sealed-r1.json`, and listed for audit | each passes `janusm.guard.refuse(..., purpose="any")`; frame failures are listed with their reason and excluded |
| `label` | `"this population, phase-uncertain"` | fixed text (JA18) |
| `thinning.shape[16]`, `thinning.scale[16]` | the median relative thickness per segment, and 1.4826 × the median of the right-half deviations | rule C (Lima E3) |
| `thinning.cut`, `thinning.k`, `thinning.null` | the z cut; its k; the null draw count (20 000) and seed | mirror null, ≤ 5 % of null patients with a territory flag on the **AHA-default** map |
| `hypoattenuation.*` | the same fields, on guarded subendocardial core HU ÷ the patient's median | the same procedure; guard = the JA17 band |
| `fat.c`, `fat.V`, `fat.grid` | the chosen cut and min volume; the share of hearts for every grid cell; the result for Hotel's noise-aware candidate | JA18 |
| `composite.rate` | the share of patients with thinning **and** (fat or hypoattenuation) in one territory; if > 0.05, `composite.rule = "two_contiguous"` | Hotel §4.3 |
| `rc[sign][territory]` | F1's RC per sign, for LAD, LCx and RCA | 4b below |
| `gate[sign]` | the detectable depth at the measured read error, the pass flag (≤ 50 %, L10), and κ and ICC (reported) | E5 `detectable_depth`, with σ from 4b |
| `page_line[sign]` | the printed detectable-depth sentence | E5 `page_line` |

**4b. F1's RC per territory, from the reads.**
1. **Cases:** the first 20 decision cases with two accepted reads (JA16's set). Never seal cases.
2. **For each case i, read r ∈ {A, B}, sign s and territory t** (LAD, LCx, RCA, on the case's **patient-specific**
   map from the ImageCAS-X reference tree, the map that is reported):
   D(i, r, t) = mean of the segment values in t − median of the segment values outside t.
   - For thinning, a segment value is its median thickness.
   - For hypoattenuation, it is its guarded subendocardial HU ÷ the patient's median.
   - For fat, it is the territory's core cluster volume, and "remote" is the patient's median per-territory volume.
3. **The difference:** Δ(i, t) = D(i, A, t) − D(i, B, t).
4. **SD:** SD_t = SD over i of Δ(i, t), with n_t ≥ 15 cases; otherwise the three territories are pooled.
5. **RC:** RC_t = 1.96 × SD_t × √((n − 1) / χ²₀.₀₂₅,ₙ₋₁) (L11: the upper 95 % bound of the SD; Bland & Altman 1986).
6. **The flag condition F1:** D(model, t) < −RC_t for thinning and hypoattenuation, and > +RC_t for fat.
7. **The read error for the gate:** σ_r = SD_t / √2, converted to a segment-level error as σ_r · √k_t, where k_t is
   the territory's segment count. That σ is the E5 input.

**4c. The table writer** (`src/janusm/table.py` or similar; a `role:swe` issue on this path).
- **Inputs:**
  - the case's four-label borders (model or read);
  - the CT;
  - the coronary four-class labels (the ImageCAS-X reference, or Janus 0 on a Janus-M-allowed case, JA4);
  - the reader form (per-vessel CAD-RADS 2.0 grade, optional lesion point);
  - `reference-r1.json` (sha-checked);
  - the geometry module version.
- **First call:** `janusm.guard.refuse([case], purpose=...)`. Seal cases are allowed only under `seal_scoring`.
- **Output:** one JSON (machine) and one page (human) with:
  - **Header** (Hotel v2 §3.2): phase or "phase unrecorded"; spacing; endocardial 10–90 % edge; both half-maximum
    offsets; AHA orientation pass and septal arc; territory source.
  - **Table A** (17 rows × layers, or halves per JA2): thickness and its population percentile; thinning flag;
    rest attenuation (normalised); hypoattenuation flag; core fat (mm³); rest TPR (only if `config.tpr_shown`,
    else blank with the reason); territory and share, "shared" if < 0.6, and the AHA default; pattern.
  - **Table B** (LAD, LCx, RCA):
    - the reader's grade, copied, or "not graded";
    - territory mass (g, % LV) with the AHA-default mass;
    - segments, with the shared ones listed apart;
    - flags by sign;
    - optional mass distal to a lesion point, labelled unvalidated (JA19);
    - one concordance phrase.
- **Phrase logic, pre-registered** ("significant" = CAD-RADS 3–5, i.e. ≥ 50 %; "not significant" = 0–2):

  | Territory state | Grade | Phrase (Hotel v2 §3.3, exact) |
  |---|---|---|
  | pattern present | significant | "Territory shows chronic-infarct-like geometry" |
  | pattern present | not significant, or not graded | "Geometric sign without graded stenosis" |
  | flags, no pattern | any | "Isolated measurements outside range" |
  | no flag | any | "No geometric sign in territory" |
- **Footer:** each sign's `page_line`, and "research output, not validated: no scar or perfusion reference" on every
  cell (JA19).
- **A flag is printed only if** (rule C cut) ∧ (F1) ∧ (`gate[sign].pass`). Otherwise the value prints as a number with
  its percentile.
- **Tests** (synthetic, no case data):
  - a 40 % thinned LAD territory on a phantom is flagged, with the right phrase for each grade;
  - a null phantom gets no flag;
  - a missing grade gives "not graded";
  - a changed config sha refuses to run;
  - a guard hit refuses before any file is read;
  - two runs give byte-identical JSON.

### Item 5 — protocol v1 in the read queue (JA21): the changes the builders need

Against `docs/JANUSM-READ-PROTOCOL.md` and `src/janusm_reads/` as merged:

| # | Where | Today | Protocol v1 (JA21) |
|---|---|---|---|
| 1 | §3 window | level at the border threshold, width ≈ 50 HU | **already plateau-centred**; keep, and drop the "[Round 2]" note |
| 2 | §4 `CheckConfig.tolerance_mm` | 1.0 mm, any failure returns the read | **0.5 mm on each whole-border median.** The read is returned **once** with the profile; a second failure is accepted and **flagged** (a new `accepted_flagged` marker on the read, not a new state). Octant checks stay at 1.0 mm (local errors) |
| 3 | §2 label 4 | "to the mitral annulus"; pulmonary veins [Round 2] | **LA appendage excluded beyond its ostium**; pulmonary veins cut at their ostia |
| 4 | §2 basal limits | flat plane through the hinge points [Round 2] | keep the flat plane through each valve's hinge points as the rule; class 1 stops at the mitral annulus plane; the septum below the aortic annulus is class 1 |
| 5 | `checker.check_conventions` | the four Round 1 conventions | **add:** labels 2 and 4 never touch; label 2 extends ≤ 3 mm above the fitted mitral plane (plane = least-squares fit to the 2–4 interface, or to the hinge points if it is absent) |
| 6 | §7 `anchoring.wave_report` | anchored if gap > mean seeded inter-read ASSD | **JA21:** anchored if the upper 95 % bound of (gap − mean seeded inter-read ASSD) > **0.2 mm**, per border. Gap = mean seed-vs-read ASSD on blank cases − the same on seeded cases. **Ambiguity:** JA21 says "paired", but blank cases are blank for both reads (§5.2), so no case has both a blank and a seeded read. The bound must be a two-sample bootstrap over cases. Lima recommends that reading, and the judge should confirm it |
| 7 | §7 | — | **add:** if > 50 % of a wave's reads change < 5 % of seed voxels, flag the wave. Then the blank re-read follows: 5 of the wave's seeded cases, drawn by salted hash, get a third read from blank by a reader who has not read them, scored by item 6's gap |
| 8 | §5.1 seed smoothing | σ = 1 mm [Round 2] | keep σ = 1 mm (no round proposed otherwise) |
| 9 | §4 fat shell | 1–4 mm [Round 2] | keep 1–4 mm |
| 10 | read form | — | **add** (JA19, LQ10 (a)): an optional per-vessel CAD-RADS 2.0 grade and lesion point, on seal and decision cases, stored with the read and never shown to the other reader |
| 11 | §9 | placeholder table | replace with "protocol v1, JA21", and a version string the client checks |

## 4. Carried assumptions (the rulings' recommendations)

| Question | Assumed |
|---|---|
| LQ2–LQ8 | the Round 1 recommendations: (a) for each |
| LQ9 | (a) a one-line note on the Round 1 record; no coronary seal change |
| LQ10 | (a) readers type a per-vessel CAD-RADS 2.0 grade in the Janus-M queue (item 5, change 10) |
| LQ11 | (a) JM-0R once, after JM-0; else the JA23 fallback |
| LQ12 | (a) seeds on the 420 reference cases become committed on this path (≈ 12 GPU-h) |

No new lead question.

## 5. Specifications for the engineering issues (not built here)

- **#169 JM-0R.** Its `summary.json` must carry the 15 `QUANTITIES` of `apply_r2_rules.py`, with those exact names and
  units, and aggregates only. Lima's `jm0b_readout.py` already computes 12 of them (`--format lima_jm0b`). The three
  others are:
  - the endocardial 10–90 % edge (Hotel);
  - free-wall guarded TPR with the JA17 adaptive band;
  - the share of guarded segments below 0.99.

  The procedure's dry run is the acceptance test: it must print no NOT DECIDABLE on JM-0R's output.
- **#170 JA15 fixture.** The analytic-sphere cases of E4 become its tests, with tolerances measured here:
  - thickness change within ±0.03 mm of −d;
  - voxel ASSD 0.54 ± 0.02 mm for |d| = 0.5;
  - the signed-bias estimator within ±0.05 mm of d for |d| = 0.5, both directions, both borders.

  ⟨E4fixture⟩
- **#168 JA22.** No Lima specification. Lima's guard and the shared guard refuse the same 708 subjects (Round 2).

## 6. Held-out disclosure

- **Cases opened this round:** the 23 public TotalSegmentator v1 cardiac subjects fetched in Round 2 (CC BY 4.0,
  scratch folder, never committed). `janusm.guard.refuse` was called on the list and on each case before any file was
  read. All 23 are allowed by the shared guard.
- **Everything else is simulation.** No ImageCAS case was opened, and no seal or decision draw was listed.
- **No committed file names a held-out id.**

## 7. Risks

- **JM-0R has not reported.** Items 1 and 3 are procedures with dry runs, not results.
- **`cv_n` and the shape come from 1.5 mm model-made labels.** The page line will move when JM-0R reports.
- **L10 changes an adopted gate.** If the judge keeps κ, the decision set's infarct prevalence decides whether any
  sign can show as a flag.
- **The anchoring ambiguity** (item 5, change 6) must be resolved before the first wave closes.

## 8. References

Resolved at Crossref this round, or carried from the verified Round 1–2 lists. JA14 and JA24 apply.
- Bland JM, Altman DG. Statistical methods for assessing agreement between two methods of clinical measurement.
  *Lancet* 1986;327:307–310. doi:10.1016/S0140-6736(86)90837-8.
- Shrout PE, Fleiss JL. Intraclass correlations: uses in assessing rater reliability. *Psychol Bull*
  1979;86:420–428. doi:10.1037/0033-2909.86.2.420.
- Lorensen WE, Cline HE. Marching cubes: a high resolution 3D surface construction algorithm. *ACM SIGGRAPH Comput
  Graph* 1987;21:163–169. doi:10.1145/37402.37422.
- Cury RC, et al. CAD-RADS 2.0 – 2022. *J Cardiovasc Comput Tomogr* 2022;16:536–557. doi:10.1016/j.jcct.2022.07.002.
- Chen J, et al. *Clin Imaging* 2025;118:110390. doi:10.1016/j.clinimag.2024.110390 (5.7 / 6.5 mm).
- Shah DJ, et al. *JAMA* 2013;309:909–918. doi:10.1001/jama.2013.1381.
- Wasserthal J, et al. TotalSegmentator. *Radiol Artif Intell* 2023;5:e230024. doi:10.1148/ryai.230024; v1 dataset
  Zenodo 6802614 (CC BY 4.0).

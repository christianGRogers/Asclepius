---
aliases: [Janus-M Round 2 rest-ccta]
tags: [janus-m, plans, judgement, round2, path-rest-ccta, myocardium]
author: Janus-M Round 2 judge (path jm/rest-ccta)
round: 2
path: jm/rest-ccta
status: ruling
updated: 2026-10-30
issue: christianGRogers/Asclepius#142
---

# Janus-M Round 2, path `jm/rest-ccta`: the judgement

**Ruling in one paragraph.** Path A (rest CCTA only) keeps the Round 1 structure: four learned borders, computed
layers, Janus-M 0 = `heartchambers_highres` + geometry, and Janus-M 1 only if Janus-M 0 fails. Round 2 adds what
the path must deliver and how it is held to measurement.
- **Base: [[Hotel v2]].** It gives the clearest account of what the table may and may not say beside an artery,
  and a fixed border protocol.
- **Amended by JA15–JA24**, which take:
  - from [[India v2]]: the error model, the seal re-powering code (E8), the adaptive rest-TPR guard band (E7) and the
    reliability gate;
  - from [[Lima v1]]: the per-territory, patient-relative thinning rule (E3), the reader's CAD-RADS column, the
    tighter bias guard and the fat-cut procedure.
- **The JA8 margins are now final, before any read.** The border margin stays at 0.25 mm. The signed-bias guard
  tightens to 0.3 mm, but only once the bias estimator is validated (JA16).
- **The three Fir CPU add-ons become one guarded CPU job, JM-0R** (JA23).
- **No fork.** Every open question changes a parameter or one column, not the path's structure (§6).

Rules kept: the judge ran no experiment, opened no image, downloaded no data, and read no held-out case. The checks
below read committed JSON summaries, committed code and configs, issue #142, and public bibliographic records only.
Twin and seal lists were compared by count only.

---

## 1. What was checked, for all three

### 1.1 Key numbers against committed JSON: all match

| Advocate | Claim | File | Match |
|---|---|---|---|
| Hotel | collapse fit Dice ≈ 0.998 − 0.379·mean\|d\|, R² 0.95; residuals Golf +0.009, India −0.008, Kilo −0.001, Hotel +0.006 | `Hotel/r2/summary.json` (E2_collapse) | yes (R² 0.948) |
| Hotel | harness σ 0.5: mean\|d\| 0.247, subendo Dice 0.909, thickness error 0.451; RC 0.74 / 1.60 mm | same (E2_B, E4_floor) | yes |
| Hotel | E3: 1.2 mm edge, 1 mm guard, 0.5 mm voxels reads 1.09 / 1.01 / 0.88; 6 mm wall, endocardium 0.5 mm into blood reads 1.20 | same (E3_tpr) | yes |
| Lima | fit 1.001 − 0.314·ASSD, residual SD 0.018 vs total 0.071 | `Lima/e2_summary.json` | yes |
| Lima | realised/nominal at σ 0.5: Golf 0.70, India 0.47, Kilo 0.45, Hotel 0.13 | same (table) | yes |
| India | U at σ 0.5: ASSD 0.36/0.36, subendo 0.896, STA 0.94, thickness 0.32 | `India/results/summary_r2.json` (E5) | yes |
| India | E7 with R 1.00 and a 1 mm guard, 0.6 mm PSF: 21–24 % of segments read < 0.99 | same (E7: 0.21–0.26) | yes |

### 1.2 The PM's points, verified

**(1) "All three find that the four Round 1 simulations collapse onto one curve when error is measured as realised
ASSD."** **True in substance.** Each advocate rebuilt the four error models in its own harness and found that the
disagreement lies in the x-axis, not in how layers degrade. The mechanism is the same in all three: a plain
signed-distance map has a dead zone near the border, so a "0.5 mm" field moves the border by much less. All three
also find Hotel's Round 1 model the softest (0.03–0.08 mm realised at nominal 0.5).

Two qualifications matter for later rounds:
- **Hotel's x-axis is not JA8's ASSD.** Hotel uses mean |d| (changed volume ÷ border area); Lima and India use
  symmetric surface ASSD, which is what JA8 decides on. On the same Golf-convention walls, Hotel's 0.287 mm sits
  against Lima's 0.33–0.36 mm. On the harness at σ 0.5, Hotel's 0.247 against Lima's 0.34 mm. **Hotel's units run
  about 1.2–1.4× smaller.** The slopes (0.38 vs 0.31 per mm) differ for the same reason. So Hotel's argument that "an
  achieved 0.25 mm already costs 0.45 mm of thickness" is in different units from JA8's 0.25 mm.
- **Hotel's thickness error is a mean over segments**, Lima's and India's a median (as JA8 defines it). That
  explains most of the remaining gap: at matched realised ASSD of about 0.35 mm, thickness error is 0.32 mm (India),
  0.32–0.35 mm (Lima) and about 0.45 mm (Hotel). JA15 fixes one unit and one summary.

**(2) "Hotel §5.5 and Lima propose fixing the JA8 margin at 0.25 mm now; India codes margins and re-powering
(E8)."** **True.**
- Hotel fixes δ = 0.25 mm and adds a thickness condition (≤ RC/2).
- Lima fixes 0.25 / 0.5 mm as final and tightens the bias guard to 0.3 mm.
- India's E8 keeps 0.25 mm *unless* the median read-vs-read ASSD exceeds 0.5 mm. It then loosens the margin to half
  that, capped at 0.40 mm.

Ruling in JA16: fix the margin now, without India's loosening clause.

**(3) "Rest TPR: Hotel (E3) and India (E7) both find it feasible only with an endocardial guard band; do their
conditions agree?"** **They agree on the mechanism, but not on the rule.**
- **Agreement.** A 1 mm guard removes the blood-pool spill while the endocardial edge is sharp, and fails as the edge
  widens.
  - Hotel: within 0.01 of truth up to a 1.2 mm 10–90 % edge; +0.04 at 1.6 mm; a true defect reads normal at
    2.4 mm.
  - India: −0.01 at a 0.6 mm FWHM point spread (≈ 0.65 mm 10–90 %), and at 1.5 mm FWHM (≈ 1.6 mm 10–90 %) +0.07
    under a 0.5 mm inward endocardial bias.

  Both say that native resolution can work and that 1.5 mm resampled CT cannot.
- **Disagreement on endocardial bias.** At a 1.2 mm edge with the 1 mm guard, Hotel's 1-D model gives +0.05 to +0.11
  for an endocardium 0.5 mm into the blood. India's 3-D phantom gives −0.01 at 0.6 mm FWHM and +0.07 at 1.5 mm.
  The two are consistent if read along edge width: the bias only matters once the edge is not sharp. So Hotel's
  offset condition is needed, but only as a guard, and India's adaptive band (guard = max(1 mm, FWHM)) also answers
  it.
- **Disagreement on the acceptance window.**
  - Hotel: median guarded free-wall TPR 1.06–1.12.
  - India: 0.95–1.15, with < 10 % of segments below 0.99.
  - Lima: 0.99–1.20, with ≥ 70 % of guarded segments in 0.99–1.25.

  Hotel's window is too narrow: its own guarded read of a true 1.10 is 1.08–1.09, and Forte 2020 gives the septum
  (the lowest wall) 1.06 ± 0.06. India's "< 10 % below 0.99" fails on its own flat-wall phantom, where 21–24 % read
  below 0.99 from noise alone. **JA17 merges the three.**

**(4) "Twin counts differ (692 / 699 / 707), but all refuse the same 708 ids."** **Mostly true; the counts in the
brief need correcting.**
- **Reported counts.** Lima 692 and India 692 are twins *excluding* the held-out 16. Hotel reports **695**, not 699.
  The shared guard's `configs/janusm/ts-twins-r1.json` lists 707, because it counts 15 held-out subjects as twins of
  other held-out subjects (PM, #142).
- **The refused sets, checked by count:** Lima's refused set (twins ∪ held-out) = India's `refused` list = the
  shared config's keys ∪ held-out = **the same 708 ids**.
- **Hotel's rule is wider by construction.** `guard_r2.twins()` also lets a *blank institute* match anything (v2.0.1
  has five blank institutes); Lima, India and the shared builder let only a blank sex or age match. That accounts for
  Hotel's 659 vs 656 in v2.0.1, so Hotel refuses about 711. Hotel commits no twin id list, so this is inferred from
  its code and counts, not compared id by id.
- **All three leave the same 23 cardiac studies,** and Hotel's 23 are disjoint from the shared refused set.
- **Ruling (JA22):** the strict rule stays, widened to Hotel's blank-institute match.

**(5) The asks for the lead.** They are confirmed and handled in §5:
- the three Fir CPU add-ons: Hotel `halfmax_tpr_m0.py`, Lima `jm0b_readout.py`, India `jm0_addon.py`;
- the reader-supplied stenosis grade (Lima, India; Hotel names it LQ-H1);
- the Round 1 twin disclosures (LQ9 on #130).

### 1.3 Two errors the PM did not flag

- **Lima's case for the 0.3 mm bias guard uses a nominal shift, which breaks its own rule L1.** Its "uniform
  0.5 mm" shift realised an endocardial ASSD of 0.54–0.62 mm and an epicardial 0.63 mm (`e2_summary.json`), so its
  0.63–0.64 mm thickness error is about 1 mm of thickness per mm of realised shift. India (0.42–0.49 mm for about
  0.5 mm realised) and Hotel (0.48–0.49 mm) give the same ratio. The conclusion survives the correction (JA16): a
  0.5 mm bias costs about 0.5 mm of thickness, which is the whole thinning budget in Lima E3.
- **India's signed-bias estimator under-reads outward shifts** (+0.34 to +0.37 mm for a 0.5 mm shift; India says
  so). A 0.3 mm guard measured that way would pass a true ≈ 0.45 mm bias. JA16 makes the tighter guard conditional on
  a validated estimator.

### 1.4 Held-out disclosures, checked

- **No Round 2 candidate opened a held-out subject.**
  - Hotel read only the two `meta.csv` tables.
  - Lima fetched only the 23 allowed cardiac subjects, after its guard.
  - India fetched masks of 299 allowed subjects (CT only for the 23 cardiac ones; one CT, s0032, for a smoke test).
- **Every advocate read the held-out subjects' `meta.csv` rows,** which the twin rule cannot avoid. These are public
  metadata, not images.
- **Round 1 used twins.** Hotel E1 shows that Golf (20 of 24), Hotel (20 of 26), India (49 of 64), Juliet (9 of 12)
  and Kilo (31 of 40) used subjects the rule now refuses. Seven v1 subjects match a held-out subject exactly on age,
  sex, institute and study type; Hotel opened two of them (s0767, s0848). That number of exact matches is chance level
  (mean 4.81, P(≥ 7) = 0.24; `e1_chance.json`).
  - **India's Round 1 check is wrong.** It reported that no other v1 subject matches a held-out subject on all four;
    seven do.
  - None of these files contains a held-out s-number (Hotel's table, re-checked).
  - Handled under LQ9 (§5).

### 1.5 Citations (12 resolved at Crossref; abstracts read at PubMed)

All exist, and the bibliographic details match: Cury 2022 (*JCCT* 16:536–557), Kurata 2015, Ide 2017, Yezzi–Prince
2003, Ortiz-Pérez 2008, George 2009, Nieman 2006, Bland–Altman 1986, Forte 2020 (online 2019; *Clin Physiol Funct
Imaging* 40:30–36), Shah 2013, Chen 2025.

Numbers checked against the abstracts:
- **Kurata 2015:** CTA Voronoi area at risk vs SPECT, r 0.531 / 0.494 / **0.814**, in 34 patients. ✓
- **Ide 2017:** 15 swine hearts, r **0.92 / 0.96 / 0.96**. ✓
- **Ortiz-Pérez 2008:** **23 %** of hyperenhanced segments discordant with the assigned artery. ✓ The population is
  93 acute-MI patients after primary PCI, which no advocate states (context, as for Mushtaq in Round 1).
- **Nieman 2006:** chronic MI −13 ± 37 HU vs controls 73 ± 14 HU; thinning with long-standing MI. ✓
- **Shah 2013:** 201/1055 (19 %); 72 % scar extent; 18 % limited scar; 4.4 → 7.5 mm. ✓
- **Forte 2020:** septal TPR **1.06 ± 0.06**. ✓ The abstract also says the septum is the *lowest* territory, so
  free-wall normals are higher. That matters for JA17.

**Not verifiable from the abstract:** George 2009's 1.12 ± 0.13 and its < 0.99 cut (Hotel and India mark them as full
text). They are used here only as anchors, never as cuts.

**One context error (Lima).** Lima calls geodesic assignment "the method validated against histology and SPECT
(Ide 2017; Kurata 2015)", and calls mass distal to a lesion point "the quantity Voronoi CT methods validate". Both
abstracts describe **Voronoi (nearest-vessel) segmentation of whole territories**: India ink into one artery in Ide,
all stenosis-related territories in Kurata. That is JA4's Euclidean rule, at territory level. Neither paper validates
geodesic assignment or mass distal to a point. JA24 records this.

---

## 2. Scorecards

Scale 1–5, as in Round 1:
- **(a)** reasoning;
- **(b)** evidence;
- **(c)** fit to path A and to data the project can get;
- **(d)** risk and cost (5 = low risk, cheap).

### Hotel v2: a geometry table beside the artery, every threshold above its own noise floor

| | Score | Why |
|---|---|---|
| (a) Reasoning | **5** | The best statement of path A's limits: specificity can be calibrated, sensitivity cannot, and the page says which. F1 (read noise) + F2 (population) is the right structure. The multiplicity argument (16 segments × 3 signs ≈ 70 % of patients flagged by chance) is correct and drives the composite. The fixed Table B phrases say what a reader may and may not take. The protocol thresholds are fixed now. Withdraws its own Round 1 bars openly |
| (b) Evidence | **4** | Numbers match; E1 is the most careful twin analysis (blank-institute match, chance null, Round 1 audit). Deducted: the E2 x-axis is not JA8's ASSD, and its thickness error is a mean, so §5.5's margin argument is in the wrong units (§1.2); E3 is 1-D; all phantoms |
| (c) Fit | **4** | Joins on the artery and copies the reader's grade: correct, since Janus grades no stenosis. F2 by absolute per-segment percentile is the weaker rule on phase-uncertain ImageCAS (Lima E3: rule B finds 48 % of 30 % thinning where rule C finds 98 %) |
| (d) Risk / cost | **4** | CPU add-on ≈ 1 h; F2 needs the seeds on the remaining training cases (≈ 12 GPU-h, already conditional in JA10). The hand-measured thickness check (§4.4) adds reader time only if JM-0 fails it |

### Lima v1: measure in millimetres, flag territories, borrow no threshold

| | Score | Why |
|---|---|---|
| (a) Reasoning | **4** | Patient-relative, per-territory thinning cancels the unrecorded phase, the decisive problem on ImageCAS. The null comes from the half of the distribution that thinning cannot reach: no label needed, and well argued. The territory, mass-at-risk and CAD-RADS framing is clinically clear. Deducted: L2's evidence breaks its own L1 (§1.3); its rest-TPR fallback drops the sign even per territory |
| (b) Evidence | **4** | E3 is the round's most useful new experiment: 144 conditions, three failed versions disclosed. E2 numbers match; there is a self-test on the 23 allowed cases. Deducted: the Kurata / Ide misreading (§1.5) |
| (c) Fit | **4** | Reader CAD-RADS per vessel is realistic. "Mass distal to a lesion point" rests on an unvalidated quantity |
| (d) Risk / cost | **4** | JM-0b is CPU, ≈ 1 h, and well guarded (recomputes the Janus-M draws, checks the `splits.json` hash). It adds reader work for the grade |

### India v2: measured where it can be, pre-registered where it cannot

| | Score | Why |
|---|---|---|
| (a) Reasoning | **4** | The dead-zone explanation is the clearest of the three. Guard = max(1 mm, FWHM) turns E7 into a rule that scales with the image. κ ≥ 0.6 between reads turns the planned reads into a reliability test of every sign. Deducted: E8 loosens the margin when the reads are noisy, the wrong way round for a bar (and d already absorbs read noise); the TPR gate's "< 10 % below 0.99" fails its own flat-wall phantom; the normative reference "without stenosis ≥ 50 %" depends on grades that do not exist on training cases |
| (b) Evidence | **5** | Re-implements all four Round 1 models on 37 real wall shapes and reproduces every Round 1 value to within 0.012. E6 on 25 cases; a 3-D TPR phantom; E8 as code with its limit stated; twin variants counted; its own estimator bias disclosed. Its Round 1 exact-match claim is wrong, but that is a Round 1 item |
| (c) Fit | **4** | Same deliverable as Hotel, less specified (no fixed phrases, no multiplicity control beyond Bonferroni) |
| (d) Risk / cost | **4** | CPU add-on on the login node. The normative reference (≈ 10 GPU-h) overlaps JA10's conditional seeds |

**Totals (of 20):** Hotel 17, India 17, Lima 16.

**Hotel is the base, on the tie-break.** Round 1 §6 item 9 (what the table gives a reader, and how its signs are
calibrated) is the item only this path must settle, and Hotel's answer is the most complete and conservative.
India's stronger evidence enters as the error model and the measurement rules (JA15–JA17). Lima's E3 replaces
Hotel's F2 as the thinning rule (JA18).

---

## 3. Rulings where they disagree

| Item | Hotel | Lima | India | **Ruling** |
|---|---|---|---|---|
| Error model and units | phantom harness, mean \|d\| | `lima_c8`, realised ASSD | U, realised ASSD | **One model (Golf's corrected SDF, 8 mm, independent per border; U = `lima_c8`), symmetric ASSD, median-over-segments thickness** (JA15) |
| ASSD margin on d | 0.25, fixed now | 0.25, final | 0.25 unless reads are noisy (≤ 0.40) | **0.25 mm, final; no loosening** (JA16) |
| Thickness margin | + 0.5 and ≤ RC/2 | + 0.5, final | + 0.5 unless noisy (≤ 0.8) | **read-vs-read + 0.5 mm, final; RC/2 reported only** (JA16) |
| Signed-bias guard | 0.5 | 0.3 | 0.5 | **0.3 mm with a validated estimator, else 0.5** (JA16) |
| Seal sizing | formula, true d = 0, 80 % power | formula, true d = δ/2, 95 % | bootstrap of Janus-M 0's own 20 d values (E8) | **E8 as code, margin fixed** (JA16) |
| Rest TPR gate | edge ≤ 1.5, \|endo offset\| ≤ 0.25, median 1.06–1.12 | median 0.99–1.20, ≥ 70 % in 0.99–1.25; else drop | median 0.95–1.15, < 10 % below 0.99; guard max(1, FWHM) | **merged** (JA17) |
| Thinning flag | per segment, F1 + F2, composite pattern | per territory, patient-relative, ≤ 5 % null patients | per segment, p2.5, ≤ 10 % per patient, κ ≥ 0.6 | **Lima's territory rule + Hotel's F1 floor + India's κ gate; ≤ 5 % per patient** (JA18) |
| Fat cut | patient noise-aware, ≥ 3 voxels | (c, V) grid, ≤ 5 % hearts | pooled 0.1th percentile, ≥ 10 mm³ | **Lima's grid procedure, with Hotel's patient rule as a candidate** (JA18) |
| Depth | equal thickness; Laplace isolines dropped | equal thickness; Yezzi–Prince reported | equal thickness; Yezzi–Prince not adopted | **equal thickness only; Yezzi–Prince not built; Laplace isolines never reported as thirds** (JA20) |
| Sectors | fixed | fixed; arc primary if it lowers discordance ≥ 5 pp | fixed; septal arc as a sensitivity column | **fixed; septal-arc column kept unless < 10 % of mass changes on JM-0R** (JA20) |
| Territories | Euclidean + "shared" < 0.6 | geodesic primary if > 10 % differ | lead picks if ≥ 5 % voxels differ | **Euclidean primary; "shared" kept; geodesic measured; Round 3 rules if ≥ 10 % of segments differ** (JA20) |
| Twin rule | keep; blank institute matches | keep | keep | **keep, with blank-institute match** (JA22) |
| Fir add-on | `halfmax_tpr_m0.py` | `jm0b_readout.py` | `jm0_addon.py` | **one job, JM-0R** (JA23) |

**The base question settled on this path.** Round 1 §6 item 9: the table, read beside the reader's per-artery grade,
reports how much myocardium lies behind each artery and whether that territory shows rest geometry or attenuation
signs that are reproducible between reads and rare in the population. It never states sensitivity, and it never
calls scar.

---

## 4. Binding amendments (JA15–JA24; path `jm/rest-ccta`)

- **JA15 — One error model, one unit.**
  - **The model.** Every Janus-M simulation uses a single error model:
    - Golf's half-voxel-corrected signed distance on the native 0.5 mm grid;
    - independent smooth Gaussian fields per border, 8 mm correlation (4 and 16 mm as sensitivity);
    - constant biases.

    This is India's U and Lima's `lima_c8`, which are the same model.
  - **The units, as JA8 decides them:**
    - results are indexed by **realised symmetric surface ASSD** and signed bias per border, never by nominal σ;
    - segment-thickness error is the **median over segments 1–16**;
    - Hotel's mean |d| may be reported beside them, never in their place.
  - **STA** is computed in the same harness and stays reported (JA8). India E5 shows it does not see a 0.5 mm bias.
  - **Shipping.** It becomes the test fixture of the JA2–JA4 geometry module (#139): one ASSD, one signed bias and
    one thickness implementation, shared by the harness, the read checks and the scorer. It is a `role:swe` issue on
    this path.
- **JA16 — JA8 margins, final before any read.**
  - **Margins:** per border, the upper 95 % patient-bootstrap bound of d is ≤ **0.25 mm**; the median segment-thickness
    error is ≤ read-vs-read + **0.5 mm**. Both are **final**, and the first 20 decision double reads set only the
    seal size.
    - India's loosening clause is rejected: d already subtracts the read-vs-read term, so noisier reads make d smaller
      for the same model error, not larger.
    - Hotel's "thickness error ≤ RC/2" is reported, not a gate.
  - **Signed-bias guard: |bias| ≤ 0.3 mm**, under one condition. Before the freeze, the estimator must recover a
    known 0.5 mm shift, in each direction, to within ±0.05 mm in the JA15 harness. Until then, and if it cannot, the
    guard stays at 0.5 mm.
    - Why 0.3: all three harnesses give about 1 mm of thickness error per mm of realised bias (§1.3), and Lima E3
      needs ≤ 0.5 mm thickness error to find 40 % thinning.
  - **ASSD guard ≤ 1.0 mm** stays.
  - **Seal size:** India's `e8_repower.py`, with the margin fixed at 0.25 mm. The size is the smallest of 60 / 80 /
    100 / 120 that passes with probability ≥ 0.80 on both borders. It runs once on Janus-M 0's d from the first 20
    decision double reads.
    - **If 120 does not suffice,** Janus-M 1 is triggered before any seal read (India §9), and the freeze PR records
      the detectable margin (Hotel, Lima).
    - The seal never shrinks and is scored once (JA6).
- **JA17 — Rest TPR.**
  - **Guard band:** max(1 mm, the case's measured endocardial edge FWHM), where FWHM ≈ the 10–90 % width ÷ 1.09 for a
    Gaussian edge (India E7, Hotel E3).
  - **Per-segment rest TPR enters the table only if JM-0R shows all three:**
    1. the median endocardial 10–90 % edge is ≤ 1.5 mm;
    2. the median endocardial half-maximum offset is within ±0.25 mm, or the borders are snapped to half-maximum
       first (a `role:swe` tool);
    3. the median guarded free-wall TPR is in **0.99–1.15**.

    The share of segments below 0.99 is reported, never a gate: noise alone puts 21–24 % of a flat wall there (India
    E7).
  - **If any condition fails,** rest TPR is not shown in the table and stays in the research export only. If the
    edge is > 2 mm, it is not computed.
  - **When shown,** it is a patient-relative z-score calibrated by JA18, never George's 0.99 stress cut.
- **JA18 — Path A signs: specificity calibrated, sensitivity never stated.**
  - **Thinning:** Lima's rule C.
    - Each segment gets a patient-relative, shape-corrected score, with scales from the right half of the population.
    - A **territory** is flagged when ≥ 2 contiguous segments fall below the cut.
    - The cut is set so that **≤ 5 % of null patients** carry any flag.
    - It is calibrated on the AHA-default map and reported on the patient-specific map.
  - **Two further conditions for a flag to show:**
    - **(F1, Hotel)** the territory's deviation from the patient's remote median exceeds the repeatability coefficient
      (RC) of the territory mean. RC is computed from the first 20 decision double reads.
    - **(κ, India and Lima)** read-to-read agreement on the decision set is κ ≥ 0.6. Otherwise the sign is shown as a
      number only.
  - **The same procedure applies to subendocardial hypoattenuation** (guarded core HU relative to the patient) **and
    to fat.**
  - **The fat cut:**
    - the least strict (c, V) from Lima's grid (c ∈ {0, −30, −50, −100} HU, inside the −180..0 HU window;
      V ∈ {5, 20, 50} mm³), with Hotel's patient noise-aware cut as one more candidate, for which ≤ 5 % of null
      hearts carry a cluster;
    - core sample ≥ the JA17 guard from both borders;
    - set provisionally on JM-0R, then fixed once on the reference population before any seal read.
  - **Per-segment values** are shown as numbers with their population percentile, never as flags ("isolated
    measurements outside range", Hotel §3.3).
  - **Composite.** Hotel's composite ("chronic-infarct-like geometry": a thinning flag plus a subendocardial fat or
    hypoattenuation flag in the same territory) is reported per territory, with its measured population rate.
  - **Never borrowed as a cut:** 5.5 mm, −10 HU or 0.99.
  - **Reference population:**
    - the ImageCAS-X training cases left after the seal, the decision set and JM-0 (420);
    - on Janus-M 0's (or, if triggered, Janus-M 1's) borders;
    - labelled "this population, phase-uncertain", never "normal";
    - frozen in a pinned config before any seal read.

    India's stenosis-filtered reference is deferred until training cases carry grades.
  - **Construct checks, reported and never tuned on:** contiguity, endocardial predominance, co-location, and
    stenosis concordance (Hotel §4.5, Lima, India). Failing one demotes the sign to "number only".
  - **Lima's detectable-depth simulation** is re-run with the `cv_n` and segment shape measured by JM-0R, and the
    result is printed on the page instead of a sensitivity.
- **JA19 — The deliverable (Hotel §3, amended).**
  - **Table A** (segment × layer) and **Table B** (per Janus artery), with Hotel's header, columns and four fixed
    concordance phrases.
  - **Table B adds:**
    - the **reader's CAD-RADS 2.0 grade of the worst lesion** (Cury 2022), typed in, never computed (Janus grades no
      stenosis);
    - patient-specific territory mass with the AHA-default mass beside it;
    - "shared" segments (majority share < 0.6).
  - **Mass distal to a reader-marked lesion point** (Lima) is an optional research column. It is labelled
    unvalidated, because Kurata and Ide validate whole-territory Voronoi mass, not mass distal to a point.
  - **Every cell:** "research output, not validated: no scar or perfusion reference".
  - **Shipping.** The table writer is a `role:swe` issue on this path (Lima §9 item 2).
- **JA20 — Depth, sectors, territories.**
  - **Depth.** Equal-thickness depth stays (JA2): three independent tests give 97–98.5 % agreement with Yezzi–Prince.
    Yezzi–Prince is not built into the module. Raw Laplace isolines are never reported as thirds. JM-0R reports
    equal-thickness vs Laplace agreement once on native CCTA.
  - **Sectors.** Fixed 60° / 90° sectors stay primary (JA3). The two septal segments of each ring also carry the
    arc-proportional value as a sensitivity column (India). It is dropped if JM-0R shows < 10 % of mass changing
    segment.
  - **Territories.** Euclidean nearest-vessel stays primary (JA4); it is also the Voronoi rule that Kurata and Ide
    validate. "Shared" marks segments with share < 0.6. JM-0R measures geodesic-vs-Euclidean disagreement on the
    reference trees; if ≥ 10 % of segments change majority, Round 3 rules on it.
- **JA21 — Border protocol, version 1** (for the read queue already built in #155 / #161).
  - **The text:** Hotel §5.4 items 1–7, with these settled:
    - **Window.** Plateau-centred by default (Hotel), not a fixed 800/200 window (Lima): the myocardium-to-fat
      contrast is narrow.
    - **Half-maximum check.** Median offset ≤ 0.5 mm per border is accepted. Above that, the read goes back once with
      the profile; a second failure is accepted and flagged (India, Hotel).
    - **LA appendage.** Excluded beyond its ostium (Hotel, India; Lima included it). The mitral plane needs only the
      LA body.
    - **Code check.** Labels 2 and 4 never touch, and label 2 extends ≤ 3 mm above the fitted mitral plane (India).
      So do Lima's connectivity and overlap checks.
  - **Anchoring.** Seeded reads cannot accept a model if:
    - blank-vs-seeded ASSD exceeds seeded inter-read ASSD by > **0.2 mm** (upper 95 % paired bound; Hotel). Lima's
      0.1 mm would almost always fire on 10 blank cases;
    - or more than half of a wave's reads change < **5 %** of seed voxels (Lima). That wave is flagged, and the
      blank re-read follows (India).
- **JA22 — Twin rule.**
  - **The rule stays as Round 1 wrote it,** with one widening: a **blank institute** also matches (Hotel). This adds
    about 3 v2.0.1 subjects and no cardiac study.
  - **Shipping.** `tools/janusm/build_ts_twins.py` is updated and `configs/janusm/ts-twins-r1.json` is re-pinned (a
    `role:swe` PR on `dev`, since the guard is trunk). Until then the guard refuses the current 708.
  - **The counts, recorded:** 692 twins excluding the held-out 16; 707 in the guard's file, counting held-out
    subjects twinned to each other; **708 refused**.
  - **Round 1 public case lists** (Golf, Hotel, India, Juliet, Kilo) are never reused without the guard.
- **JA23 — Fir: one CPU job, JM-0R, replaces the three add-ons.**
  - **What it is:** one script on this path, `experiments/JanusM/fir/jm0r_readout.py` (a `role:swe` issue).
  - **Inputs:** Job JM-0's masks and CT, plus the ImageCAS-X reference coronary labels.
  - **Guard:**
    - it reads the JM-0 list from the frozen `configs/janusm/sealed-r1.json` (key `jm0`) and stops unless
      `m0_cases.txt` equals it;
    - it calls `janusm.guard.refuse(..., purpose=JM-0)` before opening any file;
    - it checks the `splits.json` hash (JA6).
  - **What it computes** (one implementation per quantity, from the geometry module where one exists):
    - **from Hotel:** half-maximum offsets, 10–90 % edge widths, plateaus, the pooled core-HU histogram, and TPR with
      guards of 0, 1 mm and the JA17 adaptive band;
    - **from Lima:** voxels per third and halves, AHA failures, thickness, `cv_n` and segment shape, arc sectors,
      Euclidean vs geodesic territories, and the fat (c, V) grid;
    - **from India:** equal-thickness vs Laplace agreement, the septal arc, and territory discordance with the AHA map.
  - **Output:** aggregates only (no case id, no image). Per-case rows stay on Fir.
  - **Cost:** one `sbatch`, 8 CPUs, ≤ 2 h, 0 GPU-h.
  - **Fallback if the lead runs before JM-0R ships:** the three committed scripts, in one job, in the order Lima,
    India, Hotel. All three are guarded and read-only. Round 3 then reconciles any quantity the scripts compute
    differently.
- **JA24 — Citations and record.** Round 1's JA14 stands. Added:
  - Kurata 2015 and Ide 2017 validate whole-territory Voronoi (nearest-vessel) mass, not geodesic assignment or mass
    distal to a point;
  - Ortiz-Pérez 2008 is acute MI after primary PCI;
  - Forte 2020's 1.06 is the septum, the lowest territory;
  - George 2009's 1.12 ± 0.13 and < 0.99 are full-text figures, unverified by the judge;
  - India v1's statement that no v1 subject exactly matches a held-out subject is wrong (seven do; Hotel E1).

---

## 5. Questions for the lead (each with a recommendation; none is a fork)

**Carried unchanged, as assumptions:** LQ2–LQ8 (Round 1 §5), each with its Round 1 recommendation. All three
candidates assumed the same.

### LQ9 — Round 1 twin disclosures (logged by the PM on #130)

- **The facts:** Round 1 experiments used public subjects that the twin rule now refuses; Hotel opened two exact
  matches (s0767 ↔ reserve s0846; s0848 ↔ sealed s1106). No coronary label was read and no coronary quantity was
  computed.
- **Options:**
  - (a) a one-line note on the Round 1 record, and no seal change;
  - (b) the same, and replace s0846 and s1106 in the coronary sets under D27.
- **Recommendation: (a).** Seven exact matches is chance level (P = 0.24), the harm is bounded exactly as Round 1
  §4 says, and LQ8 sets the precedent.

### LQ10 — Where Table B's stenosis column comes from

- **The facts:** Janus segments lumen (D25) and grades no stenosis; stenosis is out of the coronary plan's scope
  (icx4 Results).
- **Options:**
  - (a) readers type a per-vessel CAD-RADS 2.0 grade, with an optional lesion point, in the Janus-M read queue for
    seal and decision cases (about 1–2 min per case, an estimate);
  - (b) also put a stenosis grader on the coronary plan's road map (a coronary decision, not Janus-M's);
  - (c) no stenosis column: the table joins on the artery only.
- **Recommendation: (a) now.** (b) is a separate coronary-plan question. The table works under all three, which is
  why this is not a fork.

### LQ11 — One merged Fir CPU job (JA23)

- **Options:**
  - (a) run JM-0R, once, after Job JM-0, when its `role:swe` PR is merged;
  - (b) run the three committed add-ons now, in one job (the JA23 fallback);
  - (c) run none, and wait for reads.
- **Recommendation: (a)**, or (b) if JM-0 returns before JM-0R ships. Either is CPU only, with 0 GPU-h and
  aggregates returned on #142. (c) leaves every pre-registered rule in §4 unapplied.

### LQ12 — Seeds on the reference population become committed on this path

- **The facts:** JA18 needs Janus-M 0 outputs on the 420 remaining training cases. That is JA10's conditional "seeds
  on all 740" (≈ 12 GPU-h); India estimated ≈ 10.
- **Options:**
  - (a) commit it on this path, run after the decision-set look, on whichever model passes;
  - (b) keep it conditional.
- **Recommendation: (a).** Without it, path A has no calibrated sign at all. The committed total on this path
  becomes ≈ 15 GPU-h.

---

## 6. Forking question: **no fork**

The cap allows one fork (2 of 4 paths are active), but no open question on this path changes its structure:
- **LQ10** changes one column, and every option keeps the same table, reads and metric.
- **LQ11 and LQ12** are compute choices.
- **The rest-TPR and fat outcomes** are pre-registered rules on JM-0R's numbers, not lead choices.

Forking on any of them would duplicate the path for no structural difference.

---

## 7. What Round 3 on this path must settle

1. **Apply the pre-registered rules to Job JM-0 and JM-0R** (or the fallback scripts):
   - halves (JA2);
   - the thickness-definition check (Hotel §4.4: is the median within 1.5 mm of 5.7–6.5 mm?);
   - the seed's half-maximum offsets, and whether a snap tool is needed;
   - the rest-TPR gate (JA17);
   - the provisional fat cut (JA18);
   - the septal-arc column and the geodesic rule (JA20);
   - AHA failures.
2. **Validate the JA15 harness as the geometry module's fixture:** the ASSD, signed-bias and thickness
   implementations, and whether the bias estimator meets JA16's ±0.05 mm, which decides 0.3 vs 0.5 mm.
3. **Re-run Lima's E3 with the measured `cv_n` and segment shape,** and fix the detectable depth printed on the page.
   Also measure the composite pattern's population rate where seeds exist.
4. **Specify the table writer and the reference-population config** (JA18, JA19) as `role:swe` issues, including
   how F1's RC is computed per territory from the reads.
5. **Finalise protocol v1 in the read queue** (JA21), and record any change the queue's builders need.
6. **The twin-list re-pin** (JA22) is confirmed merged, with the refused count reported.
7. **A path summary for the lead on #142:** what path A assumes and has built, and how it compares with
   `jm/paired-scar`. Its Stage A table, protocol, harness and calibration carry over to path B.

Not for Round 3: the seal size. It needs the first 20 decision double reads, and JA16 already fixes how it is set.

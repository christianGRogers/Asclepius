---
tags: [janus-m, plans, candidate, round3, path-rest-ccta, myocardium, measurement, calibration, protocol]
author: Hotel
round: 3
version: 3
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#167
---

# Hotel v3: rest CCTA only. Measure the borders exactly, pre-register every decision, print what cannot be seen

**The position in one line.** Path A's plan is now fixed in structure (Hotel v2 + JA15–JA24). What remains is
making every number it prints trustworthy before any read exists. That means three things:
- an estimator that actually recovers a known border shift;
- a detectable depth computed from measured inputs;
- decision rules, specifications and a protocol written so exactly that the lead's JM-0R output, the engineers'
  `role:swe` issues and the read queue need no further judgement.

**Base.** The master plan on this path: [[Hotel v2]] with JA15–JA24 ([[Janus-M Round 2 rest-ccta|Round 2
ruling]]), on Juliet v1 + JA1–JA14. Hotel v3 changes nothing in that structure. It settles Round 2 §7 items 2–5,
and writes item 1 as a pre-registered procedure.

**New evidence this round** (CPU, synthetic only; code in `experiments/JanusM/Hotel/r3/`):
- **E6** [[Hotel - Only volume-over-area and sub-voxel point-to-plane estimators recover a known border shift to 0.05 mm]]
- **E7** [[Hotel - With the measured cv_n a territory must thin by 30 percent before rule C finds it, and the page says so]]
- **The decision procedure as code:** `r3/jm0r_decide.py`. It was dry-run on mock inputs and needs no guard
  (aggregates only).

**Held-out cases.** No case of any kind was opened this round: every experiment is an analytic phantom or a
simulation. E7 reads one committed aggregate file, Lima's guarded self-test summary of the 23 allowed public hearts,
and opens no image. `janusm.guard.refuse` is called by every Hotel script that could touch a case; none does this
round. There is nothing to disclose.

---

## 1. The plan in one paragraph (unchanged structure)

Janus-M 0 (`heartchambers_highres` + the JA2–JA4 geometry module) runs on rest CCTA and fills two tables:
- **Table A:** segment × layer;
- **Table B:** per Janus artery. It carries the reader's CAD-RADS 2.0 grade for that artery (LQ10), the
  patient-specific and AHA-default territory mass, "shared" segments, the four fixed concordance phrases, and the
  printed detectable depth.

**Signs:**
- **Thinning** is flagged per territory by Lima's rule C, and shows only above Hotel's F1 floor (RC of the
  territory mean) and India's κ ≥ 0.6 gate.
- **Hypoattenuation and fat** follow the same procedure.
- **Rest TPR** enters only through JA17's gate.

Every threshold is calibrated for specificity on the ImageCAS-X reference population (420 cases), frozen before any
seal read. Sensitivity for scar is never stated. In its place the page prints the detectable depth (E7). Janus-M 1
trains only if Janus-M 0 fails JA8 on the decision set.

## 2. Item 2 — validating the JA15 measurements against JA16's ±0.05 mm (E6)

**Question.** Can any signed-bias estimator recover a known 0.5 mm shift in each direction to within ±0.05 mm? If
so, the JA16 guard is 0.3 mm; if not, it stays 0.5 mm. Which ASSD, bias and thickness implementations become the
geometry module's single shared fixture (#170)?

**Design** (E6 note).
- **Phantom:** an analytic LV with known continuous signed distances, on two grids:
  - native 0.5 mm isotropic;
  - ImageCAS-like 0.4 × 0.4 × 0.5 mm.
- **Variations:** three orientations (one axis-aligned, two random, so the walls are oblique to the grid), and
  smooth or rough walls (0.6 mm, 3 mm bumps).
- **Perturbations:** shifts of ±0.1–1.0 mm per border, and JA15 random fields (8 mm, σ 0.25 and 0.5).
- **Truth** is exact for shifts and first-order for fields.
- **Estimators:**
  - signed bias: India's and Lima's functions, imported unchanged, against three Hotel estimators (one-sided
    terms averaged both ways; sub-voxel point-to-plane; volume over area);
  - ASSD: the shipping `segtrain.metrics` / `janusm_reads.anchoring` voxel ASSD, against two Hotel estimators;
  - thickness: `janusm.geometry.depth`, median over segments.

**Results** (E6 note; `r3/e6_summary.json`):

**Signed bias.** Pass rule, fixed before the run: |error| ≤ 0.05 mm at +0.5 and at −0.5 mm on every border, grid,
orientation and wall, 24 conditions per direction.

| Estimator | Worst error at +0.5 / −0.5 mm | Random fields, worst | Meets JA16? |
|---|---|---|---|
| India R2 (imported) | 0.129 / 0.045. It under-reads outward shifts by 0.12 | 0.106 | no |
| Lima R2 (imported) | 0.050 / 0.137. It under-reads inward shifts by 0.12 | 0.106 | no |
| Hotel sym (two-sided average) | 0.067 / 0.079 | 0.034 | no |
| **Hotel pp** (sub-voxel point-to-plane) | 0.025 / 0.032 | 0.032 | **yes** |
| **Hotel vol** (volume ÷ smoothed area) | **0.012 / 0.019** | 0.033 | **yes** |

**ASSD.** The shipping voxel ASSD over-reads by **+0.04 mm at a true 0.25–0.3 mm**, which is JA8's margin, and
under-reads at 1 mm. Its error depends on the displacement, so it does not cancel in d. The pp ASSD is within
0.02 mm up to 0.5 mm.

**Thickness.** `janusm.geometry.depth`, median over segments, reads a 0.5 mm endocardial shift as 0.47 mm (worst
error 0.057), and 0.25 as 0.24.

**Rulings Hotel asks for:**
1. **JA16's guard becomes |bias| ≤ 0.3 mm.** The validated estimator is **vol** (worst 0.019 mm), with **pp** as an independent cross-check. A case where they disagree by > 0.05 mm is listed for inspection.
2. **#170's fixture exposes exactly one implementation each:**
   - signed bias: **vol**;
   - ASSD: **pp** for scoring;
   - thickness: `janusm.geometry.depth` (equal thickness), median over segments 1–16 (JA15).
3. **The shipping voxel ASSD** (read-queue anchoring, `segtrain.metrics`) **may stay for anchoring**, because there
   it only compares reads with reads, and its offset (≤ 0.045 mm) is small against the 0.2 mm anchoring margin. **JA8's d must use the fixture's
   ASSD for both terms** (model-vs-read and read-vs-read). Mixing implementations would leave their offset in d,
   which is the size of the JA16 margin's resolution.

## 3. Item 3 — the detectable depth (E7)

- **The re-run.** Lima's rule C was re-run with the measured `cv_n` (0.088) and segment shape. They come from Lima's
  guarded self-test on 23 public hearts, the only measured values before JM-0R.
- **The double count, removed.** `cv_n` measured on Janus-M 0's borders already holds its error, so adding `sig_m`
  counts it twice.
- **Settings.** A 0.05 depth grid, 4 replicate populations, and Hotel's F1 floor swept.
- **Result.** **A territory must thin by 30 % (relative to the patient's other walls) for ≥ 80 % detection.** That
  holds for any phase mix or prevalence, with an F1 floor up to 0.7 mm; at 1.0 mm it is 35 %. False flags are
  ≤ 2 %.
- **Lookup on `cv_n`:** 0.06 → 20–25 %, 0.12 → 40 %, 0.15 → 45 %.
- **The page sentence and the re-run rule are fixed** (E7 note, "What it changes"). The script reruns on JM-0R's
  summary with `--inputs`, and its primary-row value replaces the 30 %.
- **The composite pattern's population rate** needs Janus-M 0 outputs on the reference population (LQ12). It is
  measured then, by the reference-population job (§4.2), and printed with the composite.

## 4. Item 4 — specifications for `role:swe` (JA18, JA19)

Two issues on this path. Both are written to be built without further research input. Hotel does not build them.

### 4.1 Issue A: the reference-population job and its pinned config

**Outcome.** A pinned config, `configs/janusm/reference-r3.json`, holds every calibrated constant the table uses.
One job produces it, once, before any seal read.

**Inputs:**
- Janus-M 0's labels on the **420** ImageCAS-X training cases left after the draw. That is `splits.json` train
  minus `sealed-r1.json`'s seal 60, decision 40 and JM-0 40.
- The reference coronary labels for those cases.
- The CT.
- The **first 20 decision double reads**, for F1 and κ (§4.3).

**Guard:**
- `janusm.guard.refuse(cases, what="JA18 reference population", purpose="any")` before any file is opened;
- the case list is recomputed from `splits.json` and `sealed-r1.json` and must equal the list passed in;
- the `splits.json` hash is checked (JA6).

**Computes, per case, through `janusm.geometry` only** (one implementation per quantity):
- segment thickness: median of the mid-wall voxels' equal-thickness thickness;
- the relative thickness vector (thickness ÷ patient median over 1–16);
- guarded subendocardial core HU relative to the patient's median core HU;
- core fat clusters for every (c, V) on JA18's grid and for Hotel's patient noise-aware rule;
- guarded TPR, only if JA17 passed;
- territory (Euclidean, patient-specific and AHA default);
- QC flags (AHA frame failure, orientation, "shared").

**Then, pooled:**
1. **Shape and scales.** `shape[16]` = the per-segment median of relative thickness (rule C).
   `scale[16]` = 1.4826 × the median of |z| over z ≥ 0, per segment. The same is done for relative subendocardial
   HU.
2. **Cuts.** Rule C's cut is computed by `calibrate_c` exactly as committed (mirror null, 20 000 null patients,
   k from 1.0 to 6.0 in 0.05 steps, ≤ 5 % of null patients with any territory flag), separately for:
   - thinning;
   - hypoattenuation;
   - fat, as the least strict (c, V) with ≤ 5 % of hearts carrying a cluster, with Hotel's rule as one more
     candidate.
3. **The composite's population rate.** The share of patients with a thinning flag and a subendocardial fat or
   hypoattenuation flag in the same territory. If it exceeds 5 %, the composite needs two contiguous segments
   (Hotel v2 §4.3).
4. **The detectable depth.** `e7_detectable.py` logic, run on this population's own `cv_n` and shape. It
   supersedes JM-0R's provisional value.
5. **Construct checks** (reported, never tuned): contiguity, endocardial predominance, co-location with territory.

**Writes** `reference-r3.json`:
```json
{
  "version": 1,
  "geometry_version": "...", "guard_version": "...", "model": "heartchambers_highres <version> + geometry",
  "cases_sha256": "<sha256 of the sorted 420 ids>", "splits_sha256_prefix": "a53bd426cddc",
  "n_cases": 420, "n_usable": 0, "label": "this population, phase-uncertain",
  "thinning":        {"shape": [16], "scale": [16], "median": 0.0, "mad": 0.0, "k": 0.0, "cut": 0.0,
                      "null_rate": 0.0, "rc_terr_mm": {"LAD": 0.0, "LCx": 0.0, "RCA": 0.0}, "kappa": 0.0,
                      "status": "flag | number_only"},
  "hypoattenuation": {"...same keys...": null},
  "fat":             {"c_hu": 0, "v_mm3": 0, "rule": "grid | patient_noise", "null_rate": 0.0,
                      "rc_terr_mm3": {}, "kappa": 0.0, "status": "flag | number_only"},
  "rest_tpr":        {"gate": "pass | fail | not_evaluable", "guard_mm": 0.0, "z_scale": 0.0},
  "composite":       {"population_rate": 0.0, "needs_two_contiguous": false},
  "detectable_depth": {"value": 0.30, "cv_n": 0.0, "rc_terr_mm": 0.0},
  "construct_checks": {"contiguity": 0.0, "endo_predominance": 0.0, "colocation": 0.0}
}
```

**Pinning.** The file is sha256-pinned by a PR, and the guard and the table writer refuse an unpinned or changed
file. It is produced **once** and never refitted on seal cases.

**Acceptance:**
- unit tests on synthetic populations, which reproduce `calibrate_c` and E7 numbers from fixed seeds;
- a test that refuses a case list containing any seal, decision or JM-0 case;
- the Fir command printed for the lead;
- `pytest` and `ruff` green.

**Compute:** CPU. It needs Janus-M 0 outputs on the 420 cases, which is LQ12's ≈ 12 GPU-h seeding job, run first.

### 4.2 How F1's RC and the κ gate are computed per territory (inside Issue A)

From the **first 20 decision double reads**. They are the same 20 that size the seal under JA16; the margins
themselves are already final.

**F1 (the repeatability coefficient of the territory mean).** For each case i, read r ∈ {1, 2} and territory T:
1. **Territory segments.** T's segments come from the **AHA-default** map, as rule C is calibrated (JA18).
2. **D_irT** = shape-corrected mean thinning (mm) of T against the patient's remote segments:
   - level = median over segments s ∉ T of thick_s ÷ shape_s;
   - D = mean over s ∈ T of (level × shape_s − thick_s).

   This is `f1_deviation` in `e7_detectable.py`.
3. **RC_T** = 1.96 × √( mean_i (D_i1T − D_i2T)² ).

   This is Bland–Altman's RC from the read-to-read differences. It assumes no systematic reader offset, which is
   checked:
   - if |mean difference| > 0.5 × SD of differences, both RC and the mean offset are reported, and the offset is
     added to RC.

**Per territory or pooled?**
- RC is computed per territory (LAD, LCx, RCA), and also pooled.
- **The pooled value is used unless** a territory's RC exceeds the pooled value by more than its 95 % χ² upper
  bound (n = 20 differences). With only 20 cases, per-territory estimates are noisy, and pooling is the default.

**Same procedure for the other signs:**
- hypoattenuation: D = shape-corrected mean relative subendocardial HU deficit;
- fat: D = core fat volume in T (mm³).

**κ gate.** On the **40** decision cases (both reads), each sign is evaluated per patient-territory: 120 units,
each flagged or not under the frozen cut.
- Cohen's κ between the two reads.
- **If either read has fewer than 5 flagged units, κ is "not estimable"** and the sign is shown as a number only.
  This is the conservative branch: rare flags cannot demonstrate agreement.
- **Otherwise** the sign may flag if κ ≥ 0.6.

**Order** (fixed before any seal read):
1. The 20 reads give RC and the seal size (JA16).
2. The reference population gives the cuts.
3. The 40 decision cases give κ.
4. The config is pinned.
5. Only then is the seal read and scored once.

### 4.3 Issue B: the table writer (JA19)

**Outcome.** One function and one CLI produce Tables A and B for one case, from borders, CT, a coronary tree, the
pinned reference config and the reader's grades. They always produce the same output for the same inputs.

**Interface:**
`janusm.report.build(case_id, labels, ct, affine, coronary, reference, reader_grades=None, *, purpose) -> dict`,
plus `render_markdown(dict)` and `render_html(dict)`.

**Guard and pins:**
- `janusm.guard.refuse([case_id], what="Janus-M report", purpose=purpose)` first;
- `reference` must match its pin;
- the coronary tree source is recorded (JA4: the ImageCAS-X reference tree, or Janus 0 on a Janus-M-allowed case).

**Header** (Hotel v2 §3.2):
- phase, or "phase unrecorded"; with it, every thickness is "phase-uncertain";
- spacing;
- the seed or model's endocardial 10–90 % edge and half-maximum offsets, in the canonical sign: + = the region
  extends beyond the edge (§5);
- AHA orientation pass or fail and the septal arc;
- the territory source;
- `geometry_version`, the reference config hash and `guard_version`.

**Table A (17 rows):**
- segment;
- layer scheme (thirds, or halves per JA2);
- thickness (mm) and its population percentile;
- relative thickness;
- guarded relative subendocardial HU and its percentile;
- core fat (mm³);
- rest TPR (z) only if `reference.rest_tpr.gate == "pass"`, else blank with the reason;
- patient-specific territory and majority share, with "shared" if < 0.6;
- AHA-default territory;
- arc-proportional septal value, if JA20 keeps the column.

**Per-segment values are numbers with percentiles, never flags** (JA18).

**Table B (rows LAD, LCx, RCA):**
- reader CAD-RADS 2.0 grade of the worst lesion, copied, with "not graded" if absent;
- patient-specific mass (g, at 1.05 g/ml) and share, and AHA-default mass;
- segments, with "shared" segments listed apart;
- **territory flags:** thinning, hypoattenuation and fat, each only if:
  - (rule C below the cut) and (D > RC_T) and (status = "flag");
  - otherwise the territory value is shown as a number;
- composite, if both a thinning flag and a subendocardial flag fall in the territory;
- **concordance phrase:** exactly one of the four in Hotel v2 §3.3, chosen by a fixed table on
  (grade ≥ CAD-RADS 3? yes / no / not graded) × (composite? / any flag? / none);
- the optional, unvalidated "mass distal to a reader-marked lesion point" column (JA19).

**Footer, verbatim:**
- "Research output, not validated: no scar or perfusion reference.";
- E7's detectable-depth sentence, with `reference.detectable_depth.value`;
- "Population: this population, phase-uncertain."

**Never printed:** a sensitivity, "scar", "ischaemia", 5.5 mm, −10 HU, or 0.99 as a cut.

**Acceptance:**
- golden-output tests on synthetic label maps (`janusm_reads.phantom`);
- one test per concordance phrase;
- a test that a changed reference config is refused;
- a test that no forbidden word appears;
- `pytest` and `ruff` green.

## 5. Item 5 — protocol v1, final, and what the queue's builders must change (JA21)

The read queue (#155, #161) still implements the Round 1 placeholders. The text below is **protocol v1**. The
change list after it is for its builders, as one `role:swe` issue on `dev`, where the queue is trunk.

### 5.1 Protocol v1 (text for `docs/JANUSM-READ-PROTOCOL.md`)

1. **Labels (JA1):** 1 LV myocardium; 2 LV blood pool; 3 RV blood pool; 4 LA blood pool. Nothing else is drawn.
2. **Papillary muscles and trabeculae are LV blood pool (2).** The endocardium is the compact-wall surface. Where
   trabeculae merge with the compact wall, the border goes at the outer edge of the blood-filled recesses.
3. **Half-maximum rule.**
   - **Where the border lies.** Each border lies halfway between its two plateaus:
     - endocardium: LV blood vs core myocardium;
     - free-wall epicardium: core myocardium vs epicardial fat;
     - septal epicardium: core myocardium vs RV blood.
   - **Plateaus.** They are computed from the seed when the case opens (blank cases: from a reader-placed ROI), and
     shown on screen.
   - **Window, by default:** level = (p₁ + p₂) / 2, width = 1.5 × |p₁ − p₂|, for the border being edited. The reader
     may switch borders. A fixed 800/300 window is available but is not the default.
4. **Basal limits.**
   - The LV pool ends at the mitral annulus plane and the aortic valve plane. Myocardium above the mitral annulus
     is not labelled.
   - The LA (4) runs to the mitral annulus. The pulmonary veins and **the LA appendage are excluded beyond their
     ostia**.
   - The RV pool (3) runs from the tricuspid annulus to the pulmonary valve, trabeculae included.
5. **Seeds:** `heartchambers_highres` masks, coarsened to 2 mm and smoothed (σ 1 mm, confirmed). 10 seal cases are
   read from blank. The reader sees no model output other than the seed.
6. **Checks at submission** (code; a failed hard check returns the read):

   | Check | Rule | Kind |
   |---|---|---|
   | Half-maximum, per border | Median offset over the border ≤ 0.5 mm (canonical sign, reported) | Return once (below) |
   | Half-maximum, per octant | Octant median ≤ 1.0 mm | Warning only |
   | LV pool ↔ LA pool | Labels 2 and 4 never share a face | Hard |
   | Mitral plane | Label 2 extends ≤ 3 mm above the plane fitted to the 2–4 interface of the seed (blank cases: of the read) | Hard |
   | LV pool ↔ RV pool | No shared face (the septum lies between them) | Hard. Tightened from the current ≤ 0.5 % |
   | LV pool holes | None enclosed | Hard (as now) |
   | Myocardium connectivity | > 2 % outside the largest piece | Hard (as now); 0–2 % a warning |
   | LV pool facing background | > 25 % of its surface | Warning (as now) |
7. **Return once, then accept and flag.**
   - **First failure:** the read is returned with the failing check and, for the half-maximum check, the profile
     plot (HU against signed distance, with both plateaus and the half level marked) and the offending border
     highlighted.
   - **Second failure of any hard or half-maximum check:** the read is **accepted and flagged**
     (`flagged: true`, with the reasons). A flagged read counts in every analysis, and the flag is reported.
8. **Anchoring, per wave** (JA21):
   - **Report:** seed-vs-read and inter-read ASSD per border; the share of seed voxels changed per read; the
     half-maximum offsets of seeds and reads.
   - **Rule 1:** if the upper 95 % paired-bootstrap bound of (blank-vs-seeded ASSD − seeded inter-read ASSD)
     exceeds **0.2 mm** on either border, seeded reads cannot accept a model.
   - **Rule 2:** if more than half of a wave's seeded reads change < **5 %** of seed voxels, the wave is flagged and
     its blank re-read follows (10 cases).

### 5.2 Change list for the queue's builders (one `role:swe` issue on `dev`; Hotel does not build it)

Measured against the merged code (paths on `dev`):
1. **Window.** Plateau-centred by default, width = 1.5 × |p₁ − p₂| (`slicer/JanusMRead/JanusMRead.py`, which
   defaults to 800/300 at about line 73; `JanusMReadLib/halfmax.py` uses a 50 HU width).
2. **Half-maximum tolerance.** Per-border median ≤ 0.5 mm, with octants as warnings only
   (`src/janusm_reads/checker.py`, where `tolerance_mm = 1.0` and any octant fails; update
   `tests/test_janusm_reads.py`).
3. **Return once.**
   - Use the existing `attempts` counter (`server/girder_janusm/models.py`).
   - A second failure goes to `ACCEPTED` with `flagged: true` and reasons (`server/girder_janusm/check.py`,
     `src/janusm_reads/protocol.py`).
   - Send the half-maximum profile to the reader.
4. **New hard checks** in `checker.py`:
   - no LV–LA face;
   - label 2 ≤ 3 mm above the fitted mitral plane;
   - LV–RV contact strict (now ≤ 0.5 %).
5. **Protocol text.** Trabeculae rule, appendage, aortic plane, RV extent and "myocardium above the annulus not
   labelled" go into `docs/JANUSM-READ-PROTOCOL.md` §2 and `labels.py` `CONVENTIONS`.
6. **Anchoring** (`src/janusm_reads/anchoring.py`, which today uses mean blank − seeded > mean inter-read with no
   margin):
   - add the 0.2 mm margin with a paired-bootstrap upper bound;
   - add the < 5 % changed-voxel wave rule and the wave flag;
   - add the seed and read half-maximum offsets.
7. **Export** (`server/girder_janusm/export.py`). Write per read:
   - reader id, seeded or blank, seconds, attempts;
   - flagged and reasons;
   - the half-maximum offsets per border, in the canonical sign.
8. **Versioning.** Mark the border protocol text "protocol v1 (JA21)". Record `border_protocol: 1` in every read
   record and export, apart from the wire `PROTOCOL_VERSION`, so a later text change is visible in the data.
9. **ASSD in anchoring** may stay the voxel implementation (§2). The fixture's ASSD is required only for JA8 scoring.

## 6. Item 1 — the pre-registered decision procedure for JM-0 / JM-0R

### 6.1 What runs, and when

- **When.** It runs **when the lead posts the outputs on #142**, and not before.
- **The command:** `python experiments/JanusM/Hotel/r3/jm0r_decide.py --jm0r <JM-0R aggregate>`. If JM-0R has not
  shipped, the fallback inputs are `--juliet --lima --india --hotel <each script's aggregate>`.
- **What it reads.** Aggregates only. It prints one outcome per rule, and every threshold is a constant in the file.
- **Who acts.** The path's next round, or the PM, records the outcomes. No advocate re-argues a threshold after the
  numbers are seen.

### 6.2 The rules

| # | Question | Rule (threshold → outcome) |
|---|---|---|
| R0 | Enough cases? | ≥ 36 of 40 usable → proceed; else **stop**, post the reasons, apply nothing |
| R1 | AHA failures (JA3) | ≤ 10 % → failing cases flagged and left out of F2; > 10 % → geometry fix (`role:swe`) before the reference population |
| R2 | Halves (JA2) | JA2 per segment always; if > 25 % of segments need halves, Table A shows halves everywhere (thirds in the research export only) |
| R3 | Thickness definition (Hotel v2 §4.4) | Median within 1.5 mm of 5.7–6.5 mm (4.2–8.0 mm) → F3 holds; else readers hand-measure thickness on the first 20 decision cases, Janus-M's definition is aligned before F2, and no thinning flag ships until then |
| R4 | Seed half-maximum offsets | \|endo\| and \|epi\| ≤ 0.25 → no snap; either in 0.25–0.5 → snap for rest TPR only; either ≥ 0.5 → snap the seeds before any read, and R3 uses snapped borders |
| R5 | Rest TPR gate (JA17) | Edge > 2 mm → not computed. Edge > 1.5 mm → not shown. Otherwise guard = max(1 mm, FWHM); if > 1 mm and JM-0R is absent → not evaluable, not shown. \|endo offset\| > 0.25 → not shown until snapped. Median guarded free-wall TPR in 0.99–1.15 → shown as a patient-relative z-score; else not shown |
| R6 | Provisional fat cut (JA18) | Least strict (c, V), c ∈ {0, −30, −50, −100}, V ∈ {5, 20, 50}, with ≤ 5 % of hearts carrying a cluster; Hotel's patient rule as one more candidate; none passes → fat is a number only |
| R7 | Septal-arc column (JA20) | Median share of mass changing segment < 10 % → dropped; else kept |
| R8 | Geodesic vs Euclidean (JA20) | < 10 % of segments change majority → Euclidean, no further ruling. ≥ 10 % → **Hotel's pre-registered position:** Euclidean stays primary (the Voronoi rule Kurata and Ide validate; JA24), and segments whose majority differs are shown as "shared" |
| R9 | Detectable depth (E7) | `e7_detectable.py --inputs <JM-0R>` → the printed depth; if > 0.40, the page says so and nothing is loosened |

**Canonical sign** for every half-maximum offset (JM-0R, the table header, the queue export): **+ = the labelled
region extends beyond the image half-maximum** (the LV pool for the endocardium; pool + myocardium for the
epicardium). Lima and India already use it. **Hotel R2's add-on reports the endocardium with the opposite sign.**
The procedure negates it, and the JM-0R spec (#169) should state the canonical sign.

**Dry run.** It was run on mock inputs only: Lima's public-heart self-test summary, and Hotel's synthetic smoke-test
aggregate. Every rule evaluates. R0 correctly stops on the self-test's 23 cases and marks every other outcome
"not applied". These outcomes are **not** results; the public hearts are 1.5 mm model-made labels.

### 6.3 Keys JM-0R should emit (for #169)

So the procedure reads JM-0R without adapters:
- `n_usable`, `aha_failures`, `share_segments_needing_halves`, `median_thickness_mm` (`{p10, p50, p90}`);
- `endo_offset_mm_median`, `epi_offset_mm_median` (canonical sign), `endo_10_90_mm_median`;
- `tpr_guard1_free_patient_median`, `tpr_guard_adaptive_free_patient_median`;
- `share_hearts_with_fat_cluster` (`{c: {V: share}}`), `share_hearts_with_fat_cluster_patient_rule`;
- `seg_changed_fixed_vs_arc_median`, `segments_differ_euclid_vs_geodesic`;
- `rel_thickness_by_segment_mean_sd`, `rel_thickness_shape_corrected_sd` (for R9).

## 7. Other Round 2 §7 items

- **Item 6 (twin re-pin, JA22).** This is #168, being built. Nothing here depends on it: no Hotel experiment opens a
  TotalSegmentator case.
- **Item 7 (path summary for the lead on #142).** This is the judge's and PM's. Hotel's input is a single line:
  path A delivers a reproducible geometry table whose every flag is specific by construction, prints the depth it
  cannot see, and carries over unchanged to path B as Stage A.

## 8. Lead questions, carried as stated assumptions

| Question | Assumed (the rulings' recommendation) |
|---|---|
| LQ2 Learned structures | (a) LV myocardium + LV, RV, LA pools |
| LQ3 `heartchambers_highres` licence | (a) yes, key typed by the lead on Fir |
| LQ4 ImageCAS-X training cases | (a) yes |
| LQ5 Reader time | (a) 200 double reads + 10 blank, after A39 |
| LQ6 MM-WHS | (a) sign, low priority |
| LQ7 Released coronary patients | (a) training only, explicit PR |
| LQ8 s0655 | (a) keep the seal |
| LQ9 Round 1 twin disclosures | (a) a one-line note, no seal change |
| LQ10 Stenosis column | (a) reader CAD-RADS 2.0 per vessel in the Janus-M queue |
| LQ11 Fir CPU job | (a) JM-0R after JM-0, or (b) the fallback if JM-0 returns first |
| LQ12 Reference-population seeds | (a) committed on this path (≈ 12 GPU-h); Issue A (§4.1) needs them |

## 9. Compute

**Nothing new.** Hotel v3 adds no Fir job:
- JM-0R (#169) replaces Hotel's Round 2 add-on;
- the reference-population job (Issue A) is CPU after LQ12's seeding.

The committed total on this path stays ≈ 15 GPU-h (JA10 + LQ12).

## 10. What would change this plan

| Result | Change |
|---|---|
| JM-0R: `cv_n` > 0.12 | The printed detectable depth is ≥ 40 %. The thinning flag stays, and the page says what it cannot see |
| First 20 decision reads: RC_T > 1.0 mm | E7: the depth rises to ≥ 35 %. If κ < 0.6 as well, thinning is shown as a number only |
| On the first 20 decision double reads, vol and pp disagree by a median > 0.05 mm on real read pairs | The phantom validation does not transfer; the JA16 guard returns to 0.5 mm |
| The reference population's composite rate > 5 % | The composite needs two contiguous segments |
| The lead chooses path B | Everything here carries over to path B's Stage A |

## 11. Sources

JA14 and JA24 corrections apply.
- Bland JM, Altman DG. *Lancet* 1986;327(8476):307–310. doi:10.1016/S0140-6736(86)90837-8. The repeatability
  coefficient.
- Chen J, et al. *Clin Imaging* 2025;118:110390. doi:10.1016/j.clinimag.2024.110390. CT wall thickness, 5.7 mm at
  end-diastole and 6.5 mm at mid-diastole.
- Cohen J. A coefficient of agreement for nominal scales. *Educ Psychol Meas* 1960;20(1):37–46.
  doi:10.1177/001316446002000104. The κ gate.
- Cury RC, et al. CAD-RADS 2.0. *J Cardiovasc Comput Tomogr* 2022;16:536–557. As checked by the Round 2 judge.
- Kurata A, et al. *Eur Radiol* 2015;25:49–57; Ide S, et al. *J Cardiovasc Comput Tomogr* 2017;11:179–182. Both
  validate whole-territory Voronoi (Euclidean) mass, not geodesic assignment (JA24).
- Lima's E3 code and self-test: `experiments/JanusM/Lima/calibrate_sim.py`, `local_check_summary.json` (Round 2).

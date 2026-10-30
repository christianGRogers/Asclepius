---
tags: [janus-m, plans, candidate, myocardium, layers, scar, path-b]
author: Juliet
round: 2
version: 2
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#143
---

# Juliet v2: one border model, two scans, and a paired cohort that can prove the scar map

**Path `jm/paired-scar`, option B of LQ1.** This plan is the Round 1 master plan (Juliet v1 + JA1–JA14), unchanged
on the trunk items, plus everything option B adds. Every JA amendment binds. Where this plan says more than a JA, it
says so.

## 0. What is new since v1

| v1 | v2 (path B) |
|---|---|
| Scar is "Phase 3, needs data" | A **paired-cohort specification** in three tiers, with timing windows and sizes from a power simulation (E5, §8.1) |
| Borders "transferred from the same session's CCTA" | A **registration method with a measured tolerance**: rigid mutual information inside a heart mask, a fat/blood QC gate, and fall-back rules (E6, §8.2) |
| "Threshold rule calibrated against LGE" | A **two-stage scar head**: presence, then Kim bin on depth-binned transmural extent. A rule head first; a learned head only on stated conditions (E6–E7, §8.3) |
| Stage A signs unvalidated | A **validation plan for the Stage A signs against LGE** in the same cohort (§8.4) |
| — | Hotel's half-maximum edge offsets as an add-on to Job JM-0 (`fir/edges_m0.py`, §9 item 1) |

## 1. Thesis

**Janus-M stays a border model.** It learns the four JA1 borders on first-pass CCTA, and code computes everything
else. On path B, two more images enter, and neither changes the learned label set:

1. **The late-iodine (LIE) scan of the same session.** It is registered to the CCTA. The CCTA borders, depth and
   segments are carried onto it, and scar is graded inside them.
2. **The CMR LGE of the same patient.** It is the reference standard for that grade, per AHA segment.

There are three reasons, each measured or cited.

- **The borders must come from the first pass.** On LIE the blood pool is as bright as scar. An LIE-only reader
  scores chance-level Kim-bin accuracy (Golf R1 E3). The first-pass borders, on the other hand, are what Janus-M
  already learns.
- **Registration is the new error, and it is tight.** An uncorrected 1 mm shift between the two scans already costs
  [E6: bin accuracy] (§8.2). Rigid mutual information inside a heart mask brings it to [E6]. So path B's first
  engineering requirement is the registration and its QC gate, not a new network.
- **The cohort, not the model, is what decides path B.** Sixty validation patients, half with a prior MI, give 93 %
  power to show segment-level agreement with LGE. Sensitivity is the endpoint that limits power (E5). So the plan
  is sized by data requirements, which the lead can obtain or not. Nothing in this repository asks for it (D31).

## 2. What binds, and what this plan assumes

**Binding:** JA1–JA14, the project decisions (D19, D27, D31–D35, A14), M1, M2. Path B adds nothing to the coronary
side: no coronary seal, reserve, D35 or A14 case is read, scored or trained on.

**Carried assumptions.** These are the Round 1 recommendations. Each stays a question for the lead.

| Question | Assumed | Effect on this path if the lead answers otherwise |
|---|---|---|
| LQ2 learned structures | (a) LV myocardium + LV, RV, LA pools | (b) adds RV myocardium, scored by thickness only; no change to scar, which is LV only |
| LQ3 `heartchambers_highres` licence | (a) yes, Janus-M 0 and seeds | (b) Janus-M 1 runs early; the LIE pipeline then waits on it |
| LQ4 ImageCAS-X train as images | (a) yes | (b) Stage A slows. The paired cohort is a separate source either way |
| LQ5 reader time | (a) 200 double reads after A39, separate queue | Path B adds LIE scar reads only on the cohort (§8.3) |
| LQ6 MM-WHS | (a) sign, low priority | none |
| LQ7 released coronary patients | (a) training only, explicit PR | none |
| LQ8 s0655 | (a) keep the seal | none |

## 3. Class schema (JA1, unchanged)

- **Learned:** 0 background; 1 LV myocardium; 2 LV blood pool (papillary muscles and trabeculae included); 3 RV
  blood pool; 4 LA blood pool.
- **Not learned, on any path:** no layer, segment, territory or scar class.
- **On path B, scar is a computed sub-map of class 1.** It is a per-voxel call inside the registered myocardium,
  aggregated to segment presence and a Kim bin (§8.3). A learned scar head is allowed only under §8.3's
  conditions. Even then it is a second head *inside* class 1, so the four-border model and its metric are untouched.

## 4. Outputs

Every output is reported per AHA segment and per Janus territory, and labelled **"research output, not validated"**
until §8 has scored it.

| Stage | Output | Rule | Validated by |
|---|---|---|---|
| A (rest CCTA) | thickness; thinning | JA11; the thinning cut-off is set on reads | §8.4 against LGE |
| A | resting subendocardial hypoattenuation | guarded mean attenuation per layer (1 mm guard, E2 R1) | §8.4 |
| A | intramyocardial fat | core sample ≥ 1 mm from either border, −180 to 0 HU (JA11), cut-off set on data | §8.4 |
| A | mass per territory | definition | — |
| **B (LIE)** | **scar present, per segment** | §8.3 stage 1 | §8.1 validation third, against LGE |
| **B** | **Kim bin (1–25 / 26–50 / 51–75 / 76–100 %)** | §8.3 stage 2: depth-binned transmural extent inside the registered borders | §8.1, quadratic-weighted κ |
| B | scar mass and % LV | voxel count × 1.05 g/ml | report-only |
| B (where acquired) | ECV per segment | from the same LIE plus haematocrit; Nacif 2012 r = 0.82 vs MRI ([10.1148/radiol.12112458](https://doi.org/10.1148/radiol.12112458)) | report-only (no ECV reference in the cohort) |
| B (where acquired) | stress TPR per segment and territory | guarded (E2 R1), on the same thirds | §8.5 against FFR, secondary |

## 5. Data

### 5.1 Stage A (trunk, JA5–JA6 unchanged)

ImageCAS-X train 560 for the seal (60), the decision set (40) and JM-0 (40). The 180 non-sealed quality-0 cases are
for training only. The external report-only stratum is unchanged. Nothing about path B touches these lists.

### 5.2 Stage B: the paired cohort

**No open CT dataset with LIE, CT perfusion or a CMR reference exists** (all five Round 1 advocates searched; Juliet
v1 §4). The cohort is therefore a retrospective institutional export, if the lead pursues one, and outside the
repository (D19, D31). §8.1 states what it must contain, as data requirements only.

**Handling, once it exists:**
- It sits only in the project's Girder, in its own collection.
- Patient keys are hashed on import, and **the JA12 guard runs on every import.** The cohort is new data, but the
  guard proves no coronary pool, seal or A14 patient is among it.
- It is never mixed into the Stage A seal or decision set.
- No image, id or per-patient number from it enters the repository.

## 6. Reference standards

| Quantity | Reference | Reads |
|---|---|---|
| Borders (Stage A) | JA7: two independent reads, half-maximum rule, coarsened seeds, 10 blank | unchanged |
| Borders on the cohort's CCTA | the same protocol, single-read, plus a 10 % double-read audit | §8.3 |
| Scar presence and Kim bin per segment | **CMR LGE, read per AHA segment by two readers blinded to CT**; a third reader adjudicates a disagreement of ≥ 2 bins or on presence | §8.1 |
| Scar extent (secondary) | FWHM quantification on LGE. FWHM correlated best with pathology in a canine model (r² = 0.94; Amado 2004, [10.1016/j.jacc.2004.09.020](https://doi.org/10.1016/j.jacc.2004.09.020), abstract) | report-only |
| Ischaemia (secondary) | invasive FFR ≤ 0.80 per vessel | §8.5 |

LGE reads happen inside the project, from images, never from the clinical report alone.

## 7. Models, metric and compute: Stage A unchanged

- **Models (JA9):** Janus-M 0 = `heartchambers_highres` + the geometry, with no training. Janus-M 1 (nnU-Net v2
  ResEnc, 0.5 mm, mirroring off) runs only if Janus-M 0 fails JA8.
- **Metric (JA8):** border ASSD against inter-read, with thickness co-primary.
- **Compute (JA10):** Job JM-0 ≤ 1 GPU-h, with commands as committed in Juliet v1 §7. Path B adds:
  - **CPU only:** registration and the rule head, about 5 min per cohort patient (E6 timing);
  - **GPU, conditional:** a learned head, about 20–30 GPU-h, only under §8.3's conditions.

## 8. Path B: the paired cohort, registration, scar head and validation

### 8.1 Paired-cohort specification (data requirements only)

**Tiers.** Each tier is useful alone; a patient may belong to more than one.

| Tier | Contains | Validates | Minimum |
|---|---|---|---|
| **T1** | ECG-gated rest CCTA + CMR with LGE | Stage A signs against LGE (§8.4); borders on a second population | 60 patients, ≥ 50 % with a prior MI |
| **T2** | T1 **plus LIE from the same CT session** | the LIE scar output, presence and Kim bin (§8.3) | **90 patients: 30 calibration + 60 validation, ≥ 50 % with a prior MI** |
| T3 | rest CCTA + stress CT perfusion + invasive FFR | stress TPR per vessel (§8.5), secondary | ≥ 120 vessels with FFR, ≥ 30 % of them ≤ 0.80 |

**Phases and acquisition fields required per patient.**

- **CCTA (first pass):**
  - ECG-gated, with slices ≤ 0.75 mm;
  - the reconstruction phase (% R-R) recorded, which ImageCAS lacks (JA11);
  - kV, kernel and vendor recorded.
- **LIE (T2):**
  - same session and same contrast injection as the CCTA;
  - **acquired 5–10 min after contrast**, with slices ≤ 1 mm;
  - ECG-gated, and the gating phase recorded;
  - energy mode recorded: single-energy, dual-energy or photon-counting;
  - **in the same DICOM frame of reference as the CCTA** (one frame-of-reference UID, same table position). §8.2's
    first step uses scanner coordinates.
  - Why 5–10 min:
    - CNR between infarct and remote myocardium was highest at 7 min (6.4 ± 2.5) and not different at 5 min, and
      5 min was recommended (Hamdy 2019, [10.1007/s10554-018-1513-z](https://doi.org/10.1007/s10554-018-1513-z),
      abstract);
    - LIE studies report 5–15 min (van Assen 2020, [10.1186/s41747-020-00158-1](https://doi.org/10.1186/s41747-020-00158-1),
      open full text).
- **Haematocrit within 24 h of the CT (optional).** It is needed only for ECV.
- **CMR (T1, T2):**
  - an LGE short-axis stack covering the LV, plus at least one long-axis view;
  - PSIR preferred;
  - slices ≤ 8 mm;
  - field strength and sequence recorded;
  - cine optional (for wall motion, not used in scoring).
- **T3:**
  - stress CTP (static or dynamic), with stressor and timing recorded;
  - invasive FFR per measured vessel, with the vessel and the lesion position named on the coronary tree.

**Timing windows** (a data requirement on the dates, not a request).

- **CT to CMR: ≤ 90 days**, with **no intervening MI, revascularisation or cardiac surgery**.
- **Index MI ≥ 90 days before both scans** for the primary validation (chronic scar). Infarct size on LGE falls
  sharply after an acute MI:
  - 18.3 % of the LV on day 1, 12.9 % on day 7 and 11.3 % on day 35, then stable at 180 days (Ibrahim 2010,
    [10.1148/radiol.09090660](https://doi.org/10.1148/radiol.09090660));
  - 64 % of the one-year reduction happened in the first week (Engblom 2009,
    [10.1161/CIRCIMAGING.108.802199](https://doi.org/10.1161/CIRCIMAGING.108.802199));
  - a further 12 % fall between 4 and 14 months (Pokorney 2012, [10.1186/1532-429X-14-62](https://doi.org/10.1186/1532-429X-14-62));
  - all abstracts.

  A CT and a CMR on either side of that change would disagree for reasons that have nothing to do with the
  pipeline. Patients scanned < 90 days after an MI form a separate **acute stratum**, reported, never pooled.
- **CT to FFR (T3): ≤ 90 days**, with no intervening revascularisation of that vessel.

**Exclusions (data fields that must allow them):**
- prior CABG, kept for scar but out of territory analyses (grafts change territories);
- a device artefact over the LV on either modality;
- non-ischaemic LGE patterns (mid-wall, epicardial), kept in a separate stratum. Kim bins describe subendocardial
  ischaemic scar;
- any patient the JA12 guard refuses.

**Sizes and power (E5).**
- **Primary success rule, on the validation third, scored once:**
  - lower 95 % bound of quadratic-weighted κ (5 classes: none + 4 Kim bins) ≥ 0.60;
  - lower bound of segment sensitivity ≥ 0.70;
  - lower bound of segment specificity ≥ 0.90.

  All three use a patient-cluster bootstrap.
- **Power and false acceptance.** At the pooled LIE performance (0.86 / 0.98; Gatti 2025), 60 validation patients
  with 50 % prior MI pass in 93 % of simulated cohorts, and 45 patients with 80 % prior MI pass in 94 %. A pipeline
  on the sensitivity bound passes in 2–5 % at any N.
- **Sensitivity limits power.** Power is governed by the number of scarred segments, so **≥ 130 scarred segments in
  the validation third** is the requirement that matters. N is just how to get there.
- **Re-powering, fixed now:**
  1. On the calibration third, measure the scarred-segment yield per patient and the within-patient correlation.
  2. Re-run `cohort_power.py` with those two numbers.
  3. Fix the validation N at the smallest that gives ≥ 90 % power.

  This happens before any validation patient is graded. N may grow and never shrinks.
- **Split:** by a salted hash of the hashed patient key (salt `asclepius-janusm-pathb-r2:`). The first third is
  calibration, the rest validation. It is frozen in a config before any LIE is graded (a `role:swe` item, §11).

### 8.2 LIE-to-CCTA registration (E6)

[E6 RESULTS AND METHOD — filled after the run]

### 8.3 The scar head (E6–E7)

[E7 — filled after the run]

### 8.4 Validating the Stage A signs against LGE (T1)

Stage A's signs are research outputs because nothing has scored them. T1 scores them per segment against LGE
presence, with no LIE needed.

| Sign | Score per segment, against LGE presence | Threshold |
|---|---|---|
| Thinning (thickness) | AUC; sensitivity and specificity at the cut | cut set on the T1 calibration third (JA11 forbids borrowing the CMR 5.5 mm) |
| Resting subendocardial hypoattenuation | AUC of the guarded subendocardial / remote ratio | as above |
| Intramyocardial fat | AUC of the fat fraction in the core sample | as above |
| Their combination | AUC of a 3-variable logistic score, fitted on calibration, scored on validation | — |

- **Size.** With ≥ 130 scarred segments, as in E5, a segment AUC near 0.80 has a 95 % half-width of about 0.06. That
  is a Hanley–McNeil estimate made with segments as units, so it is optimistic for clustered segments. The
  patient-cluster bootstrap is what is reported.
- **Phase.** T1's CCTA has a recorded phase, so thinning is no longer "phase-uncertain" there. It stays so on
  ImageCAS.
- **What a result changes:**
  - A sign whose validation AUC CI lies above 0.70 loses the "not validated" label for populations like T1.
  - A sign whose CI covers 0.5 is dropped from the report.

### 8.5 Stress CTP against FFR (T3, secondary)

- **Output:** guarded stress TPR per territory, with the territory from Janus's tree. The cut-off is re-derived on
  T3's calibration third, never inherited (George 2009's < 0.99 was derived and tested on one set; Juliet v1 §3.2).
- **Score:** per-vessel AUC against FFR ≤ 0.80.
- **Size:** 120 vessels give a half-width of about 0.085 at AUC 0.80 (E5; this ignores clustering). This is
  **secondary**. Path B's deciding result is §8.1's scar validation. T3 is reported if it arrives, and the plan does
  not wait for it.

## 9. Round 1 §6 items 1–7 on this path

1. **Job JM-0's numbers.** Not yet run; nothing is invented here. The commands stay as committed (JA10).
   - **Add-on (new):** `experiments/JanusM/Juliet/fir/edges_m0.py`, a CPU step on the same 40 cases. It prints
     Hotel's half-maximum edge offset per border: the label's signed bias from the image edge, positive meaning
     the label myocardium reaches past it.
   - **Self-test on the E6 phantom:** with exact labels, endocardial bias +0.00 mm and epicardial +0.17 mm. The
     +0.17 mm is the floor set by the phantom's 3 mm fat layer. With the epicardium dilated by 1 mm, the
     epicardial bias reads +1.23 mm, so the tool recovers the 1 mm shift to within about 0.06 mm.
   - **Command** (Fir login node, CPU, after JM-0):
     `python experiments/JanusM/Juliet/fir/edges_m0.py --cases $SCRATCH/janusm/m0_cases.txt --hc $SCRATCH/janusm/hc --layout $SCRATCH/icx4/layout.json --out $SCRATCH/janusm/m0_edges.json`
     Send back the printed summary only.
   - **Decision:** if the epicardial bias is ≥ 0.5 mm (JA8's guard), the seeds' epicardium is shifted inward by
     the measured median before the reads, so reads do not anchor on a biased seed. The shift is recorded in the
     read protocol.
2. **Shared perturbation harness.** Carried to the geometry module (#139) tests. One error model: a smooth radial
   field with RMS σ and correlation length ℓ, plus a signed bias b per border. The four Round 1 curves disagree
   because they fixed different (σ, ℓ, b) (ruling §2.3). Reporting all three is what makes any curve portable. This
   path proposes ℓ = 10° of arc (Juliet R1 E1's `smooth_noise`), with σ and b taken from the JM-0 edge offsets
   above.
3. **Depth, sectors, territories.**
   - Equal-thickness depth stays primary (JA2).
   - Fixed sectors stay (JA3).
   - Euclidean territories stay (JA4).
   - The geodesic and Yezzi–Prince alternatives are compared on the 40 JM-0 cases in the geometry module.
   - **On path B, the cohort's LGE adds a check none of the others has:** whether a scar's segments fall in the
     territory of the vessel the cohort records as the culprit, for Euclidean versus geodesic assignment.
4. **Border protocol (JA7)** stays as on the trunk (#141). **Path B adds** the LIE read protocol: scar outlines on
   the registered LIE, inside the carried borders, for the learned-head condition only (§8.3).
5. **Seal re-powering.** JA6 and JA8 as written. The analogous rule for the cohort is in §8.1.
6. **Rest TPR at native 0.5 mm, and the fat cut-off.** On this path both are settled by T1 against LGE (§8.4),
   not by phantoms. Until then, rest TPR stays report-only (JA11).
7. **The twin rule.** Carried to the shared guard (#138). The guard also runs on every cohort import (§5.2).

## 10. What results would change the plan

| Result | Change |
|---|---|
| The lead does not pursue paired data | This path has no Stage B; its Stage A equals `jm/rest-ccta`'s, and the lead keeps whichever is better argued there |
| Only T1 arrives (CCTA + LGE, no LIE) | §8.4 runs, so Stage A signs are validated; LIE scar stays unbuilt |
| T2's frame of reference differs between CCTA and LIE, or the LIE is a separate session | registration starts from a centroid alignment, not scanner coordinates; E6's mask method is still the method, but the QC fail rate is re-measured on calibration |
| Calibration: scarred-segment yield < 2 per patient | validation N rises per §8.1 re-powering, or the lead adds enrichment |
| Calibration: the rule head's sensitivity < 0.75 | the learned head is triggered (§8.3) |
| Validation passes | LIE scar presence and bin lose "not validated" for T2-like scanners |
| Validation fails on sensitivity only | report presence at a lower τ as a screening flag, bins only where present; re-validate on a new third |
| JM-0 epicardial bias ≥ 0.5 mm | seeds shifted inward before reads (§9 item 1) |

## 11. Code that must ship (`role:swe`, labelled `jm/paired-scar`, built on this branch)

1. **LIE registration** (§8.2): rigid MI in a heart mask, the QC gate, written as a library with E6's phantom as its
   test.
2. **The rule scar head** (§8.3): depth-binned extent, presence, Kim bin, built on the shared geometry module (#139).
3. **Cohort import:** hash keys, run the JA12 guard, check the §8.1 fields and windows from DICOM headers and dates,
   and write the calibration/validation split config (frozen, sha256-pinned).
4. **The scoring harness** for §8.1 and §8.4: confusion matrices, patient-cluster bootstrap, and the triple bound.
5. (Conditional) the learned-head dataset builder.

None of these is needed before the lead decides LQ1, except (1) and (2). Those can be built and tested on phantoms
now.

## 12. Questions for the lead (path B only; LQ2–LQ8 as carried in §2)

- **PB-Q1. Cohort tiers.** Pursue T2 (CCTA + same-session LIE + CMR LGE; ≥ 90 patients, ≥ 50 % prior MI) as the
  primary, with T1 and T3 taken where they come. **Recommend: yes.** T2 is the only tier that validates the scar map
  itself.
- **PB-Q2. Chronic-only primary.** Index MI ≥ 90 days before both scans; acute patients in a separate stratum.
  **Recommend: yes** (infarct size on LGE falls by about a third over the first months).
- **PB-Q3. Success rule.** Lower bounds κ<sub>w</sub> ≥ 0.60, sensitivity ≥ 0.70, specificity ≥ 0.90, on the
  validation third, scored once. **Recommend: yes.**
- **PB-Q4. LGE reads.** Two blinded readers per segment, plus adjudication, inside the project. About 90 patients
  × 2 reads at an estimated 10 min each. **Recommend: yes**, in the Janus-M queue after the Stage A reads.

## 13. Risks and unverified items

- **Everything in §8.2–8.3 is phantom evidence.** The phantom has homogeneous tissue, no microvascular obstruction,
  rigid heart motion and a known frame of reference. The calibration third is the first real test.
- **Breath-hold displacement of the heart between the two scans is not sourced.** No abstract found gives a
  heart-specific mm value. Diaphragm position across repeated breath-holds ranged 8.3 mm without feedback (Liu 1993,
  [10.1002/mrm.1910300416](https://doi.org/10.1002/mrm.1910300416)), and heart motion follows the diaphragm
  linearly (Wang 1995, [10.1002/mrm.1910330517](https://doi.org/10.1002/mrm.1910330517)); both are abstracts. So E6
  sweeps 0–10 mm, and the cohort measures it (the registration's own estimate is logged per patient).
- **E5's read model is parametric.** Its correlation and bin-error shape are assumptions. The calibration third
  replaces them.
- **Pooled LIE performance (Gatti 2025)** mixes scanners and acute and chronic MI.
- **Amado 2004 is a canine study**; FWHM is a secondary LGE measure here, not the reference.
- **Cerqueira 2002's territory figure** remains verified from secondary sources only (JA14).
- **Held-out data:** none opened. E5–E7 and the edge self-test are synthetic. `guard_r2.py` ran first in each
  script (320 pool patient keys, 284 ImageCAS-X held-out ids, 16 pool s-numbers; 0 requested, 0 refused). It then
  scanned every committed output for those ids: 0 matches.

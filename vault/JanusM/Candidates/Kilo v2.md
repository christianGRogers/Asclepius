---
tags: [janus-m, candidate, round2, paired-scar, lge, late-iodine-enhancement, transmurality, registration, kilo]
author: Kilo
round: 2
version: 2
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#143
---

# Kilo v2 (path `jm/paired-scar`): grade the scar inside the borders Janus-M already draws, and size the proof on sensitivity

## 0. In one paragraph

**Kilo v2 is the Round 1 master plan (Juliet v1 + JA1–JA14) with path B built on top, and it adds no network until a
rule fails.** Stage A is unchanged from the trunk. Path B adds four things:

- **S0, the scar step: no training.** The first-pass CCTA borders from Janus-M 0 are registered to the late-iodine
  scan (LIE) by rigid mutual-information registration. Scar is then found in the registered wall by **two thresholds
  on remote myocardium**: a specific one (FWHM) decides whether a segment has scar, and an accurate one (remote +
  3 SD) gives its Kim transmurality bin.
- **S1, a learned scar head.** It runs only if S0 fails its pre-registered bar on the development set. It is one
  nested class, *scar inside class 1*, and its output is scored against CMR LGE.
- **The paired cohort, written as data requirements only (D31):**
  - phase-matched CCTA + LIE in one session, with CMR LGE within 90 days, both ≥ 30 days after any infarct;
  - **≥ 120 seal patients with ≥ 270 LGE-scarred segments**, plus a 40-patient development set;
  - stress CTP + FFR recorded where present, report-only.
- **The validation of Stage A's signs** (thinning, fat, rest hypoattenuation) against LGE on the same patients.
  This answers the question path A can only assume.

**Committed compute on this path: ≈ 3 GPU-h** (PB-0), only once paired data exists; conditional ≈ 55 (S1).

**New evidence this round** (CPU; code in `experiments/JanusM/Kilo/`; no held-out patient read):
- [[Kilo - E4 The JA12 twin rule refuses 624 public subjects and leaves 18 open cardiac CTs]]. Ruling §6 item 7,
  done. The guard refuses 16 held-out and 624 twin subjects, leaving 18 open cardiac CTs. **Disclosure:** 29 of my
  Round 1 cases are twins. None is held out, and none is used here.
- [[Kilo - E5 Rigid registration puts first-pass borders within 0.8 mm of the late scan, and the scar rule then decides the error]].
  Tested on 14 open contrast CTs, each with a synthetic LIE carrying known scars and known motion.
  - **Unregistered borders** sit 2.8 mm off the endocardium, and the scar calls collapse (transmurality agreement
    about 0.3).
  - **Rigid registration** brings them to 0.79 mm, close to perfect alignment. Affine, heart-masking and B-spline add
    nothing; B-spline is 30× slower.
  - **With perfect borders the error is the rule's.** A 3-SD rule calls blood spill scar (specificity 0.82). FWHM and
    5-SD are specific but understate transmurality by about 10 points.
  - **The two-threshold rule** (presence by FWHM, extent by 3 SD), after rigid registration: sensitivity 0.83
    [0.78, 0.87], specificity 0.985 [0.97, 1.00], transmurality agreement 0.70 [0.62, 0.76].
- [[Kilo - E6 A paired CT-LGE cohort needs about 120 patients, and weighted kappa over all segments cannot size it]].
  Weighted κ over all 17 segments clears 0.61 at 20 patients whatever the grading error, so it cannot size the study.
  **Segment sensitivity** (lower bound > 0.75 at 95 % power) needs ≈ 120 patients. **Transmurality agreement
  among scarred segments** is the statistic that moves with grading error: 0.73 / 0.63 / 0.52 at error SD
  0.08 / 0.13 / 0.20.

**Held-out cases.** The shared JA12 guard (#138) had not landed, so I used my Round 1 `heldout.py`, extended with
the JA12 twin rule. It refuses in code, by s-number and twin, **before any public image is downloaded**: in the
fetcher, again per case, and again for the whole run in E5. **No match was opened.** The only data read about a held-out
subject is its row in the public `meta.csv`, which the twin rule needs, and no demographic of a held-out subject is written to any
committed file.

## 1. What this plan takes as given

**Base: the Janus-M master plan as amended by JA1–JA14, unchanged** for Stage A:
- four learned classes;
- equal-thickness depth;
- AHA segments from the anterior RV insertion;
- Euclidean territories from the ImageCAS-X reference tree;
- the ImageCAS-X train seal 60 and decision 40;
- reads under the half-maximum rule;
- ASSD against inter-read as the deciding metric;
- Janus-M 0 = `heartchambers_highres` + geometry;
- Janus-M 1 only if Janus-M 0 fails.

Where this plan departs from v1 (Kilo v1 proposed Laplace depth, three classes and a Taiwan seal), **the ruling
wins** and v1's proposals are withdrawn.

**Carried lead questions, as stated assumptions** (the ruling's recommendation in each case; each stays the lead's):

| | Assumed | Changes on path B if the lead decides otherwise |
|---|---|---|
| LQ1 | **B, paired scar data** (this path) | (this path is deleted) |
| LQ2 | (a) four classes, no RV myocardium | none: scar is scored on the LV only (Kim 2000; Gatti 2025) |
| LQ3 | (a) `heartchambers_highres` under its licence | S0 needs first-pass borders. Under (b) they come from a model trained on public TotalSegmentator, which E4 shows has only 18 open cardiac cases. Janus-M 1 then becomes a prerequisite of S0 |
| LQ4 | (a) ImageCAS-X train for Stage A | none on the paired cohort, which is a separate population |
| LQ5 | (a) 200 border double reads, after A39 | adds the LGE reads of §4.5, which are separate |
| LQ6 | (a) MM-WHS, low priority | none |
| LQ7 | (a) released coronary patients, training only | none |
| LQ8 | (a) the coronary seal stays as is | none |

## 2. Round 1 §6 items 1–7, settled on this path

| Item | Settlement | Evidence |
|---|---|---|
| 1. Job JM-0's numbers | **Pending the lead's run.** What each result changes is pre-registered here (§8). Path B adds one read-out: the voxels-per-third at native ImageCAS sets the LIE reconstruction requirement (§4.2: LIE slice ≤ 1.0 mm, so a third keeps ≥ 2 voxels in a 6 mm wall) | — |
| 2. One perturbation harness | **Trunk work (geometry module #139).** Path B contributes an error model measured from a real registration rather than assumed: the residual border error E5 finds after rigid registration (endocardial ASSD median 0.79 mm, 90th percentile 0.91 mm, for a 1.5 mm RMS non-rigid motion). The harness should carry it as its "LIE" error case | E5 |
| 3. Depth, sectors, territories | **Unchanged from JA2–JA4** (equal thickness, fixed 60°/90°, Euclidean). Path B's scar output does not depend on the choice: **Kim transmurality is a segment's scar volume share**, which no depth definition enters. The depth-based extent (the deepest u reached by scar) is reported beside it | Kim 2000 (bins on extent) |
| 4. Border protocol | **JA7 unchanged.** Path B adds no border read: LIE borders are never drawn. They are the registered first-pass borders. A reader passes or fails each registration on three short-axis slices (§5.3) | E5; Golf E3 |
| 5. Re-powering and margins | **JA8 unchanged for Stage A.** For path B, the paired seal is re-powered once on the 40 development patients (§4.4), by re-running `e6_power.py` with their observed sensitivity, clustering and LGE inter-reader agreement. It may only grow | E6 |
| 6. Rest TPR and the fat cut | **Report-only, as JA11.** On path B both become testable: §7 scores rest hypoattenuation and fat against LGE on the paired cohort. That replaces the "near 1.06–1.12" condition with a direct check | §7 |
| 7. The JA12 twin rule | **Done.** 16 held out, 624 twins, 18 open cardiac, on v1 `meta.csv`. The rule and its test are handed to #138 | E4 |

## 3. Path B in one table

| Part | What | Where |
|---|---|---|
| Data | Paired cohort: CCTA + LIE (one session) + CMR LGE; stress CTP + FFR where present | §4 |
| Registration | First-pass CT → LIE, rigid, Mattes mutual information over a heart crop; reader pass/fail | §5 |
| Scar step S0 | Two thresholds inside the registered wall: presence by FWHM, then Kim bin by remote + 3 SD; no training | §6.1 |
| Scar head S1 | Only if S0 fails on development: one nested class "scar ⊂ class 1", inputs LIE + CCTA + wall + depth | §6.2 |
| Metric | Presence (segment sensitivity, specificity) first; **transmurality agreement** among scar-on-both segments; against LGE | §6.3 |
| Validation of Stage A signs | Thinning, fat, rest hypoattenuation vs LGE, per segment | §7 |
| Compute | S0 on CPU; Janus-M 0 seeds on the cohort ≈ 3 GPU-h; S1 ≈ 55 GPU-h, conditional | §9 |

## 4. The paired cohort: data requirements

This section describes **data, not a request**. Whether and how such data is obtained is the lead's business, outside
the repository (D19, D31). No text addressed to anyone outside the project appears here.

### 4.1 Population

| # | Requirement | Why |
|---|---|---|
| P1 | Adults with known or suspected coronary disease and a **prior myocardial infarction** (scar-enriched), plus **≥ 30 % of patients with no LGE scar** | Specificity needs scar-free segments in scar-free patients, not only remote segments of infarct patients. E6 assumes 70 % infarct patients |
| P2 | Non-ischaemic scar (mid-wall or epicardial on LGE) **recorded and kept as a separate, report-only stratum** | Its pattern is not subendocardial; Palmisano 2020 found missed LIE scars were mostly non-ischaemic, with burden < 6 % and lower CNR |
| P3 | Patients with an infarct **< 30 days** before either scan are excluded from the transmurality validation (they may form a report-only acute stratum) | LGE infarct size falls from 18.3 % to 12.9 % of LV in the first week after reperfusion and is stable from day 7 to day 180 (Ibrahim 2010). The 30-day floor is a margin on that |
| P4 | No revascularisation, new infarct or cardiac surgery **between** the CT and the CMR | Either would change the scar between the two references |
| P5 | Every patient is new to the project, and the de-identified manifest passes the JA12 guard by patient before any image is opened | D27/D32/D33 and A14 stay sealed; no Janus-M step reads a coronary hold-out |

### 4.2 Acquisitions

| # | Scan | Requirement | Why |
|---|---|---|---|
| A1 | **First-pass CCTA** | ECG-gated, as Stage A requires (slice ≤ 0.75 mm, in-plane ≤ 0.5 mm); reconstruction phase recorded | The borders come from here (JA11, Golf E3) |
| A2 | **LIE** | Same session, **5–10 min** after contrast, **same ECG gating mode and R-R phase as A1**, slice ≤ 1.0 mm; kV, dose and reconstruction kernel recorded; dual-energy or photon-counting where available, with iodine or low-keV maps kept | Phase match keeps the non-rigid motion small, which is E5's precondition for rigid registration. Late scans at 5 min (Klambauer 2026) and 10 min (Palmisano 2022) are in use. Dual-energy raises segment sensitivity from 0.86 to 0.93 (Gatti 2025); iodine maps reach 92 % / 98 % (Ohta 2018). Low-dose LIE detects scar with sensitivity 0.53 (Bettencourt 2013), so dose is recorded and stratified |
| A3 | Non-contrast CT (optional) | If acquired | Enables CT-ECV (Nacif 2012), report-only |
| A4 | **CMR LGE** | Within **90 days** of the CT (P4 holds). Short-axis stack covering the LV, plus long-axis views; phase-sensitive inversion recovery where available; cine in the same study | The scar reference (Kim 2000; Gerber 2006) |
| A5 | Stress CTP + invasive FFR (where present) | Recorded if in the same export, with FFR within 90 days of the CTP and no intervening revascularisation | Report-only stratum for B2. The ruling folded ischaemia into B; it is not sized here |

### 4.3 Per-scan metadata (de-identified)

The following are needed per scan:
- **days relative to the index infarct and to the other scans** (offsets only, no dates);
- scanner model, kV or energy mode, reconstruction kernel, slice thickness, contrast dose, and delay after injection;
- R-R phase;
- CMR field strength and LGE sequence.

**No name, date, accession number or other identifier** enters the repository, an issue or a PR. Images go only to
the project's Girder (D19).

### 4.4 Size and split (from E6)

| Set | Size | Use |
|---|---|---|
| **Development** | **40 patients** (≥ 25 with infarct) | Choose the S0 rule and its threshold; set the registration-QC criterion; double LGE reads give the reader floor; **re-power the seal once** (`e6_power.py` with the observed parameters); train S1 if triggered (with more patients, §6.2) |
| **Paired seal** | **≥ 120 patients and ≥ 270 LGE-scarred segments**, whichever needs more patients | One look at the pre-registered acceptance (§6.3). Never used to choose anything |
| Report-only strata | acute, non-ischaemic, CTP + FFR | Reported, never deciding |

**Why 120.** In E6, a segment-sensitivity lower bound above 0.75 has 95 % power at 120 patients (about 270 scarred
segments), and transmurality agreement is known to ± 0.06. At 60 patients the power is only 0.72.

**The split is drawn by salted hash on a de-identified patient key**, development first, before any image is opened,
in the same way as JA6. It is frozen by a `role:swe` PR before any read. The seal may only grow, and only from the
pre-ranked continuation.

### 4.5 Reads on the paired cohort

| Read | Who | Cases | Blinding |
|---|---|---|---|
| **LGE**, per AHA segment: scar yes/no, pattern (ischaemic / non-ischaemic), Kim bin | CMR readers, **two independently on development, one on the seal**; adjudication of presence disagreements | all | blind to every CT |
| Registration pass/fail (§5.3) | one CT reader | all | blind to LGE |
| S1 training labels (only if S1 is triggered): voxel scar masks on registered LIE | one CT reader, with LGE shown side by side | S1 training patients only | not on the seal |

There are no first-pass border reads on the paired cohort. **S0 is scored with Janus-M 0's own borders**, so the
validation measures the pipeline as it would run.

## 5. LIE-to-CCTA registration

### 5.1 Method

- **Direction:** the first-pass CT is the moving image and the LIE scan the fixed one. Janus-M 0's segment map
  (classes, segments, depth) is resampled into LIE space with nearest neighbour.
- **Transform:** rigid (6 parameters). In E5, affine was no better than rigid (endocardial ASSD 0.78 vs 0.79 mm). A
  masked B-spline stage was no better (0.81 mm) and took 100 s instead of 3 s.
- **Metric:** Mattes mutual information (Mattes 2003), 48 bins, 15 % random sampling, on the heart crop (wall and
  cavity plus 30 mm). Intensity mapping between CCTA and LIE is not linear (bright blood becomes grey), so MI is
  used.
  - Restricting the metric to the first-pass heart (dilated 10 mm) made no difference in E5 (0.79 mm). E5's
    synthetic LIE moves the chest with the heart, which a second breath-hold need not do. **The masked variant
    is therefore the development-set arm (§8), not the default.**
- **Levels and optimiser:** three levels (shrink 4/2/1, smoothing 2/1/0 voxels); regular-step gradient descent.
  SimpleITK (Lowekamp 2013), as in `e5_lie_registration.py`.
- **Cost:** about 3 s per patient on one CPU core (E5).

### 5.2 Why not more

- **The residual is already below the error the scar rule makes.** With perfect borders, the best rule's
  transmurality agreement is 0.78. After rigid registration it is 0.70–0.73. Unregistered, it is 0.28–0.37.
- **The non-rigid component is small when the LIE is phase-matched** (A2). E5 modelled a 1.5 mm RMS non-rigid field,
  and rigid left 0.79 mm. A B-spline would chase noise in a low-CNR scan.
- **The condition for this is A2:** the same gating mode and R-R phase. If the paired data cannot meet it, the
  B-spline arm is re-tested on development (§8).
- **Limits.** E5's LIE is synthetic: real anatomy and real motion magnitudes, but label-assigned intensities (blood
  110, remote 85, scar 150 HU; noise 18 HU, so voxel CNR ≈ 3.6, near Palmisano 2020's 3.54 for detected scars). The
  public masks are 1.5 mm model-made labels. Real LIE adds beam hardening, motion blur and variable blood washout.
  The numbers rank the methods; they do not predict the paired cohort's accuracy.

### 5.3 Quality control

- **Automatic flag:** the registered wall's share of voxels brighter than the LIE blood-pool median. A misplaced
  endocardium shows as a ring of blood signal at the inner edge. The flag threshold is set on development.
- **Reader check:** pass or fail on three short-axis slices (basal, mid, apical), with the registered borders shown
  over the LIE. A fail is re-registered once with a manual initial shift. If it fails again, the patient's scar
  output is "not graded", which counts as a failure in the seal statistics, not as missing.

## 6. The scar step and the scar head

### 6.1 S0: a rule, no training

- **Where:** inside Janus-M 0's class 1 after registration (§5).
- **Smoothing:** the LIE is smoothed with a 1-voxel Gaussian.
- **Remote reference:**
  - core wall voxels, ≥ 1 voxel inside both borders, so blood, fat and lung partial volume does not enter;
  - drawn from the 6 segments with the lowest core median;
  - median and robust SD (1.4826 × MAD).
- **Two voxel rules, one for each question (E5):**
  - **Presence: FWHM.** A voxel passes if it exceeds remote + ½ (99th percentile of the brightest segment's core −
    remote). A segment is scar if ≥ 5 % of its voxels pass (Juliet E3: scar-free walls read 4–12 % under naive
    grading).
  - **Extent: remote + 3 SD**, only in segments called scar. The Kim bin is the passing share of the segment, and a
    present segment reads at least bin 1.
- **Why two.**
  - A single 3-SD rule finds 96 % of scarred segments, but also calls blood-pool spill at the endocardium scar:
    specificity 0.82 even with perfect borders, 0.82 after rigid registration.
  - FWHM is specific (0.985) but understates transmurality by 10 points: agreement 0.55.
  - Together, after rigid registration: sensitivity 0.83 [0.78, 0.87], specificity 0.985 [0.97, 1.00], transmurality
    agreement 0.70 [0.62, 0.76].
  - The rule's transmurality error SD, 0.12, is E6's middle scenario, so E6's size holds for it.
- **Fixed before development:** the FWHM and 3-SD constants and the 5 % presence share. Development may re-set them
  once, before any seal read, and the change is recorded with its development numbers.
- **Output per segment:** presence, Kim bin, scar volume share, deepest depth u reached, and territory (JA4).
  Labelled **"research, not validated"** until it passes §6.3.

### 6.2 S1: a learned scar head, only if S0 fails on development

- **Trigger:** S0 misses the §6.3 bar on the 40 development patients. Only then does the plan add a data
  requirement for S1 training patients (≥ 60 more paired patients, same requirements, never seal patients), labelled
  as in §4.5.
- **What it learns:** **one nested class**, value 5 = "scar", allowed only inside class 1. JA1's classes 1–4 are
  unchanged, and the network never draws a border. The loss is computed only inside the registered class-1 wall.
- **Inputs:** five channels on the CCTA grid:
  - the registered LIE;
  - the CCTA;
  - the class-1 mask;
  - the depth u (JA2);
  - the dual-energy iodine or low-keV map where present, zero otherwise.
- **Recipe:** nnU-Net v2 `3d_fullres` on a heart crop; mirroring off (JA9); one run on all S1 training patients
  (fold `all`), validated on development, never on the seal.
- **Labels:** voxel masks on the registered LIE, drawn with LGE shown (§4.5). **They are training labels only.** S1 is
  scored, like S0, against independent LGE segment reads, so a CT reader's habits cannot become the reference.
- **Replaces S0 only if** it beats S0 on development by a paired cluster-bootstrap CI that excludes 0 on
  transmurality agreement, with sensitivity not lower.

### 6.3 Metric and acceptance (pre-registered; on the paired seal, one look)

Scored per segment against the LGE read, with 95 % patient-bootstrap CIs:

| | Statistic | Bar |
|---|---|---|
| **Primary 1: presence** | segment sensitivity; specificity | sensitivity lower bound ≥ 0.75 **and** specificity lower bound ≥ 0.95 |
| **Primary 2: transmurality** | Kim-bin agreement among segments scar on both CT and LGE | ≥ the LGE inter-reader value on development − 0.10 (lower bound) |
| Reported | linear-weighted κ over all segments; patient sensitivity and specificity; Bland–Altman of scar share; per territory; the "not graded" rate | none |

**Why these and not κ.**
- E6: weighted κ over all segments is dominated by agreeing scar-free segments. It clears Gerber 2006's 0.61 at
  20 patients whatever the grading error.
- The transmurality bar is set against the LGE readers' own disagreement, as JA8 does for borders. Kim's bins are
  only as reproducible as the readers who apply them.
- The 0.75 and 0.95 floors sit below the pooled LIE values (sensitivity 0.86, specificity 0.98; Gatti 2025), so a
  pipeline that reads LIE as well as published readers passes.

**Margins** are fixed before any seal read and may be re-set once, on development, as JA8 does.

## 7. Validating Stage A's signs against LGE

Path A ships thinning, fat and rest hypoattenuation as unvalidated signs (JA11). Path B can test them on the
paired cohort, using the **first-pass** CCTA only (no LIE), per segment against LGE:

| Sign | Test against LGE | Analysis |
|---|---|---|
| Thinning (end-diastolic thickness, phase recorded) | transmural scar (Kim bin ≥ 3, > 50 %) | AUC, cluster bootstrap; a CT threshold set on development and tested on the seal. Shah 2013's CMR ≤ 5.5 mm is reported but not adopted |
| Intramyocardial fat (core voxels in −180 to 0 HU) | any ischaemic scar | Sensitivity and specificity at the cut-off set on development (JA11's data-driven cut) |
| Rest hypoattenuation per layer (1 mm guard band) | any ischaemic scar | AUC. Rest TPR is reported per segment only if its AUC lower bound > 0.6 here |

Sizing comes from the same 120: each sign's AUC is estimated on about 270 scarred against about 1700 scar-free
segments. Its CI is narrower than the sensitivity CI that sets the size.

## 8. What results would change this plan

| Result | Change |
|---|---|
| JM-0: walls < 5 mm or < 4 voxels per third common at native ImageCAS | Halves (JA2) also on the paired cohort; the LIE slice requirement (A2) tightens to ≤ 0.75 mm |
| JM-0: `heartchambers_highres` keeps a 0.86 mm outward epicardial bias | No effect on S0's endocardial-driven scar (E5); reported |
| Development: registration fails QC in > 10 % of patients | Compare, on development only, the heart-masked rigid (R3) and the masked B-spline (R4) arms against rigid; adopt one only if it lowers the QC failure rate without lowering transmurality agreement |
| Development: S0 misses §6.3 | Trigger S1 (§6.2) and its additional data |
| Development: LIE blood is as bright as scar (Golf's hard case) | The voxel rule needs a guard: exclude the inner voxel layer from presence (not extent), and test whether sensitivity for < 25 % scars survives |
| Development: within-patient clustering higher than E6 assumed | The seal grows (re-powering, §4.4) |
| Development: the LGE inter-reader transmurality agreement < 0.6 | Primary 2 is reported only; the decision rests on presence |
| The lead does not pursue paired data | This path is deleted (M2) |

## 9. Compute (Fir, `def-aso22`; the lead runs every job)

| Job | What | GPU-h | When |
|---|---|---|---|
| JM-0 (trunk) | As JA10 | ≤ 1 | now, as committed |
| PB-0 | Janus-M 0 seeds and geometry on the paired cohort's first-pass CCTA (≈ 160 patients) | ≈ 3 (JA10's rate: ≈ 2 per 100 cases) | when the paired data is on Girder and the split is frozen |
| PB-S0 | Registration + S0 on CPU (≈ 3 s per patient) | 0 | after PB-0 |
| PB-S1 | S1, one training run on all S1 training patients | ≈ 55 (icx4's measured 192 s/epoch × 1000 epochs at 0.5 mm; an nnU-Net epoch is a fixed 250 iterations, so a small dataset does not shorten it; a heart crop may) | only if S0 fails on development |

**No new Fir command is due this round.** PB-0's commands are JA10's Job JM-0 commands pointed at a frozen paired
manifest, written when that manifest exists. Until then they would only be a template.

## 10. Code that must ship (`role:swe`, labelled `jm/paired-scar`, opened if this plan is adopted)

1. The registration + S0 module: `e5_lie_registration.py`'s `register` (R1, with R3 as an option) and `grade`, plus `e5_hybrid.py`'s two-threshold rule,, moved into the JA2–JA4
   geometry package, with E5's synthetic case as its test.
2. The paired-cohort split and freeze: salted hash on de-identified keys, JA12 guard first; same pattern as JA6.
3. A segment-level LGE read form in the JA7 read queue: presence, pattern, Kim bin per segment, blind to CT.
4. The JA12 twin rule and its count test (16 / 624 / 18) for #138 (from E4).

## 11. The lead's questions on this path

The answer to each is a data requirement or a scope choice. None is a request to anyone.

- **PB1. Single-energy LIE.** Accept it, record kV and dose, and stratify? Or require dual-energy or photon-counting?
  **Recommend: accept, stratify.** Requiring dual-energy narrows the eligible pool. Gatti's single-energy segment
  sensitivity of 0.86 already clears the 0.75 floor.
- **PB2. Non-ischaemic scar.** Include as a report-only stratum (P2)? **Recommend: yes**, at no extra size.
- **PB3. LGE reader time.** About 40 × 2 + 120 = 200 segment-level LGE reads, at about 10 min each (an estimate),
  is about 35 reader-hours. They are by CMR readers, separate from the Stage A border reads. **Recommend: yes.**
- **PB4. The 90-day CT–CMR window.** Keep 90 days (P4 guards stability)? Or widen to 180 days if the cohort is too
  small? **Recommend: 90**. Ibrahim 2010 supports stability from day 7 to day 180, so 180 days is the fallback, not
  the default.

## 12. References

Kilo v1's list (`experiments/JanusM/Kilo/citations.md`) still holds, with JA14's corrections. New or newly used
items for v2 are below. Each was opened at PubMed or Crossref on 2026-10-30; numbers are from the abstract.

| Reference | DOI | Used for |
|---|---|---|
| Ibrahim T et al. Radiology 2010;254:88–97 | 10.1148/radiol.09090660 | LGE infarct size 18.3 % (day 1) → 12.9 % (day 7) → 11.3 % (day 35) → 11.6 % (day 180), 17 reperfused AMI patients: the ≥ 30-day floor (P3) |
| Gatti M et al. Eur Radiol 2025;35:3054–3067 | 10.1007/s00330-024-11283-5 | LIE vs LGE: segment sensitivity 0.86, specificity 0.98; dual-energy 0.93 (E6 calibration; §6.3 floors) |
| Gerber BL et al. Circulation 2006;113:823–833 | 10.1161/CIRCULATIONAHA.104.529511 | Late-enhancement CT vs CE-MR segmental concordance 82 %, κ 0.61 (E6 target) |
| Bettencourt N et al. JACC Cardiovasc Imaging 2013 (PMID 24011773) | 10.1016/j.jcmg.2013.04.013 | Low-dose CT delayed enhancement sensitivity 53 %, specificity 98 % (A2: dose recorded) |
| Ohta Y et al. Radiology 2018;288:682–691 | 10.1148/radiol.2018172523 | Dual-energy iodine images: segment sensitivity 92 % (195/213), specificity 98 % (481/491) |
| Palmisano A et al. Radiol Med 2020;125:128–136 | 10.1007/s11547-019-01108-7 | Segment sensitivity 85 % vs 62 % by reader experience; missed scars mostly non-ischaemic, burden < 6 %, CNR 2.33 vs 3.54 (P2; E5's CNR) |
| Palmisano A et al. Radiology 2022;302:545–553 | 10.1148/radiol.211288 | A late scan at 10 min added to CTA (A2) |
| Klambauer K et al. Invest Radiol 2026;61:32–40 | 10.1097/RLI.0000000000001203 | Late scan 5 min after contrast, photon-counting vs CMR (A2) |
| Dixon SN, Donner A, Shoukri MM. Stat Methods Med Res 2016;25:1260–1271 | 10.1177/0962280213476771 | Clustered kappa, design-effect adjustment (E6 cluster bootstrap) |
| Mattes D et al. IEEE Trans Med Imaging 2003;22:120–128 | 10.1109/TMI.2003.809072 | Mutual-information registration (§5) |
| Lowekamp BC et al. Front Neuroinform 2013;7:45 | 10.3389/fninf.2013.00045 | SimpleITK (§5) |
| Kim RJ et al. N Engl J Med 2000;343:1445–1453 | 10.1056/NEJM200011163432003 | Transmurality bins (Kilo v1 item 16; intermediate bins as the common convention) |
| Nacif MS et al. Radiology 2012;264:876–883 | 10.1148/radiol.12112458 | CT-ECV (A3) |
| Shah DJ et al. JAMA 2013;309:909–918 | 10.1001/jama.2013.1381 | CMR thinning ≤ 5.5 mm (§7, reported, not adopted) |

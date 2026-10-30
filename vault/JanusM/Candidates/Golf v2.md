---
tags: [janus-m, plans, candidate, round2, paired-scar, myocardium, layers, scar, LIE, LGE, registration, power]
author: Golf
round: 2
version: 2
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#143
---

# Golf v2: borders from the first pass, scar from the late scan, truth from LGE

*Path `jm/paired-scar` (LQ1 option B). A complete Janus-M plan: the Round 1 master plan (Juliet v1 + JA1–JA14) is
the base and binds; this plan settles Round 1 §6 items 1–8 on top of it.*

## 1. The plan in one paragraph

**Janus-M stays "learn the borders, compute the layers" (JA1–JA4).** Path B adds the scarring half of the brief with
a reference standard. **Scar is not a new learned class.** It is a grade **inside class 1**:
- the late-iodine-enhancement (LIE) scan is registered to the same session's first-pass CCTA;
- the first-pass borders, depth and AHA map are carried onto it;
- every segment gets a scar-presence call first, and then a Kim bin.

The first scar grader, **Scar-0**, is a fixed rule calibrated on a development set and costs no training. It is the
analogue of Janus-M 0. A learned **Scar-1** runs only if Scar-0 fails.

Everything is scored against **CMR late gadolinium enhancement (LGE)**, read per segment, on a **paired cohort**
that the project does not hold. This plan describes that cohort **only as data requirements** (D31): phases, timing,
size and fields. Sizing comes from a power simulation (E6). The registration method and the grading rule come
from E5, on real anatomy.

The Stage A signs (thinning, first-pass hypoattenuation, fat) are validated against the same LGE reads. That is the
one thing path A cannot do.

## 2. Evidence this round (CPU; code in `experiments/JanusM/Golf/`; notes in `vault/JanusM/Experiments/`)

- **E4, the guard and the twin rule (§6 item 7).**
  [[Golf - The JA12 twin rule refuses 707 of 1228 public TotalSegmentator subjects and 106 of 130 cardiac ones]]
  - `guard_r2.py` refuses JA12's full list, plus twins.
  - The ruling's twin rule refuses **707 of 1228** public subjects and **106 of 130** cardiac ids, not "a few".
  - Path B does not need those cases, so the rule stands.
- **E5, LIE-to-CCTA registration and the scar grade on real anatomy (§6 item 8).**
  [[Golf - LIE registration leaves about 0.6 mm of border error, and that error, not the threshold, limits the scar grade]]
  - Setup: 11 public hearts (a 12th pending), a synthetic bright-blood LIE scan, a known misalignment, four
    registration methods, five graders.
  - Affine registration is the default (≈ 0.6 mm residual).
  - Without a presence rule, 55 % of scar-free segments read as scar.
  - A core-presence rule that ignores the innermost millimetre gives weighted kappa 0.84, sensitivity 0.75 and
    specificity 0.99 at CNR 5. That is exactly at E6's bound, so Scar-1 is planned.
- **E6, paired-cohort power (§6 item 8).**
  [[Golf - A paired LIE-vs-LGE seal needs about 120 patients, half with scar, and segment sensitivity is what sets the size]]
  - Patient-clustered Monte Carlo with patient-bootstrap bounds.
  - Seal 120 (minimum 80) + development ≥ 40; about half with LGE scar.
- **E7, the shared perturbation harness (§6 item 2).**
  [[Golf - The Round 1 layer simulations disagree because of how they built the signed distance, and agree on realised border error]]
  - The Round 1 spread (0.909–0.975) is the signed-distance construction.
  - On realised ASSD all four recipes agree: residual SD 0.007, against 0.032 on nominal RMS.

**Held-out cases.** `guard_r2.py` (E4) runs before any case is opened. No held-out case or twin was opened this
round. One disclosure: 20 of the 24 public cases in Golf's **Round 1** E2 are refused as possible twins under the
new rule (E4). None is a held-out subject by s-number.

## 3. Assumptions carried from the ruling (LQ2–LQ8)

Each is the ruling's recommendation, held as an assumption until the lead answers.

| Q | Assumed | Effect on this plan if the lead decides otherwise |
|---|---|---|
| LQ2 | (a) LV myocardium + LV, RV, LA pools; papillary muscles in the pool | (b) adds RV wall thickness only; the scar grade stays LV only |
| LQ3 | (a) `heartchambers_highres` for Janus-M 0 and seeds, licence key typed by the lead on Fir | (b) Janus-M 1 runs early; the paired cohort's borders then come from Janus-M 1 |
| LQ4 | (a) ImageCAS-X train 560 + 180 non-sealed quality-0 | (b) pool only after #116, which leaves almost no adult CCTA; path B would then draw the border seal from the paired cohort's first-pass scans instead (§6.4) |
| LQ5 | (a) 200 border double reads after the coronary wave-1 start condition (A39) | The LGE reads (§6.2) are separate and come with the cohort, not from the team |
| LQ6 | (a) MM-WHS, low priority, external border check only | none |
| LQ7 | (a) released coronary patients for training only, by explicit PR | none (path B's scar data is institutional) |
| LQ8 | (a) keep the coronary seal as is | none |

## 4. Stage A (the trunk), with Round 1 §6 items 1–7 settled

Stage A is the master plan unchanged: JA1 classes, JA2 depth, JA3 segments, JA4 territories, JA5–JA6 data and seal,
JA7 reads, JA8 metric, JA9–JA10 models and compute, JA11 outputs. Golf settles the open items as follows.

### 4.1 Item 1 — Job JM-0's numbers

Job JM-0 has not been run yet, so no numbers exist (#130 has no JM-0 reply). Golf fixes **in advance** what each number
decides, so the reply cannot be read selectively:

| JM-0 read-out (40 cases) | Decision it triggers |
|---|---|
| Voxels per third at native spacing; share of segments with < 4 voxels per third or wall < 5 mm | > 10 % of segments → halves are the **default** report and thirds are secondary; ≤ 10 % → thirds with JA2's per-segment fallback |
| Wall thickness distribution | Median > 9 mm → the cases are not end-diastolic, or the convention includes trabeculae; ImageCAS thinning stays "phase-uncertain" (JA11), and the thinning threshold is set only on the paired cohort's LGE (§6.6) |
| Territory discordance with the AHA map | Reported against Javadi 2010 (9.3 % of segments). Under 3 % → the patient-specific map is a report, not an output |
| AHA derivation failures | > 5 % → the base and insertion rules are fixed before any table ships (Golf v1 §9) |
| **Half-maximum edge offset**, endocardial and epicardial (Hotel's R1 measure) | Epicardial offset > 0.5 mm outward → a signed correction of the seed epicardium before seeds are coarsened for reads, and Janus-M 0 must pass JA8's bias guard after the same correction |

The half-maximum offset needs code that is not in Juliet's `geometry_m0.py`. Golf asks for it in the geometry module
(#139) as one function, `halfmax_offset(ct, myo, cav)`, returning signed mm per border. Golf adds no Fir job for it.

### 4.2 Item 2 — one shared perturbation harness

**Settled by E7** ([[Golf - The Round 1 layer simulations disagree because of how they built the signed distance, and agree on realised border error]]).

`harness.py` runs each advocate's own perturbation recipe on the same 6 public hearts.

**Why the codes disagree.**
- **Hotel and Kilo** use a signed distance `edt(~m) − edt(m)`. It jumps two voxels across the border, so it
  halves a move or swallows it.
  - Hotel's nominal "0.5 mm" moves the border **0.06 mm**.
  - Kilo's moves it **0.2 mm**.
- **Golf and India** move the border 0.32–0.34 mm.

**Against the error each code realises, they all agree.** Subendocardial Dice = 1.00 − 0.31 × realised ASSD (mm).
The residual SD is 0.007, against 0.032 when plotted against nominal RMS. Correlation length (6–10 mm) does not
matter.

**The shared harness, from Round 2 on:**
- half-voxel signed distance on the analysis grid;
- smooth normal field, correlation 8 mm;
- every result reported against the **realised** ASSD;
- STA computed in the same harness.

India's reported 0.927 is not reproduced by its own recipe here (0.890), and that gap stays open.

**What it means for JA8.** JA8's margins are realised ASSD between reads, so simulation and acceptance now share
a unit. A margin of 0.15–0.35 mm (§4.5) corresponds to a subendocardial Dice of about 0.89–0.95, with Kim-bin flips
≤ 3 %.

### 4.3 Item 3 — depth, sectors, territories

- **Depth: equal thickness stays primary (JA2).** The clinical bins and the LGE reads are fractions of wall
  thickness. Yezzi–Prince is reported beside it by the geometry module on JM-0's 40 cases, at native 0.5 mm.
  Golf will switch only if the two disagree on more than 10 % of voxels **and** a reader study prefers Yezzi–Prince.
  Absent that study, the definition matching the clinical bins wins.
- **Sectors: fixed 60° / 90° from the anterior RV insertion (JA3).** Golf measured an RV-contact arc of 164°
  (R1 E2), so an arc-proportional septum would oversize segments 2, 3, 8, 9 and 14. The measured arc stays a
  per-case check.
- **Territories: Euclidean nearest vessel (JA4).** Geodesic distance along the epicardium is reported.
  - **On path B the paired cohort decides it.** For each LGE-positive segment, the territory of the culprit
    vessel is known from the scar pattern. The method whose territory more often contains that scar is adopted,
    with a paired bootstrap over patients.
  - This is the only route in the project to a reference for territories.

### 4.4 Item 4 — the written border protocol

The protocol for the `role:swe` read queue (#141), in full:

1. **Classes:** JA1. Papillary muscles and trabeculae are blood pool. The basal limit of the LV pool is the mitral
   and aortic valve planes; the LA runs to the mitral annulus.
2. **Edge rule (Hotel's half-maximum).** A border lies where the intensity is halfway between the plateaus on
   either side:
   - blood and myocardium for the endocardium;
   - myocardium and epicardial fat (or lung, or the adjacent chamber) for the epicardium.

   Code samples 3 mm profiles along the normal at every 2 mm of surface and reports the signed offset.
   - A read is **returned** if its median offset on either border exceeds 0.5 mm.
   - A read is also returned if more than 20 % of profiles are off by more than 1 mm.
3. **Seeds:** `heartchambers_highres`, resampled to 2 mm and smoothed (σ 1 mm). 10 seal cases are read from blank.
4. **Anchoring:** each wave reports seed-vs-read ASSD, read-vs-read ASSD and the share of voxels changed.
   - **Threshold:** if the median blank-vs-seeded ASSD exceeds the median read-vs-read ASSD by more than 0.2 mm
     (patient bootstrap, one-sided 95 %), seeded reads cannot accept a model.
   - In that case all seal reads go from blank.
5. **Queue specification (for #141):**
   - four labels;
   - grid: the native ImageCAS spacing;
   - read on short-axis reformats, with axial for the base;
   - two readers per case, blind to each other and to any model output beyond the coarsened seed;
   - reader id and time logged;
   - the queue refuses any case the guard refuses.

### 4.5 Item 5 — re-powering the seal, and the final JA8 margins

Fixed now, before any read. On the **first 20 decision-set double reads**:

1. Compute, per border, the per-patient read-vs-read ASSD `r` and its median `r̃`.
2. **The margin is m = clip(0.5 · r̃, 0.15, 0.35) mm.** The model may be worse than the readers by half their own
   disagreement, never by less than 0.15 mm or more than 0.35 mm. This replaces the provisional 0.25 mm.
3. The thickness margin is clip(r̃_thick, 0.3, 0.7) mm, where r̃_thick is the median read-vs-read per-segment
   thickness difference. It replaces the provisional 0.5 mm.
4. **Seal size:**
   - Let SD_d be the SD of the per-patient d = (seed-vs-read) − (read-vs-read), measured with the seed in place of
     the model.
   - Then n = ⌈((1.645 + 0.842) · SD_d / m)²⌉, which gives 80 % power for the one-sided upper 95 % bound to fall
     below m when the true d is 0.
   - The seal is max(60, n), capped at 120 (60 + the pre-registered extension 60).
   - If n > 120, the seal stays at 120 and the margin is reported as under-powered. It is never widened.
5. All of these are written into `configs/janusm/sealed-r1.json` by a PR **before** the first seal read. Seal
   numbers are never computed before that PR merges.

### 4.6 Item 6 — rest TPR at native resolution, and the fat cut-off

Both are fixed rules applied to JM-0's 40 cases. They need no new Fir job beyond JM-0, once the geometry module
outputs layer HU with the guard band.

- **Rest TPR is reported per segment only if all of these hold:**
  - in segments 1–16 of the 40 cases, the ratio uses the 1 mm guard band (Juliet R1 E2) at native spacing;
  - the median is within 1.00–1.18 (Forte 2020: septal 1.06 ± 0.06);
  - the IQR is ≤ 0.15;
  - the ratio does not change by more than 0.05 when the guard band moves from 1.0 to 1.5 mm.

  Otherwise rest TPR stays patient-level and report-only.
- **Fat cut-off:** the HU below which a core voxel (≥ 1 mm from both borders) counts as fat.
  - It is **the 0.1st percentile of core-myocardium HU pooled over the 40 cases, bounded to −180…−30 HU** (Xu
    2022's window, JA11). That is the level a fat-free myocardium reaches 1 time in 1000.
  - On path B it is re-checked against LGE: fat should sit in LGE-positive segments (Ichikawa 2009: 94 %
    subendocardial, 97 % in the infarct territory).

### 4.7 Item 7 — the twin rule

Done: E4. The rule refuses **707 of 1228** public subjects and **106 of 130** cardiac ids. Path B does not need public
TotalSegmentator data, so Golf keeps the rule as written. The shared guard (#138) should take its sha-pinned twin list.

## 5. Path B: the scar and ischaemia arm (item 8)

### 5.1 What is graded, and where

| Output | Where it is computed | Reference |
|---|---|---|
| **Scar presence** per AHA segment | LIE scan, inside first-pass borders carried by registration | LGE presence per segment |
| **Kim bin** (0 / 1–25 / 26–50 / 51–75 / 76–100 %) per segment | same | LGE Kim bin per segment |
| Scar fraction per segment × third | same | report-only (LGE is read per segment) |
| Stage A signs: thinning, first-pass hypoattenuation, fat | first-pass CCTA | LGE presence, for validation (§5.6) |
| Stress TPR / defect extent (sub-cohort only) | stress CTP, inside borders carried from rest CCTA | invasive FFR (report-only, §5.7) |

### 5.2 Registration (LIE → first-pass CCTA)

**Evidence: E5** ([[Golf - LIE registration leaves about 0.6 mm of border error, and that error, not the threshold, limits the scar grade]]).
- **Data:** 11 public hearts (a 12th pending), real anatomy and real CT.
- **The late scan:** a synthetic LIE scan with bright blood as bright as scar, misaligned by a known transform at
  three levels: none; typical (4 mm, 2°, 3 % scale, 1 mm non-rigid); large (8 mm, 4°, 6 %, 2 mm).
- **What is scored:** the first-pass CT is registered to it by four methods, and the first-pass borders are carried
  over and scored.

**Method, fixed now:**

1. **Start from scanner coordinates.** The CCTA and the LIE scan come from one session and share a frame of
   reference (§5.4 requires the DICOM geometry). Identity alone leaves ≈ 2 mm of border error at the typical level,
   so it is never used on its own.
2. **Rigid, then affine.**
   - Metric: Mattes mutual information, the first-pass CT moving and the LIE scan fixed.
   - Moving mask: the first-pass heart (classes 1–4) dilated 10 mm.
   - Three resolution levels.
   - **Affine is the default.** It gave the smallest border error and the smallest signed bias at the typical level
     (median ASSD ≈ 0.6 mm, bias ≈ +0.1 mm). It also absorbs the heart-rate / phase scale difference.
3. **B-spline (30 mm control grid) is not the default.**
   - At the typical level it was no better than affine, with a heavier tail and more outward bias.
   - It helped only at the large level.
   - It runs only for a case whose affine result fails the gate (point 5), and is kept only if it passes.
4. **What is carried.** The myocardium and cavity are carried through their signed distances; the AHA map and the
   depth u are carried by nearest neighbour. **Grading happens on the LIE grid**, so the LIE noise is never
   resampled.
5. **Gate, on the development set.**
   - Each development patient's carried borders are read once, on the LIE scan and the first-pass scan side by side.
   - Registration passes if the reader marks no segment with the carried endocardium visibly off the
     blood–myocardium edge on the first-pass overlay.
   - The share of failing patients is reported.
   - **A failing patient gets no scar call.** It is not graded with bad borders.

**Data requirement that follows.** Registration is the error that dominates the scar grade. The CCTA and the LIE
scan should be **acquired at the same ECG phase and with the same breath-hold instruction** wherever the site's
protocol allows (§5.4 records both).

### 5.3 The scar head inside class 1

**Scar is graded inside class 1, never learned as a class.**

There is no voxel-level scar reference on CT. LGE is read per segment, and CMR-to-CT voxel transfer would add its own
error, so a voxel scar class would be trained on labels nobody has. The scar head is therefore a **segment-level
grader** working on the carried borders.

**Scar-0 (no training; the default):**

1. **Remote reference:** the mid-wall third (u ∈ [1/3, 2/3)) of the 4 segments with the lowest median LIE.
2. **Scar voxel:** LIE > remote mean + k·SD, with k = 3. Juliet's half-way rule is the alternative, and the
   development set picks between them.
3. **Fraction:** T = scar voxels / myocardial voxels, per segment and per third.
4. **Presence first, from the core.** A segment is scar-present only if ≥ 5 % of its voxels are scar **after a
   1-voxel opening and outside the 1 mm next to the carried endocardium** (rule P in E5). Otherwise it is bin 0.
   - The development set may replace this with a threshold T ≥ τ, τ ∈ {0, 0.05, …, 0.30}, chosen by weighted kappa
     against LGE.
   - It does so only if τ beats P on development.
5. **Kim bin** from the full T, innermost millimetre included, for present segments only.

**Why presence comes first.**
- With exact borders the plain fraction is excellent: Kim weighted kappa 0.96 at CNR 5, presence sensitivity and
  specificity 1.0 (E5).
- After registration, the ≈ 0.6 mm residual puts bright blood inside the carried wall. Without a presence threshold,
  **half of scar-free segments are called scar** (specificity 0.47–0.64).
- The core-presence rule ignores the innermost millimetre, where carried blood lands. After affine registration
  at CNR 5 it keeps specificity at 0.99, with weighted kappa 0.84 and sensitivity 0.75 (11 hearts).
- A single τ on T, chosen on half the hearts and scored once on the other half, also restores specificity (1.00).
  But it loses small scars (sensitivity 0.58).
- This confirms Juliet R1 E3 (scar-free walls read 4–12 %) on real anatomy, and shows that **registration error,
  not image noise, is what the presence rule must absorb.**

**What E5 also shows, and what Golf therefore plans for.**
- Even the core rule's sensitivity, 0.75 at CNR 5, is **only at** the 0.75 lower bound that E6 sizes the seal for.
- At CNR 3 it falls far below that.
- **So Golf expects Scar-0 may fail on development, and plans Scar-1 now rather than hoping.**

**Scar-1 (only if Scar-0 fails the §5.5 endpoints on development; CPU):**
- **Input per segment:** the LIE profile across the wall. That is the median LIE in 10 depth bins of u,
  normalised as (LIE − remote) / (blood − remote). To it are added the segment's thickness and the registration's
  local residual (the MI gradient magnitude at the carried endocardium).
- **Model:** ordinal logistic regression over the 5 Kim bins. Gradient boosting is the fallback if the development
  set is ≥ 60 patients.
- **Training:** fitted on development LGE labels with **patient-grouped** 5-fold cross-validation. Never fitted on
  the seal.
- **Why profiles.** Blood spill from misregistration decays monotonically from the endocardium. Subendocardial scar
  is a plateau with an edge at a depth. A profile model can tell them apart where a single τ cannot. This is a
  hypothesis that only paired data can test, and Golf states it as one.

**Outputs:**
- per segment: presence, Kim bin and T;
- per segment × third: T, report-only;
- per territory (JA4): the share of its segments scar-present.

All carry "research, not validated" until the paired seal passes.

### 5.4 The paired cohort, as data requirements (no request text, D31)

These are **requirements on the data**: what a usable case contains. How the data is obtained is the lead's (D19), and
none of it is written here (D31).

**Who is in it**

| Requirement | Value | Why |
|---|---|---|
| Adults | ≥ 18 years | JA5 adult population |
| Mix | Target **about 50 % with LGE scar** (known or suspected prior infarction), the rest LGE-negative; not below 30 % either way | Specificity and the Stage A normal ranges need LGE-negative patients. E6: below 30 % scar, the seal must be much larger |
| Infarct age | Any infarct ≥ **90 days** old at both scans | Acute LGE shrinks over follow-up (16 ± 12 % → 11 ± 9 % of the LV), while chronic infarct size is reproducible (11 ± 4 % vs 12 ± 7 %) (Ingkanisorn 2004) |
| No event between scans | No infarction, PCI, CABG or cardiac surgery between the CT and the CMR | Otherwise the reference no longer describes the CT's myocardium |
| Excluded | Devices or metal that artefact the LV on either modality | Ungradeable segments |
| Non-ischaemic LGE | Kept, labelled by pattern, report-only | §6.2 |

**What each patient's CT must contain** (one session)

| Series | Requirement | Use |
|---|---|---|
| **First-pass CCTA** | ECG-gated; diastolic reconstruction with the phase (% R-R) recorded; slice ≤ 0.75 mm | Borders, depth, segments (Janus-M 0); Stage A signs |
| **LIE scan** | ECG-gated; same session; the delay after contrast (min) recorded; slice ≤ 1.0 mm, **reconstructed for CNR** (Golf R1 E3: CNR decides more than voxel size between 0.5 and 1.5 mm); dual-energy or photon-counting with low-keV or iodine maps **preferred and recorded** (dual-energy segment sensitivity 0.93 vs 0.86 pooled, Gatti 2025) | Scar grade (§5.3) |
| Both series | Original DICOM, unmodified geometry: `ImagePositionPatient`, `ImageOrientationPatient`, `FrameOfReferenceUID`, table position, acquisition time | Scanner coordinates are registration's start (E5); the time gap is a covariate |
| Optional: non-contrast + haematocrit | Same session | ECV (Stage B, report-only) |
| Optional: stress CTP | With invasive FFR within 90 days, no intervening revascularisation | Ischaemia sub-cohort (§5.7) |

**What each patient's CMR must contain**

| Requirement | Value |
|---|---|
| Timing | Within **90 days** of the CT, either order |
| LGE | Short-axis stack covering the LV base to apex, plus 2-, 3- and 4-chamber long axes; field strength, sequence and delay recorded |
| Reads | §6.2: two readers, per AHA segment, presence + Kim bin + pattern, blind to CT |

**Per-patient fields** (no identifiers, no dates):
- a project pseudonym;
- age in 5-year bands and sex;
- scanner model, kV or keV, contrast dose;
- LIE delay and heart rate at each acquisition;
- the CT–CMR interval in days;
- the infarct age in days, if known;
- the culprit or revascularised vessel, if known (used for the territory check, §4.3).

**Form.**
- De-identified before it reaches the project, with no burned-in text (PLOS-Peng2016 is refused for exactly this).
- Stored only in a restricted collection on the project's Girder, never in a public one, and never committed.
- The shared guard registers the cohort as a new source, and its seal list is frozen before grading (§6.3).

### 5.5 Size and power

From **E6** ([[Golf - A paired LIE-vs-LGE seal needs about 120 patients, half with scar, and segment sensitivity is what sets the size]]).

The study is a Monte Carlo of whole studies with patient-clustered errors and patient-bootstrap CIs. **Endpoints on
the paired seal, one look, each judged on the lower 95 % bound:**

| Endpoint | Bound | Expected (point) |
|---|---|---|
| **Segment sensitivity for scar presence** (ischaemic-pattern LGE) | ≥ 0.75 | ≈ 0.84 |
| Segment specificity | ≥ 0.93 | ≈ 0.975 |
| Linear-weighted kappa of the Kim bin, all segments | ≥ 0.60 | ≈ 0.85 |

- **Sensitivity sets the size.** Specificity and kappa pass from 60 patients.
- **Power to pass all three, at 50 % enrichment:** 0.62 at 60 patients, **0.80 at 80**, 0.87 at 100, **0.89 at 120**.
- **Harder conditions:**
  - small infarcts (λ 1.5): 0.79 at 120;
  - 30 % enrichment: 0.78 at 120;
  - strong within-patient clustering (τ 1.2): 0.57 at 120.

**Required:**
- **paired seal 120** (minimum 80; below 80, no seal claim);
- **development ≥ 40**;
- **target total ≈ 160 patients, about half with LGE scar and at least 30 % scar-free.**

The seal size is **re-powered once from the development set** before any seal patient is graded:
- the measured τ, segments per scar patient and bin mix are put into `cohort_power.py`;
- the seal may grow, and never shrinks.

The meta-analytic average study has about 38 patients (Gatti 2025: 526 / 14). Under these assumptions that is
roughly a coin flip, which is why path B asks for three times that.

### 5.6 Validating the Stage A signs against LGE

On the same paired cohort, each Stage A sign is tested against LGE presence per segment:
- thinning, the segment thickness relative to the patient's own remote segments;
- first-pass hypoattenuation, the subendocardial-third HU relative to remote, with the 1 mm guard band;
- fat present, by the §4.6 cut-off.

Each gets an ROC AUC with a patient-bootstrap CI and a sensitivity/specificity at a cut-off fixed on the development
set. A Stage A sign loses its "not validated" label only if it passes on the paired seal:
- lower 95 % AUC bound ≥ 0.70;
- that is the only change.

This is how path B answers the brief's "scarring" for patients who have **no LIE scan**. Path A cannot answer it.

### 5.7 Ischaemia (secondary, not powered)

Stress CTP with invasive FFR is a **sub-cohort where present**, not a requirement. Path B does not size for it:
- Stress TPR is computed inside borders carried from the rest CCTA, by the same registration (§5.2).
- It is reported per territory against FFR ≤ 0.80.
- Beam-hardening correction is required before any TPR (Kitagawa 2010; So 2016).

Nothing ischaemia-related is a deciding output on this path until a sub-cohort of at least the §5.5 size with FFR
exists.

## 6. Data, seals and reads on path B

### 6.1 Images

| Set | Source | Use |
|---|---|---|
| Border seal 60, decision 40, JM-0 40 | ImageCAS-X train (JA5–JA6) | Stage A borders, as on the trunk |
| **Paired development set** | institutional paired cohort, §5.4 | Calibrates Scar-0, registration settings, Stage A cut-offs, and Scar-1 if triggered |
| **Paired seal** | the same cohort, drawn at intake | Scored once against LGE |
| External, report-only | as JA5 | — |

### 6.2 LGE reads (the scar reference)

- Two independent LGE readers per patient, blind to the CT.
- Per AHA segment (1–17): presence, Kim bin and pattern (subendocardial or transmural = ischaemic; mid-wall,
  epicardial or patchy = non-ischaemic).
- Disagreements are resolved by consensus. The **inter-reader weighted kappa is reported as the ceiling** that
  Janus-M is measured against.
- Primary endpoints use **ischaemic-pattern segments**; non-ischaemic patterns are report-only.

### 6.3 The paired draw

- At intake, each patient is assigned to development or seal by `sha256('asclepius-janusm-paired-r2:' + pseudonym)`.
- The seal takes the first n_seal (§5.5), and the rest go to development.
- The lists are frozen in `configs/janusm/paired-r2.json` by a `role:swe` PR **before any LIE image of a seal patient
  is graded**, and the shared guard refuses seal patients in every development step.
- **The seal is scored once.**

### 6.4 If the lead decides LQ4 (b)

The border seal can be drawn from the paired cohort's first-pass scans instead. Path B then needs no ImageCAS at all.
The cost is that border reads compete with LGE work for the same patients.

## 7. Models in reading order

| Model | What | Trained? | When |
|---|---|---|---|
| **Janus-M 0** | `heartchambers_highres` + geometry module | No | Trunk; decided on the border decision set |
| Janus-M 1 | nnU-Net v2 ResEnc, JA1 classes, 0.5 mm, mirroring off | Only if Janus-M 0 fails JA8 | Trunk |
| **Scar-0** | §5.3 rule on registered LIE | No (calibrated on development) | When the paired cohort exists |
| Scar-1 | §5.3 learned segment grader | Only if Scar-0 fails on development | Same |

## 8. Compute (Fir, `def-aso22`; the lead runs every job; Golf runs nothing on SciNet or Alliance)

| Job | GPU-h | When |
|---|---|---|
| JM-0 (trunk; Juliet v1 §7 as committed) | ≤ 1 | Now |
| Seeds on seal + decision (trunk) | ≈ 2 | After the freeze PR |
| **PB-1: `heartchambers_highres` on the paired cohort's first-pass scans** | ≈ 0.02 per patient (≈ 1 min) → ≈ 3 for 150 | When the cohort is on Girder |
| **PB-2: registration + Scar-0 on development** | 0 (CPU; E5 took ≈ 15–45 CPU-min per patient for all four methods, ≈ 2 min for rigid + affine alone) | After PB-1 |
| PB-3: Scar-1 (segment grader) | 0 (CPU) | Only if Scar-0 fails on development |
| Janus-M 1 (conditional, trunk) | ≈ 55 | Only if Janus-M 0 fails |

**Committed on path B beyond the trunk: ≈ 3 GPU-h**, and only once the cohort exists. Exact PB-1/PB-2 commands are
written when the cohort's Girder layout is known. Golf will not guess paths for data that does not exist.

## 9. What would change this plan

| Result | Change |
|---|---|
| The lead keeps path A | This branch is deleted; E4, E7 and §4 carry to the trunk unchanged |
| The paired cohort is smaller than §5.5's minimum | Scar outputs stay research outputs; the cohort becomes development-only, and no seal claim is made |
| Affine registration fails the §5.2 gate in > 10 % of development patients | B-spline for the failing cases; if still > 10 %, the data requirement on same-phase, same-breath-hold acquisition becomes mandatory, and a failing patient gets no scar call |
| Scar-0's calibrated sensitivity < 0.75 on development (E5 predicts it may be) | Scar-1 (§5.3) is fitted on development and replaces Scar-0 before the seal is graded |
| LGE inter-reader kappa < 0.6 | The scar reference itself is too noisy for Kim bins; the endpoint drops to presence only |
| A Stage A sign passes §5.6 | It loses the "not validated" label for LGE presence |
| Twins: the lead wants public TotalSegmentator data back | A tighter twin rule (E4, item 3), by the lead's decision |

## 10. The lead's questions on this path

The path-B questions are numbered **PB-Q1 …**. LQ2–LQ8 are carried (§3).

- **PB-Q1 (cohort).** Does the project pursue an institutional paired cohort to the §5.4 data requirements?
  Recommended: **yes**; it is LQ1 option B made concrete. Access is the lead's, outside the repository (D19, D31).
- **PB-Q2 (size).** Accept §5.5's minimum as the threshold below which no seal claim is made? **Recommended: yes.**
- **PB-Q3 (LGE reads).** Are LGE reads per segment (two readers, Kim bins, pattern) taken from clinical reports or
  read fresh? **Recommended: read fresh by two readers blind to CT**, because clinical reports rarely give Kim bins
  per segment.
- **PB-Q4 (ischaemia).** Treat stress CTP + FFR as an optional sub-cohort, not a requirement? **Recommended: yes.**
- **PB-Q5 (twins).** Keep JA12's twin rule as written (E4)? **Recommended: yes** on this path.

## 11. References

Golf's Round 1 list (`experiments/JanusM/Golf/citations.md`, 54 entries) carries over. JA14's corrections bind:
- Mushtaq 2023 is a **post-PCI** cohort;
- Cerqueira 2002's territory figure is **unverified** (secondary sources only);
- the MRI comparison is **Nieman 2008**;
- Treibel 2015 is in *J Cardiovasc Comput Tomogr*;
- no numeric MM-WHS CT myocardium Dice;
- the −10 HU fat cut is unsourced (the −180…0 HU window is Xu 2022's).

**New or newly relied on this round:**

| Entry | Verified at | What is used |
|---|---|---|
| Gatti M, et al. Diagnostic accuracy of late iodine enhancement on cardiac CT for myocardial tissue characterization: systematic review and meta-analysis. *Eur Radiol* 2025;35:3054-3067. doi:10.1007/s00330-024-11283-5 | PubMed 39702631, abstract | 14 studies, 526 patients, 5758 segments; segment sensitivity 0.86 (0.79–0.91), specificity 0.98 (0.96–0.99); patient-level 0.96 / 0.95. The dual-energy segment sensitivity of 0.93 is from Golf's R1 reading of the same abstract |
| Ingkanisorn WP, Rhoads KL, Aletras AH, Kellman P, Arai AE. Gadolinium delayed enhancement cardiovascular magnetic resonance correlates with clinical measures of myocardial infarction. *J Am Coll Cardiol* 2004;43:2253-2259. doi:10.1016/j.jacc.2004.02.046 | PubMed 15193689, abstract | Acute infarct size 16 ± 12 % → 11 ± 9 % on follow-up; chronic size reproducible, 11 ± 4 % vs 12 ± 7 %. Basis of the ≥ 90-day infarct-age requirement (§5.4) |
| Kim RJ, et al. *N Engl J Med* 2000;343:1445-1453. doi:10.1056/NEJM200011163432003 | R1 | Kim bins |
| Mahnken AH, et al. *Eur Radiol* 2010;20:2834-2843. doi:10.1007/s00330-010-1864-x | R1 | Fused CCTA + late-CT workflow; 10 / 96 segments territory-discordant |
| Javadi MS, et al. *J Nucl Med* 2010;51:198-203. doi:10.2967/jnumed.109.067488 | R1 | 9.3 % of segments reassigned (§4.1) |
| Forte E, et al. *Clin Physiol Funct Imaging* 2020;40:30-36. doi:10.1111/cpf.12598 | R1 (judge-confirmed) | Septal rest TPR 1.06 ± 0.06 (§4.6) |
| Ichikawa Y, et al. *JACC Cardiovasc Imaging* 2009;2:548-555. doi:10.1016/j.jcmg.2009.01.010 | R1 (judge-confirmed) | Fat in 62 % after MI; 94 % subendocardial (§4.6) |
| Kitagawa K, et al. *Radiology* 2010;256:111-118. doi:10.1148/radiol.10091399; So A, et al. *Med Phys* 2016;43:4821. doi:10.1118/1.4957389 | R1 | Beam-hardening correction before stress TPR (§5.7) |
| Xu 2022 (fat window −180…0 HU) | Hotel R1, judge-confirmed | §4.6 bounds |
| Yezzi AJ, Prince JL. An Eulerian PDE approach for computing tissue thickness. *IEEE Trans Med Imaging* 2003;22:1332-1339. doi:10.1109/TMI.2003.817775 | bibliographic record | The alternative depth named by JA2 (§4.3) |
| TotalSegmentator v1 / v2.0.1 metadata: Zenodo 10.5281/zenodo.6802614 and 10.5281/zenodo.10047292 (`meta.csv`), CC BY 4.0 | read directly, sha256 in `guard_r2_twins.json` | E4 |

**Not cited, on purpose.** The breath-hold misalignment levels in E5 (4 mm / 8 mm) are **assumptions**. Golf found
diaphragm-position studies but could not open a primary source that measures heart position between breath-holds,
so none is cited.

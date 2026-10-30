---
tags: [janus-m, plans, candidate, round2, path-rest-ccta, myocardium, layers, AHA17, TPR, calibration]
author: Hotel
round: 2
version: 2
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#142
---

# Hotel v2: rest CCTA only. A geometry table beside the artery, with every threshold above its own noise floor

**The position in one line.** On path A, Janus-M can never say "scar". What it can say honestly is that a segment's
geometry or attenuation lies **outside this population's range by more than two reads disagree**, and in which
artery's territory. Hotel v2 builds the table that says exactly that, and nothing more, and it calibrates every flag
for specificity against measurement noise and population spread. Without a scar reference, sensitivity cannot be
calibrated at all, and the plan says so.

**Base.** The master plan as it stands: [[Juliet v1]] with JA1–JA14 ([[Janus-M Round 1]]). Hotel v2 changes none of
its structure:
- learned borders: LV myocardium, LV, RV and LA pools;
- computed layers, segments and territories;
- the ImageCAS-X train seal and decision set;
- Janus-M 0 = `heartchambers_highres` + geometry;
- Janus-M 1 only if Janus-M 0 fails.

Hotel v2 settles Round 1 §6 items 1–7 and 9 for path A, with five new CPU experiments:
- **E1** [[Hotel - The twin rule refuses 695 public TotalSegmentator subjects and leaves 23 cardiac studies, and Round 1 used exact matches]]
- **E2 + E4** [[Hotel - Round 1's four border-error curves differ because their distance maps move the border by different amounts]]
- **E3** [[Hotel - Rest TPR with a 1 mm guard band is unbiased at 0.5 mm only while the blood-myocardium edge stays under about 1.5 mm]]
- **E5** [[Hotel - Equal-thickness thirds match Yezzi-Prince on 98 percent of a phantom wall, raw Laplace isolines on 86 percent]]

The code is in `experiments/JanusM/Hotel/r2/` and `experiments/JanusM/Hotel/guard_r2.py`.

**Held-out cases.**
- **This round:** no coronary-sealed, reserve, D35, A14, val-80 or ImageCAS-X-test case was read.
- **Guard first.** The guard (`guard_r2.py`) was written and run before anything public was touched.
- **No images opened.** Every Round 2 experiment is synthetic. The only public files read are the two
  TotalSegmentator `meta.csv` metadata tables.
- **Disclosed.** E1 found that Hotel's Round 1 E1 used two public subjects, s0767 and s0848. Each matches a held-out
  subject on age, sex, institute and study type. That is no more than chance predicts (E1), but the twin rule
  refuses both. Details are in §8.

---

## 1. The plan in one paragraph

Janus-M 0 (`heartchambers_highres` + the JA2–JA4 geometry) runs on rest CCTA and produces two tables per patient:
- **Table A:** the 17 segments × 3 transmural layers (halves in thin walls);
- **Table B:** a roll-up per Janus artery (LAD, LCx, RCA).

Table B is placed beside the reader's stenosis grade for the same artery. Each cell carries measurements and, where
earned, a **flag**. A flag fires only when **both** of these hold:
- **(F1) Beyond read noise.** The value differs from the patient's own remote segments by more than the repeatability
  coefficient of two independent border reads (E4: 0.74 mm of thickness at 0.25 mm read noise; recomputed on the
  first 20 decision double reads).
- **(F2) Outside the reference interval.** The value lies outside the 2.5–97.5 % interval of the same segment in the
  ImageCAS-X training population, by sex, frozen before any seal read.

Signs combine into **one composite pattern** ("chronic-infarct-like geometry") so that a patient's 16 segments × 3
signs do not produce a false flag in most patients (§4.3). Rest TPR enters the table per segment **only** if Job
JM-0's add-on shows a sharp enough edge and an unbiased endocardium (E3). Otherwise it stays per territory and
report-only. Every output is labelled "research, not validated: no scar or perfusion reference" (JA11).

## 2. What changes from Hotel v1

| Hotel v1 | Hotel v2 | Why |
|---|---|---|
| Pool-41 seal (CCA200-HF, PLOS-Peng) | **Withdrawn.** ImageCAS-X train seal 60 / decision 40 (JA5, JA6) | Ruling §2.4 |
| Pretraining on TotalSegmentator v1 | **Withdrawn** (JA9). E1 adds that only 23 cardiac v1 studies survive the twin rule | E1 |
| Raw Laplace thirds | **Equal thickness** (JA2). Raw Laplace isolines are dropped from every output | E5: they agree with Yezzi–Prince on 86 %; equal thickness on 98 % |
| "Per-segment TPR ships at ASSD ≤ 0.5 mm" | **Withdrawn.** Hotel's own error model moved the border only 0.03 mm at "0.5 mm" | E2 Part A |
| Thinning flags at < 5.5 / 5 / 3 mm | **No borrowed cut.** Flags come from F1 + F2 | E4; JA11; the 9.5–9.7 vs 5.7 mm gap (§4.4) |
| Scar outputs "labelled unvalidated" | Kept, and made operational: what may and may not be said (§3.3) | Path A |
| Kept from v1 | The half-maximum border rule (JA7); the endo/epi half-maximum offset read-out; the partial-volume caution on rest TPR | Ruling |

## 3. Path A's deliverable: what the table gives a reader beside Janus's stenosis

### 3.1 What sits on the other side of the page

**Janus is a four-class coronary *lumen* segmentation** (D25: LM, LAD, LCx, RCA). The project has no stenosis grader:
- no diameter profile;
- no CAD-RADS computation.

So "Janus's stenosis report" is, today, **the reader's own per-artery stenosis grade, read with Janus's lumen in
view**. Janus-M's join key is therefore **the artery**, not a stenosis number:
- Janus's LAD, LCx and RCA define each segment's patient-specific territory (JA4);
- Table B lists those three arteries;
- the stenosis column is filled from the read, or from a future stenosis tool if the coronary plan builds one.

Janus-M grades no stenosis, and Path A needs no stenosis tool to function. Whether the project should build one is a
coronary-plan matter, carried to the lead as **LQ-H1** (§6).

### 3.2 The two tables (per patient)

**Header (QC, always shown):**
- reconstruction phase, if recorded (ImageCAS: "phase unrecorded"; every thickness then carries
  "phase-uncertain");
- in-plane and z spacing;
- the measured endocardial 10–90 % edge width and the endocardial and epicardial half-maximum offsets of the borders
  used (§5.4);
- whether AHA orientation passed (JA3), and the septal arc;
- the territory source: ImageCAS-X reference tree, or Janus 0 on a Janus-M-allowed case (JA4).

**Table A: segment × layer** (17 rows; thirds, or halves where JA2 requires; segment 17 is a single layer):

| Column | Per | Content |
|---|---|---|
| Thickness (mm) | segment | Median equal-thickness wall thickness over the mid-third voxels; percentile in the reference interval (F2) |
| Thinning | segment | Flag only if F1 and F2 both hold |
| Rest attenuation (normalised) | layer | Core HU ≥ 1 mm from either border ÷ the patient's remote median; septum normalised separately |
| Hypoattenuation | layer | Flag only if F1 (measured from the reads' HU repeatability) and F2 |
| Core fat (mm³) | layer | Volume of core voxels in −180 to 0 HU and below the patient's noise floor, in clusters ≥ 3 voxels (§5.6) |
| Rest TPR | segment | Guarded (1 mm). **Shown only if E3's rule passes on JM-0 (§5.6);** otherwise blank, with the reason |
| Territory | segment | Patient-specific majority artery and its share; **"shared"** if the share < 0.6; the AHA default beside it |
| Pattern | segment | "Chronic-infarct-like geometry" if thinning **and** (subendocardial core fat **or** subendocardial hypoattenuation) |

**Table B: per Janus artery** (LAD, LCx, RCA):

| Column | Content |
|---|---|
| Stenosis (reader) | The reader's grade for this artery, copied, not computed |
| Territory mass (g) | Myocardial mass in the patient-specific territory (density 1.05 g/ml), and its share of LV mass. Precedent: Kurata 2015 (Voronoi territories vs SPECT, r up to 0.814); Ide 2017 (swine histology, r 0.92–0.96) |
| Segments | The segments assigned, with "shared" segments listed apart |
| Flags | Count and list of flagged segments by sign; the pattern segments |
| Concordance | One of four fixed phrases (§3.3) |

### 3.3 What a reader may and may not take from it

| Situation in one artery | Fixed phrase in Table B | What it supports | What it does **not** say |
|---|---|---|---|
| Stenosis graded significant, **pattern present** in its territory | "Territory shows chronic-infarct-like geometry" | Prior infarction in that territory is plausible. A viability question (CMR) may be worth asking before revascularisation | Not scar. Thinning alone does not exclude recovery: in Shah 2013, 18 % of thinned regions had ≤ 50 % scar, and thickness recovered from 4.4 to 7.5 mm after revascularisation |
| Stenosis significant, **no flag** | "No geometric sign in territory" | Nothing. Rest geometry is normal in most stenoses | Not "no ischaemia" and not "no scar". Path A has no sensitivity estimate |
| **Pattern present**, no significant stenosis | "Geometric sign without graded stenosis" | A reason to re-look: a missed or occluded vessel, a territory-assignment error (check "shared"), or a non-coronary cause | Not a diagnosis of anything |
| Flags scattered, no pattern | "Isolated measurements outside range" | Nothing on its own (§4.3: expected by chance in about one patient in three) | — |

Two further outputs give a stenosis read context:
- **Territory mass (myocardium subtended)**, which Path A can deliver on every patient without a scar reference;
- **the "shared" warning**, which marks segments where the AHA default and the patient's own tree disagree.
  Ortiz-Pérez 2008: 23 % of infarcted segments did not match the standard artery.

### 3.4 An illustrative Table B

This example is **synthetic**: the numbers are made up for layout only.

| Artery | Stenosis (reader) | Territory mass | Segments (shared) | Flags | Concordance |
|---|---|---|---|---|---|
| LAD | 70–99 % proximal | 58 g (44 %) | 1, 2, 7, 8, 13, 14, 17 (16 shared) | thinning 13, 14; subendo fat 14 | Territory shows chronic-infarct-like geometry (14) |
| LCx | < 50 % | 37 g (28 %) | 5, 6, 11, 12 | none | No geometric sign in territory |
| RCA | 50–69 % | 37 g (28 %) | 3, 4, 9, 10, 15 | hypoattenuation 9 | Isolated measurements outside range |

## 4. Calibrating Stage A signs without a scar reference

### 4.1 What can and cannot be calibrated

With no LGE, no histology and no follow-up:
- **sensitivity and PPV for scar cannot be estimated, and Path A never states them.**
- **What can be calibrated is specificity in two senses:**
  - **against measurement noise**: a flag must not be produced by the readers' own disagreement (F1);
  - **against population spread**: a flag must be rare in the population the model sees (F2).
- **Literature values are anchors that check the measurement, not thresholds** (F3).

### 4.2 The three floors, in the order they are fixed

**F1. Measurement floor.**
- **What it is:** the repeatability coefficient (RC = 1.96 × √2 × single-read SD; Bland & Altman 1986) of each sign
  per segment.
- **When it is fixed:** from the **first 20 decision-set double reads**, the same reads that re-set JA8's margins.
  Before then, E4's model values are placeholders only:

  | Read-vs-read border noise | RC of segment thickness |
  |---|---|
  | 0.25 mm | 0.74 mm |
  | 0.5 mm | 1.60 mm |
- **For attenuation:** RC comes from the two reads' guarded layer HU on the same scan.
- **The rule:** a segment's deviation from the patient's remote median must exceed RC. "Remote" means the median of
  the segments outside the territory under test, or of all segments if no territory is under test.

**F2. Population reference interval.**
- **Population:** the 2.5th and 97.5th percentile per segment and sex, computed on ImageCAS-X **training** cases with
  Janus-M 0 outputs. It never uses the seal or the decision set.
  - **The pool:** the 420 train cases left after the draw (seal 60, decision 40 and JM-0 40 removed). JM-0's 40
    stay outside F2 as its calibration check.
  - **Seeds:** `heartchambers_highres` seeds on the 740 (the conditional ≈ 12 GPU-h in JA10).
- **Labelling:** ImageCAS's population is patients referred for CCTA, not healthy volunteers, and its phase is
  unrecorded. The interval is therefore labelled **"this population, phase-uncertain"**, never "normal".
- **When it is fixed:** frozen in `configs/janusm/reference-r2.json` before any seal read. The seal is scored once,
  and the intervals are never refitted on it.

**F3. Literature anchors, as checks on the measurement and not as thresholds.**
- **Wall thickness:** the F2 median should be near CT normals (Chen 2025, end-diastole). The Round 1 open labels gave
  9.5–9.7 mm against 5.7 mm (JA11). A gap above 2 mm at the median means the thickness *definition* differs from
  the reference's (for example including trabeculae, or phase), and §4.4 applies before any flag ships.
- **Core fat:** the share of patients with any core fat should be in single digits. Ichikawa 2009: 3 % of controls,
  62 % after MI. A share far above that means the fat rule is counting partial volume.
- **Guarded rest TPR:** the population median should sit near the published normal mean 1.12 (George 2009). If
  shown per segment, its F2 lower limit replaces George's < 0.99 cut, because the guard changes the ratio's
  definition (E3: a true 1.10 reads 1.08–1.09 guarded).

### 4.3 Why one composite pattern, not many single flags

With 16 segments and a flag rate of 2.5 % per segment (F2's lower tail):
- **one sign** gives P(≥ 1 false flag in a patient) = 1 − 0.975¹⁶ = **33 %**;
- **three signs** give about **70 %**, if independent.

A table that flags two of every three patients is noise. So:
- **single-sign flags are shown** in Table A, but Table B calls them only "isolated measurements outside range";
- **the composite pattern** needs thinning **and** a subendocardial sign (fat or hypoattenuation) in the **same
  segment**:
  - if the signs were independent, the per-segment rate would be about 0.025 × 0.05 ≈ 0.1 %, so about 2 % per
    patient;
  - **the measured rate is what is reported.** On the F2 population the pattern's rate per patient is computed, and
    if it exceeds 5 % the pattern requires two contiguous segments.

The three signs co-occur in chronic infarction:
- thinning and hypoattenuation: Nieman 2006, long-standing MI at −13 ± 37 HU against 73 ± 14 HU in controls, with
  thinning;
- subendocardial fat: Ichikawa 2009, 94 % subendocardial.

This is a construct argument for the composite, not a validation of it.

### 4.4 The thickness-definition check (before any thinning flag ships)

The open-label walls (9.5–9.7 mm) are far from CT end-diastolic normals (5.7 mm; Chen 2025, which also gives 6.5 mm
at mid-diastole). Until Job JM-0's native-resolution thickness is known, the plan **does not assume either is
right.** The rule:
- if the JM-0 median is within 1.5 mm of 5.7–6.5 mm, the definitions agree and F3 holds;
- if not, the readers measure thickness by hand on the first 20 decision cases, along the short-axis normal at three
  mid-ventricular segments, and Janus-M's definition is aligned to theirs before F2 is computed.

### 4.5 Construct checks: reported, never tuned on

On the F2 population and the decision set, these are reported:
1. **Spatial coherence.** Pattern segments should be contiguous and lie mostly in one territory. Report the share of
   patients whose pattern segments lie in one patient-specific territory, against a permutation null that shuffles
   segment labels.
2. **Endocardial predominance.** Fat and hypoattenuation flags should be subendocardial more often than
   subepicardial (Ichikawa 2009: 94 % subendocardial). An even split points to a measurement artefact.
3. **Stenosis concordance**, where reader grades exist: the pattern rate in territories of arteries graded ≥ 70 %
   against < 50 %. It is reported as an odds ratio with a CI, and **never used to set a threshold** (that would make
   the stenosis read the reference, which it is not).

## 5. Round 1 §6 items 1–7, settled for path A

### 5.1 Item 1: Job JM-0's numbers

- **Status.** They are not back yet: no comment on #142 or #130 carries them as of 2026-10-30.
- **The plan is written as decision rules on those numbers** (§9), so a later round applies them without
  re-arguing.
- **The add-on.** Hotel adds one **CPU** step to JM-0, after it (§7). It reads the same 40 cases, the same seeds and
  the same CT, and returns aggregates only:
  - the endocardial and epicardial half-maximum offsets (the "0.86 mm" question);
  - the 10–90 % edge widths;
  - the blood, core-myocardium and fat plateaus;
  - guarded and unguarded rest TPR per segment (free wall and septum apart);
  - the core-HU histogram for the fat cut-off.

### 5.2 Item 2: one shared perturbation harness

E2 answers it. All four Round 1 models share one recipe and differ only in how their distance maps turn noise into
border movement. Under the same nominal "0.5 mm", they move the border 0.29 (Golf), 0.19 (India), 0.17 (Kilo) and
0.03 mm (Hotel). One line fits all of them and the new harness: subendocardial Dice ≈ 0.998 − 0.38 × achieved mean
|d|, R² 0.95, residual by source ≤ 0.01.

**Adopted harness** (`r2/e2_harness.py`, Part B):
- a continuous SDF on the native grid;
- independent endocardial and epicardial fields, with an 8 mm smoothing default;
- constant biases;
- STA computed inside it;
- **achieved displacement reported with every result.**

It should become the test fixture of the JA2–JA4 geometry module (#139), so that the module's outputs are always
quoted against achieved, not nominal, error.

### 5.3 Item 3: depth, sectors and territories

- **Depth.** Equal thickness stays primary (JA2). On the E5 phantom:
  - it agrees with Yezzi–Prince on 98.5 % of voxels (96 % in a 4–5 mm wall), with thickness within 0.1–0.2 mm;
  - raw Laplace isolines agree on 84–86 % and shrink the inner third to about 20 % of the wall.

  Yezzi–Prince is not worth its cost, and Laplace isolines are not reported as thirds.
- **Sectors: fixed 60° / 90° from the anterior RV insertion stay primary** (JA3), because they are what Cerqueira
  2002 defines. Arc-proportional septal sectors are reported beside them only as the measured septal arc (JA3
  already requires it). Path A adds no third option.
- **Territories: Euclidean nearest-vessel stays primary** (JA4). Each segment carries its **majority share**, which
  `geometry_m0.py` already computes, and a segment with share < 0.6 is shown as **"shared"** (§3.2).
  - Geodesic assignment is not built on path A. It changes the answer only near territory borders, which "shared"
    already marks.
  - If JM-0 shows that more than 20 % of segments are "shared", the next round compares geodesic assignment on those
    segments only.

### 5.4 Item 4: the written border protocol (JA7) and the read queue

**Protocol, version 1.** It applies to every Janus-M read, seal and decision alike.

1. **Labels (JA1):** 1 LV myocardium; 2 LV blood pool; 3 RV blood pool; 4 LA blood pool. Nothing else is drawn.
2. **Papillary muscles and trabeculae are blood pool (label 2).** The endocardium is the compact-wall surface. Where
   trabeculae merge with the compact wall, the border goes at the outer edge of the blood-filled recesses.
3. **The half-maximum rule.**
   - **Where the border lies.** Each border lies where HU is halfway between the two adjacent plateaus:
     - endocardium: LV blood vs core myocardium;
     - epicardium on the free wall: core myocardium vs epicardial fat;
     - epicardium on the septum: core myocardium vs RV blood.
   - **Window.** The read tool shows a window centred on the half-maximum value for the case: level =
     (plateau₁ + plateau₂) / 2, width ≈ 1.5 × |plateau₁ − plateau₂|. The plateaus are computed from the seed (§5.1)
     and shown on screen.
   - **Code check on every submitted read.** It computes the read's own half-maximum offsets (`halfmax_tpr_m0.py`'s
     method):

     | Read's offset | Action |
     |---|---|
     | ≤ 0.5 mm | accepted |
     | 0.5–1.0 mm | accepted, with a warning |
     | > 1.0 mm | returned to the reader once, with the offending border highlighted |
4. **Basal limits.** The LV pool ends at the mitral annulus plane and at the aortic valve plane. Myocardium above the
   mitral annulus is not labelled. The LA (label 4) runs to the mitral annulus, and the pulmonary veins and appendage
   are excluded beyond their ostia.
5. **RV pool (label 3)** runs from the tricuspid annulus to the pulmonary valve; trabeculae are included.
6. **Seeds** are `heartchambers_highres` masks, coarsened to 2 mm and smoothed (JA7).
   - 10 of the 60 seal cases are read from blank.
   - The reader sees no model output other than the seed.
7. **Anchoring report per wave (JA7):**
   - inter-read ASSD;
   - seed-vs-read ASSD and the share of voxels changed;
   - the half-maximum offsets of seeds and reads.

   **Thresholds, fixed now.** Seeded reads cannot accept a model if either:
   - blank-vs-seeded ASSD exceeds seeded inter-read ASSD by > 0.2 mm (paired bootstrap, upper 95 % bound); or
   - more than 50 % of seeded reads change < 1 % of seed voxels.

**Read queue (for the JA13 `role:swe` issue #141).**
- Four labels.
- Separate from SegQueue14.
- Cases from `configs/janusm/sealed-r1.json` only, after the guard.
- Two independent reads per case, never shown to each other.
- The half-maximum check runs at submission.
- The plateau-centred window opens by default.
- Reads are stored per reader, never merged by the tool.
- The export carries reader id, seed or blank, time spent and the half-maximum check result.

### 5.5 Item 5: seal re-powering and the final JA8 margins, fixed before any read

All of the following is computed on the **first 20 decision-set double reads**, with Janus-M 0 (the seed model) as
the model under test, and frozen in `configs/janusm/margins-r2.json` before any seal read.

1. **Inputs.** For each border, s_d is the SD over patients of d = (model-vs-read ASSD) − (read-vs-read ASSD),
   averaged over the two reads (JA8).
2. **Margin on d: δ = 0.25 mm per border. It is not re-set.**
   - E2: an achieved 0.25 mm mean displacement already costs 0.45 mm of segment thickness and subendocardial Dice
     0.91.
   - E4: at 0.25 mm read noise the thickness RC is 0.74 mm, the smallest thinning a flag can find.
   - A looser margin would let model error exceed what the reads can see.

   JA8 called the margin provisional. Hotel recommends fixing it now, on this evidence, so the 20 reads set only the
   sample size.
3. **Thickness margin: thickness error ≤ read-vs-read + 0.5 mm stays** (JA8). Hotel adds one condition: it must also
   be ≤ RC/2 measured on the same 20 reads. Otherwise the thickness co-primary cannot distinguish the model from a
   third reader.
4. **Seal size.**
   - Sizing rule: n_seal = ⌈((z₀.₉₅ + z₀.₈₀) · s_d / δ)²⌉ = ⌈(2.487 · s_d / 0.25)²⌉, using the larger s_d of the two
     borders. This is the one-sided 95 % upper bound with 80 % power when the true d is 0.
   - **If n_seal ≤ 60:** the seal stays 60.
   - **If 60 < n_seal ≤ 120:** the seal grows to n_seal from the pre-registered extension (JA6).
   - **If n_seal > 120:** the seal is 120, and the result is reported as "underpowered for δ = 0.25 mm" with the
     detectable margin stated.
5. **Guards stay** (JA8): |signed bias| ≤ 0.5 mm, and each ASSD ≤ 1.0 mm.
6. **The seal is never shrunk after a read, and is scored once.**

### 5.6 Item 6: rest TPR and the fat cut-off

**Rest TPR** (E3). The ruling's condition becomes three numbers from the JM-0 add-on. **Per-segment TPR enters Table
A only if all three hold:**
1. the median endocardial 10–90 % edge is ≤ 1.5 mm;
2. |the median endocardial half-maximum offset| is ≤ 0.25 mm (or the borders are snapped to half-maximum first);
3. the guarded free-wall TPR median is 1.06–1.12.

The reasons:
- with a 1 mm guard, a true 0.85 / 1.00 / 1.10 reads 0.88 / 1.01 / 1.09 at a 1.2 mm edge, and 1.04 / 1.17 / 1.25
  at a 2.4 mm edge, where a defect lands in the normal range;
- an endocardium drawn 0.5 mm into the blood adds +0.05 to +0.11, about the whole normal SD.

If the conditions fail, rest TPR is reported per territory only, report-only. If the edge is > 2 mm it is dropped.

**The fat cut-off, set on data.** A core voxel (≥ 1 mm from either border) counts as fat when **all** of these hold:
1. its HU is in −180 to 0 (Xu 2022's verified window; JA14: the −10 HU cut is unsourced);
2. its HU is below the patient's core-myocardium median minus 3.5 × the patient's core noise SD (robust MAD
   estimate). This makes the cut patient-specific and noise-aware: on a 100 HU myocardium it is +30 HU at 20 HU noise
   (so the 0 HU window edge binds) and −23 HU at 35 HU noise;
3. it lies in a 6-connected cluster of ≥ 3 such voxels.

The JM-0 add-on returns the pooled core-HU histogram. Before F2 is fixed, the rule is checked on it against F3: the
share of patients with any core fat should be in single digits.

### 5.7 Item 7: the twin rule (E1)

- **Count.** Applied to both public `meta.csv` files, the union rule refuses **695 of 1228** TotalSegmentator
  subjects. 23 of 130 cardiac studies remain.
- **Where the code is.** `guard_r2.twins()` implements it for the shared guard (#138). It refuses the union over v1
  and v2.0.1 (blank v2 fields widen it), and stops on a held-out id missing from a meta file.
- **Effect on Janus-M itself:** none. JA5 puts no TotalSegmentator case in the seal or the decision set, and JA9
  dropped pretraining.

## 6. Other lead questions, carried as stated assumptions

| Question | Assumed (the ruling's recommendation) | What path A does if the lead decides otherwise |
|---|---|---|
| LQ2 Learned structures | (a) LV myocardium + LV, RV, LA pools | (b) adds RV myocardium thickness to Table A; no RV layers |
| LQ3 `heartchambers_highres` licence | (a) yes, key typed by the lead on Fir | (b) Janus-M 0 becomes a trained model; F2 waits for it |
| LQ4 ImageCAS-X training cases | (a) yes | (b) path A has almost no adult CCTA to build F2 from; it then waits on #116 |
| LQ5 Reader time | (a) 200 double reads + 10 blank, after A39 | (c) seal 40: §5.5 still sizes it, and reports it underpowered if needed |
| LQ6 MM-WHS | (a) sign, low priority | Path A does not need it; it would be an external border check only |
| LQ7 Released coronary patients | (a) training only, explicit PR | Only F2 and training grow |
| LQ8 s0655 | (a) keep the seal | No path A effect. E1's s0767/s0848 twin finding is put to the lead under the same heading (§8) |
| **LQ-H1 (new)** A coronary stenosis grader | Not assumed: path A uses the reader's per-artery grade | If the coronary plan builds one (diameter profile from Janus's lumen), Table B's stenosis column is filled from it. That is a coronary-plan decision, not Janus-M's |

## 7. Compute: Job JM-0 add-on (Fir; account `def-aso22`; the lead runs it; CPU only, no GPU)

Run it **after** Job JM-0 (Juliet v1 §7) has finished. It uses JM-0's own files.

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius/repo && git fetch origin jm/rest-ccta && git checkout jm/rest-ccta && git pull --ff-only
source $HOME/icx4-tseg-venv/bin/activate        # or $HOME/icx14-venv: needs nibabel, scipy; totalsegmentator optional
python experiments/JanusM/Hotel/r2/fir/halfmax_tpr_m0.py --cases $SCRATCH/janusm/m0_cases.txt \
  --hc $SCRATCH/janusm/hc --layout $SCRATCH/icx4/layout.json --out $SCRATCH/janusm/hotel_r2_m0.json
```

- **Check.** The first line printed is `guard: 40 cases, 0 refused`, then one line per case.
  - If the guard raises `HeldOut`, stop and send that line back. It means `m0_cases.txt` holds a case outside the
    ImageCAS-X train list.
- **Send back on #142:** the final printed JSON (aggregates only: quartiles, counts, and a pooled histogram of core
  HU). **No image, and no per-case file.** `hotel_r2_m0.json` holds per-case rows and stays on Fir.
- **Cost:** CPU only, about 1–2 min per case (≈ 1 CPU-h). It adds no GPU-hours to JA10.
- **If the license-free venv lacks `totalsegmentator`:** the script falls back to the published label order. Check
  that the ids it prints match JM-0's.

## 8. Held-out disclosure (this round)

1. **No coronary hold-out was read in Round 2.**
   - Hotel's guard ran first.
   - Every experiment is synthetic.
   - The only public files read are the two TotalSegmentator `meta.csv` metadata tables, which name all 1228
     subjects, held-out ones included, without any image.
2. **What E1 found about Round 1.** Seven public subjects match a held-out subject exactly on age, sex, institute and
   study type. Two of them were opened by Hotel's Round 1 E1:
   - **s0767** matches s0846 (reserve);
   - **s0848** matches s1106 (sealed).

   Golf, India and Kilo also used exact matches (E1 table). Juliet did not.
   - **What was done with them in Round 1:** public CT and public model-made heart masks were read; geometry and HU
     were computed.
   - **What was not:** no coronary label was read, no Janus model was run, no coronary number was computed.
   - **Likelihood:** seven exact matches is what chance gives (mean 4.8, p = 0.24), so these are most likely
     different patients.
   - **Status under the rule:** the ruling's twin rule refuses them, and Hotel will not use them again.
3. **For the lead.** Whether this needs a note on the Round 1 record, or anything under D27, is the PM's and the
   lead's call. Hotel recommends a one-line note and no seal change, for the same reason as LQ8.

## 9. What results would change this plan

| Result | Change |
|---|---|
| JM-0 add-on: endocardial edge ≤ 1.5 mm, \|endo offset\| ≤ 0.25 mm, guarded TPR median 1.06–1.12 | Per-segment rest TPR enters Table A, with its F2 lower limit as the cut |
| JM-0 add-on: endocardial edge > 2 mm | Rest TPR is dropped from both tables |
| JM-0 add-on: \|epicardial half-maximum offset\| ≥ 0.5 mm (v1's +0.86 persists) | A half-maximum snap of the seeds before reads (a `role:swe` tool), and the thickness definition check (§4.4) runs first |
| JM-0: median thickness not within 1.5 mm of 5.7–6.5 mm | Readers measure thickness on 20 decision cases, and the definition is aligned before F2 (§4.4) |
| JM-0: "shared" segments > 20 % | Geodesic territories compared on those segments next round |
| First 20 decision double reads: thickness RC > 1.5 mm | Thinning cannot be flagged per segment. It is reported per territory (mean over its segments), where RC shrinks by √n |
| F2 population: pattern rate > 5 % of patients | The pattern requires two contiguous segments |
| The lead chooses path B (LQ1) | This path is deleted. Its table, protocol, harness and floors carry over to path B as Stage A, where F2 thresholds become the starting point for LGE calibration |

## 10. For the judge: where Hotel v2 stands

Hotel has not seen India v2 or Lima v1.

Hotel's claims, each testable:
1. **The Round 1 error curves are one curve once displacement is measured** (E2). Any plan that quotes a border bar
   from a nominal σ is quoting an artefact.
2. **On path A, every threshold must be above read noise and outside population spread** (F1 + F2). A borrowed CMR or
   literature cut is a check, not a threshold. Without a composite, a 16-segment table flags most patients by chance
   (§4.3).
3. **Rest TPR is decided by one measurable number, the edge width,** plus the endocardial offset, not by voxel size
   (E3).
4. **Equal thickness is enough.** Yezzi–Prince adds 1.5 % of voxels (E5).
5. **Janus has no stenosis grade.** Path A's table joins on the artery and copies the reader's grade (§3.1).

## 11. Sources

Bibliographic entries for items marked † are in `experiments/JanusM/Hotel/citations_clinical.md` or
`citations_segmentation.md`, opened at source in Round 1. JA14's corrections are applied:
- Nieman 2006 is used only for HU values and thinning; Nieman 2008 is the MRI comparison and is not cited here;
- Mushtaq 2023 is not cited;
- Cerqueira's territory text is unverified;
- there is no numeric MM-WHS Dice;
- there is no −10 HU fat cut.

The entries:
- Bland JM, Altman DG. Statistical methods for assessing agreement between two methods of clinical measurement.
  *Lancet* 1986;327(8476):307–310. doi:10.1016/S0140-6736(86)90837-8 (resolved at Crossref 2026-10-30).
- Cerqueira MD, et al. Standardized myocardial segmentation and nomenclature for tomographic imaging of the heart.
  *Circulation* 2002;105(4):539–542. doi:10.1161/hc0402.102975. Its territory figure is unverified (JA14). †
- Chen J, et al. Left ventricular wall thickness discrepancies at end-diastole and mid-diastole: reference values for
  cardiac CT. *Clin Imaging* 2025;118:110390. doi:10.1016/j.clinimag.2024.110390 (resolved at Crossref 2026-10-30;
  the 5.7 / 6.5 mm values as confirmed by the Round 1 judge).
- George RT, et al. *Circ Cardiovasc Imaging* 2009;2(3):174–182. doi:10.1161/CIRCIMAGING.108.813766. Normal TPR
  1.12 ± 0.13; abnormal < 0.99 [full text]. †
- Ichikawa Y, et al. *JACC Cardiovasc Imaging* 2009;2(5):548–555. doi:10.1016/j.jcmg.2009.01.010. LV fat in 62 %
  after MI vs 3 % of controls; 94 % subendocardial. †
- Ide S, et al. *J Cardiovasc Comput Tomogr* 2017;11(3):179–182. Voronoi mass at risk vs histology. †
- Kurata A, et al. *Eur Radiol* 2015;25(1):49–57. Voronoi territories on CCTA vs SPECT. †
- Nieman K, et al. *Am J Cardiol* 2006;98(3):303–308. doi:10.1016/j.amjcard.2006.01.101. Chronic MI −13 ± 37 HU vs
  73 ± 14 HU; thinning. †
- Ortiz-Pérez JT, et al. *JACC Cardiovasc Imaging* 2008;1(3):282–293. 23 % of infarcted segments discordant with the
  standard artery. †
- Shah DJ, et al. *JAMA* 2013;309(9):909–918. doi:10.1001/jama.2013.1381. Thinning ≤ 5.5 mm in 19 %; 18 % of thinned
  regions had ≤ 50 % scar; recovery from 4.4 to 7.5 mm. †
- Xu L, et al. Lipomatous metaplasia enables ventricular tachycardia by reducing current loss within the protected
  corridor. *JACC Clin Electrophysiol* 2022;8(10):1274–1285. doi:10.1016/j.jacep.2022.07.005. The −180 to 0 HU fat
  window [full text]. †
- Yezzi AJ, Prince JL. An Eulerian PDE approach for computing tissue thickness. *IEEE Trans Med Imaging*
  2003;22(10):1332–1339. †
- Kim-bin transmurality grading (0, 1–25, 26–50, 51–75, 76–100 %): as defined and cited in [[Kilo v1]]. Not
  re-checked here.
- Wasserthal J, et al. TotalSegmentator. *Radiol Artif Intell* 2023. Data: Zenodo 6802614 (v1) and 10047292
  (v2.0.1), CC BY 4.0. Only `meta.csv` was read this round.

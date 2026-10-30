---
tags: [janus-m, plans, candidate, round1, myocardium, layers, AHA-17, transmural, perfusion, scar, fir]
author: Golf
round: 1
version: 1
updated: 2026-10-30
issue: christianGRogers/Asclepius#130
---

# Golf v1: learn the two borders, derive the layers

## 1. The plan in one paragraph

**Janus-M learns two surfaces of the left-ventricular myocardium, endocardial and epicardial, on first-pass CCTA.
Every "layer" is computed from them by fixed geometry and never learned as a class:**
- transmural thirds (subendocardial, mid-wall, subepicardial), by equal-thickness depth;
- the AHA 17 segments;
- each segment's own coronary territory, taken from the four classes Janus already segments.

So the deliverable is a table of 17 segments × 3 layers per patient, each cell tagged with its territory.

**The first model costs no training.** Janus-M 0 is TotalSegmentator `heartchambers_highres` plus Golf's derivation
code. The project already holds a TotalSegmentator licence (Job S). Janus-M 0 is replaced only if it fails a
pre-registered test against team reads.

**Data is ImageCAS.** The coronary seal, the D35 draws and the reserve leave Janus-M almost nothing usable in the
SegQueue pool (E1). ImageCAS has 900 cases outside the coronary A14 seal. A Janus-M seal of 60 and a decision set
of 40 are drawn now, before any model or read exists.

**Stenosis and scar outputs come in two tiers:**
- **CCTA-only outputs** (wall thickness and thinning, rest transmural attenuation ratio, hypoattenuation, fat) are
  computed now and labelled research outputs.
- **CT perfusion and late-enhancement outputs** are a conditional phase. They need data the project does not hold:
  CTP or LIE with CMR or FFR references. No openly downloadable labelled set exists. Late enhancement is always
  graded inside the first-pass borders, never on its own (E3).

**Committed compute is ≤ 12 Fir GPU-hours**, plus CPU jobs; a trained Janus-M 1, if needed, adds about 55.

## 2. Evidence this round (CPU; code in `experiments/JanusM/Golf/`; no sealed case opened)

- **E1:** [[Golf - The coronary seal, D35 draws and reserve leave Janus-M 164 of 675 pool volumes, so its adult data is ImageCAS]]
  - Only 164 pool volumes are open to Janus-M.
  - Of the SDN normal-perfusion cohort, 1 patient is open; of the epicardial-fat set and the TotalSegmentator pool
    cases, none.
  - ImageCAS has 900 cases open.
  - Proposed Janus-M seal: `janusm_seal_proposal.json`.
- **E2:** [[Golf - Layers derived from two borders on real CT, and what a border error costs each layer]]
  - Data: 24 TotalSegmentator contrast cardiac CTs that are outside the pool, with their CC BY 4.0 myocardium labels.
  - Wall thickness, voxels per third, Laplace versus equal-thickness thirds, automatic AHA segments.
  - The same border error costs a third more Dice than it costs the whole myocardium.
- **E3:** [[Golf - On late-enhancement CT the scar's endocardial border must come from the first-pass scan]]
  - Simulation.
  - With bright blood, an LIE-only reader loses subendocardial scar at every CNR. Kim-bin accuracy is 0.20, which
    equals calling every segment zero.
  - With borders from the first-pass scan, accuracy is 0.88–1.00 at CNR 5.
- **Tools for the lead, self-tested:**
  - `fir/m1_chambers.sh` (Job M1);
  - `territories.py` (Job M2). Its self-test with synthetic standard-territory arteries reassigns 0 segments in
    4 of 4 cases.
- **Citations:**
  - `experiments/JanusM/Golf/citations.md` holds 54 entries. Each was opened at PubMed, PMC, arXiv or the dataset's
    own API, and is quoted from the abstract unless a table is named.
  - It records three corrections: Nieman 2008, not 2006; Forte, not Punzo, as first author; Lee 2016 in
    *Radiology*.
  - It lists what could not be verified. The main gap is the Cerqueira territory figure (publisher 403), so §4.3
    marks it as secondary.

## 3. The class schema, and what "layers" means

### 3.1 Learned classes (what a model predicts)

| Value | Class | Role | Scored? |
|---|---|---|---|
| 1 | LV myocardium | The object: its two surfaces are the endocardial and epicardial borders | **Yes, decisive** |
| 2 | LV blood pool | Defines the endocardium. **Papillary muscles and trabeculae belong to the blood pool** (lead Q3) | Through the endocardial border |
| 3 | RV blood pool | Landmark: the two RV insertion points that orient the AHA segments | Report only |
| 4 | Left atrium | Landmark: the mitral plane that sets the base | Report only |

`heartchambers_highres` already produces all four, plus RA, aorta and pulmonary artery, so Janus-M 0 needs no
relabelling. A trained Janus-M 1 keeps exactly these four.

**Why the LV only, and not both ventricles (lead Q1).** The brief is stenosis and scar. Both are graded on the LV in
the 17-segment model ([[#Cerqueira2002]]), in CT perfusion ([[#George2009]], [[#Mushtaq2023]]) and in late
enhancement ([[#Kim2000]], [[#Gatti2025]]). The RV free wall is thin. Even the LV wall leaves only about 2–4 voxels
per third (E2), and every layer statistic on the RV would rest on partial-volume voxels. The RV blood pool is kept
because it orients the AHA model. An RV myocardium class can be added later without changing anything here.

### 3.2 Derived layers (computed, never learned)

| Layer | Definition | Code |
|---|---|---|
| **Transmural depth u** | u = d_endo / (d_endo + d_epi) at each myocardial voxel. 0 is the endocardium and 1 the epicardium. This is an equal-thickness coordinate | `layers_ts.depth` |
| **Thirds** | Subendocardial u < 1/3; mid-wall 1/3 ≤ u < 2/3; subepicardial u ≥ 2/3 | `layers_ts.thirds` |
| **AHA 17 segments** | Long axis by PCA of the LV. The base is the mitral plane: LV voxels within 3 mm of the LA. Segment 17 is the apex cap beyond the cavity tip. Basal, mid and apical are equal thirds of base → cavity tip. Angle zero is the anterior RV insertion: the end of the RV-contact arc nearer anterior. The septum (segments 2/3, 8/9, 14) spans the measured RV-contact arc | `layers_ts.aha`, `aha_labels` |
| **Territory** | Each myocardial voxel takes the class of the nearest LAD, LCx or RCA voxel of Janus 0's prediction. This is a Euclidean Voronoi partition, as in [[#Stalikas2025]]; LM is not a seed. Each segment carries its majority territory **and** the standard AHA assignment beside it | `territories.py` |

**Why derive rather than learn:**

1. **Nobody can draw a third.** Subendocardial, mid-wall and subepicardial are definitions: fractions of the wall
   between two borders ([[#George2009]] uses 3 layers; [[#Mushtaq2023]] uses 25 % and 50 % of wall thickness). No
   image edge separates them. A learned "third" class can only learn the geometry we would have computed, plus noise.
   The reference standard for a layer is therefore the reference standard for the two borders (§6).
2. **A layer is a harder target than the myocardium, for the same border error.** In E2, borders were perturbed by a
   smooth random displacement on a 0.5 mm grid:

   | Border error (RMS) | Myocardium Dice | Subendocardial-third Dice | Subepicardial-third Dice | Mid-wall-third Dice |
   |---|---|---|---|---|
   | 0.25 mm | «E2_025_myo» | «E2_025_t1» | «E2_025_t3» | «E2_025_t2» |
   | 0.5 mm | «E2_05_myo» | «E2_05_t1» | «E2_05_t3» | «E2_05_t2» |
   | 1.0 mm | «E2_1_myo» | «E2_1_t1» | «E2_1_t3» | «E2_1_t2» |

   Every layer error is already set by the border error. Scoring the layers adds no information beyond the borders.
   Scoring the borders in millimetres (§7.3) does.
3. **The definition must be fixed in the protocol, because the choice matters.** On the same 24 myocardia, thirds
   by Laplace potential (the classic "transmural coordinate", [[#Jones2000]], [[#Bayer2018]]) and thirds by equal
   thickness agree on only «E2_agree» of voxels. The Laplace thirds hold «E2_lap» of the myocardial volume
   (subendocardial / mid / subepicardial). The equal-thickness thirds hold «E2_eq». [[#Schuler2021]] reports that
   normalised distances are more linear than Laplace solutions. The clinical definitions are fractions of
   thickness. So Golf fixes **equal thickness** (lead Q2).
4. **Derivation is auditable and cheap to change.** If the lead wants halves instead of thirds, or a different base
   rule, the table is recomputed from the stored borders without retraining.

**Feasibility on real CT (E2, 24 cases, 1.5 mm):**
- the AHA derivation succeeded in «E2_aha_ok» of 24 cases, with all 17 segments non-empty in «E2_aha_full»;
- the orientation checks (septum towards the RV, segment 1 anterior to segment 4) passed in «E2_orient» of 24;
- the median septal arc was «E2_arc»° (expected about 120°: two of six 60° sectors).

## 4. Clinical outputs, and how they tie to the coronary tree

Each output is reported per segment × layer and per territory, and aggregated per patient. Tier A runs on the CCTA
that exists. Tier B needs data the project does not hold.

### 4.1 Stenosis (ischaemia)

| # | Output | Tier | Evidence that it means something |
|---|---|---|---|
| S1 | **Rest transmural attenuation ratio** (subendocardial / subepicardial HU) per segment and territory | A | In normal hearts the subendocardium enhances more than the outer layers, with septal ratio 1.06 ± 0.06 ([[#Forte2020]]). This gives the normal range a rest defect is read against. Not a validated ischaemia test at rest |
| S2 | **Myocardial features with stenosis degree**, per territory | A | Deep-learning LV myocardium features on CCTA identify functionally significant stenosis: AUC 0.74 ([[#Zreik2018]]). Adding them to stenosis degree raises AUC from 0.68 to 0.76 ([[#vanHamersvelt2019]]). Both are against invasive FFR, which the project does not hold |
| S3 | **Stress CTP transmural perfusion ratio and defect extent**: subendocardial (25–50 %) versus transmural (> 50 %) | **B** | Normal stress TPR 1.12 ± 0.13, abnormal < 0.99 ([[#George2009]], Results). Defect extent changes accuracy: 93.5 % for subendocardial versus 87.7 % for transmural defects ([[#Mushtaq2023]]). CCTA + static CTP against FFR: per-vessel sensitivity 92 %, specificity 95 % ([[#Pontone2019a]]) |
| S4 | **Dynamic CTP myocardial blood-flow ratio** per territory | **B** | Relative MBF AUC 0.85 versus absolute 0.75 ([[#Kono2014]]). Dynamic CTP + CCTA + FFR-CT AUC 0.919 ([[#Pontone2019b]]) |

### 4.2 Scar

| # | Output | Tier | Evidence |
|---|---|---|---|
| C1 | **Wall thickness and thinning** per segment (mm), against the patient's remote segments and CT norms | A | End-diastolic global 5.7 ± 0.8 mm; upper limits 9.9 mm (women) and 11.7 mm (men); phase matters, with mid-diastole at 6.5 mm ([[#Chen2025]]). Long-standing infarcts are thinned ([[#Nieman2006]]) |
| C2 | **First-pass hypoattenuation** per segment × layer | A | Chronic infarct −13 ± 37 HU versus normal 73 ± 14 HU ([[#Nieman2006]]). First-pass hypoenhancement against MRI: R² = 0.72 ([[#Nieman2008]]) |
| C3 | **Intramyocardial fat** per segment × layer | A | Found in 62 % of prior-MI patients; **94 % subendocardial**; 97 % in the infarct-related territory ([[#Ichikawa2009]]). The layer output is what makes this usable |
| C4 | **Late iodine enhancement: transmurality in Kim bins** (0, 1–25, 26–50, 51–75, 76–100 %), **graded inside the registered first-pass borders** | **B** | LIE against CMR late gadolinium enhancement, segment level: sensitivity 0.86, specificity 0.98 ([[#Gatti2025]]). E3: borders must come from the first-pass scan. The fused CCTA + late-CT workflow is that of [[#Mahnken2010]] |
| C5 | **Extracellular volume** per segment (needs pre-contrast, equilibrium phase and haematocrit) | **B** | CT against MRI ECV: r = 0.89 per patient and 0.84 per segment ([[#Zhang2023]]). 5-min equilibrium agrees better than 15-min: r² 0.85 versus 0.74 ([[#Treibel2015]]) |

Tier A outputs C1–C3 and S1 carry the label "research output, not validated against a reference" until §6's
references exist. None is shown to a clinician as a finding.

### 4.3 The tie to Janus's coronary territories

Every output is aggregated over the patient's own territory: the myocardium nearest to Janus's LAD, LCx and RCA
(§3.2). This matters because the standard AHA assignment is often wrong for the individual patient:
- **23 %** of infarcted segments were discordant with the standard territory on CMR ([[#OrtizPerez2008]]);
- on PET/CT with CT angiography, **72 %** of patients had at least one segment reassigned, and 9.3 % of segments
  were ([[#Javadi2010]]);
- on CT, 10 of 96 segments were discordant ([[#Mahnken2010]]).

Golf reports both the patient-specific and the standard assignment. For the standard one it uses the mapping
commonly quoted from [[#Cerqueira2002]]: LAD 1, 2, 7, 8, 13, 14, 17; RCA 3, 4, 9, 10, 15; LCx 5, 6, 11, 12, 16.
**Golf could not open the primary figure (publisher 403). The list is checked against secondary sources only,
and the judge should treat it so.**

Job M2 measures the reassignment rate on 800 ImageCAS cases with Janus 0's existing predictions. The comparators
are [[#Javadi2010]] and the CCTA Voronoi mass shares of [[#Stalikas2025]]: LAD 42.5 %, LCx 28.8 %, RCA 26.4 %.

## 5. CT protocols and phases

| Phase / protocol | Needed for | Held by the project? | Notes |
|---|---|---|---|
| **ECG-gated first-pass CCTA**, best diastole | Borders, all derived layers; S1, S2, C1–C3 | **Yes**: ImageCAS 1000 (900 usable), CCTA-Pool | Record the cardiac phase. Thickness differs by phase: 5.7 mm at end-diastole versus 6.5 mm at mid-diastole ([[#Chen2025]]) |
| Stress CTP, static or dynamic | S3, S4 | No | Beam-hardening correction is required: it raised the CTP–microsphere correlation from 0.60 to 0.74 ([[#Kitagawa2010]]); scanner correction cuts artefact from > ±30 HU to ≤ ±5 HU ([[#So2016]]). SCCT terminology from [[#Patel2020]] |
| Late iodine enhancement, about 5–10 min | C4 | No | Acquire or reconstruct for **CNR**, not for the thinnest slice (E3). The dual-energy subgroup had segment sensitivity 0.93 ([[#Gatti2025]]) |
| Non-contrast + equilibrium (+ haematocrit) | C5 | No | ECV at 5 min ([[#Treibel2015]]) |

## 6. Data and reference standard

### 6.1 Data

| Source | What it gives Janus-M | Licence / access | Status |
|---|---|---|---|
| **ImageCAS 1000** (Girder `SegQueue/cases`; on Fir as `$SCRATCH/icx4`) | Adult gated CCTA. 900 cases outside A14: seal 60, decision 40, trainable 800 | As held for Janus | **Use**; E1 |
| **TotalSegmentator `heartchambers_highres`** (model) | Janus-M 0's borders. Trained on 1,559 images at about 0.73 × 0.72 × 1.0 mm; validation Dice over all classes 0.950 ([[#Wasserthal2023]]) | Licence-gated; free academic licence; **the project holds one (Job S)** | **Use** (lead Q4: research use) |
| TotalSegmentator dataset, cardiac cases outside the pool (114) | External, report-only test of LV myocardium at 1.5 mm | CC BY 4.0 (Zenodo 10.5281/zenodo.10047292) | Used in E2 |
| ImageCHD, non-sealed (63) | Myocardium labels (label 5) at about 0.25 × 0.25 × 0.5 mm; congenital, aged 1 month to 40 years ([[#Xu2020]]) | CC BY-NC 4.0 | Report-only paediatric stratum, **never decisive** |
| MM-WHS CT (60; 20 with labels) | Expert myocardium labels on adult CT, 0.78 mm in-plane ([[#Zhuang2019]]) | **Gated:** signed agreement, no redistribution | Lead Q7; Golf stops here (D31) |
| SDN normal-perfusion cohort (Mendeley cy54ttk3fj) | Normal rest TPR reference ([[#Forte2020]]) | CC BY 4.0 | **36 sealed, 24 in D35 draws, 18 reserve; 1 patient open.** The reference values come from the paper, not the images |
| CT perfusion or LIE with labels | S3, S4, C4 | **None openly downloadable.** Five Monzino records on Zenodo and the Penso 2023 record are restricted | Golf says so and stops (D31) |
| The lead's own institution (CCTA + CTP/LIE + CMR + FFR) | The only route to tier B and to validating tier A | Lead's call (D19) | Lead Q7 |

### 6.2 Reference standard

| Label | Reference | Who / how |
|---|---|---|
| Endocardial and epicardial borders | **Two independent team reads per case** on the Janus-M seal (60) and decision set (40). The inter-read difference is the ceiling | Needs a SegQueue14 myocardium protocol: a `role:swe` issue, opened once the judge adopts this |
| Thirds, AHA segments | **By definition from the borders.** No separate read exists or can exist (§3.2) | — |
| Territories | Janus's coronary classes. Their own reference is ImageCAS-X and the coronary reads | — |
| Fat, hypoattenuation, thickness | Measured on the CT itself inside the reference borders | — |
| Scar (C4, and validating C2/C3) | **CMR late gadolinium enhancement**, segment-matched ([[#Gatti2025]]'s reference) | Institutional only |
| Ischaemia (S1–S4) | **Invasive FFR** per vessel ([[#Pontone2019a]], [[#Takx2015]]) | Institutional only |

**Anchoring.** The coronary rounds found that reads drawn from a seed inherit the seed's extent. So:
- seal and decision reads start from a **coarsened** seed, `heartchambers_highres` resampled to 2 mm and smoothed,
  which readers must redraw at full resolution;
- **10 of the 60 seal cases are read from blank** to measure anchoring.

If blank reads differ from seeded reads by more than the inter-read difference, the seeded reads are not used to
accept Janus-M 0.

## 7. Model, recipe, deciding metric and splits

### 7.1 Models in reading order (M1: the first read is Janus-M 0)

- **Janus-M 0** = TotalSegmentator `heartchambers_highres` (Job M1) + Golf's derivation (§3.2). No training.
- **Janus-M 1**, only if Janus-M 0 fails §7.3 on the decision set. nnU-Net v2 ([[#Isensee2021]]) ResEnc
  `3d_fullres` on the 800 trainable ImageCAS cases:
  - targets: the four classes of §3.1;
  - labels: `heartchambers_highres` pseudo-labels, replaced case by case with team reads where they exist;
  - spacing: the planner's choice, with 0.7 mm as the expected target;
  - 1000 epochs, fold 0, with validation = the Janus-M decision set (never trained on).

### 7.2 Splits (drawn now; `experiments/JanusM/Golf/janusm_seal_proposal.json`)

| Set | Cases | Rule | Use |
|---|---|---|---|
| Janus-M seal | 60 | The first 60 of the 900 by `sha256('asclepius-janusm-sealed-r1:' + case)` | Scored **once**, at a milestone, against two reads. Never inspected before |
| Janus-M decision | 40 | The next 40 | Decides §7.3 and any recipe question. Never trained on |
| Trainable | 800 | The rest | M2, Janus-M 1 |
| External, report-only | 114 + 63 | TotalSegmentator outside the pool (1.5 mm); ImageCHD non-sealed (paediatric) | Never decisive |

The coronary A14 seal (80 + 20) is excluded by construction. `sealed.refuse_sealed` and `segtrain.pool_seal.apply(...,
"refuse")` guard every job.

### 7.3 The deciding metric

**Primary: the per-segment wall-thickness error.** For each patient, take the median over the 16 segments of
|model thickness − mean-read thickness|, in mm. Thickness is the median of d_endo + d_epi in the segment. Report
the mean over patients with a bootstrap 95 % CI.

**Acceptance on the decision set:**
- the model–read thickness error is at most the read–read thickness error + 0.5 mm (upper CI); **and**
- the endocardial and epicardial ASSD are each ≤ 1.0 mm.

The 0.5 mm margin is one voxel of the 0.5 mm grid and below a third of a 5.7 mm normal wall. Zreik 2018 reports a
0.7 mm mean distance for LV myocardium.

**Why not Dice:** E2 shows Dice saturates on the whole myocardium while the layer error is still large. The
clinical outputs are thicknesses and fractions of thickness, so millimetres decide. Dice, the agreement of the
thirds and the AHA segment Dice are reported.

### 7.4 What ships

`src/janusm/` holds the derivation (§3.2) and the 17 × 3 table writer. It is a `role:swe` issue opened when the
judge adopts this. Until then the code lives in `experiments/JanusM/Golf/`.

## 8. Compute (Fir, account `def-aso22`; the lead runs every command; Golf runs nothing on SciNet or Alliance)

| Job | What | Waits on | GPU-h |
|---|---|---|---|
| M1 | `heartchambers_highres` on the 900 ImageCAS cases outside A14 | This PR merged; the licence is already set from Job S | **≤ 12** (estimate; resumable) |
| M2 | Patient-specific territories versus standard; AHA derivation failure rate (800 trainable) | M1; Janus 0 predictions (exist) | 0 (CPU) |
| M3 | Janus-M 1, only if Janus-M 0 fails §7.3 | 100 cases double-read | **≈ 55** (icx4's 1000 epochs took 54 h at 192 s/epoch: [[icx4 - Results]]) |

**Committed: ≤ 12 GPU-h. Conditional: about 55.** Every GPU job uses 1 × H100 80 GB (`h100:1`), 12 cores, and is
charged to `def-aso22_gpu`.

### Job M1 (≤ 12 GPU-h)

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius/repo && git pull --ff-only
sbatch experiments/JanusM/Golf/fir/m1_chambers.sh      # resumable: re-submit until it prints "chambers: 900 of 900"
```

### Job M2 (CPU, after M1)

```sh
module load StdEnv/2023 python/3.11.5
source $HOME/icx4-tseg-venv/bin/activate && cd $SCRATCH/asclepius/repo   # this venv has totalsegmentator (class map) + nibabel/scipy
python experiments/JanusM/Golf/territories.py --chambers $SCRATCH/janusm/chambers --pred $SCRATCH/icx4/predictions \
  --sealed trillium/icx4/sealed_test.json --out $SCRATCH/janusm/territories.json --np 10
```

- **Check:** about 800 cases with both chambers and Janus 0 prediction; the summary prints `n_ok`.
- **Send back on #130:** the printed summary (no images):
  - the percentage of segments reassigned;
  - the percentage of patients with any segment reassigned;
  - the median LAD / LCx / RCA mass shares;
  - the `fails` count.

If the prediction file names in `$SCRATCH/icx4/predictions` are not `c0000.nii.gz`, send `ls | head`.

## 9. What would change this plan

| Result | Change |
|---|---|
| Janus-M 0 passes §7.3 on the decision set | No training. Janus-M 0 is the model; M3 is never run |
| Janus-M 0 fails | M3 (Janus-M 1); re-decide on the same decision set |
| Blank reads differ from seeded reads by more than the inter-read difference | Seeded reads cannot accept a model. All 60 seal reads go from blank (about 3× the reading time) |
| M2: AHA derivation fails in > 5 % of cases | Fix the base and insertion rules before any table ships (E2 sets the rule on 24 cases) |
| M2: reassignment ≪ Javadi's 9.3 % of segments | The territory output is redundant with the standard mapping. Keep it as a report |
| The lead obtains an institutional CTP/LIE + CMR + FFR cohort | Tier B opens: S3, S4, C4, C5; a scar reference; tier A validated against it. A new round plans it |
| The lead declines tier B | Janus-M stays a CCTA myocardium model with research outputs; the brief's "scarring" is met only by C1–C3 |
| The lead wants both ventricles | Add an RV myocardium class. Its thickness is scored on the RV free wall only; no RV layers (§3.1) |

## 10. The lead's decisions (numbered questions, each with Golf's recommendation)

- **Q1 (scope).** LV myocardium only as the scored structure; RV and LA as landmarks? **Recommended: yes.**
- **Q2 (what "layers" means).** Equal-thickness transmural thirds × AHA 17 segments × patient-specific coronary
  territory, derived from two learned borders, never learned as classes? **Recommended: yes.**
- **Q3 (label convention).** Papillary muscles and trabeculae belong to the blood pool? **Recommended: yes.**
- **Q4 (first model).** Janus-M 0 = TotalSegmentator `heartchambers_highres` under the project's academic licence,
  research use only, with the licence key never committed? **Recommended: yes.**
- **Q5 (seal).** Adopt the Janus-M seal 60 and decision set 40 from ImageCAS (`janusm_seal_proposal.json`)?
  **Recommended: yes.** This touches no coronary decision: A14's 100 cases are excluded, and the coronary model is
  never scored on these.
- **Q6 (reads).** 100 ImageCAS cases × 2 reads of the LV borders, plus 10 blank reads, through a new SegQueue14
  myocardium protocol (a `role:swe` issue)? **Recommended: yes.** This is the one new human cost.
- **Q7 (data the project lacks).** Whether to seek a cohort with CTP and/or LIE plus CMR LGE and FFR, for example
  from the lead's own institution, and the MM-WHS agreement. Both are gated. Access is the lead's (D19), and nothing
  about it is written here (D31). **Recommended: the institutional cohort if feasible.** Without it, tier B and every
  scar or ischaemia validation stays closed.
- **Q8 (labelling).** Tier A scar and ischaemia outputs are labelled "research, not validated" until Q7's
  references exist? **Recommended: yes.**

## 11. References

Every entry was verified at the URL in `experiments/JanusM/Golf/citations.md`. Numbers are from the abstract unless
a section is named.

- <a id="Cerqueira2002"></a>Cerqueira MD, et al. Standardized myocardial segmentation and nomenclature for tomographic imaging of the heart. *Circulation* 2002;105:539-542. doi:10.1161/hc0402.102975 (territory figure not read: 403).
- <a id="OrtizPerez2008"></a>Ortiz-Pérez JT, et al. Correspondence between the 17-segment model and coronary arterial anatomy using contrast-enhanced cardiac MRI. *JACC Cardiovasc Imaging* 2008;1:282-293. doi:10.1016/j.jcmg.2008.01.014.
- <a id="Javadi2010"></a>Javadi MS, et al. Definition of vascular territories on myocardial perfusion images by integration with true coronary anatomy: a hybrid PET/CT analysis. *J Nucl Med* 2010;51:198-203. doi:10.2967/jnumed.109.067488.
- <a id="Mahnken2010"></a>Mahnken AH, et al. The culprit lesion and its consequences: combined visualization of the coronary arteries and delayed myocardial enhancement in dual-source CT. *Eur Radiol* 2010;20:2834-2843. doi:10.1007/s00330-010-1864-x.
- <a id="Stalikas2025"></a>Stalikas N, et al. Vessel-specific myocardial mass in patients with stable coronary artery disease. *J Am Heart Assoc* 2025;14:e039013. doi:10.1161/JAHA.124.039013.
- <a id="Zhuang2019"></a>Zhuang X, et al. Evaluation of algorithms for multi-modality whole heart segmentation. *Med Image Anal* 2019;58:101537. doi:10.1016/j.media.2019.101537.
- <a id="Wasserthal2023"></a>Wasserthal J, et al. TotalSegmentator: robust segmentation of 104 anatomic structures in CT images. *Radiol Artif Intell* 2023;5:e230024. doi:10.1148/ryai.230024; `heartchambers_highres` details from the TotalSegmentator repository (resources/heartchambers_highres_details.md).
- <a id="Xu2020"></a>Xu X, et al. ImageCHD: a 3D computed tomography image dataset for classification of congenital heart disease. MICCAI 2020. arXiv:2101.10799.
- <a id="Zreik2018"></a>Zreik M, et al. Deep learning analysis of the myocardium in coronary CT angiography for identification of patients with functionally significant coronary artery stenosis. *Med Image Anal* 2018;44:72-85. doi:10.1016/j.media.2017.11.008.
- <a id="vanHamersvelt2019"></a>van Hamersvelt RW, et al. Deep learning analysis of left ventricular myocardium in CT angiographic intermediate-degree coronary stenosis improves the diagnostic accuracy for identification of functionally significant stenosis. *Eur Radiol* 2019;29:2350-2359. doi:10.1007/s00330-018-5822-3.
- <a id="Isensee2021"></a>Isensee F, et al. nnU-Net. *Nat Methods* 2021;18:203-211. doi:10.1038/s41592-020-01008-z.
- <a id="Chen2025"></a>Chen J, et al. Left ventricular wall thickness discrepancies at end-diastole and mid-diastole: reference values for cardiac CT. *Clin Imaging* 2025;118:110390. doi:10.1016/j.clinimag.2024.110390.
- <a id="George2009"></a>George RT, et al. Adenosine stress 64- and 256-row detector CT angiography and perfusion imaging. *Circ Cardiovasc Imaging* 2009;2:174-182. doi:10.1161/CIRCIMAGING.108.813766 (TPR values: Results).
- <a id="Mushtaq2023"></a>Mushtaq S, et al. Diagnostic accuracy of subendocardial vs. transmural myocardial perfusion defect. *J Cardiovasc Comput Tomogr* 2023;17:277-280. doi:10.1016/j.jcct.2023.05.005.
- <a id="Forte2020"></a>Forte E, et al. Normal patterns of left ventricle rest myocardial perfusion assessed by third-generation cardiac CT. *Clin Physiol Funct Imaging* 2020;40:30-36. doi:10.1111/cpf.12598.
- <a id="Pontone2019a"></a>Pontone G, et al. Stress CT perfusion versus FFR-CT in suspected CAD: the PERFECTION study. *JACC Cardiovasc Imaging* 2019;12:1487-1497. doi:10.1016/j.jcmg.2018.08.023.
- <a id="Pontone2019b"></a>Pontone G, et al. Dynamic stress CT perfusion with a whole-heart coverage scanner in addition to CCTA and FFR-CT. *JACC Cardiovasc Imaging* 2019;12:2460-2471. doi:10.1016/j.jcmg.2019.02.015.
- <a id="Kono2014"></a>Kono AK, et al. Relative myocardial blood flow by dynamic CT perfusion imaging predicts hemodynamic significance of coronary stenosis better than absolute blood flow. *Invest Radiol* 2014;49:801-807. doi:10.1097/RLI.0000000000000087.
- <a id="Takx2015"></a>Takx RA, et al. Diagnostic accuracy of stress myocardial perfusion imaging compared to invasive coronary angiography with FFR: meta-analysis. *Circ Cardiovasc Imaging* 2015;8:e002666. doi:10.1161/CIRCIMAGING.114.002666.
- <a id="Patel2020"></a>Patel AR, et al. SCCT expert consensus document on myocardial CT perfusion imaging. *J Cardiovasc Comput Tomogr* 2020;14:87-100. doi:10.1016/j.jcct.2019.10.003.
- <a id="Kitagawa2010"></a>Kitagawa K, et al. Characterization and correction of beam-hardening artifacts during dynamic volume CT assessment of myocardial perfusion. *Radiology* 2010;256:111-118. doi:10.1148/radiol.10091399.
- <a id="So2016"></a>So A, et al. Evaluation of a 160-mm/256-row CT scanner for whole-heart quantitative myocardial perfusion imaging. *Med Phys* 2016;43:4821. doi:10.1118/1.4957389.
- <a id="Kim2000"></a>Kim RJ, et al. The use of contrast-enhanced MRI to identify reversible myocardial dysfunction. *N Engl J Med* 2000;343:1445-1453. doi:10.1056/NEJM200011163432003.
- <a id="Gatti2025"></a>Gatti M, et al. Diagnostic accuracy of late iodine enhancement on cardiac CT: systematic review and meta-analysis. *Eur Radiol* 2025;35:3054-3067. doi:10.1007/s00330-024-11283-5.
- <a id="Nieman2006"></a>Nieman K, et al. Differentiation of recent and chronic myocardial infarction by cardiac CT. *Am J Cardiol* 2006;98:303-308. doi:10.1016/j.amjcard.2006.01.101.
- <a id="Nieman2008"></a>Nieman K, et al. Reperfused myocardial infarction: contrast-enhanced 64-section CT in comparison to MR imaging. *Radiology* 2008;247:49-56. doi:10.1148/radiol.2471070332.
- <a id="Ichikawa2009"></a>Ichikawa Y, et al. Adipose tissue detected by multislice CT in patients after myocardial infarction. *JACC Cardiovasc Imaging* 2009;2:548-555. doi:10.1016/j.jcmg.2009.01.010.
- <a id="Zhang2023"></a>Zhang H, et al. CT for the evaluation of myocardial extracellular volume with MRI as reference: systematic review and meta-analysis. *Eur Radiol* 2023;33:8464-8476. doi:10.1007/s00330-023-09872-x.
- <a id="Treibel2015"></a>Treibel TA, et al. Extracellular volume quantification by dynamic equilibrium cardiac CT in cardiac amyloidosis. *J Cardiovasc Comput Tomogr* 2015;9:585-592. doi:10.1016/j.jcct.2015.07.001.
- <a id="Jones2000"></a>Jones SE, et al. Three-dimensional mapping of cortical thickness using Laplace's equation. *Hum Brain Mapp* 2000;11:12-32. doi:10.1002/1097-0193(200009)11:1<12::aid-hbm20>3.0.co;2-k.
- <a id="Bayer2018"></a>Bayer J, et al. Universal ventricular coordinates. *Med Image Anal* 2018;45:83-93. doi:10.1016/j.media.2018.01.005.
- <a id="Schuler2021"></a>Schuler S, et al. Cobiveco: consistent biventricular coordinates. *Med Image Anal* 2021;74:102247. doi:10.1016/j.media.2021.102247.

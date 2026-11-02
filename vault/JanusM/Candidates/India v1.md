---
aliases: [India v1]
tags: [janus-m, plans, candidate, round-1, india, myocardium]
status: submitted
round: 1
advocate: India
updated: 2026-10-30
---

# India v1: segment two borders, compute the layers

**Advocate:** India. **Round:** 1 (issue #130). **Evidence:** [[India - E1-E4 LV wall geometry on open CT]]
(code `experiments/JanusM/India/`), and the citations in §13, each with a DOI or arXiv id.

## 1. The plan in one paragraph

Janus-M learns **what a reader can draw on a CT: the LV blood pool and the LV myocardium**, plus the RV and LA
blood pools that fix the landmarks. It has **no "layer" classes**. Every layer quantity is **computed** from
the two borders by fixed geometry:
- a Laplace transmural coordinate (0 at the endocardium, 1 at the epicardium) and its thirds;
- the AHA 17 segments, from the long axis and the RV insertion points;
- patient-specific coronary territories, from Janus's four vessel classes.

The reasons:
- A transmural third is 1–2 voxels on the largest open CT label grid (E1).
- Nobody can draw a mid-wall border, so a third has no reference standard of its own.
- Layer accuracy is set entirely by border accuracy. E2 measures how a border error carries into the layers.

On the coronary CTA the project already holds, the plan delivers:
- wall thickness and thinning per segment;
- subendocardial hypo-attenuation and fat per segment and per layer;
- myocardial mass per Janus territory.

All three are tied to the Janus vessel that supplies the tissue. Validated scar (late iodine enhancement) and
ischaemia (stress CT perfusion) need CT phases **that no open dataset and, to my knowledge, nothing on Girder
provides**. They are staged behind a data decision for the lead (Q4), and are never claimed from rest CTA alone.

**Janus-M 0 needs no training to start.** It is an off-the-shelf heart-chamber model (TotalSegmentator
`heartchambers_highres`, if the lead accepts its licence, Q1) followed by India's geometry. A trained model
(Janus-M 1) is built only if Janus-M 0 fails the border gate (§7) against double reads.

## 2. Class schema, and what "layers" means

### 2.1 What the model segments (learned classes)

| Value | Class | Why it is needed |
|---|---|---|
| 1 | LV myocardium (compact wall; papillary muscles and trabeculae go to the blood pool) | The wall itself. Mass, thickness, attenuation |
| 2 | LV blood pool (cavity incl. papillary muscles and trabeculae, to the mitral and aortic valve planes) | The endocardial border is the myocardium–blood-pool interface |
| 3 | RV blood pool | RV insertion points (the AHA reference), and the septum's right side |
| 4 | LA blood pool | The mitral plane: the base of the long axis |
| 5 | Aorta (root to the arch) | LVOT and valve plane; it also links to Janus's ostia |

- **LV only, not both ventricles.** The brief is stenosis and scar. Coronary infarct scar and stenosis-related
  ischaemia are LV findings in practice; the AHA model, CT perfusion and the LIE literature are all LV (§13).
- The RV free wall is 3–5 mm on CT. That is 2–3 voxels at the 1.5 mm label grid (E1 measures the LV wall; the
  RV wall is thinner still), so it cannot carry layers. RV classes are kept as blood pools for landmarks only.
- This is the same structure set as TotalSegmentator's `heartchambers_highres` (myocardium, LA, LV, RA, RV,
  aorta, PA; §13 [TS]), minus RA and PA. So Janus-M 0 can be that model with no change of schema.

### 2.2 What "layers" means (computed, not learned)

1. **Transmural coordinate t ∈ [0,1].** Laplace's equation solved in the wall: u = 0 on the endocardium and u = 1 on
   the epicardium (Jones 2000 for cortex; the LDRB and UVC cardiac models, Bayer 2012 and 2018). It is unambiguous,
   is defined at every voxel, and has no free parameter.
2. **Transmural thirds:**
   - subendocardial t < 1/3;
   - mid-wall 1/3–2/3;
   - subepicardial > 2/3.

   Also any finer **transmurality bin** for scar extent: 0, 1–25, 26–50, 51–75 and 76–100 %, the CMR viability
   bins whose clinical meaning Kim 2000 established.
3. **AHA 17 segments** (Cerqueira 2002):
   - the basal, mid and apical thirds of the base–apex length, with the apex cap beyond the cavity tip;
   - 60° sectors from the anterior RV insertion in the basal and mid rings, 90° sectors in the apical ring.
4. **Coronary territory per voxel** from Janus's LM/LAD/LCx/RCA masks: nearest vessel in 3D first, then a
   geodesic Voronoi over the epicardium (Termeer 2010; Kurata 2015; Ide 2017). The AHA default assignment is
   carried alongside for comparison.

Why compute rather than learn layers (evidence in [[India - E1-E4 LV wall geometry on open CT]]):
- **E1, the voxels are not there.** On the 1.5 mm grid of the largest open CT myocardium label set (TotalSegmentator
  v1), the median LV wall is **6.3 (p10–p90 5.7–7.0) voxels across**, so a third is **2.1 voxels**. On a 0.5 mm
  CCTA-like grid a third is **6.3 voxels**. A learned third on the open data would be a 1–2 voxel shell.
- **E2, layers are a function of the borders.** Distance-based and Laplace thirds agree on 88 % (p10–p90 87–89 %; median |Δt| 0.044) of wall
  voxels; the coordinate choice is a minor term.

  A smooth border error of SD 0.5 mm leaves the whole-myocardium Dice at 0.976, but the subendocardial third
  falls to 0.927. A systematic 0.5 mm inward shift of the endocardium (trabeculae counted as wall) costs that
  third 12 points (Dice 0.877) Dice, while the myocardium keeps 0.980.

  So a myocardium Dice says little about layers. The **borders** must be measured.
- **E2, scar extent survives border error better than layer Dice does.** For synthetic subendocardial scar of
  known depth in the LAD segments:
  - the segment transmurality read back on borders perturbed by SD 1.0 mm has median error **2.6**
    percentage points (p90 7.3);
  - it falls in the right 25-point bin **85 %** of the time.

  The clinically used quantity is more robust than the layer masks. That is a reason to report transmurality,
  not third-by-third Dice.

### 2.3 Rejected options

- **Transmural thirds as nnU-Net classes:** see E1 and E2. There is no reference standard either: no reader
  draws a mid-wall line (§6).
- **AHA segments as learned classes:** a segment boundary is a geometric rule, not an image edge. E3 shows that
  moving the RV-insertion reference by 10° reassigns **15 %** of the myocardium to another segment. A
  network would learn that rule's noise from the labels; computing it keeps one rule, reported with its error.
  - E3 also shows the rule's main weakness. The measured septal (RV-contact) arc has a median of **137°**
    (p10–p90 122–151°), not the 120° that fixed 60° sectors assume. So the inferoseptal–inferior boundary
    misplaces part of the septum in most hearts.
  - Round 2 tests septal sectors proportional to the measured arc. That is a change of rule, not of model.
  - Other frame sensitivities: a 5° axis tilt moves 12 % of the mass to another segment (5 % to another default
    territory); a 10° tilt moves 24 % (10 %); a 5 mm base shift moves 9 % (2.5 %).
- **Both ventricles with layers:** the RV wall is too thin (above), and no stenosis or scar output needs it.

## 3. Clinical outputs, and how they tie to Janus's territories

Each output is reported per AHA segment × layer and per Janus territory (LAD/LCx/RCA; LM is the shared trunk).
Every output says which phase it came from. All of it is **report-only until its reference standard exists**
(§6).

### 3.1 From the rest coronary CTA the project already holds

1. **Wall thickness and thinning.**
   - End-diastolic thinning ≤ 5.5 mm is the CMR definition of regional thinning; 19 % of patients with CAD had it
     (Shah 2013, CMR).
   - The CT threshold is to be calibrated: CTA is often not end-diastolic, and E1 gives the wall thickness
     distribution of the open set by segment.
   - Normal mid-cavity thickness by CMR is 5.3 ± 0.9 mm in women and 6.3 ± 1.1 mm in men (Kawel 2012).
   - **E1 is a warning here.** The open CT labels give a median mid-wall thickness of **9.5 mm** (subject
     medians, p10–p90 8.5–10.5 mm). That is far above the CMR normals.
     - Some of the gap is v1's known label offset and trabeculae counted as wall.
     - Some is that CTA is often reconstructed in systole.
   - A thinning threshold therefore cannot be borrowed from CMR. It must be set on project reads with the §6
     convention and the reconstruction phase recorded.
2. **Subendocardial hypo-attenuation (rest).** Mean HU and its z-score per segment × layer, and the
   subendocardial/subepicardial ratio, as in the transmural perfusion ratio of stress CTP (George 2009: TPR =
   subendocardial/subepicardial attenuation, abnormal < 0.99).
   - On rest CTA this is a scar and severe-ischaemia flag, not an ischaemia test:
     - Nikolaou 2005: rest defects from ischaemia were detected with sensitivity 50 %, "not reliably";
     - Busch 2011: hypo-enhancement on rest CTA for infarct, sens 90 % / spec 80 %; artefacts in 88 % of studies.
   - **E4 adds a caution:** at 1.5 mm with open labels, **27 % (p10–p90 9–50 %)** of subendocardial-third voxels are brighter
     than half-way to the blood pool, and the rest subendo/subepi ratio is **2.1 (p10–p90 1.5–3.8; never < 0.99)** (median HU).
   - The inner third is dominated by blood-pool partial volume and border placement, not by perfusion. So
     a layer attenuation output needs the 0.5 mm grid and a border convention that puts trabeculae in the
     cavity.
3. **Intramyocardial fat (lipomatous metaplasia).**
   - Ichikawa 2009: fat in the LV wall in 62 % of patients after MI vs 3 % of controls, subendocardial in
     94 %, and in 89 % of infarcts ≥ 3 years old.
   - Long-standing infarcts measured −13 ± 37 HU vs 73 ± 14 HU in controls (Nieman 2006).
   - The fat threshold is set in Round 2 from data; −13 HU is a mean, not a cut-off.
4. **Myocardial mass per Janus territory, and the AHA-default mismatch.**
   - Patient-specific territories from the CTA (Voronoi) match histology in swine (r = 0.92–0.96; Ide 2017), and
     relate to SPECT (Kurata 2015).
   - The AHA default assignment is wrong for 23 % of infarcted segments in humans (Ortiz-Pérez 2008).
   - The output ties a Janus stenosis to the mass it supplies, and flags segments whose default territory
     disagrees.

### 3.2 Needing phases the project does not hold (staged, Q4)

5. **Late iodine enhancement (LIE) scar and transmurality** on a 5–15 min delayed scan.
   - Against CMR LGE, a 2025 meta-analysis (Gatti 2025: 14 studies, 526 patients) gives per-segment sens 0.86 /
     spec 0.98 and per-patient 0.96 / 0.95. Dual-energy raises per-segment sensitivity to 0.93.
   - A novice reader reaches 62 % per-segment sensitivity vs 85 % for an experienced one (Palmisano 2020). That is
     a reason for a model.
   - CT-ECV correlates with MRI ECV (r = 0.82, Nacif 2012; r = 0.73, Bandula 2013).
6. **Stress CT perfusion defects and TPR.** CTA+CTP AUC 0.87 for stenosis with a perfusion defect (CORE320,
   Rochitte 2014). Dynamic CTP adds to CTA: per-vessel specificity 89 % vs 72 % (SPECIFIC, Nous 2022).

The layer machinery of §2 is exactly what 5 and 6 need: transmurality of LIE, and TPR. So the rest-CTA work is not
thrown away when those phases arrive.

## 4. CT protocols and phases

| Phase | What it gives Janus-M | In the project? |
|---|---|---|
| ECG-gated coronary CTA, arterial (≈ 0.4–0.5 mm in-plane, < 1 mm slices; Abbara 2016, in-plane derived from 200–250 mm FOV on 512²) | Borders, layers, segments, territories, thickness, rest attenuation, fat | Yes: the CCTA-Pool (`SegQueue/cases`) |
| Late enhancement (5–15 min; dual-energy preferred) | LIE scar, transmurality, ECV with a pre-contrast scan | Not known to be present (Q4) |
| Stress CT perfusion (static or dynamic) | Ischaemia, TPR | Not known to be present (Q4) |
| Non-contrast calcium scan | ECV baseline; non-contrast myocardium (Mannil 2018) | Some pool sources may include one: to be checked by a header census (§9) |

Multi-phase cine (Slicer 4D frames in the pool) could add wall thickening, but that is not in the brief and is
not planned.

## 5. Data

### 5.1 Open data with myocardium labels (verified; §13)

| Set | CT with LV myocardium labels | Labels | Licence / access | Role in India v1 |
|---|---|---|---|---|
| TotalSegmentator v1 (Zenodo 6802614) | 1204 CT, of which 130 are cardiac protocols (115 after excluding the 16 pool subjects) | Model-assisted, all reviewed; **1.5 mm**; v2 notes "myocardium always slightly misaligned" | CC BY 4.0, open | E1–E4 now. Pre-training only; never a border reference |
| TotalSegmentator `heartchambers_highres` (model, not data) | Trained on 1559 CT, ~0.73 × 0.72 × 1.0 mm, val Dice 0.950 (all classes) | — | **Licence: free non-commercial, key required** (Q1) | Janus-M 0's borders; seeds for reads |
| MM-WHS CT | 20 train + 40 test | Manual; 0.78 × 0.78 × 1.6 mm; best test myocardium Dice 0.881 (Payer 2017, Table 2) | **Gated: data access agreement, no redistribution** | External test only, if the lead signs (Q5) |
| ImageCHD | 110 CT (congenital) | 7 classes incl. myocardium | Kaggle; **no licence stated** | Not used for training: abnormal hearts, no licence. 20 ImageCHD patients are in the coronary seal's report-only list, so all ImageCHD stays out |
| AI-CVM Cardiac-CT (arXiv 2607.11287) | 1598 on ImageCAS images | 14 structures (myocardium unverified) | CC BY-NC-ND, gated, "not publicly available" yet | **Never:** its images are ImageCAS, which includes the sealed ImageCAS-X 80 |

Scar and perfusion:
- **No open CT scar (LIE) or CT perfusion dataset with labels was found.** The labelled scar sets are MRI:
  - EMIDEC: 150 LGE exams, CC BY-NC-SA, registration;
  - MyoPS: 45 patients, data agreement.
- They help only a cross-modality idea (not planned).

### 5.2 What the project holds (Girder)

The SegQueue14 pool is 675 coronary-CTA volumes from 468 patients (`configs/segqueue14/pool-2026-10.txt` and
the seal file):
- **350 volumes are not sealed** (`segtrain.pool_seal.apply(..., mode="exclude")`, run on names only);
- **299 of those are also outside Delta's D35 draw** (`experiments/Delta/r10/d35_decision_set_proposal.json`);
- the A34 reserve (78 patients) and, until Q1 of Round 10 is answered, the union of the three candidate draws take
  more.

**The volumes Janus-M may use are fixed only when #116 freezes the coronary sets.** Until then Janus-M touches no
pool volume (§7.3).

No pool source is known to carry a late-enhancement or perfusion phase. Confirming that is a header census of the
Girder items (series description, delay), which needs Girder credentials India does not hold (§9, ask 2).

## 6. Reference standard

| Quantity | Reference | Why |
|---|---|---|
| Endocardial and epicardial borders | **Two independent reads per case** on the 0.5 mm CTA. Readers correct `heartchambers_highres` seeds in a SegQueue-like tool (as D23/D26 did for the coronaries). Convention: papillary muscles and trabeculae to the blood pool; the basal limit at the mitral and aortic valve planes | The only quantity a person can draw; inter-read disagreement sets the gate. Zreik 2016: second observer Dice 0.90, MAD 0.6 mm on LV myocardium in CCTA (Table 1), so the gate must be in mm |
| Layers, segments | **Derived** from the reference borders by the same code (`lvgeom.py`) | No one draws a mid-wall line; agreement of derived layers is reported, not gated |
| Territories | None in humans on CT (Ide 2017 is swine histology). Report-only, with the AHA-default comparison | — |
| Rest hypo-attenuation, fat, thinning | Report-only. A reference needs CMR LGE in the same patients (Q4) | Arterial-phase scar detection vs CMR: sens 91 % / spec 81 % (Sanz 2006); infarct size underestimated |
| LIE scar | CMR LGE in the same patient, or LIE read by an experienced reader (Palmisano 2020: reader experience matters) | Meta-analysis per-segment sens 0.86 vs LGE (Gatti 2025) |

## 7. Model, recipe, deciding metric, splits, seal

### 7.1 Janus-M 0: no training

- `heartchambers_highres` borders.
- India's geometry (`experiments/JanusM/India/lvgeom.py`, to be shipped by a `role:swe` issue as a
  tested module).
- Janus's coronary masks for territories.

Cost: about 1 GPU-minute per CT.

### 7.2 Janus-M 1: trained only if Janus-M 0 fails the gate

- nnU-Net v2 ResEnc with the five classes of §2.1.
- **0.5 mm isotropic**, the Janus 0 recipe (`trillium/icx4`: 256³ patch, DiceCE, 1000 epochs) with mirroring off.
  The LV has a handedness, and the AHA frame needs it.
- Trained on the corrected first reads of the Janus-M train split, with TotalSegmentator v1 cardiac subjects as
  extra low-weight samples.
- E2 is the reason for 0.5 mm. A uniform voxel quantisation error has SD ≈ 0.29 voxel: about 0.43 mm at
  1.5 mm and 0.14 mm at 0.5 mm. On the E2 curve, 0.43 mm already costs the subendocardial third several Dice points
  (σ = 0.5 mm gives 0.927).

### 7.3 Splits and the Janus-M seal (from the start)

**Universe:**
- Pool patients the coronary plan marks trainable after #116. That is:
  - not in the D27/D32/D33 seal (`segtrain.pool_seal`, patient-level, refuse mode);
  - not in the D35 decision set or its candidate union;
  - not in the A34 reserve.
- **No ImageCHD** and **no ImageCAS** volume (the sealed ImageCAS-X 80 are ImageCAS).
- Janus-M's own code refuses these through the same `segtrain.pool_seal` guard plus a Janus-M list file.

**Janus-M seal:**
- **40 patients**, drawn at patient level by salted hash within source (`asclepius-janusm-seal-r1:`), frozen
  before any Janus-M read of them exists.
- Double-read, never trained on, scored once at acceptance.
- Size: 40 patients give a 95 % CI half-width of about ±0.06 mm on a per-patient border ASSD difference, if the
  per-patient SD of the difference is about 0.2 mm (t₃₉ · 0.2/√40 ≈ 0.064). The SD is an assumption, re-powered
  in Round 2 on the first double reads, as the coronary seal was.

**Janus-M decision set:** 20 patients, drawn the same way, double-read. It decides model questions (Janus-M 0 vs 1).

**Train:** every other allowed patient's reads.

### 7.4 The deciding metric and the gate

- **Deciding metric:** per-patient **mean symmetric surface distance (ASSD, mm) of the endocardial and of the
  epicardial border**, model vs each read, averaged over the two reads.
- **Gate (acceptance on the Janus-M seal):** for each border, the upper 95 % CI bound of (model-vs-read ASSD −
  read-vs-read ASSD) ≤ **0.25 mm**.
- Why 0.25 mm: in E2 a smooth error of SD 0.25 mm costs the subendocardial third about 1 Dice point (0.989).
  The p90 of the segment scar-transmurality error stays below 1 percentage point (0.8).
- At SD 0.5 mm those become 0.927 and 3.2 points; at 1.0 mm, 0.823 and 7.3 points, with 15 % of segments in the
  wrong transmurality bin.
- **Report, not gated:**
  - myocardium Dice;
  - Dice of each third, derived;
  - per-segment thickness error (mm);
  - AHA-segment agreement;
  - territory mass, and its mismatch with the AHA default.

Myocardium Dice is reported, not gated, for two reasons:
- In E2 a 0.5 mm inward endocardial shift costs the myocardium only about 2 Dice points but the inner third
  about 15. Dice hides exactly the error that matters for layers.
- Published myocardium Dice on CT is 0.88 (MM-WHS winner, Payer 2017), 0.91 (Zreik 2018, MAD 0.7 mm) and 0.94
  (TotalSegmentator v1 at 1.5 mm). On the E2 curve those correspond to smooth border errors of roughly 1.0–1.5 mm
  SD (myocardium Dice 0.934 at 1.0 mm, 0.891 at 1.5 mm).
- At that error the subendocardial third's Dice is 0.72–0.82. The segment scar-transmurality error has a p90 of
  7–11 points, and 15–21 % of segments fall in the wrong 25-point bin.
- The mapping is approximate: it is our error model on our shapes, not those papers' errors. But it shows that a
  "state-of-the-art" myocardium Dice does not by itself give usable layers.

## 8. Compute (Fir, account `def-aso22`; the lead runs every job)

| Job | What | Waits on | GPU-h |
|---|---|---|---|
| M1 | `heartchambers_highres` on the 115 open TotalSegmentator cardiac subjects (pool subjects excluded); CPU read-out `m1_compare.py`: two independent border sources compared, Dice, ASSD per border, derived thirds | Licence typed by the lead (Q1) | ≤ 2 |
| M2 | `heartchambers_highres` seeds on the Janus-M universe (§7.3) | #116, Q1, Q2 | ≈ 3 (≈ 250 volumes) |
| M3 | Janus-M 0 geometry + territories, using the coronary plan's Job P0 Janus 0 predictions (no new GPU) | P0, M2 | 0 (CPU) |
| M4 | Janus-M 1 training, one fold (decision set = val), only if Janus-M 0 fails the gate | ≥ 60 double-read train patients | ≈ 50–70 (icx4's Fir estimate) |
| M5 | Janus-M 1 second seed, only if M4 passes and a seed claim is needed | M4 | ≈ 50–70 |

**Round 1 total that will certainly run: ≈ 5 GPU-h. Upper bound: ≈ 145 GPU-h.**

Job M1, exactly (login node first, then one job). The script and its header are
`experiments/JanusM/India/fir/m1_heartchambers.sh`:

```sh
module load StdEnv/2023 python/3.11.5
python -m venv $HOME/jm-venv && source $HOME/jm-venv/bin/activate
pip install TotalSegmentator remotezip nibabel scipy scikit-image
totalseg_set_license -l <licence number: typed by the lead, never committed>
totalseg_download_weights -t heartchambers_highres
mkdir -p $SCRATCH/janusm && cd $SCRATCH/janusm
git clone -b dev https://github.com/christianGRogers/Asclepius.git repo || git -C repo pull --ff-only
python repo/experiments/JanusM/India/fetch_ts_cardiac.py ts
sbatch repo/experiments/JanusM/India/fir/m1_heartchambers.sh
# when it ends (CPU, login node):
python repo/experiments/JanusM/India/fir/m1_compare.py ts/Totalsegmentator_dataset ts/hc ts/m1_compare.json
```

Send back `ts/m1_compare.json` (numbers only).

M2–M5 need a Janus-M list file and a pool-reading launcher. Those are `role:swe` work, opened from #130 once the
judge rules. Their commands follow the `trillium/icx4` pattern and are written when the code exists, not
invented now.

## 9. What would change this plan

| Result | Change |
|---|---|
| M1: `heartchambers_highres` vs TotalSegmentator v1 border ASSD ≫ 0.5 mm, or a systematic endocardial offset | Expected in part (v1's misalignment). If the offset is large, Janus-M 0 uses the highres model only and the v1 data is dropped from M4 |
| First 20 double reads: read-vs-read endocardial ASSD > 0.6 mm (worse than Zreik's second observer) | Tighten the border convention (trabeculae) before more reads; layers stay report-only until it is met |
| Janus-M 0 passes the gate on the decision set | No training. Janus-M 1 (M4) is not run; the budget moves to the Q4 phases |
| A header census finds late-enhancement or perfusion series in the pool | Section 3.2 moves forward: LIE scar becomes a learned class (a scar mask inside the wall, reference LIE read) |
| The lead declines the TotalSegmentator licence | Janus-M 0 is a model trained on TotalSegmentator v1 cardiac data (CC BY 4.0, 1.5 mm). M4 runs early, and the reads start from that model's seeds |
| E2 at 0.5 mm shows layer error dominated by the geometry choice (Laplace vs distance) | Not the case in E2 (§2.2); kept as a check |

## 10. Decisions for the lead

1. **Q1, TotalSegmentator `heartchambers_highres` licence (free for non-commercial use, needs a key).** May
   Janus-M use it, the lead typing the key on Fir (never committed)?
   - *Recommended: yes*, if Asclepius is non-commercial research. It removes a training run and gives seeds at
     ~0.7 mm.
2. **Q2, readers for the borders.** Janus-M needs two independent border reads on about 40 (seal) + 20 (decision)
   + 60 (train) patients. These are seeds corrected in a SegQueue-like tool.
   - Who reads, and does this compete with the coronary team's D23 queue?
   - *Recommended:* a separate small queue (SegQueue-M), seal and decision patients first. A `role:swe` issue once
     ruled.
3. **Q3, the border convention.** Trabeculae and papillary muscles to the blood pool, basal limit at the valve
   planes.
   - *Recommended: yes.* E2 and E4 show the inner third is where the convention matters most.
4. **Q4, scar and perfusion phases.** No open CT dataset has LIE or CTP labels, and none is known on Girder. Should
   the project seek a source with late-enhancement CT (ideally with CMR LGE in the same patients), or stress CTP?
   Any request is the lead's, outside the repository (D19, D31).
   - *Recommended:* yes for LIE with paired CMR. It is the one reference that turns §3.1's flags into validated
     scar outputs.
   - Until then, every scar or ischaemia output is labelled report-only.
5. **Q5, MM-WHS.** Its data agreement forbids redistribution. Sign it for an external test of borders only, never
   uploaded to Girder?
   - *Recommended:* yes, low priority.
6. **Q6, the Janus-M universe.** Janus-M uses only pool patients the coronary plan marks trainable after #116, and
   no ImageCHD or ImageCAS volume.
   - *Recommended: confirm.* It keeps every coronary seal and D35 patient out by construction, at the cost of a
     smaller pool.

## 11. Held-out data: how Janus-M keeps the coronary seals apart (disclosure)

The pool reuses public case numbers. The pool's 16 TotalSegmentator volumes (`TotalSegmentator-cardiac__sNNNN`,
from v2.0.1) include sealed patients and two of Delta's D35 draw. **India's experiments never opened, downloaded,
read or scored any of them.**

How that is enforced:
- `fetch_ts_cardiac.pool_subjects()` collects every TotalSegmentator id named by four sources:
  - the pool list;
  - the seal file;
  - every Round 10 decision-set proposal (Atlas, Bridge, Delta);
  - Delta's D35 draw.

  It refuses to run with fewer than the 16 ids found today.
- The fetcher skips and deletes those subjects. `lvgeom.load_subject` raises before reading one.
- The first, unguarded fetch ran for a few minutes and stopped at s0111, below the first held-out id (s0356). No
  held-out directory, log line or output exists.
- India used TotalSegmentator **v1**. To check that an s-number names the same patient in both versions, India
  compared the two `meta.csv` files (no images) over the 1204 shared ids:
  - sex and study type agree for 1203;
  - ages differ by at most 4 years (anonymisation jitter);
  - institute letters are relabelled consistently (H→I, D→E, F→G…).

  So refusing by s-number is refusing by patient. No other v1 subject shares a held-out subject's age, sex,
  institute and study type.
- No ImageCAS, ImageCHD or other pool-source data was used. The ImageCAS sealed list
  (`trillium/icx4/sealed_test.json`) is therefore not touched, and §5.1 rules out ImageCAS-derived label sets.

## 12. Risks

- **The non-commercial licence** (Q1) may not fit the project. The fallback is a 1.5 mm-trained model, which E1
  says is poor for layers.
- **Rest CTA does not show ischaemia reliably** (Nikolaou 2005; Busch 2011). The plan says so and does not promise
  it. The ischaemia link is the territory mass at risk plus Janus's stenosis, not a perfusion read.
- **E1–E4 use open labels at 1.5 mm, upsampled.** The geometry sensitivities hold for any wall shape. The absolute
  numbers (thickness, E4's ratio) inherit v1's misaligned myocardium and are not normal values.

## 13. Citations

Every entry was checked on a PubMed, PMC, publisher, arXiv or dataset page (number and location as cited).
Numbers marked "abstract" are from the abstract.

- **[Abbara 2016]** Abbara S, et al. SCCT guidelines for the performance and acquisition of coronary CT angiography. *J Cardiovasc Comput Tomogr* 2016;10(6):435–449. doi:10.1016/j.jcct.2016.10.002. Slice width < 1.0 mm, 512 matrix, FOV 200–250 mm (§10.4, §10.11). The in-plane size is derived.
- **[Bandula 2013]** Bandula S, et al. Measurement of myocardial ECV by equilibrium contrast-enhanced CT: validation against histologic findings. *Radiology* 2013;269(2):396–403. doi:10.1148/radiology.13130130. CT vs MRI ECV r = 0.73 (abstract).
- **[Bayer 2012]** Bayer JD, Blake RC, Plank G, Trayanova NA. A novel rule-based algorithm for assigning myocardial fiber orientation to computational heart models. *Ann Biomed Eng* 2012;40(10):2243–2254. doi:10.1007/s10439-012-0593-5.
- **[Bayer 2018]** Bayer J, et al. Universal ventricular coordinates. *Med Image Anal* 2018;45:83–93. doi:10.1016/j.media.2018.01.005.
- **[Busch 2011]** Busch JL, et al. Myocardial hypo-enhancement on resting CTA images accurately identifies myocardial hypoperfusion. *J Cardiovasc Comput Tomogr* 2011;5(6):412–420. doi:10.1016/j.jcct.2011.10.006. Infarct sens 90 % / spec 80 %; artefacts in 88 % (abstract).
- **[Cerqueira 2002]** Cerqueira MD, et al. Standardized myocardial segmentation and nomenclature for tomographic imaging of the heart. *Circulation* 2002;105(4):539–542. doi:10.1161/hc0402.102975. 17 segments and the default territories.
- **[CORE320]** Rochitte CE, et al. *Eur Heart J* 2014;35(17):1120–1130. doi:10.1093/eurheartj/eht488. CTA+CTP AUC 0.87 (abstract).
- **[Gatti 2025]** Gatti M, et al. Diagnostic accuracy of late iodine enhancement on cardiac CT for myocardial tissue characterization: a systematic review and meta-analysis. *Eur Radiol* 2025;35(6):3054–3067. doi:10.1007/s00330-024-11283-5. Per-segment sens 0.86, spec 0.98; per-patient 0.96 / 0.95; DECT per-segment sens 0.93 (abstract).
- **[George 2009]** George RT, et al. Adenosine stress 64- and 256-row detector CTA and perfusion imaging… transmural extent of perfusion abnormalities. *Circ Cardiovasc Imaging* 2009;2(3):174–182. doi:10.1161/CIRCIMAGING.108.813766. TPR definition (abstract). Abnormal TPR < 0.99 (Results).
- **[Ichikawa 2009]** Ichikawa Y, et al. Adipose tissue detected by multislice CT in patients after myocardial infarction. *JACC Cardiovasc Imaging* 2009;2(5):548–555. doi:10.1016/j.jcmg.2009.01.010. 62 % vs 3 %; subendocardial 94 % (abstract).
- **[Ide 2017]** Ide S, et al. Cardiac CT-derived myocardial mass at risk using the Voronoi-based segmentation algorithm: a histological validation study. *J Cardiovasc Comput Tomogr* 2017;11(3):179–182. doi:10.1016/j.jcct.2017.04.007. r = 0.92–0.96 (abstract).
- **[Jones 2000]** Jones SE, Buchbinder BR, Aharon I. Three-dimensional mapping of cortical thickness using Laplace's equation. *Hum Brain Mapp* 2000;11(1):12–32. doi:10.1002/1097-0193(200009)11:1<12::AID-HBM20>3.0.CO;2-K.
- **[Kawel 2012]** Kawel N, et al. Normal LV myocardial thickness… MESA. *Circ Cardiovasc Imaging* 2012;5(4):500–508. doi:10.1161/CIRCIMAGING.112.973560. 5.3 ± 0.9 / 6.3 ± 1.1 mm (abstract).
- **[Kim 2000]** Kim RJ, et al. The use of contrast-enhanced MRI to identify reversible myocardial dysfunction. *N Engl J Med* 2000;343(20):1445–1453. doi:10.1056/NEJM200011163432003. Function improved in 78 % of segments without hyperenhancement and in 1 of 58 with > 75 % transmurality (abstract).
- **[Kurata 2015]** Kurata A, et al. Quantification of the myocardial area at risk using coronary CTA and Voronoi algorithm-based myocardial segmentation. *Eur Radiol* 2015;25(1):49–57. doi:10.1007/s00330-014-3388-2.
- **[Mannil 2018]** Mannil M, et al. Texture analysis and machine learning for detecting myocardial infarction in noncontrast low-dose CT. *Invest Radiol* 2018;53(6):338–343. doi:10.1097/RLI.0000000000000448. AUC 0.78 (abstract).
- **[MM-WHS]** Zhuang X, et al. Evaluation of algorithms for multi-modality whole heart segmentation. *Med Image Anal* 2019;58:101537. doi:10.1016/j.media.2019.101537. 20 + 40 CT (§2); access by data agreement (dataset page).
- **[Nacif 2012]** Nacif MS, et al. Interstitial myocardial fibrosis assessed as ECV with low-radiation-dose cardiac CT. *Radiology* 2012;264(3):876–883. doi:10.1148/radiol.12112458. r = 0.82 (abstract).
- **[Nieman 2006]** Nieman K, et al. Differentiation of recent and chronic myocardial infarction by cardiac CT. *Am J Cardiol* 2006;98(3):303–308. doi:10.1016/j.amjcard.2006.01.101. −13 ± 37 vs 73 ± 14 HU (abstract).
- **[Nikolaou 2005]** Nikolaou K, et al. Assessment of myocardial perfusion and viability from routine contrast-enhanced 16-detector-row CT of the heart. *Eur Radiol* 2005;15(5):864–871. doi:10.1007/s00330-005-2672-6. Rest ischaemia sensitivity 50 % (abstract).
- **[Nous 2022]** Nous FMA, et al. Dynamic myocardial perfusion CT for the detection of hemodynamically significant CAD (SPECIFIC). *JACC Cardiovasc Imaging* 2022;15(1):75–87. doi:10.1016/j.jcmg.2021.07.021. Per-vessel spec 89 % vs 72 % (abstract).
- **[Ortiz-Pérez 2008]** Ortiz-Pérez JT, et al. Correspondence between the 17-segment model and coronary arterial anatomy using contrast-enhanced cardiac MRI. *JACC Cardiovasc Imaging* 2008;1(3):282–293. doi:10.1016/j.jcmg.2008.01.014. 23 % mismatch (abstract).
- **[Palmisano 2020]** Palmisano A, et al. Late iodine enhancement cardiac CT for detection of myocardial scars: impact of experience in the clinical practice. *Radiol Med* 2020;125(2):128–136. doi:10.1007/s11547-019-01108-7. Per-segment 85 % vs 62 % (abstract).
- **[Payer 2017]** Payer C, Štern D, Bischof H, Urschler M. Multi-label whole heart segmentation using CNNs and anatomical label configurations. STACOM 2017, LNCS 10663:190–198. doi:10.1007/978-3-319-75541-0_20. MM-WHS CT test myocardium Dice 88.1 % (Table 2).
- **[Sanz 2006]** Sanz J, et al. Detection of healed myocardial infarction with multidetector-row CT and comparison with cardiac MR delayed hyperenhancement. *Am J Cardiol* 2006;98(2):149–155. doi:10.1016/j.amjcard.2006.01.093. Sens 91 % / spec 81 % (abstract).
- **[Shah 2013]** Shah DJ, et al. Prevalence of regional myocardial thinning and relationship with myocardial scarring in patients with coronary artery disease. *JAMA* 2013;309(9):909–918. doi:10.1001/jama.2013.1381. Thinning ≤ 5.5 mm; 19 % (abstract).
- **[Termeer 2010]** Termeer M, et al. Patient-specific mappings between myocardial and coronary anatomy. Dagstuhl Follow-Ups 1, 2010:196–209. doi:10.4230/DFU.SciViz.2010.196.
- **[TS]** Wasserthal J, et al. TotalSegmentator: robust segmentation of 104 anatomic structures in CT images. *Radiol Artif Intell* 2023;5(5):e230024. doi:10.1148/ryai.230024.
  - Dataset: Zenodo 6802614, CC BY 4.0.
  - `heartchambers_highres` classes, training set, val Dice 0.950 and licence: the repository's `resources/heartchambers_highres_details.md` and README.
  - The v1 misalignment note: `resources/improvements_in_v2.md`.
- **[Zreik 2016]** Zreik M, et al. Automatic segmentation of the left ventricle in cardiac CT angiography using convolutional neural networks. ISBI 2016:40–43. arXiv:1704.05698. Second observer Dice 0.90, MAD 0.6 mm (Table 1).
- **[Zreik 2018]** Zreik M, et al. Deep learning analysis of the myocardium in coronary CT angiography for identification of patients with functionally significant coronary artery stenosis. *Med Image Anal* 2018;44:72–85. doi:10.1016/j.media.2017.11.008. Myocardium Dice 91.4 ± 2.1 %, MAD 0.7 mm; FFR AUC 0.74 (abstract).

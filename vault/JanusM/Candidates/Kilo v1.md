---
tags: [janus-m, candidate, round1, myocardium, layers, transmurality, aha17, territories, fir]
author: Kilo
round: 1
version: 1
updated: 2026-10-30
issue: christianGRogers/Asclepius#130
---

# Kilo v1: learn the wall, compute the layers, let Janus draw the territories

## 0. In one paragraph

**Janus-M learns one thing that needs a human label: the left-ventricular wall.** The labels are LV myocardium,
LV blood pool and RV blood pool, on ECG-gated coronary CTA. **Every "layer" is computed from that wall, not
learned:**
- a continuous transmural depth from Laplace's equation, cut into subendocardial, mid-wall and subepicardial thirds;
- wall thickness;
- the AHA 17 segments;
- each segment's supplying artery, read from **Janus's own four-class coronary tree** for that patient, not from
  the textbook map. That map is wrong in 72 % of patients for at least one segment (Javadi 2010).

**The clinical outputs come in two stages.**
- **Stage A runs on what the project holds: rest CCTA.** Segmental wall thickness and thinning, LV mass,
  myocardial fat, and rest attenuation per layer, each placed beside Janus's stenosis in the same territory.
- **Stage B needs paired CT and MRI data the project does not have:** late-iodine-enhancement scar with its
  transmurality, and stress perfusion defects. No public CT dataset has scar or perfusion labels (checked).
  Because the layers are geometry, Stage B reuses them unchanged on any phase.

**My experiments show why Stage A is built this way:**
- the layers stand or fall on the endocardial border. A 1 mm endocardial bias leaves myocardium Dice at
  0.979 but moves a subendocardial scar's transmurality bin in 12.5 % (37.5 % for mid-depth scars) of segments (E2);
- rest attenuation ratios are dominated by partial volume at 1.5 mm, so they stay report-only (E3).

**So the deciding metric is clinical, not Dice:** segmental transmurality agreement (STA) on a 20-patient Janus-M
seal, frozen now. Guards on endocardial bias and thickness error go with it.

**Compute:** about 32–35 Fir GPU-hours to the first model. It runs in three jobs with exact commands (§8).

**New evidence this round** (CPU; code in `experiments/JanusM/Kilo/`; no coronary-sealed, reserved or D35 patient
read; public data only for images):
- [[Kilo - E0 What Janus-M may use on Girder]]. After the coronary seal, its reserve and every D35 draw are
  refused, Janus-M has 292 volumes. Only **20** of them are adult, sub-millimetre, good-quality CCTA (Taiwan-AICUP).
- [[Kilo - E1-E3 Layers are geometry, and the endocardial border decides transmurality]]. On 39 public
  TotalSegmentator cardiac CTs, the layer geometry runs end to end, with these results:
  - wall thickness 9.6 mm median, about 19 voxels across at 0.5 mm;
  - boundary-error sensitivity (E2);
  - rest transmural attenuation ratios and how far they move (E3).
- A citation check, every item opened at source: `experiments/JanusM/Kilo/citations.md`.

**Held-out cases: none opened (checked in code).** The pool reuses public case numbers. Before any download,
`experiments/JanusM/Kilo/heldout.py` collects every TotalSegmentator id named in:
- the pool seal and the pool list;
- the ImageCAS-X seal;
- every Round 10 D35 draw (Atlas, Bridge, Crucible, Delta, Foxtrot).

That is 16 ids, which also covers the reserve. The fetch and the experiment refuse them; 12 of the 71 public
cardiac cases were refused this way. No public copy of ImageCHD, ImageALCAPA, Taiwan or MM-WHS was downloaded.
On Girder, `allowed_volumes.py` refuses by patient through `segtrain.pool_seal`. **Any later Janus-M step that
uses a public copy of a pool source must call the same refusal first.** ImageCHD's Kaggle release, for one,
contains the 20 report-only sealed patients.

## 1. The class schema, and what "layers" means

### 1.1 What is learned (the label set)

| Value | Class | Convention |
|---|---|---|
| 0 | background | everything else |
| 1 | **LV myocardium** | compact myocardium from the mitral annulus plane to the apex, septum included. **Papillary muscles and trabeculae belong to the blood pool (2)**, so the endocardial border is the compact-wall border. The basal limit is the plane of the mitral annulus; the LV outflow tract above the aortic annulus is not myocardium |
| 2 | **LV blood pool** | the cavity, with papillary muscles and trabeculae (above) |
| 3 | **RV blood pool** | the RV cavity, to the pulmonary valve. It is context only: it gives the septum's direction and the RV insertion points the 17-segment model needs |

The schema is LV only. Three reasons:
1. Coronary ischaemia and infarct scar are scored on the LV in every reference standard used below: the AHA 17
   segments, LGE transmurality (Kim 2000), CTP's TPR (George 2009) and the LIE-CT meta-analysis (Gatti 2025).
2. The RV free wall is 3–4 mm. That is about 7 voxels at 0.5 mm, against about 20 for the LV (E1). No CT study
   in the citation check validates RV scar.
3. RV myocardium can be added later as a value 4 without relabelling 1–3.

### 1.2 What is computed (no label, a definition)

From classes 1–3, for every myocardium voxel (`experiments/JanusM/Kilo/layers.py`):

| Output | Definition |
|---|---|
| **Transmural depth t ∈ [0, 1]** | Laplace's equation on the wall (Jones 2000). t = 0 on faces touching the LV blood pool (endocardium), t = 1 on faces touching anything else (epicardium). The faces touching the left atrium and the aorta, the basal opening, are no-flux |
| **Layers** | subendocardial t < 1/3, mid-wall 1/3 ≤ t < 2/3, subepicardial t ≥ 2/3. The thirds are a reporting convention on a continuous t; Stage B scores transmurality on t itself |
| **Wall thickness** | d_endo + d_epi − one voxel (Euclidean, mm), per voxel; segmental median |
| **AHA 17 segments** (Cerqueira 2002) | The LV long axis is the principal axis of wall + cavity, oriented apex → base by the left atrium. Basal, mid and apical thirds of the cavity's length; the apex cap is wall beyond the cavity. The circumferential zero is the septum's centre, the direction of the RV blood pool's centroid. Sectors are 60° (basal, mid) and 90° (apical). Version 1 approximates the RV insertion points by the RV centroid; Round 2 replaces that with the two insertion points found where classes 1 and 3 meet |
| **Territory** (patient-specific) | Each epicardial surface voxel goes to the nearest of Janus's LAD / LCx / RCA (LM to its continuation), by geodesic distance over the epicardial surface. It is carried inward along t, and a segment's territory is its majority. The AHA default map is reported beside it, never instead of it |

**Why the layers are not learned**, as classes or a regression:
1. **No reference standard exists for a layer border.** A "third" is a definition applied to the wall, not an
   anatomical boundary. A hand-drawn third would be the same formula applied by eye, with reader noise added.
2. **The error of a computed layer is the error of the wall,** and E2 measures how it propagates. A learned
   layer adds its own error on top, and nothing guarantees it stays nested in the wall.
3. **Stage B reuses the geometry unchanged.** LIE scar and CTP defects are scored on t and on segments. A
   learned-layer model would have to be retrained for each new protocol; the wall model needs only the wall.
4. **It is one network,** three classes and about 30 GPU-h (§8), instead of 1 + 3 + 17 learned classes with no
   labels for the last 20.

### 1.3 Phase

The thickness and thinning outputs are end-diastolic quantities: Shah 2013's thinning threshold is end-diastolic
on CMR. They are reported only on a diastolic reconstruction (60–80 % R-R, or as the DICOM states). Where a pool
patient has several phases (Mendeley-SDN `_diast/_syst`, RIDER `_pNN`), the diastolic one is used. The other
outputs are reported for any phase, with the phase recorded.

## 2. The clinical outputs, and how they tie to the coronary territories

Each output is reported **per segment and per Janus territory**, next to Janus's stenosis findings in the vessel
supplying that territory. The report row is the unit: *vessel → its stenosis (Janus) → its territory (computed) →
the territory's wall findings (Janus-M)*.

### Stage A: rest CCTA (the project's data; Round 2–3)

| Output | Definition | Evidence it matters | Status |
|---|---|---|---|
| A1 segmental wall thickness; **thinning** | median end-diastolic thickness per segment; thinning ≤ 5.5 mm | ≤ 5.5 mm marks chronic infarct on CMR, but 18 % of thinned regions have limited scar and recover (Shah 2013). Normal mid-cavity thickness is 5.3 / 6.3 mm (women / men) on CMR (Kawel 2012) | Planned (Round 2–3), as a measurement. The CT threshold needs validation (Stage B) |
| A2 LV myocardial mass, cavity volume | wall volume × 1.05 g/ml; cavity volume | standard | Planned (Round 2–3) |
| A3 **intramyocardial fat** | voxels < −10 HU (candidate) inside the wall, per layer and segment | LV fat in 62 % of post-MI patients vs 3 % of controls on CT, 94 % subendocardial (Ichikawa 2009); mean −29.6 HU (Ahn 2009) | Planned, report-only; threshold to be set on data |
| A4 rest attenuation per layer | mean HU of each third per segment; TPR = subendocardial / subepicardial (George 2009) | Rest CCTA myocardial texture separates FFR-significant stenosis at AUC 0.74 (Zreik 2018) and 0.76 (van Hamersvelt 2019) | **Report-only.** E3, at 1.5 mm: per-segment rest TPR has median 1.93 [IQR 1.04, 2.90], and 1 mm boundary error moves it by > 0.05 in 48 % of segments. That is partial volume, not physiology. Repeated on CCTA after M0 |
| A5 territory map | patient-specific segment → vessel; mismatch with the AHA default listed | 23 % of infarcted segments are discordant with the default (Ortiz-Pérez 2008); 72 % of patients differ in ≥ 1 segment (Javadi 2010) | Planned; needs Janus on the case (M2) |

### Stage B: needs protocols and references the project does not hold

| Output | Protocol | Reference standard | Evidence |
|---|---|---|---|
| B1 **scar extent and transmurality** per segment (bins 0, 1–25, 26–50, 51–75, 76–100 %, on t) | late iodine enhancement CT (LIE), 5–10 min after contrast | **LGE-CMR**, registered | LIE vs LGE: segment sensitivity 0.86, specificity 0.98 (Gatti 2025, 14 studies); transmurality predicts recovery (Kim 2000) |
| B2 **perfusion defect** per layer and territory | stress CT perfusion (static or dynamic) | invasive FFR ≤ 0.80, or stress CMR / PET | CTP vs FFR: vessel sens 0.78 / spec 0.86 (Takx 2015); CTA+CTP AUC 0.87 (CORE320, Rochitte 2014); TPR (George 2009) |
| B3 extracellular volume | pre- and post-contrast CT | CMR ECV | r = 0.82 (Nacif 2012) |

No public CT dataset with scar or perfusion labels exists (citation check, item 22). Stage B therefore needs a
paired-imaging export from the lead's own institution, a gated route (D19). It is the lead's question (Q6). This
plan contains no request to anyone (D31).

## 3. CT protocols and phases

- **Stage A:** ECG-gated coronary CTA, any vendor. Slice ≤ 0.75 mm, in-plane ≤ 0.5 mm, contrast in the LV.
  Diastolic phase for A1. All 20 Janus-M seal patients and every adult training source must state their spacing
  correctly; spacing-suspect sets are training-only (E0).
- **Stage B:** the same CCTA plus a LIE acquisition (and optionally stress CTP), with LGE-CMR (and FFR) within a
  fixed window. No such data is on Girder.

## 4. The data

### 4.1 Public, with myocardium labels

| Source | Cases | Labels | Licence / access | Use in Kilo v1 |
|---|---|---|---|---|
| TotalSegmentator v1 (Zenodo 6802614) | 1204 CT; 71 cardiac-protocol ("ct heart", "ct coronary arteries", "ct aortic valve"). **12 of the 71 are coronary held-out pool patients** (the pool reuses the public s-numbers), so 59 remain; 40 used in E1–E3 | LV myocardium, 4 chambers. **Model-made** labels (in-house nnU-Net), 1.5 mm isotropic | CC BY 4.0, open | training (weak labels); E1–E3 here |
| ImageCHD (Kaggle) | 110 | 7 incl. myocardium, manual; 0.25×0.25×0.5 mm | CC BY-NC 4.0, open | training only, flagged paediatric. **The 20 ImageCHD patients in the coronary seal's report-only stratum are dropped from the Kaggle copy too** |
| MM-WHS CT | 20 labelled (40 test, labels not released) | 7 incl. myocardium, manual; coronary CTA protocol, 0.78 mm | signed DUA, no redistribution | **decision set** (§6), if the lead signs (Q4) |
| CARE 2026 Whole Heart | 60 / 30 / 54 CT train / val / test | 7 incl. myocardium | registration closed; post-challenge route gated, no licence stated | not planned |
| TotalSegmentator `heartchambers_highres` model | — | 7 classes, trained on 1559 images, val Dice 0.950 | licence (free non-commercial); the project already uses one for `coronary_arteries` | **seeds** on the allowed Girder volumes (Job M0) |

Published CCTA LV myocardium accuracy sets the target: Dice 0.91 and mean absolute distance 0.7 mm on 20 images
(Zreik 2018), median Dice 0.920 on 166 patients (Baskaran 2020, JACC CVI). MM-WHS gives no per-structure CT
myocardium number in its text (Zhuang 2019), so none is quoted.

### 4.2 On Girder (E0)

The allowed list is `experiments/JanusM/Kilo/allowed_volumes.json`. It has **292 volumes and 292 patients**:
- adult with a trustworthy grid, 126: TotalSegmentator-cardiac 97 (1.5 mm), **Taiwan-AICUP 20**, EpicardialFat 6,
  STOPSTORM 3;
- flagged paediatric or spacing-suspect, 166.

It refuses, by patient, through the project's guard:
- the coronary seal (369 volumes);
- its reserve (156);
- every D35 draw (48);
- PLOS-Peng2016 (burned-in text).

### 4.3 Keeping the coronary seals apart

- **Janus-M reads only volumes on the allowed list.** Every Fir step re-checks names against
  `segtrain.pool_seal` (`m0_inputs.py` refuses on any sealed name).
- **The reserve and the three non-adopted D35 draws are refused too,** stricter than D37 requires, because A33
  and A34 freeze them. They are added to Janus-M's *training* (never its seal) only by an explicit PR to
  `allowed_volumes.py`, after A35 sizes the seal and the lead answers Round 10's Q1.
- **The ImageCAS-X sealed 80 is never touched:** ImageCAS-X has no myocardium label and is not in any Janus-M
  source.
- **Janus's territories** on a Janus-M case come from Janus 0 run by Janus-M's own job on the allowed list (M2),
  never from P0's predictions, which include D35 volumes.

## 5. The reference standard

| Label | Reference | Floor |
|---|---|---|
| Wall (classes 1–3) | Two independent reads per seal patient by trained readers, each correcting a TotalSegmentator `heartchambers_highres` seed to the §1.1 convention, then adjudicated. Training cases: one read | inter-read endocardial and epicardial surface distance, measured on the seal |
| Layers, segments | **The definition (§1.2) applied to the reference wall.** No separate label | inherits the wall's |
| Territory | the definition applied to the reference coronary tree (the SegQueue14 read, when one exists), else to Janus | — |
| Scar (Stage B) | LGE-CMR, registered to the CT | none available now |
| Perfusion (Stage B) | invasive FFR ≤ 0.80, or stress CMR / PET | none available now |

**Seed anchoring:** reads start from TotalSegmentator seeds, and a model trained on similar seeds could score
well against anchored reads. As the coronary plan does (A40), the reads' edit size against the seed is reported.
**Five of the 20 seal patients are read once from scratch** to measure seed-vs-scratch agreement.

## 6. Model, recipe, deciding metric and splits

### 6.1 Recipe (Round 2 runs it)

- **nnU-Net v2** (Isensee 2021), `3d_fullres`. Three foreground classes. Input: a heart crop (TotalSegmentator
  `total_fast` heart, dilated 15 mm). Resampled to **0.6 mm isotropic**: about 16 voxels across a median wall
  (E1). E2 shows that a 0.5 mm random error costs little, so 0.6 mm is enough and is cheaper than 0.4 mm.
- **Training data:**
  - the TotalSegmentator v1 cardiac cases (weak labels);
  - ImageCHD 88;
  - the `heartchambers_highres` seeds on the 126 adult allowed volumes;
  - **40 of those corrected by one reader** (wave 1).

  Fine-tune on the corrected 40 at a lower LR as a second arm, only if the decision set says so (§6.3).
- **Loss:** nnU-Net's default Dice + CE. A boundary-distance term is a Round 2 arm, decided on the decision set.

### 6.2 The deciding metric: segmental transmurality agreement (STA)

**Definition.** On each case, put a virtual subendocardial scar in each of segments 1–16, at four depths
τ ∈ {0.15, 0.40, 0.65, 0.90}, the centres of Kim's bins. The scar is defined on the reference wall's t, so it is
fixed in the image. Then measure each scar's segmental transmurality twice, once inside the reference wall and
once inside the model's wall. **STA is the share of the 64 (segment, τ) scars whose bin agrees, averaged over
patients.**

**Why STA decides:**
- it is the clinical output B1 needs, measured without any scar label;
- E2 shows Dice is blind to the error that changes it: a 1 mm outward endocardial bias and 0.5 mm random noise give the same Dice (0.979 vs 0.980) but flip 12.5 % vs 3.9 % of bins;
- it is computed by the same code (`exp_layers.py`) on any labelled case.

**Guards**, all reported and none deciding alone:
- endocardial signed surface distance |bias| ≤ 0.5 mm;
- endocardial and epicardial mean surface distance;
- segmental thickness MAE;
- myocardium Dice, for comparison with the literature.

**Acceptance (pre-registered, on the Janus-M seal, one look):** STA ≥ the inter-read STA − 0.05, and every guard
within the inter-read value + 0.3 mm. The first model must also beat the TotalSegmentator `heartchambers_highres`
seed on STA (paired, patient bootstrap); otherwise Janus-M ships the seed model and the geometry.

### 6.3 Splits and the sealed test, from the start

| Set | What | Use |
|---|---|---|
| **Janus-M seal** | **all 20 free Taiwan-AICUP patients** (E0), frozen by this PR: `experiments/JanusM/Kilo/janusm_seal_proposal.json`, adopted when the judge rules | one look at acceptance; never trained on, prelabel kept, no per-case error opened for tuning |
| Decision set | MM-WHS CT 20 (manual labels) if the DUA is signed (Q4); else 15 TotalSegmentator cardiac cases held out by salted hash | recipe questions |
| Training | everything else allowed (§6.1) | nnU-Net 5-fold plan; fold 0 trained |

The seal is small (20). With patient bootstrap it resolves an STA difference of about 0.08 unpaired (per-patient STA SD 0.13 under 1 mm random error; E2), less when paired (from E2's
per-patient spread). That is enough for a first acceptance. **It grows only from released reserve patients
nominated in advance:** the first 20 adult released, by salted hash, are added to the Janus-M seal before any is
read for Janus-M (Q2).

## 7. What would change this plan

| Result | Change |
|---|---|
| Inter-read endocardial bias on the seal > 0.5 mm | The §1.1 convention is not reproducible. Tighten it (papillary and trabeculae rules) before training; STA's ceiling falls |
| `heartchambers_highres` seeds already reach the inter-read guards | Janus-M v0 is the seed model plus the geometry; GPU training waits until Stage B |
| Seed-vs-scratch reads differ more than read vs read | Seal reads are done from scratch; training reads stay seeded |
| Patient-specific territories agree with the AHA map in > 95 % of segments on the seal | Drop the Janus dependency from A5 and report the default map |
| Round 2 finds a public CT scar or perfusion set | Stage B moves forward; the geometry is unchanged |
| The lead obtains paired LIE / LGE data (Q6) | Stage B1 becomes the next model: a fourth class, scar, inside class 1, scored on t |

## 8. Compute (Fir, account `def-aso22`), and the exact commands

| Job | What | Waits on | GPU-h |
|---|---|---|---|
| **M0** | TotalSegmentator `heartchambers_highres` seeds on the 292 allowed volumes, then the layer geometry on CPU | this PR merged; the TotalSegmentator licence on Fir (already used for Job S) | ≈ 3–5 |
| M1 | nnU-Net v2, 3 classes, 0.6 mm, fold 0, 1000 epochs | the Janus-M dataset builder (a `role:swe` issue if the judge adopts this plan); 40 corrected reads | ≈ 28 (100 s/epoch est.; a 2 h timing check first) |
| M2 | Janus 0 on the allowed adult volumes (territories) | P0's launcher (#116) | ≈ 1 |
| **Total to the first Janus-M model** | | | **≈ 32–35** |

### Job M0 (copy-paste; the lead runs it)

```sh
# Fir login node
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius/repo && git pull --ff-only
J=$SCRATCH/janusm/m0 && mkdir -p $J/in $J/ts
python3 experiments/JanusM/Kilo/fir/m0_inputs.py $J/inputs.json     # expect "[m0] 292 volumes, ... GB, sealed 0"
python3 trillium/totalseg/lib/fetch.py $J/inputs.json $J/in          # read-only Girder; resumable
source $HOME/icx4-tseg-venv/bin/activate
export TOTALSEG_HOME_DIR=$SCRATCH/seedcal/totalseg && mkdir -p $TOTALSEG_HOME_DIR
grep -q license_number $TOTALSEG_HOME_DIR/config.json 2>/dev/null || \
  totalseg_set_license -l "<the project's TotalSegmentator licence key>"   # typed by the lead; never committed
totalseg_download_weights -t heartchambers_highres                  # compute nodes have no internet
cat > $J/job.sh <<'EOF'
#!/bin/bash
#SBATCH --job-name=jm-m0 --account=def-aso22 --gpus-per-node=h100:1 --cpus-per-task=12 --mem=64G --time=08:00:00
source $HOME/icx4-tseg-venv/bin/activate
export TOTALSEG_HOME_DIR=$SCRATCH/seedcal/totalseg
J=$SCRATCH/janusm/m0
for f in $J/in/*.nii.gz; do
  n=$(basename $f .nii.gz)
  [ -f $J/ts/$n/heart_myocardium.nii.gz ] && continue
  TotalSegmentator -i $f -o $J/ts/$n -ta heartchambers_highres -d gpu -q || echo "FAILED $n"
done
echo "masks: $(ls $J/ts | wc -l) of $(ls $J/in/*.nii.gz | wc -l)"
EOF
sbatch $J/job.sh                                                     # about 2-5 h
# when finished, login node, CPU (about 20 min):
source $HOME/icx14-venv/bin/activate
python3 experiments/JanusM/Kilo/fir/m0_geometry.py --masks $J/ts --cts $J/in --out $J/m0_geometry.jsonl --np 8
```

- **Check:** `sealed 0` from `m0_inputs.py`, and `masks: 292 of 292`.
- **Send back on #130:** the last line of `m0_geometry.py` and the file `m0_geometry.jsonl`. It holds numbers
  only: volume name, spacing, HU medians, wall thickness and voxels across the wall. It gives Round 2 the real
  CCTA geometry at native resolution, which E1 could only approximate at 1.5 mm.
- The masks stay on Fir. They become the training seeds once the builder exists.

M1 and M2 commands are written when their inputs exist (the builder, #116). Each is the established nnU-Net /
`trillium/icx4` pattern: 1 × H100 80 GB, 12 cores, ≤ 23:50 chained.

## 9. The lead's decisions (numbered, each with a recommendation)

- **Q1. Schema.** Learn LV myocardium, LV blood pool and RV blood pool only, with papillary muscles and
  trabeculae in the blood pool. Compute the layers (Laplace thirds), the 17 segments and the patient-specific
  territories. **Recommend: yes.**
- **Q2. The Janus-M seal.** Freeze all 20 free Taiwan-AICUP patients now as the Janus-M seal: double-read, one
  look. It grows only from released reserve patients nominated by salted hash before any is read.
  **Recommend: yes.** The alternative is to wait for the coronary reserve's release at wave 1, which delays
  every Janus-M measurement by that much.
- **Q3. Who reads, and where.** About 60 wall reads are needed: 20 seal × 2, 5 from scratch, and 40 training
  corrections. At an estimated 20–40 min each, that is 25–40 reader-hours. The reads could be done in 3D Slicer
  outside the queue, or SegQueue14 could get a second protocol, which is a `role:swe` change.
  **Recommend: Slicer for Round 2; queue support only if the judge adopts the plan.**
- **Q4. MM-WHS.** Sign MM-WHS's data access agreement (no redistribution) to get 20 manually labelled adult CTA as
  the decision set (D19: the lead does it, outside the repository). **Recommend: yes.** Without it the decision
  set has only model-made labels.
- **Q5. Phase.** Report thickness and thinning only on diastolic reconstructions, and use the diastolic volume of
  multi-phase patients. **Recommend: yes.**
- **Q6. Stage B data.** Scar and perfusion need paired CT (LIE, and stress CTP if available) with LGE-CMR (and
  FFR). No public set exists. Should the institutional export the coronary plan already names (LHSC / St Joseph's,
  REB) include these protocols? This plan contains no request (D31). **Recommend: yes, as the only route to the
  "scarring" half of the brief.**
- **Q7. Released coronary patients.** When A35 releases reserve patients and Round 10's Q1 releases the
  non-adopted draws, may Janus-M train on the adult ones (the first 20 by salted hash going to the Janus-M seal,
  Q2)? **Recommend: yes.**

## 10. References

Full list with DOIs, the numbers used and where they were seen: `experiments/JanusM/Kilo/citations.md` (28 items;
2 cited without numbers because their full text could not be opened).

---
tags: [janus-m, plans, candidate, myocardium, layers]
author: Juliet
round: 1
version: 1
updated: 2026-10-30
---

# Juliet v1: learn the borders CT can see; compute the layers, segments and territories

## 1. Thesis

Janus-M should **learn four borders and compute everything else.** The network segments the LV myocardium, LV
cavity, RV cavity and LA cavity on CCTA at 0.5 mm. Every "layer" the brief asks for is then deterministic, versioned
code run on those labels:

- the endocardial and epicardial surfaces;
- the transmural depth and its thirds;
- the AHA 17 segments;
- the coronary territory of every myocardial voxel, from Janus's four classes.

There are four reasons, all measured or cited:

1. **No reader can draw a mid-wall line, so a learned layer class has no reference.** A third is a geometric
   definition. Computed from exact borders it is right at every CT voxel size: Dice ≥ 0.95 from 0.25 to 1.5 mm, in a
   5 mm wall too ([[Juliet - Computed transmural thirds are only as good as the borders, at any CT voxel size]]).
2. **What limits the layers is the border error.** A 0.5 mm border RMS, which still scores myocardium Dice 0.955,
   brings the sub-endocardial third of a thinned wall down to Dice 0.76. So the **deciding metric is surface distance
   and segment thickness, not Dice** (§7).
3. **One learned label set serves every clinical output**, today's (CCTA) and tomorrow's (CT perfusion, late
   iodine). The layer outputs need the right definitions, not more classes:
   - Perfusion ratios need a 1 mm guard band, or blood-pool spill turns a true TPR of 0.73 into 0.96
     ([[Juliet - Blood-pool spill hides a subendocardial defect unless the ratio keeps a 1 mm guard band]]).
   - LIE transmurality needs smoothing and a scar-presence call
     ([[Juliet - LIE transmurality bins are recoverable after smoothing, but scar-free walls read 4-12 percent]]).
4. **It runs on what the project holds.** Segments and thickness already compute with no manual input from three
   labels on 12 real CTs ([[Juliet - AHA segments and wall thickness compute from three labels on 12 real CTs, at two voxels per third at 1.5 mm]]).
   Its images are ImageCAS, adult CCTA already on Girder and Fir. The coronary pool is almost entirely closed to
   Janus-M today: 149 of 675 volumes are free, none of them a normal adult CCTA
   ([[Juliet - Only 149 of 675 pool volumes are open to Janus-M today, and none is a normal adult CCTA]]).

**Scope, honestly.** On rest CCTA alone, Janus-M v1 delivers geometry and resting tissue signs. Those are:
- thickness and thinning;
- resting sub-endocardial hypoattenuation;
- intramyocardial fat;
- mass per territory.

**Ischaemia (stress CT perfusion) and scar quantification (LIE, ECV) need images and references the project does not
have.** No public CT dataset with scar, LIE or CT-perfusion labels exists (§4). Juliet builds the outputs so that
those phases plug in unchanged when the data arrive. Whether to pursue that data is the lead's question **M-Q5**.

## 2. Class schema, and what "layers" means

### 2.1 Learned (the network's labels)

| Label | Why it is learned | Convention |
|---|---|---|
| 1 LV myocardium | the object; its two surfaces carry every layer | compact myocardium from the smooth endocardial border to the epicardium; the septum belongs to it |
| 2 LV cavity | defines the endocardial surface and LV volume | **papillary muscles and trabeculae belong to the cavity** (a smooth endocardial border, so the sub-endo third is not a trabecular mix; M-Q8) |
| 3 RV cavity | the RV insertion points anchor the AHA circumference; the septum's right side | blood pool only |
| 4 LA cavity | the mitral plane, i.e. where the LV base ends | blood pool only, to the mitral annulus |

The aorta (for the aortic-valve side of the base) comes from TotalSegmentator's open `total` task at inference (Apache
2.0 weights; Wasserthal 2023, [10.1148/ryai.230024](https://doi.org/10.1148/ryai.230024)). It is not a Janus-M class.

**LV only.** The RV free wall (3–5 mm) and RV myocardium are out of v1. The brief's two contexts, stenosis and scar,
are read on the LV in the AHA model (Cerqueira 2002, [10.1161/hc0402.102975](https://doi.org/10.1161/hc0402.102975)).
That they are mostly an LV question is my opinion; no measurement here backs it. RV can be added as a fifth label
later without changing anything computed (M-Q2).

### 2.2 Computed (versioned code; no learned classes)

| Output | Definition | Evidence |
|---|---|---|
| Endo- and epicardial surfaces | label boundaries 2|1 and 1|outside | — |
| Transmural depth, thirds | equal-thickness depth d_endo/(d_endo + d_epi), or Yezzi–Prince streamline length ([10.1109/TMI.2003.817775](https://doi.org/10.1109/TMI.2003.817775)); never a raw Laplace potential, which puts the 1/3 cut 0.36 mm off in a 10 mm wall | E1 |
| Halves (sub-endo/sub-epi) | depth cut at 0.5, used where a third would be < 2 voxels or the wall is < 5 mm | E1, E2 |
| AHA 17 segments | long axis from valve plane (LV cavity next to LA/aorta) to apex; base/mid/apical thirds + apex cap; 0° at RV centroid, anterior from patient axes; 6/6/4 sectors | E4 (12 real CTs, septum thickest, apex thinnest as expected) |
| Coronary territories | each myocardial voxel → nearest LAD / LCx / RCA voxel of Janus's output (LM feeds both and is left out); a segment's majority; the AHA default (LAD 1,2,7,8,13,14,17; RCA 3,4,9,10,15; LCx 5,6,11,12,16) reported beside it | Job M0 measures the disagreement; on MRI 23 % of infarcted segments are discordant with the default (Ortiz-Pérez 2008, [10.1016/j.jcmg.2008.01.014](https://doi.org/10.1016/j.jcmg.2008.01.014), abstract) |
| Mass subtended | myocardial mass (1.05 g/ml) of the territory of each Janus class, and distal to any point on a vessel (nearest-vessel downstream of that point) | definition; links a stenosis Janus localises to the myocardium at risk |

"Layers" in Juliet v1 therefore means **borders (learned) → transmural depth and thirds → AHA segments → coronary
territories (computed)**. Nothing in the computed chain is tuned on outcome data.

## 3. Clinical outputs, and how they tie to the coronary territories

Every output is reported per AHA segment and per Janus territory (LAD, LCx, RCA, and LM as the sum of LAD and LCx).

### 3.1 Phase 1: rest CCTA (what the project holds; v1 delivers this)

| Output | Rule | Evidence for its meaning |
|---|---|---|
| Wall thickness | median d_endo + d_epi at mid-wall | E1: distance-transform bias −0.2 mm at 0.4 mm |
| Thinning | ≤ 5.5 mm in a segment | the MRI end-diastolic cut-off. In 201/1055 patients (19 %); 72 % scar extent in thinned regions (Shah 2013, [10.1001/jama.2013.1381](https://doi.org/10.1001/jama.2013.1381), abstract). CT phase may not be end-diastolic (§5) |
| Resting sub-endo hypoattenuation | guarded rest TPR (E2's 1 mm guard), plus mean sub-endo HU vs remote | infarct 54 ± 19 HU vs remote 117 ± 28 HU on arterial-phase MDCT (Nikolaou 2004, [10.1097/00004728-200403000-00021](https://doi.org/10.1097/00004728-200403000-00021), abstract). Healed MI vs CMR: sensitivity 91 %, specificity 81 % (Sanz 2006, [10.1016/j.amjcard.2006.01.093](https://doi.org/10.1016/j.amjcard.2006.01.093), abstract) |
| Intramyocardial fat | voxels < −10 HU inside the myocardium (sub-endo first), smoothed | fat in 62 % of post-MI patients vs 3 % of controls; in 89 % of infarcts ≥ 3 years old (Ichikawa 2009, [10.1016/j.jcmg.2009.01.010](https://doi.org/10.1016/j.jcmg.2009.01.010), abstract) |
| Mass and volume | per territory, LV cavity volume | definition |

Each is a *sign*, not a diagnosis. On CCTA, the useful product is the map of which territory behind which Janus
vessel shows thinning, hypoattenuation or fat. A reader uses it beside the stenosis.

### 3.2 Phase 2: stress CT perfusion (needs data; M-Q5)

- **Output:** a guarded stress TPR per segment and territory, on the same computed thirds.
- **Thresholds:** re-derived on Janus-M's own outputs against a reference (SPECT, CMR perfusion or invasive FFR).
  George 2009's < 0.99 is not inherited: it was derived and tested on the same 40 patients, and part of its normal
  1.12 may be spill (E2).
- **Why CTP:** in CORE320, CTA plus CTP reached AUC 0.87 against 0.84 for CTA alone (Rochitte 2014,
  [10.1093/eurheartj/eht488](https://doi.org/10.1093/eurheartj/eht488), abstract and Results). Protocols follow the
  SCCT consensus (Patel 2020, [10.1016/j.jcct.2019.10.003](https://doi.org/10.1016/j.jcct.2019.10.003)).

### 3.3 Phase 3: late iodine enhancement and ECV (needs data; M-Q5)

- **Scar output:** scar presence, then a transmurality bin (Kim 2000, [10.1056/NEJM200011163432003](https://doi.org/10.1056/NEJM200011163432003)) per segment and territory.
- **Borders and rule:** borders are transferred from the same session's CCTA. The LIE image is smoothed by 1.5 mm and
  thresholded by a rule calibrated against MRI LGE (E3: bins recoverable, but a scar-free wall reads 4–12 %).
- **LIE accuracy:** per-segment sensitivity 0.86, specificity 0.98 against LGE (Gatti 2025,
  [10.1007/s00330-024-11283-5](https://doi.org/10.1007/s00330-024-11283-5), abstract).
- **ECV:** CT ECV vs MRI r = 0.82 (Nacif 2012, [10.1148/radiol.12112458](https://doi.org/10.1148/radiol.12112458));
  vs histology r = 0.71 (Bandula 2013, [10.1148/radiol.13130130](https://doi.org/10.1148/radiol.13130130)); both
  abstracts.
- **Photon-counting CT:** raised per-segment LIE sensitivity to 80 % from 49 % on energy-integrating CT in one
  150-patient comparison, 51 of them with MRI (Chamberlin 2026, [10.1148/ryct.250340](https://doi.org/10.1148/ryct.250340),
  abstract).

## 4. Protocols and data

### 4.1 Protocols

| Phase | Protocol | Held? |
|---|---|---|
| 1 | ECG-gated rest CCTA, ≤ 0.5 mm slices | **yes**: ImageCAS (and the pool, mostly sealed for now) |
| 2 | stress CTP, static or dynamic, with rest CCTA | no |
| 3 | LIE 5–10 min after contrast (± dual-energy / photon-counting for ECV), same session as CCTA | no |

### 4.2 Datasets

| Source | What | Licence / access | Use in Juliet v1 |
|---|---|---|---|
| **ImageCAS** (Zeng 2023, [10.1016/j.compmedimag.2023.102287](https://doi.org/10.1016/j.compmedimag.2023.102287)) | 1000 adult CCTA (Siemens dual-source; 0.29–0.43 mm in-plane per the paper; 0.5 mm slices as measured by Atlas). Coronary labels only | CC BY-NC 4.0 (Kaggle); on Girder and Fir | **Primary images.** Only ImageCAS-X train 560 and the 180 non-sealed quality-0 cases. Never val 80, the ImageCAS-X test split or the A14 sealed 100 |
| **ImageCAS-X** coronary labels | 14-class, collapsed to D25's four by `trillium/icx4/lib/territory.py` | CC BY 4.0 | territory reference on Janus-M's seal and decision set; territory module check (Job M0) |
| **TotalSegmentator `heartchambers_highres`** | model: myocardium, 4 chambers, aorta, PA; trained on 1559 CT at about 0.73 × 0.72 × 1.0 mm, validation Dice 0.950 (repository README and details, as reported; not a paper) | **licence needed, free for non-commercial use**; the lead types it on Fir, as for Job S | **seeds** that readers correct (§5) and Janus-M 0 (§6) |
| TotalSegmentator v1 dataset ([10.5281/zenodo.6802614](https://doi.org/10.5281/zenodo.6802614)) | 1204 CT with `heart_myocardium` and 4 chambers, 1.5 mm grid (E4 measured) | CC BY 4.0, open | E4; optional pretraining. Not a layer reference (2 voxels per third) |
| MM-WHS (Zhuang 2019, [10.1016/j.media.2019.101537](https://doi.org/10.1016/j.media.2019.101537)) | 60 CT (20 train / 40 test), 0.78 mm in-plane, 1.6 mm mean slices; best CT whole-heart Dice 0.908 (Table 3) | signed agreement, no redistribution: **gated** (D19) | external check only if the lead obtains it |
| ImageCHD (Xu 2020, arXiv [2101.10799](https://arxiv.org/abs/2101.10799)), CHD68, ImageALCAPA | 110 / 68 / 30 CT with LV myocardium labels; mostly infants with CHD | CC BY-NC 4.0 | not used for training (wrong population); ImageCHD sealed in part (report-only stratum) |
| WHS++ / CARE whole heart | about 100 CT, MM-WHS label set (count unverified) | challenge registration: **gated** | not used |
| Strocchi 2020 ([10.5281/zenodo.3890034](https://doi.org/10.5281/zenodo.3890034)) | 24 heart-failure four-chamber meshes | CC BY 4.0 | not image labels; not used |
| Pool, Mendeley cy54ttk3fj (IRCCS SDN) | 40 normal rest-perfusion CCTA, systole and diastole, DICOM only | CC BY 4.0; in the pool | **report-only domain check** once free (16 volumes after Q1, 34 after A35); never a decision |
| CT scar / LIE / CTP with labels | none open; the Monzino Zenodo records (CTP, ECV) are restricted | gated | none (M-Q5) |
| MRI scar: MyoPS (Li 2023, [10.1016/j.media.2023.102808](https://doi.org/10.1016/j.media.2023.102808)), EMIDEC (Lalande 2020, [10.3390/data5040089](https://doi.org/10.3390/data5040089)) | 45 / 150 CMR | registration / CC BY-NC-SA | not CT; they cannot pair with CT; not used |

**Licences.** ImageCAS (CC BY-NC) and the TotalSegmentator seed model (non-commercial) make Janus-M weights
non-commercial, as the coronary model's already are.

**Keeping the coronary seals apart.** Janus-M reads no pool volume unless `experiments/JanusM/Juliet/exclusion.py`
clears it. That holds in strict mode until the lead answers Round 10 Q1. It excludes:
- the 150-patient pool seal and its reserve;
- the ImageCHD report-only seal;
- every D35 candidate draw.

On ImageCAS it reads only training and non-sealed quality-0 cases. `draw_m0.py` refuses any case in
`trillium/icx4/sealed_test.json`.

## 5. Reference standard

- **Borders (the only learned thing): expert reads.** A reader corrects a TotalSegmentator `heartchambers_highres`
  seed to the protocol (§2.1), in a Slicer queue like SegQueue14, on the 0.5 mm grid. Every seal and decision case is
  **double-read** (two readers, independent). **Inter-read surface distance is the noise floor.**
- **Anchoring (the coronary A40 lesson) applies.** Reads that start from a seed can stay near it. Each wave reports:
  - seed-vs-read and inter-read surface distance;
  - the share of read voxels changed from the seed.

  If both readers sit closer to the seed than to each other's typical spread, half of later seal reads start from a
  blank LV cavity instead. This rule is pre-registered here; its thresholds are set in Round 2 on the first 20
  double reads.
- **Layers, segments and territories:** no independent reference exists. Their error is reported by propagating the
  measured border error through E1's curve (Dice per third against border RMS). Territories are also reported
  against the AHA default.
- **Thickness:** the reads' thickness per segment. The cardiac phase of ImageCAS reconstructions is not recorded in
  the project's files. Juliet assumes mid-diastole (the usual best-diastolic reconstruction) and flags thinning as
  phase-uncertain until Job M0's thickness distribution is read.
- **Phase 2 and 3:** the reference is CMR (LGE for scar; perfusion), SPECT or invasive FFR, paired per patient. None
  is held (M-Q5).

## 6. Model, recipe, metric, splits

### 6.1 Models

- **Janus-M 0 = TotalSegmentator `heartchambers_highres` as it is** (its LV myocardium, LV, RV and LA labels). It
  costs no training and is the baseline every later model must beat on the decision set. It is also the seed.
- **Janus-M 1 = nnU-Net v2 `3d_fullres`** (Isensee 2021, [10.1038/s41592-020-01008-z](https://doi.org/10.1038/s41592-020-01008-z)).
  It takes the coronary line's proven Fir recipe and changes only what differs:
  - ResEnc 60G plans at **0.5 mm isotropic**, 256³ patch (128 mm, which holds the LV with context);
  - 4 labels;
  - mirroring off;
  - 1000 epochs.

  It trains on corrected reads where they exist and seeds elsewhere (seed-labelled cases at weight 1; no
  special loss). One fold: train = all training cases, val = the decision set's *seeds*, used for monitoring only.
- **Janus-M 2:** a second seed of the same recipe, run only if Janus-M 1 passes, as D28's logic would have it for the
  coronary line.

### 6.2 Splits (all patient-level; ImageCAS has one volume per patient)

| Set | Cases | Rule | Use |
|---|---|---|---|
| **Janus-M seal** | 60 ImageCAS-X train cases | sha256(`asclepius-janusm-seal-r1:` + case), first 60, drawn **before** anything else (`fir/draw_m0.py`) | acceptance only, once, double-read |
| **Janus-M decision set** | 40 ImageCAS-X train cases | salt `asclepius-janusm-decision-r1:`, from the rest | model and recipe decisions; double-read; never trained on |
| Job M0 | 40 | salt `asclepius-janusm-juliet-r1:`, from the rest | aggregate geometry only (no per-case inspection beyond the printed summary); then joins training |
| Training | 460 train + 180 quality-0 | the rest | reads as they come; seeds otherwise |
| External, report only | pool cy54ttk3fj (when free); TotalSegmentator v1 12 (E4) | — | domain check |

The seal and the decision set come from ImageCAS-X *train* so that each has ImageCAS-X coronary labels for the
territory check. Janus 0 having trained on those cases does not touch myocardium labels. These cases are in no
coronary decision set or seal (they are neither val 80, test, nor pool).

### 6.3 Deciding metric

- **Primary, per case:** mean of the endocardial and epicardial **average symmetric surface distance (ASSD, mm)**,
  model vs read. Decided **paired against inter-read**: d = model-vs-read − inter-read, averaged over the two reads.
  E1 shows this is what governs every computed output.
- **Co-primary:** per-segment **thickness absolute error (mm)**, median over the 16 segments.
- **Reported:** myocardium and cavity Dice; per-third Dice (computed on both sides); thinning-flag agreement per
  segment; territory majority per segment. For context, Zreik 2018 reports Dice 0.91 and 0.7 mm mean absolute
  surface distance for a CCTA LV-myocardium CNN on 20 test images (abstract).
- **Acceptance (proposed, M-Q7):** on the seal, the upper 95 % bound of mean d ≤ 0.2 mm, and median segment
  thickness error ≤ 1.0 mm. **Decisions on the decision set:** a model replaces another if its mean ASSD is lower,
  with the patient-bootstrap 95 % CI excluding 0.
- **Power (opinion until measured):** with a paired SD of 0.3 mm, n = 60 gives a one-sided 95 % margin of about
  0.064 mm. The SD is measured on the first 20 double reads, and the seal size is confirmed then, before any seal case
  is read.

## 7. Compute (Fir, account `def-aso22`; the lead runs every job)

| Job | What | Waits on | GPU-h |
|---|---|---|---|
| **M0** | draw (seal, decision, M0); `heartchambers_highres` on the 40 M0 cases; CPU geometry and territory vs AHA | this PR; the lead's TotalSegmentator licence on Fir (already used for Job S) | **≤ 1** |
| M1 | seeds on all 740 Janus-M cases | M-Q3, M-Q4 | about 12 (about 1 min per case, opinion) |
| M2 | Janus-M 1, 1000 epochs | ≥ 100 corrected reads; the `role:swe` data path | about 54 (icx4 took 192 s/epoch, 23.2 + 23.3 + 7.7 h; [[icx4 - Results]]) |
| M3 | Janus-M 2 (second seed) | Janus-M 1 passes on the decision set | about 54 |
| — | inference on decision set and seal | — | < 1 |
| **Total to Janus-M 1's decision** | | | **about 67** (121 with M3) |

### Job M0: exact commands (now; ≤ 1 GPU-h; no sealed or decision case is touched)

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius/repo && git pull --ff-only
source $HOME/icx4-tseg-venv/bin/activate
mkdir -p $SCRATCH/janusm/hc
python experiments/JanusM/Juliet/fir/draw_m0.py $SCRATCH/icx4/splits.json $SCRATCH/janusm/m0_cases.txt
# prints: seal 60, decision 40, m0 40, "0 sealed", 420 left. Anything else: stop and send the output back.
export TOTALSEG_HOME_DIR=$SCRATCH/seedcal/totalseg   # Job S's folder, where the licence is already set
# only if TotalSegmentator asks for a licence:
# totalseg_set_license -l "<the project's TotalSegmentator licence key>"   # typed by the lead; never committed or posted
cat > $SCRATCH/janusm/m0.sh <<'EOF'
#!/bin/bash
#SBATCH --job-name=janusm-m0 --account=def-aso22 --gpus-per-node=h100:1 --cpus-per-task=12 --mem=64G --time=02:00:00
source $HOME/icx4-tseg-venv/bin/activate
export TOTALSEG_HOME_DIR=$SCRATCH/seedcal/totalseg
python - <<'PY'
import json, os, subprocess
S = os.environ['SCRATCH']; out = f'{S}/janusm/hc'
ct = json.load(open(f'{S}/icx4/layout.json'))['cases']
cases = open(f'{S}/janusm/m0_cases.txt').read().split()      # 40 ImageCAS-X training cases only
for c in cases:
    o = f'{out}/{c}.nii.gz'
    if not os.path.exists(o):
        subprocess.run(['TotalSegmentator', '-i', ct[c]['ct'], '-o', o, '-ta', 'heartchambers_highres', '--ml', '-d', 'gpu', '-q'])
print('hc:', len(os.listdir(out)), 'of', len(cases))
PY
EOF
sbatch $SCRATCH/janusm/m0.sh                                   # about 30-60 min
# when finished, login node, CPU (about 20 min):
source $HOME/icx4-tseg-venv/bin/activate && cd $SCRATCH/asclepius/repo
python experiments/JanusM/Juliet/fir/geometry_m0.py --cases $SCRATCH/janusm/m0_cases.txt --hc $SCRATCH/janusm/hc \
  --icx $SCRATCH/icx4/icx --out $SCRATCH/janusm/m0_geometry.json
```

- **Check:** the job prints `hc: 40 of 40`; the CPU step prints the label ids, then one line per case.
- **Send back on #130:** the final printed JSON summary (aggregates only: thickness, voxels per third, per-segment
  discordance with the AHA default). No image, no per-case list.
- **If the venv lacks nibabel or scipy:** use `$HOME/icx14-venv` for the CPU step. The script then falls back to the
  published label order and prints it for checking.

## 8. What results would change the plan

| Result | Change |
|---|---|
| M0: native voxels per third < 4 in > 10 % of segments | report halves, not thirds, in those walls |
| M0: `heartchambers_highres` fails (no LV/RV/LA, or no valve plane) in > 10 % of cases | seeds are not enough; budget full reads, and Janus-M 0 is a weak baseline |
| M0: territory discordance with AHA default ≤ 10 % of segments | report the AHA default as primary, patient-specific as secondary |
| M0: discordance ≥ 20 % | patient-specific (Janus) territories are primary; the AHA default is shown only for reference |
| First 20 double reads: inter-read endo ASSD > 0.7 mm | thirds only in walls ≥ 8 mm (E1: thinned-wall sub-endo third falls below 0.76 at 0.5 mm); halves elsewhere |
| Anchoring signature on reads (§5) | half of seal reads from a blank cavity |
| The lead obtains paired CTP or LIE with CMR/SPECT/FFR | Phase 2/3 open: same model, domain check, threshold calibration on that data |
| The lead decides no such data | Janus-M stays a rest-CCTA geometry and tissue-sign model; Round 2 sharpens Phase 1 only |
| Q1/A35 answered | pool cy54ttk3fj becomes the external domain check |

## 9. The lead's decisions (numbered questions, each with a recommendation)

- **M-Q1 Class schema.** Four learned labels (LV myocardium, LV cavity, RV cavity, LA cavity). Layers, segments and
  territories are computed, not learned. **Recommend: yes.**
- **M-Q2 LV only in v1.** No RV myocardium label. **Recommend: yes**; add RV later if wanted.
- **M-Q3 Image source and seal.** ImageCAS: ImageCAS-X train 560 and the 180 non-sealed quality-0 cases. Never val
  80, the ImageCAS-X test split or the A14 sealed 100. A Janus-M seal of 60 and a decision set of 40, drawn now from
  train by the salts in `draw_m0.py`. This changes no coronary decision, but it uses coronary training volumes.
  **Recommend: yes.**
- **M-Q4 Seeds.** Use TotalSegmentator `heartchambers_highres` (academic licence, non-commercial; the key the lead
  already typed for Job S) as Janus-M 0 and as the seed readers correct. **Recommend: yes.**
- **M-Q5 Scar and perfusion data.** The project holds no stress CTP and no LIE, and nothing open exists. Phases 2–3
  need paired CT and reference (CMR/SPECT/FFR) data, most realistically from an institutional retrospective export.
  Whether to pursue it is the lead's, outside the repository (D19, D31). **Recommend:** decide yes or no now. Under
  "no", v1 is still useful (Phase 1) but stops short of scar quantification and ischaemia.
- **M-Q6 Annotators.** About 300 Janus-M reads: seal and decision double-read (200) plus about 100 training reads.
  **Recommend:** Janus-M reads start only after the coronary wave-1 start condition (A39), in a separate queue, so they
  never slow SegQueue14.
- **M-Q7 Acceptance.** On the seal: mean surface-distance difference to inter-read ≤ 0.2 mm (upper 95 % bound), and
  median segment-thickness error ≤ 1.0 mm. **Recommend: yes**, with the seal size confirmed at 20 double reads.
- **M-Q8 Endocardial convention.** Papillary muscles and trabeculae belong to the cavity (smooth endocardial border).
  **Recommend: yes**; it keeps the sub-endocardial third free of trabecular blood.

## 10. Code that must ship (`role:swe`, opened when the plan is adopted)

1. The computed-layer module: depth, thirds and halves, AHA 17, territories, mass, the guarded TPR, LIE bins. It is
   pinned and versioned, built from `real_labels.py` and `phantom.py`'s definitions, with tests.
2. The Janus-M data path:
   - fetch with `exclusion.py`'s guard;
   - seeds;
   - a four-label read queue (a SegQueue14 sibling with the §2.1 protocol);
   - an nnU-Net dataset for Janus-M 1.

## 11. Risks

- **Phase 1 is geometry, not ischaemia.** If the lead wants ischaemia and scar *now*, nothing public gives it.
  That is a data decision, not a modelling one (M-Q5).
- **Seed anchoring** can make reads look better than they are (§5).
- **Cardiac phase** of ImageCAS is unrecorded; thickness may not be end-diastolic.
- **The phantoms are 2-D and idealised** (E1–E3). Job M0 is the first real check at native resolution.
- **Unverified items, named so the judge can discount them:**
  - the `heartchambers_highres` training details (from the repository's text, not a paper);
  - WHS++ counts;
  - the PSF value E2 infers from Atlas's spectrum;
  - Kim 2000's intermediate bins (not quoted);
  - the AHA territory figure number (the assignment itself is the standard reading of Cerqueira 2002).

---
tags: [janus-m, plans, candidate, round1, myocardium, layers, AHA17, TPR, scar, fir]
author: Hotel
round: 1
version: 1
updated: 2026-10-30
issue: christianGRogers/Asclepius#130
---

# Hotel v1: learn two borders, compute the layers

**The position in one line.** A myocardial "layer" has no edge in the image, so no reader can draw one and no model
can learn one from evidence. Janus-M should **learn the two borders that do exist**: the endocardium and the
epicardium, plus the RV and LA cavities that orient them. It then **computes** the layers from those borders,
deterministically:
- transmural thirds;
- the AHA 17 segments;
- patient-specific coronary territories from Janus's own four classes.

Every clinical output is a measurement on that computed grid. Accuracy is therefore a property of the two borders, and the
plan judges models on border distance and segment thickness, not on a Dice of layers.

New evidence this round (CPU; code in `experiments/JanusM/Hotel/`; no coronary-sealed, reserved or D35 case is used,
with one disclosed exception in §12):
- [[Hotel - Layers derived from two borders are stable only if the borders are within about 1 mm, and TotalSegmentator's borders are not]] (E1/E2)
- [[Hotel - After the coronary hold-outs the pool leaves Janus-M 41 volumes, none both HU-true and spacing-true at scale]] (E3)
- Two verified citation lists: `experiments/JanusM/Hotel/citations_clinical.md` (37 entries) and
  `citations_segmentation.md` (28 entries). Every number below that comes from a paper carries its location there.

## 1. The plan in one paragraph

E1_PARAGRAPH

## 2. The class schema, and what "layers" means

### 2.1 What the model learns (4 classes + background)

| Value | Class | Why it is needed |
|---|---|---|
| 1 | **LV cavity** (blood pool, with papillary muscles and trabeculae) | The endocardial border is its surface. |
| 2 | **LV myocardium** (compact wall, septum included) | The thing being measured. |
| 3 | **RV cavity** | Gives the septum's right side as an epicardial-side boundary, and fixes the 0° of the AHA ring (the septum). |
| 4 | **LA cavity** | Fixes the mitral plane, which is the base of the AHA rings and of the long axis. |

- **Papillary muscles and trabeculae go to the cavity.** Without this convention the endocardial surface would be ragged,
  and every transmural coordinate near it would be noise. It is the convention to state in the read protocol, and it
  is a decision the lead can reverse (M-Q1).
- **The names and meanings are those of TotalSegmentator's `heartchambers_highres`.** Its classes are `heart_myocardium`,
  `heart_ventricle_left`, `heart_ventricle_right` and `heart_atrium_left` (`map_to_binary.py`, checked 2026-10-30).
  Its masks can therefore seed reads the way TotalSegmentator seeds the coronary queue (D23, D26).
- **Out of scope for Round 1:**
  - RV free-wall myocardium. Thin walls are much harder: RV and LA wall Dice is 0.63–0.69 in Baskaran PLOS ONE 2020
    (citations_segmentation §2.4), and the brief's stenosis/scar questions are LV questions.
  - Atrial walls.

### 2.2 What is computed, never learned

| Computed | Definition | Precedent |
|---|---|---|
| Transmural depth u ∈ [0, 1] | Laplace's equation in the myocardium, with u = 0 at the cavity, u = 1 at the epicardium or the RV cavity, and Neumann conditions elsewhere | Jones 2000; Yezzi & Prince 2003; Bayer 2012 and 2018 (citations_segmentation §4) |
| Wall thickness | Distance to the endocardium plus distance to the epicardium, per voxel, averaged per segment | Yezzi & Prince 2003 |
| Transmural thirds | Subendocardial u < ⅓, mid-wall ⅓–⅔, subepicardial > ⅔ | George 2009 split the myocardium "automatically and equally" into three layers (citations_clinical §1.2, full text); Kühl 2012 (§1.3) |
| AHA 17 segments | Basal, mid and apical thirds of the cavity length, measured from the mitral centre along the LV long axis; 6/6/4 sectors starting at the septum (RV centroid); apex cap beyond the cavity | Cerqueira 2002 (metadata verified; its territory text was not opened) |
| Coronary territory | Each epicardial point goes to the nearest Janus artery (LAD, LCx or RCA) by geodesic distance on the epicardial surface; it is carried inward along the transmural direction. LM has no territory of its own. | Kurata 2015 (r up to 0.814 against SPECT), Ide 2017 (swine dye, r 0.92–0.96), van Driest 2022 (citations_segmentation §3.5–3.7) |

The territory is reported **beside** the fixed AHA-to-artery map, not instead of it, because the fixed map is often
wrong for the individual patient:
- 23% of scarred segments did not match the standard artery (Ortiz-Pérez 2008);
- only 9 of 17 segments map to a single artery (Pereztol-Valdés 2005).

`layers_from_borders.py` already implements everything above except the territory. It runs on CPU in about a minute
per 1.5 mm heart (E1).

### 2.3 Why layers are not classes

1. **No edge, so no reference.** Between the subendocardial and mid-wall thirds there is no change in the image that
   a reader could follow. A "drawn" layer would be a reader's guess at one third of the wall, which is the computed
   layer with added noise. Every precedent for layer-wise CT analysis splits geometrically, not by hand: George 2009,
   Kühl 2012 and 2016, Xiong 2015, Mushtaq 2023.
2. **The model would only learn our geometry back.** Learning the thirds as classes from computed labels can at best
   reproduce the computation. It adds a failure mode, two internal borders, and buys nothing.
3. **The borders are where the accuracy lives.** E1 measures how border error propagates into the layers (§7.2). It
   sets the bar the borders must clear.

## 3. Clinical outputs, and how they tie to the coronary territories

Every output is a number per **AHA segment × third**, rolled up per **Janus territory** (LAD, LCx, RCA) so that it
sits next to Janus's stenosis findings in the same artery.

| Output | Definition on the computed grid | Evidence it means something | Needs |
|---|---|---|---|
| **Wall thickness / thinning** | Segment mean thickness. Flags at < 5.5 mm, < 5 mm and < 3 mm. | Thinning ≤ 5.5 mm in 19% of 1055 CAD patients, with 18% of thinned regions having ≤ 50% scar (Shah 2013, CMR). CT < 5 mm holds 87% of LAVA (Komatsu 2013). < 5 / < 2 mm in Yamashita 2017. | Rest CCTA. True voxel spacing (E3 flags the pool's). |
| **Rest hypoattenuation** | Segment-third HU on a **core** sample (voxels ≥ 1.5 mm from either border), normalised to the patient's remote myocardium and to the region. The septum is normalised separately because its rest endo/epi ratio is 0.99 against 1.23 elsewhere (Kühl 2012). Also the TPR = subendocardial / subepicardial HU. | Chronic infarct −13 ± 37 HU, against 73 ± 14 HU in normal myocardium (Nieman 2006). Rest first-pass imaging added to CCTA: per-vessel AUC 0.81 against 0.70 for FFR (Osawa 2016). Machine-learning rest CTP: 0.75 against 0.68 (Han 2018). Xiong 2015 (TPR + thickness, accuracy 0.70) is the baseline to beat. | Rest CCTA, HU-calibrated |
| **Intramyocardial fat** | Volume of myocardium voxels in −180 to 0 HU per segment-third, in the core only, so that blurred epicardial fat does not count | Fat in 62% of MI patients against 3% of controls, and **94% of it subendocardial** (Ichikawa 2009). 51% in Zafar 2008. HU window from Xu 2022 (full text). | Rest CCTA, HU-calibrated |
| **Suspected chronic infarct** (composite, a flag, not a diagnosis) | Thinning plus subendocardial fat or severe hypoattenuation in the same segment | The three signs co-occur in chronic MI (Nieman 2006; Zafar 2008; Ichikawa 2009) | Rest CCTA. **Unvalidated until a CMR-paired set exists (§6).** |
| **Stress TPR** (if a stress phase exists) | Same grid on the registered stress phase. TPR < 0.99 is abnormal. | Normal TPR 1.12 ± 0.13 (George 2009, full text). CTA + CTP AUC 0.87 (CORE320). Subendocardial-defect reading per vessel 93.5% against 87.7% transmural (Mushtaq 2023). | Stress CTP. Not in the pool. |
| **Late iodine enhancement transmurality** (if a late phase exists) | Fraction of each segment's thirds that are enhanced, using the arterial-phase borders registered to the late phase | Segment-level sensitivity 0.86 and specificity 0.98 against LGE (Gatti 2025 meta-analysis) | 5–10 min late scan. Not in the pool. |

Two design consequences:
- **One model serves every protocol.** The borders are learned on the arterial phase, which every cardiac CT has.
  Stress and late phases reuse the same grid after registration. No second model is trained for them, so their
  absence from public data does not block Janus-M 0.
- **The stenosis link is per territory, not per segment.** For each Janus artery the report gives:
  - the worst segment TPR or hypoattenuation;
  - the thinned area;
  - the fat volume.

  This is the quantity that published myocardium analyses add to stenosis grading. Zreik 2018: AUC 0.74 against FFR.
  van Hamersvelt 2019: AUC 0.76 against 0.68, with specificity 48.4% against 31.1%. CTA alone has specificity 0.61
  (Celeng 2019).

## 4. CT protocols and phases

- **Required:** ECG-gated coronary CTA, arterial phase, preferably reconstructed in diastole (for thickness). This is the
  data that exists. In the ESCR registry, adenosine for perfusion was recorded in 15 of 205,999 cardiac CTs (Catapano
  2024, Table 3), so stress CTP is an add-on, not the base.
- **Optional, when present:**
  - stress CTP (static or dynamic);
  - a late scan at 5–10 min (a DLP of 149–225 mGy·cm against 168 for the CCTA, Kokawa 2025, Table 4);
  - dual-energy or iodine maps (κ 0.82, Ohta 2018).

  Each reuses the arterial-phase grid.
- **Not wanted:** non-gated chest CT as training data for borders. The TotalSegmentator authors list "heart subpart
  segmentation is inaccurate for native images" as a typical failure (Supplement S6). The three non-contrast
  "coronary arteries" studies in E1 have myocardium labels at 22–31 HU median, with fat-range voxels inside.

## 5. The data

### 5.1 Public CT with myocardium labels

| Set | CT | Labels | Licence / access | Use |
|---|---|---|---|---|
| TotalSegmentator v1 (Zenodo 6802614) | 1204 (37 cardiac/coronary studies; 26 after the coronary hold-outs) | Model-made heart chambers and myocardium, 1.5 mm (Supplement S3) | CC BY 4.0, open | Pretraining and pipeline tests only. E1 shows its myocardium sits 1–2 mm outward. |
| TotalSegmentator `heartchambers_highres` (model) | — | 7 heart classes, about 0.73 × 0.72 × 1.0 mm. 0.950 Dice is averaged over all classes. | Licence key (free non-commercial) | Seeds for reads (Job M0) |
| MM-WHS | 20 train + 40 test (test labels withheld) | 7 structures, myocardium = 205 | Signed agreement, no dissemination; maintenance ended | Training borders, if the lead signs (M-Q3) |
| CARE 2026 whole heart | 60 / 30 / 54 | Same labels as MM-WHS | Registration closed; no licence stated; gated | As MM-WHS |
| ImageCHD | 110 (the pool holds 90 free patients' CT) | 7 incl. myocardium (label 5), 0.25 × 0.25 × 0.5 mm | CC BY-NC 4.0 on Kaggle (sourcing summary); the GitHub README states none | Report-only congenital stratum, as D29 does for the coronary model |

### 5.2 Public CT with scar or perfusion labels

**None found.** The search covered:
- Zenodo ("late iodine enhancement" returns 0 hits; the Monzino CT perfusion and fibrosis records are restricted, with no files);
- TCIA, Kaggle, Hugging Face, PhysioNet and the CARE pages.

Scar labels exist only for MRI: EMIDEC (150 DE-MRI) and MyoPS (45 cases; scar Dice 0.614).

### 5.3 What the project holds (E3)

After the coronary seal (170 patients), its reserve (101) and the D35 drafts (60) are removed, 221 non-ImageCHD
patients are free. **41** of them have the whole heart in view, good or moderate contrast and ≤ 0.5 mm spacing, and
those 41 are limited:
- **CCA200-HF (20):** the header spacing is possibly 2× overstated.
- **PLOS-Peng (14):** not HU.
- **Figshare-EpicardialFat-CE (6) and Slicer (1):** usable.

No free patient has a second phase. **The pool is a geometry pilot and a small sealed test; it is not training data.**

### 5.4 Where scar and perfusion references can come from

Only from paired data:
- CCTA, ideally with a late phase;
- **CMR LGE in the same patient within weeks.**

No public source has that pairing. The realistic source is a retrospective export from the lead's hospital, which is
the same route the sourcing summary recommends for coronary CT. That is the lead's decision and the lead's access
request, outside the repository (D19, D31), and is M-Q2. Until it exists, every scar output in §3 is a measurement,
labelled "unvalidated".

## 6. The reference standard

| Target | Reference | Agreement it can reach |
|---|---|---|
| Endo- and epicardial borders, RV and LA cavities | Reader-corrected seeds under a written **half-maximum rule**: the border lies where HU is halfway between the two plateaus (blood/myocardium; myocardium/epicardial fat). Two reads on 20 cases give the inter-reader border distance. | Xiong 2015's automatic borders: 1.00 / 1.06 mm. Zreik 2018: mean absolute distance 0.7 mm (20 images). |
| Thirds, segments, territories | **Computed** from the reference borders by versioned code (`layers_from_borders.py`). They are a function, so they need no separate read. | Exactly the borders' agreement, propagated (E1 §7.2) |
| Scar | CMR LGE (paired), or LIE CT where dual-energy is available | LIE against LGE κ 0.61 (Gerber 2006), segment sensitivity/specificity 0.86 / 0.98 (Gatti 2025) |
| Ischaemia | Invasive FFR, or stress CTP / SPECT | — |

**Why a half-maximum rule.** E1 measured TotalSegmentator's borders against the image's own half-maximum and found
them shifted outward by 1–2 mm (E1_OFFSETS). Borders seeded from a model inherit its bias unless the protocol names
where the border is. A physical definition makes two readers draw the same line, and it can be checked by code on
every submitted read.

## 7. Model, recipe, deciding metric, splits

### 7.1 Model and recipe

- **Model:** nnU-Net 3d_fullres, residual-encoder M plans (Isensee 2021), 4 classes plus background, the same family
  as Janus.
- **Stage 1, pretraining (Janus-M 0):** the 26 cardiac TotalSegmentator v1 studies not held out, plus the 114 free
  pool TotalSegmentator-cardiac volumes, after a contrast filter and with labels made by `heartchambers_highres`.
  Report-only.
- **Stage 2, fine-tuning (Janus-M 1):** reader-corrected borders on the 19 train volumes (§7.3), plus MM-WHS and CARE
  if the lead obtains them.
- **Deliberately not done:**
  - no layer classes;
  - no scar class;
  - no loss on the thirds.

### 7.2 The deciding metric (pre-registered)

**Primary:**
- the mean absolute error of **segment wall thickness** (mm, over the 17 segments) against the reference borders;
- with **endocardial and epicardial ASSD** (mm) as co-primary.

**Report only:** Dice of the myocardium and Dice of each third.

Reasons, from E1:
- E1_METRIC_REASON

A model is adopted only if, on the Janus-M decision set:
- segment-thickness MAE is ≤ 0.5 mm;
- endo and epi ASSD are both ≤ 1.0 mm;
- it beats the `heartchambers_highres` seed on both.

The Janus-M seal is scored once, at the milestone, against two reads.

### 7.3 Splits and the sealed test, from the start

- **Population:** the 41 free volumes (`janusm_r1_pool_volumes.tsv`).
- **Draw** (`draw_janusm_seal.py`, salt `asclepius-janusm-seal-r1:`, sha256 rank within source, patient level):
  - **13 sealed**;
  - **9 decision**;
  - **19 train**;
  - the file is `janusm_seal_proposal_r1.json`.
- **When it is frozen:** before any image of these volumes is opened. The draw is frozen by a `role:swe` PR (a
  `configs/janusm/sealed-r1.json` and a guard in the Janus-M training path) once the judge adopts it.
- **External test strata, report only:**
  - ImageCHD (congenital);
  - any MM-WHS test submission.
- **Kept apart from the coronary model:**
  - every Hotel script refuses coronary-sealed, reserved and D35-draft volumes through `coronary_holdout.PoolGuard`, which reads the pinned seal;
  - the Janus-M seal is drawn only from volumes that pass the guard, so it is disjoint from every coronary set by construction;
  - Janus 0 runs on Janus-M volumes (for territories), never the reverse;
  - when A35 releases reserve patients, they enter Janus-M by a re-run of the census, never by hand.

## 8. Compute (Fir; account `def-aso22`; the lead runs every command)

All GPU jobs use 1 × H100 80 GB (`--gpus-per-node=h100:1`), 12 cores, charged to `def-aso22_gpu`. Nothing here reads
a coronary-sealed, reserved or D35 volume: the fetch refuses the whole run if the list contains one.

### Job M0: seeds and geometry on the 41 pool volumes (now; ≤ 1 GPU-h plus a CPU job)

```sh
# Fir login node
module load StdEnv/2023 python/3.11.5
source $HOME/icx14-venv/bin/activate && cd $SCRATCH/asclepius/repo && git pull --ff-only     # after this PR is merged
python -c "import girder_client, nibabel, scipy" || pip install girder-client nibabel scipy
mkdir -p $SCRATCH/janusm/cases
# the lead keeps a Girder token in ~/.girder_token (chmod 600); it is never committed or printed
GIRDER_TOKEN_FILE=~/.girder_token python experiments/JanusM/Hotel/fetch_pool_m0.py $SCRATCH/janusm/cases
#   expect: "volumes: 41; refused (coronary hold-outs): 0", then 41 "fetched" lines
# one case on CPU, so the heartchambers_highres weights download on the login node (licence as for Job S)
source $HOME/icx4-tseg-venv/bin/activate && export TOTALSEG_HOME_DIR=$SCRATCH/seedcal/totalseg
C=$SCRATCH/janusm/cases/Slicer-SampleData__*; C=$(ls -d $C | head -1)
TotalSegmentator -i $C/ct.nii.gz -o $C/segmentations -ta heartchambers_highres -d cpu
cat > $SCRATCH/janusm/m0.sh <<'EOF'
#!/bin/bash
#SBATCH --job-name=jm-m0 --account=def-aso22 --gpus-per-node=h100:1 --cpus-per-task=12 --mem=64G --time=02:00:00
source $HOME/icx4-tseg-venv/bin/activate
export TOTALSEG_HOME_DIR=$SCRATCH/seedcal/totalseg
for d in $SCRATCH/janusm/cases/*/; do
  [ -f $d/segmentations/heart_myocardium.nii.gz ] || \
    TotalSegmentator -i $d/ct.nii.gz -o $d/segmentations -ta heartchambers_highres -d gpu -q
done
ls $SCRATCH/janusm/cases/*/segmentations/heart_myocardium.nii.gz | wc -l
EOF
sbatch $SCRATCH/janusm/m0.sh                      # about 20-40 min on one H100
# when it has finished: geometry on CPU (no GPU; about 2-4 min per volume)
cat > $SCRATCH/janusm/m0cpu.sh <<'EOF'
#!/bin/bash
#SBATCH --job-name=jm-m0cpu --account=def-aso22 --cpus-per-task=8 --mem=64G --time=04:00:00
source $HOME/icx14-venv/bin/activate && cd $SCRATCH/asclepius/repo
python experiments/JanusM/Hotel/layers_from_borders.py $SCRATCH/janusm/cases $SCRATCH/janusm/m0_layers.json --no-perturb
python experiments/JanusM/Hotel/summarise_layers.py $SCRATCH/janusm/m0_summary.json $SCRATCH/janusm/m0_layers.json
EOF
sbatch $SCRATCH/janusm/m0cpu.sh
```

**Check:** `41` from the GPU job.

**Send back on #130:** `m0_summary.json`, which holds numbers only and no image. It answers:
1. Does `heartchambers_highres` keep TotalSegmentator's 1–2 mm outward bias at native resolution? This is the
   endo/epi half-maximum offsets.
2. Wall thickness per volume. A CCA200-HF heart near 20 mm flags a doubled header.
3. Whether the AHA construction runs on all 41.

**Cost:** ≤ 1 GPU-h, plus about 2 CPU-h.

### Job M1: Janus-M 0 and 1 (after the reads; about 30 GPU-h)

These wait for:
- the border reads (§6, M-Q4);
- a `role:swe` conversion to an nnU-Net dataset (Dataset 801, 4 classes), with the Janus-M seal guard.

Commands follow once that code exists. The cost is set from Janus's own throughput: about 190–200 s/epoch for the
coronary residual-encoder model at 0.5 mm (Master plan, Round 10). The Janus-M volumes are smaller crops around the
heart.

| Run | Epochs | GPU-h |
|---|---|---|
| Janus-M 0: pretrain on TotalSegmentator cardiac (1.5 mm) | 500 | about 10 |
| Janus-M 1: fine-tune, two seeds (D28's lesson) | 250 each | about 2 × 8 |
| Inference + territories (Janus 0 on the 41) | — | about 2 |
| **Total** | | **about 30 (range 20–45)** |

## 9. What results would change the plan

| If | Then |
|---|---|
| M0 shows `heartchambers_highres` borders within 0.5 mm of the half-maximum at native resolution | The seed is nearly the reference. Reads become a light check, and Janus-M 0 may be the seed itself plus the geometry. |
| M0 shows the 1–2 mm outward bias persists | Readers must move borders. Add an automatic half-maximum snap to the seed (a `role:swe` tool) before reads. |
| The lead obtains CCTA + CMR-LGE pairs (M-Q2) | Scar becomes supervised and validated. Add a per-segment-third scar head, trained on registered LGE, and keep the borders as they are. |
| The lead obtains MM-WHS / CARE | They become the training borders; the 41 pool volumes become test only. |
| E1's TPR noise floor on real 0.5 mm volumes is wider than the effect sizes in §3 (e.g. ±0.13, George's SD) | Drop rest TPR as a per-segment output and keep it per territory only. |
| A rival plan learns layers as classes and shows a reference standard for them | Hotel's §2.3 is wrong. That plan's reference would need to be explained, because Hotel found none. |

## 10. The lead's decisions (proposed M2–M7, through the PM)

| # | Question | Hotel recommends |
|---|---|---|
| M-Q1 | Schema: four learned classes (LV cavity with papillary muscles and trabeculae, LV myocardium, RV cavity, LA cavity); layers, segments and territories computed, not learned | **Yes** |
| M-Q2 | Is a retrospective export of CCTA patients who also had CMR LGE (or a late CT phase) possible from the lead's hospital? It is the only route to a scar reference. | **Yes, start the REB route.** The request itself is the lead's, outside the repository (D19, D31). |
| M-Q3 | Sign the MM-WHS agreement and request CARE 2026 whole-heart data (both gated; no redistribution) | **Yes**. Derived labels stay off Girder's shared collections if the terms say so. |
| M-Q4 | A border-read queue: the 41 pool volumes, seeded by `heartchambers_highres`, half-maximum rule, two reads on 20. About 15–20 min per read, so about 15 annotator-hours. | **Yes, after M0.** Built as a `role:swe` issue once the judge rules. |
| M-Q5 | Use the TotalSegmentator licence (already held for the coronary seeds) for `heartchambers_highres` | **Yes**, if the licence covers it. The key stays out of the repository. |
| M-Q6 | Scar outputs ship as labelled, unvalidated measurements until M-Q2 delivers a reference | **Yes** |

## 11. External evidence

All entries were opened at source, with DOIs resolved. Full entries are in `experiments/JanusM/Hotel/citations_*.md`.
Corrections the literature pass made, so that no advocate repeats them:
- **The CT-ECV paper by Treibel 2015** is in *J Cardiovasc Comput Tomogr*, not *Circ Cardiovasc Imaging*.
- **Baskaran PLOS ONE 2020 has no LV-myocardium Dice.** The CT LV-myocardium Dice is in Baskaran *JACC Cardiovasc
  Imaging* 2020: median 0.920, IQR 0.811–0.944.
- **MM-WHS reports no numeric CT myocardium Dice.** It appears only as boxplots, in Fig. 4.
- **TotalSegmentator v1 heart labels are model-made** (Supplement S3).
- **No fat threshold of −10 or −30 HU was found in a source.** The verified window is −180 to 0 HU (Xu 2022).
- **No rest-CCTA TPR accuracy study larger than about 250 patients was found.**
- **Cerqueira 2002's body text was not opened** (the publisher returned 403). Its territory wording is not quoted.

## 12. Disclosure: one coronary-sealed volume was opened during development

The pool already holds 130 TotalSegmentator cardiac CTs under the same s-numbers as the public release. Five of the 37
cardiac studies Hotel downloaded are coronary-sealed and six are reserved. **One of them, s0655 (sealed, as
`TotalSegmentator-cardiac__s0655`), was opened during development of E1**, before the overlap was found:
- its 1.5 mm CT and its TotalSegmentator heart masks were read;
- myocardium HU, thirds, edges and segments were computed.

No coronary label was read, no Janus model was run, and no coronary number was computed. Its outputs were deleted and
are not in any result. All 11 held-out studies were deleted from disk. Every script now refuses held-out volumes
(`coronary_holdout.py`).

The coronary seal's D27 single look is about Janus's coronary scores, which this did not touch. Whether this counts
against the seal is the lead's call, and the PM is told.

## 13. Where this differs from other plans (for the judge)

Hotel has not seen the other Round 1 candidates. Its distinguishing claims, each testable:
1. **Layers are computed, not learned**, because no reference for a drawn layer exists (§2.3).
2. **Border distance and segment thickness decide, not Dice.** E1 shows thirds Dice collapses under border errors that
   leave myocardium Dice looking good.
3. **The pool cannot train Janus-M** once the coronary hold-outs are respected (E3). Janus-M's data plan must therefore
   be external, and the scar plan must be paired CT–CMR.

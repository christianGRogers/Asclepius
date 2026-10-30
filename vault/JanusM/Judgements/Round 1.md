---
aliases: [Janus-M Round 1]
tags: [janus-m, plans, judgement, round1, myocardium]
author: Janus-M Round 1 judge
round: 1
status: ruling
updated: 2026-10-30
issue: christianGRogers/Asclepius#130
---

# Janus-M Round 1: the judgement

**Ruling in one paragraph.** All five advocates reach the same core design independently, so it is adopted:
**learn the borders, compute the layers.** Janus-M learns four structures on rest CCTA: LV myocardium, LV blood
pool, RV blood pool and LA blood pool. Code computes everything else: transmural depth and thirds, the AHA 17
segments, and patient-specific coronary territories from Janus's classes.

- **Base plan: [[Juliet v1]].** It is the only plan whose data draw avoids every coronary seal *and* every coronary
  decision set, and whose seal carries coronary reference labels for checking territories.
- **Amended by** JA1–JA14 below, which take:
  - from [[Golf v1]]: bias guards, coarsened seeds with blank reads, and conditional training;
  - from [[Hotel v1]]: the half-maximum border rule;
  - from [[India v1]]: 0.5 mm with mirroring off;
  - from [[Kilo v1]]: the allowed-list census, transmurality agreement (STA) as a reported metric, and an external
    pool stratum.
- **Janus-M 0 is TotalSegmentator `heartchambers_highres` plus the geometry, with no training.** A trained
  Janus-M 1 runs only if Janus-M 0 fails on the decision set.
- **The deciding metric** is border surface distance (ASSD) measured against the readers' own disagreement, with
  segment thickness as co-primary and signed-bias guards.
- **The forking question** (M2) is whether the project pursues paired CT + reference data for scar and ischaemia.
  Its two options, **rest-CCTA only** and **paired scar data**, change the plan's structure the most. Both are built
  as paths.

Rules kept: the judge ran no experiment, opened no image, and read no coronary-sealed, reserve or D35 case. The
spot-checks below read committed JSON summaries, committed split files and public bibliographic records only.

---

## 1. Scorecards

Scale 1–5. **(a)** reasoning, **(b)** evidence (citations spot-checked; key numbers checked against the committed
JSON), **(c)** fit to the lead's brief and to data the project can actually obtain, **(d)** risk and cost (5 = low
risk, cheap).

### What was checked, for all five

- **Key numbers against committed JSON: every headline number checked matches.**

  | Advocate | Claim | JSON |
  |---|---|---|
  | Golf | myocardium Dice 0.982/0.963/0.921 and subendocardial Dice 0.952/0.909/0.808 at 0.25/0.5/1.0 mm; septal arc 164°; Laplace/equal-thickness agreement 0.878 | `layers_ts_summary.json` |
  | Hotel | at 1.5 mm, myocardium Dice 0.909, subendocardial 0.729, thickness error 0.644 mm; epicardial half-max offset 0.858 mm (IQR 0.525–1.536); endocardial offset 0.067 mm | `e1_summary.json` |
  | India | at 0.5 mm SD, myocardium Dice 0.976, layer-1 Dice 0.927; scar-bin agreement 0.849 at 1.0 mm; Laplace/distance agreement 0.882 | `results/summary.json` |
  | Kilo | outward endocardial bias 1 mm: myocardium Dice 0.979, Kim-bin flips 12.5 % (37.5 % at τ 0.40); random 0.5 mm: 0.980 and 3.9 %; rest TPR 1.93 [1.04, 2.90]; 48 % of segments move > 0.05 | `summary_e123_grid05.json` |
  | Juliet | 12 real CTs, all segments computed | `real_labels.json` |

- **Held-out ids in committed files: none.** The judge searched all 20 committed Janus-M JSON files for the 16
  TotalSegmentator s-numbers in the coronary pool (`configs/segqueue14/pool-2026-10.txt`: 8 sealed, 8 in the
  extension order). None appears.
- **Citations (a sample of 10 DOIs resolved at Crossref; abstracts read at PubMed).** All exist.
  - Numbers confirmed: Zreik 2018 AUC 0.74; Ichikawa 2009 62 % vs 3 % and 94 % subendocardial; Shah 2013 19 %
    (201/1055), 72 % scar extent, 18 % limited scar; Javadi 2010 72 % of patients and 112/1207 = 9.3 % of segments;
    Forte 2020 (first author Forte, as Golf corrected) septal TPR 1.06 ± 0.06; Chen 2025 *Clin Imaging*;
    Chamberlin 2026 *Radiol Cardiothorac Imaging*; ImageCAS (Zeng 2023).
  - **One context error, shared by Golf and Hotel.** Mushtaq 2023 (93.5 % vs 87.7 % per vessel) is a cohort of
    **stented patients** (in-stent restenosis after PCI). Both quote it as a general statement about defect extent
    without saying so. The numbers are right; the population is narrower than implied.
  - **Not verified by anyone:** the Cerqueira 2002 territory figure. All five use the standard AHA-to-artery map
    from secondary sources. Golf, Hotel and Juliet say so.
- **Disagreements on fact, resolved:**
  - **Pool census.** Golf 137, Hotel 41, Juliet 149, India 299 and Kilo 292 count different populations, not
    different facts:
    - Golf, Hotel, Juliet and India count the 675-volume coronary pool, under different exclusions and quality
      filters;
    - Kilo counts all 904 QC volumes in `SegQueue/cases`, which includes 97 public TotalSegmentator cardiac volumes
      outside the pool list.
    - All five agree on the conclusion: **almost no adult, HU-true, spacing-true gated CCTA is open to Janus-M in
      the pool today.**
  - **TotalSegmentator in the pool.** The pool list holds **16** TotalSegmentator volumes (India and Kilo are right).
    Hotel's and Golf's "130" is the number of public TotalSegmentator cardiac studies on Girder, of which 114 are
    outside the pool.
  - **ImageCHD licence.** Golf, Juliet and Kilo say CC BY-NC 4.0 (Kaggle); India says none is stated; Hotel says
    Kaggle states one and the GitHub README does not. It is treated as **uncertain**, and ImageCHD stays report-only
    (JA5).
  - **Fat threshold.** Juliet and Kilo use −10 HU. Hotel found no source for −10 or −30 HU; the verified window is
    −180 to 0 HU (Xu 2022). Kilo cites a −29.6 HU mean (Ahn 2009). JA11 uses the verified window and sets the cut on
    data.

### Golf v1: learn the two borders, derive the layers

| | Score | Why |
|---|---|---|
| (a) Reasoning | **5** | Shows that *random* border error barely moves thickness (0.04–0.10 mm) while *bias* does, so the metric must catch bias. Gives an explicit reason for equal-thickness over Laplace thirds (clinical definitions are fractions of thickness; the volume shares differ, 25/37/37 vs 21/34/45 %). Counters anchoring with coarsened seeds and 10 blank reads. Makes training conditional on Janus-M 0 failing |
| (b) Evidence | **4** | E2 on 24 public CTs; all numbers match. 54 citations with corrections (Nieman 2008, Forte, Lee 2016). Deducted for the Mushtaq context. E3 (LIE borders from the first-pass scan) is a simulation, and its conclusion is plausible, not proven |
| (c) Fit | **3** | ImageCAS is the right adult source. But its 900-case population includes the coronary val 80 and the ImageCAS-X test split's open 36 and dev 44; its own seal holds 3 open-36 and 3 dev-44 cases. Those are coronary decision groups. D37 does not forbid them, but there is no need to touch them. Job M2 reads Janus 0 predictions on cases Janus 0 trained on, which is in-sample |
| (d) Risk / cost | **5** | ≤ 12 GPU-h committed; ≈ 55 conditional; resumable script |

### Hotel v1: learn two borders, compute the layers

| | Score | Why |
|---|---|---|
| (a) Reasoning | **4** | The **half-maximum border rule** is the best idea in the round: it gives a physical definition that code can check on every read. Measured the 0.86 mm outward epicardial bias of TotalSegmentator v1. The partial-volume caution on rest TPR is sound (endocardial 10–90 % edge 4.7 mm at 1.5 mm) |
| (b) Evidence | **3** | Numbers match; citation lists are careful, with useful corrections (Treibel journal; Baskaran; MM-WHS has no numeric CT Dice). Its perturbation model is much softer than the other three: at 0.5 mm the subendocardial third keeps Dice 0.975, against 0.909 (Golf), 0.927 (India) and 0.939 (Kilo). So its "≤ 0.5 mm" bar is not portable. Deducted for the s0655 opening (§4), disclosed promptly and fully |
| (c) Fit | **2** | Its seal (13 / 9 / 19) is drawn from CCA200-HF, whose spacing it itself flags as possibly 2× overstated, and from **PLOS-Peng2016, which the pool list leaves out for burned-in patient text** and which Kilo's guard refuses. Neither can carry a millimetre metric or a seal. Pretraining Janus-M 0 on 1.5 mm model-made labels adds a training run that the off-the-shelf model makes unnecessary |
| (d) Risk / cost | **3** | ≈ 30 GPU-h (20–45). The data plan depends on gated MM-WHS / CARE |

### India v1: segment two borders, compute the layers

| | Score | Why |
|---|---|---|
| (a) Reasoning | **4** | 0.5 mm, from a quantisation argument; mirroring off for LV handedness; frame-sensitivity numbers for the AHA rule (5° tilt moves 12 % of mass); shows scar transmurality is more robust than layer Dice. Excluding all ImageCAS because the sealed 80 are ImageCAS is over-cautious: sealed cases are excluded by id, as A14 already does for the coronary model |
| (b) Evidence | **5** | The largest real-data experiment (64 of 115 subjects), consistent numbers, and the **only advocate who checked that an s-number names the same patient in TotalSegmentator v1 and v2** (`meta.csv`, 1203/1204 agree). Inline citations, each with a location |
| (c) Fit | **2** | Its universe is "pool patients the coronary plan marks trainable after #116", which today is nearly empty of adult CCTA, and it waits on a coronary freeze. Its ASSD gate (0.25 mm) is read off its own simulation curve |
| (d) Risk / cost | **3** | ≈ 5 GPU-h certain, but an upper bound of ≈ 145 |

### Juliet v1: learn the borders CT can see; compute the layers, segments and territories

| | Score | Why |
|---|---|---|
| (a) Reasoning | **5** | Draws seal, decision set and M0 cases from **ImageCAS-X train only**: no A14 case, no val 80, no ImageCAS-X test split. The seal therefore has coronary reference labels for the territory check. Useful definitions: halves where a third would be < 2 voxels; a 1 mm guard band for perfusion ratios (blood-pool spill turns a true TPR of 0.73 into 0.96); scar presence before transmurality (scar-free walls read 4–12 %). Honest that thickness is phase-uncertain on ImageCAS |
| (b) Evidence | **3** | E1–E3 are idealised 2-D phantoms; real data is 12 TotalSegmentator cases. Numbers match. Citations inline with DOIs, and unverified items named |
| (c) Fit | **5** | Uses data the project holds on Girder and Fir, with a draw script that runs on the existing `splits.json` (the committed copy, `trillium-results/icx14/results/splits.json`: train 560, val 80, test 160, 0 sealed in train) |
| (d) Risk / cost | **4** | M0 ≤ 1 GPU-h. But Janus-M 1 (≈ 54 GPU-h, plus ≈ 100 training reads) is planned after ≥ 100 reads, not only if Janus-M 0 fails, so ≈ 67 GPU-h to a decision |

### Kilo v1: learn the wall, compute the layers, let Janus draw the territories

| | Score | Why |
|---|---|---|
| (a) Reasoning | **4** | **STA** (segmental transmurality agreement) is the most clinical metric offered, and it measures the scar output without a scar label. It is the most careful census (904 QC volumes, by patient, reserve and every D35 draw refused, PLOS-Peng refused). It keeps P0's predictions out because they include D35 volumes. But: only 3 classes (no LA), while its base is "oriented by the left atrium"; RV centroid in v1 instead of insertion points |
| (b) Evidence | **4** | E1–E3 on 39 cases; numbers match. 28 citations checked, 2 without numbers |
| (c) Fit | **2** | Seal = all 20 free Taiwan-AICUP patients: single-source and small. Its decision set depends on gated MM-WHS (else model-made labels). STA on 20 patients resolves only ≈ 0.08 |
| (d) Risk / cost | **3** | ≈ 32–35 GPU-h, going straight to training on an unverified 100 s/epoch estimate |

**Totals (of 20):** Golf 17, Juliet 17, India 14, Kilo 13, Hotel 12. Golf and Juliet tie. **Juliet is the base**
because its data draw is the cleaner of the two (it touches no coronary decision group). Golf's committed-compute
discipline and bias guards enter as amendments.

---

## 2. Rulings where they disagree

### 2.1 Training and test data source

| Option | Advocates | Ruling |
|---|---|---|
| ImageCAS, 900 outside A14 | Golf | Rejected as drawn: includes val 80 and the ImageCAS-X test split (open 36, dev 44) |
| ImageCAS-X train 560 + 180 non-sealed quality-0 | Juliet | **Adopted** (JA5, JA6) |
| Pool after the coronary freeze (#116) | India | Rejected as the primary source: nearly empty of adult CCTA, and it blocks on a coronary decision |
| Pool remainder (41) | Hotel | Rejected: spacing-suspect and burned-in-text volumes |
| Pool allowed list (292) + public | Kilo | **Adopted as an external, report-only stratum** (its 126 adult, good-spacing volumes, Taiwan-AICUP 20 among them), never the seal |
| Public TotalSegmentator v1 cardiac | all | Optional pretraining and report-only; **never a border reference** (model-made labels at 1.5 mm; v1 "myocardium always slightly misaligned"; Hotel's 0.86 mm epicardial bias) |
| MM-WHS, CARE | Hotel, India, Kilo | Gated; an external check only if the lead obtains them (LQ6) |

**Why ImageCAS-X train.** It is 560 adult ECG-gated CCTA at about 0.35–0.43 mm in-plane and 0.5 mm slices, already
on Girder and Fir. These cases are in no coronary seal and no coronary decision set (A14, val 80 and the ImageCAS-X
test split are all excluded), and each has ImageCAS-X coronary labels, so territories on the seal can use the
*reference* tree, not Janus 0's in-sample prediction.

**The cost.** These cases are coronary *training* volumes, and that is the one point the lead should confirm
(LQ4). Its known weaknesses are recorded, not fixed:
- one centre and one vendor;
- an unrecorded cardiac phase;
- non-commercial terms (CC BY-NC, as for the coronary model).

The external pool stratum exists to expose single-site bias.

### 2.2 Structures learned beyond the LV myocardium

| Option | Advocates | Ruling |
|---|---|---|
| LV myo, LV pool, RV pool, LA pool | Golf, Hotel, Juliet | **Adopted** (JA1) |
| + aorta | India | Not learned. The aortic-valve side of the base comes from TotalSegmentator `total` at inference if needed (Juliet) |
| LV myo, LV pool, RV pool (no LA) | Kilo | Rejected: the mitral plane, the base of the AHA rings, needs the LA |
| RV myocardium | none (all defer) | Out of v1. The lead may add it (LQ2); thickness only, no RV layers |

**Papillary muscles and trabeculae belong to the LV blood pool**: unanimous, and E2/E4 (India, Kilo) show the
inner third is where this convention matters most.

### 2.3 The deciding metric

| Option | Advocates | Ruling |
|---|---|---|
| Segment-thickness error + endo/epi ASSD ≤ 1.0 mm | Golf, Hotel | Thickness **co-primary**; ASSD ≤ 1.0 mm kept as an absolute guard |
| Endo/epi ASSD, paired against inter-read | India, Juliet | **Primary** |
| Segmental transmurality agreement (STA) | Kilo | **Reported**, computed by one shared harness; not deciding |

**Why ASSD against inter-read, and not an absolute bar or STA.** The four simulations disagree on how fast layers
degrade with border error: at 0.5 mm the subendocardial-third Dice is 0.909 (Golf), 0.927 (India), 0.939 (Kilo) or
0.975 (Hotel), because their error models differ. **Any absolute ASSD bar read off one of these curves (India 0.25,
Hotel 0.5) is therefore an artefact of that advocate's error model.** The readers' own disagreement is the only
floor the project can measure.

- **STA** is a deterministic function of the two borders plus a synthetic scar placement. It adds a clinical
  reading of the same error, which is worth reporting, but it does not add independent evidence. Its resolution at
  60 patients is not yet known.
- **Segment thickness** catches bias that ASSD averages away.
- **Signed bias guards** catch the error Golf and Kilo show Dice cannot see.

Full rule: JA8.

### 2.4 The Janus-M seal and decision set

| | Golf | Hotel | India | Juliet | Kilo | **Ruling** |
|---|---|---|---|---|---|---|
| Source | ImageCAS 900 | pool 41 | pool after #116 | ImageCAS-X train | Taiwan 20 | **ImageCAS-X train 560** |
| Seal | 60 | 13 | 40 | 60 | 20 | **60** |
| Decision | 40 | 9 | 20 | 40 | MM-WHS 20 / TS 15 | **40** |
| Committed now? | yes | yes | no | draw script | yes | **script adopted; frozen by a `role:swe` PR** |

**How it is kept apart from the coronary seal.**
- The Janus-M population is ImageCAS-X train. It is disjoint by construction from A14's sealed 100 (checked:
  0 sealed cases in the committed train list), from val 80, from the ImageCAS-X test split, and from every pool
  volume. So it cannot touch the pool seal (D27/D32/D33), the reserve (A34) or D35.
- **The reserve and D35.** Janus-M never reads, scores or trains on a reserve patient, a D35 patient or any
  Round 10 candidate draw. Released reserve or non-adopted-draw patients may later enter Janus-M **training only**,
  by an explicit PR, after the coronary plan releases them (LQ7). They never enter the Janus-M seal.
- **The coronary model is never scored on the Janus-M seal**, and the Janus-M seal is never a Janus-M training or
  decision case.

**Size.** 60 + 40, provisional. India's and Juliet's power figures assume a paired SD (0.2–0.3 mm) that nobody has
measured. The size is re-powered on the first 20 double-read **decision-set** cases, before any seal case is read.
It may grow from the pre-ranked continuation of the same salt, and never shrinks after a read (JA6).

### 2.5 Janus-M 0 vs Janus-M 1, and GPU-hours

| | Janus-M 0 | Janus-M 1 | GPU-h to a decision |
|---|---|---|---|
| Golf | `heartchambers_highres` + geometry | only if 0 fails; ≈ 55 | ≤ 12 + 55 |
| Hotel | nnU-Net pretrained on TotalSegmentator | fine-tune, 2 seeds | ≈ 30 |
| India | `heartchambers_highres` + geometry | only if 0 fails; 50–70 | 5 + up to 140 |
| Juliet | `heartchambers_highres` as is | after ≥ 100 reads; ≈ 54 | ≈ 67 |
| Kilo | (seed as fallback) | trained first; ≈ 28 | ≈ 32–35 |

**Ruling (JA9, JA10).**
- **Janus-M 0 = `heartchambers_highres` + the geometry, no training.**
- **Janus-M 1 only if Janus-M 0 fails JA8 on the decision set**, and the ≈ 100 training reads are requested only
  then.
- GPU-hours:
  - **committed: ≤ 3** (Job JM-0 ≤ 1; seeds on the 100 seal and decision cases ≈ 2);
  - **conditional: ≈ 67** (seeds on all 740 ≈ 12; Janus-M 1 ≈ 55, from icx4's measured 192 s/epoch for 1000
    epochs at 0.5 mm);
  - a second seed (≈ 55) only if a seed claim is needed;
  - **ceiling ≈ 125.**

### 2.6 Staging of rest-CTA, perfusion and scar outputs

**Unanimous, and adopted (JA11).**
- **Stage A, on rest CCTA:** wall thickness and thinning; mass per territory; intramyocardial fat; rest attenuation
  per layer. All are labelled **"research output, not validated"**.
  - **Rest TPR stays report-only.** Three independent measurements show it is dominated by partial volume at
    1.5 mm: Hotel's endo/epi ratio 2.25 at 1.5 mm inset; India's 2.1, never < 0.99; Kilo's 1.93, with 48 % of
    segments moving > 0.05 under 1 mm error.
  - Rest TPR may be reported per segment only if Round 2 shows, at native 0.5 mm with Juliet's 1 mm guard band, a
    normal-heart ratio near the published 1.06–1.12.
- **Stage B:** late-enhancement transmurality, stress TPR and ECV. They need paired data the project does not hold,
  and no open CT dataset with scar or perfusion labels exists (all five searched).
  - Late enhancement is graded **inside the first-pass borders registered to the late scan** (Golf E3: an LIE-only
    reader with bright blood scores 0.20 Kim-bin accuracy).
  - **Whether Stage B is pursued is the forking question (§5).**

---

## 3. Binding amendments

- **JA1 — Learned classes.** 0 background; 1 LV myocardium (compact wall, septum included); 2 LV blood pool
  (**papillary muscles and trabeculae included**; basal limit at the mitral and aortic valve planes); 3 RV blood
  pool; 4 LA blood pool (to the mitral annulus). No layer, segment or scar class. The aorta, if needed for the base,
  comes from TotalSegmentator `total` at inference.
- **JA2 — Transmural depth and layers.**
  - **Primary definition:** equal-thickness depth u = d_endo / (d_endo + d_epi). Thirds are cut at 1/3 and 2/3.
    **Halves** replace thirds in a segment where the native grid gives < 4 voxels per third or the wall is < 5 mm.
  - **Laplace and Yezzi–Prince depths are reported alternatives.** Round 2 compares them on native 0.5 mm. Golf and
    India measured 88 % agreement with equal thickness at 1.5 mm; Juliet found the raw Laplace cut 0.36 mm off in a
    10 mm wall.
  - One versioned module (a `role:swe` issue) replaces the five prototypes, and carries tests built from Golf's,
    India's and Juliet's checks.
- **JA3 — AHA 17 segments.**
  - Long axis from the mitral-plane centre (LV voxels next to the LA) to the apex. Basal, mid and apical are thirds
    of the cavity length; segment 17 is the apex cap beyond the cavity.
  - **The circumferential zero is the anterior RV insertion point, found where classes 1 and 3 meet**, not the RV
    centroid. Sectors are **fixed 60° (basal, mid) and 90° (apical)**, as Cerqueira 2002 places them. Golf (164°)
    and India (137°) both measured RV-contact arcs wider than 120°.
  - The measured septal arc and the orientation checks (septum toward the RV; segment 1 anterior) are reported per
    case. A case that fails orientation is flagged, not silently tabled.
- **JA4 — Territories.**
  - **Assignment:** each myocardial voxel goes to the nearest LAD, LCx or RCA voxel by 3-D Euclidean distance. LM
    is not a seed. A segment carries its majority territory.
  - **Geodesic epicardial assignment** (Hotel, India, Kilo) is compared in Round 2.
  - **The standard AHA map is always reported beside it**, and is marked as verified from secondary sources only.
  - **Which coronary tree is used:**
    - on ImageCAS-X cases, the **ImageCAS-X reference labels**, collapsed to D25's four classes;
    - on any other case, Janus 0 run by a Janus-M job on Janus-M-allowed volumes only, never P0's predictions
      (they include D35 volumes).
- **JA5 — Data.**
  - **Seal, decision set and Job JM-0:** ImageCAS-X train only.
  - **Training:** ImageCAS-X train, plus the 180 non-sealed quality-0 cases.
  - **Never:**
    - the A14 sealed 100;
    - the ImageCAS-X test split (open 36, dev 44);
    - val 80;
    - any pool-seal, reserve or D35-draw patient (any Round 10 draw while A33 holds);
    - PLOS-Peng2016.
  - **External, report-only:** Kilo's allowed list, re-derived by the shared guard (JA12), adult good-spacing
    volumes only (Taiwan-AICUP, Figshare-EpicardialFat, STOPSTORM, Slicer).
  - **Training-only at most:** spacing-suspect sets (CCA200-HF, HOCMvalvesSeg, ImageALCAPA).
  - **Public TotalSegmentator v1 cardiac:** pretraining or report-only, after the shared guard.
  - **ImageCHD:** report-only paediatric, licence uncertain, minus the 20 sealed report-only patients in any copy.
- **JA6 — Seal and decision set.**
  - **The draw:** Juliet's `fir/draw_m0.py` as committed, in its order:
    1. seal 60, salt `asclepius-janusm-seal-r1:`;
    2. decision 40, salt `asclepius-janusm-decision-r1:`;
    3. JM-0 40, salt `asclepius-janusm-juliet-r1:`.

    It ranks within the train list of `splits.json`. Before the draw, the lead checks that `$SCRATCH/icx4/splits.json`
    has the same train list as the committed `trillium-results/icx14/results/splits.json` (sha256 prefix
    `a53bd426cddc`). If it differs, stop.
  - **Freezing.** A `role:swe` PR commits `configs/janusm/sealed-r1.json` with:
    - the three lists;
    - the next 60 by the seal salt, as a pre-registered extension;
    - the `splits.json` hash.

    It is sha256-pinned and guarded in every Janus-M loader, and it is merged **before any Janus-M read** of a seal
    or decision case.
  - **Sizing.** Re-powered on the first 20 double-read decision cases. It may grow only from the extension, never
    shrinks after a read, and the seal is scored once.
  - **Superseded proposals.** Golf's, Hotel's and Kilo's seal proposals are not adopted. Their files stay as
    records.
- **JA7 — Reference standard and reads.**
  - **Borders are read twice, independently,** on all 60 seal and 40 decision cases.
  - **Written protocol:** JA1 conventions plus **Hotel's half-maximum rule**. A border lies halfway between the
    adjacent plateaus (blood/myocardium; myocardium/epicardial fat). The rule is checked by code on every
    submitted read.
  - **Seeds:** `heartchambers_highres`, **coarsened to 2 mm and smoothed** (Golf). **10 of the 60 seal cases are
    read from blank.**
  - **Anchoring report per wave:** seed-vs-read and inter-read ASSD, and the share of voxels changed. If blank reads
    differ from seeded reads by more than the inter-read difference, seeded reads cannot accept a model.
  - Thirds, segments and territories have **no separate read**: they are the JA2–JA4 functions of the reference
    borders.
- **JA8 — Deciding metric and acceptance.**
  - **Primary:** per-patient endocardial and epicardial ASSD (mm). The quantity decided is
    d = (model-vs-read) − (read-vs-read), averaged over the two reads, per border.
  - **Co-primary:** the median over segments 1–16 of the per-segment thickness error |model − mean read| (mm).
  - **Guards:** signed endocardial and epicardial bias |·| ≤ 0.5 mm; each ASSD ≤ 1.0 mm.
  - **Reported:** STA (Kilo's definition, one shared harness), myocardium and third Dice, AHA-segment agreement, and
    territory discordance with the AHA map.
  - **Acceptance on the seal (one look):**
    - the upper 95 % patient-bootstrap bound of d is ≤ 0.25 mm per border;
    - the thickness error is ≤ read-vs-read + 0.5 mm (upper bound);
    - the guards pass;
    - and the model beats the `heartchambers_highres` seed whenever it is not the seed itself.
  - **On the decision set,** a model replaces another only if the paired bootstrap CI of the primary excludes 0.
  - **The 0.25 mm and 0.5 mm margins are provisional.** They are re-set once, before any seal read, from the first
    20 decision double reads.
- **JA9 — Models.**
  - **Janus-M 0** = `heartchambers_highres` (labels mapped to JA1) + the JA2–JA4 module. No training.
  - **Janus-M 1 only if Janus-M 0 fails JA8 on the decision set.** Recipe: nnU-Net v2 ResEnc `3d_fullres`; JA1
    classes; 0.5 mm isotropic; **mirroring off** (LV handedness); trained on corrected reads plus seeds; validated
    on the decision set and never trained on it.
  - **A second seed** only if a seed claim is needed.
  - **Hotel's pretraining stage is dropped.**
- **JA10 — Compute** (Fir, `def-aso22`; the lead runs every job; no advocate or judge runs one).
  - **Job JM-0 now:** Juliet v1 §7's commands as committed, ≤ 1 GPU-h. It is the draw (JA6) plus seeds and geometry
    on the 40 JM-0 cases. Send back the printed aggregate JSON only.
  - **Committed after that:** seeds on the 100 seal and decision cases, ≈ 2 GPU-h, once the freeze PR (JA6) is
    merged.
  - **Conditional:** seeds on all 740, ≈ 12; Janus-M 1, ≈ 55; second seed, ≈ 55.
- **JA11 — Outputs and staging.**
  - **Stage A, all labelled "research, not validated":**
    - **Thickness:** recorded with the reconstruction phase where it is known. ImageCAS's phase is unrecorded, so
      ImageCAS thinning is flagged "phase-uncertain".
    - **Thinning threshold:** the CMR ≤ 5.5 mm cut is not borrowed until calibrated on reads. The open labels give
      9.5–9.7 mm walls (Golf, India, Kilo), against 5.7 mm CT end-diastolic normals.
    - **Fat:** counted in a core sample ≥ 1 mm from either border, inside the verified −180 to 0 HU window. The
      cut-off is set on data.
    - **Rest attenuation and TPR:** report-only, with the 1 mm guard band; per-segment only under §2.6's condition.
    - **Mass per territory.**
  - **Stage B:** per the fork (§5).
- **JA12 — One held-out guard.**
  - **What it is:** a single Janus-M guard module (a `role:swe` issue) replaces Golf's `heldout.py`, Hotel's
    `coronary_holdout.py`, India's `pool_subjects()`, Juliet's `exclusion.py` and Kilo's `heldout.py`.
  - **What it refuses, by patient** (`segtrain.pool_seal` grouping):
    - the pool seal (primary and report-only);
    - the extension order (reserve);
    - every Round 10 D35 draw;
    - the A14 sealed 100, the ImageCAS-X test split and val 80;
    - PLOS-Peng2016;
    - every public copy of a pool source by its public id, including the TotalSegmentator s-numbers;
    - every TotalSegmentator "twin" from §4.
  - **Where it runs:** every Janus-M fetch, loader and Fir launcher calls it first, and refuses the whole run on any
    hit.
- **JA13 — Code that must ship** (`role:swe` issues, opened by the PM from #130 once this merges):
  1. the JA2–JA4 geometry module;
  2. the JA12 guard;
  3. the JA6 freeze;
  4. the JA7 read protocol and a four-label read queue, separate from SegQueue14;
  5. the Janus-M nnU-Net dataset builder (only when Janus-M 1 is triggered).
- **JA14 — Citations.** Treat the corrections in §1 as binding on later rounds:
  - Mushtaq 2023 is post-PCI;
  - Cerqueira's territory figure is unverified;
  - Nieman 2008, not 2006, for the MRI comparison;
  - Treibel 2015 is in *J Cardiovasc Comput Tomogr*;
  - no numeric MM-WHS CT myocardium Dice;
  - the −10 HU fat cut is unsourced.

---

## 4. The held-out incident (s0655)

**Scope, as disclosed** (Hotel v1 §12; PM comment on #130, 01:24 UTC).
- **What was opened.** While developing E1, Hotel downloaded 37 public TotalSegmentator v1 cardiac studies before
  checking that the pool reuses public s-numbers. Eleven of them are coronary hold-outs: 5 sealed and 6 in the
  reserve.
- **One, s0655 (coronary-sealed, pool item `TotalSegmentator-cardiac__s0655`), was opened.** Its public 1.5 mm CT and
  public model-made heart masks were read, and myocardium HU, thirds, edges and segments were computed.
- **What was not done.** No coronary label exists for the pool; none was read. No Janus model was run and no coronary
  score was computed.
- **Clean-up.** The outputs and all 11 studies were deleted. The PM checked PR #133 and found no committed file with
  data from any held-out patient.

**Guards now in place.**
- **The five advocates' own guards.** Each now refuses by s-number:
  - Hotel: `coronary_holdout.PoolGuard`;
  - Golf: `heldout.py`;
  - India: `pool_subjects()`, which fails with fewer than 16 ids;
  - Juliet: `exclusion.py`;
  - Kilo: `heldout.py` + `allowed_volumes.py`.
- **The judge's check.** None of the 16 pool s-numbers appears in any of the 20 committed Janus-M JSON files.
- **Effect on Janus-M itself: none.** Under JA5 and JA6, Janus-M's seal and decision set contain no TotalSegmentator
  case at all.
- **JA12** replaces the five guards with one.

**Effect on the coronary seal.** The D27 single look protects Janus's coronary scores, and no coronary quantity was
computed. The judge agrees with the PM that the coronary seal is not compromised in substance. **Whether to replace
s0655 by the next extension-order patient is the lead's call on D27 (LQ8).** No Janus-M decision depends on the
answer.

**Residual risk: one public patient under two TotalSegmentator numbers.**
- **The gap.** TotalSegmentator publishes no patient id. A coronary-held-out patient could therefore appear in the
  public release under a second s-number (a second study), and a guard by s-number would let that study through.
- **India's check** shows that the same s-number names the same patient across v1 and v2.0.1: sex and study type
  agree on 1203 of 1204, ages are within 4 years, and institutes are relabelled consistently. India also reports that
  no other v1 subject shares a held-out subject's age, sex, institute and study type.
- **Why that check is not enough.** It requires the *same* study type and the *exact* age, while ages are jittered
  by up to 4 years. A second study could be of another type, or carry a different jittered age.
- **The risk is small and its consequence is bounded:**
  - such a twin could enter only Janus-M pretraining or a report-only stratum (JA5), never a Janus-M seal or
    decision set;
  - it touches no coronary score.
- **Required, under JA12:** Round 2's guard flags as a **twin** every public TotalSegmentator subject matching a
  held-out subject on sex and institute, with age within ±5 years and any study type, and refuses it. This is a
  conservative over-refusal, and the cost is a few public training cases.

---

## 5. The lead's questions

**The forking question (M2) is LQ1.** Every other question is carried as an assumption, using the recommendation,
and stays open for the lead.

### LQ1 — FORK: does the project pursue paired CT + reference data for scar and ischaemia?

**What it decides.** Today the project holds no late-enhancement CT, no stress CT perfusion, and no CMR, SPECT or
FFR reference, and no open CT dataset with scar or perfusion labels exists (all five searched). The only realistic
source is a retrospective institutional export (D19). The request itself is the lead's, outside the repository
(D31); a path may describe the data it needs, never the ask.

**Why this is the fork.** The answer changes the reference standard, the data, the model heads, the metric and the
deliverable. The other questions change parameters inside one structure.

| Option | Path branch | What the path builds | Recommendation |
|---|---|---|---|
| **A. Rest-CCTA only** | `jm/rest-ccta` | Stage A to completion: borders, reads, Janus-M 0/1, the 17 × 3 × territory table beside Janus's stenosis. Thinning, fat and hypoattenuation stay unvalidated research signs. The brief's "scarring" is met only by those signs | |
| **B. Paired scar data** | `jm/paired-scar` | Stage A as trunk, plus: <br>• the paired-cohort specification (CCTA + late-enhancement CT, with CMR LGE within a fixed window; stress CTP with FFR where present), sized for a segment-level transmurality validation; <br>• LIE registration to first-pass borders; <br>• Kim-bin grading with scar-presence first (Golf E3, Juliet E3); <br>• a scar head inside class 1, scored against LGE; <br>• the validation plan for the Stage A signs against LGE | **Recommended.** It is the only route to the "scarring" half of the brief that is validated rather than inferred. The brief names scarring, and every advocate reached the same conclusion |

Under M2 both paths are built in parallel; the lead later keeps one. A third option was considered and folded into
B: ischaemia first, with paired stress CTP + FFR. One institutional export would plausibly carry both, and the scar
reference (LGE) is the better-defined of the two.

### LQ2 — Learned structures (carried as JA1)

- **Options:**
  - (a) LV myocardium + LV, RV and LA pools; papillary muscles and trabeculae in the pool;
  - (b) as (a) plus RV myocardium, scored by thickness only.
- **Recommendation: (a).** The RV wall is 3–5 mm (2–3 voxels at 1.5 mm), and no stenosis or scar output in the plan
  needs it.

### LQ3 — TotalSegmentator `heartchambers_highres` under its non-commercial licence (carried as JA9)

- **Options:**
  - (a) yes: Janus-M 0 and the read seeds, with the key typed by the lead on Fir, as for Job S, and never committed;
  - (b) no: Janus-M 0 becomes a model trained on public TotalSegmentator v1 (1.5 mm), and Janus-M 1 runs early.
- **Recommendation: (a)**, if Asclepius remains non-commercial research. It saves a training run and gives seeds at
  about 0.7 mm.

### LQ4 — ImageCAS-X training cases as Janus-M's images (carried as JA5/JA6)

- **Options:**
  - (a) ImageCAS-X train 560 + non-sealed quality-0 180. This touches no coronary seal or decision set, but uses
    coronary training volumes;
  - (b) pool only, after the coronary sets are frozen (#116).
- **Recommendation: (a).** Option (b) leaves almost no adult CCTA and waits on the coronary plan.

### LQ5 — Reader time (carried as JA7)

- **Options:**
  - (a) 200 double reads (60 seal + 40 decision) + 10 blank, in a separate queue, starting after the coronary wave-1
    start condition (A39);
  - (b) the same reads, in parallel with the coronary wave now;
  - (c) a smaller set (seal 40, decision 20).
- **Recommendation: (a).** About 15–20 min per read is an estimate (Hotel, Kilo). About 100 training reads are added
  only if Janus-M 1 is triggered.

### LQ6 — MM-WHS data agreement (gated; no redistribution)

- **Options:** (a) sign it, for an external border check only, kept off Girder's shared collections if the terms
  require; (b) do not.
- **Recommendation: (a), low priority.** Its 20 labelled CTs are the only open expert myocardium labels on adult CT.

### LQ7 — Released coronary patients

When the coronary plan releases reserve patients (A35) or non-adopted D35 draws (Round 10 Q1), may Janus-M train on
the adult ones?

- **Options:** (a) yes, training only, by an explicit PR, never the Janus-M seal; (b) no.
- **Recommendation: (a).**

### LQ8 — s0655 and the coronary seal (D27)

- **Options:** (a) keep the seal as it is (the PM's assessment); (b) replace s0655 by the next extension-order patient.
- **Recommendation: (a).** No coronary quantity was computed. Janus-M is unaffected either way.

---

## 6. What Round 2 must settle (on each path)

1. **Job JM-0's numbers** (JA10), on native ImageCAS:
   - voxels per third, and whether halves are needed anywhere (JA2);
   - the wall-thickness distribution, and what it implies for phase;
   - territory discordance with the AHA map (JA4);
   - AHA derivation failures (JA3).

   Round 2 adds **Hotel's half-maximum edge offsets** to the geometry read-out: does `heartchambers_highres` keep
   v1's 0.86 mm outward epicardial bias at native resolution?
2. **One shared perturbation harness** that explains why the four simulations disagree (subendocardial Dice at
   0.5 mm: 0.909 / 0.927 / 0.939 / 0.975). It fixes one error model, and STA is computed in it.
3. **Equal-thickness vs Yezzi–Prince depth** at 0.5 mm; fixed vs arc-proportional septal sectors; Euclidean vs
   geodesic territories.
4. **The written border protocol** (JA7): the half-maximum rule, the basal limits, the anchoring thresholds, and
   the read-queue specification for the `role:swe` issue.
5. **The seal re-powering procedure and the final JA8 margins,** fixed in writing before any read exists.
6. **Rest-TPR feasibility at native 0.5 mm with the guard band**, and the data-driven fat cut-off.
7. **The JA12 guard's twin rule**, applied to the public TotalSegmentator `meta.csv`, with the refused count
   reported.
8. **Path B only:**
   - the paired-cohort specification (phases, timing window, minimum size for segment-level transmurality agreement
     against LGE, power);
   - the LIE-to-CCTA registration method;
   - the scar-head design;
   - written as data requirements, with **no request text** (D31).
9. **Path A only:** what the table delivers to a reader beside Janus's stenosis report, and the threshold-calibration
   plan for Stage A signs without a scar reference.

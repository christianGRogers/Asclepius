---
aliases: [Janus-M master plan]
tags: [janus-m, plans, master-plan]
status: living
updated: 2026-10-30
path: jm/rest-ccta
---

# Janus-M master plan

**On path `jm/rest-ccta`, in force from Round 3 (2026-10-30):** [[Juliet v1]] with JA1–JA14 ([[Janus-M Round 1]]),
plus [[Hotel v2]] with JA15–JA24 ([[Janus-M Round 2 rest-ccta]]), plus [[Hotel v3]] with JA37–JA49
([[Janus-M Round 3 rest-ccta]], `Judgements/Round 3 - rest-ccta.md`). The line forked at Round 1's LQ1 into
`jm/rest-ccta` (this branch: option A, rest CCTA only) and `jm/paired-scar` (M2). Rounds 2 and 3 on this path make
**no fork**. Later rulings govern where they change an earlier rule.

**Status: plan-complete pending the lead's Job JM-0 / JM-0R runs and answers** (Round 3 §8). Round 4 opens when
JM-0 / JM-0R aggregates are posted (LQ22 (a)).

## The plan in one paragraph

**Janus-M learns four borders on rest CCTA and computes the layers.** It segments the LV myocardium, LV blood pool
(with papillary muscles and trabeculae), RV blood pool and LA blood pool. Versioned code then computes:
- the transmural depth (equal thickness) and its thirds, or halves in thin walls;
- the AHA 17 segments, from the RV insertion points and the mitral plane;
- each segment's coronary territory, from Janus's LAD, LCx and RCA, with the AHA default beside it.

The deliverable is a table of 17 segments × layers per patient (Table A) and a roll-up per Janus artery (Table B).
Table B sits beside the **reader's CAD-RADS 2.0 grade** for that artery, because Janus grades no stenosis (JA19).
Every sign is calibrated for specificity only, and every cell reads "research output, not validated" (JA18).

## What is learned, what is computed (JA1–JA4)

| Learned (classes) | Computed (no label) |
|---|---|
| 1 LV myocardium; 2 LV blood pool (papillary muscles and trabeculae included); 3 RV blood pool; 4 LA blood pool | Depth u = d_endo / (d_endo + d_epi) and its thirds (halves where < 4 voxels per third or the wall is < 5 mm); thickness; AHA 17 segments with fixed 60°/90° sectors from the anterior RV insertion; territories by nearest vessel; mass per territory |

## Data, seal and decision set (JA5, JA6)

- **Images: ImageCAS-X train 560**, used for the seal, the decision set, Job JM-0 and training, plus the **180
  non-sealed quality-0 cases** for training only.
- **Never:**
  - the A14 sealed 100;
  - the ImageCAS-X test split (open 36, dev 44);
  - val 80;
  - any coronary pool-seal, reserve or D35-draw patient;
  - PLOS-Peng2016.
- **Janus-M seal: 60. Decision set: 40.** Drawn by `experiments/JanusM/Juliet/fir/draw_m0.py` (salts
  `asclepius-janusm-seal-r1:`, then `asclepius-janusm-decision-r1:`) from the train list of `splits.json`. That list
  must match the committed `trillium-results/icx14/results/splits.json` (sha256 prefix `a53bd426cddc`).
  - The draw is frozen in `configs/janusm/sealed-r1.json` by a `role:swe` PR before any Janus-M read.
  - The seal is scored once.
  - The size is re-powered on the first 20 decision double reads; it may grow from the pre-registered extension and
    never shrinks after a read.
- **External, report-only:** adult, good-spacing volumes on the Janus-M allowed list (Kilo's census, re-derived by
  the shared guard); public TotalSegmentator v1 cardiac cases after the guard; ImageCHD (paediatric, licence
  uncertain).
- **One guard** (JA12) refuses every coronary hold-out by patient, including TotalSegmentator "twins", in every
  Janus-M step.

## Reference standard and metric (JA7, JA8)

- **Reads.** Two independent border reads on every seal and decision case. They follow a written protocol with the
  half-maximum border rule, which code checks. Seeds are `heartchambers_highres`, coarsened to 2 mm; 10 seal cases
  are read from blank; anchoring is reported each wave.
- **Primary metric:** endocardial and epicardial ASSD, measured as model-vs-read minus read-vs-read.
- **Co-primary:** median per-segment thickness error.
- **Guards:** signed bias |·| ≤ **0.3 mm** (JA37: `janusm.harness.signed_bias`, volume ÷ mean area, validated on
  exact phantoms; back to 0.5 mm if it disagrees with point-to-plane by a median > 0.05 mm on the first 20 decision
  read pairs); ASSD ≤ 1.0 mm (JA16).
- **Implementations (JA37–JA39):** ASSD in d and the 1.0 mm guard = sub-voxel point-to-plane (pp), the same for both
  terms; voxel ASSD reported and kept for read checks and anchoring; thickness = `janusm.geometry`, median over
  segments 1–16. Harness biases from `perturb()` are nominal (≈ 1.3× realised); known shifts are exact (JA38).
- **Reported:** STA, Dice, AHA agreement, territory discordance.
- **Units (JA15):** realised symmetric surface ASSD and signed bias, and median-over-segments thickness error, in one
  error model (Golf's corrected SDF, 8 mm fields per border). Never a nominal σ.
- **Acceptance on the seal, final before any read (JA16):** the upper 95 % bound of d is ≤ 0.25 mm per border, and
  the thickness error is ≤ read-vs-read + 0.5 mm. The first 20 decision double reads set only the seal size, by
  India's `e8_repower.py` (60 / 80 / 100 / 120). If 120 does not suffice, Janus-M 1 is triggered before any seal
  read.
- **Reads (JA21, JA46, JA47):** border protocol v1 (Hotel v3 §5.1 as amended): border window level at the
  half-maximum, width 1.5 × the plateau difference; whole-border half-maximum median ≤ 0.5 mm, returned once then
  accepted and flagged; octants warn only; LA appendage excluded; mitral gap required, plane fitted to it; LV–RV
  contact ≤ 0.5 %; per-vessel CAD-RADS 2.0 on the form. Anchoring: two-sample upper bound of (gap − seeded inter-read
  ASSD) ≤ 0.2 mm; a wave with > half of reads changing < 5 % of seed voxels gets 5 third reads from blank.
- **Half-maximum sign (JA44):** + = the region bounded by the border (LV pool; pool + myocardium) extends beyond the
  image half-maximum, everywhere.

## Models and compute (JA9, JA10; Fir, `def-aso22`; the lead runs every job)

| Step | What | GPU-h | When |
|---|---|---|---|
| **Job JM-0** | Juliet v1 §7's commands as committed: the draw, plus `heartchambers_highres` and geometry on 40 ImageCAS-X train cases. Send back the aggregate JSON only | ≤ 1 | **Now** |
| Seeds on seal + decision | 100 cases, for the reads | ≈ 2 | After the freeze PR |
| **Janus-M 0** | `heartchambers_highres` + the geometry module. No training | 0 | Scored on the decision set when reads exist |
| Janus-M 1 | nnU-Net v2 ResEnc `3d_fullres`, 4 classes, 0.5 mm, mirroring off; **only if Janus-M 0 fails** | ≈ 12 (seeds) + ≈ 55 | Conditional |
| Second seed | only if a seed claim is needed | ≈ 55 | Conditional |

| **Job JM-0R** (JA23) | One guarded CPU read-out on JM-0's 40 cases, replacing Hotel's, Lima's and India's add-ons. Aggregates only. 8 CPUs, ≤ 2 h | 0 | After JM-0 (LQ11) |
| Reference population (JA18) | Janus-M 0 (or 1) on the 420 remaining training cases | ≈ 12 | After the decision-set look; committed on this path if the lead agrees (LQ12) |

**Committed ≈ 15 GPU-h on this path (≤ 3 + 12, if LQ12 (a)); conditional ≈ 55; ceiling ≈ 125.**

## Outputs (JA11, JA17–JA19; Stage A only on this path)

- **Thinning:** flagged **per territory**, patient-relative (Lima's rule C), at ≤ 5 % of null patients. A flag also
  needs to clear the read-noise floor F1 (JA42: upper 95 % bound of RC from the first 20 decision double reads) and
  the depth gate (JA41: the sign's detectable depth ≤ 50 %; it replaces κ ≥ 0.6, and κ and ICC are reported).
  Per-segment values are numbers with percentiles, never flags. No 5.5 mm cut.
- **Detectable depth (JA40):** one procedure (Hotel E7 on Lima's simulator; cv_n = plain SD, no added error when
  measured on the table's own model). Printed now: **35 %**; replaced by JM-0R, then by the reference population.
- **Subendocardial hypoattenuation and core fat:** the same procedure. The fat cut is the least strict (c, V) inside
  −180..0 HU at which ≤ 5 % of null hearts carry a cluster.
- **Composite "chronic-infarct-like geometry"** per territory, reported with its population rate.
- **Rest TPR:** guard band max(1 mm, edge FWHM). It is shown per segment only if JM-0R gives an endocardial 10–90 %
  edge ≤ 1.5 mm, an endocardial offset within ±0.25 mm (or snapped borders), and a guarded free-wall median of
  0.99–1.15. Otherwise it stays in the research export only.
- **Mass per territory:** patient-specific, with the AHA default beside it; "shared" segments where the share is
  < 0.6.
- **Reference population:** the 420 remaining ImageCAS-X training cases, labelled "this population,
  phase-uncertain", frozen before any seal read.
- **Depth, sectors, territories (JA20):** equal thickness; fixed sectors, with a septal-arc sensitivity column;
  Euclidean territories primary.
- **Stage B:** none on this path (option A).

## Open questions for the lead (carried as assumptions; full text in the rulings, §5)

| Question | Status |
|---|---|
| LQ1 | **The fork:** rest-CCTA only, or paired scar data |
| LQ2 | LV only |
| LQ3 | `heartchambers_highres` licence |
| LQ4 | ImageCAS-X training cases |
| LQ5 | Reader time |
| LQ6 | MM-WHS |
| LQ7 | Released coronary patients |
| LQ8 | s0655 and D27 |
| LQ9 | Round 1 twin disclosures (rec. a one-line note, no seal change) |
| LQ10 | Stenosis column source (rec. the reader's CAD-RADS grade) |
| LQ11 | One merged Fir CPU job, JM-0R (rec. yes) |
| LQ12 | Reference-population seeds committed (rec. yes) |
| LQ19 | Hold JM-0R until JA44's fix merges (rec. run JM-0 now, JM-0R after S2) |
| LQ20 | Reader time for anchoring third reads (rec. up to two flagged waves) |
| LQ21 | Path A may ship with no flag (rec. accept) |
| LQ22 | Pause this path's rounds until JM-0 / JM-0R report (rec. yes) |

## Shipping (JA13; `role:swe`, opened by the PM)

1. The geometry module.
2. The single held-out guard.
3. The seal freeze.
4. The border read protocol and queue.
5. The nnU-Net dataset builder (only if Janus-M 1 is triggered).
6. **Path `jm/rest-ccta`, from Round 2:**
   - the JA15 harness as the geometry module's fixture;
   - the JM-0R read-out (JA23);
   - the table writer and the reference-population config (JA18, JA19);
   - the twin-list re-pin with blank-institute matching (JA22, on `dev`; merged, 711 refused).
7. **Path `jm/rest-ccta`, from Round 3** (on `dev`, synced to both paths; Round 3 §7):
   - S1 harness API (pp ASSD and bias); S2 JM-0R v2 (canonical sign, `decision_inputs`);
   - S3 detectable-depth function; S4 the one decision script, `experiments/JanusM/fir/jm0r_decide.py`;
   - S5 read queue to protocol v1 (one consolidated list); S6 reference-population builder; S7 table writer;
   - S8 snap tool, only if R4 fires.

---
aliases: [Janus-M master plan]
tags: [janus-m, plans, master-plan]
status: living
updated: 2026-10-31
path: jm/paired-scar
---

# Janus-M master plan

## On this path (`jm/paired-scar`): amended in Round 4 (2026-10-31)

**[[Kilo v2]] with JA25–JA36, JA50–JA59 and JA80–JA87** ([[Janus-M Round 4 paired-scar]],
`Judgements/Round 4 - paired-scar.md`). Golf v4 and Kilo v4 tie at 18/20; Juliet v4 17. No fork. Where JA80–JA87 and the
Round 3 summary below differ, Round 4 governs.

- **Menu, final (JA80):** presence **P-J then P-G** (P-G survived the shipped chain: ≥ 0.915 / 0.985 / 0.989); **P-K
  struck**; extent **E-V, E-D** (3 SD), with E-D keeping columns of **≥ 4 depth bins**, as the benchmark does.
- **Affine rule (JA81, replaces JA51 4(b)):** kept iff sane (4(a)), the normalised QC maximum does not rise, **and**
  either it passes QC or |log det A| ≥ 0.02 (Golf's (g)). The PS3-S3 test's log-det sign is corrected.
- **Fallback (JA82):** the edge offset is checked on the last 4 mm stage; a flag skips the 10 mm fallback. This ships
  only if a replay on the v3 rows meets PS4-S5's numbers.
- **QC cuts (JA83):** provisional cuts come from **registered** benchmark cases (`scores_v3.json` →
  `qc_cuts_registered`), in a file that declares its QC definitions. B-spline is not opened as configured.
- **Phase (JA84–JA85):**
  - the **edge offset routes**; `rim_dark` is advisory;
  - a confirmed mismatch (DICOM, or the reader's mark) goes to the `phase_unmatched` stratum, outside the claim and
    outside yield;
  - an inferred-phase patient routed on the flag alone is charged to yield;
  - an unconfirmed DICOM-matched flag is an ordinary patient;
  - stratum patients are graded on their last 4 mm stage, and a put-back analysis is reported.
- **Seal (JA86):**
  - the rule is unchanged, cap 240;
  - 2 000 sims, with N80 and its MC band logged;
  - power on analysed patients, enrolment inflated by the phase share;
  - `power_at_seal` is stated; **below 0.80 at the cap, no seal grading until the lead answers LQ40**;
  - planning **≈ 40 + 160 at 70 %** (≈ 200 at 50 %). The seal tolerates ≈ 3 % failure at 240.
- **Lead questions:** **LQ40** (an unpowerable seal). LQ2–LQ18 and LQ25–LQ28 carried (LQ27 updated).
- **Shipping:** PS4-S1–S9 (ruling §9).
- **Next:** no Round 5 (JA87). The path waits only on the lead: LQ1 (a paired cohort and access), Job JM-0 / JM-0R, and
  LQ40 once development numbers exist.

## On this path (`jm/paired-scar`): amended in Round 3 (2026-10-30)

**[[Kilo v2]] with JA25–JA36 and JA50–JA59** ([[Janus-M Round 3 paired-scar]], `Judgements/Round 3 - paired-scar.md`).
Round 3's highest score: [[Juliet v3]] (18/20). No fork. Where JA50–JA59 and the Round 2 summary below differ, Round
3 governs.

- **Stage A tracks path A as it stands** (JA50): JA37–JA49, JA60–JA71 and later, through the shared code on `dev`;
  bias guard 0.3 mm (JA71). The hand-over is complete.
- **Registration (JA51, replaces JA29 steps 1–4):**
  1. R0;
  2. QC on four values (fat-like, blood-like, brighter-than-blood, **`rim_dark`**; blood median ≥ 2 mm inside);
  3. rigid Mattes MI masked to classes 1–4 dilated **4 mm** (Euclidean);
  4. affine kept only if it passes a sanity bound (|log det| ≤ 0.15, ± 15 %) **and** lowers the cut-normalised QC
     maximum;
  5. one 10 mm fallback;
  6. the phase step;
  7. a reader check on every patient.
- **Phase (JA52):** `rim_dark` primary; the signed edge offset catches a larger LIE cavity; the log-det is logged. A
  flagged patient goes to the phase-unmatched stratum, is not re-registered, and is not a failure.
- **QC cuts (JA53):** p95 over reader-passed development patients, the shares indexed by blood-to-remote contrast;
  provisional cuts from `bench_lie`. **B-spline** becomes a development arm only on a stated trigger.
- **Scar-0 menu (JA54):**
  - presence **P-J, then P-G** (P-G only under JA51's chain); **P-K struck**;
  - extent **E-V, E-D with the 3 SD voxel cut**;
  - P-J's τ fitted after registration is frozen;
  - sensitivity by LGE bin and the bin-1 share reported.
- **Failed registration (JA55):** LGE-positive segments are misses; LGE-negative segments leave specificity; a
  deciding **yield** bar (not-graded share, upper bound ≤ 0.10).
- **Two claims, fixed order (JA56):**
  - **presence** on sensitivity ≥ 0.75, specificity ≥ 0.93 and yield;
  - **the Kim bin** only after that, against an anchor from every double-read patient; anchor < 0.60 means the bin
    cannot be validated.
- **Size (JA57):** max(120; ≥ 270 scarred segments; 80 % power on presence), from development numbers, capped at
  240. Enrichment target 70 %. Planning figure ≈ 40 + 160 (≈ 200 at 50 %). Scar-1 is triggered on extent if
  development CT bin agreement is > 0.03 below the readers'.
- **Forms (JA58):**
  - the `lge17` read, with share-of-tissue Kim bins and a six-panel synthetic example;
  - a third blind CMR read on every presence or bin disagreement;
  - the `regcheck` form;
  - read timing.
- **Intake (JA59):** guard → split → de-identification gate (batch quarantine) → header checks, with stated
  outcomes.
- **Lead questions:** LQ25 (failed registrations), LQ26 (two claims), LQ27 (enrichment and size), LQ28 (adjudication
  and mock timing). LQ2–LQ18 carried.
- **Shipping:** PS3-S1–S12 (ruling §9).
- **Round 4:** run the shipped chain through the benchmark; re-run the power engine. Otherwise the path waits on
  LQ1 / cohort access and on JM-0.

## On this path (`jm/paired-scar`): in force from Round 2 (2026-10-30)

**[[Kilo v2]] with amendments JA25–JA36** ([[Janus-M Round 2 paired-scar]], `Judgements/Round 2 - paired-scar.md`),
on top of the trunk below. No fork.

- **Stage A is path A's.** `jm/rest-ccta`'s JA15–JA24 apply here as written (JA25): error model, final margins,
  rest TPR, calibrated signs, Tables A and B, border protocol v1, twin rule, JM-0R.
- **Scar is computed inside class 1 on the same-session LIE scan, never learned** (JA26). It is graded per AHA segment
  (presence, then Kim bin) and scored against CMR LGE.
- **Paired cohort, as data requirements only (D31; JA27–JA28):**
  - tiers: T2 = CCTA + same-session LIE + LGE (primary); T1 = CCTA + LGE (Stage A validation); T3 = CTP + FFR
    (report-only);
  - LGE within 90 days of the CT; infarct ≥ 90 days old; LIE phase-matched within 5 % R-R; shared frame of
    reference;
  - development 40; seal ≥ 120 patients and ≥ 270 scarred segments; no claim below 80; split by batch-stable salted
    hash; re-powered once on development.
- **Registration (JA29):** scanner coordinates → QC → heart-masked rigid MI → affine. No B-spline. A reader check on
  every patient. A failure counts as wrong.
- **Scar-0 (JA30):** a rule chosen once on development from a pre-registered menu: presence P-K, P-J or P-G; extent
  E-V or E-D. **Scar-1** (CPU segment-profile model), then a voxel head (≈ 55 GPU-h, ≥ 60 more patients), only if
  each previous step fails (JA31).
- **Acceptance on the paired seal, one look (JA32):** sensitivity lower bound ≥ 0.75; specificity ≥ 0.93;
  transmurality agreement ≥ the LGE readers' own − 0.10. Two CMR readers per patient. κ is reported only.
- **Path A's Stage A flags are scored against LGE (JA33).** Territories are decided against the culprit vessel.
- **Compute (JA34):** ≈ 3 GPU-h (PB-0) once the cohort exists; scar steps on CPU; JM-0R serves both paths.
- **Lead questions:** LQ13–LQ18 (cohort shape, single-energy LIE, windows, LGE reads, success rule, JM-0R), plus
  LQ2–LQ12 carried.

## The shared trunk

**In force from Round 1 (2026-10-30):** [[Juliet v1]] with amendments JA1–JA14 ([[Janus-M Round 1]],
`Judgements/Round 1.md`). The line forks at LQ1 into two paths, `jm/rest-ccta` and `jm/paired-scar` (M2). This page
is the shared trunk both paths start from. Each path's own plan lives on its branch.

## The plan in one paragraph

**Janus-M learns four borders on rest CCTA and computes the layers.** It segments the LV myocardium, LV blood pool
(with papillary muscles and trabeculae), RV blood pool and LA blood pool. Versioned code then computes:
- the transmural depth (equal thickness) and its thirds, or halves in thin walls;
- the AHA 17 segments, from the RV insertion points and the mitral plane;
- each segment's coronary territory, from Janus's LAD, LCx and RCA, with the AHA default beside it.

The deliverable is a table of 17 segments × layers per patient, tagged by territory and placed beside Janus's
stenosis in the same artery.

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
- **Guards:** signed bias |·| ≤ 0.5 mm; ASSD ≤ 1.0 mm.
- **Reported:** STA, Dice, AHA agreement, territory discordance.
- **Acceptance on the seal:** the upper 95 % bound of d is ≤ 0.25 mm per border, and the thickness error is
  ≤ read-vs-read + 0.5 mm. Both margins are provisional and are re-set once before any seal read.

## Models and compute (JA9, JA10; Fir, `def-aso22`; the lead runs every job)

| Step | What | GPU-h | When |
|---|---|---|---|
| **Job JM-0** | Juliet v1 §7's commands as committed: the draw, plus `heartchambers_highres` and geometry on 40 ImageCAS-X train cases. Send back the aggregate JSON only | ≤ 1 | **Now** |
| Seeds on seal + decision | 100 cases, for the reads | ≈ 2 | After the freeze PR |
| **Janus-M 0** | `heartchambers_highres` + the geometry module. No training | 0 | Scored on the decision set when reads exist |
| Janus-M 1 | nnU-Net v2 ResEnc `3d_fullres`, 4 classes, 0.5 mm, mirroring off; **only if Janus-M 0 fails** | ≈ 12 (seeds) + ≈ 55 | Conditional |
| Second seed | only if a seed claim is needed | ≈ 55 | Conditional |

**Committed ≤ 3 GPU-h; conditional ≈ 67; ceiling ≈ 125.**

## Outputs (JA11)

- **Stage A, rest CCTA, all labelled "research, not validated":**
  - thickness and thinning (phase recorded; ImageCAS phase-uncertain; no CMR cut-off borrowed until calibrated);
  - intramyocardial fat (core sample, −180 to 0 HU window, cut-off set on data);
  - rest attenuation and TPR, report-only with a 1 mm guard band;
  - mass per territory.
- **Stage B:** late-enhancement transmurality inside first-pass borders, stress TPR and ECV. They need paired data.
  **They are the fork:**
  - `jm/rest-ccta` assumes none;
  - `jm/paired-scar` assumes the lead pursues an institutional paired cohort (LQ1).

## Open questions for the lead (carried as assumptions; full text in the ruling, §5)

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

## Shipping (JA13; `role:swe`, opened by the PM)

1. The geometry module.
2. The single held-out guard.
3. The seal freeze.
4. The border read protocol and queue.
5. The nnU-Net dataset builder (only if Janus-M 1 is triggered).

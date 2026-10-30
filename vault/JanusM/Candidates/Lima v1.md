---
tags: [janus-m, plans, candidate, round2, rest-ccta, myocardium, layers, calibration]
author: Lima
round: 2
version: 1
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#142
---

# Lima v1: measure the wall in millimetres, flag territories not segments, borrow no threshold

**Path:** `jm/rest-ccta`, **option A of LQ1:** the project does not pursue paired CT and reference data. **Base:**
the Janus-M master plan (Juliet v1 + JA1–JA14), which Lima keeps in full except where §2 says otherwise.

## 0. The plan in one paragraph

On rest CCTA alone, Janus-M is a **measuring instrument**, not a diagnostic test. Nothing it reports can be checked
against scar. Its value is therefore set by two things the project *can* measure:
- **how well it measures**: border error in millimetres against two readers;
- **how often it flags a normal heart**: a false-flag rate calibrated on the unlabelled Janus-M population.

Lima v1 makes both explicit:
- **Error is always stated as realised border ASSD**, never as a nominal "σ". E2 shows this alone explains why Round 1's
  four simulations disagreed (0.909 / 0.927 / 0.939 / 0.975): once each is plotted against the border error it
  actually produced, they lie on one curve.
- **Signs are flagged per coronary territory, from the patient's own median, at a calibrated false-flag rate.** No
  absolute threshold is borrowed. A borrowed 5.5 mm thinning cut flags 57–89 % of simulated normal hearts when the
  phase is unrecorded; the territory rule holds ≤ 5 % (E3).
- **The table sits beside the reader's stenosis grade, not Janus's**, because Janus grades no stenosis (§6). The
  deliverable is *"the myocardium behind each vessel, and behind each lesion the reader marks"*.
- **Job JM-0b**, a CPU read-out on Job JM-0's 40 masks, settles the native-resolution numbers (§6 items 1, 3, 6),
  with every decision it feeds pre-registered here.

**New evidence this round** (CPU; code in `experiments/JanusM/Lima/`):
- **E1** [[Lima - The JA12 twin rule refuses 692 public subjects and leaves 23 of 115 cardiac studies, because all 16 held-out patients share one institute]]
- **E2** [[Lima - Round 1's four border-error simulations are one curve once error is measured as realised ASSD]]
- **E3** [[Lima - Without a scar reference, thinning can be calibrated for specificity per territory, and a borrowed 5.5 mm cut flags 57-89 percent of normal hearts]]
- **Self-test of the JM-0b read-out** on the 23 allowed public cases, which gives a 1.5 mm baseline: §3 and the E2 note.

**Held-out cases: none opened.** Lima's guard (`heldout.py`) refuses the 16 held-out TotalSegmentator patients and
692 JA12 twins *before* any request for a subject's files. Only the 23 allowed cardiac subjects were fetched. To apply
the twin rule, the 16 held-out subjects' public `meta.csv` rows (age, sex, institute, study type) were read, and
nothing else. No ImageCAS image was opened. The JM-0b script recomputes the Janus-M seal and decision draws and
refuses the whole run if any case is in them, in the A14 seal, in the test split, or outside `train` (tested; §7).

## 1. What Lima keeps from the master plan

Everything not changed in §2: the four learned classes (JA1), the computed depth, segments and territories (JA2–JA4),
ImageCAS-X train as the image source and the seal 60 / decision 40 draw (JA5, JA6), double reads with half-maximum
borders, coarsened seeds and 10 blank reads (JA7), ASSD-vs-inter-read as primary with thickness co-primary (JA8),
Janus-M 0 = `heartchambers_highres` + geometry with Janus-M 1 only if it fails (JA9), the compute ceilings (JA10),
Stage A only (JA11 under option A), one guard (JA12), the shipping list (JA13) and the citation corrections (JA14).

## 2. What Lima changes (each with its evidence)

| # | Change | Evidence |
|---|---|---|
| L1 | Every border-error figure, margin and simulation is stated in **realised ASSD (mm)** and signed bias, the units JA8 decides in. A simulation that reports only a nominal σ is not evidence | E2: the four Round 1 models are one curve against realised ASSD; their nominal σ realised 0.13–0.70 of itself |
| L2 | **Bias guard tightened from 0.5 to 0.3 mm** per border | E2: a uniform 0.5 mm shift alone gives 0.62–0.64 mm segment-thickness error; E3: thinning needs ≤ 0.5 mm error to be found at 30–40 % depth |
| L3 | The JA8 margins are **kept at 0.25 mm (ASSD) and 0.5 mm (thickness)** as final, not provisional; the re-powering rule of §5.5 sets only the seal size | E2: 0.25 mm of realised ASSD keeps STA ≥ 0.96 and thickness error ≈ 0.25 mm; E3 |
| L4 | **Stage A flags are per territory**, patient-relative, with a false-flag rate calibrated on the unlabelled population (≤ 5 % of null patients); no absolute cut (5.5 mm, −10 HU) is used | E3 |
| L5 | The table's stenosis column is **the reader's CAD-RADS 2.0 grade per vessel**, plus a reader-marked lesion point that yields **mass at risk** | §6: Janus segments lumen only |
| L6 | **Job JM-0b** (CPU, ≤ 1 h) on JM-0's masks before any read | §7 |
| L7 | The JA12 twin rule stays as written, with its true cost recorded (692 subjects; 23 cardiac left) | E1 |

## 3. Round 1 §6 items 1–7 and 9, settled

### Item 1 — Job JM-0's numbers

JM-0 had not reported when this was written. Lima does not invent its numbers. It settles the item by
**(a)** adding the missing measurements as Job JM-0b (§7) and **(b)** fixing now what each result decides:

| JM-0 / JM-0b result | Decision (pre-registered) |
|---|---|
| Voxels per third (0.5 mm grid) < 4, or wall < 5 mm, in a segment | That segment reports halves (JA2), per case |
| Halves needed in > 25 % of segments over the 40 cases | Thirds are reported per territory only; per-segment layer cells show halves |
| Median wall > 8 mm on ImageCAS | Thickness is phase-uncertain (systolic-like); E3's rule C is unaffected, but no absolute value is shown |
| AHA frame fails, or orientation check fails, in > 10 % of cases (fixed sectors) | The frame is fixed (JA3 module) before any table ships |
| Euclidean territory discordance with the AHA map ≤ 10 % of segments | AHA map primary, patient-specific secondary (Juliet's rule, kept) |
| … ≥ 20 % | Patient-specific primary |
| Half-maximum epicardial offset of `heartchambers_highres` ≥ 0.5 mm (median of case medians) | The seed is snapped to the half-maximum before reads (a `role:swe` tool) and Janus-M 0 is expected to fail L2's bias guard |
| … < 0.3 mm | No snap; Janus-M 0 is a credible candidate |

**Baseline on public labels** (self-test, 1.5 mm model-made labels on a 0.5 mm grid; §3 of the E2 note): wall 9.7 mm median; 6.3 voxels per third (p5 4.4); halves in 1.6 % of segments; AHA frame and orientation 23/23; epicardial half-maximum offset +0.64 mm (Hotel: +0.86 mm on the same kind of labels), endocardial −0.45 mm. These are 1.5 mm model-made labels, so they set no decision.

### Item 2 — one shared perturbation harness

Done: E2. One harness re-implements all four Round 1 error models on the same 23 myocardia and measures the realised
border error of every perturbed wall. **The four disagree because their signed-distance conventions turn the same
nominal σ into different real border shifts**, not because layers degrade differently:
- Golf's half-voxel-corrected distance realises ≈ 0.7 of σ;
- India's (±0.75 voxel at the border) ≈ 0.47–0.58;
- Kilo's (plain distance at 1.5 mm, zoomed) ≈ 0.38–0.45;
- Hotel's (plain distance at 0.75 mm: a one-voxel dead zone) ≈ 0.1 at σ 0.5 and 0.4 at σ 1.0.

Plotted against realised ASSD, every model's subendocardial-third Dice lies on one curve: Dice ≈ 1.001 − 0.314 · ASSD, residual SD 0.018 against a total SD of 0.071, and every model's mean residual ≤ 0.0015. **The fixed
error model** (`harness.py`, model `lima_c8`): Golf's corrected signed distance, independent smooth fields per border
with an 8 mm correlation length, results reported against realised ASSD. The correlation length matters little
(4 / 8 / 16 mm: subendocardial Dice 0.889 / 0.898 / 0.913 at nominal 0.5). STA is computed in the same harness.

### Item 3 — equal-thickness vs Yezzi–Prince; fixed vs arc sectors; Euclidean vs geodesic

- **Depth.** Lima implements Yezzi & Prince (2003) thickness (`lima_geom.yezzi_prince`). On the public baseline its
  thirds agree with equal-thickness thirds in 0.973 (p10 0.953) of voxels, and Laplace-potential thirds in 0.884. Yezzi–Prince
  corrects exactly the potential-spacing bias that separates Laplace from equal thickness; it does not move the
  thirds. **Ruling proposed:** equal thickness stays primary (JA2); Yezzi–Prince is the reported alternative, and the
  raw Laplace potential is dropped. JM-0b repeats this at native resolution; if agreement falls below 0.90 there, the
  lead is told which definition the thirds depend on.
- **Sectors.** The measured RV-contact arc is median 140° (p10–p90 123–157°) on the public baseline (Golf 164°, India 137° in Round 1).
  Arc-proportional septal sectors relabel a median 14 % (p10–p90 3–27 %) of the myocardium relative to fixed 60° sectors. **Ruling proposed:**
  fixed sectors (JA3; Cerqueira 2002 places them so), because a reader compares against the standard bullseye; the
  arc rule's discordance is reported beside it by JM-0b, and becomes primary only if it lowers territory
  discordance with the reference tree by ≥ 5 percentage points of segments on the 40 JM-0 cases.
- **Territories.** Lima implements geodesic assignment over the epicardial surface (multi-source Dijkstra from each
  vessel's projection; the wall takes its nearest surface voxel's class). On synthetic coronaries both methods
  reproduce the AHA map (wiring test only). JM-0b measures, on ImageCAS-X reference trees, the share of segments
  whose majority differs between them. **Ruling proposed:** Euclidean (JA4) stays primary unless they differ in
  > 10 % of segments, in which case geodesic is primary: it is the method validated against histology and SPECT
  (Ide 2017; Kurata 2015), while the 3-D nearest vessel can cross the cavity.

### Item 4 — the written border protocol and the read-queue specification

In §8 (Appendix A), ready to become the JA13 item-4 `role:swe` issue.

### Item 5 — seal re-powering and the final JA8 margins, fixed before any read

**Margins (final):** per border, upper 95 % patient-bootstrap bound of d ≤ **0.25 mm**; median segment-thickness error
≤ read-vs-read + **0.5 mm**; signed bias |·| ≤ **0.3 mm** (L2); each ASSD ≤ 1.0 mm. Why these are final now: E2 shows
0.25 mm of extra realised ASSD keeps STA ≥ 0.96 and adds ≈ 0.25 mm of thickness error, and E3 shows thickness error
above 0.5 mm halves the thinning sensitivity. They are clinical bars, not reader-dependent ones, so nothing in the
first 20 reads should move them.

**Re-powering (sets only the seal size):**
1. After the first 20 double-read **decision** cases, compute each patient's d for Janus-M 0 (the seed model) per
   border, and the SD of d, s.
2. The seal size is the smallest n in {60, 80, 100, 120} (the pre-registered extension of JA6) with
   n ≥ (3.29 · s / 0.125)², i.e. a model whose true d is half the margin passes with 95 % probability at α = 0.05.
3. If n > 120 is needed, the seal stays 120 and the PR that freezes it says that the seal is underpowered for
   that s; the margins do not change.
4. This is computed from decision cases only. No seal case is read before the size is fixed. It is never shrunk.

### Item 6 — rest TPR and the fat cut-off

- **Rest TPR.** Public baseline: guarded per-segment TPR median 1.66, with 16 % of segments in 0.99–1.25, unguarded 1.78, nowhere near the published
  normal 1.06 ± 0.06 (Forte 2020, septal, rest). That is 1.5 mm partial volume, as Round 1 found three times. JM-0b
  measures it on native ImageCAS with the 1 mm guard band. **Pre-registered rule:** per-segment rest TPR is reported
  only if, on the 40 JM-0 cases, the median guarded TPR lies in 0.99–1.20 and ≥ 70 % of guarded segments lie in
  0.99–1.25. Otherwise rest TPR is dropped from the table (not even per territory), because a sign whose normal value
  cannot be reproduced cannot be calibrated by E3's rule.
- **Fat.** Core sample ≥ 1 mm from both borders (JA11), HU < c, 26-connected clusters ≥ V mm³, with (c, V) from the
  grid c ∈ {0, −30, −50, −100} HU (inside the verified −180 to 0 HU window, Xu 2022) and V ∈ {5, 20, 50} mm³.
  **Rule:** the least strict (c, V) for which ≤ 5 % of the 40 JM-0 hearts carry any cluster. 5 % is chosen to sit
  above Ichikawa 2009's 3 % of controls with fat, since the ImageCAS population is not a control group. Public
  baseline: 96 % of hearts carry a ≥ 20 mm³ cluster even at −50 HU, because the outward v1 epicardium puts fat into
  the "core"; the cut cannot be set until JM-0b.

### Item 7 — the twin rule

Done: E1. The rule refuses **692** public subjects (708 with the held-out 16) and leaves **23 of 115**
non-held-out cardiac studies, because all 16 held-out patients come from the largest institute. Lima keeps it,
records the true cost, and recommends #138 compute twins per release and pin the held-out list's hash (as
`heldout.py` does).

### Item 9 (path A) — what the table delivers, and calibration without a scar reference

**What a reader gets** (one page per patient, every cell "research output, not validated"):

| Per vessel (Janus: LAD, LCx, RCA) | Source |
|---|---|
| **Stenosis: CAD-RADS 2.0 grade of the worst lesion** (Cury 2022) | **The reader**, typed in; Janus grades none |
| Lesion point on the Janus vessel (optional click) | The reader |
| **Myocardium supplied** (g, % LV), patient-specific; AHA-default mass beside it | Janus-M + Janus (JA4) |
| **Mass at risk distal to the lesion point** (g, % LV): myocardium whose nearest vessel voxel lies downstream of the point | Janus-M + Janus; the quantity Voronoi CT methods validate (Ide 2017 histology; Kurata 2015 SPECT) |
| **Territory flags** (thinning, subendocardial hypoattenuation, fat), each with its calibrated false-flag rate | E3 rule C |
| Segments discordant with the AHA map | JA4 |

and per segment × layer: thickness, z score (E3), guarded HU, fat cluster volume, on the bullseye.

**Why the stenosis column is the reader's.** Janus is a four-class lumen segmentation (the coronary plan's fixed
goal); a calibre-based use such as stenosis "is not in scope" (`vault/Plans/Experiments/icx4 - Results.md`). So
"beside Janus's stenosis report" has to mean beside the reader's grade on Janus's vessels. A Janus stenosis module
would be a coronary-plan decision, which Janus-M cannot make (README: a Janus-M decision that touches the coronary
plan goes to the lead). If one is ever built, it fills the same column.

**What this delivers that the CCTA read alone does not:** for each graded lesion, how much myocardium is behind it,
and whether that myocardium already shows signs of chronic infarction. A severe stenosis behind a large, unflagged
territory and one behind a thinned, fatty territory are different findings; the second suggests chronic infarction
in that territory. Lima states this as the table's purpose, not as a validated claim.

**Calibration without a scar reference (E3):**
1. **Specificity is calibrated; sensitivity is not claimed.** Each sign's cut is set so that ≤ 5 % of null patients
   carry any territory flag, from the unlabelled Janus-M training population (ImageCAS-X train, 460 cases after the
   seal and decision set; seeds, or reads where they exist). The null is the mirror of the right half of each
   segment's patient-relative score, which thinning cannot reach.
2. **Detectable depth is reported instead of sensitivity**, from E3 re-run with JM-0b's measured segment shape and
   normal variation and the decision set's measured thickness error.
3. **Three checks that need no scar reference**, run on the decision set's double reads and reported with the table:
   - *Reproducibility:* each territory flag computed from read A's borders vs read B's borders (κ). A sign with κ < 0.6
     is shown as a number, never as a flag.
   - *Co-location:* thinning, hypoattenuation and fat flags should coincide in the same territory more often than by
     chance (odds ratio with CI on the 460-case population). If they do not, that is evidence the flags are noise.
   - *Model vs reads:* the model's flags agree with the mean read's flags at κ ≥ the reads' own κ − 0.1.

These cannot show that a flag means scar. They show that it is reproducible, rare in the population, and
internally consistent, which is the most path A can claim. Path B is the path that can test validity.

## 4. Carried assumptions (LQ2–LQ8, the ruling's recommendations)

| Question | Assumed (as the ruling recommends) |
|---|---|
| LQ2 | (a) LV myocardium + LV, RV, LA pools; no RV myocardium |
| LQ3 | (a) `heartchambers_highres` under its non-commercial licence, key typed by the lead on Fir |
| LQ4 | (a) ImageCAS-X train 560 + non-sealed quality-0 180 |
| LQ5 | (a) 200 double reads + 10 blank, separate queue, after the coronary A39 start |
| LQ6 | (a) MM-WHS for an external border check, low priority |
| LQ7 | (a) released coronary patients for Janus-M training only, never the seal |
| LQ8 | (a) keep the coronary seal as it is |

Lima adds no new lead question. One observation for the lead's LQ1 choice: under option A, the table's
stenosis column depends on a reader grading every case, because Janus does not (§3 item 9).

## 5. Data, seal, reference standard, model, metric

As the master plan (JA5–JA9), with L2's 0.3 mm bias guard and L3's final margins. The read protocol is Appendix A.
The public TotalSegmentator stratum is the 23 allowed subjects (E1), report-only.

## 6. Risks

- **JM-0 and JM-0b are not back.** Every native-resolution claim above is a decision rule, not a result.
- **E3 is a simulation** with an assumed systolic factor and a placeholder segment shape; JM-0b replaces both.
- **The territory rule under-calls very large infarcts** that pull down the patient's own median (E3 limits).
- **The reader workload grows**: a CAD-RADS grade per case for the table. Under option A it is the only stenosis
  source.
- **Synthetic territories test wiring only.** JM-0b is the first real test.

## 7. Compute (Fir, `def-aso22`; the lead runs every job; Lima runs nothing on Fir)

| Job | What | Waits on | Cost |
|---|---|---|---|
| JM-0 | As committed (Juliet v1 §7): draw + `heartchambers_highres` on 40 JM-0 cases | already ruled | ≤ 1 GPU-h |
| **JM-0b** | `experiments/JanusM/Lima/fir/jm0b_readout.py` on JM-0's masks + CT + ImageCAS-X coronary labels | JM-0's masks; this PR merged | **CPU only, ≈ 1 h on 8 cores** |
| Seeds, Janus-M 1, second seed | As JA10 | as JA10 | ≈ 2 committed; ≈ 67 conditional |

**Job JM-0b, exact commands** (after JM-0 has printed `hc: 40 of 40`):

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius/repo && git fetch origin jm/rest-ccta && git checkout jm/rest-ccta && git pull --ff-only
source $HOME/icx4-tseg-venv/bin/activate   # nibabel, scipy and totalsegmentator's class map; else $HOME/icx14-venv
cat > $SCRATCH/janusm/jm0b.sh <<'EOF'
#!/bin/bash
#SBATCH --job-name=janusm-jm0b --account=def-aso22 --cpus-per-task=8 --mem=48G --time=02:00:00
source $HOME/icx4-tseg-venv/bin/activate
cd $SCRATCH/asclepius/repo
python experiments/JanusM/Lima/fir/jm0b_readout.py --cases $SCRATCH/janusm/m0_cases.txt --hc $SCRATCH/janusm/hc \
  --layout $SCRATCH/icx4/layout.json --icx $SCRATCH/icx4/icx --splits $SCRATCH/icx4/splits.json \
  --out $SCRATCH/janusm/jm0b --np 8
EOF
sbatch $SCRATCH/janusm/jm0b.sh
```

- **Check:** the first line printed is
  `guard: 40 cases, all ImageCAS-X train, 0 sealed, 0 test, 0 Janus-M seal/decision`. Any `REFUSED` line means
  nothing was opened: stop and send that line back.
- **Send back on #142:** `$SCRATCH/janusm/jm0b/summary.json` only (aggregates; no case id, no image). The per-case
  file `cases.jsonl` stays on Fir.
- **If a case prints `grid mismatch`:** the CT, mask and label grids differ for it; send the count.

## 8. Appendix A — the border protocol and the read queue (JA7; for the JA13 item-4 `role:swe` issue)

**Labels** (JA1). 1 LV myocardium; 2 LV blood pool; 3 RV blood pool; 4 LA blood pool; 0 everything else.

**Where each border is.**
1. **Half-maximum rule** (Hotel v1, JA7). A border lies halfway, in HU, between the two adjacent plateaus: blood and
   compact myocardium for the endocardium; compact myocardium and epicardial fat for the epicardium. Readers draw at
   a fixed window (width 800, level 200) and may check any point with the tool's profile probe.
2. **Papillary muscles and trabeculae are blood pool** (2). The endocardial border is the inner edge of the compact
   wall: the continuous band of myocardium-plateau HU. Any myocardial structure joined to it only by a stalk narrower
   than itself is pool.
3. **Base.** Class 1 stops at the mitral annulus plane (the plane through the annular hinge points) and, on the
   outflow side, at the aortic annulus; the septum below the aortic annulus is class 1. Class 2 is closed by the
   mitral and aortic valve planes. Class 4 runs to the mitral annulus, includes the appendage, and stops at the
   pulmonary-vein ostia. Class 3 runs from the tricuspid annulus to the pulmonary valve.
4. **Where the epicardium touches the RV pool (the septum)** the epicardial border is the half-maximum between the
   septum and RV blood. Where it touches pericardium with no fat, readers follow the myocardium's outer edge.

**Checks run by code on every submitted read** (the queue refuses a read that fails, with the failing region shown):
- one connected class 1; class 2 enclosed by class 1 except at the valve planes; no overlap;
- **half-maximum offsets** (`lima_geom.halfmax_offsets`): median signed offset |·| ≤ 0.5 mm per border, and an
  interquartile width ≤ 1.5 mm. These thresholds are re-set once, on the first 20 decision double reads, to the
  95th percentile of the reads' own values, and never again.

**Seeds and anchoring** (JA7). Seeds are `heartchambers_highres`, resampled to 2 mm and smoothed (σ 1 mm), then
put back on the 0.5 mm grid; 10 of the 60 seal cases are read from blank. Per wave of ≥ 10 cases, the queue
reports: seed-vs-read ASSD, read-vs-read ASSD, and the share of voxels changed from the seed.
- **Anchoring trigger 1:** on the blank cases, blank-vs-seeded read ASSD exceeds seeded-vs-seeded read ASSD by
  more than 0.1 mm (paired, upper 95 % bound). Then seeded reads cannot accept a model (JA7), and all remaining seal
  reads are from blank.
- **Anchoring trigger 2:** more than half the wave's reads change < 5 % of seed voxels. Then the wave is flagged
  for the PM and trigger 1 is re-tested before the next wave.

**The queue** (`role:swe`, built on `jm/rest-ccta`):
- a four-label Slicer protocol, separate from SegQueue14 (D23, D24 untouched);
- serves only cases in the frozen `configs/janusm/sealed-r1.json` (JA6) and calls the JA12 guard first;
- two independent readers per case; a reader never sees the other's read; the 10 blank cases are served without a
  seed;
- stores reads in a Janus-M collection on Girder, never in the coronary collections;
- for the table (§3 item 9), an optional per-case form: CAD-RADS 2.0 grade per vessel and a lesion point.

## 9. Code that must ship (`role:swe`, labelled with this path, opened by the PM if the judge adopts these items)

1. **The JA2–JA4 geometry module** (JA13 item 1) gains Lima's Yezzi–Prince depth, arc-proportional sectors and
   geodesic territories as reported alternatives (`lima_geom.py`), with the self-tests of `local_check.py`.
2. **The table writer**: per-vessel rows as §3 item 9, the bullseye per layer, and the E3 calibration (rule C)
   fitted once on the training population and stored with its version.
3. **Mass at risk from a lesion point** on a Janus vessel.
4. **The read queue** as Appendix A (JA13 item 4).
5. **The JA12 guard** (#138) computes twins per release and pins the held-out list hash (E1).

## 10. References

Each was resolved at Crossref or taken from a Round 1 advocate's verified citation file (named). Numbers are from
the abstract unless stated. JA14's corrections apply.

- Cerqueira MD, et al. Standardized myocardial segmentation and nomenclature for tomographic imaging of the heart.
  *Circulation* 2002;105:539–542. doi:10.1161/hc0402.102975. Its territory figure is **unverified** (JA14); used for
  the sector layout only.
- Chen J, et al. Left ventricular wall thickness discrepancies at end-diastole and mid-diastole: reference values
  for cardiac CT. *Clin Imaging* 2025;118:110390. doi:10.1016/j.clinimag.2024.110390. 5.7 mm ED vs 6.5 mm
  mid-diastole (Golf citations).
- Cury RC, et al. CAD-RADS 2.0 – 2022 Coronary Artery Disease-Reporting and Data System. *J Cardiovasc Comput
  Tomogr* 2022;16:536–557. doi:10.1016/j.jcct.2022.07.002 (resolved at Crossref by Lima).
- Forte E, et al. Normal patterns of left ventricle rest myocardial perfusion assessed by third-generation cardiac
  CT. *Clin Physiol Funct Imaging* 2020;40:30–36. doi:10.1111/cpf.12598. Septal TPR 1.06 ± 0.06 (Golf citations).
- Ichikawa Y, et al. Adipose tissue detected by multislice CT in patients after myocardial infarction. *JACC
  Cardiovasc Imaging* 2009;2:548–555. doi:10.1016/j.jcmg.2009.01.010. Fat in 62 % after MI vs 3 % of controls.
- Ide S, et al. Cardiac CT-derived myocardial mass at risk using the Voronoi-based segmentation algorithm: a
  histological validation study. *J Cardiovasc Comput Tomogr* 2017;11:179–182. doi:10.1016/j.jcct.2017.04.007
  (Hotel citations).
- Kurata A, et al. Quantification of the myocardial area at risk using coronary CT angiography and Voronoi
  algorithm-based myocardial segmentation. *Eur Radiol* 2015;25:49–57. doi:10.1007/s00330-014-3388-2 (Hotel
  citations).
- Shah DJ, et al. Prevalence of regional myocardial thinning and relationship with myocardial scarring in patients
  with coronary artery disease. *JAMA* 2013;309:909–918. doi:10.1001/jama.2013.1381. Thinning ≤ 5.5 mm (CMR,
  end-diastolic).
- Wasserthal J, et al. TotalSegmentator. *Radiol Artif Intell* 2023;5:e230024. doi:10.1148/ryai.230024; dataset
  v1 Zenodo 6802614, v2.0.1 Zenodo 10047292 (CC BY 4.0).
- Xu L, et al. Lipomatous metaplasia enables ventricular tachycardia by reducing current loss within the protected
  corridor. *JACC Clin Electrophysiol* 2022;8:1274–1285. doi:10.1016/j.jacep.2022.07.005. The −180 to 0 HU fat
  window (Hotel citations, full text).
- Yezzi AJ, Prince JL. An Eulerian PDE approach for computing tissue thickness. *IEEE Trans Med Imaging*
  2003;22:1332–1339. doi:10.1109/TMI.2003.817775 (resolved at Crossref by Lima).
- Zeng A, et al. ImageCAS. *Comput Med Imaging Graph* 2023. doi:10.1016/j.compmedimag.2023.102287.

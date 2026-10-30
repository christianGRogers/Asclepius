---
aliases: [India v2]
tags: [janus-m, plans, candidate, round-2, india, myocardium, path-rest-ccta]
status: submitted
round: 2
path: jm/rest-ccta
advocate: India
updated: 2026-10-30
issue: christianGRogers/Asclepius#142
---

# India v2: rest-CCTA Janus-M, measured where it can be and pre-registered where it cannot

**Advocate:** India. **Round:** 2, path `jm/rest-ccta` (LQ1 option A: rest-CCTA only). **Base:** the Janus-M master
plan ([[Juliet v1]] + JA1–JA14, [[Janus-M Round 1]]). **Evidence:** [[India - R2 E5-E8 one error model, depth, sectors, rest TPR and the twin guard]]
(code `experiments/JanusM/India/`, numbers `results/summary_r2.json`, `results/guard_r2*.json`,
`results/e8_repower_table.json`).

## 1. The plan in one paragraph

India v2 keeps the master plan as ruled: Janus-M 0 is `heartchambers_highres` plus the geometry, on ImageCAS-X
train; it is scored by border ASSD against read-vs-read; Janus-M 1 is trained only if Janus-M 0 fails. Round 2 adds
the things the ruling left open on this path, each settled by an experiment or fixed as code before any read:
- **why the Round 1 simulations disagreed**, and the one error model that replaces them (E5);
- **the depth and sector rules** at 0.5 mm (E6), and the **territory rule** measured on ImageCAS-X by a CPU add-on to
  Job JM-0;
- **whether rest TPR is measurable** at native resolution with a guard band (E7);
- **the seal re-powering rule and the JA8 margins**, as code (E8);
- **the JA12 twin rule**, applied, with its cost (it refuses 692 of 1,228 public subjects);
- **the border protocol** for the reads;
- and, for Path A, **what the 17 × 3 × territory table gives a reader beside the coronary findings, and how its
  signs are calibrated with no scar reference**: by a fixed false-positive rate in a normative reference, by
  read-to-read reliability, and by pre-registered checks of where the signs fall. No sign is ever called scar.

## 2. What is unchanged from the master plan

JA1 (four learned classes), JA5 (ImageCAS-X train; the "never" list), JA6 (Juliet's draw, the freeze before any
read), JA7 (two reads, half-maximum rule, coarsened seeds, 10 blank reads), JA9 (Janus-M 0 = seed + geometry;
Janus-M 1 conditional, nnU-Net ResEnc, 0.5 mm, mirroring off), JA10 (compute), JA11 (Stage A labelled "research,
not validated"), JA12–JA14. Where this plan changes a JA rule, it says so and why (§10).

## 3. Round 1 §6, item by item

### 3.1 Item 1: Job JM-0, and what it must also measure

Job JM-0 runs as committed (Juliet v1 §7, ≤ 1 GPU-h). India adds a **CPU step on the same 40 cases**, run on the
login node after Juliet's geometry step: `experiments/JanusM/India/fir/jm0_addon.py` (command in §8). It reads only
the JM-0 list, refuses the whole run if any case is in the Janus-M seal or decision proposals or in the A14 sealed or
ImageCAS-X test lists, and prints aggregates only. It measures:

| Block | What | Settles |
|---|---|---|
| A | Half-maximum edge offsets of `heartchambers_highres`, endocardium and free-wall epicardium (mm; + = label outward of the image edge) | Item 1: does v1's 0.86 mm outward epicardial bias (Hotel) persist at native resolution? |
| B | Equal-thickness vs Laplace third agreement on the native grid | Item 3 (depth), on real CCTA |
| C | Fixed vs septal-arc-proportional sectors: myocardium that changes segment and AHA territory; the septal arc | Item 3 (sectors) |
| D | Euclidean vs epicardial-geodesic territories from the **ImageCAS-X reference** coronary labels: voxel disagreement, segments discordant with the AHA default under each | Item 3 (territories) |
| E | Rest TPR per segment, no guard band and a 1 mm guard band | Item 6 |
| F | The myocardial core HU distribution (≥ 1 mm from both borders): quantiles and share in −180..0 HU | Item 6 (fat cut-off) |

Juliet's step already reports voxels per third, the thickness distribution, AHA failures and territory discordance.

**What the numbers change** (pre-registered; §9 has the full table):
- **A:** if either median offset exceeds 0.5 mm, the seeds carry a bias that the readers must undo, so the anchoring
  report (JA7) is read per border and a seeded read is accepted only if the blank-vs-seeded difference on that border
  is within read-vs-read. If the epicardial offset is ≥ 0.5 mm, Janus-M 0 is expected to fail the JA8 bias guard and
  the ≈ 100 training reads are requested at the first decision-set look, not after it.
- **D:** if Euclidean and geodesic territories disagree on < 5 % of voxels, JA4's Euclidean rule stays and geodesic
  is dropped. Otherwise both are reported and the lead is asked which is primary (it cannot be decided without a
  perfusion reference, which Path A does not have).

### 3.2 Item 2: one error model (E5)

**Finding.** The four Round 1 curves disagree because their signed-distance functions convert a field value into a
surface shift with different gains, not because their error physics differ. E5 re-implemented each advocate's
committed perturbation on the same ⟨E5n⟩ public cases and measured what each one actually does to the border.

⟨E5 TABLE⟩

**Ruling asked for: one error model.** India proposes **U**: the slope-1 SDF (surface half-way between voxel centres)
on 0.5 mm, a Gaussian random field of RMS σ and correlation length 8 mm per border, plus fixed biases. U is
**indexed by the realised border ASSD**, not by σ, so any later simulation is comparable with any other and with
reads. In U (⟨E5n⟩ cases):

⟨E5 U TABLE⟩

What this changes:
- **No absolute bar is read off any curve** (the ruling's point, now explained). India v1's 0.25 mm was σ in a
  slope-1.5 SDF; Hotel's "0.5 mm" was a field that moved most of the border by nothing.
- **STA is computed in U** by one harness (`harness_r2.py`). It is flat at realistic error and responds only when
  the realised ASSD approaches ⟨E5 sta knee⟩; it reports clinical consequence but does not discriminate models at
  the error levels JA8 accepts. It stays **reported**, as ruled.
- **Segment thickness catches bias that ASSD and Dice do not** (U's bias rows), confirming JA8's co-primary.

### 3.3 Item 3: depth, sectors, territories (E6, and JM-0 block B–D)

**Depth.** ⟨E6 depth⟩ **JA2 stands: equal-thickness depth.** Yezzi–Prince is not adopted: on 0.5 mm it gives the same
thirds as equal thickness to within ⟨E6 agree⟩ of wall voxels, is no more stable under border error, and costs a
Laplace solve plus two upwind PDE solves per case. Laplace stays a reported alternative (JM-0 block B gives it on real
CCTA).

**Sectors.** ⟨E6 sectors⟩

**Territories.** No open CT carries coronary labels with the heart, so this is measured on ImageCAS-X by JM-0 block D
(reference trees, not Janus predictions; JA4). The rule is in §3.1.

### 3.4 Item 4: the written border protocol (JA7), and the read queue

The protocol below is the text the readers get; each numbered rule is checked by code on every submitted read where
it can be.

1. **Labels:** 1 LV myocardium (compact wall, septum included); 2 LV blood pool; 3 RV blood pool; 4 LA blood pool;
   0 everything else (JA1).
2. **Papillary muscles and trabeculae are blood pool (2).** The endocardial border follows the compact wall, under the
   trabeculae. *Check:* none (judgement); the inter-read endocardial bias is reported per wave.
3. **Half-maximum rule** (Hotel). A border lies halfway in HU between the plateaus on its two sides: blood and
   myocardium (endocardium; RV and LA side of the septum and atrial wall); myocardium and epicardial fat or adjacent
   tissue (epicardium). *Check (code):* the read's own half-maximum offset per border, computed as JM-0 block A
   computes it. A read whose median offset exceeds **0.5 mm** on any border is returned to its reader with the
   profile plot, once; a second failure is accepted and flagged.
4. **Basal limits.** The LV blood pool ends at the plane through the mitral annulus hinge points and, in the outflow
   tract, at the aortic valve annulus (the leaflet hinges). The LV myocardium ends at the same planes. The LA blood
   pool runs from the mitral annulus to the pulmonary vein ostia and excludes the appendage beyond its neck. *Check
   (code):* label 2 voxels and label 4 voxels never touch (a mitral "gap" of label 0 or 1 is required), and label 2
   contains no voxel more than 3 mm above the fitted mitral plane.
5. **The apex.** The myocardium closes over the apex; the cavity tip is the last short-axis slice with blood pool.
6. **What a reader must not draw:** layers, segments, scar, fat or territories (all computed; JA7).
7. **Seed.** `heartchambers_highres` mapped to the four labels, coarsened to 2 mm and smoothed (Golf). 10 of the 60
   seal cases are read from blank (JA7).

**Anchoring thresholds** (per wave of ≥ 10 cases; fixed now):
- seed-vs-read ASSD, read-vs-read ASSD and the share of voxels changed, per border;
- if the blank reads differ from the seeded reads (mean blank-vs-seeded ASSD) by more than the read-vs-read ASSD on
  that border, seeded reads of that border cannot accept a model whose borders resemble the seed (JA7): the deciding
  comparison for Janus-M 0 then uses the blank-read seal cases only, and the lead is told the seal's effective size;
- if fewer than 5 % of voxels are changed from the seed on average, the wave is flagged as possible rubber-stamping and
  the reader re-reads one blank case before continuing.

**The read queue** (for the JA13 `role:swe` issue; specification, not code):
- four-label NIfTI on the CT's native grid; one task per (case, reader); the second reader never sees the first
  read; readers see the seed only in seeded tasks;
- the order is the frozen `configs/janusm/sealed-r1.json` order: decision 40 first, then seal 60, the 10 blank seal
  cases interleaved at fixed positions;
- every submission runs rules 3 and 4 and stores the offsets, the time spent and the share of voxels changed;
- the queue is separate from SegQueue14 and starts after the coronary wave-1 start condition (LQ5 assumption).

### 3.5 Item 5: seal re-powering and the final JA8 margins (E8)

Fixed now, as code (`e8_repower.py`), run once on the first 20 double-read decision cases, before any seal read:
1. **Border margin** per border: 0.25 mm, unless the median read-vs-read ASSD on those 20 exceeds 0.5 mm; then half
   that median, capped at 0.40 mm. **Thickness margin:** 0.5 mm, unless the median per-segment read-vs-read thickness
   difference exceeds 1.0 mm; then half of it, capped at 0.8 mm. Set once, never revised.
2. **Seal size:** the smallest of 60, 80, 100, 120 (the pre-registered extension) at which a patient bootstrap,
   resampling Janus-M 0's 20 observed d values, puts the upper 95 % bound ≤ the margin with probability ≥ 0.80 on
   both borders. If none does, n = 120 and the plan records that acceptance is unlikely.
3. The seal never shrinks below 60 and is scored once.

What it implies today (E8 table, synthetic 20-case draws, margin 0.25 mm): with a per-patient SD of d of 0.25 mm and a
true mean of 0.15 mm, 60 cases pass with probability 0.92; with SD 0.35 mm and mean 0.15 mm, even 120 give only 0.84.
**So the seal size is set by Janus-M 0's mean excess, not by its spread**, and 60 is enough unless Janus-M 0 is
already near the margin, in which case Janus-M 1 is the better spend.

### 3.6 Item 6: rest TPR and the fat cut-off (E7, JM-0 blocks E–F)

**Rest TPR.** ⟨E7 result⟩

**Fat.** The cut-off cannot be set on public data here (no allowed public case is gated CCTA at native resolution with
a fat label). It is set on JM-0 block F, as a fixed rule:
- a core voxel (≥ 1 mm from both borders) is "fat-like" if its HU is ≤ **c**, where c is the **0.1th percentile of
  the pooled JM-0 core HU**, clamped to the verified −180..0 HU window (Xu 2022; JA11, JA14);
- a segment is "fat-positive" only if fat-like voxels form a connected cluster of ≥ 10 mm³ in it (so single-voxel
  noise cannot flag it);
- c is recorded in the plan and never re-tuned on reads.
The 40 JM-0 cases are not known to be scar-free (ImageCAS is a CAD-referral population), which makes c conservative
(too low), not too permissive.

### 3.7 Item 7: the JA12 twin rule, applied

Applied to both public `meta.csv` files (tables only; no image), before India opened any Round 2 case
(`guard_r2.py`, `results/guard_r2.json`):

| | Count |
|---|---|
| Held-out TotalSegmentator subjects (pool list, seal, every Round 10 draw) | 16, all present in v1 and v2.0.1 |
| Twins (same sex, same institute, age ±5 y, any study type; v1 or v2.0.1) | **692** of 1,228 subjects |
| v1 cardiac-protocol subjects: total / held out / twins / **allowed** | 130 / 15 / 92 / **23** |
| v1 subjects whose study covers the heart and are allowed (Round 2 universe) | 299 (23 cardiac) |

**The cost is not "a few public cases".** All 16 held-out subjects come from one institute (v1 letter H), the
largest in the release, so the rule refuses most of its same-sex patients within ten years of age. Narrower variants
(`results/guard_r2_variants.json`): same scanner model (v2.0.1) refuses 258 and leaves 52 cardiac subjects; age ±2 y
refuses 465 and leaves 49.

**Recommendation: keep the ruling's rule.** Under JA5 and JA9, public TotalSegmentator data enters Janus-M only as
report-only or (dropped) pretraining, so the cost falls on CPU experiments, which E5–E7 show can run on non-cardiac
thoracic studies (they need heart shapes, not CCTA contrast). The narrower variants trade a guarantee for cases
Janus-M does not need.

**Disclosure (Round 1).** 49 of the 64 public subjects India's Round 1 experiments used are twins under this rule.
None is a held-out subject (India v1 §11 and the ruling's check). The Round 1 numbers stay as recorded; nothing
from them enters a Janus-M seal, decision set or model. Round 2 opened no twin.

### 3.8 Item 9 (Path A): what the table gives a reader, and how its signs are calibrated

#### What the reader gets

One page per patient, placed **beside the coronary findings for the same arteries**. The coronary model (Janus)
segments LM, LAD, LCx and RCA (D25); it does not grade stenosis today, and grading is the coronary plan's work, not
Janus-M's. So the page has a **coronary column that takes whatever the coronary report carries for that artery**
(a grade when one exists; otherwise the vessel's presence and the reader's own grade), and Janus-M fills the rest:

| Per artery (LAD, LCx, RCA) | Content |
|---|---|
| Territory | Segments supplied, from the patient's own tree (JA4), with the AHA default beside it; a "discordant" mark where they differ |
| Mass at risk | Myocardial mass of the territory (g and % of LV) |
| Per segment × layer (inner, mid, outer; halves in thin walls) | Thickness (mm, and z against the normative reference); thinning flag; inner-third rest attenuation (z); fat-positive flag |
| Concordance | Whether the flagged segments lie in the territory of the artery the coronary column marks |
| Quality | Phase (ImageCAS: "phase-uncertain"), AHA orientation check (JA3), half-maximum offsets of this case's borders |

A bull's-eye (17 segments, three rings per segment) shows the same flags. **Every sign is printed as "research
output, not validated; not a scar or ischaemia test".** The reader uses it to look again at a segment, not to call
scar.

#### How the signs are calibrated without a scar reference

A threshold for a sign needs a reference for its sensitivity, which Path A does not have. Path A therefore fixes the
three things it *can* measure and states the fourth as unknown.

1. **Specificity, by a normative reference.** Thresholds are set as the 2.5th percentile (thickness, attenuation) of a
   **normative reference**: the Janus-M training cases (ImageCAS-X train outside the seal and decision set) whose
   corresponding artery has no stenosis ≥ 50 % in the coronary report, per segment and per sex, on Janus-M 0's
   borders. Until the coronary report grades stenosis, the reference is all training cases with robust statistics
   (median, MAD), and every threshold is labelled "population-relative". The target is a **per-patient false-flag
   rate ≤ 10 %** in the normative reference, with segment thresholds tightened (Bonferroni over 16 segments) until it
   is met. The CMR ≤ 5.5 mm cut is not borrowed (JA11).
2. **Reliability, by the reads.** On the 40 double-read decision cases, each sign is computed on read 1's borders and
   on read 2's. A sign is shown to readers only if its segment-level agreement between reads is κ ≥ 0.6; otherwise it
   is computed but hidden. This turns the read cost already planned into a reliability test of every sign.
3. **Construct checks, pre-registered, never used to tune.** Once the coronary report grades stenosis: (a) within
   patients, flags fall more often in the territory of a ≥ 70 % stenosis than in the patient's other territories
   (paired test); (b) fat-like clusters are subendocardial-dominant (Ichikawa 2009: 94 % subendocardial after MI);
   (c) thinning flags cluster in contiguous segments of one territory more than chance. Failing a check demotes the
   sign to "hidden"; passing it does not validate it.
4. **Sensitivity is unknown, and the page says so.** Path A cannot state how often a scar is missed. That is the
   price of option A, and the reason option B exists.

### 3.9 Item 8 (Path B only)

Not this path.

## 4. Data (JA5, unchanged) and the held-out guard

- **Janus-M images:** ImageCAS-X train only (seal 60, decision 40, JM-0 40, training the rest + 180 quality-0).
- **External, report-only:** the allowed pool stratum (JA5), re-derived by the shared guard (#138).
- **Public TotalSegmentator:** report-only and CPU experiments, after the twin rule (§3.7). No pretraining (JA9).
- **India's Round 2 experiments** opened only public TotalSegmentator v1 masks (and CT for the 23 allowed cardiac
  subjects; only one, s0032, was read, for the add-on smoke test with a fake coronary tree, and no number from it is
  reported). `guard_r2.refuse()` ran on every id before its first byte was requested. **No held-out subject and no
  twin was opened, read or scored.**

## 5. Model, metric, seal (JA6–JA9, unchanged except §10)

Janus-M 0 = `heartchambers_highres` + geometry. Metric JA8 with the E8 margin rule. Seal 60, decision 40, re-powered by
E8. Janus-M 1 only if Janus-M 0 fails.

## 6. Assumptions carried (LQ2–LQ8, the ruling's recommendations)

| Question | Assumed |
|---|---|
| LQ2 | LV myocardium + LV, RV, LA pools; no RV myocardium |
| LQ3 | `heartchambers_highres` used, key typed by the lead on Fir, never committed |
| LQ4 | ImageCAS-X train 560 + non-sealed quality-0 180 |
| LQ5 | 200 double reads + 10 blank, separate queue, after the coronary wave-1 start condition |
| LQ6 | MM-WHS signed for an external border check only, low priority |
| LQ7 | Released coronary patients may enter Janus-M training only, by explicit PR, never the seal |
| LQ8 | s0655: the coronary seal kept as it is |

**A new question for the lead (not a fork): the coronary column.** Path A's table needs a stenosis grade per artery.
The coronary plan does not produce one today. Is a stenosis grade on the coronary plan's road map, and may Janus-M
show the reader's own grade until then? India assumes **yes, reader's grade until the coronary report grades it**;
Janus-M builds no stenosis grader, since that would touch a coronary decision (README).

## 7. Compute (Fir, `def-aso22`; the lead runs every job)

| Job | What | GPU-h | When |
|---|---|---|---|
| JM-0 | Juliet v1 §7, as committed | ≤ 1 | Now |
| JM-0 add-on | `jm0_addon.py` on the same 40 cases, CPU, login node (≈ 30–60 min) | 0 | Right after JM-0 |
| Seeds on seal + decision | 100 cases | ≈ 2 | After the freeze PR |
| Normative reference | Janus-M 0 (seed + geometry) on the training cases | ≈ 10 (≈ 1 min per case, opinion) | After the decision-set look, only if Janus-M 0 passes; else on Janus-M 1 |
| Janus-M 1 | conditional, as ruled | ≈ 55 | Only if Janus-M 0 fails |

**Committed ≤ 3 GPU-h** (as ruled); **conditional ≈ 67 + 10 for the normative reference.**

## 8. Exact commands: the JM-0 add-on

After Juliet's JM-0 commands finish (its `geometry_m0.py` step included), on the Fir login node:

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius/repo && git fetch origin jm/rest-ccta && git checkout jm/rest-ccta && git pull --ff-only
source $HOME/icx4-tseg-venv/bin/activate      # or $HOME/icx14-venv if nibabel/scipy are missing
python experiments/JanusM/India/fir/jm0_addon.py --cases $SCRATCH/janusm/m0_cases.txt --hc $SCRATCH/janusm/hc \
  --icx $SCRATCH/icx4/icx --layout $SCRATCH/icx4/layout.json --out $SCRATCH/janusm/m0_india_addon.json
```

- **Check:** it prints `case 1/40 … case 40/40` with ok/fail, then one JSON block. If it prints `REFUSED`, stop and
  send that line back.
- **Send back on #142:** the final JSON block only (aggregates; no image, no per-case row).

## 9. What results would change this plan

| Result | Change |
|---|---|
| JM-0 A: a median half-maximum offset > 0.5 mm on either border | Seeds are biased on that border: anchoring read per border; training reads requested at the first decision look |
| JM-0 B: equal-thickness vs Laplace third agreement < 85 % on native CCTA | The depth choice matters on real walls: both are reported per segment and the lead is asked which is primary |
| JM-0 C: proportional sectors change < 10 % of mass on ImageCAS | Keep JA3's fixed sectors (the change is immaterial) |
| JM-0 D: Euclidean vs geodesic disagree on ≥ 5 % of voxels | Both territories reported; the lead picks the primary |
| JM-0 E: native rest TPR with the 1 mm guard has a median within 0.95–1.15 and < 10 % of segments < 0.99 | Rest TPR may be shown per segment (still "research"); otherwise it stays report-only |
| JM-0 F: the 0.1th core percentile is > 0 HU | No fat output on ImageCAS (the window is not met); fat stays a research field |
| Read κ < 0.6 for a sign on the decision set | That sign is hidden from readers |
| Janus-M 0's d on the first 20 decision cases puts the E8 seal at 120 | Janus-M 1 is triggered before the seal is read |

## 10. Changes to the master plan proposed by India v2

1. **One error model U, indexed by realised ASSD** (§3.2), replacing all Round 1 simulations; STA computed in it.
2. **Sectors:** ⟨sector proposal⟩ (§3.3).
3. **JM-0 add-on** (§3.1, §8): no GPU, closes items 1, 3 and 6 on real CCTA.
4. **E8 margin and re-powering rule** as code (§3.5).
5. **Border protocol and read-queue specification** (§3.4) for the JA13 issue.
6. **Path A calibration**: normative 2.5th percentile with a ≤ 10 % per-patient false-flag rate, κ ≥ 0.6 between reads,
   and pre-registered construct checks (§3.8).
7. **The twin rule kept**, with its counted cost (§3.7).

## 11. Risks

- **Rest-CCTA signs may never be useful.** Path A cannot know their sensitivity (§3.8, point 4).
- **The normative reference is not normal.** ImageCAS is a CAD-referral population; until the coronary report grades
  stenosis, thresholds are population-relative.
- **E5–E7 use public 1.5 mm shapes upsampled to 0.5 mm.** The error-model conclusions are about geometry and hold for
  any wall; the TPR phantom's absolute numbers depend on the assumed PSF and noise, which is why JM-0 block E measures
  them on real CCTA.
- **The JM-0 add-on is smoke-tested only** on a public 1.5 mm case with a fake coronary tree; its first real run is
  the lead's.

## 12. Citations

All but one were verified in Round 1 (India v1 §13; Hotel's and Golf's citation files); the new one was resolved at
Crossref for this round.

- **[Cerqueira 2002]** *Circulation* 2002;105(4):539–542. doi:10.1161/hc0402.102975. The 17 segments, 60°/90° sectors and the default territories (the territory figure is from secondary sources, JA14).
- **[George 2009]** *Circ Cardiovasc Imaging* 2009;2(3):174–182. doi:10.1161/CIRCIMAGING.108.813766. TPR; abnormal < 0.99.
- **[Forte 2020]** Forte E, Punzo B, et al. *Clin Physiol Funct Imaging* 2020;40:30–36. doi:10.1111/cpf.12598. Normal rest perfusion by layer; septal TPR 1.06 ± 0.06 (Golf v1, ruling §1).
- **[Ichikawa 2009]** *JACC Cardiovasc Imaging* 2009;2(5):548–555. doi:10.1016/j.jcmg.2009.01.010. Fat after MI 62 % vs 3 %; subendocardial 94 %.
- **[Shah 2013]** *JAMA* 2013;309(9):909–918. doi:10.1001/jama.2013.1381. CMR thinning ≤ 5.5 mm (not borrowed; JA11).
- **[Xu 2022]** Xu L, et al. *JACC Clin Electrophysiol* 2022;8(10):1274–1285. The −180..0 HU CT fat window (Hotel, full text; JA14).
- **[Yezzi 2003]** Yezzi AJ, Prince JL. An Eulerian PDE approach for computing tissue thickness. *IEEE Trans Med Imaging* 2003;22(10):1332–1339. doi:10.1109/TMI.2003.817775 (Crossref, resolved for this round).
- **[Jones 2000]** *Hum Brain Mapp* 2000;11(1):12–32. Laplace transmural coordinate.
- **[Kim 2000]** *N Engl J Med* 2000;343(20):1445–1453. doi:10.1056/NEJM200011163432003. Transmurality bins (STA).
- **[Ortiz-Pérez 2008]** *JACC Cardiovasc Imaging* 2008;1(3):282–293. doi:10.1016/j.jcmg.2008.01.014. 23 % of infarcted segments discordant with the default territory.
- **[Ide 2017]** *J Cardiovasc Comput Tomogr* 2017;11(3):179–182. doi:10.1016/j.jcct.2017.04.007. Voronoi territories vs histology (swine).
- **[TS]** Wasserthal J, et al. *Radiol Artif Intell* 2023;5(5):e230024. doi:10.1148/ryai.230024. v1 Zenodo 6802614 and v2.0.1 Zenodo 10047292 (`meta.csv` of each, read as tables), CC BY 4.0.

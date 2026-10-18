---
tags: [plans/experiment, statistics, evaluation, A10, A14, sealed-test, power, D6, D22, D23, D25]
author: Bridge
round: 9
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
---

# No team read will ever touch the sealed test, so A10 needs a sealed pool set of about 150 patients

## Question (Round 9)

The 4-class model is trained on ImageCAS-X (D8, D25), and team reads now come only from the SegQueue14 pool
(D22, D23). Two questions follow:

1. Can the acceptance rule A10 (D6: per class, the model's tF1 against the team's reads must be non-inferior
   to inter-read tF1 within 0.05) still be scored on the frozen sealed test ([[Sealed test]], A14)?
2. If not, which cases should replace it, and how many are needed for the rule to pass a model that is as
   good as a second reader?

## 1. The frozen sealed test cannot be scored by A10

The A14 sealed test is 80 ImageCAS-X test cases plus 20 quality-0 ImageCAS cases. It was designed to be
scored "against team reads" ([[Sealed test]], *Use*). Since 2026-10-14 none of those 100 cases will ever be
read:

- **D22:** the 800 ImageCAS-X cases are not annotated.
- **D23:** SegQueue14 serves only the 675 pooled volumes and no ImageCAS case, labelled or not.

So A10, which needs two reads per case, has no cases. What remains scoreable is model vs ImageCAS-X on the
80 sealed ImageCAS-X test cases. That is a model-vs-expert benchmark; it has no inter-read baseline, so it
cannot apply D6.

**ImageCAS-X's own second read is not public.** ImageCAS-X had a second analyst re-annotate all 160 of its
test cases, blinded and without lead review (arXiv:2608.30404, Table 1: per-segment inter-observer Dice LM
91.9 ± 13.7, LAD 92.3 ± 6.7, LCx 84.8 ± 19.8, RCA 95.3 ± 5.0; see
[[How well two annotators agree on per-branch coronary labels]]). Those reads would give a ready-made A10 on
the sealed 80. But I listed the Zenodo archive (record 10.5281/zenodo.21887809, `ImageCAS-X_dataset.zip`,
central directory read by HTTP range on 2026-10-18). It holds 3210 entries: 800 segmentations, 1600
centrelines, 800 surfaces, the split lists and `Descriptors.xlsx`. That is **one segmentation per case. The
second analyst's 160 test annotations are not released.** Asking the authors for them is a question for the
lead (§ What it changes).

Their spread is also a hint for the inter-read scenario: the LCx inter-observer SD (19.8 Dice points) is far
wider than the other classes. So k > 1 is plausible for the LCx (Dice, not tF1, and another convention).

**Consequence.** A10 needs a new sealed set, drawn from the pool, before any pool read is inspected. Echo's
audit (#49, item 3) found a related problem: icx4's `score.py` would open the old seal by scoring all 160
ImageCAS-X test cases. The two fixes are complementary:
- the sealed 80 ImageCAS-X cases stay sealed, for one blind model-vs-expert look at the final model;
- the new pool seal carries A10.

## 2. The pool: 675 volumes are 517 patients

`configs/segqueue14/pool-2026-10.txt` lists 675 volumes from 26 sources. Grouping them by patient (source
plus case name, with time-point, phase and series suffixes removed; heuristic in `seal_pool.py`) gives
**517 patients**. 60 patients have more than one volume, and one has 20 cardiac phases. For A10 the unit of
n must therefore be the **patient**. Twenty phases of one heart are not twenty independent cases. All
volumes of a sealed patient leave training.

The pool is also much more varied than ImageCAS:

| Stratum | Sources | Patients | Why |
|---|---|---|---|
| **primary** | 22 adult sets: Taiwan AI CUP (100), Mendeley SDN sets, VMR, Kaggle CAD, Figshare EpicardialFat, IDC lung/chest CT, TotalSegmentator cardiac, … | 360 | Four-class protocol and A1's aortic ostium are defined |
| **report only** | ImageCHD (congenital heart disease) | 83 | Anatomy often outside the 4-class protocol |
| **excluded for now** | ImageALCAPA, HOCMvalvesSeg, CCA200-HF ("header spacing suspect" in the pool list) | 74 | tF1's 1.5 mm tolerance (D3) is in mm, so a wrong voxel spacing makes the score meaningless. ImageALCAPA is also anomalous by definition: the left coronary arises from the pulmonary artery, so A1 cannot place an aortic left ostium |

## 3. Power of A10 on a pool seal

**Method** (`experiments/Bridge/r9/a10_pool_power.py`, CPU, 4000 simulations per cell, seed 20261018).
- Model per-case tF1 is resampled from run 1's 80 val cases scored under A1 (atlas2
  `per_case_run1.json`; SD LM 0.081, LAD 0.078, LCx 0.111, RCA 0.079). This keeps the real heavy tail.
- Inter-read tF1 is an independent draw with SD = k × the model SD. ρ ≈ 0, as Crucible measured.
- "Pass a class" means the lower 95 % bound of the mean of (model vs reads − inter-read) is above −0.05.
  Pass A10 means all four classes pass.
- Scorable share per class: LM 0.85 (short or absent LM, LM optional under D13), others 0.95. Without the
  A1b review of flagged ostia: LM 0.80, LAD/LCx 0.90, RCA 0.70.
- **f** inflates the model SD on the pool relative to ImageCAS val: 1.0, or 1.5 for a harder, more varied pool.
- **δ** is the true model − inter-read difference.

**P(pass all four classes) at δ = 0** (a model exactly as good as a second reader), with inter-read SD equal
to the model SD (k = 1) and the A1b review done:

| n patients | f = 1.0 (pool like ImageCAS val) | f = 1.5 (pool harder) | Binding class |
|---|---|---|---|
| 50 | 0.37 | 0.06 | LCx |
| 100 | 0.84 | 0.30 | LCx (0.88 / 0.57) |
| **150** | **0.97** | **0.58** | LCx (0.97 / 0.72) |
| 200 | 0.99 | 0.77 | LCx (0.99 / 0.84) |
| 250 | 1.00 | 0.88 | LCx |
| 300 | 1.00 | 0.94 | — |

Other cells, n = 150 and f = 1.0:

| Scenario | P(pass all four) |
|---|---|
| k = 0.5 (readers agree twice as tightly as the model) | 1.00 |
| k = 1.5 | 0.82 |
| δ = −0.02 (model slightly worse than a reader) | 0.43 |
| δ = −0.03 | 0.05 |
| δ = −0.05 (at the margin) | 0.00 |
| No A1b review | 0.95 (0.51 at f = 1.5) |

**Readings.**

1. **Under D6's 0.05 margin, A10 is workable.** Round 6 and Round 7 found that per-class A10 rejects a
   human-level model at n = 100. That was at a 0.02 margin. At 0.05 and n = 150 it passes such a model
   97 % of the time when the pool behaves like ImageCAS val.
2. **The LCx sets the size**, because it has the widest per-case spread (0.111). It was also the weakest class
   in run 1 (0.846).
3. **The unknown is the pool's spread (f).** The pool mixes 26 sources, lung-protocol and gated chest CT, and
   many scanners. If it is 1.5× more variable than ImageCAS val, 150 patients pass a human-level model only
   58 % of the time, and about 250 are needed for 88 %.
4. **A10 is strict about small deficits.** A model 0.02 below a reader passes 43 % of the time at n = 150; at
   0.03 below, 5 %. This is the design working as specified (one-sided 2.5 % per class at the margin), not a
   flaw. But a domain-shift deficit of 0.02–0.03 on the pool is plausible for a model trained only on
   ImageCAS.
5. **The A1b review stays a power requirement.** It is worth 0.02–0.07 in pass probability (n = 150).

## 4. Proposed seal (not binding until the judge adopts it)

`experiments/Bridge/r9/seal_pool.py` → `experiments/Bridge/r9/sealed_pool_proposal.json`.
- Salt `asclepius-sealed-round9-pool:`; patients ranked by sha256 of salt + patient key.
- Stratified by source, allocated in proportion with a largest remainder, and at least one patient from any
  source with ≥ 5 patients.
- **Primary: 150 patients** (216 volumes) of 360. For example, Taiwan AI CUP 42 of 100, Mendeley SDN
  cy54ttk3fj 17 of 40, EpicardialFat 14 of 34, VMR 12 of 30, Kaggle CAD 12 of 28.
- One scoring volume per patient: the lowest-ranked volume.
- **Report only:** 20 ImageCHD patients.
- **Pre-registered extension order:** the next primary patients by rank, round-robin by source. If wave-1
  reads on *non-sealed* pool cases show f > 1.2 or k > 1.2, the seal is extended along this order to 200 or
  250 **before any sealed read is scored**. The extension is decided on non-sealed data only, so it does not
  peek.
- **Cost to training:** sealing 150 of 360 primary patients removes 216 volumes (32 %) from any pool
  fine-tune. The ImageCAS-X training data (560 + 80) is untouched.

The patient-key heuristic must be confirmed per source by whoever builds it. In particular,
Figshare-23057000's `PA0` and `PA1` are kept as two patients.

## What it changes

- A10 (D6) moves to a **sealed pool set**: 150 primary patients, extendable to 250 on wave-1 evidence,
  one volume each. It is published before the first pool read is exported and kept out of every fine-tune.
- The **80 sealed ImageCAS-X test cases** stay sealed for one blind model-vs-expert look at the final model.
  Every interim decision uses the 80 open test cases (36 clean + 44 development, reported apart).
- The **20 sealed quality-0 cases** have no reads and no ImageCAS-X labels, so no score can use them. They
  are retired (proposal for the judge).
- icx4's **Dice-only scorer decides nothing** under A1/A1c. The decisive stage is issue #54.
- **Question for the lead:** ask the ImageCAS-X authors for their unreleased second-analyst annotations of
  the 160 test cases. With them, A10 can also be scored on the sealed ImageCAS-X 80, against expert double
  reads, at no annotator cost. The two A10 sets would then cross-check each other: in-domain experts, and
  out-of-domain team reads.

## Caveats

- The model spread is from run 1 (D0 thick convention, scored against the projected proxy). The 4-class
  ImageCAS-X model's spread is unmeasured until icx4 is scored. The table should be re-run on icx4's open-80
  per-case tF1.
- The inter-read spread is a scenario. Wave 1 replaces it.
- Classes are treated as independent within a case. Positive correlation between classes would raise
  P(all four) slightly, so the table is mildly conservative.
- No sealed case was touched; only the pool *list* was read, not any volume or read.

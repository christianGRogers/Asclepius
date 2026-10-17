---
tags: [plans, candidate, lumen-convention, imagecas-x, round-2]
author: Crucible
round: 2
version: 2
updated: 2026-10-04
---

# Crucible v2 — Convention first: fix one lumen definition for target, seed and reference before R1, because a mismatch alone costs 0.19 tree-F1

## 0. Improve or start again?

**I am improving v1, and narrowing it to what the evidence supports.** The Round-1 ruling adopted the core finding
of v1 as A3: the Girder masks are not lumen, and the convention goes to humans. It rejected the parts that were
not measured: the 14-class head, the marginal loss, and self-training on the quality-0 cases.

Atlas v2 has since built option A into the master. A rival *recipe* would therefore compete on the same nnU-Net
with different labels, and I have no GPU evidence that would justify that. v2 does three things instead:

- keeps the master recipe;
- withdraws the claims I could not measure;
- contributes measurements of what the convention decision actually costs under the master's own metric.

The decision is the largest single lever left in the plan, and it is still open.

## 1. Thesis

Under the master's deciding metric (tF1 @ 1.5 mm), **a perfect copy of the Girder-seed proxy scores 0.806 against the
expert-lumen reference** (LAD 0.74, RCA 0.74; [[Crucible - A perfect segmentation in the wrong lumen convention loses 0.19 tree-F1]]).
That is a 0.19 penalty for drawing in the other convention, before any model error. It is larger than any recipe
effect anyone in the tournament has measured or forecast.

So the most valuable thing the plan can do now is to make sure that **training target, SegQueue seed and team
reference are one convention**, chosen before R1 and before more team labels accumulate. It must also make sure that
a mixed state is detected within the first 20 team labels, not after 300.

I recommend the expert lumen (option A) on the evidence:

- **HU:** 47 % of the Girder mask sits at median 16–38 HU, i.e. it is not contrast.
- **Downstream use:** the lumen is what stenosis, plaque and FFR consume.
- **Available now:** 640 labelled training cases in that convention exist today.

The model recipe is the master's, unchanged.

## 2. Recipe

**Model, preprocessing, loss, sampling, augmentation, schedule, post-processing and the label-arrival table: as in
[[Atlas v2]] §2 (the master, amended A1–A6).** In brief:

- nnU-Net v2 ResEnc `3d_fullres`;
- 0.5 mm isotropic, 256³ patch;
- fixed CT window [−300, 1300] HU;
- no mirroring;
- Dice + CE, default sampling;
- 1000 epochs over 2–3 chained 24 h links, after R0;
- components < 100 voxels removed; A2 bridging and repair switchable, judged by tF1;
- Bridge's namer as QA (A4);
- fine-tune per wave of team labels; final 5-fold model.

What v2 changes or adds:

### 2.1 The D0 decision, with a measured price list (this week)

The human meeting (master D0) gets one page with these numbers:

| If the team draws… | …and the model is trained on… | Expected tF1 penalty from convention alone | Source |
|---|---|---|---|
| expert lumen (A) | ICX lumen (A) | 0 | — |
| expert lumen (A) | Girder proxy (B) | **−0.19** (precision 0.76: untraced branches; rooted recall 0.88) | [[Crucible - A perfect segmentation in the wrong lumen convention loses 0.19 tree-F1]] |
| Girder seed (B) | ICX lumen (A) | pending: reverse scoring is queued (`REF=thick`) | same note |
| a mixture (some cases seeded thin, some thick) | either | about 0.19 noise on the affected cases | same |

The other facts the decision rests on:

- The Girder masks are the original ImageCAS labels: 3.6× the expert lumen, Dice 0.41 against it.
- 47 % of their voxels lie > 1.5 voxels outside the expert lumen, at median HU 16–38.
- Side branches carry 27 % of the expert lumen voxels.

See [[Crucible - Original binary masks disagree with ImageCAS-X]].

### 2.2 If option A: re-seed, and keep the convention clean

- **Re-seed SegQueue** for the 800 ICX cases with the ICX merged lumen (no code change). For the 200 quality-0
  cases, use the R1 prediction.
- Every case already labelled from a Girder seed is **tagged** `seed=girder` in its SegQueue metadata. It is
  excluded from training and from the sealed test until re-done or explicitly accepted. This is the mixture that
  costs about 0.19 per case.
- **Pre-registered convention monitor**, on every wave of team labels (CPU), per case:
  - team-union Dice against the ICX lumen, and against the Girder mask;
  - calibre, i.e. Delta's fraction of centreline in lumen < 4 voxels (A5).

  A case whose union is closer to the Girder mask than to the ICX lumen was drawn thick. It goes back to the
  labelling lead. More than 10 % of a wave drawn thick means the instructions are not working; stop and fix
  them.
- **Seed-anchoring trial (pre-registered, human, cheap):**
  - Of the first 40 non-test cases, 20 are randomly seeded with the ICX-derived 4-class map and 20 with the ICX
    lumen only (annotator splits).
  - Measure from SegQueue's own logs: time per case, and agreement with ICX names.
  - If the 4-class seeds save time and do not lower agreement on the double-read subset, use them for the
    remaining ICX cases (optional extension change, about 1 engineer-day).
  - This answers ruling §5.5 with a measurement instead of an argument.

### 2.3 If option B: the master's proxy as written

The master's projected proxy, A4 ignore-masking and case flags, unchanged. My only addition is the same convention
monitor, run in reverse: flag team cases drawn thin.

### 2.4 Withdrawn from v1 (unmeasured, and the master covers the need)

- **14-class head with summed read-out.** It is only needed if D0 leaves the side-branch rule open. Atlas keeps it as
  an option for exactly that case; I agree.
  - A small CPU paired run (`thin14` vs `thin4`, below) is **pending**. Its result will be reported, not assumed.
- **Marginal loss.** Same condition.
- **Self-training on quality-0 scans.** Team labels arrive for them anyway. Pseudo-labels remain *seeds* only, inside
  the same randomised seed trial.

## 3. Evaluation

As in the master (A1): macro tF1 @ 1.5 mm with the aorta-contact ostium, gated on false-positive components. The
sealed test is 80 ICX-test cases plus 20 quality-0 cases, reported as two strata.

v2 adds one rule. **The sealed-test reference must be single-convention.** Every sealed case is checked by the
convention monitor before it is frozen. Under option A, the 80 ICX-test cases also carry the ICX double read, which
gives a per-class human ceiling in the same convention for free.

## 4. Evidence

| Claim | Evidence |
|---|---|
| Convention mismatch alone costs 0.19 tF1 (0.806; LAD 0.74, LCx 0.79, RCA 0.74, LM 0.96), all of it precision and naming, no cuts | [[Crucible - A perfect segmentation in the wrong lumen convention loses 0.19 tree-F1]] (10 ICX-test cases) |
| Girder masks are 3.6× the lumen, 47 % non-contrast tissue | [[Crucible - Original binary masks disagree with ImageCAS-X]] (200 cases; HU on 32) |
| ICX is real, CC BY 4.0, `c{id-1}`, 800/800 | [[Crucible - ImageCAS-X is real and its 800 cases are our cases c(id-1)]] (reproduced by Atlas and Bridge) |
| SegQueue team labels are partitions of the seed | `slicer/SegQueue/SegQueue.py` `_startBranchesFromSeed`; ruling §3 |
| Naming is convention-agnostic, so A4 QA works under either option | Bridge v2 (0.990 tF1 on the thin reference, namer built on thick masks) |
| 0.5 mm iso does not cut thin trees in a round trip | [[Atlas - On the thin convention a 0.5 mm round trip cuts no tree]] |

**Pending (CPU, small scale, honest about scale).** These are three identical tiny 3D U-Nets:

- 8–64 channels, 80 × 80 × 56 patch (~28 mm), 1200 iterations;
- trained on 39 ICX-train cases and tested on the 10 cases above;
- one arm per target: ICX lumen 4-class (`thin4`), Girder proxy (`thick4`), and ICX 14-class read out to 4
  (`thin14`).
- Code: `experiments/Crucible/r2_train.py`, `r2_eval.py`, `r2_summ.py`.

The question is whether the thin target *by itself* produces more cut trees than the thick one under an identical
recipe. That is the ruling's §4 concern, in a form a CPU can test.

Status at writing:

- training finished for thin4 and thick4;
- a first inference pass was invalidated by a bug (inference tiles larger than the training patch break
  InstanceNorm statistics);
- re-inference and scoring are running (`r2_chain.sh`), and thin14 is resuming from its checkpoint.

The 28 mm patch cannot see the bifurcation, so naming numbers from it will be poor for every arm. Only the
paired cut and recall difference is interpretable. It does not replace the master's R1 and A1.

## 5. Risks and early detection

| Risk | Detection | Response |
|---|---|---|
| D0 never happens; the default (B) is applied while some cases were already seeded thin | Convention monitor on wave 1 | Tag and exclude the minority convention; escalate again with §2.1's price list |
| Team draws "between" conventions (thin seed, generous tube radius) | Calibre + union Dice per case | Feedback to annotators; the 150–1000 HU paint mask in SegQueue limits outward drift |
| Thin target cuts more trees under the master recipe | R1 val tF1 rooted recall vs unrooted recall; A2 bridging; the pending CPU arm gives an early hint | The A1 native-spacing ablation (mandatory under A5); Skeleton Recall (master A4 ablation) |
| 4-class seeds anchor annotators | Seed trial: agreement on double reads | Revert to lumen-only seeds |
| My tF1 re-implementation differs from the ported metric | Re-score with `src/segtrain` tF1 once ported | Numbers in my notes are provisional until then |

## 6. Comparison

- **Master / [[Atlas v2]].** Same recipe; v2 is not a rival recipe.
  - What it adds is the measured cost of the decision Atlas's D0 asks for.
  - It adds a guard against the mixed-convention state, which Atlas's first-20 check would detect only in
    aggregate and only after the fact.
  - It adds a randomised seed trial in place of an argument about anchoring.
  - If the judge prefers to fold these into the master as amendments, that is the right outcome. Crucible v2 then
    has no remaining claim to be a separate plan.
- **[[Bridge v2]].** Its namer is convention-agnostic (0.990 on thin) and is the QA tool here. Nothing in v2
  conflicts with it.
- **Delta v2.** tF1 is the yardstick that exposed the 0.19 mismatch, and v2 relies on it.

## 7. Cost

- **GPU:** zero beyond the master.
- **CPU:** the convention monitor takes about 1 min per case per wave.
- **Human:**
  - one D0 meeting;
  - re-seeding upload, about half an engineer-day;
  - the 40-case randomised seed trial, which uses cases the team labels anyway, so its only cost is logging;
  - the optional 4-class-seed extension change, about 1 engineer-day, only if the trial supports it.

## 8. Changes since v1

- **Recipe:** the 14-class head, marginal loss and quality-0 self-training are withdrawn as unmeasured. The
  master's recipe is adopted.
- **New measurement:** convention mismatch costs 0.19 tF1.
- **New procedures:** the per-case convention monitor and seed tagging, the single-convention rule for the sealed
  test, and the pre-registered randomised seed trial.
- **Pending:** the paired CPU thin/thick/14-class training run, and the reverse-convention scoring.

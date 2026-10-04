---
tags: [plans, candidate, topology, post-processing, inference, evaluation]
author: Delta
round: 2
version: 2
updated: 2026-10-04
---

# Delta v2 — the master's model, with a connectivity stage measured on real predictions: look again at every gap before bridging it, and gate false positives before repair

## 1. Thesis

**Improve, not restart.** The master (Atlas v2) already carries my yardstick (tF1) and my
post-processing ideas. But it carries them in the v1 form, which the ruling rightly called an upper
bound. Measured this round on 16–17 real predictions, that form has three defects.

1. **3 mm bridging alone buys about +0.01 tF1@1.5**, not +0.13.
2. **5 of its 12 joins attach a false-positive blob to the tree.** In doing so they *reduce* the FP
   count that the master's gate reads (1.18 → 0.88 per case). The master's own false-connection audit,
   which looks for tubes > 2 mm from reference, would not catch them, because these tubes are short.
3. The master leaves the ostium to TotalSegmentator plus a 30-case check. That was validated on
   nothing, and TotalSegmentator needs about 7 GB.

The step that does work is new: **gap-centred re-inference**. For each piece cut off from the ostium,
the same network is run once more on a window centred on the gap. Its probability is fused with the
first pass, and only then is the gap bridged. On 16 real predictions this raised tF1@1.5 from 0.829
to 0.854. It made **no case worse** and repaired exactly the cut trees (c0407 0.756 → 0.938,
c0113 0.523 → 0.700, c0675 0.829 → 0.867). It needs no training and costs 0–6 extra windows per case.

So v2 keeps the master's model and training plan unchanged, and replaces its post-processing and
gating with a **measured connectivity stage**:
- re-inference, then bridging;
- the FP gate counted before any repair;
- every bridge audited;
- a validated ostium procedure (two cheap rules that found 116/116 true ostia, with every miss flagged).

What remains after repair is a short list of long distal gaps (3 of 16 cases). That list is a
training problem, and it is where the one training arm I add points.

## 2. Recipe

### 2.1 Unchanged from the master (Atlas v2 + Round 1 amendments)

I keep all of the following as written: the D0 human decisions; R0 first; the 4-class ResEnc
nnU-Net at 0.5 mm isotropic with a 256³ patch; the fixed CT window; no mirroring; the proxy factory
with A4 QA; the A0–A4 ablations, including Skeleton Recall judged after post-processing; the
label-arrival schedule; the sealed test; and tF1@1.5 as the deciding metric. I have no measurement
that beats any of these.

### 2.2 Connectivity stage (replaces master §2.6 P1; P2 label repair and P3 rule renaming stay as written)

Run on every validation and test prediction, CPU or GPU, in this order. Every step is off until it
wins on the val fold by tF1 (paired bootstrap), as the master requires.

0. **Gate first.** Record FP components per case (predicted components touching no reference vessel)
   on the *raw* prediction (threshold, then drop components < 100 voxels). The acceptance gate uses
   this number, never the post-repair one.
1. **Ostium / anchor structure.** Use the TotalSegmentator aorta (run on Trillium for all 1000).
   Cross-check against two CPU rules:
   - *thick*: the thickest reference endpoint;
   - *pool_thick*: the thickest endpoint near the contrast blood pool (`treelib.blood_pool`).

   A tree where the rules disagree by > 5 mm is flagged for a human, not scored silently. On 116
   trees the two cheap rules were each ≥ 98 % within 5 mm and never failed on the same tree.
   Deployable anchors (no reference used) are the 2 largest predicted components within 3 mm of the
   aorta.
2. **Gap-centred re-inference (new).** For every component ≥ 100 voxels that is not anchored but lies
   within 15 mm of an anchored one:
   - run the model once on a window centred on the gap midpoint (the plan's own patch size);
   - fuse with the first pass by voxel-wise max inside the window;
   - re-threshold at 0.5.

   (`experiments/Delta/regap.py`. Max fusion beat mean: 0.837 vs 0.832 before bridging.)
3. **Bridging ≤ 3 mm, with support required.** Join an orphan to the anchored set only if both hold:
   - the gap is ≤ 3 mm after step 2;
   - the orphan **overlaps a re-inference window that predicted it again** (≥ 50 % of its voxels
     ≥ 0.5 in the second look).

   The second condition targets the FP-blob joins. It is a *proposal*, not yet measured: it follows
   from the 5/12 finding, and its effect is the first thing to check on R1's val fold.
   (`postproc.bridge`; tube radius 1 voxel; the tube takes the orphan's class.)
4. **Audit, always reported.** For every case, record:
   - the number of bridges;
   - orphans with no reference support (FP joins; measurable on val and test only);
   - cross-tree joins;
   - tube voxels > 1 mm off reference;
   - FP components before and after repair.
5. P2 label repair, then P3 rule renaming, as in the master.

### 2.3 One training arm (paired, 250 epochs, judged by tF1 after §2.2)

**A5: distal-gap sampling.** After R1, run the connectivity stage on R1's predictions of the
*training* cases. The centreline stretches it still cannot reconnect (long gaps, as in c0679, c0774 and
c0526) become sampling targets. One third of the foreground-forced patches are centred on them, and
fine-tuning runs 250 epochs.

Rationale: the residual failures are thin distal RCA/LCx gaps that no post-processing reaches (E8,
E10). This is hard-example mining on the topology error itself, not on voxels. It is unmeasured; I
pre-register it as an arm, at about 11 H100-h, and drop it if the CI includes 0.

### 2.4 Final model

As in the master. The connectivity stage is part of the deployed inference if it won on val.

## 3. Evaluation

As in the master (tF1@1.5, sealed test, FP gate, 30 val cases checked for ostia), with three
changes:
- the FP gate is computed **before** repair;
- the bridge audit (§2.2.4) is reported with every result;
- the ostium check uses ImageCAS-X's own centreline start points (`start_points` in their VTK files,
  fetched for 61 cases in 3 MB) as truth, with no hand annotation. This is already done: 116/116
  under the cross-checked procedure.

## 4. Evidence

| Claim | Evidence |
|---|---|
| Implemented 3 mm bridging: +0.010 tF1@1.5 on 17 real predictions; 5 of 12 joins are FP blobs; FP count falls 1.18 → 0.88 | [[Delta - Real bridging on 17 nnU-Net predictions gains little alone, half its 3 mm joins are false positives, and gap-centred re-inference makes it work]] |
| Re-inference + 3 mm bridging: 0.829 → 0.854 tF1@1.5 on 16 cases, no case worse, CI [0.000, 0.057] | same |
| Cheap ostium rules: 116/116 with cross-check; TotalSegmentator uses ~7 GB RSS, OOM on the shared box | [[Delta - Two cheap ostium rules find 116 of 116 true ostia, and their disagreement flags every miss]] |
| Real cut trees exist where Dice does not see them | [[Delta - A released nnU-Net cuts 3 of 8 test trees that Dice scores at 0.84-0.92]] |
| tF1 definition and its blind spot (FP blobs) | [[Delta - Dice cannot see the errors that break a coronary tree]] |
| Label repair: islands fixed, carina left alone | [[Delta - Label repair fixes islands but cannot fix a wrong carina]] |

## 5. Risks and early detection

| Risk | Signal | Response |
|---|---|---|
| Re-inference gain is an artefact of my cheaper first pass (tile step 0.75 instead of 0.5) | **pending control**: first pass at step 0.5 on the 4 cut cases (started, not finished) | if step 0.5 alone matches, drop step 2 and keep only the default overlap |
| The 256³ model cuts fewer trees, so there is little to repair | count of un-anchored components on R1 val | the stage is off by default; its cost is only CPU |
| The support rule (step 3) also blocks true joins | bridges kept vs blocked on R1 val, against the reference | fall back to the audit-only form |
| Ostium rules fail on separate LAD/LCx ostia (3 %, none in the validation sample) | rule disagreement flag | human review |
| Oracle names hide naming errors at bridges | R1 4-class predictions | repeat E10/E11 on R1 val with real names |

## 6. Comparison

**Against the master (Atlas v2).**
- Same model and same training, so no risk is added there.
- Its P1 bridging as written measured +0.01 tF1. Its FP gate, read after P1, is gamed by FP joins.
  Its false-connection audit (tube > 2 mm from reference) misses short FP-blob joins.
- v2 changes all three, and adds the one step that repaired cut trees on real output, at no GPU
  training cost.
- Its ostium check is still to be done; mine is done, on 116 trees, with a free truth source.

**Against Bridge v2 (namer on the master's mask).** Complementary. Bridge's naming bridges (4 mm) never
edit voxels, so they do not touch tF1's connectivity; my stage does, and runs first. Bridge's E2E note
measures naming on real output; mine measures connectivity. Both should run on R1 val.

## 7. Cost

- **GPU:** A5 about 11 H100-h. Re-inference adds about 2 windows per case at inference (seconds on an
  H100). TotalSegmentator on 1000 cases takes about 2 GPU-hours. Everything else is the master's.
- **CPU:** stage ≈ 1–4 min per case.
- **Human:** review of flagged ostia (≈ 2 % of trees) and of audited bridges on val.

## 8. Changes since v1

- **Kept:** the master's recipe instead of re-stating Atlas v1's.
- **Retracted:** the 0.78 → 0.91 bridging claim. It was a metric tolerance; measured, the gain is +0.01.
- **Added**, each with a new experiment on real predictions:
  - gap-centred re-inference;
  - FP gate before repair;
  - bridge audit and support rule;
  - the validated ostium procedure;
  - the A5 distal-gap sampling arm.
- **Pending:**
  - the tile-step 0.5 control;
  - re-inference on c0846 and c0951;
  - the support rule's measured effect.

---
tags: [plans, candidate, topology, post-processing, ostium, trillium]
author: Delta
round: 3
version: 3
updated: 2026-10-08
---

# Delta v3 — settle P1′ with its control, drop the support rule, and test it all on a real thick-convention 4-class model on Trillium

## 1. Decision and thesis: improve, not restart

The project lead's decisions ([[Human decisions]]) are binding:
- the thick ImageCAS mask, split into four classes, is the target, the seed and the reference;
- side branches follow the territory rule; the ramus goes to LCx;
- every case is labelled twice;
- tF1 tolerance is fixed at 1.5 mm.

All challengers have converged on the master's recipe. I have no evidenced training-side alternative,
so a different recipe would be an assertion. v3 therefore keeps the master's model and training and
does three things.

1. **Answers the Round 2 ruling's three asks** (§4):
   - the tile-step-0.5 control for P1′;
   - the support rule, measured;
   - the ostium check extended to an absent-LM case.
2. **Re-reads my own evidence under the thick convention.** Every connectivity number I have so far
   came from a model trained on the *thin* ImageCAS-X lumen. On the thick masks only about 4 % of
   centreline runs through lumens under 4 voxels across, against 65 % on the thin lumen
   ([[Delta - Two references of the same vessels agree on centrelines, not on voxels]]). So cut trees
   should be rarer, the A5 calibre trigger stays off, and the size of every repair gain is an open
   question on the decided convention.
3. **Prepares the one experiment that can settle all of it:** a real 4-class thick-convention model on
   Trillium (`trillium/delta/`, 1 × H100, ≤ 24 h). It tests P1′ against nnU-Net's default inference,
   bridging, the support rule and label repair, all by tF1 @ 1.5 mm with the binding audit and FP gate.
   Until that result is back, P1′ stays a candidate. The plan pre-commits to the decision table below.

## 2. Results this round (CPU, released binary model, thin convention)

**Tile-step-0.5 control (C1 of the ruling).** The first pass was re-run at nnU-Net's default step 0.5,
and re-inference was then applied on top of it. All comparisons are tF1 @ 1.5 mm.

| case | step 0.75 first | **step 0.5 first** | step 0.75 + P1′ + bridge | **step 0.5 + P1′ + bridge** |
|---|---|---|---|---|
| c0675 | 0.829 | **0.834** | 0.867 | **0.902** |
| c0526 | 0.850 | **0.858** | 0.851 | **0.850** |
| c0407 | 0.756 | PENDING | 0.938 | PENDING |
| c0113 | 0.523 | PENDING | 0.700 | PENDING |

- So far, nnU-Net's default overlap barely changes the first pass (+0.005 and +0.008). It does **not**
  reproduce P1′'s gain.
- P1′ on top of the default overlap still gains +0.068 on c0675, but costs −0.008 on c0526.
- That c0526 result is the first case where P1′ made something **worse**, so the v2 claim "never worse"
  no longer holds.
- c0407 and c0113 are the decisive cut cases. Their step-0.5 runs were killed twice by out-of-memory
  events on the shared machine, and are re-running.

**Support rule (ruling §4.2): it fails.** On the 6 cut and repaired cases (step 0.75, P1′ + 3 mm bridging):
- it kept all 4 false-positive joins, because each FP orphan *was* predicted again in the second look;
- it blocked 2 true joins (c0407: a 3200-voxel orphan; c0675: a 396-voxel orphan);
- it lowered c0407 from 0.938 to 0.807.

**Dropped.** The "FP" orphans that re-inference confirms are most likely vessels the *thin* reference
did not trace. This is the convention problem again: under the decided thick reference they may well
be true joins. Trillium measures this directly.

**Ostium, absent LM.** c0020 (LM absent, three trees, three true ostia): the rules applied **per tree
component** find all three, within 1.4 mm, and agree. The per-component validation
(`experiments/Delta/ostium_eval_cc.py`) on all 71 cases, including c0141 and c0196, is pending.
TotalSegmentator on more cases is still blocked by memory here (it was OOM-killed twice); on Trillium
it is the master's A1 rule anyway.

## 3. Recipe

**Unchanged from the master:**
- Atlas v2 with the Round 1–2 amendments and [[Human decisions]];
- the ResEnc 0.5 mm 256³ model, fixed window, no mirroring;
- the A1 ostium procedure with the cross-check, applied per tree component so that absent-LM cases
  work;
- the A2 raw-prediction FP gate and bridge audit.

**Changes I propose:**
1. **Remove the support rule** from P1′ (§2).
2. **P1′ is judged against nnU-Net's default inference (step 0.5), never against a cheaper first
   pass.** It is adopted only if the Trillium C2 comparison clears its CI. Otherwise nnU-Net's default
   inference stands.
3. **Two reads per case: the topology-safe way to use them.** This is the new open question.
   - **tF1 reference.** Score a prediction against *each* read and report the mean. The per-case
     inter-rater tF1 (read A against read B) is the ceiling, available on all 1000 cases.
   - **Training target.** Use both reads as separate samples, or the voxel-wise mean as a soft label.
     **Never use the voxel intersection.**
   - Why not the intersection: it is an erosion wherever the two boundaries disagree. One voxel of
     erosion cut the thin trees into +37 pieces
     ([[Delta - Dice cannot see the errors that break a coronary tree]]). On thick masks the effect is
     smaller (c0000: 0 extra pieces), but it is unmeasured on real double reads.
   - **Name disagreements** (voxels on which the two reads give different classes): set to `ignore` in
     the class loss only, never in the vessel/background loss, so the tree stays connected in the
     target.
   - Pre-registered check on the first 20 double-read cases: count the components of read A ∩ read B
     against each read alone. If the intersection adds components in > 10 % of cases, the
     intersection is banned from any use, including STAPLE-style consensus.

## 4. Evaluation

As in the master, with three additions:
- per-read tF1 and the inter-rater tF1 ceiling on all cases;
- P1′ evaluated only against step-0.5 inference;
- the Trillium decision table below.

**Decision table (pre-committed; full version in the pending note):**

| Trillium result | Decision |
|---|---|
| C2 (default inference + P1′ vs default) CI > 0, no case worse by > 0.01 | P1′ on by default |
| otherwise | P1′ dropped; nnU-Net default inference |
| bridging alone ≈ 0, or FP joins ≥ true joins | P1 bridging removed |
| label repair CI > 0 | P2 on by default |
| cut-tree rate ≤ 1/160 | connectivity stage becomes QA-only |

## 5. Evidence

| Claim | Evidence |
|---|---|
| Default overlap does not reproduce P1′'s gain on the 2 cases done; P1′ hurt one case | `regap05.jsonl` / `regap_v3.jsonl` (this round; `experiments/Delta/regap.py`, `nnunet_infer.py` step 0.5); note pending completion of c0407 and c0113 |
| The support rule keeps FP joins and blocks true ones | same, `audit` fields |
| Bridging alone +0.01; half the joins are FP (thin reference) | [[Delta - Real bridging on 17 nnU-Net predictions gains little alone, half its 3 mm joins are false positives, and gap-centred re-inference makes it work]] |
| Ostium rules 116/116 with cross-check; absent-LM case works per component | [[Delta - Two cheap ostium rules find 116 of 116 true ostia, and their disagreement flags every miss]] + c0020 result above |
| The pending decisive experiment | [[Delta - PENDING Trillium run - does gap-centred re-inference beat nnU-Net's default inference on a thick-convention 4-class model]] |

## 6. Risks

| Risk | Status |
|---|---|
| P1′ is an artefact of my cheaper first pass | Partly answered: default overlap gives +0.005 to +0.008, and P1′ still adds +0.068 on c0675. c0407 and c0113 are pending, and Trillium answers it at scale. |
| The thick convention makes all of this moot (few cuts) | This is the most likely outcome given the calibre. Trillium reports the cut-tree rate. |
| The Trillium run fails or over-runs | It is idempotent and resumable, keeps a walltime ledger, and has a deadline-aware trainer. The CPU smoke test passed end to end. |

## 7. Cost

- **GPU:** the Trillium experiment, ≤ 24 H100-h, one job. P1′ adds about 2 windows per case at inference.
- **Human:** the double-read intersection check (CPU), and review of flagged ostia.

## 8. Changes since v2

- **Dropped:** the support rule (measured to fail) and the "never worse" claim (c0526).
- **Added:**
  - the tile-step control (2 of 4 cut cases done);
  - per-component ostia for absent LM;
  - the Trillium experiment, with a pre-committed decision table;
  - topology-safe use of double reads;
  - conformance to [[Human decisions]] (thick convention; the A5 trigger is off).
- **Withdrawn:** the A5 distal-gap sampling arm, until the Trillium run shows residual cuts.

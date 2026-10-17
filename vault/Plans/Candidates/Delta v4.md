---
tags: [plans, candidate, topology, post-processing, trillium, sealed-test]
author: Delta
round: 4
version: 4
updated: 2026-10-08
---

# Delta v4 — the master's recipe, with a Trillium run fixed to A13, a proposed sealed split, and bridging re-read on the thick reference

## 1. Decision and thesis: improve, not restart

The Round 3 ruling adopted my procedural contributions:
- A1: ostium cross-check per tree component;
- A2: the raw FP gate and the bridge audit;
- never using the voxel intersection of the two reads.

What is left to settle is a single question: does **gap-centred re-inference (P1′)** earn a place in
the master's inference? The ruling says the pending Trillium run "is the whole case for P1′". v4
therefore does four things:
1. fixes that run to A13;
2. answers C4 (re-reading bridging against the thick reference);
3. completes the per-component ostium validation;
4. proposes the one missing piece of hygiene the master needs for any of this: a published, fixed
   split of the ImageCAS-X test set into the sealed 80 and the open 80.

## 2. Changes for A13 (Trillium run, `trillium/delta/`)

1. **Sealed test.** The run stages, predicts and scores only the **80 open** ImageCAS-X test cases.
   Sealed cases are excluded twice: at data preparation (never staged) and again in evaluation.
   Summaries state the source of the sealed list and the number excluded.
2. **Sealed list.** No master list exists: Atlas v3 says "80 sealed" but names none. Delta therefore
   publishes `trillium/delta/icx_test_split.json`:
   - rank the 160 ImageCAS-X test cases by sha256("asclepius-sealed-v1:" + case id);
   - the first 80 are sealed, the last 80 are open.

   The split is deterministic and reproducible, and was chosen without looking at any outcome.
   **Proposal: the master adopts it as its sealed ImageCAS-X 80.** Any list the master publishes later
   (`sealed_test.txt|json` in Atlas's results or experiment folder) takes precedence automatically.

   Disclosure: some of my CPU experiments touched cases this split now seals, for example c0675,
   c0526 and c0111. That happened with the released ImageCAS-X model, against the ImageCAS-X
   reference, never against team reads. The master's sealed scoring uses team reads, so nothing has
   been tuned on the sealed test's labels.
3. **Model (defects (i) and (iii)).** `./delta`, with no arguments, decides for itself:

   | Atlas's run state | What `./delta` does |
   |---|---|
   | finished (`$SCRATCH/atlas/DONE` or a results manifest, plus a checkpoint) | **inference only on Atlas's master-configuration checkpoint** (256³ patch, 0.5 mm iso), ≤ 10 h |
   | queued or running (`atlas-r0r1`) | wait; nothing is submitted, because A13 says Atlas goes first |
   | never run | fall back to its own ResEnc-L training, ≤ 24 h |

   Inference-only mode removes the patch-size defect and saves about 20 H100-h.
4. **Tested on CPU**, in both case layouts:
   - dry runs in all three modes, including a fake squeue for the "Atlas queued" state;
   - shellcheck clean;
   - end-to-end smoke runs in own mode and in Atlas-checkpoint mode. The smoke tests confirm that
     80 sealed cases are excluded and that the summary reports the mode and the sealed source.
   - Workers killed by the OS now cost only a serial re-score at the end, not the whole run.

## 3. New evidence this round

**C4 — bridging re-read against the thick reference**
([[Delta - Against the thick reference, bridging still joins false positives 6 times in 13]]):
- Of the 5 joins that were false against the thin reference, 2 become true under the thick mask.
  1 thin-true join becomes false.
- Under the binding thick reference, **6 of 13 joins (46 %) still attach a piece that touches no
  reference vessel**.
- Raw FP components are 1.22 per case (thick) against 1.11 (thin).
- So my Round 3 hypothesis that the "FP" orphans were untraced vessels is only partly true. Bridging
  alone stays not expected to pass, and the A2 audit and pre-repair gate are needed on the decided
  reference too.

**Ostium per component, completed** (ruling §5; `experiments/Delta/ostium_eval_cc.py`):
- 62 cases with ImageCAS-X centreline truth and **130 true ostia**, including the 3 absent-LM cases;
- **127 ostia**: both rules agree and both are right, within 5 mm;
- **3 trees flagged** (rules disagree by > 5 mm), and in every one of them one rule was right;
- **0 ostia** where the rules agreed and were wrong.

So the A1 cross-checked procedure got every ostium right or flagged it. The 9 other cached CTs had no
centreline file fetched, so they have no truth and were not scored.

**P1′ on uncut cases at step 0.5** (ruling §5): not run on CPU. Each step-0.5 case costs about
20 CPU-minutes and was repeatedly OOM-killed on the shared machine. At step 0.75, P1′ changed every
uncut case by ≤ 0.001 ([[Delta - The tile-step-0.5 control - nnU-Net's default overlap does not reproduce re-inference's repair, and the support rule fails]]).
The Trillium run measures it on all 80 open cases at step 0.5, and its rule "no case worse by > 0.01"
covers the uncut cases.

## 4. Recipe

**Unchanged from the master** (Atlas v3 + amendments + [[Human decisions]]).

**Proposed:**
1. **Adopt `icx_test_split.json` as the sealed ImageCAS-X 80** (or publish a list before any
   Trillium job runs).
2. **P1′** (gap-centred re-inference + ≤ 3 mm bridging, no support rule) becomes a switchable step,
   decided **only** by the Trillium run's C2 on the open 80: CI > 0 and no case worse by > 0.01.
   Otherwise nnU-Net's default inference stands.
3. **P1** (bridging alone) is removed if Trillium's C4 shows FP joins ≥ true joins against the thick
   reference. CPU evidence (6 of 13 false) points that way.
4. Two reads per case: as ruled (mean-against-reads tF1; no intersection).

## 5. Evaluation

As in the master.

The Trillium run's decision table is pre-committed, on the **open 80 only**: see
[[Delta - PENDING Trillium run - does gap-centred re-inference beat nnU-Net's default inference on a thick-convention 4-class model]].

## 6. Evidence

| Claim | Evidence |
|---|---|
| Thick re-read: 6/13 joins still false; raw FP 1.22 per case | [[Delta - Against the thick reference, bridging still joins false positives 6 times in 13]] |
| P1′ is not an overlap artefact on the 4 cut cases (+0.103 vs +0.003); support rule fails | [[Delta - The tile-step-0.5 control - nnU-Net's default overlap does not reproduce re-inference's repair, and the support rule fails]] |
| Ostium per component: 127/130 agreed and right, 3 flagged with one rule right, 0 silent errors (62 cases, incl. 3 absent-LM) | §3 above (`ostcc.jsonl`, `ostcc_lm.jsonl`); [[Delta - Two cheap ostium rules find 116 of 116 true ostia, and their disagreement flags every miss]] |
| Sealed split | `trillium/delta/icx_test_split.json` |

## 7. Risks

| Risk | Response |
|---|---|
| The master picks a different sealed 80 *after* Delta's run has scored cases from it | Mitigation: the master adopts the published split, or publishes its list before the lead runs `./delta`, which then reads it automatically |
| Atlas's checkpoint is mid-training (job died) | `./delta` uses final, then latest, then best; the summary records which |
| P1′ gains vanish under the 256³ patch | That is the answer the run gives; P1′ is then dropped |

## 8. Cost

- **GPU:** ≤ 10 H100-h in inference-only mode; ≤ 24 h only if Atlas never runs.
- **Human:** adopting or publishing the sealed list (minutes).

## 9. Changes since v3

- **A13 fixes:** only the open 80 are evaluated; inference-only on Atlas's checkpoint; waits while
  Atlas runs; worker-failure resilience.
- **Proposed:** the sealed split, `icx_test_split.json`.
- **C4 answered:** under the thick reference, bridging FP joins stay at 6 of 13.
- **Completed:** the per-component ostium run (127/130 right, 3/130 flagged, 0 silent errors).

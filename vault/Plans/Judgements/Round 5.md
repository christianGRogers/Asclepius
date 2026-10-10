---
tags: [plans, judgement]
round: 5
updated: 2026-10-10
---

# Round 5 ruling

This is the first round with real GPU evidence. I checked the advocates' notes against the raw files in `trillium-results/round5/{atlas,bridge,crucible}/results/SUMMARY.md`, and every headline number matches:

- **Atlas:** 174.9 s/epoch, 55.6 GiB, 412 epochs, tF1 0.846, FP 1.488 per case, swaps 0.009, 17 flagged cuts.
- **Bridge:** R − D −0.0128 [−0.0251, −0.0020], H − D −0.0133, O − D +0.0097.
- **Crucible:** both − single +0.030 [+0.010, +0.050]; a11 − both −0.008 [−0.018, +0.003] against the truth and −0.035 [−0.046, −0.023] against the reads.

One small discrepancy: Bridge's arm D scores 0.847 where Atlas reports 0.846. The two use slightly different provisional ostium rules, so the difference is immaterial.

## 1. Master plan: **Atlas v5**, adopted with these binding changes

The master recipe passed R0 by a wide margin: 175 s/epoch against an acceptance of 306, and 55.6 GiB peak against 75. Its first real 4-class model names well: swap rate 0.9 %, centreline naming accuracy 0.991, and both naming competitors lose to it. No challenger proposes a rival recipe. Atlas v5 keeps the title.

### Revised amendments

**A1, the ostium rule (revised; Delta's implementation adopted).** The rule of record is the **reference centreline voxel nearest the TotalSegmentator aorta, per tree component and per side**. `thick` and `pool_thick` cross-check it, and any disagreement greater than 5 mm flags the tree. This is now implemented in `src/segtrain/tf1.py`. I read `find_ostia`, and it matches the note: any-degree centreline voxel, a per-side split, a flag set on disagreement or when the tree does not touch the aorta, and results marked `provisional` when no aorta mask is available. Three conditions bind:

- **A1a.** Any tF1 computed without an aorta mask is reported but decides nothing. This sharpens A9.
- **A1b.** Flagged trees are reported separately. They are excluded from decisive aggregates until a human has reviewed them. Paired comparisons may include them, since every arm shares the same reference ostia. Delta has not yet counted the flag rate under the revised rule; the endpoint version flagged 38 of 160 trees. That count is due before wave 1, because flags cost reviewer time.
- **A1c (governance).** The decisive metric's code is frozen by version hash before any decision table is read. A future change needs an evidence note and regression tests, as Delta supplied this time, and is announced in the round in which it is made. Delta's change is accepted after the fact on that basis.

**A2, post-processing (narrowed).** With correct ostia, connectivity costs only about **0.004** macro tF1 per case on the master model, and more than half of that sits in 2 cases. P1 bridging was never expected to pass, and is now formally **removed** from the candidate list. P1′ survives only if Delta's pending run passes the stricter table it pre-registered before seeing any result: mean at least +0.002, CI above 0, no case worse by more than 0.01, the gain concentrated in gap cases, and fewer FP joins than true joins. Otherwise connectivity work becomes a QA report (bridge audit plus gap sites). P2 label repair stays a candidate.

**A4, the absent-LM guard (from Bridge v5).** A label or proxy with no LM is never excluded on the `lm` or `ostium` triggers. It is marked for review instead. Evidence: 2 of the 3 swaps in the R − D comparison were absent-LM cases, and 11 of 800 ImageCAS-X cases have no LM. The same guard applies to the A11 third-read triggers.

**A7, naming (settled).** R and H are **not adopted**, because both CIs lie below 0. Bridge's own pre-registered closure rule also fires (O − D = 0.0097, under 0.01). R and H are retired as shipping candidates. The namer keeps three QA roles: A4, the A11 decision extractor, and a new report-only structural audit of D (Bridge v5 §2.2).

**A11′, training on two reads (Crucible v7; replaces the voxel rule of A11).** Each read is a separate training sample with **no name-conflict `ignore`**. Each sample keeps its own read's labels. The case-level third-read rule is unchanged, including the ramus-only exemption and the A4 guard above. Reasoning is in §3 C3.

**A11 test (re-specified).** It still runs only if A12a detects annotator habits. It compares A11′ against agree-or-ignore, which statistically tied with A11′ on the GPU. Its decisive read is **tF1 against the reads** (A10), with the carina anchor reported alongside. The Round 4 premise for judging it on the anchor alone ("A10 cannot choose a fusion") has been falsified at network level.

**A13: unchanged.** Inference-only reuse of the master's checkpoint has worked: Bridge's comparison cost a few GPU-hours, not about 20.

### New amendments

**A15, the FP gate.** The gate stays at ≤ 1 per case, read on the raw prediction. It is not relaxed, but it is now known to be **unachieved by any model measured**: 1.49 for the master, 1.22 for the released ImageCAS-X model. Its threshold has no baseline behind it. It is an *acceptance* criterion for the final model, not a gate on further training. The next lever is chosen by the FP census (A16), as follows:

- **Mostly low-confidence blobs.** A single global vessel-probability threshold, chosen on val and frozen, counts as part of the model's output and therefore as "raw". It is adopted only if tF1 on val is not worse (CI) and the FP count falls. A component-level deletion filter is **not** raw. It would breach the "never delete ≥ 100 voxels" rule, and it may be proposed only with census evidence that it removes no reference vessel.
- **Mostly real vessel outside the ImageCAS mask** (inside ImageCAS-X labels). This is a question for the humans (§6), not for the tournament. Under D0 such vessel counts as false by definition, and no team read can ever contain it, because edits are confined to the mask.

**A16, the next Trillium run (Atlas run 2), amended.**

- **Phase A** (census plus re-score, at most 1.5 h, no training) is approved, with one change. The re-score must use the **A1 rule of record**: TotalSegmentator aortas for the 80 val CTs (about 40 s per case on CPU, or on the node) and `segtrain.tf1` at the frozen hash. Results are reported with flagged trees separated. `pool_thick` and the ImageCAS-X start points serve as validation columns only.
- **Phase B** (the A2 window ablation, 412 epochs, paired against run 1) is approved. This is a planned ablation, the window is the pre-registered first suspect for the FP failure, and run 1 serves as its control, so no new control is needed. Atlas's decision rule is accepted: paired tF1 under A1 with the CI excluding 0; if tF1 ties, the window with fewer FP components wins.
- **R1 at full length (48.6 h) does not start yet.** It starts after run 2, with the winning window. Atlas's pre-registered epoch rule is accepted: if R1 and the 412-epoch model differ by less than 0.01 tF1 on val, fine-tunes stay at 250 epochs and the final model may use 500. Starting R1 now would spend about 49 H100-h on a window that run 2 may reject. Without team reads, a full-length proxy model has two uses: initialising fine-tunes, and answering the epoch question. Neither is urgent before the window is settled.
- **Deprioritised: ablation A4 (Skeleton Recall).** Its documented effect is more components (Round 1 note V), which works against the failing FP gate. Its target, connectivity, has about 0.004 of headroom left. It runs only if the census or R1 shows recall-type distal losses. A3 (rotation) remains a pure accuracy question and comes after R1.

## 2. Scorecards

Scores are out of 5.

### Atlas v5 (winner, amended)

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4.5 | Applied its own table row by row. Diagnosed the cut-tree flags correctly and promoted nothing on a flagged metric. Its argument for running the census before choosing a lever is right. |
| (b) Evidence | 4 | The raw files match. Two weaknesses. The "better of two provisional rules" tF1 (0.871) picks the better rule per case, which is an optimistic selection and not a measurement; Atlas labels it as such. Two cases (c0717, c0560) were called real RCA misses, and Delta's 69-point check shows they are ostium artefacts. That error runs in the conservative direction. |
| (c) Fit | 4.5 | R0 settles feasibility: R1 needs three chained 23:50 jobs. The recipe is implemented in `src/segtrain`. |
| (d) Risk/cost | 4 | 21.8 H100-h spent. The FP gate is the open risk. |

**Verdict:** keeps the title.

### Delta v5

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 5 | Located the round's main measurement error, which was in the metric, not the model. Narrowed its own thesis to fit: P1′ now has at most 0.004 to win. Tightened its pending decision table **before** its result, and predicted in advance that P1′ would fail. |
| (b) Evidence | 4.5 | 69 RCA truth points; 13 of 17 cuts shown to be artefacts. Ostium validation on the thick reference: 160 ostia, 139 right, 15 of 21 misses flagged, 6 silent misses of which 4 are only 5.0–5.3 mm off. The finding that the cheap rules fail silently on 8 % of trees reverses its own Round 4 result (0 silent errors, which was measured on the thin lumen). One caveat: the 0.0043 residual counts the 11 RCAs with no truth point as correct, so it is optimistic. |
| (c) Fit | 4.5 | Its metric fix is in the master's code. |
| (d) Risk/cost | 5 | No new GPU. |

**Verdict:** its A1 revision binds. Its pending run is still the case for P1′, and Delta itself expects that case to fail.

### Crucible v7

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4.5 | Applied both of its pre-registered rows and reported openly that they point in different directions. Withdrew its own Round 4 CPU claim once the GPU run falsified it. Flags the a11-vs-agree gap as unexplained rather than inventing a mechanism. |
| (b) Evidence | 3.5 | A real network with equal steps across six arms, and the CIs are sound. Limits: simulated reads in a deliberately strong opposite-habit regime, one seed, a 96 × 160 × 160 patch, 200 cases. The LM per-class figures come from `results.json` aggregates, with no per-case inspection. |
| (c) Fit | 5 | A11′ removes machinery (the `ignore` label in the read datasets) and costs nothing. |
| (d) Risk/cost | 4.5 | If real habits are weak, the choice does not matter; A11′ was never worse in any measured regime. |

**Verdict:** A11′ is adopted.

### Bridge v5

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4.5 | Applied A7 and its own closure rule, and withdrew its thesis without hedging. Its narrowed role is correct: a structural namer is right for *detecting* decision errors and wrong for *overwriting* a network that names at 0.991. |
| (b) Evidence | 4 | The raw files match. Its failure analysis (3 swaps, all namer errors, 2 of them absent-LM) is checked on the thick masks. |
| (c) Fit | 4.5 | The QA roles cost nothing. One problem: the "gated subtree renaming" is to be tested "on R1 data not seen in Round 5", but **R1's validation set is the same 80 cases that motivated it**. As written, that test is not out-of-sample (see §5). |
| (d) Risk/cost | 5 | No GPU. |

**Verdict:** naming goes to the network. Bridge's tools remain as QA.

## 3. Rulings on the questions put

### C1. Were the pre-registered tables applied honestly? **Yes, all four.**

- **Atlas:** every row applied as written. The swap/R row was handed to Bridge's measurement, as agreed.
- **Bridge:** A7 applied. Its own "O − D < 0.01" rule was applied against its interest.
- **Crucible:** the narrowing row (a11 < both against the truth, CI excluding 0) does *not* fire, and Crucible says so. Its recommendation rests on the general row (both beats single and is no worse than agree or union) and on the A10 score, and it presents both readings.
- **Delta:** its run is pending. Its revised table is stricter than v4's and was fixed before the result.

One process note. Crucible's general row was written before `a11` was added as an arm, so it never says what to do when both beats a11 against the reads but not against the truth. The tie is resolved by the judge (C3), not by the table.

### C2. The FP-gate failure

The failure is accepted as real and broad: 1.49 per case (CI 1.21–1.78); 38 of 80 cases have two or more FP components; it barely tracks case tF1 (ρ −0.16); it is the same in cut and uncut cases. The master changes on three points:

1. **Recipe:** no change yet.
2. **Post-processing:** A2 holds. Under the raw-gate rule no bridging or repair step can pass the gate, and none should be allowed to.
3. **The gate's achievability is unknown.** Its threshold was set without a baseline. The weak correlation with ImageCAS-X vessel outside the mask (ρ 0.27, p 0.017) suggests some FPs may be real vessels the reference omits. That is a hypothesis. The census tests it, and A15 routes each outcome.

### C3. A11′

Accepted. The Round 3 hybrid (the name-conflict `ignore`) was my own synthesis and was never measured. The first network-level measurement finds two things:

- **It does not help against the truth:** −0.008, CI [−0.018, +0.003].
- **It hurts on the master's decisive score:** −0.035 against the reads, CI excluding 0.

The proposed mechanism is coherent, though only partly supported. The network fills the ignored carina band with LM, and so adopts one annotator's LM-end habit (LM against read B: 0.505 for a11, 0.785 for both). The agree arm ignores the same voxels without this collapse, which keeps the mechanism partly unexplained, as Crucible says.

The two pre-registered tests disagree. I therefore decide on two principles:

- with no evidence for a piece of machinery, prefer the simpler rule;
- the decisive metric under D0 is the score against the reads.

Both favour A11′. Two further results support it: both-as-samples beat a single read by +0.030 against the truth, so the second read is worth training on, not only for evaluation; and the oracle arm did not beat two noisy reads (one seed). The evidence is simulated, in a habit regime, from one seed. A11′ is therefore a default, not a closed question, and the conditional A11 test re-examines it on real reads.

### C4. The "cut trees" and the corrected tF1

The diagnosis is **accepted**. Two independent analyses agree that most flagged cuts were misplaced reference ostia: Atlas found 11 of 17 using 13 RCA truth points, and Delta found 13 of 17 using 69. About 4 of the 80 cases are real partial mid-tree cuts, and 3 of those are on the LCx.

**No corrected number is accepted yet.** 0.846 is a lower bound and 0.895 an upper bound (Delta, scoring the artefact classes at their clDice). The 0.87–0.90 range is an estimate built on optimistic selection. The decisive figure is whatever the A1 re-score in run 2 Phase A produces.

**Bridge's paired differences are unaffected**, because every arm shares the same reference ostia. The A7 verdict stands.

### C5. Bridge's narrowed role

Accepted, in the form described under A7 above.

### C6. The next Trillium runs

The next run is Atlas run 2, with Phase A amended to use the A1 rule; it is approved. R1 at full length follows run 2. Delta's run finishes as it is. **No other GPU run is justified now.** Specifically:

- naming is settled;
- the fusion question waits on real reads (wave 1 / A12);
- the ablations follow R1 (A3), are deprioritised (A4), or have not been triggered (A1 spacing).

## 4. Contested facts

1. **Can a score against the reads choose a fusion rule?** Round 4 accepted Crucible's CPU claim that it could not. Its GPU run falsifies that claim (a11 − both −0.035 against the reads). I accept the network-level result over the plurality proxy: the proxy assumed convergence to the label mode, which a finite network filling `ignore` voxels does not do. The Round 4 anchor-only judging rule for the A11 test is withdrawn (A11 test above).
2. **Are c0717 and c0560 real RCA misses?** Atlas says probably; Delta shows the roots are 36 mm and 11 mm from the expert ostium. **Delta is accepted**: it has truth points for these cases and Atlas did not.
3. **Are the cheap ostium rules safe?** On the thin lumen there were 0 silent errors in 130 ostia (Round 4). On the thick reference there were 11 silent errors in 133. **Both results stand.** The thick reference is the binding one, and its endpoints often do not sit at the ostium: the mask barely tapers, and the skeleton passes the ostium at a degree-2 point. That is why the aorta rule is mandatory (A1).

## 5. What would change the ruling

**Atlas, to keep the title:**
- Run run 2 as amended.
- Report tF1 under A1 (flagged trees separated) and the FP census.
- Choose the window by its own rule.
- Then run R1 at full length.

A1-scored tF1 well below 0.87, or a census showing that FPs are confident, model-intrinsic hallucinations, would reopen the recipe: an FP-aware loss or a different context. Any advocate with an evidenced fix could then compete.

**Bridge:**
- Run the gated subtree renaming only on data never used in Round 5: the A14 **open 80** test cases (inference on R1's checkpoint), not R1's validation set.
- Report the structural-audit flag rate.

**Crucible:**
- Refit the habit model on wave-1 reads (A12a).
- If habits are absent, A11′ versus agree is moot and its work on fusion is done.
- A second seed of the a11/agree/both arms would resolve the unexplained a11-vs-agree gap cheaply, at about 4 h for three arms at 23 s/epoch. This is optional.

**Delta:**
- Report its pending run against the pre-stated table, primary read with aorta-rule roots where the predictions survive.
- Report the flag rate of the revised A1 rule on its 160 ostia (A1b).

## 6. Decisions that belong to humans

1. **The FP gate's reference** (only if the census shows that most FP components are real vessel inside ImageCAS-X but outside the ImageCAS mask). Should real vessels the reference cannot contain count against acceptance? D0 makes the mask the reference, but the gate's purpose (no hallucinated vessel) may call for a different count. This is for the clinical lead.
2. **Reviewer time for flagged ostia.** Under A1b, flagged trees need a human look before sealed scoring. The endpoint version of the rule flagged about 24 % of trees, and the revised rule's rate is due. The labelling lead should approve the budget.
3. Carried over: the A10 margin (0.02), the third-read budget, and pairing reads across habit groups if A12a finds habits.

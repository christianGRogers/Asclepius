---
tags: [plans/experiment, trillium, result, a1, a2-window, fp-census, a15, round8]
author: Atlas
round: 8
updated: 2026-10-11
status: result
---

# Atlas - Trillium run 2 results, the A1 re-score, the window ablation and what the confident false positives are

Run 2 (`trillium/atlas2`, job 1066679, 22.5 h on one H100) was pre-registered in
[[Atlas - Pending Trillium run 2, A1 re-score, FP census and the window ablation]]. Raw results:
`trillium-results/round6/atlas2/results/`. The CPU follow-up here is `experiments/Atlas/r8_fp_anatomy.py` →
`r8_fp_anatomy.jsonl`. It reads only run 1's 80 val segmentations, the ImageCAS masks, the 116 TotalSegmentator
aortas and the 11 CTs cached locally.

## Answers

1. **Run 1 under the A1 ostium of record.** Decisive macro tF1 is **0.896**: LM 0.966, LAD 0.901, LCx 0.846,
   RCA 0.883 (80 cases, 272 unflagged trees; 44 of 316 trees flagged).
   - That is inside the judge's bounds (0.846–0.895), at the top. It is above the 0.87 that would have reopened the
     recipe (Round 5 §5).
   - My round-5 estimate (0.87–0.90) held. The RCA, which looked weakest under the provisional ostium, is now
     second weakest; the **LCx is the weakest class**.
   - Ostium validation against the ImageCAS-X start points: 160 ostia, median 2.0 mm, 143 within 5 mm, 32 flagged,
     5 silent misses.
2. **The window. By the letter of the rule, "default" wins. The truncation weakens the comparison but does not
   reverse it, because every handicap falls on the winner.**
   - The default-window arm (B) ran **368 of 412 epochs**. Phase A took 4.0 h, not the 1 h I forecast: TotalSegmentator
     took 112 s per case on the node, not ~15 s.
   - B's poly schedule was therefore cut at an LR of 1.3e-3, not annealed to 0.
   - Paired B − run 1 (decisive): tF1 −0.0027 [−0.0118, +0.0062], a tie; FP −0.19 [−0.48, +0.10] per case.
   - A truncated, un-annealed arm is handicapped. The comparison is weakened but still decision-grade (§1).
3. **The FP census verdict stands (A15), and the false positives are identified.** 94 of 119 FP components (79 %)
   are `confident_other`.
   - **What they are:** tubular, vessel-calibre structures running *alongside* the arterial tree, not beyond its
     ends. They sit in epicardial fat, and their core enhances to about **half** the neighbouring artery's lumen.
   - That is the signature of **cardiac veins** (the anterior interventricular vein beside the LAD, the great
     cardiac vein beside the LCx in the AV groove, the small cardiac vein beside the RCA). A minority look like
     unannotated small arterial branches.
   - A global probability threshold cannot remove them: they are confident (p90 ≥ 0.94).
   - The heart-and-aorta ROI filter (A20 / F3) cannot remove them either: 91 of 94 lie within 25 mm of the coronary
     tree itself. A20's precondition (≥ 25 % beyond 25 mm) fails.
   - (§3)
4. **Recipe change and next run (proposal only, §4).**
   - The recipe change is an **FP-aware loss**: a distance-gated focal background term that up-weights
     confidently-predicted voxels more than 1.5 mm from any labelled vessel.
   - Why a loss change: these voxels are ~0.8 % of the predicted foreground, so DiceCE barely penalises them, while
     the gate counts components.
   - It must be tested before R1. **Proposed run 3:** two warm 200-epoch fine-tunes from B's checkpoint with the
     A17a trainer, plain vs FP-aware, paired; ≤ 21 h.
   - R1 at full length then runs with the default window, and with the FP term if run 3 adopts it.

## 1. The window decision, applied honestly

**The rule, as pre-registered.**
- Paired decisive tF1 decides when its CI excludes 0.
- On a tie, the window with fewer FP components per case wins.
- On equal FP, the fixed window stays.
- R1 then runs with the winner.
- The note also said: *"If the node is slower than run 1's, the trainer stops at the deadline … and the report flags
  the pairing as weakened."* It did not say that a weakened pairing voids the rule.

**What happened.**

| | run 1 (fixed [−300, 1300]) | B (default [−169, 719]) | B − run 1 (paired, 80) |
|---|---|---|---|
| epochs | 412, poly annealed to 0 | **368**, poly stopped at LR 1.3e-3 | |
| decisive macro tF1 | 0.896 | 0.893 | −0.0027 [−0.0118, +0.0062] |
| LM / LAD / LCx / RCA (unflagged trees) | 0.966 / 0.901 / 0.846 / 0.883 | 0.966 / 0.899 / 0.828 / 0.883 | LCx −0.018 [−0.043, +0.005]; others −0.000 to −0.001 |
| flagged trees, mean change | | | LM −0.26 (n 4), LAD −0.12 (8), LCx −0.10 (8), RCA −0.01 (24) |
| FP components per case | 1.49 | 1.30 | −0.19 [−0.48, +0.10]; fewer in 31 cases, more in 19 |
| `confident_other` FP components | 94 | 78 | |

**Does the truncation invalidate the comparison by my own rule? No. It weakens it in one known direction.**
- B lost 11 % of its epochs and, more importantly, the low-LR tail of the poly schedule. That tail is where nnU-Net
  refines thin branches and cleans up isolated predictions.
- Both handicaps work **against B**, on tF1 and on stray components alike.
- A comparison biased against the arm that won still supports that arm. Under the rule's letter, B ties on tF1 and
  has fewer FP components, so **default wins**.
- What the truncation does take away is any claim about the *size* of the effects. "Default is no worse on tF1"
  survives; "default removes 0.19 FP components per case" does not, because the CI crosses 0 and the truncated arm
  is not the arm R1 would train.

**Two signals I do not explain away.**
- **The LCx (−0.018, CI to −0.043).** The default window clips above 719 HU, where calcified plaque sits. The LCx in
  the AV groove is also where B's un-annealed head would be weakest. The two causes cannot be separated here.
- **The flagged trees are much worse in B.** These are trees whose ostium rules disagree, often unusual anatomy.
  They are out of the decisive aggregate (A1b), but they go to human review and will be scored once reviewed.

**Decision.** R1 at full length uses the **default window**, per the rule. Two guards, fixed now, before R1 exists:
- **R1-default must not be worse than run 1 on the decisive tF1** (paired on the same 80 val cases; CI lower bound
  > −0.01). R1 has 1000 epochs against run 1's 412, so failing that would be a red flag on the window. The waves would
  then revert to the fixed window. MDE at n = 80: 0.010–0.022 (A19).
- **The LCx and the flagged trees are reported separately** in R1's val. LCx decisive tF1 below 0.83 (run 1 0.846,
  minus run 1's paired-noise CI half-width) triggers a check of calcified LCx cases before any wave uses R1.

## 2. Why Phase A took four hours

| Stage | Forecast | Measured |
|---|---|---|
| TotalSegmentator aortas, 116 cases, GPU | ~30 min | **3.72 h** (112 s per case, median) |
| Open-36 prediction | ~30 min | 0.29 h |
| Phase B preprocessing (overlapped) | ~40 min | done within Phase A |

TotalSegmentator's time is dominated by resampling the full 512 × 512 × 275 CT to 3 mm and back on two threads, not
by the network. Any future job that needs aortas must budget ~2 min per case, crop to the tree first (as `src/segtrain`'s
batch aorta producer already does), or compute the aortas before the job. A deadline-aware job should also set the epoch count from the
time actually left before training starts, so that the poly schedule completes (run 2's job only warned).

## 3. What the `confident_other` false positives are

**Population.**
- 94 components in 51 of the 80 cases (1.8 per affected case).
- Predicted class: RCA 38, LCx 31, LAD 25.
- All are ≥ 100 voxels, touch no ImageCAS-mask voxel, have p90 ≥ 0.94, and overlap no ImageCAS-X vessel.

| Property | 10th | 25th | **median** | 75th | 90th percentile |
|---|---|---|---|---|---|
| volume (mm³) | 8 | 20 | **41** | 96 | 174 |
| length, ±2 SD along the main axis (mm) | 3.8 | 5.1 | **7.7** | 13.9 | 24.0 |
| elongation (√ of the first two PCA eigenvalues' ratio) | 1.4 | 2.0 | **2.5** | 4.2 | 5.7 |
| inscribed radius (mm) | 0.9 | 1.1 | **1.3** | 1.5 | 1.7 |
| distance to the ImageCAS mask (mm) | 1.3 | 1.9 | **3.4** | 7.0 | 13.8 |
| distance to the predicted tree (mm) | 1.4 | 1.8 | **3.2** | 7.9 | 12.7 |
| distance to the nearest *tip* of the mask's centreline (mm) | 4.6 | 7.0 | **13.6** | 21.2 | 25.6 |
| radius of the mask vessel nearby (mm) | 1.5 | 1.6 | **1.8** | 2.1 | 2.5 |

**Where they are.**
- **They are alongside the tree, not beyond it.** 61 of 94 lie within 5 mm of the mask, but only 18 lie within 6 mm
  of one of its centreline tips. They are not distal continuations the annotator stopped short of, and not a
  truncation effect.
- **They are vessel-sized and tubular.** Inscribed radius is about 1.3 mm, against 1.8 mm for the artery beside
  them; 39 of 94 have elongation > 3; lengths reach 24–36 mm.
- **They are on the heart, not outside it.** 91 of 94 lie within 25 mm of the coronary tree; 48 lie within 25 mm of
  the aorta.

**Enhancement**, on the 21 components whose CT is cached locally (11 cases):

| | median |
|---|---|
| component core HU | **135** |
| lumen core HU of the artery nearby (mask voxels ≥ 1 mm inside) | **251** |
| core / nearby lumen | **0.45** (IQR 0.32–0.76); 15 of 21 below 0.75 |
| ring 1–4 voxels around the component | 16 of 21 negative HU, i.e. epicardial fat |

**Reading.**
- Vessel-calibre tubes in epicardial fat, running a few millimetres from a coronary artery and enhancing to half its
  lumen in an arterial-phase CT, are **cardiac veins**:
  - the anterior interventricular vein accompanies the LAD;
  - the great cardiac vein and coronary sinus run with the LCx in the AV groove;
  - the small cardiac vein runs with the RCA.
- The 6 of 21 enhancing like the artery (ratio ≥ 0.75) are more likely **unannotated small arterial branches**,
  whose origin the model did not connect (a side branch whose proximal millimetres are missed).
- Neither kind is in the reference. ImageCAS-X does not trace them either: `icx_frac` is 0 for every one, by the
  category's definition.

**Why the master recipe produces them.**
- These structures sit inside nearly every 256³ training patch, already labelled background, so the network sees
  them constantly. It predicts them anyway because the objective barely notices them.
- At 1.5 components × ~41 mm³ per case, they are about 0.8 % of the predicted foreground volume. DiceCE spends
  almost nothing on them, while the gate counts each as one whole failure.
- The window helps a little (94 → 78 `confident_other`), as more contrast resolution between ~135 and ~250 HU should.
  It does not change the mechanism.

**What does not remove them.**
- **A global threshold:** they are confident. FP falls only from 1.49 to 1.27 at t = 0.8 (tF1 −0.002); higher t
  costs tF1 (−0.015 at 0.9) for no further gain.
- **The A20 ROI filter:** they are on the heart.
- **A component-deletion filter:** not raw, so it cannot pass the gate (A15). It would also have to separate them
  from the ≈ 0.8 true-but-disconnected tree fragments per case.

## 4. The recipe change and the next run (proposal; not built)

**The change: an FP-aware loss**, added to nnU-Net's DiceCE on the full-resolution output:

L = L_DiceCE + λ · mean over B of [ −p_fg(v)^γ · log p_bg(v) ], where B = background voxels farther than 1.5 mm from
any labelled (or `ignore`) voxel.

- The band is a 3-voxel max-pool dilation of the label at 0.5 mm, computed on the GPU.
- p_fg = 1 − p_bg, and the weight is detached.
- Defaults: λ = 1, γ = 2.
- It is focal loss's hard-negative weighting (Lin et al., ICCV 2017), restricted to voxels away from the annotated
  tree. That restriction leaves the tree's boundary, where reads disagree about calibre, to DiceCE.
- It is related to instance-aware losses that penalise false-positive objects per instance rather than per voxel
  (Kofler et al., *blob loss*, arXiv 2205.08209).
- It needs no instance labels and no connected components per iteration.
- **Risk.** If some of these structures are real unannotated branches, the term teaches the model to suppress them.
  ~~Under D0 and D7 the mask is the reference, so that is the intended behaviour.~~ **Corrected (Round 8,
  A24.4):** D7 lets readers add a missing vessel segment (and remove a vein) as a noted major error, so a few real
  branches may enter team reads; the term is re-checked on team reads before the waves rely on it.

**Run 3 (proposed): `atlas3`, the FP-loss pilot.**
- Same contract as before; ≤ 21 h on one H100.
- **Source.** B's `checkpoint_final.pth` (default window, the window R1 will use; the A17a trainer refuses a source
  with another normalisation, so run 1 cannot be the source).
- **Arms.** Two warm fine-tunes, 200 epochs each, A17a trainer (peak 1e-2, 2,500-iteration warm-up), same data,
  split and seed:
  - **F0:** plain;
  - **F1:** FP-aware loss.
  - Time: 2 × 200 × 176 s = 19.6 h, plus 1 h for validation and scoring with the stored aortas.
- **Decision table**, paired F1 − F0 on the 80 val cases, decisive tF1 (A1, flagged apart):
  - **adopt** the FP term for R1 and the waves if FP components per case fall with the CI excluding 0 *and* tF1 is
    non-inferior (CI lower bound > −0.01);
  - **not adopted** if FP falls but tF1 is inferior; then report the trade-off to the judge (FP-gate vs tF1 is a
    human question);
  - **not adopted** if FP does not fall. The FP gate's achievability then goes to the humans with this census as
    evidence (A15 branch).
  - **MDE** (A19): FP per case 0.41 (paired SD 1.31 from run 2, n = 80), i.e. ≈ 28 % of 1.49; tF1 0.010–0.022.
- **Order.** Run 3 first, then R1 at full length (48.6 h, three chained jobs) with the default window and the FP term
  if adopted.
  - R1's role is initialising the fine-tunes and answering the epoch question. Running it without a term that may
    be adopted would mean the waves fine-tune a model trained without it.
  - The final model is trained from scratch either way (A17).

## Limits

- **Small CT sample.** The HU reading rests on 21 components in the 11 cases whose CT is cached locally. The other
  73 have only the census's mean HU, whose median of 80 is consistent but partial-volume diluted.
- **No vein labels.** "Cardiac vein" is an anatomical reading of location, calibre, course and enhancement, not a
  label. No reference in the project traces veins.
- **Proxy reference.** The reference is the projected proxy, the ImageCAS mask. Team reads will not add these
  structures, because edits are confined to the mask (D7).
- **One seed, truncated arm.** The window comparison has one seed per arm and a truncated B (§1).

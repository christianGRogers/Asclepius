---
tags: [plans, candidate, literature, amendments, round6]
author: Foxtrot
round: 6
version: 1
updated: 2026-10-10
---

# Foxtrot v1: nothing published beats the master's model; four amendments, on fine-tune mechanics and the FP gate

## 1. Thesis

I searched the 2024–2026 literature and challenge reports for a method that beats a well-configured nnU-Net
on per-branch coronary or comparable multi-class vessel labelling, or that changes best practice for a part
of the master recipe. **I found none.** The verified evidence:

- In both multi-class vessel challenges, TopCoW (NEJM AI 2026) and TopBrain 2025, the top three teams
  built on nnU-Net.
- The only vessel foundation model entered (vesselFM, fine-tuned) came 9th of 11 on TopBrain CTA.
- The one coronary benchmark where nnU-Net lost (ImageCAS-X: CAS-Net 91.2 vs 89.8 DSC) used a
  default-configured nnU-Net: a 48–56 mm patch and the automatic CT window. The master departs from that
  configuration on both points, and the gap there is in topology and false positives (β err 5.6 vs 1.9),
  not overlap.
- Large-scale CT pretraining (MedNeXt-v2, CADS, TotalSegmentator weights) gains about 0.6–2 Dice on organ
  and tumour sets. It has no coronary measurement, lost by 14 Dice in the one fine-spacing vessel case
  reported, and cannot be loaded into the master's 7-stage network.

So I do **not** challenge the model, data, schedule or metric. This plan is the master
([[Atlas v5]] + A1–A16; the Round 6 fine-tune recipe as in [[Atlas v7]]) plus four amendments where the
literature or the code shows a specific gap:

- **F1, a precondition on Q1.** Stock nnU-Net warm starts re-initialise the output heads and have no
  warm-up, and no fine-tune trainer exists.
- **F2, insurance on Q1.** If warm 1e-2 fails FT1, test 1e-3 before retiring warm starts, as the cited paper
  found.
- **F3, the A15 census lever.** A heart-and-aorta ROI component rule that provably cannot delete reference
  vessel.
- **F4, a conditional, costed pretraining proposal.** It runs only if the final model misses acceptance.

## 2. Recipe

The recipe is the master's in every respect not listed here: data prep, proxy, 4-class ResEnc at 0.5 mm with
a 256³ patch, the fixed window decided by run 2, Dice + CE, default sampling, mirroring off, 1000-epoch R1,
the per-wave fine-tunes of Atlas v7 §2.7, A11′ two-read samples, the A1 ostium, and tF1 @ 1.5 mm. The
amendments follow.

### F1. Implement the warm start the plan describes, and test it before FT1 (precondition, CPU + 0 GPU)

Evidence: [[Foxtrot - Stock nnU-Net warm starts re-initialise the segmentation heads and have no warm-up, and the MAE paper found 1e-3 better than 1e-2]].

- `nnUNetv2_train -pretrained_weights` (nnU-Net 2.8.1) skips every `.seg_layers.` key, so all
  deep-supervision output heads restart from random. It then trains at LR 1e-2 poly from epoch 0, with no
  warm-up. Atlas v7 specifies "all layers" and a 10-epoch linear warm-up. Neither exists in `src/segtrain` or
  `trillium/`.
- **Amendment.** Before FT1, the trainer owner (Atlas: trainer module) adds
  `nnUNetTrainer_segtrain_finetune`. It:
  1. loads the full state dict of the last accepted model, `seg_layers` included, asserting identical
     plans, classes and keys;
  2. ramps the LR linearly over a stated number of **iterations**, then applies poly decay;
  3. records both in the run's `events`.

  A CPU test under `tests/` should load a checkpoint and assert bitwise-equal `seg_layers` after loading, and
  check the LR at iterations 0, mid-ramp and end of ramp. FT1's warm arm is invalid without it.
- The warm-up length should be stated against a source. The cited paper used 12.5k iterations (50 epochs);
  Atlas v7's 10 epochs is 2,500. I do not ask for a change, only for the deviation to be stated.

### F2. If warm-at-1e-2 fails FT1, run warm-at-1e-3 before retiring warm starts (conditional, 12.2 H100-h)

- Atlas v7's FT1 compares warm at 250 epochs (peak 1e-2, warm-up) with scratch at 500, margin 0.01.
- The only fine-tuning ablation inside nnU-Net that I could find (Wald et al., CVPR 2025, Table 3) found
  peak 1e-3 better than 1e-2 in every transfer configuration: 71.76 vs 71.02 average DSC with full transfer
  and warm-up.
- Atlas argues 1e-2 is needed to unlearn proxy habits. That argument is plausible, but it is not the
  evidence the plan cites.
- **Pre-registered.** If FT1-warm fails non-inferiority, one more 250-epoch warm arm at peak 1e-3 runs on
  the same data and decision set. Warm starts are retired only if it also fails. If FT1-warm passes,
  nothing extra runs.

### F3. A heart-and-aorta ROI rule as the census lever for far-from-tree FPs (conditional, ≈ 0 GPU)

Evidence:

- [[Foxtrot - The ImageCAS reference lies wholly within 17 mm of a TotalSegmentator heart-and-aorta ROI]];
- literature in [[Foxtrot - Nothing published by October 2026 beats a well-configured nnU-Net on per-branch coronary or vessel labelling]] §4:
  - TopCoW: ROI localisation "reduce[s] false positives in the background";
  - ADE-HTL, best β err in ImageCAS-X, uses TotalSegmentator heart masks at inference;
  - TotalSegmentator's coronary task crops to the heart.

**Rule.**

- Run TotalSegmentator `fast`, `roi_subset=['heart', 'aorta']` on the CT. The A1 rule already runs this model
  for the aorta, so the heart is free.
- Delete every predicted connected component whose **minimum** distance to (heart ∪ aorta) exceeds
  **d = 25 mm**. That is the measured reference maximum (16.5 mm over 40 non-sealed cases; 0 reference
  voxels beyond 20 mm) plus an 8.5 mm margin; see the note.
- The rule is disabled for a case whose heart mask is implausibly small (< 5000 voxels at 3 mm, a field-of-view
  or segmentation failure), and the case is reported.

**Why it is safe by construction.**

- On all 40 non-sealed cases measured, every ImageCAS reference voxel lies within 16.5 mm (< d) of the ROI.
- So any predicted component that touches the reference has minimum distance ≤ d and is kept. The rule
  removes only components with zero reference overlap.
- Per case, therefore, the FP count cannot rise, tF1 recall cannot change, and tF1 precision cannot fall.
  This is the "removes no reference vessel" evidence the judge required in A15 for a non-raw deletion
  filter, measured on the reference side before any prediction is seen.

**When it is adopted.** Only through A15's census branch:

- run 2's Phase A census, or its re-analysis on the saved val segmentations, shows that a material share of
  FP components (pre-registered: ≥ 25 %) lie beyond d of the TotalSegmentator heart ∪ aorta on the 80 val
  cases;
- on val, FP per case falls with a paired CI excluding 0;
- tF1 is not worse. That is guaranteed for reference-touching components, so the check only confirms the
  implementation.

It is reported **beside** the raw FP gate, never in place of it. Whether a heart-ROI FP count may serve as
the acceptance count is the judge's call under A15 (it is not "raw"). My argument for allowing it: the
ROI is computed from the CT alone, by a frozen external model, before the coronary output is examined.
TotalSegmentator ships its own coronary model the same way.

**Cost.** TotalSegmentator heart masks for the 80 val CTs. The A1 re-score in run 2 Phase A already
computes the aorta with the same model; adding `heart` to `roi_subset` costs nothing extra on the next job,
or about 100 s per CT on CPU. The rule itself is a distance transform on the prediction. **No training.**

### F4. Pretraining: a conditional, costed proposal only (not a job)

Evidence: [[Foxtrot - Large-scale CT pretraining gains about one Dice point on organs, has no vessel evidence, and cannot be loaded into the master's network]].

- **Trigger.** At the sealed milestone, the final model fails A10 in some class, *and* the wave history shows
  tF1 still rising with data (FT2 → FT3 gain ≥ 0.01). That is the regime in which pretraining's
  representation gain could plausibly matter. Otherwise nothing runs.
- **Arm.** MedNeXt-v2 base, the official nnU-Net release with CADS-subset pretrained weights, fine-tuned
  at 0.5 mm with a 192³ patch (96 mm: the fine-tune patch the paper found best; it gives up the master's
  128 mm). Settings: AdamW, peak 1e-3, 50-epoch warm-up, 300 epochs on the final data. Compared with the
  master's final model on the 160-case decision set by paired tF1, margin 0.01 the other way: adopt only
  if better.
- **Cost estimate.**
  - nnU-Net Revisited timed MedNeXt L k3 at 68 A100-h per 1000 epochs, against 35 for ResEnc L.
  - Scaling to 300 epochs and to 192³ (≈ 3.4× the voxels of a 128³ patch) gives ≈ 70 A100-h ≈ 35–50 H100-h,
    plus a 1 h R0-style memory and speed check.
  - Range 25–70 H100-h, since the patch scaling is linear in voxels only to first order.
  - Human effort: none.
- **Prior.**
  - Expected effect is ≤ +0.01 tF1. CADS over ResEnc-L is +0.9 DSC on organs.
  - The spacing mismatch can be negative: MAE Table 9 lost 14 Dice.
  - On the decision set's 0.020 MDE ([[Bridge v6]]) it is likely undetectable. That is why it stays
    conditional.

### What does not change, and why (each checked against the literature)

| Part | Literature 2024–2026 | Decision |
|---|---|---|
| Architecture (ResEnc, 256³, 0.5 mm) | TopCoW/TopBrain winners all nnU-Net; MedNeXt-v2's gain over ResEnc-L from scratch is +0.66 (82.31 vs 81.65), within noise for one dataset | Keep |
| Foundation / promptable models | vesselFM fine-tuned 9th of 11 (TopBrain CTA); SAM/VISTA as in the vault note | Ruled out |
| Losses | Skeleton Recall and cbDice are common in TopCoW/TopBrain top teams; on coronaries clDice worsened β err (ImageCAS-X) | Round 5's deprioritisation of A4 stands; revisit only on recall-type distal losses |
| Several annotators | Nothing supersedes Crucible's GPU result | A11′ stands |
| Post-processing | Two-stage ROI and component removal are standard among the top teams | F3, conditional |
| Pretraining | +0.6 to +2 Dice on organs and tumours; nothing on coronaries; incompatible with the master's network | F4, conditional |

## 3. Evaluation

Unchanged: macro tF1 @ 1.5 mm against each read (A10), A1 ostium, frozen `tf1.py`, A15 raw FP gate, swap
rate. F3 adds one reported column: FP components per case after the ROI rule. That column is never a
substitute for the raw gate unless the judge rules so.

## 4. Evidence

| Claim | Evidence |
|---|---|
| No method beats a well-configured nnU-Net on multi-class vessel or per-branch coronary labelling; the ImageCAS-X loss was against a default configuration | [[Foxtrot - Nothing published by October 2026 beats a well-configured nnU-Net on per-branch coronary or vessel labelling]] (TopCoW arXiv:2312.17670v5; TopBrain medRxiv 10.64898/2026.05.28.26354312; ImageCAS-X arXiv:2608.30404 + repo configs; NA-UNETR arXiv:2608.12274; CorSegRec arXiv:2504.01597) |
| Pretraining gains and loader incompatibility | [[Foxtrot - Large-scale CT pretraining gains about one Dice point on organs, has no vessel evidence, and cannot be loaded into the master's network]] (MedNeXt-v2 arXiv:2512.17774 Table 4; SegBook arXiv:2411.14525 Table 4; MAE CVPR 2025 Tables 4, 9; nnU-Net 2.8.1 `load_pretrained_weights`; master plans file) |
| Warm start resets heads, has no warm-up; cited paper prefers 1e-3 | [[Foxtrot - Stock nnU-Net warm starts re-initialise the segmentation heads and have no warm-up, and the MAE paper found 1e-3 better than 1e-2]] |
| The reference lies within d of a TotalSegmentator heart ∪ aorta ROI | [[Foxtrot - The ImageCAS reference lies wholly within 17 mm of a TotalSegmentator heart-and-aorta ROI]] |

## 5. Risks and early detection

| Risk | Signal | Response |
|---|---|---|
| FPs are mostly near the heart (F3 useless) | Census: < 25 % of FP components beyond d | F3 not adopted; A15's other branches apply |
| TotalSegmentator heart fails on a case (FOV, artefact) | Heart volume < 5000 3-mm voxels, or reference voxel beyond d on a val/test case | Rule disabled per case; reported |
| A reference vessel lies beyond d on unseen data | Re-measure on each wave's read cases (CPU, about 100 s per case) | Raise d; the guarantee is re-checked every wave |
| F1 trainer not written before FT1 | FT1 job runs stock `-pretrained_weights` | FT1 result not decisive (judge) |
| F2 adds cost | Only if FT1-warm fails | 12.2 H100-h |

## 6. Comparison with the master and the other candidates

- **Master (Atlas v5/v7).** All recipe decisions are kept. The literature gives no reason to revisit them,
  which is itself the answer to Q5.
  - F1 corrects two statements in Atlas v7 §2.7.3: "all layers" is false under stock nnU-Net, and the
    1e-2 citation is misread. It also makes the plan's warm arm implementable as written.
  - F2 is cheap insurance that FT1 does not retire warm starts by testing the paper's worse LR.
- **Delta v6** closes post-processing for connectivity. F3 is different: it targets FPs, not cuts, and it
  is safe by construction rather than tuned on predictions.
- **Bridge v6** shows that the decision set can see about 0.020. That is why F4 stays conditional and F2
  costs only one arm.
- **Crucible v7.** No change; I found nothing newer on fusion.

## 7. Cost

| Item | GPU | CPU / human |
|---|---|---|
| F1 trainer + test | 0 | ½ day engineering (trainer owner) |
| F2 (only if FT1-warm fails) | 12.2 H100-h | — |
| F3 heart masks for val/test | ≈ 0 (same TotalSegmentator call as A1) | ≈ 100 s per CT if done on CPU |
| F4 (only on its trigger) | 25–70 H100-h (estimate) | — |

## 8. Changes since the previous version

First version (new advocate, Round 6).

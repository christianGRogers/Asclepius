---
tags: [plans, candidate, amendments, fp-gate, report, round8]
author: Foxtrot
round: 8
version: 4
updated: 2026-10-11
---

# Foxtrot v4: the FP triage report; veins are the largest class, but a third are uncallable and some are unenhanced

## 1. Thesis

Decision: **improve (narrow).** v4 is [[Foxtrot v3]] plus the FP triage approved in Round 8 as a report.

- The model recipe is the master's.
- A17a and A17b stand.
- F3 stays withdrawn.
- F4 stays conditional.

Evidence: [[Foxtrot - Of 26 FP components with a cached CT, about 4 in 10 read as veins and a third cannot be called]].

On all 26 raw FP components with a cached CT (12 val cases), classified by rules fixed before the run:

| Class | Count | Share and 95 % CI |
|---|---|---|
| vein | 10 | 38 % [25, 55] |
| unlabelled artery branch | 4 | 15 % [4, 28] |
| mask artefact | 3 | 12 % [0, 21] |
| calcium | 0 | — |
| indeterminate | 9 | 35 % [21, 48] |

Two qualifications:

- 4 of the 10 veins are **unenhanced**, with core 0–32 HU.
- 5 of the 9 indeterminate components would become veins if the course criterion were dropped. That gives
  an upper range of 15/26 veins.

## 2. Amendments (report-level; no gate, no GPU)

1. **If Atlas's FP-aware-loss pilot (run 3) is approved, add one column to its report: tF1 recall on
   reference voxels below 60 HU** (≈ 47 % of mask voxels are 16–38 HU, D0), for each arm.
   - Why: the loss suppresses confident predictions away from labelled vessel. Some FPs are unenhanced
     tubes, the same kind of thing the mask itself labels. A loss that removes them could also erode
     low-HU mask vessel.
   - Cost: zero GPU; it is computed in the scoring.
   - The column decides nothing. It is the early detector for that risk.
2. **Human look at 13 components:** the 9 indeterminate and the 4 unenhanced "veins". The labelling lead
   can do it in under an hour. The CT patch, mask and prediction are listed per component in
   `summarise_triage.py`'s table. It turns the 35 % "cannot call" into a count.

## 3. Unchanged

Recipe, evaluation, evidence, risks, comparison and cost are as in [[Foxtrot v1]]–[[Foxtrot v3]]. No new
Trillium experiment is proposed by me.

## 4. Changes since v3

1. Added the FP triage report: 26 components, explicit rules, case-bootstrap CIs, threshold sensitivity.
2. Proposed the low-HU recall column for run 3, and the 13-component human look.

---
tags: [experiment, janus1-F, track-1F, round3, scorer, gates, stage2, leakage, nnunet, cpu]
author: Delta
updated: 2026-11-23
issue: christianGRogers/Asclepius#303
code: experiments/Delta/j1f_r3/
---

# Delta - Janus 1-F round 3: the scorer and gates are frozen as tested code, and two of F-A22's stage-2 lines fail a correct model

**Questions** ([[Janus 1-F Round 2]] §5, items 1–5):
1. Can the scorer of record (Atlas's definitions, SegQueue's collapse) be frozen with a hash and pass the round-2
   checks on training fixtures? Does it count the same pieces F-A15's lines were simulated on?
2. Does the gate file apply F-A15's lines exactly (OM2 recall 0.59 fails, 0.61 passes)?
3. How big is one locked case's `--save_probabilities` npz, so that the chunked predict-and-decode can be sized?
4. What does nnU-Net 2.8.1 require of the stage-1 dataset that the v2 spec did not do?
5. How often do F-A22's stage-2 lines (L1 0.02, L2 30 mm / 95 %, K1 0.05) fail a stage-2 model that is correct or
   nearly so?

**Setup.**
- **Compute:** CPU only.
- **Data:** the labels of the D45 620 training cases, fetched with Atlas's `fetch_620.py`, which checks every member
  name against the 620 before reading it.
- **Not used:** no locked-100 label, no sealed or quality-0 case, no CT, no model output.
- **Sources read:** nnU-Net 2.8.1's wheel, from PyPI.
- **Item 5's design.** ImageCAS-X has no stage-2 class, so its own traced side branches stand in for them:
  - D1–D3 on the LAD;
  - OM1, OM2 and Ramus on the LCx;
  - PDA and PLB on the RCA.

  Each stand-in is optionally bled k = 1 or 2 voxels into the traced vessel it touches: an ostium painted too wide.

## Results

RESULTS_BLOCK

## What it changes

CHANGES_BLOCK

Plan: [[Candidates/Janus 1-F/Delta v3|Delta v3]].

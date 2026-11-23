---
aliases: [Foxtrot j1f round 3]
tags: [plans, experiment, track-1-F, round3, janus1-f, D45, D47, scorer, gates, stage2, imagecas-x]
author: Foxtrot
track: 1-F
round: 3
updated: 2026-11-23
issue: christianGRogers/Asclepius#303
---

# The amended scorer reproduces the simulated pieces on all 620, and a correct stage-2 model fails L1 and K1 as ruled

Evidence for [[Candidates/Janus 1-F/Foxtrot v3|Foxtrot v3]] (track 1-F, round 3).

## Question

[[Janus 1-F Round 2]] §5 asks round 3 for CPU evidence on four points:
1. Atlas's scorer with SegQueue's collapse imported: does it pass Delta's and Atlas's tests on training fixtures, and
   are its per-piece counts on the 620 the ones F-A15's lines were simulated on? (item 1)
2. Does `j1f_gates.json` fail OM2 recall 0.59 and pass 0.61? (item 2)
3. How much disk does the chunked predict need per locked case? (item 3)
4. Do F-A22's stage-2 numbers (L1 ≤ 0.02, L2 at 30 mm and 95 %, K1 ≤ 0.05) false-fail a correct stage-2 prediction
   on ImageCAS-X references? (item 5)

## Setup

- **Data:** the 620 training labels only. They were fetched by `fetch_620.py`, which asserts the 620's pin
  (`1350cb1f…1152`) and requests only those 620 members of Zenodo's zip. Every script asserts the pin again. No
  locked-100, sealed, quality-0, D60 or TotalSegmentator-twin file was opened.
- **Code:** `experiments/Foxtrot/j1f_r3/`.
  - `j1f_scorer.py`: Atlas's scorer, with `collapse4` replaced by SegQueue's `collapse_to_four`, pinned by sha256.
  - `test_scorer.py`: Delta's checks and Atlas's self-test and perturbations, on Delta's six training fixtures.
  - `gates.py`, `j1f_gates.json`: the gates file and its decision layer, with a self-test.
  - `decode_ref.py`: reference F/T decode and the split builder, with self-tests.
  - `pass_r3.py`, `summarise_pass.py`: every training label through the amended scorer.
  - `stage2_falsefail.py`, `summarise_stage2.py`: item 5.
  - `npz_size.py`: item 3.
- **Environment:** numpy 2.5.3, scipy 1.18.1, scikit-image 0.26.0, nibabel 5.5.0. CPU only, 4 cores.

## Results

### 1. The scorer of record

- `j1f_scorer.py` sha256 `50826b26667c999e8e193effe54e60f7832c9166c863c284554491276d8e8252`.
- **51 of 51 checks pass**, plus one report: a PDA cut to 40 % of its length is still detected in 3 of 6 pieces
  (cover 0.44–0.58), because the 1.5 mm tolerance adds to the 40 % kept. Cut to 30 %, it is missed in all 6.
- **On all 620, the amended scorer's pieces equal Atlas's `census_r2.jsonl` in every case**, for all 8 branch
  classes, voxel count and length alike. Pieces: D1 611, D2 359, D3 47, OM1 540, OM2 229, Ramus 149, PDA 676,
  PLB 620.
- So `gate_sim.pieces_dist` is identical, and Atlas's line rule re-derives F-A15's 18 numbers exactly. **No
  re-freeze is needed.**
- **Collapse:** 1,296 PDA/PLB components (93 to the LCx, 1,203 to the RCA) with **0 fallbacks**. Against D25, 40
  voxels differ in 2 cases, all of them "Other".
- **Converter:** the scorer's `stage1_labels` and `labels_r2.map13` (F0-r2's) agree on every voxel of the 620. Both
  give `{'d3': 47, 'd4_to_lad': 2, 'other_lcx': 20, 'other_nearest': 1, 'other_ignore': 8}`.
- **SegQueue counts face contact only.** Atlas's synthetic PLB touches its RCA along an edge, so it is an unattached
  fallback to the RCA. No reference map of the 620 has one. Predictions may, and `collect` counts them.

### 2. The gates file

`j1f_gates.json` sha256 `b268a2fc51c94a248141f4d21e3ef66d155db838b640688a39b41014032905de`.

`gates.py selftest` checks:
- OM2 recall 0.59 fails; 0.61 passes; 24 of 40 pieces (0.60) passes;
- each of the 18 lines at line − 0.01 fails that class only;
- the 4-of-6 edge;
- a wrong sha256 refuses.

### 3. Disk per locked case

⟨NPZNOTE⟩

### 4. Stage-2 numbers on a correct prediction

⟨S2NOTE⟩

## What it changes

- **Item 1:** the scorer of record is `50826b26…8252`. F-A15 stands without re-freezing.
- **Item 2:** `j1f_gates.json` is `b268a2fc…05de`.
- **Item 3:** chunks of 10 hold ⟨CHUNKS⟩ GB at their peak.
- **Item 5:** ⟨S2CHANGE⟩

## Limits

- The septals are straight synthetic tubes aimed at the PDA; real septals curve and vary in length. Their
  measurement waits on the first extended reads, which F-A21 and F-A22 already route into the freeze before J1F-2.
- Real traced branches (D2, OM2, PLB), grown one voxel into their parent, stand in for the junction geometry of the
  untraced classes.
- The npz estimate is a modelled softmax field, not a network's. Track 1-L's Job 0 `du -sh` gives a measured
  5-class figure when it runs.

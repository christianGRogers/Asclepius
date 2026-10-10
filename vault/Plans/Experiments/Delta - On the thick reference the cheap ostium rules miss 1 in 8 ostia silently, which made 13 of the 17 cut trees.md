---
tags: [plans, experiment, ostium, tree-f1, thick-convention, round5, fp-gate]
author: Delta
round: 5
updated: 2026-10-10
---

# On the thick reference the cheap ostium rules miss 1 in 8 ostia silently, which made 13 of the 17 cut trees

## Question

Atlas's short R1 run (80 val cases) reported 17 cases with a "cut tree", meaning clDice − tF1 > 0.10 in some class, and 1.49 FP components per case. Three questions:

- What are these errors, case by case?
- How much of the loss could P1′ or bridging recover?
- Which of the A1 ostium rules is safe on the **thick** reference, the binding convention?

My earlier validation found 116 of 116 ostia correct ([[Delta - Two cheap ostium rules find 116 of 116 true ostia, and their disagreement flags every miss]]), but it was on the ImageCAS-X lumen, not on the thick reference.

## Method (CPU, no predictions; those stay on Trillium)

1. **Atlas's reference and roots.** `experiments/Delta/r5_cut_anatomy.py` rebuilds Atlas's reference for all 80 val cases with Atlas's own `proxy.make_label`. It recomputes Atlas's roots with Atlas's own `tf1._ostia` and the per-component ostia of `segtrain.tf1.find_ostia`.
   - Both are measured against the ImageCAS-X centreline start points, the experts' ostia.
   - I fetched the right-coronary centreline files for the val cases (range reads from Zenodo), so **69 RCAs** have a truth point instead of 13.
   - The output is joined to `per_case_val.json` by `summarise_r5.py`.
2. **Thick-reference ostium validation.** `r5_ostium_thick.py` (summary: `summarise_r5_ostium.py`) runs on every case with a local CT and ImageCAS-X truth: 71 cases, 133 expert ostia. It tests `thick`, `pool_thick` and two "nearest the blood pool" variants on the thick proxy.
3. **The A1 rule of record.** `r5_aorta_rule.py` (summary: `summarise_r5_aorta.py`) uses TotalSegmentator aorta masks (`aorta_ts.py`) on the same 71 cases plus the 13 val cases above. It compares `aorta_end`, which is `segtrain.tf1` as implemented (thickest endpoint within 5 mm of the aorta), against `aorta_any` (the centreline voxel nearest the aorta, per component, and per component and side).

## Results

### 1. Thirteen of the 17 cuts are misplaced ostia; 4 are real

| Kind | Cases | Signature |
|---|---|---|
| Atlas's root 10–117 mm from the expert ostium | **13**: RCA in c0038, c0163, c0252, c0288, c0368, c0560, c0606, c0717, c0744, c0848; LAD+LCx in c0133, c0613, c0956 | The class scores tF1 ≈ 0 while clDice is 0.73–0.98. The root sits on a distal endpoint the prediction does not reach |
| Real partial mid-tree cut, root correct | **4**: c0095 LAD, c0186 LCx, c0826 LCx, c0878 LCx | clDice − tF1 between 0.10 and 0.26 in one class |

- Over all 80 cases, Atlas's `thick` root is more than 5 mm off for **28 of 69 RCAs and 6 of 80 left trees**. In 28 uncut cases the root was also wrong, but the prediction happened to reach it.
- The segtrain per-component `thick` rule without CT does better but is still unsafe: 17 of 66 RCAs and 7 of 80 left trees are off.
- c0717 and c0560 do have RCA truth. Their roots are 36 mm and 11 mm off, so these are artefacts, not "RCA missed near the ostium". Atlas's note calls them real.

Atlas reached the same diagnosis from 13 RCA truth points ([[Atlas - Trillium R0 and short R1 results]]). This run puts numbers on it with 69.

### 2. With the ostium right, connectivity costs 0.004 tF1 per case: the ceiling for P1′ and bridging

- Mean clDice − tF1 (macro) is 0.054. Of that, 0.050 sits in classes whose ostium is misplaced, and **0.0043** in the rest.
- The residual exceeds 0.01 in 11 cases and 0.03 in 2: c0878 (0.065) and c0095 (0.033).
- The 1.5 mm tolerance already credits 0.013 per case (tF1 − tF1 at 0 mm). Small gaps are already forgiven.
- Counted at clDice, the misplaced classes would give a macro tF1 of up to **0.895** instead of 0.846. That is an upper bound; Atlas's estimate is 0.87–0.90.

### 3. The FP gate fails diffusely, and post-processing cannot pass it

- Per case: 0 FP components in 23 cases, 1 in 19, 2 in 23, 3 in 8, 4 in 5, 5 in 2. The 10 worst cases hold 33 % of all FP components.
- The FP rate is the same in cut and uncut cases (1.65 vs 1.44).
- About 0.9 extra true pieces per case touch the reference but are disconnected. They carry little centreline, as section 2 shows.
- A2 reads the gate on the raw prediction. So no bridging or repair step can pass it; only the model, its window, or a calibrated component filter that the master chooses to count can. That last option would be a change to A2, not mine to make.

### 4. On the thick reference, the cheap rules are not safe (71 cases, 133 expert ostia)

| Rule | Left (74) | Right (59) | All (133) |
|---|---|---|---|
| `thick` | 65 | 47 | 112 (84 %) |
| `pool_thick` | 65 | 53 | **118 (89 %)** |
| centreline voxel nearest the pool | 29 | 50 | 79 |

- **11 of 133 ostia (8 %) are silent errors**: `thick` and `pool_thick` agree, and both are wrong. On the ImageCAS-X lumen this number was 0 of 130.
- The cross-check flags 11 more; in 7 of those `pool_thick` is right.
- Nearest-the-pool fails on the left because the LCx lies on the left atrium and the LAD on the ventricles. The pool there is a heart chamber, not the aorta.
- **Why the rules fail.** The thick mask often has no skeleton endpoint at the ostium.
  - In c0163 the skeleton passes 2.7 mm from the RCA ostium as a degree-2 point. It runs another 12.8 mm to an endpoint, and the nearest endpoint is 13.4 mm away.
  - The RCA barely tapers in the mask: median radius 1.39 mm at the distal end against 1.33 mm at the ostium end. So "thickest endpoint" lands on a distal tip.

### 5. The aorta rule (TotalSegmentator): it fixes the RCA roots, and leaves misses that are mostly flagged

84 cases (the 71 CT cases plus the 13 val artefact cases), 160 expert ostia. TotalSegmentator ran in its fast, aorta-only mode at about 40 s per case on CPU.

| Rule | Left (89) | Right (71) | All (160) |
|---|---|---|---|
| `thick` | 72 | 53 | 125 (78 %) |
| `aorta_end`, else `thick` (segtrain as first written) | 74 | 58 | 132 (83 %) |
| nearest centreline voxel to the aorta, per component | 76 | 62 | 138 |
| **the same, per component and side** (segtrain as revised) | 77 | 62 | **139 (87 %)** |
| either `thick` or the revised rule right (ceiling of a human review of flags) | | | 151 |

- **The val artefacts are fixed.** On the 13 val cases, the revised rule puts **all 11 misplaced RCA roots within 3.8 mm** of the expert ostium; the largest error is 3.8 mm and the median 2.3 mm. Of the 6 misplaced left ostia it fixes 3; the other 3 are near misses of 5.1–7.9 mm.
- **Most misses are flagged.** The revised rule misses 21 of 160 ostia, and 15 of those trees are **flagged**. In 10 of the flagged trees `thick` was right.
- **Silent errors.** 6 of 160 (3.8 %) are wrong and unflagged. Four of them are near misses (5.0–5.3 mm, against a 5 mm threshold); 2 are gross (c0500 RCA 13 mm, c0738 left 12 mm). The endpoint version had 7 silent errors, and the cheap rules alone had 11 of 133 (8 %).
- **Where the gross misses come from.** The coronary passes close to the aortic wall somewhere other than its ostium, for example a proximal RCA hugging the root. The nearest voxel then lands there, and the endpoint rules usually catch it through the flag.
- An endpoint-first hybrid (`aorta_end`, else nearest voxel) gets 138 of 160. It is not better.

## What this changes

1. **A9/A1.** On the thick reference, a tF1 scored with the cheap rules alone is not just "provisional"; it is wrong for about 1 tree in 8. Atlas's 0.846 understates the model.
   - Decisive tF1 numbers must use the aorta rule.
   - Atlas's val should be re-scored with TotalSegmentator aortas: about 40 s per case on CPU.
2. **`segtrain.tf1` is revised.** The aorta rule now takes the centreline voxel nearest the aorta, per tree and side, with the cheap rules as the cross-check. Two new tests cover it, and the API is unchanged apart from a new `Ostium.side`.
   - Flagged trees need a human look. That is the A1 procedure working as designed. The flag rate over all 160 was not tallied for the revised rule; the endpoint version flagged 38.
3. **The "cut tree" count** (clDice − tF1 > 0.10) only means something on trees with an aorta-validated ostium.
4. **P1′ / bridging** can at most recover about 0.004 macro tF1 per case on this model, concentrated in about 4 of 80 cases. The pre-stated test for my pending run is in [[Delta v5]].

## Limits

- No predictions were available on CPU. The case classification uses Atlas's per-class numbers, plus reference-side geometry.
- The 4 "real" cuts are real under a correct ostium, but their size is read from clDice − tF1.
- 11 val cases have no right-coronary truth. Their roots are counted as correct in the 0.004 residual.
- The 71-case validation set is not the val set; it is the cases with a CT on disk, none of them sealed.

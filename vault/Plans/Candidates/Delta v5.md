---
tags: [plans, candidate, topology, post-processing, ostium, tree-f1, round5]
author: Delta
round: 5
version: 5
updated: 2026-10-10
---

# Delta v5 — fix the ostium before judging connectivity; P1′ has 0.004 to win, and its test is fixed now

## 1. Thesis: improve, and narrow

Atlas's short R1 (the master recipe, 412 epochs, 80 val cases) shows where tree-F1 is really lost, and post-processing is not the place.

[[Delta - On the thick reference the cheap ostium rules miss 1 in 8 ostia silently, which made 13 of the 17 cut trees]] shows:

- **13 of the 17 "cut trees" are misplaced reference ostia.** Atlas's `thick` root is more than 5 mm off for 28 of 69 RCAs. Four cuts are real: one LAD and three LCx.
- **With correct ostia, connectivity costs 0.0043 macro tF1 per case.** That is the most P1′ and bridging could ever recover on this model. More than half of it sits in 2 cases.
- **On the thick reference the cheap rules fail silently** for 11 of 133 ostia (8 %). On the ImageCAS-X lumen the figure was 0 of 130, so my own A1 cross-check is not safe on the binding convention without the aorta mask.
- **The FP gate (1.49 per case) fails diffusely, on the raw prediction**, where no post-processing acts by A2's definition.

v5 therefore makes three changes:

1. It moves my effort from connectivity repair to the **ostium of the deciding metric**.
2. It pre-states a sharper test for the pending P1′ run.
3. It concedes in advance what happens if that test fails.

## 2. Proposed amendments

1. **A1, amended: the aorta rule is mandatory for any decisive tF1 on the thick reference.**
   - The ostium is the centreline voxel nearest the TotalSegmentator aorta, per reference tree component and side. Endpoints are not required: the thick mask's ostium is often a pass-through point of the skeleton.
   - `thick` and `pool_thick` remain the cross-check. A disagreement above 5 mm flags the tree.
   - A tF1 without an aorta mask is reported, but it may not decide anything.
   - Evidence (84 cases, 160 expert ostia): 139 right (87 %), against 125 for `thick`. 15 of the 21 misses are flagged; 6 are silent, 4 of them by 5.0–5.3 mm.
   - All 11 misplaced RCA roots in Atlas's val land within 3.8 mm.
   - `segtrain.tf1` (my module) now implements this rule, with tests.
   - Flagged trees go to a human. With review, the ceiling is 151 of 160.
2. **Re-score Atlas's val with TotalSegmentator aortas** (about 40 s per CT on CPU) before any decision table is read on it. Atlas's 0.846 is a lower bound: up to 0.895 if the artefact classes scored their clDice.
3. **The "cut tree" count only on trees whose ostium is aorta-validated (not flagged).** Otherwise it measures the ostium rule, not the model.
4. **The FP gate is a model property.** I support Atlas's order: the FP census first, then the window ablation. Bridging and repair are not candidate fixes, and a component filter would be a change to A2 for the master to make.

## 3. The pending Trillium run: what it must show (fixed now, before any result)

The run is P1′ against nnU-Net's default inference, on Atlas's checkpoint, over the open ImageCAS-X test cases, against the thick reference. It writes three scores per case: tF1 with `thick` roots, tF1 with `pool_thick` roots (`tf1_15_poolroots`), and the ostium flags.

| # | Requirement for "P1′ / bridging fixes cuts" | Why |
|---|---|---|
| 1 | **Primary read: `tf1_15_poolroots` on unflagged trees.** The thick-root numbers are secondary. If the two disagree, pool roots govern. If the predictions survive on $SCRATCH, the aorta-rule re-score governs over both | `pool_thick` is right for 89 % of ostia on the thick reference, `thick` for 84 %, and flagged trees hold most of the misses |
| 2 | C2 (step 0.5 + P1′ minus step 0.5 raw): mean ≥ **+0.002**, 95 % CI > 0, and no case worse by > 0.01 | A CI above 0 alone could pass on noise against a 0.004 ceiling |
| 3 | At least half of the gain comes from cases with a gap site (`n_sites` > 0, an un-anchored piece within 15 mm), and those cases gain ≥ 0.02 on average | P1′ is meant to repair real cuts, not move scores everywhere |
| 4 | Bridge audit: FP joins < true joins. The raw-style FP count after re-inference, before bridging, rises by no more than 0.1 per case | Bridging must not buy connectivity with false vessels, and re-inference must not create FP pieces |
| 5 | C4 (bridging alone) is not below 0, and C5 (support rule) is reported. Neither decides P1′ | Unchanged from v4 |

**My prediction, stated now:** C2's mean will be below +0.002, or its CI will include 0, because the measured ceiling is 0.004. If so:

- **P1′ and P1 bridging leave the master's recipe.** Connectivity post-processing becomes a QA report: the A2 bridge audit plus gap sites.
- If requirements 1–4 all pass, P1′ goes in as a switchable step that is on by default, as v4 proposed.

## 4. Recipe

- **Master as it stands**, plus amendments 1–4 above.
- **Withdrawn unless §3 passes:** P1′ and P1.
- **Kept:**
  - the A2 raw FP gate and bridge audit;
  - the per-component ostium, now aorta-first;
  - the rule of never intersecting the two reads.

## 5. Evidence

| Claim | Evidence |
|---|---|
| 13 of 17 cuts are misplaced ostia; 28 of 69 RCA roots off; residual connectivity loss 0.0043 per case | the note above; `experiments/Delta/r5_cut_anatomy.py`, `summarise_r5.py` |
| Cheap rules on the thick reference: 118 of 133 right, 11 silent errors | `r5_ostium_thick.py`, `summarise_r5_ostium.py` |
| The aorta nearest-voxel rule fixes the artefact RCAs; 139 of 160 overall, 6 silent errors | `r5_aorta_rule.py`, `summarise_r5_aorta.py` |
| Agrees with Atlas's own diagnosis (13 RCA truth points) | [[Atlas - Trillium R0 and short R1 results]] |

## 6. Risks

| Risk | Response |
|---|---|
| The aorta rule fails where the proxy joins the left and right trees | Choose the ostium per component and side; a validation variant tests exactly this |
| TotalSegmentator misses the aorta in a crop | The tree is flagged (no centreline within 5 mm), never scored silently |
| My Trillium run's pool roots are themselves off by about 1 in 9 | Requirement 1 reads unflagged trees only, and an aorta re-score supersedes it |

## 7. Cost

- **GPU:** none new.
- **CPU:** about 1 h for TotalSegmentator on the 80 val CTs, plus the re-score.

## 8. Changes since v4

- Diagnosis of R1's cuts.
- A1 made aorta-first and stated per side.
- P1′'s test sharpened, with its expected failure pre-stated.
- FP repair conceded to the model and window.

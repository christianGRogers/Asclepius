---
tags: [plans, candidate, tree-f1, ostium, rca, failure-taxonomy, round6]
author: Delta
round: 6
version: 7
updated: 2026-10-10
---

# Delta v7: the RCA's deficit is the metric's, and what remains is reference extent — fix the labels' rule, not the model

## 1. Decision: improve (v6's narrowed scope, plus Q2)

v6 closed post-processing and kept the deciding metric. Round 6 asks Q2: why is the RCA weakest, and where does the remaining error live? The answer is [[Delta - The RCA is weakest only through its ostium, and the remaining error tracks reference extent, not truncation or dominance]]:

- **The RCA's deficit is the provisional ostium.**
  - It costs the RCA 0.111 of its 0.229 tF1 loss on val, and 0.078 per case on the open set.
  - Without it the RCA (clDice 0.884) ranks between the LAD and the LCx.
  - **The LCx is the weakest class**, with segment loss 0.132, 3 of the 4 real cuts, and 22 of 80 cases below clDice 0.8.
- **What is left is segmentation loss, and it tracks reference extent.** Segmentation loss is centreline of the right name that is missed or extra. It rises with how far the case's mask departs from expert tracing, in either direction: vessel the mask has that ImageCAS-X does not trace, or ImageCAS-X vessel the mask lacks.
  - Spearman ρ = 0.33–0.57 for the LAD, LCx and RCA.
  - Linear attribution: about 0.06 per case on the RCA and 0.07 on the LCx. This is correlational.
- **Not causes:**
  - field-of-view truncation (2 of 143 cases);
  - a small or left-dominant RCA (no effect);
  - RCA length (ρ 0.04);
  - real cuts (≤ 0.009 per class);
  - RCA naming (0.002).
- **Distal calibre** matters modestly for the LAD and LCx (about 0.01 each) and not detectably for the RCA.

## 2. Proposed changes

### A. Pre-stated reading of run 2 Phase A (fixed now, before its result)

Phase A re-scores run 1's val with the A1 rule. My Q2 explanation **predicts**, on unflagged trees:

1. RCA A1-tF1 at least **0.85**: clDice 0.884, minus real cuts, minus the 1.5 mm difference.
2. The class order becomes LM > LAD ≈ RCA > **LCx**.
3. The RCA's gain over 0.771 is at least 0.07.

**Falsifier:** if unflagged RCA A1-tF1 is below 0.84, or the RCA is still the lowest class, then the ostium does not explain the RCA deficit. My taxonomy is then wrong on its main term, and §2C becomes the first thing to run.

### B. A written extent rule for team reads (a decision for the labelling lead)

- D0 makes the ImageCAS mask the reference, but its extent varies case to case. The RCA mask carries a median 21 % of vessel that ImageCAS-X does not trace (RV, conus and acute-marginal branches). The LCx most often lacks ImageCAS-X vessel (35 of 80 cases above 10 %).
- A model cannot learn which side branches a given annotator included. That loss is irreducible by training on these labels.
- **Proposal:** the two-read protocol carries one extent rule, e.g. "every branch of at least 1.5 mm diameter at its origin, to where it falls below 1 mm". Crucible's A3 convention monitor checks extent per read (side-branch count and length against the rule), not only calibre.
- Whether sub-rule branches in the *proxy* reference are scored as `ignore` is a scoring choice for the master. It would need A1c's procedure, because it touches the frozen metric's inputs, not its code.

### C. Miss census on run 1's val predictions (proposal, CPU, after run 2 returns; no Trillium work now)

- **What:** for every missed or wrongly named reference centreline voxel, and every predicted centreline voxel outside its class, record:
  - geodesic distance from the A1 ostium;
  - radius;
  - whether ImageCAS-X traces it;
  - distance to the nearest prediction;
  - HU.
- **Method:** it uses `segtrain.tf1` unchanged, through its existing outputs.
- **Cost:** about 1 CPU-minute per case, 80 cases. It needs the saved predictions copied off $SCRATCH (about 1 GB), or it can run there as a CPU step in whatever job next touches them.
- **Value:** it turns §1's correlations into a location map. It also tells the labelling lead whether RV and conus branches, distal tips, or FP pieces are the RCA's remaining 0.11.

### D. Reference QA

- Flag references whose left and right trees are joined (4 of 80 val; their RCA loses about 0.11 more).
- The per-side A1 ostium already scores them correctly. They should still be listed for the labelling lead.

### E. Not proposed (the evidence says they would not pay)

- field-of-view handling;
- dominance-specific training or sampling;
- RCA-specific loss weighting;
- any connectivity post-processing (v6).

## 3. A1b flag rate of the revised rule (measured; due before wave 1)

`experiments/Delta/r6_flags.py` ran the revised rule (aorta plus CT, so `thick` and `pool_thick` both cross-check) on the 84 cases with aorta masks, 171 trees. Summary: `summarise_r6_flags.py`.

| | Trees | Flagged | Unflagged: ostium within 5 mm | Flagged: ostium within 5 mm |
|---|---|---|---|---|
| All | 171 | **46 (27 %)** | **112 / 118 (95 %)** | 23 / 39 |
| Left | 86 | 17 (20 %) | 65 / 69 | 8 / 17 |
| Right | 85 | 29 (34 %) | 47 / 49 | 15 / 22 |

- **Silent errors:** 6 of 171 trees are unflagged and wrong. Four of them are 5.0–5.3 mm off; two are gross (c0500 RCA 12.8 mm, c0738 left 12.1 mm).
- **The flag is informative.** Flagged trees are right only 59 % of the time, against 95 % for unflagged trees.
- **Review budget (for the labelling lead, A1b).**
  - About 0.55 flagged trees per case, i.e. about 550 trees over 1000 cases.
  - At about 1 minute each, picking the ostium on the CT, that is roughly 9 reader-hours.
  - Restricted to the 100 sealed cases: about 55 trees, roughly 1 hour.
- **Cheaper option, if the budget is refused:** flag on aorta vs `pool_thick` disagreement only. This was not measured; it would need its own validation.

## 4. Evidence

| Claim | Evidence |
|---|---|
| Per-class loss decomposition; taxonomy; attributions | Q2 note; `experiments/Delta/r6_attrs.py`, `r6_taxonomy.py` |
| Ostium: A1 rule 139/160; misplaced-root costs | [[Delta - On the thick reference the cheap ostium rules miss 1 in 8 ostia silently, which made 13 of the 17 cut trees]] |
| Post-processing closed | [[Delta - Trillium P1′ result on the master model]] |

## 5. Risks

| Risk | Response |
|---|---|
| The extent correlation is confounded by anatomical complexity | §2C localises it; §2B is cheap regardless, because a written rule is needed for two reads to agree |
| Phase A flags many RCAs, so the unflagged aggregate is small | Report the n. The prediction is stated for unflagged trees and is falsifiable at any n ≥ 30 |

## 6. Changes since v6

- Q2 answered.
- A falsifiable reading of Phase A, stated in advance.
- An extent rule for team reads proposed.
- The miss census proposed.
- Reference QA for joined trees.
- The A1b flag rate is measured: 27 % of trees, with 95 % of unflagged trees correct.

---
tags: [plans, experiment, round6, tree-f1, rca, failure-taxonomy, ostium, convention]
author: Delta
round: 6
updated: 2026-10-10
---

# The RCA is weakest only through its ostium, and the remaining error tracks reference extent, not truncation or dominance

## Question (Round 6, Q2)

Why is the RCA the weakest class in R1 (tF1 0.771, against 0.869 for the LAD and 0.812 for the LCx), and where does the remaining error of every class live? The candidate causes are:

- field-of-view truncation;
- a small or non-dominant RCA;
- the ostium;
- the convention (what the reference does and does not contain);
- distal loss.

For each one: how often it occurs, what it costs, what would fix it, and whether Atlas run 2 will tell us.

## Data and method (CPU only; no predictions on this machine)

**Scores (round 5, GPU).** All three sets come from the same model, Atlas's run-1 checkpoint.

| Source | Cases | What it gives |
|---|---|---|
| Atlas `per_case_val.json` | 80 val | per-class tF1, clDice and Dice |
| Bridge `cases/` | 80 val | O − D: oracle names on the same foreground, i.e. naming headroom |
| Delta `per_case.jsonl` | 63 open test cases | per-class tF1 at tile step 0.5, raw |

**Reference attributes.** `experiments/Delta/r6_attrs.py` computes these for all 143 cases, on Atlas's own proxy (`make_label`) and the ImageCAS-X 14-class labels:

- geometry: centreline length, radius, and the fraction of centreline thinner than 1 mm;
- field of view: distance of each class to the scan faces;
- dominance: R-PDA/R-PLA against L-PDA/L-PLA;
- convention:
  - `mask_unnamed`: mask voxels more than 2 mm from any ImageCAS-X voxel, i.e. vessel the experts did not trace or name;
  - `icx_outside_mask`: ImageCAS-X vessel more than 1 mm outside the mask, i.e. vessel the reference lacks;
- reference structure: number of components, and whether the RCA is joined to the left tree.

**Ostium truth.** The provisional `thick` roots are compared with the ImageCAS-X start points. Centrelines were fetched for every case: 69 of 80 val, 63 of 63 open.

**Loss decomposition.** For val, per class, `r6_taxonomy.py` splits 1 − tF1 into four parts:

| Part | Definition |
|---|---|
| ostium | clDice − tF1, when the root is more than 5 mm from the expert ostium |
| cut | clDice − tF1 otherwise |
| naming | O − D |
| segment | 1 − clDice − naming |

The segment part is the centreline of the right name that is either missed or extra. Round-5 outputs cannot split it further into recall and precision. Segment loss is then stratified and regressed on the reference attributes.

## Results

### 1. Loss decomposition, val (80 cases; mean per case)

| Class | 1 − tF1 | ostium | real cut | naming | segment | 1 − Dice |
|---|---|---|---|---|---|---|
| LM | 0.036 | 0.000 | 0.000 | 0.022 | 0.014 | 0.096 |
| LAD | 0.131 | 0.033 | 0.005 | 0.011 | 0.082 | 0.156 |
| LCx | 0.188 | 0.030 | 0.009 | 0.016 | **0.132** | 0.229 |
| RCA | **0.229** | **0.111** | 0.003 | 0.002 | 0.114 | 0.160 |

**Half of the RCA's loss (0.111 of 0.229) is the provisional ostium.** Once that is removed, the RCA (segment 0.114, clDice 0.884) sits between the LAD and the LCx. **The LCx is the weakest class**: it has the most segment loss, the most real cuts (3 of the 4 real cuts), and the most clDice values below 0.8 (22 of 80, against 7 for the RCA).

The open set agrees on a different model run and different cases:

- The provisional root is more than 5 mm off in 13 of 63 RCAs.
- Those RCAs lose 0.511, against 0.136 where the root is right, which attributes 0.078 per case to the ostium.
- With the root right, RCA loss (0.136) is again between the LAD (0.128) and the LCx (0.184).

### 2. Taxonomy, per failure type

| Failure type | How often | tF1 cost per case | What would fix it | Will atlas2 tell us? |
|---|---|---|---|---|
| **Ostium, provisional `thick` root misplaced** (the RCA mask's ostium is a pass-through point; the root lands on a distal tip) | RCA 28/69 val, 13/63 open; left 6/80 val | **RCA 0.111 val / 0.078 open**; LAD 0.033, LCx 0.030 | The A1 aorta rule, already adopted. On 160 expert ostia it gets 139 right and fixes all 11 misplaced val RCAs. Flagged trees go to a human (A1b) | **Yes, directly.** Phase A re-scores run 1 with A1, so RCA tF1 should rise toward its clDice (0.884) |
| **Reference extent / convention** (mask vessel that ImageCAS-X does not trace; ImageCAS-X vessel the mask lacks) | Mask-only vessel is common on the RCA: median 21 % of RCA mask voxels, against 6–8 % for the LAD and LCx. ImageCAS-X vessel outside the mask exceeds 10 % in 14/80 RCAs and 35/80 LCx | Correlational. Spearman ρ with segment loss is 0.33–0.57 for LAD, LCx and RCA (p ≤ 0.003). A linear fit attributes about **0.058 RCA**, 0.071 LCx and 0.048 LAD per case (R² 0.15 / 0.41 / 0.42) | A written extent rule for team reads (which side branches count, and a minimum calibre), applied the same way to every case. Optionally, score sub-rule branches as `ignore`. This is a labelling-protocol decision, not a model change | **Partly.** The FP census's `icx_vessel` category measures the "mask lacks" half for FP components only, and per-class precision vs recall says which half dominates. Neither localises the misses. A miss census (below) would |
| **Reference artefact: RCA joined to the left tree in the mask** | 4/80 val, 1/63 open | RCA loss 0.218 vs 0.108 (p = 0.001), so about 0.006 per case | Split the proxy by side at scoring (A1's per-side ostium already does this); flag it in reference QA | No |
| **Distal calibre** (thin centreline, radius < 1 mm) | Upper quartile per class | LAD about 0.010 (p = 0.02), LCx 0.013 (p = 0.004); RCA not significant on val (p = 0.34), weak on open (ρ 0.30, p = 0.03) | Window or loss ablations (run 2 Phase B tests the window); higher resolution is already 0.5 mm | Phase B shows only whether the window moves it |
| **Real cut** (correct root, disconnected piece) | 4/80 val (3 LCx) | RCA 0.003, LCx 0.009, LAD 0.005 | None worth its cost: P1′, P1 and P2 failed on the master model | Phase A's A1 tF1 vs clDice gives it exactly |
| **Naming** (right vessel, wrong class) | — | RCA 0.002, LCx 0.016, LM 0.022, LAD 0.011 | Nothing for the RCA; the LM and LCx names live at the carina (Bridge / Crucible) | No |
| **Field-of-view truncation** | **2 of 143 cases** have any class centreline within 2 mm of a scan face (c0815 LM, c0341 RCA); 4 cases have more than 5 % of a class's centreline within 5 mm of a face, all LM or LAD, at a z-end of the scan | ≈ 0 (c0341 RCA loss 0.13 vs 0.15 for the other open RCAs) | Not needed | — |
| **Small or left-dominant RCA** | 4/80 val, 2/50 open by ImageCAS-X PDA/PLA labels | Not significant (val +0.003, open −0.005); RCA length has no effect (ρ 0.04) | Not needed | — |

### 3. What remains after the ostium

About half of every class's segment loss tracks how far the case's reference extent departs from expert tracing. For the RCA this is weaker (R² 0.15) and about half its segment loss is unexplained by any attribute measured here. Five candidate causes cannot be told apart from scores alone:

- missed distal segments;
- RV branches and the conus;
- precision lost to FP pieces named RCA;
- calibre mismatch near the ostium;
- motion and image quality.

Separating them needs the predictions.

## Proposal: a miss census for the next scoring pass (CPU, on saved predictions; costed, not requested)

For every reference centreline voxel that is missed or wrongly named, per class, record:

- its geodesic distance from the A1 ostium;
- its radius;
- whether ImageCAS-X names it (mask-only or not);
- its distance to the nearest prediction;
- its HU.

Do the same for predicted centreline outside the class.

- **Cost:** about 1 CPU-minute per case on the 80 run-1 val predictions, with no GPU.
- **Value:** it turns the correlations in §2 into a location map. For example, it would say whether "RCA error = mask-only RV branches" holds, and it would tell the labelling lead which extent rule matters.

It would be scored with `segtrain.tf1` unchanged (frozen under A1c), using its existing `recall`/`precision` and the centreline it builds.

## A1b: flag rate of the revised ostium rule (Round 5 action item)

- On 84 cases (171 trees, aorta plus CT): **27 % of trees are flagged**, 20 % on the left and 34 % on the right.
- Unflagged trees have the ostium within 5 mm 95 % of the time (112 / 118); flagged trees 59 % (23 / 39).
- 6 silent errors, 4 of them 5.0–5.3 mm off.
- Implied human review: about 0.55 trees per case.
- Details in [[Delta v7]] §3; script `experiments/Delta/r6_flags.py`.

## Limits

- No predictions were available. Every attribution is between case-level scores and reference geometry, and it is **correlational**: complex anatomy could drive both mask-only vessel and model error.
- ImageCAS-X does not name RCA side branches (no class for conus, RV or acute marginals). So `mask_unnamed` is partly "side branch" by construction, which is why the RCA median is high.
- Dominance comes from the ImageCAS-X PDA/PLA labels, not from a reader.
- Naming headroom is Bridge's O − D, computed with Bridge's own provisional roots.
- Val and open are different case sets scored with different reference roots. They agree in direction, not in exact size.

Scripts: `experiments/Delta/r6_attrs.py`, `r6_taxonomy.py` (output `work/Delta/r6/taxonomy.txt`); the ostium figures come from `r5_*`.

---
aliases: [Proposed changes (metrics)]
tags: [research, evaluation, metrics, proposed-changes]
status: living
updated: 2026-09-19
---

# Proposed changes

Concrete changes this topic's research argues for, in [[Training plan]] and in
the evaluation code. Each carries the note that justifies it. Nothing here has
been applied — the plan and the code are owned elsewhere.

## To [[Training plan]], "Evaluation" section

| # | Change | Evidence |
|---|---|---|
| E1 | Cite Maier-Hein/Reinke et al., Nat Methods 2024 for the metric pool; state the fingerprint items (tubular FP3.3, small-relative-to-grid FP3.1, noisy reference FP4.3.1, empty reference FP4.6) that justify demoting Dice | [[Which metrics to report for thin tubular multiclass segmentation]] |
| E2 | Rename "AHD" to **MASD** and define it, or state that AHD = ImageCAS's average symmetric surface distance kept for comparability. Never report bare HD | same |
| E3 | Make the NSD tolerance an explicit reported parameter, derived from the annotation overlap set; the current default of 1.5 mm is ~4 voxels at coronary spacing and is indefensible here | same (Metrics Reloaded DG7.1: τ "can be set according to the inter-rater variability") |
| E4 | Add the NaN policy in two halves: absent-in-both is skipped; present-in-one is scored at the worst value (Dice 0, and a *finite* distance bound) | same + [[How to measure branch detection and score absent branches]] |
| E5 | Define "branch detection rate" = per-class recall at IoU ≥ 0.25 using TopCoW's four-way TP/FN/FP/TN rule, and report detection F1 beside it | [[How to measure branch detection and score absent branches]] |
| E6 | State that clDice does not measure boundary/calibre accuracy, so clDice never substitutes for NSD/MASD | [[Why Dice misreads a three-voxel coronary branch]] |
| E7 | Require per-case distributions (strip/violin) and confidence intervals on every per-class metric, not means alone; small classes will have single-digit case counts | Metrics Reloaded pitfall table ("Small test set size — Recommendation of confidence intervals for all metrics"); [P3.4] |
| E8 | Report Betti-0 error per class with 26-connectivity (empty mask ⇒ b0 = 0) alongside connected-component counts | [[How to measure branch detection and score absent branches]] |
| E9 | Fewer decimal places: "More than one decimal number is often not useful given the typically high inter-rater variability" | Metrics Reloaded, reporting pitfalls |
| E10 | Close "Acceptance thresholds" with the five-tier table (trunks/common/variable/rare + topology + NSD), replacing the handover draft, and mark it provisional until the multiclass baseline exists | [[Acceptance thresholds for per-branch coronary segmentation]] |
| E11 | Add a concrete Betti-0 ≤ 1 gate for the four trunk classes (LM/LAD/LCx/RCA), anchored on ImageCAS-X's inter-observer Betti error of 0.2–0.4 | same |
| E12 | State explicitly that the evaluation thresholds measure segmentation quality against a human reference, not validated clinical utility — no outcome or invasive-reference study exists for this project, unlike the cleared coronary CT AI products surveyed | [[Regulatory and clinical deployment evidence for coronary CT AI]] |
| E13 | Name the CLAIM item-32 / TRIPOD+AI item-16 limitation explicitly: the binary calibration run's test set is drawn from the same single-centre cohort as training | [[CLAIM and TRIPOD+AI checklists for a coronary segmentation manuscript]] |
| E14 | Add an external-validation step for the binary run on ASOCA (different scanner/protocol); expect ~5–8 point Dice drop based on three independent cross-dataset measurements | [[External validation and cross-dataset generalisation for coronary segmentation]] |
| E15 | Add a per-class NSD tolerance table derived from the annotation overlap set (95th percentile of pooled inter-annotator surface-point distances), replacing the single module-level constant; interim default one voxel (≈0.35 mm) for every class until that set exists | [[NSD tolerance selection for sub-millimetre coronary vessels]] |
| E16 | Report Betti matching error (not just Betti-0 error) for the final multiclass configuration, because plain Betti-0 counting is cancellation-blind to a dropped-branch-plus-hallucinated-fragment failure pattern | [[Topology and connectivity metrics for coronary trees]] |
| E17 | Report per-dominance and per-disease-status subgroup performance, using the same stratification already recommended for fold construction | [[CLAIM and TRIPOD+AI checklists for a coronary segmentation manuscript]], [[Fold schemes and split ratios]] |
| E18 | Disclose whether annotators see the binary model's presegmentation before drawing per-branch labels (a blinding decision) — flagged to the annotation-protocol agent, disclosure is this topic's concern | [[CLAIM and TRIPOD+AI checklists for a coronary segmentation manuscript]] |

## To `src/segtrain/metrics.py`

| # | Gap | Why it matters |
|---|---|---|
| M1 | **No clDice.** `score_case` computes Dice and NSD only | clDice is the framework's named recommendation for tubular structures and is what detects a missing distal sub-branch; TopCoW's implementation (skimage `skeletonize_3d`, harmonic mean of the two centreline scores) is a ~30-line reference |
| M2 | **No detection outcome or IoU per class.** Presence is only visible as `ref_voxels`/`pred_voxels` | the branch detection rate in [[Training plan]] cannot be computed from the current CSVs at all |
| M3 | **No connected-component or Betti-0 count** | the plan asks for "connected-component count against expected"; nothing computes it |
| M4 | **No confusion matrix between classes.** Every metric is one-versus-rest per label | LAD/LCx and PDA/PLV confusion is a *swap*, which one-versus-rest Dice reports as two independent mediocre scores instead of one systematic error |
| M5 | **`hausdorff95` returns `inf` for one-sided absence and `agreement()` serialises it to `None`**, so the worst cases silently vanish from means | this is the failure mode the metric exists to catch; needs a finite, stated bound (TopCoW uses 90 mm) |
| M6 | **`DEFAULT_NSD_TOLERANCE_MM = 1.5`** is inherited from 1.5 mm isotropic whole-body data | at 0.35 mm it is ~4 voxels, wider than a distal vessel; needs to be a per-task config value with a coronary default |
| M7 | **No MASD/ASSD.** Only HD95 and NSD | MASD is the framework's default distance metric; ImageCAS's comparison number (AHD 0.818 mm) is of this family, so we cannot currently reproduce their table |
| M8 | **`summarize()` pools all (case, structure) pairs into one "mean Dice"** | the exact aggregation pitfall [P3.2] warns about; per-class means already exist and should be the headline |
| M9 | **No bootstrap CI / paired-test helper beyond `wilcoxon`** in `src/segtrain/evaluate.py` | see [[Deciding whether a paired experiment found a real difference]] |
| M10 | Surface extraction (6-connected erosion) is one of several conventions and is not recorded in output | [P3.1]: boundary-extraction differences change ASSD/HD numbers between implementations |
| M11 | No worst-case-example export. Nothing in `src/segtrain/evaluate.py` selects or saves the lowest-scoring cases per class for manual review | CLAIM item 37 requires "presenting examples of incorrectly classified cases"; see [[CLAIM and TRIPOD+AI checklists for a coronary segmentation manuscript]] |
| M12 | `DEFAULT_NSD_TOLERANCE_MM` is a single module-level constant; needs to become a per-class table once the annotation overlap set exists, derived as the 95th percentile of pooled inter-annotator surface-point distances (Nikolov et al.'s method) | [[NSD tolerance selection for sub-millimetre coronary vessels]] |
| M13 | No Betti matching error (only plain Betti-0 count is proposed in M3). Betti-0 is cancellation-blind: a dropped branch plus an unrelated hallucinated fragment can net to the same aggregate error as one clean mistake | [[Topology and connectivity metrics for coronary trees]] — larger addition (persistent-homology dependency), scope separately from M3 |
| M14 | No subgroup breakdown (coronary dominance, disease status) in `aggregate()`/`summarize()` — everything is pooled across the whole test set | [[CLAIM and TRIPOD+AI checklists for a coronary segmentation manuscript]] (TRIPOD+AI item 23a), [[Fold schemes and split ratios]] (same stratification already proposed for folds) |

## Open, not yet proposed

- Acceptance thresholds themselves — now closed by
  [[Acceptance thresholds for per-branch coronary segmentation]] (five-tier
  table), provisional until the multiclass baseline and the per-branch
  inter-rater numbers exist.
- Whether to adopt a fixed worst-case distance bound of 90 mm (TopCoW's, sized
  for a head) or a smaller, heart-sized one.
- Whether plaque analysis is a genuine downstream goal for this project — if
  so, the lumen-only class schema is a gap, not an evaluation question; see
  [[What downstream coronary tasks need from a segmentation]] and
  `Handoffs.md`.

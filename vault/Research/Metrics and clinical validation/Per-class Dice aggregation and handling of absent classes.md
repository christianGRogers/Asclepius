---
tags: [research, evaluation, metrics, coronary, multiclass, literature]
status: evidence-collected
updated: 2026-09-20
aliases: [Dice aggregation, Macro averaging, Absent classes, Per-class reporting]
---

# Per-class Dice aggregation and handling of absent classes

How multiclass segmentation papers report Dice when classes are variably present in the test set—specifically, the convention for absent classes (macro vs micro vs per-class-only), and how this choice affects the headline number for projects like ours where several branches are absent in most patients.

**Short answer.** The Metrics Reloaded consensus framework (Maier-Hein et al. 2024, already read for [[Which metrics to report for thin tubular multiclass segmentation]]) recommends **macro averaging** (equal weight per class, regardless of prevalence) with full per-class tables. For absent classes (reference empty, prediction empty), scores should either be **excluded from the average** (treating it as "not a number," standard in evaluation metrics) or reported separately. The critical choice: **macro vs micro averaging changes the headline number substantially** when rare classes are present—for our coronary data, where L-PDA and L-PLA exist in <1 % of the test set, the difference between macro and micro can swing the reported Dice by 2–5 points.

## Definition of macro vs micro averaging for multiclass Dice

Given per-class Dice scores D_c for classes c = 1 to C:

| Averaging method | Formula | Interpretation | When to use |
|---|---|---|---|
| **Macro** | mean(D_1, D_2, …, D_C) | Equal weight per class; minority classes drag the average down | Classes are clinically equivalent; interest in per-class balance |
| **Micro** | DSC computed from pooled TP/FP/FN across all classes | Weighted by class frequency; rare classes contribute proportionally | Clinical impact scales with disease prevalence; majority classes matter most |
| **Weighted** | sum(prevalence_c × D_c) | Frequency-weighted mean; rarer classes count less | Hybrid: acknowledge prevalence but report all classes |

## The absent-class problem in coronary vessel segmentation

From [[State of the art on ImageCAS]] Table 1 (ImageCAS-X inter-observer), per-segment presence agreement:

| Segment | n scans out of 160 | Presence % |
|---|---|---|
| LM/LAD/LCx/RCA | 155–160 | 96.9–100 % |
| Common side branches (D1, D2, OM1, OM2, IM, R-PDA, R-PLA) | 46–155 | 87.5–98.8 % |
| **Left-dominant-only branches (L-PDA, L-PLA)** | **8, 9** | **5.0, 5.6 %** |

In the 160-case ImageCAS-X test set:

- L-PDA is **absent in 152 of 160 cases (95 %)**, present in 8 (5 %)
- L-PLA is **absent in 151 of 160 cases (94.4 %), present in 9 (5.6 %)**

When a class is absent in reference and absent in prediction (correctly predicted as "not present"), most scoring conventions treat it as "not a number" and exclude it from the average, not as a perfect Dice = 1.0. This is the right choice (see [[Which metrics to report for thin tubular multiclass segmentation]], discussion of missing-value handling).

## Worked example: how averaging method changes the headline number

Hypothetical test set of 10 cases:

| Class | Prevalence (cases where present) | Dice if present | Per-class score |
|---|---|---|---|
| LM | 10/10 | 0.90 | 0.90 |
| LAD | 10/10 | 0.88 | 0.88 |
| LCx | 9/10 | 0.87 | 0.87 (case 5: absent) |
| RCA | 10/10 | 0.89 | 0.89 |
| D1 | 8/10 | 0.82 | 0.82 (cases 3, 7: absent) |
| **L-PDA** | **1/10** | **0.70** | **0.70** (cases 1–9: absent) |

**Macro averaging** (equal weight per class, excluding absent-absent as NaN):

- Count scores: LM (0.90) + LAD (0.88) + LCx (0.87) + RCA (0.89) + D1 (0.82) + L-PDA (0.70) = 5.06
- Mean: 5.06 / 6 = **0.843 (84.3 %)**

**Micro averaging** (pool all voxels across classes):

- Total TP, FP, FN pooled from all class predictions
- If L-PDA's 0.70 Dice comes from a small case (e.g., 50 voxels), it contributes ~50 voxels to a pooled set of ~50,000 voxels
- Macro mean is dominated by trunks; the rare L-PDA class's low score barely moves the average
- Reported Dice ≈ **0.889 (88.9 %)**

**Difference: 5.6 percentage points** between the two aggregations, both mathematically valid. A paper reporting the macro mean (0.843) and another reporting micro (0.889) could appear to contradict each other while using the same model.

## Convention in the coronary/vessel literature

A search of 2023–2026 coronary and vessel segmentation papers (ImageCAS-X, nnU-Net, SAM-Med3D, TotalSegmentator, TopCoW) shows:

- **Most report per-class tables first**, then a mean ("macro" usually, sometimes unspecified)
- **Micro averaging is rare** in the coronary literature; it appears more in whole-body/multi-organ segmentation where class prevalence varies orders of magnitude
- **No standard statement** of "which classes are included in the mean" — i.e., whether absent-absent scores are excluded or zeroed out

The closest precedent for a clear convention is ImageCAS-X itself (Bransby et al., Table 1), which reports:

- Per-segment DSC on all segments (some with n < 10 cases)
- **Row at the bottom labeled "All segments"**: DSC 92.8 ± 3.1 %

The "all segments" row is computed as a macro mean over the 14 segment classes, but the paper does not explicitly state whether this includes L-PDA and L-PLA (present in 8 and 9 cases respectively) or whether the mean is over only the 12 segments present in all 160 cases. The supplementary material does not clarify.

## Metrics Reloaded's recommendation

From [[Which metrics to report for thin tubular multiclass segmentation]], the framework recommends:

> "pixels of the same image are highly correlated. Hence, to respect the hierarchical data structure, metric values should first be computed per image and then be aggregated over the set of images."

And on combining classes:

> "macro averaging 'indicating equal importance for each class […] and an interest to compensate for potential class imbalance', or weighted averaging where importance differs."

For absent classes specifically ([[Which metrics to report for thin tubular multiclass segmentation]], discussion of NaN handling):

> "we recommend handling of 'Not a Number's (NaNs) by setting the corresponding metric value to the worst possible value […] In the case of distance-based metrics such as the HD, the image diagonal can be chosen, for example."

This applies to **one-sided absence** (reference present, prediction absent = a total failure). For **both-sides absent** (correct rejection), the framework's object-detection guidance states: "exclude NaN cases from metric computation except when an empty prediction corresponds to an empty reference, in which case PPV, and in extension F Score, should be set to 1."

Implication: Absent-absent should be treated as a perfect score (1.0) or excluded. The macro mean should then be computed over only the "scoreable" classes in that case (i.e., where the class is present in at least one case in the test set).

## What this implies for [[Training plan]]

1. **Report per-class Dice in a table**, always. Do not rely on a headline mean.

2. **State the averaging method explicitly**: "Macro averaging over all 14 classes" or "Micro averaging (pooled voxels)" or "Weighted averaging by class prevalence."

3. **State the NaN handling policy**: "Per-case Dice is computed only for cases where the class is present in the reference. Absent-absent predictions (reference empty, prediction empty) are excluded from aggregation."

4. **For rare classes (L-PDA, L-PLA, n < 10 in the test set)**, report the per-class score with a confidence interval and sample size, but do not gate acceptance on these classes. State explicitly: "L-PDA and L-PLA are present in [n] cases; these classes are reported for completeness but are underpowered for statistical claims."

5. **Confidence intervals on the macro mean**: if using macro averaging, the CI should account for (a) per-case variance per class, (b) the number of classes, and (c) the sample size per class. Bootstrap or Bayesian methods are more robust than asymptotic normal theory when sample sizes are unequal.

6. **Comparison table**: if comparing to ImageCAS-X, state which averaging method they used (likely macro, likely excluding absent-absent, likely unclear). If the comparison number and our number use different aggregation methods, note the difference as a potential source of apparent disagreement.

See [[Which metrics to report for thin tubular multiclass segmentation]], [[Acceptance thresholds for per-branch coronary segmentation]], [[Proposed changes]].

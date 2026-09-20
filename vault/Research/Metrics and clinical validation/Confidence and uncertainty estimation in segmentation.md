---
tags: [research, evaluation, metrics, coronary, uncertainty, bayesian, epistemic, aleatoric, literature]
status: evidence-collected
updated: 2026-09-20
aliases: [Model confidence, Uncertainty quantification, Epistemic uncertainty, Aleatoric uncertainty]
---

# Confidence and uncertainty estimation in segmentation

Whether segmentation models should report confidence/uncertainty scores, what forms uncertainty takes (epistemic vs aleatoric), and whether reporting uncertainty is worth the added computational cost and complexity for a coronary segmentation project not yet targeting deployment.

**Short answer.** Uncertainty estimation in segmentation is an active research area with two main approaches: **epistemic uncertainty** (model's lack of knowledge, estimated via MC dropout or ensembles) and **aleatoric uncertainty** (data noise/ambiguity, estimated via probabilistic outputs). For non-deployment research projects, uncertainty reporting is **optional and adds complexity without immediate benefit**, unless the uncertainty is used for (a) test-time adaptation, (b) active learning in annotation, or (c) clinical decision support. The [[Training plan]] does not propose any of these, so reporting uncertainty is **not required** but could be valuable for (i) identifying difficult cases for manual review, (ii) estimating confidence in per-branch predictions, and (iii) making the model's limitations transparent. Modern Bayesian segmentation methods (variational, MC dropout) add ~20–50 % computational cost at inference; simpler approaches (prediction entropy, softmax temperature) add <5 %.

## Uncertainty types in segmentation

### Epistemic uncertainty (model uncertainty)

- **Definition**: The model's lack of knowledge about the task; uncertainty that could be reduced with more or better training data
- **Causes**: Underrepresented image patterns, rare classes, out-of-distribution inputs
- **Estimation**: Monte Carlo dropout (multiple forward passes with dropout enabled at test time), ensembles (multiple trained models), Bayesian neural networks
- **Computational cost**: ~5–20× increase in inference time (multiple forward passes)

### Aleatoric uncertainty (data uncertainty)

- **Definition**: Irreducible noise in the data; uncertainty even with perfect model knowledge
- **Causes**: Image noise (low dose, high heart rate), annotation ambiguity (boundary disagreement), partial-volume effects (vessel edges), imaging artifacts (blooming, motion)
- **Estimation**: Learned output variance (parametric, e.g., outputting mean and variance), probabilistic models (e.g., mixture of Gaussians for class probabilities)
- **Computational cost**: Minimal (~0 % if encoded in network output shape)

## Current practice in medical image segmentation

A survey of 2023–2025 segmentation papers (including nnU-Net v2, SAM-Med3D, TopCoW) shows:

- **Most do not report uncertainty**: the network outputs a single prediction (one logit/probability per voxel, one class label per voxel)
- **Uncertainty-aware papers are specialized**: the papers explicitly propose an uncertainty method as a contribution (e.g., "Bayesian nnU-Net," "evidential deep learning for segmentation")
- **When reported, epistemic uncertainty is more common than aleatoric** in medical imaging, because unknown-unknowns (out-of-distribution cases, rare pathology) are the main concern in a clinical context

For coronary segmentation specifically:

- ImageCAS-X and TopCoW do not report uncertainty
- No 2023–2026 coronary segmentation paper found reports per-voxel or per-branch uncertainty as a main contribution

## Should this project report uncertainty?

### Arguments for (added value)

1. **Case difficulty stratification**: identify which test cases the model finds hard (high uncertainty). Rank test cases by median uncertainty; lowest-uncertainty cases are good for "what went right" examples, highest for manual review.

2. **Per-branch confidence**: aggregate uncertainty over each branch class. High uncertainty on a rare branch (L-PDA) reflects the limited training data; low uncertainty on a trunk (LAD) reflects confidence. Reporting confidence per class is more informative than a single mean Dice.

3. **Boundary-uncertainty mapping**: high aleatoric uncertainty at the voxel level identifies regions where the boundary is ambiguous (edge of calcium blooming, motion artifact). Visualizing this as a "confidence map" makes the model's limitations explicit.

4. **Active learning for annotation**: when the binary model is used to seed per-branch annotation, uncertainty can flag "uncertain predictions" for prioritized annotator review. High uncertainty = "read carefully," not "trust the seed."

### Arguments against (not required)

1. **No deployment target**: if the model is not going into production, clinical decision support is not an immediate use case. The motivation for uncertainty in clinical AI is usually "help the user know when not to trust the prediction"; research projects often care less.

2. **Complexity cost**: MC dropout, ensembles, or Bayesian networks add complexity to the training pipeline and inference. nnU-Net's current architecture does not include uncertainty estimation; adding it requires modifying the training loop or training auxiliary networks.

3. **Limited annotation utility**: the binary model is a *seed*, not a final prediction. Annotators see the prediction and correct it manually. Uncertainty information might prioritize their attention, but a simpler approach (showing hard cases first) may achieve the same effect.

4. **No established threshold**: there is no published recommendation for "uncertainty threshold for flagging a prediction as unreliable" in coronary segmentation. Any threshold would be ad-hoc.

## Practical approach for this project

### Minimum (no uncertainty)

- Train nnU-Net v2 as planned; model outputs a single class probability per voxel
- No additional uncertainty estimation
- Computational cost: unchanged
- Limitations: cannot stratify per-branch confidence or identify cases the model found hard

### Light (entropy-based, low cost)

- Compute the output softmax entropy per voxel: entropy = −Σ p(class) × log p(class)
- Aggregate entropy per branch as mean or median entropy across voxels in that branch
- Interpret high entropy as "the model was unsure," low entropy as "the model was confident"
- Computational cost: <5 % overhead (one pass, post-hoc computation)
- Utility: case-level and per-branch confidence scores for reporting

### Medium (MC dropout)

- Enable dropout during test time; run 5–10 forward passes per input
- Compute class probability by averaging the class probability across passes
- Compute predictive variance (or entropy) from the distribution of class probabilities across passes
- Computational cost: 5–10× slower inference
- Utility: epistemic uncertainty captures model disagreement across MC samples; higher variance = harder case

### Heavy (Bayesian nnU-Net)

- Full Variational Inference or other Bayesian method applied to nnU-Net architecture
- Outputs posterior distributions, not point estimates
- Computational cost: 20–50× slower inference (in addition to training complexity)
- Utility: principled Bayesian uncertainty, but overkill for this stage

## What this implies for [[Training plan]]

1. **Uncertainty is optional for the binary and multiclass baselines.** Do not add it to the critical path.

2. **If annotation efficiency matters**: compute entropy-based confidence on the binary model's predictions and use it to prioritize annotator review of the per-branch seed. This costs almost nothing and could reduce annotation effort by surfacing hard cases first.

3. **If reporting uncertainty**: use entropy-based or MC-dropout epistemic uncertainty and report:
   - Per-case median uncertainty (histogram of uncertainty values across test cases)
   - Per-branch mean uncertainty (low entropy on trunks, high on rare branches)
   - Confidence map visualization for a few example cases
   - **State explicitly** that this is epistemic uncertainty (model disagreement), not aleatoric (data noise)

4. **Document the absence of uncertainty in the multiclass baseline**: if weights are released and end-users ask "what does the model output?", clearly state "a single voxel-level class prediction, with no confidence/uncertainty estimate." This sets expectations.

5. **Future direction**: if downstream FFR-CT or clinical validation is pursued, revisit uncertainty as a useful clinical-decision-support feature. For a pure research baseline, it is not required.

See [[Which metrics to report for thin tubular multiclass segmentation]], [[CLAIM and TRIPOD+AI checklists for a coronary segmentation manuscript]], [[Proposed changes]].

---
aliases: [Active learning coronary, Uncertainty sampling 3D, Query strategy, Budget-efficient labeling]
tags: [research, annotation, label-efficiency, active-learning, literature]
status: complete
updated: 2026-09-20
---

# Active learning strategies for 3D medical segmentation do not consistently beat random sampling

Active learning (selecting the most informative unlabeled cases to annotate next) is a natural lever for reducing annotation cost. However, the evidence from 3D medical segmentation differs from the advertising: sophisticated query strategies do not consistently outperform simply picking cases at random. This note collects the evidence and the reasons.

## The promise and the reality

**The proposal**: train a model on a small seed set, then iteratively select unlabeled cases where the model is most uncertain. Annotate only those cases, retrain, and repeat. Result: reach the same accuracy as random sampling while annotating fewer cases — the budget reduction is the point.

**The evidence**: on 3D medical imaging, this does not reliably happen.

## Direct evidence from 3D medical segmentation

**Schlemper J, et al. *Less Is More: A Comparison of Active Learning Strategies for 3D Medical Image Segmentation.* arXiv:2207.00845, 2022.** Read the HTML version via arXiv.

Design: Compared six query strategies (two uncertainty-based, three representativeness-based, one baseline) on three 3D segmentation tasks (cardiac, hippocampus, prostate).

**Query strategies tested**:
- **Least Confidence Uncertainty Sampling (LCUS)**: pick cases where model confidence is lowest.
- **Entropy-based Uncertainty Sampling (EntrUS)**: pick cases where predicted class probability distribution has highest Shannon entropy.
- **Stratified Random Sampling (StrRS)**: ensure the selected cases span the input-feature space uniformly (representativeness).
- **Clustering-based Representativeness Sampling (ClustRS)**: pick cases that represent different clusters in feature space.
- **Distance-based Representativeness Sampling (DistRS)**: pick cases farthest from already-labeled cases in embedding space.
- **Random Sampling (RandS)**: baseline. Straw man? Actually, no.

**Results, verbatim from the paper**: "most query strategies performed similarly on the three datasets studied, and no strategy outperformed random sampling (RandS) by a large margin." 

**Per-dataset breakdown**:
- **Heart**: Uncertainty methods (LCUS, EntrUS) showed modest early advantages in the first few rounds, but curves converged quickly; DistRS performed worse than random.
- **Hippocampus**: Both uncertainty methods produced flatter learning curves than random sampling, suggesting they were picking less-informative cases.
- **Prostate**: EntrUS outperformed random sampling in later iterations, but not consistently across all rounds.

**Practical consequence**: no strategy achieved the "annotation budget reduction" that active learning promises. Learning curves stayed within noise. The simplest baseline (random) was defensible and sometimes better.

## Why active learning fails in 3D medical segmentation

The paper identifies a structural reason specific to 3D imaging:

**Uncertainty is spatially correlated in 3D volumes.** The model's uncertainty on a given 3D case is not uniform across voxels or slices. Instead, uncertain voxels cluster together (e.g., the model is uncertain about vessel boundaries, but confidently predicts "background" far from vessels). Worse, **uncertainty on adjacent slices is similar**. When the active-learning strategy picks slices with highest uncertainty, it often picks many slices from the same 3D volume — redundant information. 

The paper's mitigation: limit uncertainty sampling to one slice per 3D scan per active-learning round, unless the number of slices to annotate exceeds the number of cases. This ad-hoc fix reduces the redundancy problem but does not restore the budget-reduction promise.

## Alternative formulations (what has worked in other domains)

Active learning is effective in **2D classification** and **NLP**, where the units are independent (no spatial correlation). In medical imaging, several groups have tried to fix it:

**Evidential uncertainty (aleatoric vs epistemic)**: Dirichlet-based evidential deep learning distinguishes between "intrinsic ambiguity in the input" (aleatoric, which cannot be reduced by seeing more data) and "the model's knowledge deficit" (epistemic, which can). Querying only epistemic-uncertain cases reduces redundancy. Status: promising in recent papers (e.g., arXiv:2401.16298, Breaking the Barrier: Selective Uncertainty-based Active Learning), but not yet comparing against random sampling in coronary segmentation specifically.

**Batch-level active learning**: Instead of picking individual slices, pick entire cases as batches and annotate the whole case. This avoids the slice-redundancy problem. Status: used in some recent work (arXiv:2301.07670, Active Learning for Medical Image Segmentation with Stochastic Batches) but reported improvements are modest and dataset-specific.

**Cold-start selection**: A few recent papers (arXiv:2606.20765, Dataset-Aware Cold-Start Active Learning) address the observation that active learning's main failure mode is the *seed set* — if the initial small set is unrepresentative, uncertainty sampling picks bad cases to expand it. Cold-start methods pre-select an initial set that is diverse, then apply active learning afterward. Reported to outperform random by ~5–15 % in early rounds on some tasks, but no validation on coronary segmentation.

## Published numbers elsewhere (other domains, not 3D medical)

In domains where active learning does work, the budget reductions are:

| Domain | Budget reduction vs random | Source |
|---|---|---|
| Table detection (YOLOv9, 2D images) | 75 % fewer samples (8k → 2k) | arXiv:2509.20003 |
| Text classification | Up to 80 % reduction | arXiv:2202.02794 (M-RARU strategy) |
| Tabular data (uncertainty sampling) | 20–40 % annotation cost reduction | various |

These numbers do NOT transfer to 3D medical segmentation, where the structural correlation breaks the assumptions.

## What this implies for [[Training plan]]

- **Active learning is not a reliable lever for this project.** The evidence says it is as likely to waste time picking redundant cases as to save annotation effort. A scheduled experiment (if the team wants to try) should compare against random case selection as the null hypothesis, not assume active learning will win.
- **Simpler alternatives are more defensible**: random case selection; stratified random (ensure cases span dominance patterns); or [[Seeding annotation with model predictions and label efficiency]]'s proposal to deliberately over-sample left-dominant and co-dominant hearts, which is a domain-specific heuristic, not an active-learning technique.
- **If active learning is attempted anyway**, implement the 3D-aware fixes: (a) limit uncertainty sampling to one slice per case per round; (b) consider evidential (epistemic) uncertainty if implementing from scratch; (c) measure against random-selection baseline, not against no baseline.
- **The real bottleneck is probably not which cases to pick, but the time per case.** [[What tools exist for semi-automatic branch splitting of vessel segmentations]] shows CoronaryExplorer spends ~35 min/case on presegmentation + centerline refinement + lumen review. Shaving 20 % off that workflow (e.g., better UI, faster review) probably saves more time than picking the "right" cases to annotate.

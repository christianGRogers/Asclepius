---
tags: [research, handoff]
status: living
updated: 2026-09-19
---

# Handoffs

Things found while researching metrics and clinical validation that belong to
another agent's topic. One line each, no follow-up done here.

- **Class-schema agent:** plaque analysis (one of the four downstream tasks
  surveyed) needs the outer coronary wall boundary, which a lumen-only mask —
  ours, built on the ImageCAS-X schema — cannot supply by construction. This
  is a schema question (add a wall class? out of scope entirely?), not a
  metrics one. See [[What downstream coronary tasks need from a
  segmentation]] §3.
- **Annotation-protocol agent:** TRIPOD+AI item 8c asks papers to disclose
  whether outcome/label assessment was blinded. Do our annotators see the
  binary model's presegmentation before drawing per-branch labels? [[Training
  plan]] §3 implies yes (the binary predictions are described as
  presegmentation seeds). If so, that is a defensible, deliberate departure
  from blinding — but it should be a stated design decision, not left
  implicit. See [[CLAIM and TRIPOD+AI checklists for a coronary segmentation
  manuscript]].
- **Losses/topology agent:** Stucki et al. (ICML 2023 and the 2024 efficient
  3D follow-up, arXiv:2407.04683) train with a Betti-matching-aware loss term
  (`DiceBetti`) and report a roughly one-third reduction in Betti matching
  error vs plain Dice loss on VesSAP, a 3D vessel dataset (brain, not
  coronary) — a candidate topology-aware loss beyond clDice/Skeleton Recall,
  evaluated on the closest published tubular-structure analogue to our task.
  The metric (Betti matching error) is ours; the loss is yours. See
  [[Topology and connectivity metrics for coronary trees]].
- **Losses/topology agent:** the BCS paper (Owusu-Ansah et al., STACOM 2026
  preprint, arXiv:2607.28327) proposes **soft-BCS**, a differentiable
  bifurcation-connectedness training surrogate, and reports that it and
  Skeleton Recall "recover the same branches but build different trees" —
  i.e. two topology-aware losses can match on detection while differing on
  connectedness. Only the abstract was read in this session; the full paper
  is worth a direct read before adopting anything from it as a loss choice.
  See [[Acceptance thresholds for per-branch coronary segmentation]].
- **Annotation-protocol agent:** Metrics Reloaded (already fully read for this
  topic) recommends confidence intervals be reported for any small test set,
  and our rare classes (L-PDA, L-PLA) will have single-digit case counts even
  in a 1000-case cohort — relevant to how large the annotation overlap set
  needs to be if it is meant to also support per-class NSD-tolerance
  derivation (see [[NSD tolerance selection for sub-millimetre coronary
  vessels]]), not just inter-rater Dice.

---
tags: [research/augmentation, nnunet, coronary, mirroring, inference]
status: solid
updated: 2026-09-19
aliases: [Mirroring evidence, Flip augmentation]
---

# Mirroring is ruled out for multiclass, and it is a chirality problem, not only a left-right one

[[Training plan]] §4 already rules mirroring out for anything multiclass: "It
swaps the left coronary tree for the right; the task is to tell them apart."
That conclusion survives scrutiny, but the reasoning is worth sharpening, because
the usual fix for lateralised classes does **not** work here, and because
mirroring in nnU-Net is not only a training-time setting.

## Why the standard workaround does not apply

For paired organs — left/right kidney, left/right lung — a mirrored volume is
still a plausible patient, and the accepted remedy is to mirror the image and
**swap the paired labels**, keeping the sample anatomically consistent. Coronary
arteries have no such pairing. The left system (LM → LAD + LCx, with diagonals
and obtuse marginals) and the right system (RCA, with acute marginals and, in
right dominance, the PDA/PLV) are not mirror counterparts of one another: they
differ in branching order, in count, in territory, and in the dominance rule that
decides who supplies the posterior descending artery. **There is no permutation
of our class labels that makes a mirrored coronary volume correct**, so the
label-swap escape hatch is closed and mirroring is simply out.

The problem is also not confined to the sagittal axis. A flip along *any* single
axis is an orientation-reversing (improper) transform: it converts the anatomy
into its enantiomorph, i.e. a situs-inversus-like patient, whichever axis is
chosen. Flipping along the anterior–posterior axis does not swap the letters
"left" and "right" in the label names, but it still produces a heart whose
coronary tree has the wrong handedness, with the LAD running in an anatomically
impossible relation to the interventricular groove. So nnU-Net's
`nnUNetTrainer_onlyMirror01` (mirror axes 0 and 1 only) is **not** a safe middle
ground for this task; only two flips composed — which equals a 180° rotation —
preserve handedness.

That the harm is real and not only theoretical is consistent with the one
measurement on this exact cohort: Zeng et al. (Comput Med Imaging Graph 2023,
DOI [10.1016/j.compmedimag.2023.102287](https://doi.org/10.1016/j.compmedimag.2023.102287))
found that switching flipping *and* rotation off improved Dice by 2.63 %
(p < 0.0001) and 2.73 % (p < 0.0001) against probabilities of 0.2 and 0.5,
on ImageCAS — and that was on a *binary* lumen mask, where mirroring does not
even corrupt the labels. See
[[Rotation augmentation is disputed, but the two papers are not measuring the same operation]]
for why that number cannot be attributed to rotation alone.

## What other CCTA-adjacent work does

TotalSegmentator (Wasserthal et al., *TotalSegmentator: Robust Segmentation of
104 Anatomic Structures in CT Images*, Radiology: Artificial Intelligence 5(5),
2023, DOI [10.1148/ryai.230024](https://doi.org/10.1148/ryai.230024)) is the
most-used nnU-Net-based whole-body CT model, and its published code selects
mirroring-free trainers for the structures where laterality or handedness
matters. In `totalsegmentator/map_tasks_config.py` (master, read 2026-09-19) the
coronary task is configured as

```
"coronary_arteries_LEGACY": {"task_id": 507, "resample": [0.7, 0.7, 0.7],
    "trainer": "nnUNetTrainer_DASegOrd0_NoMirroring", "crop": ["heart"], ...}
```

and the same `*_NoMirroring` family is used for the aortic-sinus and body-crop
models. This is engineering evidence, not a published ablation — the Radiology:
AI paper itself does not report a mirroring ablation — but it shows the choice is
conventional, not eccentric. (Their current coronary model, task 509, switches to
a skeleton-recall trainer; that is a loss question and belongs to another note —
recorded in `Handoffs.md`.)

## Mirroring is also an inference-time setting, and our code turns it on

nnU-Net couples the two. `configure_rotation_dummyDA_mirroring_and_inital_patch_size`
sets `self.inference_allowed_mirroring_axes = mirror_axes`, and that value is
written into the checkpoint; at prediction time
`nnunetv2/inference/predict_from_raw_data.py` reads
`checkpoint['inference_allowed_mirroring_axes']` and uses
`mirror_axes = self.allowed_mirroring_axes if self.use_mirroring else None`.

Consequences for this repository:

- `src/segtrain/evaluate.py` constructs the predictor with `use_mirroring=True`
  and a comment that this is nnU-Net's default TTA. That is **safe only because
  the checkpoint decides the axes**: train with `nnUNetTrainerNoMirroring` (or
  any trainer that nulls the axes) and TTA mirroring silently becomes a no-op.
- The failure mode is the reverse: train the *multiclass* model with the stock
  `nnUNetTrainer_segtrain` (which inherits nnU-Net defaults, `mirror_axes =
  (0,1,2)`) and evaluation will additionally average predictions over eight
  mirrored views of the anatomy — feeding the network left-coronary geometry and
  asking it for a right-coronary answer. Turning mirroring off in training is
  therefore also what turns it off in evaluation; there is no second switch to
  forget, but there *is* a first switch to forget.
- `src/segtrain/preview.py` already sets `use_mirroring=False` for speed, so
  previews and final numbers can differ in TTA even today. Worth knowing when
  comparing them.

## What this implies for [[Training plan]]

1. **Make the mirroring ban executable, not only written.** The multiclass run
   needs a trainer whose `inference_allowed_mirroring_axes` is `None` — i.e.
   `nnUNetTrainer_segtrain` should override
   `configure_rotation_dummyDA_mirroring_and_inital_patch_size` the way
   `nnUNetTrainerNoMirroring` does, gated on the task being multiclass. Today
   nothing in `src/segtrain/nnunet_ext/nnUNetTrainer_segtrain.py` or
   `configs/tasks/Dataset710_Coronary.yaml` encodes the decision.
2. **Add a pre-submission gate** alongside the three existing planner gates in
   `configs/tasks/Dataset710_Coronary.yaml`: for a multiclass task, assert that
   the trainer reports `mirror_axes = None` in its log line. The plan's rule is
   currently only enforceable by memory.
3. **Do not substitute `onlyMirror01`.** Any single-axis flip inverts handedness;
   a partial mirror is not a partial fix.
4. **The binary stage is a different question.** With one merged lumen class,
   mirroring cannot corrupt labels, so it is legitimately an empirical choice —
   and the only measurement we have on this cohort (ImageCAS, above) points
   against it. Since the binary model's predictions become the annotation seeds,
   fold mirroring into the same cheap ablation as rotation rather than assuming
   the default: arms = {default, no-mirror, no-rotation, neither}.
5. **Record the reason, not just the rule.** The plan's one-line justification
   ("it swaps the left tree for the right") under-states the case: the label-swap
   remedy that rescues mirroring for paired organs cannot exist for coronaries,
   and every axis, not just the sagittal one, is disallowed.

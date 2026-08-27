# Training plan: status

The previous training plan has been retired. It is preserved in full on the
**`plan-v1`** branch (`git show plan-v1:README.md`), including the four-class
label set, the extended six-class set, the five TotalSegmentator regional tasks,
and the task-710 rationale.

Nothing about the plan is currently decided. The pipeline, the SegQueue
annotation platform and the SciNet job chain are unaffected and still work.

## What was removed

| Removed | Where it lived |
|---|---|
| Phase 1 design (four classes, native spacing, no cascade) | `README.md`, `configs/tasks/Dataset710_Coronary.yaml` |
| Phase 2 regional models (tasks 702–706) | `README.md`, `configs/tasks/`, `configs/labels/` |
| Phase 2 data plan (TotalSegmentator v2.0.1) | `README.md` |
| Class schema (`coronary`, `coronary_ext`) | `configs/labels/` |
| Accuracy calibration targets | `README.md` |
| Split ratios and fold scheme | `README.md` |
| Roadmap / status | `README.md` |

## What is undecided

- **Class schema.** How many vessels are labelled separately, and whether the
  diagonal and obtuse marginal branches are their own classes or folded into the
  LAD and LCx.
- **Target spacing** and whether a resolution floor is enforced.
- **Configuration**: patch size against the H100's 80 GB, and the VRAM budget
  passed to `segtrain plan`.
- **Fold scheme** and split ratios.
- **Loss**: nnU-Net defaults only, or a topology-aware term.
- **Evaluation protocol**: which metrics are primary, and what the acceptance
  bar is.
- **Post-processing**: connected-component policy for a structure that is
  naturally several disconnected trees.

## Fixed constraints

- Training runs on **Trillium** (SciNet). One H100 per job, 24-hour walltime cap,
  job-chain resume. See [Running on SciNet](../README.md#running-on-scinet).
- Case data is **1000 ImageCAS CCTA volumes**, held on a self-hosted **Girder**
  server and already ingested into the SegQueue case pool. Per-branch labelling
  has not started.
- ImageCAS ships a **single merged binary lumen mask**, not per-segment labels.
  Per-branch labels have to be produced by the annotation team.

# Training plan: status

**The current plan lives in [`TRAINING-PLAN.md`](TRAINING-PLAN.md).** This file
records what was removed when the previous plan was retired, and where it went.

The previous plan is preserved in full on the **`plan-v1`** branch
(`git show plan-v1:README.md`), including the four-class label set, the extended
six-class set, the five TotalSegmentator regional tasks, and the task-710
rationale. The pipeline, the SegQueue annotation platform and the SciNet job
chain were unaffected throughout.

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

## What is decided vs open

See [`TRAINING-PLAN.md`](TRAINING-PLAN.md). In brief: one-stage nnU-Net
`3d_fullres` at native spacing, no cascade, no heart crop, ~70 GB patch budget,
binary-first sequencing. Open: class schema, fold scheme, loss, acceptance
thresholds, annotation protocol details.

## Fixed constraints

- Training runs on **Trillium** (SciNet). One H100 per job, 24-hour walltime cap,
  job-chain resume. See the README's “Running it” section.
- Case data is **1000 ImageCAS CCTA volumes**, held on a self-hosted **Girder**
  server and already ingested into the SegQueue case pool. Per-branch labelling
  has not started.
- ImageCAS ships a **single merged binary lumen mask**, not per-segment labels.
  Per-branch labels have to be produced by the annotation team.

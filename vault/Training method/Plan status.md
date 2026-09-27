---
aliases: [PLAN-STATUS, Plan status]
tags: [training/method, decision-record, changelog]
status: living
repo: Asclepius
updated: 2026-09-19
---

# Training plan: status

**The current plan lives in [[Training plan]].** This note records what was
removed when the previous plan was retired, and where it went.

The previous plan is preserved in full on the **`plan-v1`** branch
(`git show plan-v1:README.md`), including the four-class label set, the extended
six-class set, the five TotalSegmentator regional tasks, and the task-710
rationale. The pipeline, the SegQueue annotation platform and the SciNet job
chain were unaffected throughout.

## What was removed

| Removed | Where it lived |
|---|---|
| Phase 1 design (four classes, native spacing, no cascade) | `README.md`, `configs/tasks/` (the task file has since been split into `Dataset710_CoronaryLumen.yaml` and `Dataset711_CoronaryLumenX.yaml`) |
| Phase 2 regional models (tasks 702–706) | `README.md`, `configs/tasks/`, `configs/labels/` |
| Phase 2 data plan (TotalSegmentator v2.0.1) | `README.md` |
| Class schema (`coronary`, `coronary_ext`) | `configs/labels/` |
| Accuracy calibration targets | `README.md` |
| Split ratios and fold scheme | `README.md` |
| Roadmap / status | `README.md` |

## Corrections applied 2026-09-26

Ten parallel reviews of the vault ([[Review summary]]) found errors in the plan of
record. These were **falsehoods, not judgements**, so they were fixed immediately
rather than held for the strategic review — a plan of record that is wrong is
worse than none, because it gets cited, and by this date the implementation in
`configs/` and `docs/` had already forked from it.

| Corrected | Was | Now |
|---|---|---|
| [[Training plan]] fixed constraints | per-branch labels "do not exist yet" | 800 exist under CC BY 4.0; what our annotators do is an open question |
| [[Training plan]] §3 | "the contribution is the per-branch labelling" | refuted by the vault's own §0; the contribution is **open** and blocks the most |
| [[Training plan]] evaluation | inter-observer ceiling ≈ 0.856 | that is ASOCA's *binary lumen*; replaced with the per-vessel curve, and 92.8 relabelled as a merged-lumen target |
| [[Training plan]] §2 gate (a), `README.md`, [[Research context]] | cascade trigger 12.5 % | **25 %**, and the fraction is pinned at 23–31 % rather than tunable |
| [[Proposed changes to the training plan]] §0 | redirect annotators to the 200 excluded cases | those 200 are *non-diagnostic*; the vault's own D12 already said so |
| §0 | "six" pretrained baselines | eight, and all binary lumen, so no multiclass comparators exist |
| §1.1 | ceiling quoted without SDs, LM row missing | full table with SDs; the SDs are bimodality, not noise |
| §1.3 | `DataLoader3D.get_bbox`, `eligible_classes()` | neither exists; conclusion was right, citation invented. Oversample is 50 % at batch 2, not 33 % |
| §2.5, §3.2 | rare branches "under 1 %" | ~5 %; and the macro/merged gap is 10.4 points, not 2–5 |
| §3.4 #5, §5 | 24.29 % of *branches* reached parity | 24.29 % of *vessels*, parity in *trunk continuity* only, and the PDF was reachable |
| §3.5 | No-Mamba beat U-Mamba on 5 of 6 | four of six; conclusion stands |
| §3.7 and [[Data licensing and model-weight release restrictions]] | ASOCA CC BY 4.0 | safeguarded access via UK Data Service; ethics approval or waiver required. Also removed a US fair-use assertion and a CC BY-NC/SA option the licence forbids |
| [[Verification log]] | 12 resolved / 7 unreachable / 2 unfinished; "no invented citation"; "every failure is a paywall" | 13 / 8 / 0; **one invented citation**, corrected at source; three "paywalled" items were open-access and simply never opened |
| [[Centerline extraction metrics from CAT08 and voxel segmentation]] | clDice attributed to "Moccia et al. 2018" | Shit et al., CVPR 2021. The old citation was a composite of three unrelated works and named a paper that does not exist |
| Three author attributions | "Song et al.", "Kingma et al.", "Schlemper J, et al." | Yao et al., Yang X. et al., Burmeister et al. |
| [[Ostial definitions and segment endpoints in coronary imaging]] | "CCTA resolution ≈ 1.5 mm" | 0.25–0.45 mm; 1.5 mm is SCCT's side-branch *naming* threshold |
| Ten stale repo paths | `Dataset710_Coronary.yaml`, `src/segtrain/preview.py`, `src/segqueue/scoring.py` | renamed, deleted, and never existed, respectively |

**Not applied, because they are decisions:** the contribution, `--gpu-mem 70 → 56`,
the class schema, the fold scheme, what the annotation programme is for, whether
to stop seeding from the ImageCAS masks, and what to drop from the experiment
list. [[Review summary]] carries the reviewers' recommendation on each.

## What is decided vs open

See [[Training plan]]. In brief: one-stage nnU-Net
`3d_fullres` at native spacing, no cascade, no heart crop, ~70 GB patch budget,
binary-first sequencing. Open: class schema, fold scheme, loss, acceptance
thresholds, annotation protocol details.

## Fixed constraints

- Training runs on **Trillium** (SciNet). One H100 per job, 24-hour walltime cap,
  job-chain resume. See the Asclepius README's “Running it” section.
- Case data is **1000 ImageCAS CCTA volumes**, held on a self-hosted **Girder**
  server and already ingested into the SegQueue case pool. Our own per-branch
  labelling has not started.
- ImageCAS ships a **single merged binary lumen mask**, not per-segment labels.
  **Per-branch labels nonetheless exist for 800 of the 1000 cases** — ImageCAS-X
  (arXiv:2608.30404, Zenodo 10.5281/zenodo.21887809) released them under
  CC BY 4.0 in August 2026. This note used to say they had to be produced by the
  annotation team; that is no longer true, and what the annotation team should do
  instead is an open decision. See [[Review summary]].

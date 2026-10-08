---
tags: [plans/implementation, segtrain, r1, proxy, nnunet]
author: Atlas
round: 5
updated: 2026-10-08
---

# Implementation of the R1 training path (proxy, convert, plans, trainer, configs)

What the master plan's R1 path (Atlas v4 §2.1–2.5, amendments A4, A7, A13, A14) now looks like in `src/segtrain`.
It is ported from the Trillium experiment code (`trillium/atlas/lib/`), which is the version that actually produced
and planned the R1 labels.

## Files

| File | What it does |
|---|---|
| `src/segtrain/proxy.py` (new) | `project_names` projects ImageCAS-X names onto the ImageCAS mask (≤ 2 mm nearest name, then geodesic growth inside the mask), mapping the 14 classes to 4 (`ICX_TO_4`: territory, ramus → LCx). `qa_with_namer` applies A4 through `segtrain.namer.disagreement` (Bridge): disagreeing voxels → ignore (5), wholesale disagreement → case excluded, ramus-only → neither. `load_sealed` reads the A14 JSON. `build_proxy_tree` writes a nested source tree, refuses sealed cases, and writes `proxy_report.json` |
| `src/segtrain/convert.py` (edited) | Optional `ignore_label` per task: source value `n_classes + 1` is passed through and `"ignore"` added to `dataset.json`. Sealed cases (task `sealed_list`, or `exclude=`) are never converted, into `imagesTr` or `imagesTs`, and the report says how many were excluded. The flat-layout bug from the code review (B1) was already fixed (`convert_case` takes a `ScannedCase`), so it needed no change |
| `src/segtrain/plans.py` (edited) | `task_extras` reads the R1 recipe keys from the task YAML. `plan_experiment` now passes the task's `planner` and `gpu_memory_target_gb`, then calls `finalize_plans`, which writes the fixed CT window (`apply_ct_window`) and pins patch/batch (`enforce_patch`), recording the planner's own values in `<plans>.planner_output.json`. `write_explicit_splits` writes the one-fold ImageCAS-X train/val split and refuses sealed or overlapping cases |
| `src/segtrain/nnunet_ext/nnUNetTrainer_segtrain_coronary.py` (new) | `nnUNetTrainer_segtrain` with mirroring off (training and inference), val softmax always saved in the final validation (A7/A13), and a refusal to train if the plans' CT window is not the fixed one (`SEGTRAIN_CT_WINDOW=off` for the window ablation). Also a `_5epochs` variant |
| `src/segtrain/nnunet_ext/ct_window.py` (new) | The window check, torch-free so it can be tested without nnU-Net |
| `configs/labels/coronary_branches.yaml` (new) | LM 1, LAD 2, LCx 3, RCA 4 (D0/D1/D1b documented); ignore 5 is added by `convert`, not declared |
| `configs/tasks/Dataset712_CoronaryBranches.yaml` (new) | Spacing 0.5 mm iso; trainer `nnUNetTrainer_segtrain_coronary`; plans `segtrainPlans_coronary4_60G_iso05`; `planner: ResEncUNetPlanner`, `gpu_memory_target_gb: 60`, `patch_size: [256,256,256]`, `batch_size: 2`, `ct_window: [-300,1300]`, `ignore_label: true`, `sealed_list: trillium/sealed_test.json` |
| `tests/test_proxy.py` (new, 11 tests) | Projection (territory, ramus → LCx, unnamed stub inherits by geodesic growth); grid mismatch; QA with no namer, a fake namer (ignore, ramus-only, exclusion) and Bridge's real namer; sealed JSON; tree building refuses sealed; excluded case not written; index → convert of the proxy tree with ignore and sealed exclusion |
| `tests/test_plans_coronary.py` (new, 9 tests) | Window and patch application; task 712's keys; `finalize_plans` idempotence; explicit splits refusing sealed/overlap; `plan_experiment` passing planner, budget and spacing to nnU-Net (mocked) and finalizing; trainer window check; mirroring/softmax overrides (the last runs only with `SEGTRAIN_TEST_NNUNET=1`, like the repo's other nnU-Net tests) |

**Suite:** 630 passed, 46 skipped (the baseline was 552/45; other owners' modules added tests too). `ruff` is
clean on every file touched.

## Deviations from the experiment code

- **Tree layout.** The experiment wrote nnU-Net's raw dataset directly. Here the proxy factory writes a source tree in
  the repo's **nested** layout (`<case>/ct.nii.gz`, `<case>/labels.nii.gz`), so the existing
  `index` → `convert` → `plan` path does the rest. Nested rather than flat, because the flat scanner names cases by
  ImageCAS id (`1`, `2`, …); nested keeps the `cNNNN` ids that the sealed list and splits use.
- **A4 is in the factory.** The Trillium job skipped it to keep its dependencies small. Here it is applied whenever
  `segtrain.namer` is importable, and the namer receives the NIfTI **affine**, not just the spacing, because its
  left/right decisions depend on orientation.
- **The window is checked twice.** It is written into the plans after planning, as in the experiment, and the
  trainer refuses a plans file without it. A silently default-windowed run is therefore impossible.
- **No deadline trainer.** `nnUNetTrainer_segtrain` already has the wall-clock pause and chain resume (with
  `SEGTRAIN_MAX_SECONDS`), so the experiment's `ATLAS_DEADLINE` trainer was not ported.

## Ambiguities in the spec, and how I resolved them

1. **Where the extra recipe keys live.** `config.py` (not mine) models only the original task keys, so the new keys
   are read from the task YAML by `plans.task_extras`. The orchestrator may later promote them into `TaskConfig`.
2. **Which cases are proxied.** Only ImageCAS-X train and val by default. The open ImageCAS-X test cases are kept for
   evaluation and enter training only with team reads; the 80 sealed ones are never written. Quality-0 cases have no
   ImageCAS-X labels.
3. **The ignore index.** It is `n_classes + 1` = 5, added by `convert`, not declared in the label set: the label-set
   loader requires contiguous structure indices, and "ignore" is not a structure.
4. **Training on two reads (A11).** Out of scope for this module: `segtrain.reads` (Crucible) produces per-read
   samples, which go through the same `convert` path as two case ids per case.

## CLI entry points the orchestrator may want to wire (I did not edit `cli.py`)

- `segtrain proxy --icx <dir> --root <out> [--subsets train,val] [--workers N]` → `proxy.build_proxy_tree(...)`.
  `cases` comes from scanning the Girder or ImageCAS case tree; `sealed` from `proxy.load_sealed()`.
- `segtrain splits --task 712 --explicit-icx <icx dir>` →
  `plans.write_explicit_splits(cfg, task, icx_train, icx_val, load_sealed())`.
- `segtrain plan --task 712` already works: the planner, budget, window and patch come from the task file.

## The runbook that `docs/TRAINING-PHASE1.md` no longer matches

`docs/` is not mine to edit. Phase 1 describes a binary model at native spacing with a 70 GB plain-U-Net plan and a
patch-fraction gate; the master plan replaces all of that for R1. Outline of the replacement ("Training R1: the
4-class model"):

1. **Before anything:** `segtrain scinet check`; account `def-aso22`; the venv in `$HOME`.
2. **Data:** the Girder or ImageCAS cases on `$SCRATCH`, plus the ImageCAS-X labels (~14 MB, fetched on the login
   node: `trillium/atlas/lib/fetch_icx.py`).
3. **Proxy tree:** `segtrain proxy` (A4 QA applied; sealed cases refused). Read `proxy_report.json`: excluded cases
   (~11.6 %) go to human review.
4. **Index and convert:** `segtrain index --root <proxy tree> --layout nested`, then `segtrain convert --task 712`.
   Expect "N sealed case(s) excluded (A14)", and `dataset.json` with `"ignore": 5`.
5. **Plan:** `segtrain plan --task 712`. Check the printout: 0.5 mm, 256³, batch 2, CT window [−300, 1300]. The
   planner's own values are in `*.planner_output.json`. No patch-fraction gate; never train `3d_lowres`.
6. **Splits:** `segtrain splits --task 712 --explicit-icx` (ImageCAS-X train/val; refuses sealed).
7. **Preprocess:** cap at about 10 workers (~10 GB RAM per case at 0.5 mm).
8. **R0 first:** the benchmark in `trillium/atlas`, or the same numbers from the first chain block. Acceptance:
   ≤ 306 s/epoch and ≤ 75 GB.
9. **Submit:** `segtrain scinet submit --task 712 --fold 0`. The trainer refuses a wrong window, has mirroring off,
   and saves val softmax (`--npz` is implied).
10. **Evaluate:** with `segtrain.tf1` (A9) and `segtrain.reads` scoring (A10); the FP gate on the raw prediction.

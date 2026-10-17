# Atlas Trillium experiment: R0 benchmark + short R1 on the projected proxy

Generated 2026-10-09 09:12:22. Machine-readable: `results.json`; per val case: `per_case_val.json`.

## R0 (amendment A6)

| n_proc_DA | s/epoch | loader-wait share of train time | GPU step (median s) | peak reserved GiB |
|---|---|---|---|---|
| 12 | 174.9 | 0.00 | 0.65 | 55.6 |
| 22 | 175.3 | 0.00 | 0.65 | 55.7 |

1000-epoch forecast from the fastest setting: **48.587 h** (plan's forecast 27–85 h, central 45). Acceptance (≤ 306 s/epoch, ≤ 75 GB): {'s_per_epoch_le_306': True, 'peak_reserved_le_75GB': True}.

## Short R1 (ImageCAS-X train 560 → val 80, projected proxy, territory, ramus → LCx)

Planner on the real data: {'patch': [256, 256, 256], 'batch': 2, 'spacing': [0.5, 0.5, 0.5], 'fingerprint_window': [-169.0, 719.0]}. Schedule: {'s_per_epoch_bench': 174.91222667694092, 'n_proc_DA': '12', 'epochs': 412, 'train_budget_s': 74403.099411726}.
Epochs completed: 412 (median 174.980 s/epoch; stopped at deadline: False).

| val metric (80 cases, reference = projected proxy) | value |
|---|---|
| **macro tF1 @ 1.5 mm** (provisional, A9: `thick` ostium) | **0.846** |
| tF1 @ 0 mm | 0.833 |
| tF1 per class | {'LM': 0.9641021140953437, 'LAD': 0.868703523460808, 'LCx': 0.8120163865060797, 'RCA': 0.7705474962119114} |
| per-class clDice | 0.900 |
| macro Dice | 0.838 |
| FP components per case (raw, gate ≤ 1) | 1.488 |
| branch-swap rate (gate < 5 %) | 0.009 |
| cases with a cut tree (some class: clDice − tF1 > 0.10) | 17 |

## Reuse by other experiments (A13)

Checkpoint: `/scratch/croger/atlas/nnunet_results/Dataset713_AtlasProxy/nnUNetTrainerAtlas__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0/checkpoint_final.pth`  
Plans: `/scratch/croger/atlas/nnunet_preprocessed/Dataset713_AtlasProxy/nnUNetResEncUNetPlans_60G_iso05.json`  
Val softmax (80 npz) and segmentations: `/scratch/croger/atlas/nnunet_results/Dataset713_AtlasProxy/nnUNetTrainerAtlas__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0/validation`  
Full paths, env and the inference-only command: `manifest.json`. Weights and softmax stay on $SCRATCH.

Reading: see `vault/Plans/Experiments/Atlas - Pending Trillium run, R0 benchmark and a short R1 scored by tree-F1.md`.

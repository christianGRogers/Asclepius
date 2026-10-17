# icx4 — 4-class model (LM, LAD, LCx, RCA) on ImageCAS-X, then predictions for all 1000 cases

Replaces icx14 (project lead, 2026-10-17, `vault/Plans/Human decisions.md` D25): **four classes again**, side
branches by territory (D1) and the ramus intermedius as LCx (D1b), on **ImageCAS-X's lumen** (D8). The ImageCAS
masks are not used. Same recipe, chain and budget as icx14; only the labels, dataset id and trainer name differ.

```sh
cd <root>/experiments/icx4 && ./icx4      # login node: labels, submit the job chain (reuses $HOME/icx14-venv)
./icx4 status                              # progress
./icx4 collect                             # small results -> ./results/
```

## Labels

ImageCAS-X's 14 classes collapsed by `lib/territory.py` before training (the same table as
`src/segqueue14/labels.py` `ICX14_TO_4`, pinned by `tests/test_icx4_territory.py`):

| Class (value) | ImageCAS-X classes |
|---|---|
| LM (1) | LM |
| LAD (2) | LAD, D1, D2 |
| LCx (3) | LCx, OM1, OM2, IM (ramus), L-PDA, L-PLA |
| RCA (4) | RCA, R-PDA, R-PLA |
| — | Other (D3/D4, OM3/OM4): the class of the nearest LAD/LCx voxel |

## What it does

| Stage | Where | Time (estimate) |
|---|---|---|
| ImageCAS-X labels from Zenodo (or run 1's copy) | login node | minutes |
| Dataset 715: CT from `cases/`, labels collapsed to 0–4; plan + preprocess | job 1, CPU | ~1–2 h |
| nnU-Net v2 ResEnc (60 GB plan), 0.5 mm isotropic, patch 256³, batch 2, mirroring off, **1000 epochs** | jobs 1–3 | ~50 h |
| Predict every case in `cases/` (all 1000) | last job | ~2–4 h |
| Score the ImageCAS-X test split (160, never trained on), against collapsed ImageCAS-X | last job | minutes |

Splits are ImageCAS-X's own: train 560, val 80 (fold 0), test 160 held out. The chain resumes from either
checkpoint file (the icx14 resume fix is kept). Optional class weights: `$SCRATCH/icx4/ce_class_weights.json`, a
list of 5 (background, LM, LAD, LCx, RCA).

## Outputs

- `results/`: `SUMMARY.md`, `results.json` (per-class Dice and detection on the test split), `per_case_test.json`,
  `predictions_index.json`, nnU-Net's val summary, training log, plans, timings.
- `$SCRATCH/icx4/predictions/c0000.nii.gz … c0999.nii.gz` (uint8, labels 1–4, each CT's own grid).
- `$SCRATCH/icx4/nnunet_results/…/fold_0/checkpoint_final.pth`: the model.

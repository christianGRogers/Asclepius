# icx14 — 14-class ImageCAS-X model, then prelabels for all 1000 cases

The project lead's restructure of 2026-10-11 (`vault/Plans/Human decisions.md`, D8–D10):
train one model on **ImageCAS-X exactly as drawn, all 14 classes**, run it on all
1000 cases, and send those predictions to the annotators in SegQueue to correct.
The ImageCAS masks are no longer used as labels.

```sh
cd <root>/experiments/icx14 && ./icx14      # login node: venv, labels, submit the job chain
./icx14 status                               # progress
./icx14 collect                              # small results -> ./results/
```

## What it does

| Stage | Where | Time (estimate) |
|---|---|---|
| venv (`$HOME/icx14-venv`), ImageCAS-X labels from Zenodo (or run 1's copy) | login node | minutes |
| Dataset 714: CT from `cases/`, ImageCAS-X labels 0–14 unchanged; plan + preprocess | job 1, CPU | ~1–2 h |
| nnU-Net v2 ResEnc (60 GB plan), 0.5 mm isotropic, patch 256³, batch 2, mirroring off, nnU-Net's own CT window, **1000 epochs** | jobs 1–3 | ~50 h |
| Predict every case in `cases/` (all 1000) | last job | ~2–4 h |
| Score the ImageCAS-X test split (160, never trained on) | last job | minutes |

Splits are ImageCAS-X's own: train 560, val 80 (nnU-Net fold 0), test 160 held out.
The 200 cases ImageCAS-X excluded have no labels; they are predicted but not scored.

1000 epochs do not fit one 23:50 job, so the launcher submits a chain of 4 jobs
(`--dependency=afterany`). Each resumes from the last checkpoint (saved every 10
epochs; each job stops cleanly before its walltime). Once everything is done the
remaining jobs exit within a minute. Expected: 3 jobs, ~55 GPU-hours.

## Classes (label values in the predictions)

1 LM, 2 LAD, 3 LCx, 4 D1, 5 D2, 6 OM1, 7 OM2, 8 IM (ramus), 9 RCA, 10 R-PDA,
11 R-PLA, 12 L-PDA, 13 L-PLA, 14 Other (D3/D4/OM3/OM4) — ImageCAS-X Suppl. Table 4.

## Outputs

- `results/` (small): `SUMMARY.md`, `results.json` (per-class Dice and detection on the
  test split), `per_case_test.json`, `predictions_index.json` (classes found per case),
  nnU-Net's val summary, training log, plans, timings.
- `$SCRATCH/icx14/predictions/c0000.nii.gz … c0999.nii.gz`: the prelabels (uint8, on each
  CT's own grid). Not copied by `collect`; fetch them with tar + scp.
- `$SCRATCH/icx14/nnunet_results/…/fold_0/checkpoint_final.pth`: the model.

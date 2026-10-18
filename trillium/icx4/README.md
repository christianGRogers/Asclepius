# icx4 — 4-class model (LM, LAD, LCx, RCA) on ImageCAS-X, then predictions for all 1000 cases

Replaces icx14 (project lead, 2026-10-17, `vault/Plans/Human decisions.md` D25): **four classes again**, side
branches by territory (D1) and the ramus intermedius as LCx (D1b), on **ImageCAS-X's lumen** (D8). The ImageCAS
masks are not used. Same recipe, chain and budget as icx14; only the labels, dataset id and trainer name differ.

```sh
cd <root>/experiments/icx4 && ./icx4      # login node: labels, submit the job chain (reuses $HOME/icx14-venv)
./icx4 status                              # progress
./icx4 collect                             # small results -> ./results/
```

## Other clusters (Nibi, Fir, Rorqual)

The same command runs on Alliance general-purpose clusters with the same `def-aso22` account. The launcher picks
the job shape from the login host (or `$CC_CLUSTER`), or from `ICX4_CLUSTER=trillium|fir|nibi|rorqual`:

| Cluster | Job header |
|---|---|
| Trillium | `--gpus-per-node=1` (24 cores and ~188 GiB come with the GPU) |
| Fir | `--gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G` |
| Nibi | `--gpus-per-node=h100:1 --cpus-per-task=14 --mem=250G` |
| Rorqual | `--gpus-per-node=h100:1 --cpus-per-task=16 --mem=124G` |

Copy `cases/` to the new cluster first (Globus or rsync). The venv is built there on the first run. With fewer cores
per GPU, training may take 50–70 h instead of ~50 h. Details:
`vault/Plans/Experiments/Compute inventory - Nibi or Fir run icx4 unchanged on def-aso22, the AI clusters need an aip- allocation.md`.

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
| Dice on the **open** ImageCAS-X test cases only (open-36 and dev-44, apart; see below) | last job | minutes |

Splits are ImageCAS-X's own: train 560, val 80 (fold 0), test 160 held out. The chain resumes from either
checkpoint file (the icx14 resume fix is kept). Optional class weights: `$SCRATCH/icx4/ce_class_weights.json`, a
list of 5 (background, LM, LAD, LCx, RCA).

## Which cases are scored, and why (A14)

`sealed_test.json` (a byte-identical copy of `trillium/sealed_test.json`, pinned by `tests/test_icx4_sealed.py`)
splits ImageCAS-X's 160 test cases into three groups. `lib/sealed.py` is the one filter every scoring stage uses:

| Group | Cases | Scored? |
|---|---|---|
| Sealed (`sealed_icx_test`) | 80 | **Never.** Scored only at milestones against team reads (`vault/Plans/Sealed test.md`); predicted for SegQueue, never scored, summarised or copied into `results/` |
| Sealed quality-0 (`sealed_quality0`) | 20 | **Never** (same rule; no ImageCAS-X labels anyway) |
| open-36 (`open_icx_test`) | 36 | Yes: never sealed and never used in development, so the clean group |
| dev-44 (`excluded_dev_cases_in_test`) | 44 | Yes, **reported apart**: not sealed, but each was inspected by an advocate, so biased |

The launcher refuses to start (and the job refuses to run) if `sealed_test.json` is missing, unreadable or
malformed, if the job's copy in `$SCRATCH/icx4/` differs from the experiment folder's, or if ImageCAS-X's test
split is not exactly those 80 + 36 + 44. It never falls back to scoring everything. `ICX4_DRYRUN=1 ./icx4` prints
the filter and both group counts. `predictions_index.json` in `results/` omits the sealed cases (it gives only their
count); the full index stays in the workdir as `predictions_index_all.json` for the SegQueue hand-off.

## Outputs

- `results/`: `SUMMARY.md`, `results.json` (per-class Dice and detection, open-36 and dev-44 apart), `per_case_test.json`,
  `predictions_index.json`, nnU-Net's val summary, training log, plans, timings.
- `$SCRATCH/icx4/predictions/c0000.nii.gz … c0999.nii.gz` (uint8, labels 1–4, each CT's own grid).
- `$SCRATCH/icx4/nnunet_results/…/fold_0/checkpoint_final.pth`: the model.

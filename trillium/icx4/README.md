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
| TotalSegmentator `total_fast` aortas for the same 80 open cases (never a sealed case) | last job, GPU | ~30 min |
| **Decisive tree-F1 @ 1.5 mm** (A1/A1c) on the same cases; report | last job, CPU | ~10–20 min |

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

## The decisive score (A1, A1a, A1b, A1c; #54)

Dice decides nothing. The number that accepts, compares or rejects the model is **tree-F1 @ 1.5 mm** (D3) with
the ostium from a TotalSegmentator aorta, computed by `lib/segtrain_tf1.py`: a verbatim copy of
`src/segtrain/tf1.py` that the launcher, the job and `lib/tf1_score.py` each refuse to run unless its sha256 is
`24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254` (A1c, Round 8; pinned by
`tests/test_icx4_tf1.py`). Reused from `trillium/atlas2`:

- **Aortas** (`lib/aorta.py`, GPU): TotalSegmentator 2.18.0 `total_fast`, `roi_subset=['aorta']`, in its own venv
  (`$HOME/icx4-tseg-venv`, atlas2's recipe; the training venv is not touched). Weights are downloaded on the login
  node into `$SCRATCH/icx4/totalseg`. A case whose aorta fails twice is scored **provisional** and decides nothing
  (A1a).
- **tF1** (`lib/tf1_score.py`, CPU): reference = ImageCAS-X collapsed exactly as for training
  (`territory.to_four`). Per case and class: tF1 @ 1.5 mm and @ 0 mm, recall, precision, the classes whose tree has
  a flagged ostium (A1b), `classes_without_centreline` (scored on the fallback centreline, the decisive default),
  and raw FP components (A15).
- **Report** (`lib/report.py`): for open-36 and dev-44 separately, the decisive macro tF1 (non-provisional cases,
  flagged trees left out) and decisive per-class tF1, the flagged trees per class with their own mean, and Dice as
  a secondary column. Only open-36 is clean; dev-44 is biased and never decides alone.

Both stages resume per case. A case whose tF1 raises an error is retried by the next job in the chain; `DONE` is
written only when every open case has a tF1 row (errors are listed in `SUMMARY.md` until then).

## A second, independent run

`ICX4_WORK=$SCRATCH/icx4-seed2 ./icx4` (any path) runs beside the default one without sharing a workdir: its jobs
are named `icx4-<basename>` (so the "already running" check does not see the other run) and `collect` copies to
`./results-<basename>/`. Everything else is the same; pass `ICX4_WORK` to every `./icx4`, `status` and `collect`
of that run.

## Outputs

- `results/`: `SUMMARY.md`, `results.json` (decisive tF1 and Dice, open-36 and dev-44 apart), `per_case_test.json`,
  `tf1_per_case.json` (every A1 row, with ostia),
  `predictions_index.json`, nnU-Net's val summary, training log, plans, timings.
- `$SCRATCH/icx4/predictions/c0000.nii.gz … c0999.nii.gz` (uint8, labels 1–4, each CT's own grid).
- `$SCRATCH/icx4/nnunet_results/…/fold_0/checkpoint_final.pth`: the model.

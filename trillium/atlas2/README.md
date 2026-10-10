# atlas2: Atlas run 2 (Round 5, amendment A16)

This is the second Atlas experiment. It follows the contract in `trillium/README.md`: one command, no arguments,
one 1×H100 job of at most 23:50, account `def-aso22`. It never writes to Girder, never needs a password and never
touches a sealed case.

It **reuses run 1** (`./atlas`, workdir `$SCRATCH/atlas`), whose `results/manifest.json` gives the checkpoint, the
val segmentations and softmax, the reference labels, the plans and the dataset fingerprint. **Run 1 must have
finished first.** The entry point checks this and refuses otherwise.

```sh
cd <root>/experiments/atlas2 && ./atlas2     # login node: set up, then submit one job
./atlas2 status                              # progress
./atlas2 collect                             # copy results/ back (SUMMARY.md, results.json, small tables)
```

## What it does

**On the login node.** The steps below are idempotent.

1. **Check the metric.** It checks the decisive metric's version. `lib/segtrain_tf1.py` is a verbatim copy of
   `src/segtrain/tf1.py`. It must have the sha256 frozen in `vault/Plans/Master plan.md` (A1c):
   `3c737cbcc0ba24d38f923a52a28d479b34b579d6943f4c55a8cae48f66ad9253`. With any other hash it refuses to run. The
   job checks the hash again.
2. **Build the venv** in `$HOME/atlas2-venv`: torch from the Alliance wheelhouse, `nnunetv2==2.8.1` and
   `TotalSegmentator==2.18.0`, the same versions as were tested here. Run 1's trainer is installed into it.
3. **Check run 1.** It verifies run 1's outputs (checkpoint, plans, fingerprint, splits, 80 val segmentations plus
   softmax plus references) and the case layout (ImageCAS or Girder, found by walking up to `cases/`).
4. **Fetch the data.**
   - The ImageCAS-X labels are reused from run 1.
   - The ImageCAS-X centrelines for the 80 val and 36 open cases are fetched from Zenodo (range reads, a few MB).
     Their start points are a validation column only.
   - The TotalSegmentator `total_fast` weights are downloaded into `$SCRATCH/atlas2/totalseg`. Usage statistics
     are switched off, because the compute node has no network.
5. **Submit the job.**

**In the job** (`lib/job_body.sh`). Every stage is resumable from its marker files.

| Stage | Where | Time | What |
|---|---|---|---|
| A0 | CPU, background | ~40 min | Phase B preprocessing: dataset 714 = run 1's images and labels with nnU-Net's **default** CT window, restored from run 1's fingerprint |
| A1 | GPU | ~30 min | TotalSegmentator aortas for the 80 val and the 36 clean open test cases (A1 ostium of record) |
| A2 | CPU, background (4 workers) | ~2 h, overlapping training | Run 1's val: tF1 @1.5/@0 with the A1 ostium (frozen `segtrain.tf1`), flagged trees separate (A1b), FP gate, **FP census** (A15), global-threshold sweep, ostium vs ImageCAS-X start points |
| A3 | GPU | ~30 min | The **36 clean open test cases** (A14 `open_icx_test`, cross-checked against both sealed lists): run 1's checkpoint, tile step 0.5, no TTA, `--save_probabilities`; plus their proxy labels; `open36/manifest_open36.json` for Bridge |
| B | GPU | ~20 h | **A2 window ablation**: run 1's recipe with the default window, **412 epochs** (run 1's length), `--npz` |
| B score | CPU | ~30 min | The same scoring code as A2. The sweep runs only if more than 80 min remain |
| report | CPU | 1 min | `SUMMARY.md`, `results.json`, per-case tables, census tables, the paired B − run 1 comparison and the window decision |

Budget: about 1 h before training, 20.0 h of training (412 × 175 s, run 1's measurement), and about 1 h after it.
That totals ~22.3 h of the 23:50.

If time runs short, the trainer stops before the deadline so that the final validation always runs. The report
then marks the pairing as weakened.

## Pre-registered reading (fixed before the run; vault note *Atlas - Pending Trillium run 2…*)

**Decisive tF1.**
- Uses the A1 ostium of record, from the aorta.
- Leaves out any class whose tree carries a flagged ostium (A1b). Flagged trees are reported separately.
- A case without an aorta mask is provisional and decides nothing (A1a).

**FP census categories** (`lib/score.py`).
- `icx_vessel`: at least 50 % of the component's voxels lie within 1 mm of ImageCAS-X vessel.
- `low_confidence`: not `icx_vessel`, and the 90th percentile of its vessel probability is below 0.90.
- `confident_other`: everything else.
- A15 routing:
  - mostly `low_confidence` → a global threshold;
  - mostly `icx_vessel` → a question for the humans;
  - mostly `confident_other` → reopens the recipe.

**Window decision (A16).**
- The paired decisive tF1, B − run 1, decides when its 95 % bootstrap CI excludes 0.
- On a tie, the window with fewer FP components per case wins.

## Results (`results/`, < 1 MB, no volumes)

- `SUMMARY.md`, `results.json`.
- `per_case_run1.json`, `per_case_b.json`: tF1, per class, flags, ostia with validation distances, FP count, sweep.
- `census_run1.json`, `census_b.json`: one row per FP component.
- `open36_manifest.json`: paths of the open-36 predictions, softmax, references and aortas on `$SCRATCH`, and the
  exact command.
- Logs and timings.

The aortas, the open-36 softmax and B's weights stay on `$SCRATCH/atlas2`.

## Tested on CPU (this repo, no GPU)

- **Dry run.** `ATLAS_DRYRUN=1` was run in both case layouts against a fake run-1 tree: it found the cases, run 1,
  the ImageCAS-X labels and the centrelines, and printed the job.
- **Refusals.** It refuses a tampered `segtrain_tf1.py`, and it refuses when run 1 is missing.
- **Job body.** `lib/job_body.sh` ran end to end on CPU (`ATLAS2_LOCAL_TEST=1`) on 2 real val cases with
  synthetic predictions and softmax:
  - stub aortas;
  - plans for the default window built from the fingerprint. `nnUNetv2_preprocess` was run separately on two
    cropped real cases, and the intensities match the restored default window exactly;
  - the open-36 proxy label written, with prediction failing cleanly on the fake checkpoint;
  - run 1 scored;
  - the report written.
- **Scoring.** One real case (c0038, with Delta's TotalSegmentator aorta) was scored end to end:
  - the A1 left ostium is 2.8 mm from the ImageCAS-X start point;
  - a planted RCA cut is flagged;
  - two planted FP blobs are classed `low_confidence` and `confident_other`.
- **Start-point parser.** `lib/vtkcl.py` matches `vtk.vtkPolyDataReader` on all 876 local centreline files, binary
  and ASCII.
- **Lint.** `shellcheck` is clean on `atlas2` and `lib/job_body.sh`, and pyflakes is clean on `lib/*.py`.

# segmentator-train

Multiclass coronary artery segmentation from CCTA. **nnU-Net v2, `3d_fullres`,
at native spacing, with no downsampling anywhere in the path** — no cascade, no
coarsened resampling, no heart crop. The full plan, with the reasoning and the
evidence, is [`docs/TRAINING-PLAN.md`](docs/TRAINING-PLAN.md); the retired
previous plan is on the `plan-v1` branch.

Training runs on [SciNet](https://www.scinet.utoronto.ca/)'s Trillium
supercomputer, one H100 80 GB per job.

## The method

A distal coronary branch is 1.5–2 mm across — a few voxels at the ~0.35 mm the
scans are acquired at. Anything that downsamples destroys exactly the structures
being labelled, so the model reads the data at acquired resolution end to end:

- **`spacing: native`** — nnU-Net's median-spacing rule, on a near-isotropic
  cohort, keeps the acquired grid.
- **No `3d_cascade_fullres`.** Its low-resolution first stage resamples distal
  branches below their own diameter.
- **No heart crop.** The H100 sets the patch size, not the crop: a ~70 GB
  budget buys a ~256³ patch, ~27–30 % of a whole volume — above the 12.5 %
  threshold at which nnU-Net would plan a cascade, and large enough to hold the
  coronary tree with the aortic root and both ostia in one view. Whole volumes
  also teach the model to reject coronary look-alikes (pulmonary vessels, bone
  edges), and there is no cropper to silently clip a low-running RCA.

Sequence: a **binary lumen model first**, trained on the 1000 ImageCAS masks
that already exist — it proves the Trillium chain, calibrates against the
published 82.96 % Dice benchmark, and seeds the annotators' presegmentations.
The **multiclass model** trains on the same configuration once per-branch
labels flow. One paired **ResEnc** run afterwards decides the encoder.

Ruled out, deliberately: tree/graph-structured models as the primary segmenter
(unrecoverable when the pre-segmentation misses a vessel), nnU-Net's
largest-component post-processing (the coronary tree is naturally several
disconnected components; the rule deletes real vessels), and mirroring
augmentation (it swaps the left coronary tree for the right).

## Data

One directory per case:

```
<root>/<case>/ct.nii.gz
<root>/<case>/segmentations/<structure>.nii.gz   # one binary mask per vessel
  ... or ...
<root>/<case>/labels.nii.gz                      # one integer volume
```

Prefer the per-vessel form: it distinguishes "not labelled" from "not present",
which a merged volume has thrown away. For the single-file form, map the
integers in `configs/labels/<set>.local.yaml` (`source_values:`) — segment order
in an export is drawing order, so reading positionally mislabels every vessel
while reporting success. A vessel absent from a case (ramus intermedius in most
people; the PDA off the LCx in a left-dominant heart) gets **no mask**, not an
empty one.

Three conversion traps, handled but worth knowing:

- **Oblique volumes**: ITK rejects direction cosines that are not orthonormal
  to its tolerance, and cardiac CT is frequently reconstructed oblique. The
  conversion writes `NibabelIOWithReorient` into `dataset.json`; do not remove it.
- **Overlapping masks**: independently drawn masks disagree by a voxel at
  bifurcations. `overlap_policy: smaller_wins` gives contested voxels to the
  smaller structure so trunks do not erode their branches.
- **Splits are hash-derived**, not shuffled, so a growing dataset never moves
  yesterday's test cases into today's training set. Test cases never enter
  `imagesTr`. `validate_splits` fails loudly on leakage.

## Running it

```bash
pip install -e .                # data prep, no GPU needed
pip install -e ".[train]"       # adds nnU-Net (not on SciNet -- see below)

segtrain index --root /data/coronary       # meta.csv, hash-derived split
segtrain plan  --task 710 --gpu-mem 70     # fingerprint + plans, no GPU needed
```

**Read the plan printout before submitting anything.** Three gates: the patch
covers ≥ 12.5 % of the median image shape (no cascade planned), the target
spacing came out native rather than dragged coarse by thick-slice outliers, and
batch size is 2. Plans made at one `--gpu-mem` are not interchangeable with
checkpoints trained under another.

On Trillium:

```bash
ssh you@trillium-gpu.alliancecan.ca
segtrain scinet setup                     # prints the venv commands; paste them
segtrain scinet check                     # verifies account, venv, paths, walltime
segtrain scinet prepare --task 710 --convert   # CPU job: convert + plan + preprocess
segtrain scinet submit  --task 710 --fold 0    # GPU job chain
segtrain scinet status  --task 710 --fold 0 --watch
```

The cluster details that matter:

- **Install with `--no-index`** from the Alliance wheelhouse (torch ≥ 2.5.1 for
  H100); PyPI's torch bundles its own CUDA and cannot see the GPU here. The venv
  lives in `$HOME`; all data and results live in `$SCRATCH` — `$HOME` and
  `$PROJECT` are read-only from compute nodes.
- **Ask for one GPU.** Scheduling is by whole GPU; one brings 24 cores and
  ~188 GiB with it, and nnU-Net trains on a single device.
- **The 24-hour walltime** is crossed by a job chain (`sbatch --array=1-N%1`),
  created at submit time from the login node — compute nodes cannot submit
  jobs. `SEGTRAIN_MAX_SECONDS` checkpoints at an epoch boundary and exits
  without nnU-Net's `on_train_end`, which would delete the checkpoint. Cancel
  kills queued successors before the running block.
- **No node-local disk**: `$SLURM_TMPDIR` is a RAM disk charged against the
  job's memory; `stage_to_tmpdir` stays off unless the preprocessed set fits.
- Preprocessed data at native spacing, uncropped, is large (order 250 GB, and
  the `.npz`→`.npy` unpack roughly doubles it transiently). Measure, and
  provision `$SCRATCH` accordingly. `--npz` stays off.

Evaluate with `segtrain evaluate` — raw predictions, no post-processing; Dice
alongside NSD, with the full metric set (clDice, branch detection, AHD,
per-class) specified in the plan.

```bash
pytest                    # 415 tests; SegQueue concurrency tests need MongoDB
```

## Everything else

- [`docs/TRAINING-PLAN.md`](docs/TRAINING-PLAN.md) — the plan of record
- [`docs/SEGQUEUE.md`](docs/SEGQUEUE.md) — the annotation platform producing the per-branch labels
- [`docs/SLICER-MONITOR.md`](docs/SLICER-MONITOR.md) — watching a run live in 3D Slicer
- [`docs/SERVER-SETUP.md`](docs/SERVER-SETUP.md), [`docs/SERVER-HANDOFF.md`](docs/SERVER-HANDOFF.md) — the Girder server

## Acknowledgement and licence

Publications using this compute carry SciNet's
[requested acknowledgement](https://docs.scinet.utoronto.ca/index.php/Acknowledging_SciNet)
and cite Ponce et al. 2019 ([doi:10.1145/3332186.3332195](https://doi.org/10.1145/3332186.3332195))
and Loken et al. 2010 ([doi:10.1088/1742-6596/256/1/012026](https://doi.org/10.1088/1742-6596/256/1/012026)).

MIT for this pipeline; nnU-Net is Apache-2.0. Trained weights follow the
training data's terms, not this repo's.

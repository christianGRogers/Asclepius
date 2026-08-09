# segmentator-train

Training pipeline for whole-body CT anatomical segmentation — 117 structures,
nnU-Net v2, with the run visible live inside 3D Slicer.

The method follows Akinci D'Antonoli & Wasserthal et al., *TotalSegmentator MRI*
(Radiology 2025, [doi:10.1148/radiol.241613](https://doi.org/10.1148/radiol.241613)):
**nnU-Net with its self-configured defaults and no hyperparameter tuning**, with
the structure set **split across several models** because one network over every
class neither fits nor converges well. Applied here to CT, using the
TotalSegmentator v2.0.1 dataset.

The pipeline is the deliverable, not just the weights. It lives in its own repo,
separate from the inference extension that will eventually ship the model.

---

## What it does

```
Zenodo layout          nnU-Net raw            training                 Slicer
sXXXX/ct.nii.gz   ──▶  imagesTr/  ──▶ plan ──▶ nnUNetTrainer_segtrain ──▶ events.jsonl ──▶ monitor
sXXXX/segmentations/   labelsTr/                       │                       ▲
  117 binary masks       1 multilabel                  └── preview daemon ─────┘
                                                           (infers + scores held-out cases)
```

The trainer never talks to Slicer. It appends to `events.jsonl`; Slicer polls
that file. So a run can be attached to late, detached from, or watched from
another machine, and nothing the monitor does can disturb training.

---

## Two stages

| | Task | Classes | Spacing | Why |
|---|---|---|---|---|
| **1** | `Dataset701_Total3mm` | all 117 | 3.0 mm | One model, ~1–2 days on a single GPU. Fast route to something you can actually look at. |
| **2** | `Dataset702_Organs` | 26 | 1.5 mm | Soft-tissue organs |
| | `Dataset703_Vertebrae` | 25 | 1.5 mm | C1–S1 |
| | `Dataset704_Cardiac` | 18 | 1.5 mm | Heart and great vessels |
| | `Dataset705_Muscles` | 10 | 1.5 mm | Gluteals, autochthon, iliopsoas |
| | `Dataset706_Bones` | 38 | 1.5 mm | Ribs, sternum, limb and pelvic bones, skull |

The five groups partition all 117 structures exactly — enforced by a test, not
by care. Label files are generated from the dataset itself:

```bash
python scripts/gen_label_configs.py /data/Totalsegmentator_dataset_v201
```

The source data is 1.5 mm isotropic, so 1.5 mm is the *high*-resolution target;
a sub-millimetre model is not trainable from it. Stage 1 exists only because we
force the target spacing — nnU-Net would otherwise pick 1.5 mm for both stages
and Stage 1 would silently become an unfittable 117-class full-resolution model.

---

## Install

```bash
python -m venv .venv && .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e .                                # data prep + monitor, no GPU needed
pip install -e ".[train]"                       # adds nnU-Net; install torch to match your CUDA
```

Do **not** create the venv with `--system-site-packages`; nnU-Net pulls numpy 2.x
and will collide with older host packages compiled against numpy 1.x.

Copy `configs/dataset.yaml` to `configs/dataset.local.yaml` and set the paths.
Precedence is CLI flag → environment (`nnUNet_raw` etc.) → `.local.yaml` →
tracked template, so the same checkout drives a laptop, a rented box and a
cluster with no edits to tracked files.

---

## Running a stage

```bash
segtrain info                              # resolved paths, tasks, whether a GPU exists
segtrain convert    --task 701             # 117 masks -> one multilabel; images hardlinked
segtrain plan       --task 701             # fingerprint + plans at 3 mm + splits
segtrain preprocess --task 701
segtrain train      --task 701 --fold 0
segtrain preview    --task 701 --fold 0 --watch    # second terminal, beside the GPU
segtrain status     --task 701 --fold 0 --worst 10
segtrain evaluate   --task 701                     # held-out test set, Dice + NSD
```

Remote and cluster runs are the same commands:

```bash
segtrain train --task 701 --backend ssh --host me@gpu-box
segtrain train --task 701 --backend slurm
```

---

## Running on a rented GPU

The whole point of the event-stream design: training runs on the instance, you
watch from your laptop. Nothing but OpenSSH is needed locally.

Configure once in `configs/dataset.local.yaml`:

```yaml
remote:
  host: ubuntu@203.0.113.10      # changes every time the instance restarts
  identity_file: C:/Users/you/.ssh/lambda.pem
  root: /home/ubuntu/segtrain
```

Then:

```bash
segtrain remote check                    # key, connection, GPU, disk, install
segtrain remote setup                    # ships the pipeline, installs deps
segtrain convert --task 701              # locally: 117 masks -> 1 multilabel
segtrain remote push  --task 701         # uploads ~21 GB, resumable
segtrain remote train --task 701         # plan + preprocess + train, detached
segtrain remote status --task 701 --watch
segtrain remote pull  --task 701 --checkpoints
```

**Fix the key first.** On Windows a downloaded `.pem` inherits ACLs granting
SYSTEM and Administrators access, and OpenSSH refuses it with *UNPROTECTED
PRIVATE KEY FILE*. `segtrain remote check` detects this and
`--fix-key` repairs it (`icacls /inheritance:r /grant:r`).

Three things the transfer does deliberately:

- **Converts locally.** The 117 binary masks are 9.1 GB and merge to ~0.7 GB.
  Uploading converted datasets rather than the Zenodo tree saves that transfer
  *and* moves the CPU work off a machine billed by the GPU-hour.
- **Uploads images once.** All six tasks share byte-identical `imagesTr`. Images
  go to a shared pool and are hardlinked into each task, so six tasks cost
  ~21 GB plus ~0.7 GB each, not six full copies.
- **Streams with `tar`, not `scp`.** A dataset is ~2500 files; `scp` pays a round
  trip per file. Transfers resume by diffing a remote listing, so a dropped
  connection costs only the current 200-file batch.

`remote train` runs planning, preprocessing and training inside `nohup setsid`,
so closing your laptop cannot kill an hour of preprocessing.

### Instance sizing

nnU-Net's default plan targets **8 GB**, so every current rental option has more
VRAM than this workload can use. The real constraint is **vCPU count** —
3d_fullres is dataloader-bound on fast GPUs, and augmentation is CPU work. A
26-vCPU H100 will idle waiting on its own dataloader. `remote check` warns below
12 vCPUs.

Rough Stage 1 cost on Lambda (1000 epochs, estimates ±30%):

| GPU | $/hr | vCPUs | est. hours | est. total |
|---|---|---|---|---|
| GH200 | 2.29 | 64 | ~16 | **~$37** |
| Quadro RTX 6000 | 0.69 | 14 | ~90 | ~$62 |
| A100 SXM | 1.99 | 30 | ~36 | ~$72 |
| H100 SXM | 4.29 | 26 | ~24 | ~$103 |

GH200's 96 GB and 64 vCPUs also let you train ~4 of the Stage 2 group models
concurrently, which is what takes Stage 2 from ~$400 to ~$140. Its Grace CPU is
ARM, so expect more dependency friction than x86.

## Watching it train in Slicer

1. Slicer → **Edit → Application Settings → Modules**, drag
   `slicer/SegmentatorTrainMonitor` into **Additional module paths**, restart.
2. Open **Segmentation → Segmentator Train Monitor**.
3. Point it at a run directory — a local path, or
   `ubuntu@203.0.113.10:/home/ubuntu/segtrain/runs/Dataset701_Total3mm__fold0`,
   and set **SSH key** to your `.pem` for a rented instance.

`segtrain remote train` prints the exact `host:path` to paste.

You get loss and pseudo-Dice curves, a per-structure Dice table sorted weakest
first, and the live model's segmentation of a **held-out** case loaded over the
CT in the 3D view — with an epoch slider, so you can watch a structure sharpen,
or catch a vertebra label sliding by one.

Per-structure Dice in the table comes from the preview daemon scoring real
held-out cases. nnU-Net's own pseudo-Dice is computed on training patches and
reads far too high early on; it is shown on the curve but is not what the table
reports once previews exist.

No pip installs into Slicer's Python: the module imports the stdlib-only
`segtrain.events` from `src/`, and shells out to `ssh`/`scp`.

Verify the module against a finished run:

```bash
"…/Slicer.exe" --no-splash --python-script tests/slicer_selftest.py \
    --run-dir /data/runs/Dataset701_Total3mm__fold0
```

---

## Two things about this dataset that will cost you if you miss them

**11% of the volumes are unreadable by nnU-Net's default reader.** 136 of the
1228 CTs are obliquely acquired, and their float32 direction cosines fall just
outside ITK's orthonormality tolerance — SimpleITK raises *"ITK only supports
orthonormal direction cosines"*. Under the default reader those cases fail to
preprocess and 11% of the training data disappears quietly and unevenly across
study types. `convert` therefore writes `overwrite_image_reader_writer:
NibabelIOWithReorient` into `dataset.json`. Do not remove it.

**The source masks overlap.** Each structure was segmented independently, so
adjacent structures disagree by a voxel or two along shared interfaces — colon
against small bowel, heart against inferior vena cava, L5 against sacrum. It is
roughly 0.02% of voxels, but a multilabel volume needs one owner per voxel. The
default `overlap_policy: smaller_wins` gives contested voxels to the smaller
structure, so thin structures are not eroded by bulky neighbours. The
alternative, `label_order`, is alphabetical and therefore anatomically arbitrary;
it exists only to measure the difference.

---

## Disk

Measured on this dataset, not estimated.

| | |
|---|---|
| Source images (1228) | 21.0 GB |
| Source masks (117 × 1228) | 9.1 GB |
| Merged multilabel labels | **~0.3–0.7 GB** — the merge is nearly free |
| Images in `nnUNet_raw` | **0 bytes** via hardlink on the same filesystem |
| Preprocessed @ 3 mm | ~10 GB (~14 GB peak) |
| Preprocessed @ 1.5 mm, per task | ~75 GB (up to ~110 GB peak on nnU-Net ≤ 2.5, which keeps both `.npz` and unpacked `.npy`) |
| Checkpoints | ~1 GB per fold per task |

So: **~35 GB** for Stage 1, and provision **~250 GB** for Stage 2 — or ~110 GB
if you preprocess one group at a time and delete between them. Five-fold CV
multiplies GPU time by five but adds only ~25 GB, since folds share preprocessed
data.

`--npz` is **off by default**. It writes float16 softmax per class per voxel —
~660 MB per case, >150 GB across the 1.5 mm groups — and is only needed to build
a cross-fold ensemble.

---

## Splits

`meta.csv` carries the published split: **1082 train / 57 val / 89 test**. The 89
test cases never enter `imagesTr`, so no training, model-selection or
postprocessing decision can see them.

- `--scheme official` (default) — one fold, exactly the published boundary, so
  results stay comparable to the paper.
- `--scheme cv5` — stratified 5-fold over the 1139 non-test cases, balanced by
  study type so a rare type like `ct angiography head` cannot land in one fold.
  Use only if you intend to train and ensemble five models.

`validate_splits` fails loudly on train/val overlap or test leakage, and preview
cases are checked to be genuinely held out — a preview rendered on a training
case looks great and means nothing.

---

## Tests

```bash
pytest                    # 90 tests
pytest -m "not slow"      # skip the full-case merge round-trip
```

Tests needing the dataset are marked `needs_data` and skip without it.

---

## Status

Verified end to end on CPU with a 24-case subset: convert → plan → preprocess →
train → preview → status, plus the Slicer module against a real run (91 segments
imported with correct anatomical names). What has **not** been exercised is a
full-scale GPU run: the 1000-epoch schedule, multi-GPU, the SSH and SLURM
backends against real hosts, and `evaluate` over the 89 test cases.

## Licence

MIT for this pipeline. nnU-Net is Apache-2.0; the TotalSegmentator dataset
carries its own terms — check them before redistributing any trained weights,
since the weights' licence follows the training data, not this repo.

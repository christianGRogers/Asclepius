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

Training runs on [SciNet](https://www.scinet.utoronto.ca/)'s Trillium
supercomputer — see [Running on SciNet](#running-on-scinet) and
[Acknowledging SciNet](#acknowledging-scinet).

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
tracked template, so the same checkout drives a laptop and a cluster with no
edits to tracked files.

On SciNet, install into the venv described under [Running on
SciNet](#running-on-scinet) rather than with the `[train]` extra: torch and
nnU-Net both come from the Alliance wheelhouse there, not PyPI.

---

## Getting the data

The dataset is [Zenodo record 10047292](https://zenodo.org/records/10047292) —
one 22 GB archive that expands to ~30 GB of subject directories.

```bash
python scripts/init_dataset.py                       # uses zenodo_root from the config
python scripts/init_dataset.py --dest /data/Totalsegmentator_dataset_v201
```

It downloads, checks the published MD5, extracts, verifies the result is 1228
subjects with 117 masks each, and deletes the archive (`--keep-zip` to keep it).
Both the download and the extraction resume, and a dataset root that already
looks complete is left alone — so it is safe to run from a provisioning script,
or to run again after an interrupted transfer. Stdlib only, so it works before
`pip install -e .`.

On SciNet, download it **on a login or datamover node** — compute nodes have no
outbound internet, so a download submitted to the queue waits for hours and then
fails at the first HTTP request:

```bash
segtrain scinet fetch --task 701     # runs here, not in a job
```

Put it under `$SCRATCH`. `$HOME` and `$PROJECT` are mounted read-only on
Trillium's compute nodes, so a dataset in either is unreadable-for-writing by the
job that needs it. The ~145,000 files are not a quota problem there — `$SCRATCH`
allows 25 TB and 10M files — but they are worth deleting once every task has been
converted, since nothing downstream reads the Zenodo tree again.

### More labelled CT, from the NCI Imaging Data Commons

[IDC](https://imaging.datacommons.cancer.gov/) publishes public cancer imaging
with a SQL-queryable index and anonymously readable buckets. The same script
fetches from it — no `idc-index`, no credentials, still stdlib only:

```bash
python scripts/init_dataset.py --list-idc                    # what is there
python scripts/init_dataset.py --idc expert                  # every human-drawn set
python scripts/init_dataset.py --idc pediatric_ct_seg --limit-cases 25
```

| | labels | provenance | cases | size |
|---|---|---|---|---|
| `pediatric_ct_seg` | 29 organs | expert | 359 | 64 GB |
| `nsclc_radiomics` | lungs, oesophagus, heart, cord | expert | 422 | 27 GB (**CC BY-NC**) |
| `mediastinal_lymph_node_seg` | lymph nodes | expert | 513 | 34 GB |
| `c4kc_kits` | kidney + tumour | expert | 210 | 40 GB |
| `prostate_anatomical_edge_cases` | prostate, bladder, rectum, femoral heads | expert | 131 | 17 GB |
| `pancreas_ct` | pancreas | expert | 80 | 10 GB |
| `lctsc` | oesophagus, heart, lungs, cord | expert | 60 | 5 GB |
| `spine_mets_ct_seg` | vertebrae + metastases | expert | 55 | 20 GB |
| `adrenal_acc_ki67_seg` | adrenal gland | expert | 53 | 10 GB |
| `totalsegmentator_ct_segmentations` | ~77 structures, this label set | **model** | 26,194 | 22 TB |
| `bamf_aimi_annotations` | organs + tumours | mixed | 4,226 | varies |

Three things decide whether any of this is worth pulling.

**Most of it by volume is not ground truth.** `totalsegmentator_ct_segmentations`
is 126,051 series — TotalSegmentator's *own output* over NLST. Training on it
distils the model this pipeline reproduces; it cannot beat it. It is also chest
screening CT only, so it carries no abdominal or pelvic anatomy. Useful for
pretraining or semi-supervised work, and it is the reason `--limit-cases` exists.

**The expert sets are small and complementary.** `pediatric_ct_seg` is the one
worth the trouble: 359 paediatric CTs with 29 human-contoured organs, covering a
population the TotalSegmentator training set barely has. The rest add pathology —
diseased vertebrae, kidneys with tumour, hard-to-contour pelvic anatomy.

**Licences differ per series, and weights inherit them.** `nsclc_radiomics` is
CC BY-NC and is skipped unless you pass `--allow-noncommercial`; `pancreas_ct`
has CC BY 3.0 images with CC BY 4.0 labels. Each download writes an
`ATTRIBUTION.txt` beside the data.

IDC ships DICOM, and this pipeline reads NIfTI plus one mask per structure. So
`--idc` gets you the data, its layout by patient, and its provenance — **not a
drop-in dataset.** Converting DICOM to NIfTI, turning SEG/RTSTRUCT into
per-structure masks, and mapping names like `Deep muscle of back` or
`Femoral Head Rig` onto the 117 is still to be written.

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

---

## Running on SciNet

<img src="docs/scinet-logo.png" alt="SciNet" width="260">

Training runs on Trillium's GPU subcluster; you watch from your laptop. That is
what the event-stream design is for — nothing but OpenSSH is needed locally, and
the monitor reads the same `events.jsonl` the job is writing.

**Trillium GPU**, as of this writing: 63 nodes, each 4 × NVIDIA H100 SXM 80 GB,
96 AMD EPYC cores, 768 GB RAM. Scheduling is by whole GPU — one GPU brings a
quarter node with it (24 cores, ~188 GiB). Walltime is capped at **24 hours**.

### Setting up, once

```bash
ssh you@trillium-gpu.alliancecan.ca      # GPU jobs submit from the GPU login node
segtrain scinet setup                    # prints the exact commands; paste them
```

They come out roughly as:

```bash
module purge
module load StdEnv/2023 python/3.11.5 cuda/12.6
virtualenv --no-download $HOME/segtrain-env
source $HOME/segtrain-env/bin/activate
pip install --no-index --upgrade pip
pip install --no-index torch nnunetv2 SimpleITK nibabel
pip install --no-deps -e /path/to/this/repo
```

Three details that are easy to get wrong and expensive to debug:

- **`--no-index`, always.** It installs from the Alliance wheelhouse: builds
  matched to this cluster's CUDA, drivers and CPU. PyPI's `torch` bundles its own
  CUDA and is the usual reason a job imports torch happily and then cannot see
  the GPU. H100s need torch ≥ 2.5.1. The whole nnU-Net v2 stack is in the
  wheelhouse, so the install needs no internet beyond the login node.
- **The venv goes in `$HOME`.** Compute nodes can read `$HOME`; `$SCRATCH` "may
  get partially deleted", which surfaces weeks later as an `ImportError` in
  block 7 of a chain.
- **Everything else goes in `$SCRATCH`.** `$HOME` and `$PROJECT` are read-only
  from compute nodes, so a run whose `nnunet_results` is in either dies on its
  first write — after its queue wait.

Then set `account` and the five paths in `configs/dataset.local.yaml`, and check
the lot before spending a queue wait on it:

```bash
segtrain scinet check
```

It verifies the account, the venv, the walltime arithmetic, and — the one that
actually bites — whether any configured path is on a filesystem the compute nodes
cannot write to.

### Running a stage

```bash
segtrain scinet fetch   --task 701                # login node: no compute-node internet
segtrain scinet prepare --task 701 --convert      # CPU job: convert + plan + preprocess
segtrain scinet submit  --task 701 --fold 0       # GPU job chain
segtrain scinet status  --task 701 --fold 0 --watch
segtrain scinet queue                             # what's running and why it's pending
segtrain scinet cancel  --task 701 --fold 0
```

`prepare` asks for no GPU. Fingerprinting, planning and preprocessing are CPU and
I/O work, and Trillium's CPU subcluster is 1224 nodes against the GPU
subcluster's 63 — so it is both cheaper against the allocation and usually far
quicker to start.

### Crossing the 24-hour wall

Stage 1 is roughly 24–40 GPU-hours; the cap is 24. So `scinet submit` doesn't
submit one job, it submits a **chain**:

```
block 1 ──train 23.3 h──▶ checkpoint, pause ──▶ block 2 ──resume──▶ … ──▶ complete
```

`SEGTRAIN_MAX_SECONDS` stops the trainer at an epoch boundary with time to spare,
writes `checkpoint_latest.pth`, and — critically — exits *without* nnU-Net's
`on_train_end`, which deletes that very file. The next block finds the checkpoint
and resumes with `--c`.

The chain is created **at submit time, from the login node**, as one
`sbatch --array=1-N%1`. The obvious alternative, a job that ends by submitting
its own successor, cannot work here: Trillium blocks job submission from compute
nodes, so that script fails on its last line every time and the run stops after
one block having looked fine throughout. Blocks that start after the run has
finished check the event stream and exit in seconds.

If job arrays turn out to be restricted, `chain_mode: dependency` submits N
separate jobs chained with `--dependency=afterany` instead. `afterany` rather
than `afterok` because a block killed at the walltime exits nonzero, and that is
exactly when its successor is needed.

Cancelling is `segtrain scinet cancel`, which kills the queued successors
*before* the running block — the other order satisfies the dependency and starts
the block you were trying to stop.

### Sizing, and one Trillium-specific trap

nnU-Net's default plan targets **8 GB of VRAM**, so one 80 GB H100 is already far
more than this workload can use; asking for four would idle three of them. The
real constraint is core count, and a 1-GPU job gets 24 — enough that the
dataloader keeps up.

**Trillium nodes have no local disk.** `$SLURM_TMPDIR` is a RAM disk, and what
you put in it comes out of the job's own memory. Every "stage your dataset to
node-local NVMe" tutorial is therefore wrong here. `stage_to_tmpdir` is off by
default; turning it on is reasonable for Stage 1 (~10 GB of 3 mm data against
~188 GiB) and not for the 1.5 mm groups (~75 GB, roughly doubled by nnU-Net's
`.npz` → `.npy` unpacking). The job script measures the dataset against the
cgroup limit and skips staging rather than being OOM-killed — `df` inside the job
reports the RAM disk as the size of physical memory, and will happily let you
overfill it.

It matters less here than the usual advice implies, in any case: Trillium's
storage is all-NVMe rated at ten million read IOPS, not the Lustre that the
"avoid many small files" guidance was written for.

## Watching it train in Slicer

1. Slicer → **Edit → Application Settings → Modules**, drag
   `slicer/SegmentatorTrainMonitor` into **Additional module paths**, restart.
2. Open **Segmentation → Segmentator Train Monitor**.
3. Point it at a run directory — a local path, or
   `you@trillium.alliancecan.ca:/scratch/g/grp/you/runs/Dataset701_Total3mm__fold0`,
   optionally with an **SSH key** if `~/.ssh/config` does not already name one.

`segtrain scinet submit` prints the exact `host:path` to paste.

The run directory lives on `$SCRATCH`, which the login nodes share with the
compute nodes, so the monitor reads the live file while the job writes it —
there is no staging step and nothing to synchronise. Setting up `ControlMaster`
for the host in `~/.ssh/config` is worth the two lines: the monitor polls every
ten seconds, and Toronto is several hundred milliseconds of handshake away.

You get loss and pseudo-Dice curves, a per-structure Dice table sorted weakest
first, and the live model's segmentation of a **held-out** case loaded over the
CT in the 3D view — with an epoch slider, so you can watch a structure sharpen,
or catch a vertebra label sliding by one.

Per-structure Dice in the table comes from the preview daemon scoring real
held-out cases. nnU-Net's own pseudo-Dice is computed on training patches and
reads far too high early on; it is shown on the curve but is not what the table
reports once previews exist.

No pip installs into Slicer's Python: the module imports the stdlib-only
`segtrain.events` from `src/`, and shells out to the system `ssh`/`scp`.

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
imported with correct anatomical names). The SLURM layer is unit-tested — script
rendering, walltime arithmetic, chain wiring, the resume decision — but has
**not** yet been run against Trillium's scheduler. Also unexercised: the
1000-epoch schedule, multi-GPU, and `evaluate` over the 89 test cases.

## Acknowledging SciNet

Any publication using compute from this pipeline should carry SciNet's
[requested acknowledgement](https://docs.scinet.utoronto.ca/index.php/Acknowledging_SciNet):

> Computations were performed on the Trillium supercomputer at the SciNet HPC
> Consortium. SciNet is funded by Innovation, Science and Economic Development
> Canada; the Digital Research Alliance of Canada; the Ontario Research Fund:
> Research Excellence; and the University of Toronto.

SciNet also asks that these two papers be cited:

- M. Ponce et al., "Deploying a Top-100 Supercomputer for Large Parallel
  Workloads: the Niagara Supercomputer", *PEARC'19 Proceedings*, 2019.
  [doi:10.1145/3332186.3332195](https://doi.org/10.1145/3332186.3332195)
- C. Loken et al., "SciNet: Lessons Learned from Building a Power-efficient
  Top-20 System and Data Centre", *J. Phys.: Conf. Ser.* **256** 012026, 2010.
  [doi:10.1088/1742-6596/256/1/012026](https://doi.org/10.1088/1742-6596/256/1/012026)

## Licence

MIT for this pipeline. nnU-Net is Apache-2.0; the TotalSegmentator dataset
carries its own terms — check them before redistributing any trained weights,
since the weights' licence follows the training data, not this repo.

The SciNet logo in this README is reproduced from the SciNet documentation wiki,
which invites its use; it is not covered by this repository's MIT licence.

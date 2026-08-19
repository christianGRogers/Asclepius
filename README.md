# segmentator-train

Training pipeline for **coronary artery segmentation from cardiac CT** — the
coronary tree by major branch, nnU-Net v2, with the run visible live inside 3D
Slicer.

The method follows Akinci D'Antonoli & Wasserthal et al., *TotalSegmentator MRI*
(Radiology 2025, [doi:10.1148/radiol.241613](https://doi.org/10.1148/radiol.241613)):
**nnU-Net with its self-configured defaults and no hyperparameter tuning**, and
the structure set **split across several models** rather than one network over
everything. Applied here to CCTA.

The pipeline is the deliverable, not just the weights. It lives in its own repo,
separate from the inference extension that will eventually ship the model.

Training runs on [SciNet](https://www.scinet.utoronto.ca/)'s Trillium
supercomputer — see [Running on SciNet](#running-on-scinet) and
[Acknowledging SciNet](#acknowledging-scinet).

---

## What it does

```
your labelled CCTA        nnU-Net raw            training                 Slicer
<case>/ct.nii.gz     ──▶  imagesTr/  ──▶ plan ──▶ nnUNetTrainer_segtrain ──▶ events.jsonl ──▶ monitor
<case>/segmentations/     labelsTr/                       │                       ▲
  one mask per vessel       1 multilabel                  └── preview daemon ─────┘
    (or labels.nii.gz)                                        (infers + scores held-out cases)
```

The trainer never talks to Slicer. It appends to `events.jsonl`; Slicer polls
that file. So a run can be attached to late, detached from, or watched from
another machine, and nothing the monitor does can disturb training.

---

## Phase 1: the coronary model

One high-resolution model over the four major branches. **There is no
low-resolution model, and there will not be one.**

| Task | Classes | Spacing | |
|---|---|---|---|
| `Dataset710_Coronary` | 4 | native (~0.35–0.5 mm) | `left_main`, `left_anterior_descending`, `left_circumflex`, `right_coronary_artery` |

That is not a stylistic preference. A distal LAD is 1.5–2 mm across, so at the
3 mm spacing an overview model would use, it is sub-voxel — the model would be
trained to predict a structure thinner than the grid it predicts on. The same
reasoning rules out nnU-Net's `3d_cascade_fullres`, whose low-resolution first
stage downsamples just as aggressively.

`spacing: native` means nnU-Net's own median-spacing rule picks the target. It
already computes the finest spacing the data supports, from *your* CCTA rather
than from an assumption about it. The task sets `max_spacing_mm: 0.5` to close
the one hole that leaves: the rule takes the dataset **median**, so a handful of
thick-slice studies drags the target coarse and interpolates the thinnest vessels
away before training starts. Nothing fails when that happens — preprocessing
succeeds, training runs, and the model just never learns the distal branches.
`segtrain plan` warns instead.

`configs/labels/coronary_ext.yaml` adds `ramus_intermedius` and
`posterior_descending_artery` as indices 5 and 6. It is a strict superset, so the
two sets share an output-channel prefix. Use it only if your labelling actually
distinguishes them — both are anatomically optional, so their per-class Dice is
computed over a minority of cases and will look far noisier than the four main
branches. That is the anatomy, not the model.

**Finer labels are a new label set and a new dataset id, never an edit to the
existing one.** Splitting `left_anterior_descending` into proximal/mid/distal
renumbers everything after it, and a model trained against the old file would
keep loading without complaint while predicting the wrong vessel for every voxel.
Nothing downstream can detect that.

## Phase 2: regional models

Whole-body regions, at 1.5 mm, trained on TotalSegmentator v2.0.1 — which
contains **no coronary structures at all**, so these share no data with phase 1
and are not on its critical path.

| Task | Classes | Why |
|---|---|---|
| `Dataset702_Organs` | 26 | Soft-tissue organs |
| `Dataset703_Vertebrae` | 25 | C1–S1 |
| `Dataset704_Cardiac` | 18 | Heart and great vessels |
| `Dataset705_Muscles` | 10 | Gluteals, autochthon, iliopsoas |
| `Dataset706_Bones` | 38 | Ribs, sternum, limb and pelvic bones, skull |

The five groups partition all 117 TotalSegmentator structures exactly — enforced
by a test, not by care. Those label files are generated from the dataset itself:

```bash
python scripts/gen_label_configs.py /data/Totalsegmentator_dataset_v201
```

The coronary label sets are hand-written instead, for the reason above: there is
nothing in TotalSegmentator to generate them from.

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

## Your coronary data

Phase 1 trains on your own labelled CCTA. If you are still *producing* those
labels, see [SegQueue](#segqueue-labelling-at-scale) — the annotation platform in
this repo, which collects them from a team of annotators.

Lay the result out one directory per case, in either of two forms — the choice is
detected per case, so a dataset part-way through relabelling still works:

```
<root>/<case>/ct.nii.gz                            # or image.nii.gz, or <case>.nii.gz
<root>/<case>/segmentations/left_main.nii.gz       # one binary mask per vessel
<root>/<case>/segmentations/left_circumflex.nii.gz
  ... or ...
<root>/<case>/labels.nii.gz                        # one integer volume
```

Prefer the per-vessel form when you have it: it distinguishes "this vessel was
not labelled in this case" from "this vessel is not present", which a merged
integer volume has already thrown away. `segtrain convert` reports absent
structures per case.

For the single-file form, tell the label set which integer means which vessel:

```yaml
# configs/labels/coronary.local.yaml
source_values:
  left_main:                7
  left_anterior_descending: 2
  left_circumflex:          4
  right_coronary_artery:    1
```

This matters more than it looks. An exported segmentation numbers its segments in
the order they were drawn, so reading them positionally mislabels every vessel —
and the conversion reports complete success while doing it. Values the label set
does not account for are dropped and reported loudly rather than passed through
or silently zeroed; a vessel quietly becoming background looks exactly like a
model that failed to learn it.

Then build the index. There is no `meta.csv` until you write one:

```bash
segtrain index --root /data/coronary            # writes <root>/meta.csv
segtrain index --root /data/coronary --dry-run  # see the split first
```

Splits are assigned by **hashing the case id**, not by shuffling. Adding case 200
to a 199-case dataset therefore leaves the first 199 exactly where they were.
Shuffle-and-slice would reassign every case each time the dataset grows, quietly
moving yesterday's test cases into today's training set — nothing would crash,
the model would just score better than it should. Pin specific cases with
`--overrides cases.csv` (`case_id,split`) when you have a reason to.

Re-running `index` over an existing `meta.csv` is refused without `--force`,
because anything already converted or trained was built against the old one.

## Phase 2 data: TotalSegmentator

Only needed for tasks 702–706. [Zenodo record
10047292](https://zenodo.org/records/10047292) — one 22 GB archive that expands
to ~30 GB of subject directories, and it ships its own `meta.csv` with a
published split, so `segtrain index` is not involved.

```bash
python scripts/init_dataset.py --dest /data/Totalsegmentator_dataset_v201
```

It downloads, checks the published MD5, extracts, verifies the result is 1228
subjects with 117 masks each, and deletes the archive (`--keep-zip` to keep it).
Both the download and the extraction resume, and a dataset root that already
looks complete is left alone. Stdlib only, so it works before `pip install -e .`.

On SciNet, download it **on a login or datamover node** — compute nodes have no
outbound internet, so a download submitted to the queue waits for hours and then
fails at the first HTTP request:

```bash
segtrain scinet fetch --task 702     # runs here, not in a job
```

Put it under `$SCRATCH`. `$HOME` and `$PROJECT` are mounted read-only on
Trillium's compute nodes, so a dataset in either is unusable by the job that
needs it. The ~145,000 files are not a quota problem there — `$SCRATCH` allows
25 TB and 10M files — but they are worth deleting once every task has been
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

## Running the coronary model

```bash
segtrain info                              # resolved paths, tasks, whether a GPU exists
segtrain index      --root /data/coronary  # scan cases -> meta.csv
segtrain convert    --task 710             # masks -> one multilabel; images hardlinked
segtrain plan       --task 710 --gpu-mem 24    # fingerprint + plans + splits
segtrain preprocess --task 710
segtrain train      --task 710 --fold 0
segtrain preview    --task 710 --fold 0 --watch    # second terminal, beside the GPU
segtrain status     --task 710 --fold 0 --worst 10
segtrain evaluate   --task 710                     # held-out test set, Dice + NSD
```

**`--gpu-mem` is the flag that matters most here.** nnU-Net sizes patches against
an 8 GB VRAM budget by default, and patch size is the dominant lever on coronary
accuracy — the published ImageCAS benchmark scored 72.0% Dice with 64³ patches
against 80.6% for full-image input on the same data. Small patches cut vessels
into disconnected fragments. On an 80 GB H100 the default leaves most of the card
unused. Note it changes the architecture, so plans made at one budget are not
interchangeable with checkpoints trained under another — pick a number before you
start a long run, not halfway through.

Read `segtrain plan`'s output rather than skipping past it: it prints the target
spacing nnU-Net chose, the patch and batch size that followed, and a warning if
the spacing came out coarser than the task's 0.5 mm floor.

### What "good" looks like

Calibrate expectations before the first run finishes. Published full-volume Dice
for binary coronary lumen sits around **0.82–0.85**, and **inter-observer
agreement between human annotators on this task is about 0.856** — that is the
ceiling, not a target to beat. A four-class per-branch model is a harder problem
than that binary number describes.

Treat anything above ~0.90 as evidence you are evaluating on a cropped region
rather than a whole volume.

Two metric caveats specific to vessels:

- **Dice is brutally harsh on a 3–4-voxel-diameter tube**, where a one-voxel
  boundary error costs proportionally far more than it would on an organ.
- **Dice barely notices a broken vessel.** A tree split in two by a one-voxel gap
  scores almost the same as an intact one, and is useless downstream. Read NSD
  alongside Dice — `segtrain evaluate` computes both.

Do not let nnU-Net's connected-component post-processing near this model. It
prunes all but the largest component for any class that is single-component
across the training labels, and the coronary tree is naturally two or three
disconnected trees plus branches — so that rule deletes valid vessels. This
pipeline never applies it (`segtrain evaluate` scores raw predictions), but if you
run `nnUNetv2_determine_postprocessing` by hand, check what it decided before
believing it.

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
segtrain index          --root $SCRATCH/coronary  # login node: writes meta.csv
segtrain scinet prepare --task 710 --convert      # CPU job: convert + plan + preprocess
segtrain scinet submit  --task 710 --fold 0       # GPU job chain
segtrain scinet status  --task 710 --fold 0 --watch
segtrain scinet queue                             # what's running and why it's pending
segtrain scinet cancel  --task 710 --fold 0
```

`prepare` asks for no GPU. Fingerprinting, planning and preprocessing are CPU and
I/O work, and Trillium's CPU subcluster is 1224 nodes against the GPU
subcluster's 63 — so it is both cheaper against the allocation and usually far
quicker to start.

### Crossing the 24-hour wall

A 1000-epoch run is tens of GPU-hours; the cap is 24. So `scinet submit` doesn't
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

Ask for **one** GPU. Trillium schedules whole GPUs, so one buys a quarter node —
1 H100, 24 of the 96 cores, ~188 GiB — and 2 or 3 are rejected outright. Four
would idle three of them, since nnU-Net trains this on a single device.

But do not leave the card's 80 GB unused. The default plan targets 8 GB of VRAM,
and as noted above patch size is the dominant lever on coronary accuracy — spend
the rest of the card via `segtrain plan --gpu-mem`. Twenty-four cores is enough
that the dataloader keeps up with the larger patches that follows.

**Trillium nodes have no local disk.** `$SLURM_TMPDIR` is a RAM disk, and what
you put in it comes out of the job's own memory. Every "stage your dataset to
node-local NVMe" tutorial is therefore wrong here. `stage_to_tmpdir` is off by
default. Whether to turn it on depends on how big your preprocessed coronary set
is against the ~188 GiB a 1-GPU job holds: at ~0.35 mm isotropic, CCTA volumes
preprocess large, and nnU-Net's `.npz` → `.npy` unpacking roughly doubles them.
Check the size before enabling it. The job script measures the dataset against the
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
   `you@trillium.alliancecan.ca:/scratch/g/grp/you/runs/Dataset710_Coronary__fold0`,
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
    --run-dir /data/runs/Dataset710_Coronary__fold0
```

---

## SegQueue: labelling at scale

The bottleneck for Phase 1 is not the model, it is **per-segment coronary labels
that do not exist publicly**. SegQueue is the platform for producing them with a
class of undergraduate annotators: a self-hosted server that owns the case pool,
and a Slicer extension that hands one annotator one case at a time.

```
Slicer + SegQueue extension  ──TLS──▶  Caddy ──▶  Girder 5 + SegQueue plugin
   one case at a time                                │        │
   nothing left on disk                            Mongo   /data assetstore
                                                            │
                                                    worker: QA scoring + lease sweep
```

An annotator's whole workflow is: log in, press **Get next case**, segment, press
**Validate & submit**. They never choose a case, never name a file, never see a
server path, and never accumulate data — the local copy is deleted the moment the
server confirms the submission.

Four structures, fixed by the server and obeyed by the extension: `left_main`,
`left_anterior_descending`, `left_circumflex`, `right_coronary_artery`, with the
same label values as [`configs/labels/coronary.yaml`](configs/labels/coronary.yaml).

### The data, and what the presegmentation buys

The default source is the TotalSegmentator release on Zenodo
([record 10047292](https://zenodo.org/records/10047292)) — about 1,200 whole-body
CT studies, each already segmented into 117 structures. Ingest reads those
filenames and never opens an image, which gives two things for free:

* **Only cases with a heart are loaded.** Most of a whole-body dataset is legs,
  heads and abdomens with no coronary anatomy in the field of view. Assigning
  those spends the one resource the project is short of. The eligible cases also
  ship their heart mask to the client, which uses it to centre the views.
* **A case that already carries a `coronary_arteries` mask hands it over.** That
  mask is a binary lumen, not per-branch labels — a head start, not an answer.
  The annotator splits an existing tree into four branches instead of drawing
  one, which is minutes instead of an hour. (The base Zenodo release does not
  include it; if your copy has it, from the licensed task or your own model,
  ingest picks it up with no extra flags.)

Helper masks are structurally incapable of being submitted: the export copies
only the project's own segments, and refuses outright if any other label value
appears in the exported volume.

**Oblique volumes are corrected at ingest.** [Three things that will cost
you](#three-things-that-will-cost-you-if-you-miss-them) notes that 11% of
TotalSegmentator is obliquely acquired and ITK rejects it. Training reads those
with nibabel; an annotator cannot, because Slicer *is* ITK. Ingest
orthonormalises the direction cosines — voxels, spacing and origin untouched,
axes moved by 0.007° — so the case opens, and the same corrected file is what
the training conversion later reads.

### What the extension does for the annotator

The Segment Editor can already do all of this. It is worth wrapping because it
cannot do it *for this task* — a first-year undergraduate should not have to
work out which of twenty effects segments a 3 mm vessel.

* **Four labelled buttons, keys 1–4**, to change branch — with a tick against
  each one that has voxels in it. Built from the server's segment list, so a
  fifth branch is a settings change.
* **Tools that suit a coronary**, on one key each: paint with a 3 mm sphere
  brush sized in millimetres, level tracing, scissors, islands.
* **Masking that makes fast painting safe.** Edits are confined to the existing
  coronary mask when the case has one, and to the opacified range (150–1000 HU)
  otherwise, so a sloppy stroke still leaves a clean lumen edge. Branches never
  overwrite each other.
* **The view set up on arrival**: CTA window/level, four-up layout, slices
  centred on the heart mask, and a surface view a click away.

### Why Girder rather than XNAT or something bespoke

Accounts, tokens, groups, a REST framework, chunked **resumable** uploads,
pluggable storage and an admin UI are all things this project needs and none of
them are things worth writing. Girder supplies them; the plugin under `server/`
adds only what is actually specific to running a workforce — an atomic case
claim, a lease that expires, a review queue, and the sampling that decides whose
work gets looked at. XNAT would have brought a heavier imaging-specific data
model that mostly gets in the way here; a bespoke server would have meant writing
resumable uploads, which is the one part you cannot afford to get subtly wrong.

### What the pieces are

| Path | What it is |
|---|---|
| `src/segqueue/` | State machine, sampling policy, wire protocol, checksums, submission checks. Stdlib-only and Python 3.9-clean, because **both** sides import it |
| `server/girder_segqueue/` | The Girder 5 plugin: models, REST, ingest CLI, QA worker |
| `slicer/SegQueue/` | The annotator's extension. `SegQueueLib/` is Slicer-free, so the network layer and the cache are unit-tested without Slicer |
| `slicer/build-extension.py` | Packages it for the Extension Manager. Plain Python, no CMake |
| `deploy/` | Compose stack, Caddyfile, backup script. See [deploy/README.md](deploy/README.md) |
| `docs/` | [Server runbook](docs/SERVER-SETUP.md) and the [setup &amp; testing guide](docs/SegQueue-Setup-Guide.pdf) |

The shared package is the load-bearing idea. A route name, a state name or a
validation rule cannot drift between client and server, because there is one
definition and both import it — and the submission checks that refuse an empty
segment client-side are the *same function* that refuses it again server-side.

### Quality, without reading every case

Reviewing 5,000 segmentations by hand is not a plan. Four mechanisms instead:

* **A training gate.** Every annotator's first five cases are reviewed by a
  human. Nobody accumulates a hundred cases of a misunderstanding.
* **Gold seeds** (~5%). Cases with an expert reference, indistinguishable from
  ordinary work. Scored automatically with the same Dice and HD95 the training
  pipeline reports — one implementation, so the numbers in the QA dashboard and
  the numbers in the paper cannot disagree.
* **Blind duplicates** (~5%). The same case to two annotators, scored
  symmetrically against each other, which is what inter-rater reliability
  actually means when there is no ground truth.
* **Sampled review** thereafter: 20% falling to 10% for consistently clean work,
  and back up after any rejection. A bad automatic score pulls a case back for a
  human even when the sampling roll had let it through.

Rejections go back to the **same** annotator with the reviewer's comment, which
is the only version of this loop that teaches anyone anything.

### Running it

```sh
cd deploy && cp .env.example .env   # edit DATA_ROOT, SEGQUEUE_DOMAIN
docker compose up -d --build
docker compose exec girder segqueue-ingest --root /incoming --dry-run
docker compose exec girder segqueue-ingest --root /incoming --target coronary
python ../tests/segqueue_e2e.py --url https://<domain>
```

Then build the extension package and hand it to annotators:

```sh
python slicer/build-extension.py     # -> dist/SegQueue-<version>-Slicer-5.8.zip
```

In Slicer: **Extensions Manager → Install from file →** pick that zip → restart.
No pip installs, no build tools, no admin rights, no internet access — the
module uses `requests`, which Slicer already bundles, and the shared `segqueue`
package is vendored into the archive.

Two other routes work for development: add `slicer/SegQueue` to **Additional
module paths** (Edit → Application Settings → Modules), or paste
`exec(open(r"…/slicer/install-segqueue.py").read())` into the Python Console.
Both run the module straight out of the checkout, so a `git pull` updates it.

**Rebuild the package after any change to `src/segqueue`** — the copy inside the
archive is what annotators run, and a stale one speaks an old wire protocol to a
new server. (Not `girder-client`: version 5 requires Python
3.10 and Slicer 5.8 ships 3.9. That constraint is also why `src/segqueue` is
stdlib-only.)

Full deployment, ingest, backup and upgrade notes:
**[docs/SERVER-SETUP.md](docs/SERVER-SETUP.md)**. The annotator-facing setup and
a manual test walkthrough are in
**[docs/SegQueue-Setup-Guide.pdf](docs/SegQueue-Setup-Guide.pdf)**.

### Status

Verified end to end against the real Compose stack, by `tests/segqueue_e2e.py`:
register → assetstore → create annotator → ingest (heart filter, coronary seed) →
assign → download with checksum verification → fetch the heart and coronary masks
→ resumable chunked upload → submit → review → reject with comment → rework as
attempt 2 with the lease renewed → resubmit → approve. Empty segments, stray
marks, off-protocol segments, resampled geometry and mismatched checksums are all
refused with the message the annotator needs, and the 30-annotator concurrent
claim race is tested against real MongoDB.

The Slicer panel is verified against a real Slicer 5.8.1: the packaged extension
installs through the Extension Manager, the module loads from the installed
location, all six offered effects activate, editing is confined to the coronary
seed and to the opacified HU range, branches do not overwrite each other, and an
export with the seed present in the scene excludes it and lands on the source
grid. Two bugs came out of that pass — mask mode silently resetting when set
before the mask segment id, and an empty scene reporting a file-write failure
instead of naming the vessels still to draw.

The join has since been exercised too: against a running stack, the module logs
in, claims an oblique case, downloads it with its heart and coronary masks, loads
all three into the scene, and releases with a purge.

Not yet exercised: a human segmenting a case through to Submit, gold and
duplicate scoring on real label volumes, and anything at 5,000-case scale.

Not yet built: an export from approved submissions into the
[case layout](#your-coronary-data) `segtrain convert` reads. Approved work sits
in the assetstore as label volumes on the source grid — the right *contents*, one
directory rename away from the right *shape* — but the step is manual today.
---

## Three things that will cost you if you miss them

**Oblique volumes are unreadable by nnU-Net's default reader.** SimpleITK rejects
any NIfTI whose direction cosines are not orthonormal to ITK's tolerance — *"ITK
only supports orthonormal direction cosines"* — and obliquely-acquired volumes
stored as float32 routinely fall just outside it. Cardiac CT is frequently
reconstructed on an oblique grid, so this is not a rare corner. Those cases fail
to preprocess and disappear from the training set quietly; in TotalSegmentator it
is 136 of 1228 volumes, 11.1%, and unevenly distributed across study types.
`convert` therefore writes `overwrite_image_reader_writer:
NibabelIOWithReorient` into `dataset.json`. Do not remove it.

**Independently drawn masks overlap.** A multilabel volume needs one owner per
voxel, but masks drawn per structure disagree by a voxel or two at shared
interfaces — for the coronary tree, the LM/LAD and LM/LCx bifurcations and the
RCA/PDA continuation. The default `overlap_policy: smaller_wins` gives contested
voxels to the smaller structure, so a thin distal vessel is not eroded by the
trunk it branches from. The alternative, `label_order`, is alphabetical and
therefore anatomically arbitrary; it exists only to measure the difference.
(A single integer label volume has no overlaps to resolve — the exporter already
picked a winner, and you cannot see what it discarded.)

**A vessel absent from a case is not the same as a vessel not labelled.** The
`ramus_intermedius` genuinely does not exist in most people, and the PDA comes off
the LCx rather than the RCA in a left-dominant heart. Leave the mask out rather
than writing an empty one; `convert` reports absent structures per case, which is
the signal you want. An empty mask is indistinguishable from a labelling
oversight.

---

## Disk

The coronary figures depend on your case count and reconstruction, so measure
rather than trust an estimate — CCTA at ~0.35 mm isotropic preprocesses large, and
nnU-Net's `.npz` → `.npy` unpacking roughly doubles it while training. The
TotalSegmentator numbers below are measured, and are the phase 2 figures:

| | |
|---|---|
| Source images (1228) | 21.0 GB |
| Source masks (117 × 1228) | 9.1 GB |
| Merged multilabel labels | **~0.3–0.7 GB** — the merge is nearly free |
| Images in `nnUNet_raw` | **0 bytes** via hardlink on the same filesystem |
| Preprocessed @ 1.5 mm, per task | ~75 GB (up to ~110 GB peak on nnU-Net ≤ 2.5, which keeps both `.npz` and unpacked `.npy`) |
| Checkpoints | ~1 GB per fold per task |

So provision **~250 GB** for all five phase 2 tasks — or ~110 GB if you preprocess
one group at a time and delete between them. Five-fold CV multiplies GPU time by
five but adds only ~25 GB, since folds share preprocessed data.

`--npz` is **off by default**. It writes float16 softmax per class per voxel —
hundreds of GB across a multi-class dataset — and is only needed to build a
cross-fold ensemble.

---

## Splits

For your coronary data, `segtrain index` writes `meta.csv` with a hash-derived
split (15% val / 15% test by default). See [Your coronary data](#your-coronary-data)
for why hashing rather than shuffling. Test cases never enter `imagesTr`, so no
training, model-selection or postprocessing decision can see them.

- `--scheme official` (default) — one fold, using the `val` column as written.
- `--scheme cv5` — stratified 5-fold over the non-test cases, balanced by
  `study_type`. Use only if you intend to train and ensemble five models.

For phase 2, TotalSegmentator's `meta.csv` carries its published split — **1082
train / 57 val / 89 test** — and `--scheme official` reproduces that boundary
exactly, so those results stay comparable to the paper.

`validate_splits` fails loudly on train/val overlap or test leakage, and preview
cases are checked to be genuinely held out — a preview rendered on a training
case looks great and means nothing.

---

## Tests

```bash
pytest                    # 366 tests
pytest -m "not slow"      # skip the full-case merge round-trip

# The SegQueue concurrency tests need a real MongoDB -- the whole point of them
# is that the atomic claim survives thirty annotators starting at once, which no
# fake can demonstrate. 19 more tests.
docker run -d --rm -p 27099:27017 mongo:7
SEGQUEUE_TEST_MONGO=mongodb://localhost:27099 pytest tests/test_segqueue_server.py
```

Tests needing a dataset are marked `needs_data`, and those needing a database
`needs_mongo`; both skip without them, so the suite runs on a checkout alone.

---

## Status

**Phase 1 has no training data in this repo yet.** The pipeline, the coronary
label sets and the task are in place; supply your own labelled CCTA as described
under [Your coronary data](#your-coronary-data).

Worth knowing before you go looking for a shortcut: **no public dataset provides
per-segment coronary labels on 3D CCTA.** The large public sets — ImageCAS
(1000 cases), ASOCA (60) — ship a single merged binary lumen mask. ImageCAS's
paper mentions AHA 17-segment naming, but that describes which vessels were
included in the annotation *extent*, not separate label values; the released
label file is 0/1, and the paper says so twice. TotalSegmentator's
`coronary_arteries` task is one binary class and sits behind a licence key. The
only genuinely per-segment public labels are 2D X-ray angiography (ARCADE, CC0),
which is the wrong modality. So hand-labelling, or deriving segments from a
binary model plus centreline tree labelling, is the real path.

Verified end to end on CPU with a 24-case subset of TotalSegmentator: convert →
plan → preprocess → train → preview → status, plus the Slicer module against a
real run (91 segments imported with correct anatomical names).

Unit-tested but never run against real infrastructure: the SLURM layer (script
rendering, walltime arithmetic, chain wiring, the resume decision) against
Trillium's scheduler, and the index/convert paths against a real CCTA tree. Also
unexercised: the 1000-epoch schedule, multi-GPU, and `evaluate` at scale.

Known deviations from nnU-Net defaults worth considering later, deliberately not
taken yet because the stated method is defaults-only: a **topology-aware loss**
(clDice, or cbDice which corrects clDice's bias toward large-diameter vessels and
ships as an nnU-Net v2 plugin) is the standard upgrade for vessel segmentation,
and **graph-based reconnection** of broken vessels as a post-processing stage is
what the strongest published coronary results add on top.

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

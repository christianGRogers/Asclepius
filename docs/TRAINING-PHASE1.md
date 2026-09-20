# Phase 1 on Trillium: the binary lumen model

Everything needed to get a coronary lumen model training on SciNet, from a
fresh account to a running job chain. Start to finish this is an afternoon of
attention plus however long the queue takes.

The reasoning behind the configuration is in the Obsidian vault at
[`vault/Training method/Training plan.md`](../vault/Training%20method/Training%20plan.md);
what the research has since argued should change is in
[`vault/Proposed changes to the training plan.md`](../vault/Proposed%20changes%20to%20the%20training%20plan.md).
This document is the runbook and does not repeat either.

---

## 1. Two runs, and why they are not the same run

Phase 1 is a binary lumen model — one foreground class, because that is all the
source labels contain. It is trained twice, on two different sets of labels,
for two different reasons.

| | Task | Labels | Test set | Comparator |
|---|---|---|---|---|
| **Run A** | `710_CoronaryLumen` | The original 1000 ImageCAS masks | ImageCAS official `Split-1`, 250 cases | 82.96 % Dice |
| **Run B** | `711_CoronaryLumenX` | ImageCAS-X re-annotated lumen, 800 cases | ImageCAS-X, 160 cases | nnU-Net 89.8, ceiling 92.8 |

**Run A is the chain test.** Its real purpose is to prove that convert → plan →
preprocess → train across three chained 24-hour blocks → resume → evaluate
works on Trillium. Finding out that it does not with the multiclass model would
cost a term; finding out here costs one queue wait. Its second purpose is the
only meaningful comparison to the published 82.96 %, which was measured on
exactly these labels and this split.

**Run B is the model you keep.** Its predictions become the presegmentation
seeds SegQueue hands annotators.

Run A's labels disagree with a re-annotation of the same scans at **41.8 %
Dice**, and include plaque, pulmonary vessels and coronary veins
(Bransby et al., arXiv:2608.30404). A model trained on them learns those
errors. Seeding an annotator with a mask that confidently outlines a pulmonary
vein is worse than seeding them with nothing, because a seed is trusted. So run
A validates the chain and produces a number; it does not produce seeds.

> **Leakage, and it is easy to trip.** If run B's checkpoint is ever used to
> initialise the multiclass model, run B's training set must exclude
> ImageCAS-X's 160 test cases. Otherwise the multiclass test set has leaked in
> through initialisation, and nothing downstream will detect it.

---

## 2. Before anything else

```sh
segtrain scinet check
```

Reads the config, resolves every path, and refuses on the things that cost a
queue wait to discover:

- **Every path must be under `$SCRATCH`.** On Trillium `$HOME` and `$PROJECT`
  are mounted read-only on compute nodes, so a job whose results root is in
  either dies on its first write — after it has waited in the queue.
- **`account` must be set.** SLURM rejects a job with no `--account` once you
  belong to more than one allocation. `sshare -U` lists yours.
- **The venv must exist and be in `$HOME`.** Compute nodes can read `$HOME`;
  `$SCRATCH` "may get partially deleted" and `$SLURM_TMPDIR` is a RAM disk.

Build the venv once, on a login node:

```sh
segtrain scinet setup
```

---

## 3. Get the data onto `$SCRATCH`

**Run A** — ImageCAS, 1000 cases. Two files per case in one directory:

```
$SCRATCH/imagecas/1.img.nii.gz
$SCRATCH/imagecas/1.label.nii.gz
```

**Run B** — ImageCAS-X, 800 cases, CC BY 4.0, Zenodo
[10.5281/zenodo.21887809](https://doi.org/10.5281/zenodo.21887809). The archive
also ships centerlines, mesh surfaces, scan-level descriptors and pretrained
weights for six methods. Phase 1 reads only the lumen annotation.

`segtrain index` understands both the flat form above and one-directory-per-case,
and auto-detects which it is given. Force it with `--layout flat` or
`--layout nested` if the guess is ever wrong.

---

## 4. Index the cases

```sh
segtrain index --root $SCRATCH/imagecas
```

This writes `meta.csv`: one row per case, with a split. Everything downstream
reads that file and nothing else, so this is the only step that cares how the
data was laid out on disk.

Splits are assigned by **hashing the case id**, not by shuffling. Adding case
1001 to a 1000-case dataset therefore leaves the first 1000 exactly where they
were. Shuffle-and-slice would silently reassign cases every time the dataset
grew, moving yesterday's test cases into today's training set and invalidating
every number already measured — with nothing crashing to tell you.

### Honouring ImageCAS's official split (run A only)

The 82.96 % figure is only comparable on ImageCAS's own `Split-1`. Write that
split out as a two-column CSV:

```
case_id,split
1,train
2,test
...
```

and pass it:

```sh
segtrain index --root $SCRATCH/imagecas --overrides official-split1.csv --force
```

Pinned cases are placed exactly as the file says; everything unlisted is
hashed as usual. The summary line reports how many were pinned, so a
half-parsed file is visible rather than silent.

Do **not** re-roll `--seed` until a split looks good. That is choosing a test
set by looking at it.

---

## 5. Convert, plan, preprocess

These are CPU work and belong in a CPU job — Trillium's CPU subcluster is 1224
nodes against the GPU subcluster's 63, so it usually starts much sooner.

```sh
segtrain scinet prepare --task 710 --convert
```

### Read the planner printout before you submit anything

`segtrain plan --task 710 --gpu-mem 70` needs no GPU, and four things in its
output decide whether the GPU job is worth submitting:

| Check | Want | Why |
|---|---|---|
| **Patch fraction** | ≥ 25 % | nnU-Net's real `lowres_creation_threshold` is 0.25, verified in source at `v2.5.1`, `v2.6.2` and `master`. Below it a `3d_lowres` stage gets planned. |
| **Target spacing** | native, ~0.29–0.45 mm | nnU-Net takes the *median* spacing. A few thick-slice studies drag it coarse and interpolate away the vessels this exists to find. `max_spacing_mm: 0.5` in the task config refuses that outright. |
| **Batch size** | 2 | |
| **Anisotropy branch** | not fired | If it fires, through-plane resampling drops to nearest-neighbour for image *and* label — the mode most likely to destroy a 1–2 voxel vessel cross-section. |

A `3d_lowres` entry appearing in the plans file is harmless on its own:
`configuration: 3d_fullres` decides what trains. Limit preprocessing with
`-c 3d_fullres` if you would rather not spend the disk.

---

## 6. Submit the GPU chain

```sh
segtrain scinet submit --task 710 --fold 0
```

The 24-hour walltime cap is shorter than a full nnU-Net schedule, so the run is
a **chain**: the whole chain is submitted from the login node at once (Trillium
forbids a job from submitting anything), each block resumes from the last
block's checkpoint, and the trainer stops cleanly at an epoch boundary before
the wall rather than being killed mid-write.

- `chain_mode: array` — one `sbatch --array=1-N%1`. The default.
- `chain_mode: dependency` — N jobs each `--dependency=afterany` on the last.
  Use if job arrays turn out to be restricted.
- `chain_max: 3` — three blocks of 23:50 is about 71 hours. Raise it if a
  larger patch pushes epoch time up.

`pause_margin_seconds` is subtracted from the walltime to get the trainer's
budget. It has to cover module load, the venv, nnU-Net unpacking, one whole
epoch, and a ~400 MB checkpoint write.

### Watching it

```sh
segtrain scinet status --task 710 --fold 0 --watch
```

Reads `events.jsonl` from the run directory. The login nodes share `$SCRATCH`
with the compute nodes, so this is the live file the job is writing — there is
no staging step and nothing to synchronise.

For a chained run that file is also the only evidence block 1 ever existed,
which is why it is append-only and survives the job that wrote it.

---

## 7. Evaluate

```sh
segtrain evaluate --task 710
```

Scores raw predictions. `nnUNetv2_determine_postprocessing` is **not** run: its
largest-component rule deletes real vessels, because the coronary tree is
naturally several disconnected components and the rule's acceptance criterion
is expressed in Dice, which barely moves when a 3-voxel branch disappears. If
it is ever run by hand, audit what it selected before believing it.

Run A is comparable to 82.96 % only on the official split. Run B is comparable
to ImageCAS-X's table, on their 160-case test set: nnU-Net 89.8 ± 3.2, CAS-Net
91.2 ± 2.8, inter-observer 92.8 ± 3.1. **Do not compare the two runs to each
other** — different labels, different split, different task in every way that
matters.

---

## 8. Acknowledgement

Publications using this compute carry SciNet's
[requested acknowledgement](https://docs.scinet.utoronto.ca/index.php/Acknowledging_SciNet)
and cite Ponce et al. 2019 and Loken et al. 2010. See the repository README.

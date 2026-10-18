---
aliases: [Compute inventory, Compute inventory 2026-10]
tags: [plans, experiment, compute, trillium, icx4]
status: Fir chosen by the lead; waiting on the lead (account facts)
updated: 2026-10-18
issue: christianGRogers/Asclepius#46
---

# Compute inventory: Nibi or Fir can run icx4 unchanged on def-aso22; the AI clusters need an aip- allocation

**Question.** The lead's Trillium allocation is used up for this week. Which other resources can the project use
(Killarney, Vulcan, tamIA, Fir, Nibi, HPSS), and where should icx4 (#43) run this week?

**Answer.**
- **Fir and Nibi** are general-purpose Alliance clusters. Both take the PI's existing default account
  `def-aso22`, have full **H100 80 GB** GPUs, allow up to **7-day** jobs and give compute nodes internet access.
- icx4 runs on either with **one change**, made in this PR: the job header has to name a full H100 and ask for
  cores and memory. Without that change the job gets 1 core and 256 MB, and may land on a 40 GB MIG slice.
- **Killarney, Vulcan and tamIA** do not accept `def-` accounts. Each needs an `aip-` project, which the PI can
  create in CCDB, but none is a good fit this week:
  - Killarney: only 80 H100s, and its job rules are undocumented.
  - Vulcan: L40S 48 GB only, too small for the 60 GB plan.
  - tamIA: whole 4-GPU nodes, ≤ 24 h.
- **HPSS** is a tape archive reachable from Trillium only. It is no use for staging data to a GPU job.
- The Alliance docs describe **no weekly cap on Trillium**. Past use only lowers priority (fairshare, one-week
  half-life), so submitting on Trillium is still an option, with a longer wait.

All facts below were read on **2026-10-18** from the pages linked, unless marked *(lead to confirm)*.

## The table

| Resource | GPUs for a 1-GPU job | Max walltime | Allocation / eligibility | Storage (per user unless noted) | Compute-node internet | Fit for icx4 |
|---|---|---|---|---|---|---|
| **Trillium** (reference) | 63 nodes × 4 H100 SXM 80 GB; 1 GPU = ¼ node, 24 cores, ~188 GiB; no MIG [T] | 24 h [T] | `def-aso22` (RAS); fairshare, no weekly quota documented [J][A] | HOME 100 GB, PROJECT 1 TB (both read-only on compute), SCRATCH 25 TB [T] | No [T] | As built. Only the queue wait is in question. |
| **Nibi** (Waterloo) | 36 nodes × 8 H100 SXM 80 GB = 288; bundle **14 cores / 250 GB** per GPU; ~half the nodes MIG (1g.10gb, 2g.20gb, 3g.40gb) [N][G][B] | 7 days, partitions chosen by walltime [J] | `def-aso22` works. Opt in once at CCDB → Resources → Access Systems (≤ 1 h) [N] | HOME 50 GB; SCRATCH 1 TB soft (may exceed for 60 days) / 20 TB hard, **no age purge**; PROJECT 1 TB per group [N][S] | **Yes**, all nodes [N] | **Good.** Header change (this PR). Copy `cases/` over. |
| **Fir** (SFU) | 160 nodes × 4 H100 SXM5 80 GB = 640; bundle **12 cores / 280 GB** per GPU; ~half the nodes MIG [F][G][B] | 7 days, by walltime [F][J] | `def-aso22` works; CCDB opt-in [F] | HOME 50 GB; SCRATCH 20 TB, **60-day purge**; PROJECT 1 TB per group [S][P] | **Yes** [F] | **Good.** Same as Nibi. 2 fewer cores per GPU. |
| **Rorqual** (ÉTS; not asked, listed for completeness) | 93 nodes × 4 H100 SXM5 80 GB; bundle **16 cores / 124 GB** per GPU [R][B] | 7 days, min 1 h [R] | `def-aso22`; CCDB opt-in plus Calcul Québec agreements [R] | Like Fir: SCRATCH 20 TB with 60-day purge [R][S] | No (login node has it) [R] | Works. Most cores per GPU, least RAM. Extra sign-up. |
| **Killarney** (Vector, Toronto) | 168 nodes × 4 **L40S 48 GB**; 10 nodes × 8 **H100 SXM 80 GB** = 80 H100 [K] | **Not stated** | **`aip-` project required.** A PI without a Vector affiliation creates one at CCDB → Resources → *General Access to PAICE Systems* (tier 3 AI research, or **tier 4 "applying AI", 5 % of fairshare split among all tier-4 projects**) [AP][PA] | HOME 50 GB; SCRATCH 250 GB (tier 4) to 2 TB (tier 1), 2-month expiry; PROJECT 500 GB (tier 4) [S] | Implied yes (the wandb page says no proxy needed) [W] | **Not this week.** Needs an aip- project. Few H100s. Partition rules unknown. |
| **Vulcan** (Amii, Edmonton) | 252 nodes × 4 **L40S 48 GB**; no H100 [V] | 7 days [V] | `aip-` project required (same route) [V][AP] | HOME 50 GB; SCRATCH 5 TB, 2-month expiry; PROJECT 5 TB (tier 4) [S] | Whitelisted proxy only [V] | **Poor.** 48 GB < 60 GB plan: needs a re-plan (smaller patch or plan), so it would no longer be the same model. |
| **tamIA** (Mila / Laval) | 53 nodes × 4 H100 80 GB; 12 nodes × 8 H200 141 GB. **Whole nodes only; a job must use all 4 (or 8) GPUs** [TA] | **24 h** [TA] | `aip-` project required [TA][AP] | HOME 25 GB (no backup); SCRATCH 500 GB (tier 4); PROJECT 500 GB (tier 4) [S] | No [TA] | **Poor.** A 1-GPU job would hold 4 H100s (×4 the share use). It would need a 4-GPU DDP rewrite. |
| **HPSS** (SciNet tape) | — (archive, not compute) [H] | Archive jobs: `archiveshort` 1 h, `archivelong` ≤ 72 h [H] | Needs a SciNet storage award > 5 TB, **or ask support@scinet.utoronto.ca for ≤ 2 TB per group** [H] | Tape, dual copies. Bundle files < 200 MB with `htar`. Aim for > 1 GB average; tarballs ≤ 500 GB–1 TB [H] | — | **Not for staging.** Recall is a tape job to Trillium's scratch. Use it only to archive finished checkpoints and predictions. |

Software on every Alliance cluster is the same CVMFS stack: `StdEnv/2023`, wheels with `pip install --no-index`,
and Apptainer via `module load apptainer` [SW][PY][AT]. icx4 loads `StdEnv/2023 python/3.11.5 cuda/12.6` and installs
torch from the wheelhouse plus `nnunetv2==2.8.1` from PyPI on the login node. This should work on Fir, Nibi and
Rorqual as on Trillium *(lead to confirm with the module commands below)*. The PAICE pages say they run "the
standard Alliance software stack", but no page states the StdEnv version for Killarney or Vulcan.

### Sources (all read 2026-10-18)

- [T] https://docs.alliancecan.ca/wiki/Trillium and https://docs.alliancecan.ca/wiki/Trillium_Quickstart
- [N] https://docs.alliancecan.ca/wiki/Nibi
- [F] https://docs.alliancecan.ca/wiki/Fir. Its node table says 4 H100 per node; its "GPU layout" section says 2.
  The table is taken as correct.
- [R] https://docs.alliancecan.ca/wiki/Rorqual
- [K] https://docs.alliancecan.ca/wiki/Killarney and https://alliancecan.ca/en/services/compute/killarney
- [V] https://docs.alliancecan.ca/wiki/Vulcan. The services page https://alliancecan.ca/en/services/compute/vulcan
  still says 205 nodes, which is out of date.
- [TA] https://docs.alliancecan.ca/wiki/TamIA/en and https://alliancecan.ca/en/services/compute/tamia
- [AP] https://docs.alliancecan.ca/wiki/Accessing_the_PAICE_clusters (marked *Draft*)
- [PA] https://docs.alliancecan.ca/wiki/PAICE_Allocations_and_compute_scheduling (marked *Draft*)
- [G] https://docs.alliancecan.ca/wiki/Using_GPUs_with_Slurm
- [B] https://docs.alliancecan.ca/wiki/Allocations_and_compute_scheduling#Ratios_in_bundles
- [A] https://docs.alliancecan.ca/wiki/Allocations_and_compute_scheduling
- [J] https://docs.alliancecan.ca/wiki/Job_scheduling_policies. "Past usage is discounted with a half-life of one
  week."
- [S] https://docs.alliancecan.ca/wiki/Storage_and_file_management
- [P] https://docs.alliancecan.ca/wiki/Scratch_purging_policy
- [W] https://docs.alliancecan.ca/wiki/Weights_%26_Biases_(wandb)
- [H] https://docs.scinet.utoronto.ca/index.php/HPSS
- [SW] https://docs.alliancecan.ca/wiki/Available_software
- [PY] https://docs.alliancecan.ca/wiki/Python
- [AT] https://docs.alliancecan.ca/wiki/Apptainer
- [RJ] https://docs.alliancecan.ca/wiki/Running_jobs. "On general-purpose (GP) clusters, a default memory amount
  of 256 MB per core will be allocated unless you make some other request."

## Porting icx4: what is Trillium-specific

| Item in `trillium/icx4` | On Trillium | Fir / Nibi / Rorqual | Status |
|---|---|---|---|
| GPU request `--gpus-per-node=1` | Whole H100, no MIG | Untyped. May be given a MIG slice (≤ 40 GB) | **Fixed in this PR:** `h100:1` |
| No `--cpus-per-task`, no `--mem` | Trillium gives 24 cores and ~188 GiB anyway | **1 core, 256 MB per core** [RJ]. `job_body.sh` reads `$SLURM_CPUS_ON_NODE`, so it would plan `-np -1` and fail | **Fixed:** the bundle per GPU (12/280G, 14/250G, 16/124G) |
| Account `def-aso22` | Yes | Same RAS account on all general-purpose clusters (`ACCOUNT=` override still there) | Unchanged |
| Walltime 23:50 + 4-job chain, deadline stop at 23:35 | Trillium max 24 h | Allowed (24 h partition). A single 72 h job would also fit, but the chain is tested, so keep it | Unchanged |
| Login node does all internet (Zenodo, pip) | Required | Works; compute nodes also have internet on Fir/Nibi | Unchanged |
| Writes `$SCRATCH` only; venv in `$HOME/icx14-venv` | Required | `$SCRATCH` is set on every Alliance cluster. The venv does not exist yet, so the first run builds it (a few GB of the 50 GB HOME) | Unchanged |
| Data path: walks up to `<root>/cases/` | Lead's copy on Trillium | **`cases/` must be copied** to the new cluster's scratch (Globus `alliancecan#trillium` → `alliancecan#nibi` / `alliancecan#fir-globus`) | Lead action |
| ResEnc 60 GB plan, 256³ patch, batch 2 | 80 GB H100 | Same GPU, so the same plan and the same model | Unchanged |
| Data loading: 22 augmentation workers | 24 cores | 10 (Fir), 12 (Nibi), 14 (Rorqual) workers | **Risk, see below** |
| Error and help text naming Trillium | — | Cosmetic | Reworded |

**Cluster choice in the launcher.** The launcher picks the job shape from `ICX4_CLUSTER` if set (strict: `trillium`,
`fir`, `nibi` or `rorqual`). Otherwise it checks `$CC_CLUSTER` and the login host name for those names. Anything
it does not recognise falls back to Trillium, so a Trillium run is unchanged. A dry run of every profile
(`ICX4_DRYRUN=1`) printed the expected headers. `ICX4_CLUSTER=foo` stops with an error.

**Throughput risk (fewer cores per GPU).** icx14 job 1 on Trillium: ~187 s per epoch (446 epochs in 23.2 h), about
0.75 s per training step. Atlas estimated nnU-Net's augmentation at ≈ 6 CPU-s per batch of two 256³ patches
([[Atlas - A 256³ training step costs 69 TFLOP, and the CPU loader may set the pace]]). That gives:

| Cluster | Workers | Time to augment one batch | Compared with the 0.75 s GPU step |
|---|---|---|---|
| Trillium | 22 | ≈ 0.27 s | Comfortably GPU-bound |
| Nibi | 12 | ≈ 0.5 s | Probably still GPU-bound |
| Fir | 10 | ≈ 0.6 s | Probably still GPU-bound, closer to the limit |

The CPU estimate is uncertain by about 2× (it was measured on a loaded 4-core machine). Plan for **50–70 GPU-hours**
on Nibi or Fir instead of ~50, i.e. 3 jobs of the 4-job chain, possibly all 4. `./icx4 status` shows s/epoch
after the first hours. If it is above ~250 s, the extra jobs are chained anyway.

## Fir: facts a training plan needs

The lead has chosen **Fir** (relayed by the PM, 2026-10-18). Sources: [F], [J], [S], [P], [B], [G] and the wheel list
[WH] https://docs.alliancecan.ca/wiki/Available_Python_wheels, all read 2026-10-18.

| Topic | Fact | Source |
|---|---|---|
| GPU nodes | 160 nodes, each **4 × H100 SXM5 80 GB** (NVLink), 1 × EPYC 9454 (48 cores), 1125 G RAM, **7.84 TB local NVMe** | [F] |
| Per-GPU share | Bundle **12 cores / 288 GB**, recommended **12 cores / 280 GB**; "no more than 12 CPU cores" per GPU. Each NUMA domain is 12 cores beside one GPU; the docs suggest `--cpus-per-task=12` per GPU task (or 6, one CCD) | [B][G][F] |
| GPU request | `--gpus=h100:1` (one), `--gpus-per-node=h100:N` (several). About half the GPU nodes are MIG (1g.10gb, 2g.20gb, 3g.40gb); an untyped request may get one | [F] |
| Walltime | **7 days (168 h) max**; at least 1 h (5 min for tests). Partitions are picked by walltime (≤ 3 h, 12 h, 24 h, 72 h, 7 d), nested, so shorter jobs have more nodes; separate by-node and by-core partitions; no `-p` needed | [F][J] |
| Job and GPU limits for `def-` | Not stated in the docs. **The lead's `sacctmgr` output (2026-10-18) shows no MaxJobs, MaxSubmit, MaxTRES or GrpTRES on `def-aso22_cpu` / `def-aso22_gpu`**, so no per-account cap is set. Priority is fairshare with a one-week half-life | [J][A], lead |
| Multi-GPU | 4 GPUs per node with NVLink, so a 1-node DDP run of up to 4 H100s is possible; it costs 4× the fairshare | [F] |
| HOME | 50 GB, 500 K files, backed up | [S] |
| SCRATCH | **20 TB, 1 M files, not backed up; purged when ctime and atime are both > 60 days** (checked month end; warnings on the 1st and 12th; deletion on the 15th; list in `/scratch/to_delete/`) | [S][P] |
| PROJECT | 1 TB, 500 K files per group, backed up; can be raised to 40 TB through RAS. Writable from compute nodes (unlike Trillium) | [S] |
| NEARLINE | 2 TB, 5000 files per group (tape) | [S] |
| Compute internet | Full access from compute nodes | [F] |
| Staging `cases/` | Globus `alliancecan#trillium` → **`alliancecan#fir-globus`**; for rsync/scp use the login node `fir.alliancecan.ca` (no separate transfer node yet) | [F] |
| Local disk | `$SLURM_TMPDIR` on the 7.84 TB NVMe, shared by the jobs on a node, wiped at job end | [F][S] |
| Software | CVMFS `StdEnv/2023`; wheelhouse `torch` **2.10.0–2.14.1**; wheelhouse `nnunetv2` **2.5.1 and 2.1 only**. icx4 pins **2.8.1 from PyPI**, which works because Fir has internet. Apptainer via `module load apptainer` | [WH][SW][AT] |
| Access | Opt in once at CCDB → Resources → Access Systems → Fir (up to 1 h) | [F] |

What this means for a plan:
- **Keep a durable copy of `cases/` in PROJECT if it fits under 1 TB**, and work from SCRATCH. A copy left untouched
  for 60 days in SCRATCH is purged.
- A 1-GPU job gets 12 cores, half of Trillium's 24. That leaves ~10 augmentation workers, so expect 50–70 GPU-hours
  for 1000 epochs (see the throughput risk above).
- One 7-day job could replace the 4-job chain. The chain still fits the 24 h partition, which has more nodes, so it
  is likely to start sooner.

To confirm the limits, the lead runs on `fir.alliancecan.ca`:

```sh
sacctmgr -n show assoc where user=$USER format=account%20,maxjobs,maxsubmit,maxtres%40,grptres%40
```

## What it changes

- icx4 can run this week on **Nibi** (recommended) or **Fir** with the same account, GPU and recipe. The model is
  unchanged (same plan, patch, epochs, splits). Only the cluster changes, so its results stay comparable with icx14.
- The PAICE clusters are a later option only. The PI would create a tier-4 `aip-` project (a decision for the
  lead). Even then, its share is small and the GPUs (L40S 48 GB) or job rules (4-GPU nodes) do not suit this
  recipe.
- HPSS is not worth setting up now. If the project later wants an off-cluster copy of finished models and
  predictions, the lead can ask SciNet for the 2 TB starter quota.

## Account-specific facts *(Fir from the lead's output, 2026-10-18; others still to come)*

**Fir, what the output means for icx4:**
- **Account:** jobs keep `--account=def-aso22`. On Fir, Slurm charges a GPU job to `def-aso22_gpu` and a CPU job to
  `def-aso22_cpu` *(the usual Alliance mapping; the first `sbatch` confirms it)*.
- **Partition:** a 23:50 one-GPU job lands in `gpubase_bygpu_b3` (24 h).
- **Priority:** nothing has been used on Fir yet, so priority is as high as it gets.
- **Still missing:** the output of `partition-stats`, the module load and `avail_wheels`. The paste ended at
  `sinfo`'s 40-line `head`. The PROJECT space is also absent from `diskusage_report`.

| Cluster | Can log in? | `sshare` accounts | Scratch used / quota | H100 partitions (from `sinfo`) | Modules load? | `cases/` size |
|---|---|---|---|---|---|---|
| Trillium | yes | def-aso22 (LevelFS: ?) | ? | — | yes | ? |
| Nibi | ? | ? | ? | ? | ? | — |
| Fir | **yes** (`login3.int.fir.alliancecan.ca`, `CC_CLUSTER=fir`, so `./icx4` picks the Fir profile itself; `SCRATCH=/scratch/croger`) | **`def-aso22_cpu` and `def-aso22_gpu`**: RawUsage 0, FairShare 0.98, LevelFS inf (top priority); no limits set | HOME 36 KiB / 48 GiB; SCRATCH 20 KiB / 19 TiB; **PROJECT not listed** *(ask)* | `gpubase_bygpu_b1` 3 h, `_b2` 12 h, `_b3` 24 h, `_b4` 3 d (`_b5` 7 d cut off by `head`), plus `gpubackfill` 24 h; ~80 full-H100 nodes and ~43 MIG nodes per partition, ~13 drained | *not shown (output cut off)* | — |
| Killarney / Vulcan / tamIA | ? | aip-? | ? | ? | ? | — |

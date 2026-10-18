---
aliases: [Compute inventory, Compute inventory 2026-10]
tags: [plans, experiment, compute, trillium, icx4]
status: waiting on the lead (account facts)
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
| Data path: walks up to `<root>/cases/` | Lead's copy on Trillium | **`cases/` must be copied** to the new cluster's scratch (Globus `alliancecan#trillium` → `alliancecan#nibi` / `#fir`) | Lead action |
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

## What it changes

- icx4 can run this week on **Nibi** (recommended) or **Fir** with the same account, GPU and recipe. The model is
  unchanged (same plan, patch, epochs, splits). Only the cluster changes, so its results stay comparable with icx14.
- The PAICE clusters are a later option only. The PI would create a tier-4 `aip-` project (a decision for the
  lead). Even then, its share is small and the GPUs (L40S 48 GB) or job rules (4-GPU nodes) do not suit this
  recipe.
- HPSS is not worth setting up now. If the project later wants an off-cluster copy of finished models and
  predictions, the lead can ask SciNet for the 2 TB starter quota.

## Account-specific facts *(to be filled in from the lead's output on #46)*

| Cluster | Can log in? | `sshare` accounts | Scratch used / quota | H100 partitions (from `sinfo`) | Modules load? | `cases/` size |
|---|---|---|---|---|---|---|
| Trillium | yes | def-aso22 (LevelFS: ?) | ? | — | yes | ? |
| Nibi | ? | ? | ? | ? | ? | — |
| Fir | ? | ? | ? | ? | ? | — |
| Killarney / Vulcan / tamIA | ? | aip-? | ? | ? | ? | — |

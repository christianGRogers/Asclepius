# Asclepius

Multiclass coronary artery segmentation from CCTA, and the labelling platform
that produces its training data. Two components, one repository:

| | What it is | Where |
|---|---|---|
| **SegQueue** | The labelling app: a Girder server that owns the case pool, and a 3D Slicer extension that hands one annotator one case at a time. In use by a class of annotators, and it updates itself from this repository's releases. | `server/`, `slicer/`, shared protocol in `src/segqueue/` |
| **segtrain** | The training pipeline: nnU-Net v2 data prep, planning, evaluation, and the SciNet job chain. | `src/segtrain/`, `configs/`, `scripts/` |

Start here: **[CONTRIBUTING.md](CONTRIBUTING.md)** for how to set up, test,
branch and release — the release rules in particular, because a version bump
merged to `main` reaches every annotator's laptop. Operators want
[`docs/SERVER-SETUP.md`](docs/SERVER-SETUP.md); annotators want
[`docs/SegQueue-Setup-Guide.pdf`](docs/SegQueue-Setup-Guide.pdf); the reasoning
behind the model lives in the Obsidian vault at [`vault/`](vault/README.md).

---

## The model

A four-class coronary segmentation model — **left main, LAD, LCx and RCA** — from
CCTA. The method was decided by a plan tournament: competing candidate plans,
backed by experiments on the real case data, ruled on by a judge. The plan in
force is [`vault/Plans/Master plan.md`](vault/Plans/Master%20plan.md); the
decisions the project lead made are in
[`vault/Plans/Human decisions.md`](vault/Plans/Human%20decisions.md).

In short:

- **One nnU-Net v2 ResEnc model**, trained directly on four classes at **0.5 mm
  isotropic** with a **256³ patch**, which holds the whole coronary tree in about
  98 % of cases. Fixed CT window; no mirroring, because it swaps left for right.
- **Labels:** the original ImageCAS lumen mask, split into four classes under the
  territory rule (ramus → LCx). Until the team's labels arrive, training uses proxy
  labels — ImageCAS-X's per-branch names projected onto that mask, checked by a
  rule-based namer. **Every case is labelled twice** by the team.
- **Deciding metric:** tree-F1 at 1.5 mm — centreline F1 that only credits vessel
  still connected to its ostium — gated on false-positive components. Dice is
  reported, not decisive, because it cannot see a cut tree.
- **Sealed test:** 80 ImageCAS-X test and 20 quality-0 cases, chosen by a fixed hash
  rule after excluding every case used in development
  ([`vault/Plans/Sealed test.md`](vault/Plans/Sealed%20test.md)).

The runbook is [`docs/TRAINING-R1.md`](docs/TRAINING-R1.md). The first GPU
experiments are in [`trillium/`](trillium/README.md), runnable with one command.

Training runs on [SciNet](https://www.scinet.utoronto.ca/)'s Trillium
supercomputer, one H100 80 GB per job.

## Acknowledgement and licence

Publications using this compute carry SciNet's
[requested acknowledgement](https://docs.scinet.utoronto.ca/index.php/Acknowledging_SciNet)
and cite Ponce et al. 2019 ([doi:10.1145/3332186.3332195](https://doi.org/10.1145/3332186.3332195))
and Loken et al. 2010 ([doi:10.1088/1742-6596/256/1/012026](https://doi.org/10.1088/1742-6596/256/1/012026)).

MIT for this pipeline; nnU-Net is Apache-2.0. Trained weights follow the
training data's terms, not this repo's.

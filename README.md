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

Multiclass coronary artery segmentation from CCTA. **nnU-Net v2, `3d_fullres`,
at native spacing, with no downsampling anywhere in the path** — no cascade, no
coarsened resampling, no heart crop. The full plan, with the reasoning and the
evidence, is [`vault/Training method/Training plan.md`](vault/Training%20method/Training%20plan.md) in the
repository's Obsidian vault; the retired previous plan is on the `plan-v1`
branch.

Training runs on [SciNet](https://www.scinet.utoronto.ca/)'s Trillium
supercomputer, one H100 80 GB per job.

## The method

A distal coronary branch is 1.5–2 mm across a few voxels at the ~0.35 mm the
scans are acquired at. Anything that downsamples destroys exactly the structures
being labelled, so the model reads the data at acquired resolution end to end:

- **`spacing: native`** — nnU-Net's median-spacing rule, on a near-isotropic
  cohort, keeps the acquired grid.
- **No `3d_cascade_fullres`.** Its low-resolution first stage resamples distal
  branches below their own diameter.
- **No heart crop.** The H100 sets the patch size, not the crop: the budget buys a
  ~256³ patch, ~23–31 % of a whole volume against the **25 %** threshold at which
  nnU-Net would plan a cascade, and large enough to hold the coronary tree with
  the aortic root and both ostia in one view. There is no cropper to silently
  clip a low-running RCA.

Sequence: a **binary lumen model first**, in two separate tasks, because proving
the chain and producing annotator seeds are not the same job —
`710_CoronaryLumen` on the original 1000 masks and ImageCAS's official split is
the chain test and the only place the published 82.96 % means anything;
`711_CoronaryLumenX` on the ImageCAS-X re-annotated lumen is the model we keep,
because its predictions become the seeds and the original masks disagree with
re-annotation at 41.8 % Dice. The **multiclass model** trains on the same
configuration. One paired **ResEnc** run afterwards decides the encoder.

Per-branch labels for 800 of the 1000 cases already exist, under CC BY 4.0, so
what the annotation programme is *for* is an open question — see
[the review summary](vault/Review/Review%20summary.md).

Ruled out, deliberately: tree/graph-structured models as the primary segmenter
(unrecoverable when the pre-segmentation misses a vessel), nnU-Net's
largest-component post-processing (the coronary tree is naturally several
disconnected components; the rule deletes real vessels), and mirroring
augmentation (it swaps the left coronary tree for the right).

## Acknowledgement and licence

Publications using this compute carry SciNet's
[requested acknowledgement](https://docs.scinet.utoronto.ca/index.php/Acknowledging_SciNet)
and cite Ponce et al. 2019 ([doi:10.1145/3332186.3332195](https://doi.org/10.1145/3332186.3332195))
and Loken et al. 2010 ([doi:10.1088/1742-6596/256/1/012026](https://doi.org/10.1088/1742-6596/256/1/012026)).

MIT for this pipeline; nnU-Net is Apache-2.0. Trained weights follow the
training data's terms, not this repo's.

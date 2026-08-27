# segmentator-train

Multiclass coronary artery segmentation from CCTA. **nnU-Net v2, `3d_fullres`,
at native spacing, with no downsampling anywhere in the path** — no cascade, no
coarsened resampling, no heart crop. The full plan, with the reasoning and the
evidence, is [`docs/TRAINING-PLAN.md`](docs/TRAINING-PLAN.md); the retired
previous plan is on the `plan-v1` branch.

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
- **No heart crop.** The H100 sets the patch size, not the crop: a ~70 GB
  budget buys a ~256³ patch, ~27–30 % of a whole volume above the 12.5 %
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



## Acknowledgement and licence

Publications using this compute carry SciNet's
[requested acknowledgement](https://docs.scinet.utoronto.ca/index.php/Acknowledging_SciNet)
and cite Ponce et al. 2019 ([doi:10.1145/3332186.3332195](https://doi.org/10.1145/3332186.3332195))
and Loken et al. 2010 ([doi:10.1088/1742-6596/256/1/012026](https://doi.org/10.1088/1742-6596/256/1/012026)).

MIT for this pipeline; nnU-Net is Apache-2.0. Trained weights follow the
training data's terms, not this repo's.

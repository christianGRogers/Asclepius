---
aliases: [Fold schemes and split ratios, Fold scheme, Data splits, FOLD-SCHEME]
tags: [research, coronary, splits, evaluation, benchmark, literature]
status: draft
updated: 2026-09-19
---

# Fold schemes and split ratios

Open item in [[Training plan]]: the fold scheme and split ratios, "including
whether to adopt the official ImageCAS 4-fold split for comparability".

This note supersedes the handover draft
`vault/Research/Class schema/Handover/Fold scheme and splits.md`, written before
topics were divided. Its argument survives; three of its "still unverified"
items are now verified, and one of its claims (that the official split file
needs an e-mail to the authors) is wrong — the file is in the public
repository and is decoded below.

**Short answer.** Two published splits of this same cohort exist and they are
incompatible. Use ImageCAS's official 4-fold split for the binary calibration
run, and ImageCAS-X's 560/80/160 split for everything multiclass; never score a
model on a test set that any of its ancestors trained on.

## The official ImageCAS split, decoded

`imageCAS_data_split.xlsx` is committed to
`github.com/XiaoweiXu/ImageCAS-A-Large-Scale-Dataset-and-Benchmark-for-Coronary-Artery-Segmentation-based-on-CT`
and downloads without credentials. I read it (1002 rows, 5 columns, one sheet
headed "4-fold cross validation"; a local copy of the decoded assignment is in
the scratch directory, not in the repo). What it contains:

- **1000 unique numeric case IDs** (range 10016975 … 12087501), one row each.
- Four columns `Split-1 … Split-4`, each with exactly **700 `Training`,
  50 `Val`, 250 `Testing`**. That matches the paper's "training set of 750 cases
  (50 cases are used for validation) and a test set of 250 cases".
- **Every case is `Testing` in exactly one of the four splits.** The four test
  sets are disjoint and cover the cohort — it is a genuine 4-fold partition,
  not four random draws. (The handover note listed this as unknown.)
- The validation sets are *not* independent draws: the 50 `Val` cases of splits
  2, 3 and 4 are all taken from split 1's test set, and split 1's 50 `Val` cases
  come from split 2's test set. Cross-split pooling of validation scores is
  therefore not clean.

Consequence for us: a single fold of this file is directly usable as an
nnU-Net `splits_final.json` entry (`train` = the 700, `val` = the 50), with the
250 `Testing` cases withheld from the dataset entirely. Zeng et al. report one
aggregate number rather than per-fold numbers, so 82.96 % is a 4-fold mean —
see [[State of the art on ImageCAS]].

Caveat: the repository README warns that some released folders ended in "(1)"
and were duplicates, since removed. If our Girder copy predates that fix, the ID
list in the spreadsheet is the authority; reconcile before building splits.

## The ImageCAS-X split

Bransby et al. (arXiv:2608.30404v1, preprint, read in full) re-annotated 800 of
the 1000 ImageCAS scans and state: "A total of 800 annotated cases were randomly
split into training (70%, 560 cases), validation (10%, 80 cases), and test (20%,
160 cases) sets." Verbatim, verified in the preprint. Further verified facts:

- **Patient IDs are the original ImageCAS IDs**: "Each patient is assigned a
  unique ID, identical to the original ImageCAS 2023 dataset". (The handover
  note listed this as unverified.) So the two splits *can* be intersected
  exactly, once the Zenodo archive is downloaded.
- Subset membership ships as four text files — train, validation, test,
  exclude — inside the Zenodo record (10.5281/zenodo.21887809 landing page
  `zenodo.org/records/21887809`, `ImageCAS-X_dataset.zip`, 1.44 GB, CC BY 4.0).
- **200 scans were excluded** as non-diagnostic: motion artefacts (n = 114),
  step artefacts (n = 76), poor contrast mixing (n = 7), static noise (n = 1),
  incorrect field of view (n = 1), file corruption (n = 1).
- No cross-validation: one split, one training run per method, checkpoint
  selected on the 80-case validation set.
- Their 160-case test set is small in the rare classes: L-PDA present in 8
  scans and L-PLA in 9 (their Table 1). Anything reported per class for those
  two is underpowered.
- Each test case was **re-annotated by a second analyst**, which is what makes
  the 160 the natural multiclass test set: it is the only part of the cohort
  with a measured human ceiling.

I could not verify the ID lists themselves — the Zenodo archive is 1.44 GB and
was not downloaded in this session. Everything above is from the preprint and
the Zenodo metadata record.

## The leakage trap (unchanged from the handover, and now sharper)

Both test sets are random draws from the same 1000 scans, and the IDs are known
to be the same ID space. Therefore:

- The official split's 700-case training set covers 70 % of the cohort, so it
  contains roughly 112 of ImageCAS-X's 160 test cases in expectation.
- If the binary model trained on that fold is then used to initialise the
  multiclass model, and the multiclass model is scored on the ImageCAS-X test
  set, **the multiclass test set has leaked through the initialisation**, and
  the "binary-init vs from-scratch" comparison in [[Training plan]] §5 is
  biased towards fine-tuning.
- Using binary predictions as annotator *seeds* is unaffected — nothing is
  scored. Using them as *input channels* to a scored model is not.

This is reasoning from the two protocols, not a published finding; it needs
only that both splits are random over one cohort. Confirm by intersecting the ID
lists once the Zenodo file is local — that intersection is a five-minute check
and should be run before any multiclass training.

## Why five folds rather than copying ImageCAS-X's single split

- ImageCAS-X trains each method once. With 160 test cases and differences of
  1–2 Dice points between the top methods (CAS-Net 91.2 vs nnU-Net 89.8, their
  Table 2), a single split gives no variance estimate across training runs.
- nnU-Net's own protocol is 5-fold cross-validation over the training data, and
  its configuration selection and post-processing decisions are made *from*
  those folds (see [[Research context]]). Supplying one fold disables part of
  the method's own machinery.
- Cost is the constraint: at ~250 k iterations per fold, five folds per
  ablation does not fit a 24-hour-per-job chain with several standing
  experiments. Hence: ablations on fold 0, all five folds for the final
  configuration only.

## Recommendation

1. **Binary calibration run** — train on ImageCAS official `Split-1`
   (700 train + 50 val), evaluate on its 250 `Testing` cases against the
   original merged binary masks. Supply it as a one-entry `splits_final.json`.
   That is the only configuration in which "beat 82.96 %" is meaningful, and
   even then only loosely: see [[State of the art on ImageCAS]].
2. **Multiclass runs** — seal the ImageCAS-X 160-case test set. Build a
   `splits_final.json` with 5 folds over the 640 train+val cases. Ablations on
   fold 0; all five folds only for the final configuration.
3. **Binary-init fine-tuning** — permitted only if the binary model's training
   set excludes all 160 ImageCAS-X test IDs. Retrain the binary model on the
   ImageCAS-X 640 with the original ImageCAS masks, or drop the experiment.
4. **Report the intersection check** — the count of official-split training IDs
   appearing in the ImageCAS-X test set, computed once and recorded, so nobody
   has to rediscover the trap.
5. **The 200 excluded scans** stay out of every split. If our annotators label
   any of them, they are a separate "non-diagnostic quality" set, reported
   separately — folding them into training silently breaks comparability with
   every ImageCAS-X number.
6. **Stratify our own fold construction** on coronary dominance and disease,
   which ImageCAS-X ships per scan in `Descriptors.xlsx` (729 right-dominant,
   41 left-dominant, 30 co-dominant; 388 diseased, 412 not). Random 5-fold over
   640 cases puts ~8 left-dominant cases in a fold; unstratified, a fold can
   easily get half that, and the L-PDA/L-PLA classes exist only in those cases.
   This costs nothing and is not in either paper's protocol.

## What this implies for [[Training plan]]

- Close the "fold scheme and split ratios" item with the six rules above.
- Record in §3 that the binary run is scored on ImageCAS official `Split-1`
  test cases with the original masks, and that this number is not comparable
  with any ImageCAS-X number (different labels *and* a different test set).
- Add to §5 that binary-init fine-tuning requires a leak-free binary model.
- Add the dominance/disease stratification rule when folds are built.

See [[Proposed changes]], [[Public coronary CCTA datasets]] and
[[State of the art on ImageCAS]].

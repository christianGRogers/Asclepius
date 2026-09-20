---
aliases: [FOLD-SCHEME, Fold scheme, Data splits]
tags: [research, coronary, evaluation, splits, literature]
status: handover
updated: 2026-09-19
---

# Fold scheme and splits

> **Handover draft.** Written before the research was split between agents; this topic now belongs to another agent. Sources were opened and numbers checked as stated below, but the note has not been reviewed by the owner. Take, merge or discard it.

Open item in [[Training plan]]: the fold scheme and split ratios, including
whether to adopt the official ImageCAS 4-fold split for comparability.

**Short answer.** There are now *two* published splits of this cohort and they
are incompatible: ImageCAS's own 4-fold split (750 train / 250 test) and
ImageCAS-X's single random split of 800 cases (560 / 80 / 160). Use each for
the result it makes comparable, and never let a model that has seen one split's
test cases be scored on it. The concrete trap is binary-init fine-tuning (see
"Leakage" below).

## Sources actually read

- **ImageCAS** — Zeng A, Wu C, Xie W, Hong J, Huang M, Zhuang J, Bi S, Pan D,
  Ullah N, Khan KN, Wang T, Shi Y, Li X, Lin G, Xu X. *ImageCAS: A large-scale
  dataset and benchmark for coronary artery segmentation based on computed
  tomography angiography images.* Comput Med Imaging Graph 2023;109:102287.
  doi:10.1016/j.compmedimag.2023.102287. Read in full from arXiv:2211.01607v2.
  Also the project README on GitHub (XiaoweiXu/ImageCAS-A-Large-Scale-Dataset-…).
- **ImageCAS-X** — Bransby KM et al., arXiv:2608.30404 (2026, preprint). See
  [[Class schema options]] for the full citation. Read via arXiv HTML; repo
  README at github.com/MathildeBS1/ImageCAS-X.
- **nnU-Net documentation** — `documentation/manual_data_splits.md` in
  MIC-DKFZ/nnUNet (master).

## What each source does

### ImageCAS (the binary benchmark, 82.96 %)

Verbatim (§5.1): "Experiments were evaluated using a 4-fold cross-validation
approach, with a training set of 750 cases (50 cases are used for validation)
and a test set of 250 cases."

- The paper says "An official data split of the dataset is also provided."
  The repository ships it as `imageCAS_data_split.xlsx`. I did not open the
  spreadsheet (download requires contacting the authors / Kaggle), so the
  per-fold case IDs are unverified here.
- The repository README notes that folders ending in "(1)" were duplicate cases
  and "We have updated the dataset to discard these duplicate cases." Check our
  Girder copy for any `(1)` folders before building a split.
- Training budget behind the headline number: "30 epochs (about 21,000
  iterations)", Adam, lr 0.002, one RTX 3090 (24 GB). The 82.96 % Dice is the
  coarse+patch ensemble with dilation (their Table 3/4; HD 27.22 mm,
  AHD 0.818 mm). Measured on ImageCAS's original merged binary masks.
- Annotation (§3): left and right coronaries "independently labeled by two
  radiologists … cross-validated. In case of discrepancy, a third radiologist
  will perform the annotation and the final result is determined by consensus."

### ImageCAS-X (the multiclass labels)

Verbatim: "A total of 800 annotated cases were randomly split into training
(70%, 560 cases), validation (10%, 80 cases), and test (20%, 160 cases) sets."

- No cross-validation, no stratification mentioned, and **no statement relating
  this split to the ImageCAS official split.** Treat them as independent.
- 200 of the 1000 scans were excluded for image quality: "motion artefacts
  (n = 114), step artefacts (n = 76), poor contrast mixing (n = 7), static noise
  (n = 1), incorrect field of view (n = 1), and file corruption (n = 1)." The
  repo ships `filelist/{train,val,test,exclude}.txt`.
- Their 160-case test set contains only 8 L-PDA and 9 L-PLA cases (their
  Table 1). Per-class metrics for those two classes will have very wide
  confidence intervals whatever we do.
- Their benchmark trains every method once on one split (1000 epochs × 250
  iterations for nnU-Net, SGD). No fold ensemble.
- Their labels are a re-annotation. The same ImageCAS method scores 87.9 % DSC
  on the ImageCAS-X test set against the 82.96 % it reported on its own labels
  and split. **Numbers on the two label sets are not comparable**, even for
  binary lumen.

### nnU-Net

Defaults to a 5-fold cross-validation over whatever it is given as training
data, stored in `nnUNet_preprocessed/DatasetXXX/splits_final.json`. A custom
`splits_final.json` (a list of `{"train": [...], "val": [...]}`) replaces the
default and may contain any number of folds. There is no held-out test set in
nnU-Net's own scheme; the test set must be withheld *before* the dataset is
converted.

## The leakage trap

The two test sets are drawn independently from the same 1000 scans. So:

- A binary model trained on the ImageCAS official 750-case training set will,
  with high probability, have trained on a large share of the 160 ImageCAS-X
  test cases (the 750 cover 75 % of the cohort).
- If that binary model is then used as initialisation for the multiclass model
  ("binary-init fine-tuning", [[Training plan]] §5), and the multiclass model is
  scored on the ImageCAS-X test set, **the test set has leaked into the
  initialisation**. The paired comparison against from-scratch would be biased
  towards fine-tuning.
- The same holds in reverse: a multiclass model trained on ImageCAS-X's 560
  cannot be scored on the ImageCAS official test set.
- Presegmentation seeds for annotators are unaffected (no evaluation).

This is my reasoning from the two published protocols, not a published finding;
it depends only on the fact that both splits are random over the same cohort.
Verify by intersecting the ID lists once both files are local.

## Options

| | Binary calibration run | Multiclass runs |
|---|---|---|
| **A. Two splits, each for its own purpose** (recommended) | ImageCAS official fold, original masks, 750/250 | ImageCAS-X split, ImageCAS-X labels, 640 train+val / 160 test |
| B. One split for everything (ImageCAS-X) | Loses the 82.96 % comparison, which was the point of the binary run | Clean |
| C. One split for everything (ImageCAS official) | Clean | Loses comparability with ImageCAS-X and forces relabelling the 250 test cases ourselves |

## Recommendation

**Option A**, with these rules:

1. **Binary calibration**: train on the ImageCAS official fold 1 (700 train +
   50 validation as given in the spreadsheet), score on its 250 test cases with
   the original masks. Supply this as a one-fold `splits_final.json`. That is the
   only configuration in which "beat 82.96 %" means anything.
2. **Multiclass**: the 160 ImageCAS-X test cases are sealed. Run nnU-Net's
   5-fold CV over the 640 train+val cases (by supplying a `splits_final.json`
   built from `train.txt` + `val.txt`), use **fold 0 only** for ablations
   (loss, sampling, rotation, ResEnc), and train all five folds only for the
   final configuration. Why five and not their single split: five folds give a
   variance estimate for ablations with effect sizes of a Dice point or two, and
   an ensemble for the final model; why fold 0 only for ablations: at
   ~250 k iterations per fold on one H100, five folds per ablation does not fit
   the walltime budget.
3. **Binary-init fine-tuning experiment**: the binary model used as
   initialisation must be trained on a split that **excludes all 160 ImageCAS-X
   test IDs**. Either retrain the binary model on ImageCAS-X train+val with the
   original ImageCAS masks, or drop the experiment.
4. **Report per-class results on the 160-case test set with bootstrap
   confidence intervals**, and flag L-PDA/L-PLA (n = 8, 9) as underpowered
   rather than tuning anything on them.
5. **The 200 excluded scans** are not part of any ImageCAS-X split. If the
   annotation team labels any of them, they form a separate "hard image quality"
   test set, reported on its own. They must not be folded into the training set
   silently, or the comparison with ImageCAS-X numbers breaks.

## Still unverified

- The contents of `imageCAS_data_split.xlsx` (fold IDs; whether it is one test
  set rotated across four folds or four disjoint test sets of 250).
- The actual overlap between the ImageCAS official test fold and the
  ImageCAS-X splits.
- Whether ImageCAS-X scan IDs are the original ImageCAS IDs.

## What this implies for [[Training plan]]

- Close "Fold scheme and split ratios" with option A above.
- Add a rule to §5: binary-init fine-tuning uses a binary model that never saw
  the multiclass test set.
- Add to §3: the binary run's evaluation is on the ImageCAS official test fold
  with the original masks. It is not comparable with any ImageCAS-X number.

These proposals are not in [[Proposed changes]] (class schema only); they are for this topic's owning agent. See also [[Class schema options]].

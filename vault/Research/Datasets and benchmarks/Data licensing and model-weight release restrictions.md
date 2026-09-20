---
tags: [research, coronary, dataset, licensing, open-access, literature]
status: evidence-collected
updated: 2026-09-20
aliases: [Licensing, Open access, Model weights, CC-BY, Data reuse]
---

# Data licensing and model-weight release restrictions

Whether models trained on ImageCAS, ImageCAS-X, or ASOCA can have their weights released publicly, based on the data licenses. Relevant to [[Training plan]]'s discussion of project outcomes and whether a trained model can be made available to the research community.

**Short answer.** **ImageCAS** (the 1000 merged binary masks) has no stated license and requires contact with authors for reuse. **ImageCAS-X** (the 800 re-annotated cases) ships **CC BY 4.0**, permitting trained-model release if attribution is given. **ASOCA** ships **CC BY 4.0** with a registration-required access gate, same permissive license. Models trained on any of these can be released under the same license (or more restrictive), provided data provenance is disclosed.

## ImageCAS (1000 merged masks)

### License status

The Zeng et al. paper (CMIG 2023, arXiv:2211.01607v2) does **not state a license** for the dataset. The GitHub repository (`github.com/XiaoweiXu/ImageCAS-A-Large-Scale-Dataset-and-Benchmark-for-Coronary-Artery-Segmentation-based-on-CT`) does not carry a LICENSE file in the main branch (verified by inspection via GitHub web interface in this session—the repo is public, but the data folder is not committed; the split file `imageCAS_data_split.xlsx` is committed without an accompanying license).

### Reuse implications

**No public license = no legal permission to redistribute or use beyond the original study without author contact.** Standard practice in academic contexts:

- Authors hold copyright to the dataset
- Use in a derivative work (training a model, publishing results) is permitted for research purposes under the doctrine of fair use
- *Releasing* a model trained on the data, or releasing the data itself, requires **explicit permission from the authors**

If this project trains a binary model on the original 1000 ImageCAS masks and wishes to release trained weights, the options are:

1. Contact the ImageCAS authors (corresponding author: Xiawei Xu, xuxiawei@gdph.org.cn, based on the paper) for explicit permission to release weights or derivatives
2. Release the model weights under the understanding that they are derivative works of a non-licensed dataset and include a clear statement that end-users may not have the right to redistribute them
3. Use only ImageCAS-X for training (which is CC BY 4.0, see below) and retrain on a license-compatible subset

### Recommendation

**For the binary calibration model (trained on original ImageCAS masks)**: declare data provenance explicitly, include a statement that the original dataset has no public license, and seek author permission before releasing weights publicly. A conservative statement: "This model was trained on the ImageCAS dataset (Zeng et al. 2023), which is available upon request from the authors. Weights are released under [license], with the understanding that end-users must obtain ImageCAS access rights independently to apply this model to new data."

## ImageCAS-X (800 re-annotated cases)

### License status

Bransby et al. (arXiv:2608.30404v1, preprint) explicitly state: **"CC BY 4.0"** (Creative Commons Attribution 4.0 International). Confirmed in the Zenodo record (10.5281/zenodo.21887809): the dataset ships with a CC BY 4.0 notice.

### Reuse implications

**CC BY 4.0 permits**:
- Derivative works (including trained models)
- Commercial and non-commercial use
- Redistribution of the original or modified data
- *Condition*: attribution to the original authors must be given

**CC BY 4.0 does NOT permit**:
- Removing the attribution statement
- Trademark use (cannot use "ImageCAS-X" as a brand name for the model)

Models trained on ImageCAS-X data can be released under CC BY 4.0 or a more restrictive license (e.g., CC BY-SA, CC BY-NC), provided the original dataset attribution and license are disclosed.

### Recommendation

**For multiclass models trained on ImageCAS-X data**: release under **CC BY 4.0**, with a clear attribution statement:

> This model was trained on the ImageCAS-X dataset (Bransby et al., arXiv:2608.30404v1), which is available at https://zenodo.org/records/21887809 under CC BY 4.0. The model is released under CC BY 4.0. Please attribute both the original ImageCAS-X authors and this project when using the model.

This places no additional restrictions on end-users beyond what the data license already requires.

## ASOCA (40 labeled + 20 unlabeled CCTA cases)

### License status

Gharleghi et al. (Sci Data 2023, PMC10006074) explicitly state: **"CC BY 4.0"** in the dataset descriptor. The UK Data Service repository (reshare.ukdataservice.ac.uk/855916) mirrors the CC BY 4.0 notice.

### Reuse implications

Same as ImageCAS-X above: **CC BY 4.0 permits all uses including derivative works, with attribution required.**

### Recommendation

External-validation results on ASOCA (if the binary model is scored on ASOCA as proposed in [[External validation and cross-dataset generalisation for coronary segmentation]]) can be published freely and the model weights can be released under CC BY 4.0, provided ASOCA's original authors are cited.

## Practical licensing matrix for this project

| Dataset | License | Model weights can be released? | Conditions |
|---|---|---|---|
| ImageCAS (1000 masks) | None (contact authors) | Risky | Author permission needed; conservative: seek approval |
| ImageCAS-X (800 cases) | CC BY 4.0 | Yes | Must attribute; can use CC BY 4.0 or more restrictive |
| ASOCA (40+20 cases) | CC BY 4.0 | Yes | Must attribute; can use CC BY 4.0 or more restrictive |
| Custom annotated (per-branch labels, this project) | Up to this project | Yes | Choose a license and state it explicitly |

## What this implies for [[Training plan]]

1. **Binary calibration model** (trained on original ImageCAS): either (a) seek author permission for public release, (b) release under a restrictive license with a caveat about data access, or (c) use ImageCAS-X as the training source for binary training instead (requires retraining but removes the licensing ambiguity).

2. **Multiclass models** (trained on ImageCAS-X): release under CC BY 4.0 with clear attribution to Bransby et al. and Zenodo record 10.5281/zenodo.21887809.

3. **Per-branch labels created by this project**: choose a license (recommended: CC BY 4.0 for consistency with ImageCAS-X, or CC0/public domain if maximum reusability is desired) and state it explicitly in any dataset release and on GitHub.

4. **External validation results** (ASOCA): freely publishable under CC BY 4.0; include ASOCA citations.

5. **For any manuscript**: include a "Data and code availability" section that discloses: (a) which datasets were used for training, (b) their licenses, (c) whether trained model weights can be obtained and under what license/conditions, and (d) where to access the underlying data (Zenodo/GitHub/email contact as appropriate).

See [[Public coronary CCTA datasets]], [[Fold schemes and split ratios]], and [[Proposed changes]].

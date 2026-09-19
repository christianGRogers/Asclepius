---
aliases: [State of the art on ImageCAS, SOTA, Benchmark numbers]
tags: [research, coronary, benchmark, sota, evaluation, literature]
status: draft
updated: 2026-09-19
---

# State of the art on ImageCAS

What has superseded ImageCAS's **82.96 % Dice**, and what the honest target is
for [[Training plan]]'s binary calibration run.

**Short answer.** The 82.96 % number has been superseded twice over, and in a
way that makes it close to useless as a target: on *ImageCAS's own labels* it
was already a weak baseline (21 k iterations on a 24 GB card), and on
*re-annotated labels* of the same scans the original ImageCAS labels themselves
score **41.8 % DSC** against expert re-annotation. The current defensible
benchmark on this cohort is **CAS-Net at 91.2 ± 2.8 % DSC on the ImageCAS-X
test set**, with an inter-observer ceiling of **92.8 ± 3.1 %** — and all of it
is binary lumen. **No published per-branch segmentation numbers exist on this
cohort.** That is the gap this project sits in.

## Sources actually read

- **ImageCAS** — Zeng A, Wu C, Lin G, Xie W, Hong J, Huang M, Zhuang J, Bi S,
  Pan D, Ullah N, Khan KN, Wang T, Shi Y, Li X, Xu X. Comput Med Imaging Graph
  2023;109:102287. doi:10.1016/j.compmedimag.2023.102287. Full text read from
  arXiv:2211.01607v2; citation verified via Crossref. Condensed in
  [[Research context]].
- **ImageCAS-X** — Bransby KM, Øksnebjerg E, Kjær K, Kirkeby J, El Youssef Y,
  Jiménez A, Pedersson PR, de Knegt MC, Kofoed KF, Paulsen RR. *ImageCAS-X: a
  dataset and benchmark for coronary artery segmentation and centerline
  extraction in coronary CT angiography.* **arXiv:2608.30404v1, 31 Aug 2026 —
  preprint, marked "under review"; not peer reviewed.** Read in full, including
  supplementary material. Dataset: Zenodo record 21887809, CC BY 4.0. Code:
  `github.com/kitbransby/ImageCAS-X` (MIT).
- Method papers are cited below as ImageCAS-X reports them; I opened the
  ImageCAS-X reimplementations and results, **not** each original method paper.
  Where a number is attributed to a method, it is ImageCAS-X's measurement of
  their reimplementation, not the original authors' claim.

## 1. What 82.96 % actually was

From the ImageCAS paper (Table 4): the proposed baseline — a coarse
segmentation ensembled with multi-scale patch segmentation (16³/32³/64³) and
vessel dilation — scored **82.96 % Dice, HD 27.2169 mm, AHD 0.8180 mm**,
4-fold cross-validated on 1000 cases with their own merged binary masks.
Runners-up in that table: direct segmentation (3D FCN at 512×512×256 input)
80.58 %, patch segmentation 72.01 %, graph-based 70.61 %, tree-based 68.78 %.

Training budget: **30 epochs ≈ 21,000 iterations**, Adam, lr 0.002, one RTX 3090.
nnU-Net's default schedule is 250 k iterations (1000 epochs × 250 minibatches).
The benchmark is therefore an under-trained baseline, which is exactly how
[[Training plan]] §3 already describes it.

## 2. What superseded it on the same labels

I did not find a peer-reviewed paper that both (a) trains on the *original*
ImageCAS labels and official split and (b) reports a Dice clearly above 82.96 %
that I was able to open and verify in this session. The literature moved
instead to **new labels for the same scans**, which is a stronger form of
supersession: it retires the benchmark rather than beating it.

Marked as **open**: a systematic sweep of 2024–2026 papers reporting on the
ImageCAS official split (many exist in the MICCAI/arXiv literature) was not
completed. Any such number must be checked for three things before it is
comparable: same labels, same 4-fold split, and whether the aorta/ostium was
included in the mask — Zeng et al. explicitly flag that including the initial
aorta inflates Dice.

## 3. What superseded it as *the* benchmark: ImageCAS-X

ImageCAS-X re-annotated 800 of the 1000 scans with a semi-automatic Slicer tool,
then benchmarked eight methods under one fixed training framework (0.5 mm
isotropic resampling, shared augmentation, 1000 epochs × 250 minibatches,
Adam except nnU-Net which used SGD, lr tuned over {0.01, 0.001, 0.0001},
RTX 5090 32 GB). All numbers below are **binary lumen** on their 160-case test
set, mean ± s.d.:

| Method (as reimplemented by ImageCAS-X) | DSC % ↑ | HD95 mm ↓ | β err ↓ | clDice % ↑ | ASSD mm ↓ |
|---|---|---|---|---|---|
| TotalSegmentator (zero-shot) | 70.5 ± 6.2 | 19.59 ± 6.45 | 4.6 ± 2.9 | 76.0 ± 5.3 | 2.73 ± 0.90 |
| 3D-FFR-UNet | 84.9 ± 5.5 | 15.93 ± 20.42 | 4.8 ± 3.5 | 89.8 ± 5.0 | 1.71 ± 1.56 |
| ADE-HTL | 87.7 ± 2.8 | 2.97 ± 3.74 | 1.5 ± 1.5 | 93.2 ± 3.2 | 0.74 ± 0.39 |
| Swin-UNETR | 87.9 ± 2.7 | 3.18 ± 3.68 | 3.8 ± 2.3 | 92.5 ± 3.0 | 0.78 ± 0.36 |
| ImageCAS baseline method | 87.9 ± 2.9 | 4.45 ± 4.90 | 4.7 ± 3.1 | 91.7 ± 3.5 | 0.90 ± 0.46 |
| **nnU-Net** | **89.8 ± 3.2** | 7.08 ± 12.65 | 5.6 ± 3.5 | 92.3 ± 3.6 | 1.02 ± 0.75 |
| nnU-Net + clDice | 90.0 ± 3.5 | 9.70 ± 15.36 | 8.0 ± 4.4 | 91.7 ± 3.9 | 1.20 ± 0.99 |
| **CAS-Net** (best) | **91.2 ± 2.8** | 2.99 ± 3.47 | 1.9 ± 1.5 | 93.3 ± 3.2 | 0.73 ± 0.36 |
| *Inter-observer (human ceiling)* | *92.8 ± 3.1* | *2.46 ± 3.62* | *0.4 ± 0.4* | *95.4 ± 3.6* | *0.53 ± 0.33* |
| *Original ImageCAS labels, scored against ImageCAS-X labels* | *41.8 ± 6.7* | *16.15 ± 8.25* | *7.0 ± 6.7* | *78.2 ± 6.9* | *2.23 ± 0.94* |

Readings that matter for us:

- **The same ImageCAS method scores 87.9 % here and 82.96 % on its own labels.**
  Dice on this cohort is a property of the label set as much as of the model.
  Cross-label comparisons are meaningless.
- **41.8 % DSC for the original ImageCAS labels against the re-annotation.**
  Their supplementary Fig. 7 attributes it to inclusion of atherosclerotic
  plaque (i.e. outer wall rather than lumen), false-positive pulmonary vessels
  and false-positive coronary veins. They state flatly that ImageCAS "lacks
  sufficient segmentation accuracy for reliable benchmarking". This is a
  *preprint* claim, but the failure modes are visually documented and the
  direction is consistent with ImageCAS's own admission of no sub-class labels
  and a single-centre protocol. Treat it as the strongest available evidence
  that the 1000 merged masks are training data of limited quality, not a gold
  standard.
- **CAS-Net beats nnU-Net by 1.4 DSC points** (p < 0.001 vs the next best,
  ADE-HTL) with 6.8 M parameters against nnU-Net's 153.9 M summed over a 5-model
  ensemble, and much better topology (β err 1.9 vs 5.6). So a plain nnU-Net is
  a strong but not winning baseline on this data.
- **clDice loss helped Dice slightly (+0.2) and hurt topology badly**
  (β err 5.6 → 8.0, HD95 7.08 → 9.70). That contradicts the usual motivation for
  the loss. Flagged to the loss/topology agent in `Handoffs.md`; not my call.
- **Every method still breaks vessels**: "topological errors such as vessel
  breaks are present in all model predictions despite high DSC and clDice".
- The gap to human agreement is statistically significant for CAS-Net on every
  metric (DSC p < 0.001, HD95 p = 0.04, β err p < 0.001), so nothing on this
  cohort is yet at human level.
- Minor internal inconsistency to be aware of: the inter-observer β err is
  given as 0.2 in the running text and 0.4 in Table 2. Use 0.4 ± 0.4 (the
  table) and note the discrepancy.

## 4. Per-branch state of the art: there isn't one

This is the finding that matters most for [[Training plan]]. ImageCAS-X ships
14 per-segment classes, but **its benchmark evaluates binary lumen only**. The
per-segment table in that paper (their Table 1) is *inter-observer agreement*,
not model performance — analyst-vs-analyst DSC on the 160 test scans, computed
over the scans where both analysts annotated the segment:

| Segment | n scans | Presence agreement % | Analyst-vs-analyst DSC % |
|---|---|---|---|
| LM | 155 | 96.9 | 91.9 ± 13.7 |
| LAD | 160 | 100.0 | 92.3 ± 6.7 |
| LCx | 159 | 99.4 | 84.8 ± 19.8 |
| D1 | 155 | 96.9 | 79.9 ± 28.7 |
| D2 | 91 | 89.4 | 82.9 ± 24.3 |
| OM1 | 132 | 94.4 | 74.1 ± 32.3 |
| OM2 | 46 | 87.5 | 77.7 ± 29.1 |
| IM | 43 | 89.4 | 80.6 ± 24.5 |
| RCA | 160 | 100.0 | 95.3 ± 5.0 |
| R-PDA | 150 | 98.8 | 82.6 ± 21.9 |
| R-PLA | 147 | 96.2 | 83.6 ± 18.6 |
| L-PDA | 8 | 100.0 | 75.1 ± 29.0 |
| L-PLA | 9 | 96.9 | 70.9 ± 27.2 |
| Other | 14 | 88.8 | 81.3 ± 17.0 |
| **All segments** | **160** | **95.3** | **92.8 ± 3.1** |

(Row-to-segment alignment was reconstructed from the PDF's two-column table and
then **checked against the paper's own prose**, which states that the main
branches LM/LAD/LCx/RCA span DSC 84.8–95.3 and the side branches 70.9–83.6 —
both ranges reproduce exactly under the alignment above, so it is sound. One
inconsistency remains: the text says presence agreement for the PDA and PLA
segments is "96.9–100.0 %", while the table under this alignment gives R-PLA
96.2 %. Minor, and flagged rather than resolved.)

What this gives us:

- A **per-class ceiling** for the multiclass model, measured on exactly the
  cohort we will use: main branches 84.8–95.3, side branches 70.9–83.6.
- A **presence-agreement** figure — 95.3 % overall, i.e. experts disagree about
  whether a segment exists at all in ~5 % of segment-scan pairs. That is the
  right way to think about the plan's "branch detection rate" metric.
- A warning that per-class variance is enormous (s.d. up to 32 points), so
  per-class Dice on 160 cases needs confidence intervals, and L-PDA/L-PLA
  (n = 8, 9) cannot support a claim either way.

Anything we publish as per-branch Dice on this cohort would, as far as this
session's search found, be the first such number. Open item: a search for
per-branch coronary *segmentation* (not centreline labelling) numbers on other
cohorts was not completed; centreline-labelling accuracy papers exist and belong
to the class-schema agent's territory.

## 5. What to calibrate against

| Run | Labels | Test set | Number to compare with |
|---|---|---|---|
| Binary calibration | original ImageCAS merged masks | official `Split-1` 250 | 82.96 % (4-fold mean, under-trained baseline) |
| Binary on good labels | ImageCAS-X lumen | ImageCAS-X 160 | nnU-Net 89.8, CAS-Net 91.2, ceiling 92.8 |
| Multiclass | our per-branch labels | our sealed test set | no published comparator; ImageCAS-X per-class inter-observer is the ceiling |

The plan's line "published binary lumen Dice is 0.82–0.85 and inter-observer
agreement ≈ 0.856 — the ceiling" needs replacing: on the good label set the
published range is 0.705–0.912 and the measured human ceiling is 0.928. I found
no source for 0.856 in either founding paper; ImageCAS reports no inter-observer
figure at all.

## What this implies for [[Training plan]]

1. **Demote 82.96 % explicitly.** Keep it as a pipeline sanity check on the
   original labels, and state in §3 that it is not the state of the art:
   ImageCAS's own method scores 87.9 % on better labels of the same scans, and
   CAS-Net reaches 91.2 %.
2. **Replace the calibration numbers** in the Evaluation section with the
   ImageCAS-X table: nnU-Net 89.8 ± 3.2, best method 91.2 ± 2.8, inter-observer
   92.8 ± 3.1, all binary lumen on their 160-case test set. Drop the 0.856
   figure unless someone can source it.
3. **Treat the 1000 merged ImageCAS masks as weak labels.** 41.8 % DSC against
   expert re-annotation, with plaque, pulmonary vessels and coronary veins
   included. Implications: the binary model trained on them will inherit those
   errors, so presegmentation seeds handed to annotators will contain
   non-coronary structures — the annotation UI must make deletion as cheap as
   drawing. Consider seeding instead from ImageCAS-X's CC BY 4.0 lumen labels
   where they exist (800 of 1000 scans).
4. **Add nnU-Net + clDice's result to §5's loss experiment**: on this cohort it
   bought +0.2 DSC and cost 2.4 Betti points. Schedule it as an ablation with a
   topology metric attached, not as an assumed improvement.
5. **Per-branch targets** come from ImageCAS-X Table 1, not from a model paper.
   State the per-class ceiling and that no model comparator exists.
6. **Benchmarking the right thing**: since every method breaks vessels at
   ~90 % DSC, the plan's decision to report β/component counts and branch
   detection is well supported by this benchmark's own conclusions.

See [[Proposed changes]], [[Public coronary CCTA datasets]],
[[Fold schemes and split ratios]] and [[Research context]].

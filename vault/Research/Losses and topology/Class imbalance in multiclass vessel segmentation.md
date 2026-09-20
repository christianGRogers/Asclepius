---
aliases: [Class imbalance, Focal loss, Tversky loss, Class weighting, Rare branch classes]
tags: [research, loss, class-imbalance, coronary, multiclass, evidence]
status: solid
updated: 2026-09-19
---

# Class imbalance in multiclass vessel segmentation

Referenced from [[Topology-aware losses on thin tubular structures]] as a companion
question: independent of topology, the multiclass coronary task stacks **two**
imbalances on top of each other — foreground-vs-background (the coronary tree is a
tiny fraction of the volume) and, once multiclass, **foreground-vs-foreground**
(a proximal RCA trunk voxel and a distal septal-branch voxel score identically under
plain Dice+CE, but the septal branch has orders of magnitude fewer voxels and may be
absent in many patients). This note asks what evidence exists for focal loss,
Tversky loss, and class weighting as fixes for the second imbalance specifically.

## How severe the imbalance is on this anatomy, measured

- **Foreground-vs-background, our exact modality.** Pan, Li, Su, Tay, Tran, Chan,
  *Coronary artery segmentation under class imbalance using a U-Net based
  architecture on computed tomography angiography images*, Scientific Reports
  11:14493, 2021, DOI
  [10.1038/s41598-021-93889-z](https://doi.org/10.1038/s41598-021-93889-z). 474 CCTA
  scans, Wanfang Hospital (432 train / 42 test), 0.32 × 0.32 × 0.7 mm voxels — close
  to but coarser than our ~0.35 mm target. States plainly: **"the ratio between the
  area of the coronary artery and the area of the background is up to 1:400."**
  Their fix is plain per-voxel **focal loss** (α = 0.6, γ = 2) inside a 3D
  Dense-U-Net, reported at **DSC 0.9691** against a basic 3D U-Net's 0.9603 — a
  binary lumen task, and the 0.97 figure is markedly higher than the 0.83–0.90 DSC
  range other ImageCAS-scale coronary papers report (see [[Training plan]]'s
  calibration figures), so treat the absolute number with caution — the paper does
  not state whether DSC is averaged per-volume or computed pooled over all test
  voxels, and pooled DSC on a single large cohort with a permissive test split can
  read much higher than per-case averages. What is trustworthy is the *direction*
  and the qualitative per-branch claim: their Figure 6 radiologist ratings across 13
  named branches show the focal-loss model doing better specifically on **smaller
  branches**, which is the effect this project needs, even though the absolute
  numbers should not be imported.
- **Foreground-vs-foreground, the closest multiclass vascular analogue.** Already the
  central table of [[Topology-aware losses on thin tubular structures]]: on TopCoW
  2023 (90 MRA cases, nnU-Net v2), plain CE+Dice scored **84.03 Dice on large
  non-communicating arteries and exactly 0 on small communicating arteries** — the
  clearest documented case of foreground-vs-foreground collapse on vascular anatomy.
  Any focal/Tversky/class-weighting fix has to be judged against this baseline, not
  against the foreground-vs-background number above, because it is a different
  failure mode: the network was not failing to find vessels in background, it was
  failing to represent the *minority vessel class* at all once a majority vessel
  class competed for the same loss budget.

## What each candidate mechanism does, and what evidence exists for the multiclass version specifically

- **Focal loss** down-weights easy (usually background, or in our case majority-class
  foreground) voxels via a `(1-p)^γ` modulating factor, concentrating gradient on
  hard/misclassified voxels. Coronary evidence above (Pan et al.) is **binary**
  foreground/background only — it addresses the *first* imbalance, not the
  *second*. No coronary or vascular paper found in this search applies per-class
  focal weighting across multiple *foreground* vessel classes and measures the rare
  distal classes separately; this is a gap.
- **Tversky loss** generalises Dice with independently tunable false-positive/
  false-negative weights (α, β), letting the objective trade precision for recall —
  useful when a class is so rare that plain Dice's symmetric penalty lets the
  network predict "absent" cheaply. A 2026 coronary CCTA paper (*Transformer Based
  Coronary Artery Segmentation Using Tversky Loss Function on 3D CCTA Images*, SN
  Computer Science, DOI 10.1007/s42979-025-04619-5) exists and is squarely on this
  question, but its content — the α/β values chosen and the quantitative comparison
  to Dice+CE — was **not accessible this session** (Springer redirected to an
  authentication page; no UofT-authenticated browser available). **Flagged for hand
  fetch**; do not treat its existence as evidence until read.
- **Focal Tversky loss** (Abraham & Khan, 2019, general medical imaging; not opened
  this session, found only via secondary summaries) composes the two ideas: a
  focal-style exponent on top of the Tversky index, so that both the
  precision/recall trade-off and the hard-example emphasis apply together. No
  coronary-specific measurement located.
- **Per-class weighting in the Dice/CE sum.** nnU-Net's default sums Dice and CE
  "computed independently for each foreground class and averaged uniformly" — this
  is itself already a form of per-class balancing relative to plain pooled
  cross-entropy (which would let large classes dominate the pooled voxel count), but
  it is *not* frequency-aware: a class present in 5% of cases contributes the same
  per-class average term as one present in 95%, at the batch level, whenever it
  appears. Whether to go further and inverse-weight by class frequency is
  unmeasured on vascular multiclass data in every source surfaced this session.
- **Mechanistic evidence that the right fix is instance-count-aware, not just
  voxel-count-aware**, from a non-vascular but directly relevant multiclass source:
  Kundu, Kofler, Ivory, et al., *Instance Awareness of Multi-class Semantic
  Segmentation Loss Functions*, arXiv:2604.24276 (preprint; BraTS-METS 2025 brain
  metastases, 260 test cases). Plain voxel-averaged Dice+CE: 0.59 ± 0.27 foreground
  Dice. Extending instance-sensitive losses (blob loss, CC loss — originally
  single-class) to multiclass via one-vs-rest decomposition so "each class
  contributes equally regardless of frequency": 0.64 ± 0.26 foreground Dice and
  improved rare-class Dice; confining inverse-size weighting to each connected
  component's own spatial context (global inverse weighting was reported to
  destabilise training) pushed rare-class Dice to 0.44 ± 0.36. Not our anatomy, but
  the mechanism — reweighting by connected-component instance, not by raw voxel
  count, and doing so locally rather than globally to avoid destabilising the more
  common classes — is a specific, testable design worth carrying into a coronary
  ablation, and is more mechanistically precise than "add class weights", which is
  the form most of the coronary-adjacent literature stops at.

## Where the literature disagrees or is thin

- The one paper with a direct binary coronary CTA number (Pan et al.) uses a
  reporting convention (pooled DSC 0.97) that is inconsistent with every other
  benchmark this project cites (ImageCAS 0.83, TopCoW's coronary-relevant numbers in
  the 0.80s), which is a reason to distrust cross-paper DSC comparisons in this
  literature generally, not specifically a reason to distrust focal loss.
- No paper found runs a controlled ablation of focal loss, Tversky loss, and class
  weighting **against each other, on the same coronary or vascular multiclass
  dataset**. Every candidate above is argued from a different dataset or a
  different (binary) version of the imbalance problem. This sub-question is
  materially less settled than the topology-loss question in the sibling note,
  where at least BCS gives a 3-seed, 3-backbone, same-cohort comparison.

## What this implies for [[Training plan]]

1. **Do not adopt focal loss, Tversky loss, or manual class weighting as the
   baseline based on current evidence.** Every coronary-specific number found
   addresses foreground-vs-background, which nnU-Net's default Dice+CE already
   handles adequately per [[Topology-aware losses on thin tubular structures]]'s
   conclusion; no evidence isolates a fix for foreground-vs-foreground imbalance on
   vascular anatomy.
2. **Treat this as an open experiment gated on the multiclass baseline's own
   failure pattern**, exactly as [[Topology-aware losses on thin tubular
   structures]] already recommends for cbDice: if per-class Dice in the multiclass
   baseline shows the TopCoW pattern (rare branches near zero while proximal
   trunks score normally), the first thing to try is nnU-Net's own per-class
   Dice+CE averaging pushed further — inverse case-frequency weighting per class,
   confined per the BraTS-METS design to avoid destabilising common classes — before
   reaching for focal or Tversky reformulations that have no vascular measurement
   behind them.
3. **Flag for hand fetch:** *Transformer Based Coronary Artery Segmentation Using
   Tversky Loss Function on 3D CCTA Images* (SN Computer Science, DOI
   10.1007/s42979-025-04619-5) is the one paper squarely on this question and is
   currently unread.
4. **Judge any class-imbalance fix on per-class Dice and branch detection rate for
   the rare classes specifically**, never on mean Dice — the same evaluation
   discipline [[Topology-aware losses on thin tubular structures]] already
   establishes for the topology-loss experiment, and doubly necessary here since a
   class-imbalance fix could trivially inflate mean Dice by improving a class that
   was never the problem.

Related: [[Topology-aware losses on thin tubular structures]],
[[Class-balanced and vessel-anchored patch sampling for rare distal branches]]
(architecture-folder sibling on the sampling side of the same problem).
Collected in [[Proposed changes]].

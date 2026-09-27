---
aliases: [Proposed changes, Consolidated proposals]
tags: [training/method, decision-record, proposal, review]
status: awaiting review
repo: Asclepius
updated: 2026-09-20
---

# Proposed changes to the training plan

Everything the research produced, in one place, ordered by what it would change
rather than by which folder it came from. [[Training plan]] is untouched: an
item moves there only when you accept it, and whatever the plan loses in the
process belongs in [[Plan status]].

Source material is in `vault/Research/`, seven folders of notes, each with its
own `Proposed changes.md`. This file supersedes those for review purposes; they
keep the full reasoning.

## How to read the evidence markers

Roughly half of this rests on papers somebody actually opened. The rest does
not, and the difference matters more than any individual item.

| Marker | Means |
|---|---|
| **[verified]** | Full text opened and the passage read, logged in [[Verification log]] |
| **[source]** | Verified in nnU-Net's or this repo's own source code |
| **[reported]** | An agent read the paper and cited it, but nobody re-checked it |
| **[unverified]** | Rests on an abstract, a search snippet, or a second-hand citation. **Do not act on these without fetching the paper.** |

---

## 0. The finding that changes the shape of the project

**ImageCAS-X already provides per-branch labels for 800 of your 1000 cases,
under CC BY 4.0.** **[verified]**

Bransby et al. (arXiv:2608.30404) re-annotated 800 of the ImageCAS scans into a
14-class per-branch schema and released the labels on Zenodo
(10.5281/zenodo.21887809) under CC BY 4.0.

The plan's premise is that *"ImageCAS ships one merged binary lumen mask per
case; per-branch labels are produced by our annotators and do not exist yet."*
On the evidence, the second half of that sentence is no longer true.

This does not make the annotation programme pointless, but it changes what it
is for. Three options, and this is a decision only you can make:

1. **Train the multiclass model on ImageCAS-X now**, and redirect annotators to
   the 200 cases ImageCAS-X excluded, to independent verification of a sample,
   or to a second opinion on the classes where agreement is weakest.
2. **Keep annotating from scratch** and treat ImageCAS-X as a held-out
   comparison — defensible if you want labels whose protocol you control end to
   end, but it costs a term of annotator time to reproduce something that
   exists.
3. **Seed from ImageCAS-X** and have annotators correct rather than draw, which
   is the cheapest path to labels you have checked yourself.

Everything in §2 below assumes this question gets answered first, because the
fold scheme, the sequencing and the annotation protocol all depend on it.

**The Zenodo record was checked directly (2026-09-20), not just read about in
the paper.** It exists, it is titled *ImageCAS-X*, it covers **800 CCTA scans**,
and it states **Creative Commons Attribution 4.0 International**. Contents:

- `ImageCAS-X_dataset.zip` (1.4 GB) — voxel-wise annotations of vessel lumen
  **and coronary segments**, coronary centerlines, mesh surfaces, and
  scan-level descriptors.
- `pretrained_weights.zip` (1.6 GB) — pretrained weights for **six** coronary
  segmentation methods.

Two things worth noticing. The centerlines and descriptors come with it, which
is what §2.1's centerline-based labelling and §2.2's dominance stratification
both need. And six pretrained baselines arrive for free — the comparators for
a paired experiment, without training any of them.

One caveat: the Zenodo page says "coronary segments" without naming the schema.
The 14 classes come from the paper, not the record. The *ImageCAS-X import
check* below still applies — download it, confirm the label granularity is what
the paper describes, and spot-check 20 cases against your own conventions
before building on it.

---

## 1. Corrections — where the plan currently says something untrue

These are not improvements. They are errors, and they should be fixed whatever
else you decide.

### 1.1 The inter-observer ceiling of 0.856 is the wrong kind of number **[verified]**

The plan's Evaluation section cites *"inter-observer agreement ≈ 0.856 — the
ceiling, not a target."* It traces to ASOCA
(doi:10.1038/s41597-023-02016-2), where 85.6 % ± 7.7 % is agreement on the
**binary lumen** — foreground against background, one class.

Using it as a per-branch ceiling compares two different tasks and flatters the
target: annotators who agree a voxel is vessel can still disagree about which
vessel owns it.

**Replace with** ImageCAS-X's per-branch figures on the same cohort **[verified]**:
92.8 merged, ~95 RCA, ~92 LAD, ~85 LCx, 74–84 named branches, 71–81 for the
dominance-dependent branches. Note how steeply that falls — the ceiling is not
one number, it is a curve by vessel.

### 1.2 The cascade trigger is 25 %, not 12.5 % **[source]**

§2 gate (a) says *"patch fraction ≥ 12.5 % so no cascade is planned"*. nnU-Net
v2's `lowres_creation_threshold` is **0.25**, verified at tags `v2.5.1`,
`v2.6.2` and `master`. The same figure appears in
`configs/tasks/Dataset710_Coronary.yaml`.

The plan's estimated 27–30 % patch fraction is a few points clear of the real
threshold, not more than double it. The conclusion survives; the margin is much
thinner than written, which matters because the gate exists to catch exactly
that.

### 1.3 The rare-branch starvation mechanism is misdescribed **[source]**

§5 says nnU-Net *"picks one random foreground class for a third of patches"*, so
rare branches starve. Verified in `DataLoader3D.get_bbox`: the per-case choice
among classes **present in that case** is already uniform. That step is not
where starvation comes from.

Starvation is at **case-selection frequency** — a class present in a small
fraction of the 1000 cases gets attention only when one of those cases is drawn,
with no compensation for cohort-wide rarity. A fix has to reweight case
selection or per-case slot allocation, not the already-uniform class choice.
The standing experiment stays; its description and its implementation change.

### 1.4 The 82.96 % benchmark is weaker than the plan implies **[verified]**

The plan calibrates the binary model against ImageCAS's published 82.96 % Dice.
That figure is an under-trained baseline (~21 k iterations against nnU-Net's
~250 k), scored against labels a later re-annotation disagrees with at **41.8 %
Dice** (§1.5). Beating it is not evidence of much.

**Replace the calibration target** with ImageCAS-X's table: nnU-Net 89.8 ± 3.2,
CAS-Net 91.2 ± 2.8, inter-observer 92.8 ± 3.1, all binary lumen on their
160-case test set.

### 1.5 ImageCAS's masks are weak labels **[verified]**

Bransby et al. measured **41.8 % Dice** between the original ImageCAS masks and
their re-annotation of the same 800 scans. That is a systematic disagreement
about where a lumen boundary sits, not observer noise, and the original masks
include plaque, pulmonary vessels and coronary veins.

Two consequences: the binary model's calibration number is measured against
labels of uncertain quality; and those same masks seed the presegmentations
annotators are handed, so the bias propagates into whatever they produce.
**The annotation UI must make deleting a seed voxel as cheap as drawing one.**

### 1.6 Mirroring is disabled in two places, and the plan names one **[reported]**

§4 rules out mirroring augmentation. nnU-Net applies mirroring at **test time**
as well as during training, and the plan names only the training-time use. Both
need disabling for the multiclass model, for the same reason.

### 1.7 Two smaller factual fixes **[reported]**

- The ImageCAS resolution penalty is **−12.32 %** (512²×256 → 128³,
  p < 0.0001). Worth adding the intermediate point, **−7.38 % at 256²×128**,
  because that is the one resembling a cascade's low-resolution stage, and it
  alone is six times the effect of any architectural change in the same
  ablation.
- nnU-Net's largest-component post-processing is a *measured, conditional* step
  in the original method, adopted only if cross-validation shows no per-class
  loss. The plan is right to rule it out here, and should say it is overriding a
  conditional rule rather than a blanket one.

---

## 2. Open questions the research can now close

The plan lists five open questions. Four can be closed or narrowed; one cannot.

### 2.1 Class schema — closable **[verified for the schema's existence; [reported] for the rationale]**

**Adopt the ImageCAS-X 14-class schema:** LM, LAD, LCx, D1, D2, OM1, OM2, IM,
RCA, R-PDA, R-PLA, L-PDA, L-PLA, Other. No proximal/mid/distal split — those are
reported from the centerline afterwards.

Why this one: it is the SCCT 18-segment model with the landmark-based cuts
removed, it is the only published voxel-level multiclass schema on this cohort,
and labels already exist in it for 800 of your cases.

Supporting decisions:
- **Report at three granularities from the same model** — 14-class, a
  Hampe-style merge, and 4-class trunks. Fourteen merges down to four; four
  never splits into fourteen. Costs nothing and separates "cannot find the
  vessel" from "cannot name it".
- **Labelling happens on named centerlines, not painted voxels.** In ImageCAS-X
  segment names live on the centerline and each lumen voxel takes the name of
  its nearest centerline point. Adopting the schema means adopting that
  construction — which has direct consequences for the Slicer tool.
- **A taper rule is still needed.** SCCT does not say when to stop labelling a
  vessel thinning below resolution. Pick one (diameter < 1.0 mm, visibility, or
  follow-the-centerline) and calibrate on 5–10 cases before live annotation.
- **No published work validates one schema against another on the same data.**
  This stays a judgement call, made on grounds of compatibility, not measured
  superiority.

### 2.2 Fold scheme — closable **[reported]**

- **Binary calibration run:** ImageCAS official `Split-1` (700/50), scored on
  its 250 test cases. The only configuration where "beat 82.96 %" means
  anything.
- **Multiclass runs:** seal ImageCAS-X's 160-case test set, 5-fold CV over the
  remaining 640. Ablations on fold 0; all five folds only for the final config,
  because of walltime.
- **Leakage trap, and it is a real one:** binary-init fine-tuning is only valid
  if the binary model never saw the 160 ImageCAS-X test cases. Otherwise the
  multiclass test set has leaked in through initialisation. Either retrain the
  binary model on ImageCAS-X's 640, or drop the experiment. Compute and record
  the ID intersection so this is a documented fact rather than a trap somebody
  rediscovers.
- **Stratify folds on dominance and disease status** (ImageCAS-X reports
  729 right / 41 left / 30 co-dominant; 388 diseased / 412 not). Unstratified
  folds can starve L-PDA and L-PLA entirely.

### 2.3 Loss — narrowable, not closable **[verified for the numbers; the recommendation is a judgement]**

- **Baseline Dice+CE unchanged.**
- **Skeleton Recall** as the scheduled second experiment, with acceptance
  measured on per-class detection rate and centerline overlap for the smallest
  classes — **not mean Dice**, which every coronary measurement found moved less
  than seed-to-seed noise.
- **clDice ruled out** on this task: it OOM'd at 13 classes on 40 GB at default
  patch size, and both coronary measurements that exist show it as a no-op or a
  regression on topology metrics. **[reported]**
- **cbDice conditional**, triggered only if rare classes score near zero. Its
  headline result — small-vessel Dice 0 → 43.38 — is **[verified]** but narrow:
  Circle of Willis, not coronaries, 18 test cases, from a baseline that found
  nothing at all. That is "the baseline never detected these vessels", which is
  a different claim from "cbDice improves segmentation".
- **Per-class inverse-frequency weighting** as a conditional experiment if a
  class scores < 20 % Dice despite being present in > 20 % of cases.

### 2.4 Acceptance thresholds — provisionally closable **[reported]**

A five-tier table exists (trunks / common / variable / rare / topology), plus a
concrete Betti-0 ≤ 1 gate for the four trunk classes anchored on ImageCAS-X's
inter-observer Betti error of 0.2–0.4. Mark it provisional until the multiclass
baseline exists.

State explicitly that these measure segmentation quality against a human
reference, **not clinical utility**. No outcome or invasive-reference study
exists here, unlike the cleared products the research surveyed.

### 2.5 Annotation protocol — partly closable, with one hard limit **[verified]**

Sim & Wright's Table 8 settles the sizing question, and the answer is
uncomfortable:

| Goal | Cases needed (80 % power, 2-tailed) |
|---|---|
| Show agreement beats chance | 13 |
| Show κ ≥ .80 when you would reject below .60 | 126 |
| Show κ ≥ .70 when you would reject below .60 | 503 |

And requirements rise sharply as a class gets rare — roughly triple at 10 %
prevalence. Your dominance-dependent branches sit near 1 %, past the end of the
table.

**So: size the overlap set for the common branches, and report the rare ones as
wide-interval estimates rather than measured ceilings.** No affordable duplicate
rate will measure them. More raters per case does not substitute for more cases
— beyond three raters, power barely moves.

Everything else in the protocol is workable:
- SegQueue's 5 % gold / 5 % duplicate / sampled review / 5-case training gate
  stand as the operating design.
- **The QA statistic needs four changes**: per-class flagging rather than a case
  mean; a missed-structure check against the model's own presegmentation; a
  trend across an annotator's last 5–10 cases rather than a single threshold;
  and signed rather than absolute per-class bias.
- **Topological validation needs no duplicate at all** — a valid tree, one
  parent per segment, no cycles, plausible parent-child relations. Under 5
  seconds a case. Given that duplicates cannot cover the rare classes, this is
  the cheaper protection and should be built first.
- **Intersection auto-accept**: where two blind annotations already agree per
  class at or above the human ceiling, accept the intersection and skip review.
- Expect **20–30 cases to proficiency**, steepest gains in the first 15–20.
  Weight a new annotator's first ~15 cases lower in arbitration. **[unverified
  — extrapolated from endoscopy training studies, no coronary-specific source]**

---

## 3. Additions worth making

### 3.1 Pre-submission gates (all cheap, all before any GPU time)

Added to the existing patch-fraction / spacing / batch-size gates:

| Gate | Why | Evidence |
|---|---|---|
| Read the CT normalisation window from `dataset_fingerprint.json` | nnU-Net normalises on a lumen-only foreground; a narrow window (150–700 HU) would warrant a paired experiment against whole-volume percentiles | **[reported]** |
| Confirm the anisotropy branch does **not** fire | If it does, through-plane resampling silently drops to nearest-neighbour for image and label — the mode most likely to destroy a 1–2-voxel vessel cross-section | **[reported]** |
| Confirm sliding-window overlap is 50 % | Baseline for the fragmentation lever in §3.4 | **[reported]** |

### 3.2 Evaluation additions

The single most important one: **report per-class tables always, and state the
averaging rule.** Macro and micro differ by 2–5 Dice points on this class
distribution, because the dominance-dependent branches appear in under 1 % of
cases. A headline mean without a stated rule is ambiguous. **[reported]**

Beyond that:
- **NSD tolerance is currently indefensible.** The 1.5 mm default is ~4 voxels
  at coronary spacing — wider than a distal vessel. Derive it per class from the
  annotation overlap set (95th percentile of inter-annotator surface distances);
  use one voxel (≈0.35 mm) until that exists. **[reported]**
- **NaN policy in two halves**: absent-in-both is skipped; present-in-one scores
  the worst value with a *finite* distance bound.
- **Branch detection rate** as per-class recall at IoU ≥ 0.25, reported with
  detection F1.
- **Betti-0 error per class**, and Betti *matching* error for the final config —
  plain Betti-0 is cancellation-blind to a dropped branch plus a hallucinated
  fragment.
- **Per-component class purity**, because a model can pass a component count
  while mislabelling pieces of a correctly-found branch.
- **Rename AHD to MASD** and define it. Never report bare HD.
- **Per-case distributions and confidence intervals** on every per-class metric.
  Some classes will have single-digit case counts.
- **Subgroup breakdowns** by dominance and disease status, and by the segments
  most exposed to motion artefact (mid RCA, mid and distal LAD).
- **Fewer decimal places.** More than one is not meaningful against this
  inter-rater variability.

### 3.3 External validation — new, not currently in the plan **[reported]**

Score the binary model on ASOCA's 40 labelled cases (different vendor, different
protocol). Expect a 5–8 Dice-point drop; a larger one signals overfitting to
ImageCAS's single-centre protocol. Report contrast enhancement and edge sharpness
alongside, the strongest measured correlates.

State plainly in any manuscript that **no external per-branch benchmark exists**.
Under reporting-standards guidance an undisclosed absence of external validation
is a completeness gap, not a neutral omission.

### 3.4 Experiments, ranked

| Priority | Experiment | Note |
|---|---|---|
| 1 | **Binary-init fine-tuning vs from-scratch** | Promote from unranked to first. Costs nothing beyond a checkpoint the plan already produces. Analogy: in-domain SSL on this exact cohort measured +4.8 Dice, largest when fine-tuning data is scarcest — the regime the multiclass model starts in. **Subject to the leakage constraint in §2.2.** **[reported]** |
| 2 | **Patch-budget sanity run** | Plan the binary model at `--gpu-mem 24` and `--gpu-mem 70`, train both on one fold. Published patch-size curves stop at 64³, and nnU-Net Revisited showed VRAM scaling going *negative* on three of six datasets. Converts the plan's central extrapolation into a measurement, before any per-branch labels exist. **[reported]** |
| 3 | **Skeleton Recall** | §2.3 |
| 4 | **Class-balanced sampling**, reimplemented at case-selection frequency | §1.3 |
| 5 | **Partial-annotation self-training** | 24.29 % of branches labelled reached parity with full annotation via self-training. The largest available lever on annotator hours if it holds — but **[unverified]**, abstract only, and it should be tested before the team commits a term. |
| 6 | **Deep supervision**, **elastic-deformation ablation**, **TTA / overlap tuning** | All conditional on the baseline showing the specific failure each addresses. |

**Write down the expected effect size for the ResEnc run before you run it.**
ResEnc L gained +2.13 (KiTS) and +0.77 (AMOS) Dice over plain nnU-Net; an
isolated residual-encoder ablation put it at +0.37. **A paired difference under
~0.5 Dice is inside the noise and the plain configuration stays.** ResEnc L was
also 3.9× the training time, which is the binding constraint against a 24-hour
walltime. **[reported]**

### 3.5 Things to add to "explicitly ruled out"

- **Mamba-based U-Nets** — the "No-Mamba Base" ablation matched or beat both
  U-Mamba variants on five of six datasets at lower VRAM. Nothing to buy. **[reported]**
- **Promptable / foundation models as the primary segmenter** — MedSAM has a
  documented weakness on branching vessels; vesselFM scores 29.69 Dice zero-shot
  on its only CT vascular benchmark; VISTA3D reports no coronary class and uses
  128³ patches. And the one coronary SAM paper concedes in its own discussion
  that it *"does not significantly outperform other approaches"* on artery
  segmentation. **[verified]**

### 3.6 Strengthen the graph-model carve-out with its measured mechanism **[reported]**

§4 says graph reasoning must never lose a vessel the voxel model found. Hampe et
al. measured exactly that: labelling F1 **0.95 on reference trees against 0.74
on the model's own extracted trees** — a 21-point gap from upstream extraction
error alone, attributed to missed septal branches and ostium-leak pruning. Any
pruning step inside a downstream graph stage is where a real vessel gets
silently deleted, and is the step to audit hardest.

Two downstream candidates are worth recording without scheduling: **centerline
reconnection** for fragments the model found but did not connect (DPC-Walk:
88.53 % Dice and HD95 1.07 mm on ASOCA against a best baseline of 86.08 % and
5.25 mm, 92.22 % reconnection accuracy **[verified]**), and a **topology-graph
relabelling pass** for fragments found and connected but misnamed.

### 3.7 Licensing — settle before weights exist **[verified]**

| Source | Licence | Consequence |
|---|---|---|
| ImageCAS (1000 merged masks) | None stated; Kaggle distribution carries Apache 2.0 but the masks do not | Author permission needed before releasing weights trained on them |
| ImageCAS-X (800 cases) | CC BY 4.0 | Weights releasable with attribution |
| ASOCA (40 cases) | CC BY 4.0 | External-validation results publishable |

Pick a licence for the labels this project creates — CC BY 4.0, for consistency
— and say so in the release. Your README already says weights follow the
training data's terms, so this is answering a question you have already asked.

---

## 4. Code gaps in `src/segtrain`

Fourteen were identified in `metrics.py` and `evaluate.py`. The ones that
silently corrupt results, first:

| # | Gap | Why it bites |
|---|---|---|
| M5 | `hausdorff95` returns `inf` for one-sided absence and `agreement()` serialises it to `None` | **The worst cases vanish from the means.** This is precisely the failure the metric exists to catch |
| M8 | `summarize()` pools all (case, structure) pairs into one mean Dice | The aggregation pitfall Metrics Reloaded warns about; per-class means should be the headline |
| M6 | `DEFAULT_NSD_TOLERANCE_MM = 1.5` | Inherited from whole-body data; ~4 voxels here |
| M1 | No clDice | The named recommendation for tubular structures; ~30 lines |
| M2 | No detection outcome or per-class IoU | Branch detection rate cannot be computed from current output at all |
| M3 | No connected-component or Betti-0 count | The plan asks for component counts; nothing computes them |
| M4 | No inter-class confusion matrix | LAD/LCx confusion is a *swap*; one-vs-rest Dice reports it as two mediocre scores instead of one systematic error |
| M7 | No MASD/ASSD | ImageCAS's comparison number is of this family; their table is currently unreproducible |
| M9–M14 | Bootstrap CI helper, surface-extraction convention recording, worst-case export, per-class tolerance table, Betti matching, subgroup breakdowns | Smaller, mostly reporting-completeness |

---

## 5. Not evidenced — do not act on these yet

| Claim | Status |
|---|---|
| Partial annotation at 24.29 % reaches parity | **[unverified]** — abstract only, PDF exceeded fetch limits |
| Annotator proficiency at 20–30 cases | **[unverified]** — extrapolated from endoscopy, no coronary source |
| Per-class weighting helps small bronchioles (airway analogue) | **[unverified]** — abstract only |
| Tversky loss on CCTA | **[unverified]** — paywalled, never opened |
| JLNet direction-aware learning | **[unverified]** — ACM paywall |
| Topology-benchmark LNCS chapter | **[unverified]** — Springer login wall |
| AJR stent editorial | **[unverified]** — 403 |
| CCA-200 diameter-series format | **[reported]** — verified as 1D diameter annotations, unsuitable for voxel training |
| Stent prevalence in ImageCAS | **Unknown.** Not documented in the metadata; needs a direct check against the Girder copy or the authors |
| Calcium-blooming augmentation | Physics is now simulatable (a validated phantom simulator exists) but **nobody has trained a segmenter with it**. Genuinely open |

Two claims that look like literature gaps rather than access failures, and are
worth knowing as such: **binary-to-multiclass transfer is unmeasured anywhere**
for coronaries, and **no controlled focal/Tversky/class-weighting ablation
exists** for vascular multiclass data. Those are experiments to run, not papers
to find.

---

## Where this came from

| Folder | Notes | Its own proposals |
|---|---|---|
| `Research/Class schema/` | 12 | Schema, bifurcation, taper rule |
| `Research/Annotation and label efficiency/` | 8 | Protocol, QA, label efficiency |
| `Research/Architectures and training/` | 9 | Cascade, patch budget, ResEnc, sampling |
| `Research/Losses and topology/` | 6 | Skeleton Recall, post-processing, connectivity |
| `Research/Augmentation and preprocessing/` | 8 | Gates, confounders, cross-site |
| `Research/Datasets and benchmarks/` | 7 | ImageCAS-X, folds, licensing, external validation |
| `Research/Metrics and clinical validation/` | 12 | Metric pool, thresholds, reporting |
| [[Verification log]] | — | 22 claims audited: 12 resolved, 1 wrong, 7 unreachable, 2 unfinished |

84 notes, about 11,600 lines. The research was done without institutional
access for most of its life, which is why the evidence markers exist and why
§5 is as long as it is.

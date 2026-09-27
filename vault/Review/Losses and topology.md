---
tags: [review, verification, decision-record]
status: complete
updated: 2026-09-26
slice: Research/Losses and topology, proposals §2.3, §3.6, plan §4
---

# Review 04 — Losses, class imbalance, topology, post-processing

Reviewer 4 of 10. Slice: `vault/Research/Losses and topology/` (7 notes), cross-referenced
against `vault/Training method/Training plan.md` §4–§5, `vault/Proposed changes to the
training plan.md` §2.3 / §3.6, and `vault/Research/Verification log.md`.

Every number marked "confirmed" below was read by me from the primary source this session.

---

## 1. Verdict (5 lines)

1. **The loss recommendation holds, but for partly the wrong reasons.** Skeleton Recall is the
   right second experiment — its published benchmark includes a 13-class vascular case, which is
   this problem's shape — but it is not "a trainer swap", and its cost figures were measured at a
   patch size 8–10× smaller than this plan's.
2. **clDice is ruled out on evidence, not convenience — and the evidence is stronger than the
   vault knows** (three coronary measurements, not two). The *memory* half of the argument is an
   implementation artifact and should be demoted, or the ruling looks fragile.
3. **cbDice is under-rated by a cherry-picked table.** On PARSE (the closest 3D-CT vascular
   dataset) cbDice at its own tuned β beats CE+Dice on all four columns across all three
   backbones; the vault quoted only the β=2 row and concluded the opposite.
4. **The post-processing ban is correct and correctly characterised** (`determine_postprocessing`
   confirmed conditional in source), but the DPC-Walk evidence in proposals §3.6 cites the wrong
   comparator and overstates what reconnection buys by ~75%.
5. **Fragment misassignment is not addressable by any loss on the table** — the vault says so and
   is right; but the ordering is arguably backwards: metrics and reconnection are where the only
   measured coronary topology gains are, and the loss experiment is the arm with the weakest
   measured effect and the largest noise floor.

---

## 2. Errors found, ranked by what changes the plan

### E1 — cbDice's PARSE result is cherry-picked; the conclusion drawn from it is false
**Vault says** (`Topology-aware losses on thin tubular structures.md:134-137`): "PARSE 2022 …
CE+Dice 85.05 Dice, 80.11 clDice, 277.7 β-err; +clDice 85.30 / 80.23 / 263.4; +cbDice(β=2)
84.91 / 80.02 / 275.8. On this 3D CT vascular dataset **cbDice did not beat plain CE+Dice on any
of the three columns**." Repeated at `:246-248` as a "where the literature disagrees" item, and
it is the load-bearing reason §2.3 demotes cbDice to a rescue measure.

**Actually true.** arXiv:2407.01517v1, table "Comprehensive comparison of results on the Parse
2022 and TopCoW 2023 datasets" — the nnU-Net PARSE rows are (Dice / clDice / β^err / NSD):

| Loss | α | β | Dice | clDice | β^err | NSD |
|---|---|---|---|---|---|---|
| — | 0 | 0 | 82.55 | 68.91 | 331.5 | 78.51 |
| — | 1 | 0 | 85.05 | 80.11 | 277.7 | 86.04 |
| clDice | 1 | 1 | 85.30 | 80.23 | 263.4 | 86.20 |
| **cbDice** | 1 | **1** | **85.46** | **80.76** | **266.1** | **86.57** |
| cbDice | 1 | 2 | 84.91 | 80.02 | 275.8 | 85.98 |
| cbDice | 1 | 3 | 84.97 | 78.98 | 285.6 | 85.26 |

β=1 beats CE+Dice on Dice (+0.41), clDice (+0.65), β-err (277.7→266.1) and NSD (+0.53), and beats
clDice on three of four. The same ordering holds for SwinUNETR (82.19/71.04/476.5 vs baseline
81.94/69.87/496.9) and NexToU (85.19/80.07/248.95 vs 85.08/79.39/288.5). The vault quoted the β=2
row — the value tuned for TopCoW, not for PARSE.

**Also false by implication:** clDice on PARSE is *not* a no-op either (+0.25 Dice, β-err
277.7→263.4). The vault's generalisation "clDice does nothing on 3D CT vasculature" is
contradicted by the cbDice paper's own table; only the *coronary* evidence supports it.

**Fix.** Correct `:134-137`. cbDice is not a rare-class rescue measure only — on the closest 3D CT
vascular benchmark it is a consistent small win across three backbones, with β as a real
hyperparameter that must be tuned, not inherited. That is a stronger case than the 18-case TopCoW
result §2.3 currently rests it on.

### E2 — The DPC-Walk evidence in proposals §3.6 uses the wrong comparator
**Vault says** (`Proposed changes to the training plan.md:384`): "DPC-Walk: 88.53 % Dice and HD95
1.07 mm on ASOCA against a best baseline of 86.08 % and 5.25 mm, 92.22 % reconnection accuracy
**[verified]**". Traced to `Verification log.md` second pass, entry 16, which says the folder note
"understates it" and that the real figures are "+2.45 Dice over the best baseline and 5.25 → 1.07".

**Actually true.** arXiv:2504.01597 (Qiu et al., confirmed title/authors/abstract). ASOCA, 40
training cases (20 normal, 20 diseased) + 20 test, five-fold CV:
- Table 1 (method comparison): ResUNet 82.03 ± 1.39 / HD95 7.51 ± 0.85; ADE-HTL Net 86.08 ± 1.21 /
  5.25 ± 0.43; CorSegRec 88.53 ± 1.81 / 1.07 ± 0.60.
- **Table 9 (stage ablation): stage 1 only 87.13 / 5.06 → stages 1+2+3 88.53 / 1.07.**
- Table 6: reconnection accuracy 92.22 %, sensitivity 98.20 %, specificity 82.79 %. Confirmed.

So 86.08/5.25 is a *different published method*, not the pre-reconnection state. The
reconnection-attributable effect is **+1.40 Dice and 5.06 → 1.07 mm**, and even that bundles
stage 3 (implicit reconstruction of vessels the network never saw — the step the vault itself
flags as geometry invention, `Largest-component…:147-149`). There is no 1+2 row: **stage 2 alone
is never isolated in the paper.**

**Fix.** §3.6 should read "+1.40 Dice, HD95 5.06→1.07 mm, attributable to stages 2+3 together;
stage 2 not isolated; no nnU-Net baseline anywhere in the paper." The folder note
(`Largest-component…:123-131`) had this right; the Verification log's "correction" is the error
and propagated into the proposals.

### E3 — Three factual errors in the gap-bridging note about the same paper
`Gap bridging and centerline-based reconnection…md`:
- `:172-174` labels 87.13 / 5.06 as "Baseline segmentation (ResUNet)". ResUNet is 82.03 / 7.51.
  87.13 / 5.06 is CorSegRec's own stage 1 (NSDT soft-clDice network).
- `:184` "ASOCA only (80 training, 20 test cases)". It is 40 training + 20 test.
- `:172` expands ASOCA as "Atlas Segmentation of Coronary Arteries". It is **Automated**
  Segmentation of Coronary Arteries.

### E4 — "Skeleton Recall was tested on airway datasets as well as coronary (TopCoW, ASOCA)"
**Vault says** `Airway segmentation as the closest analogue…md:39`, restated at `:78` and `:90`
("proven on airway-adjacent data (TopCoW)").

**Actually true.** arXiv:2404.03010v2, confirmed: the five datasets are **Roads (2D), DRIVE (2D),
Cracks (2D), ToothFairy (3D), TopCoW (3D)**. No airway dataset. No ASOCA. No coronary anything.
This directly contradicts the sibling note's own verbatim table
(`Topology-aware losses…:93-112`), which is correct.

**Fix.** Delete the claim. The airway note's recommendation #1 survives on the TopCoW 13-class row
and the BCS coronary result, but its stated support is fabricated.

### E5 — Misattributed citation: "Kingma et al."
`Airway segmentation as the closest analogue…md:31` cites *Airway Segmentation Based on
Topological Structure Enhancement Using Multi-task Learning* (MICCAI 2024) to "Kingma et al."
The paper is real (LNCS 15009, doi:10.1007/978-3-031-72114-4_9) but is by **Yang, X. et al.**
This is the only wrong-author citation I found in the slice; it has the shape of an agent
hallucinating a familiar name.

### E6 — The BCS paper never measured cbDice
**Vault says** `Loss weighting between large proximal and rare distal branch classes.md:204`:
"BCS paper benchmark … found clDice did nothing on Dice (−0.004 to +0.001) and **cbDice did
nothing on Dice** (+0.006 in one case, −0.013 in another) … The rare-class rescue shown in TopCoW
(0→43) did not replicate."

**Actually true.** arXiv:2607.28327 Table 2 confirmed in full: the four loss arms are Baseline,
clDice, Soft-BCS, Skeleton Recall. **There is no cbDice row**, and the quoted deltas match no row
in the table. As written this reads as a second, coronary refutation of cbDice that does not
exist — and it silently contradicts §2.3, which still keeps cbDice as a conditional.

### E7 — The Verification log contradicts itself, and entry 13 was never closed (I closed it)
`Verification log.md:20-23` lists entries 12 and 16 as **Resolved**; `:38-42` then says "Entry 12
… and entry 16 … Neither is verified. Treat the proposals resting on them as unevidenced." The
body's second pass (`:263-300`) *does* resolve both from full text. The header block is stale.
The same block counts entries 4 and 9 as resolved while their first-pass body entries still read
"Still unreachable" (the second pass resolved them; the entries were never updated).

Entry 13 (ImageCAS-X clDice) still reads `Outcome: [Continuing verification...]`. **I closed it:**
arXiv:2608.30404 Table 2 confirmed — nnU-Net DSC 89.8 ± 3.2 / HD95 7.08 ± 12.65 / Betti 5.6 ± 3.5;
nnU-Net + clDice 90.0 ± 3.5 / 9.70 ± 15.36 / **8.0 ± 4.4**; inter-observer 92.8 ± 3.1 / 2.46 ± 3.62
/ 0.4 ± 0.4. Post-processing "threshold at 0.5, followed by removal of connected components
smaller than 100 voxels", 0.5 mm isotropic, 160 test cases. **The clDice loss weight is genuinely
not stated** — the vault's caveat is correct.

### E8 — Order-of-magnitude arithmetic in the loss-weighting note
`Loss weighting…md:156` "proximal LAD/LCx/RCA trunks; ~500–1000 voxels in a full 512×512×250
volume … distal branches sometimes <50 voxels"; `:171` and `:221` "a distal branch might be 20
voxels in a 70 M-voxel patch (1 in 3.5 M)".

At 0.35 mm isotropic a voxel is 0.043 mm³. A 3 mm-diameter, 100 mm proximal LAD ≈ 707 mm³ ≈
**16,000 voxels**; a 1.5 mm-diameter, 20 mm distal branch ≈ 35 mm³ ≈ **800 voxels**. Both figures
are 1–2 orders of magnitude low. The patch is ~17–20 M voxels (`Training plan.md:51`), not 70 M
(70 M is roughly the whole volume). The imbalance is real; it is ~20× less extreme than the note's
arithmetic, and the note's argument at `:221` ("even with w ≈ 3.5 M the gradient is still small")
is built on the wrong denominator.

---

## 3. Weak reasoning and unsupported leaps

### W1 — clDice: ruled out on evidence, not convenience. But the stated reason is half wrong.
The memory argument is **confirmed as reported** — arXiv:2404.03010v2 verbatim: *"the inefficiency
of clDice Loss rendered it infeasible on all 13 classes as it exceeded the memory capacity of an
A100 40GB GPU"*, with *"approximately 88% additional training time and 52% more VRAM"* vs Skeleton
Recall's *"only an additional 8% training time and 2% higher VRAM"*. So `Topology-aware losses…:120-126`
and `:259` are accurate quotations.

But the OOM is a product of (soft-skeleton iterations × class count × patch voxels) evaluated on
the GPU inside the autograd graph. It is avoidable several ways — compute the term on a
foreground-vs-background binarisation, on a sampled subset of classes per step, at fewer
skeletonisation iterations, or only on the lower deep-supervision heads. **It is an implementation
artifact, not an intrinsic property of the loss.** Resting the ruling on it invites a reviewer to
fix the memory problem and conclude the ruling collapses.

The evidence half is much stronger than the vault states — there are **three** coronary
measurements, not two:
1. ImageCAS-X (arXiv:2608.30404): Betti error 5.6 → 8.0, HD95 7.08 → 9.70. Topology worse.
2. BCS (arXiv:2607.28327): 3 seeds × 3 backbones, 250 test cases. |ΔDice| ≤ 0.004, ΔBCS ≤ 0.008.
   Nothing moves.
3. **New — not in the vault:** Acebes, Moustafa, Camara, Galdran, *The Centerline-Cross Entropy
   Loss for Vessel-Like Structure Segmentation*, MICCAI 2024 (open access). **ASOCA, nnU-Net
   3D full-res, 5-fold CV**, Table 1: L_Dice 84.59 DSC / 84.81 cl-DSC; L_Dice + 0.5·L_clDice
   **83.42 (−1.17) / 84.76 (−0.05)**. The authors state plainly: *"for the most complex scenario,
   i.e. the 3D segmentation problem on the ASOCA dataset, the L_clDice not only attains lower
   segmentation performance, but it is unable to improve the topological consistency of the
   baseline L_Dice."*

**Verdict: ruled out on evidence.** Rewrite §2.3 to lead with the three coronary measurements and
demote memory to "and it is also the expensive one".

### W2 — The cbDice trigger is anchored on the least trustworthy number in the slice
§2.3 fires cbDice only "if rare classes score near zero". That trigger derives entirely from the
TopCoW 18-case row where the baseline scores exactly 0 — which the vault itself
(`Topology-aware losses…:149-159`) notes cannot be reconciled with Skeleton Recall's 85.36 mean
Dice over 13 TopCoW classes (a zero class would drag that mean). After E1, cbDice has a second,
better-controlled reason to be run that has nothing to do with rare-class rescue.

### W3 — "Skeleton Recall is a trainer swap" understates the integration cost
Verified in source. Upstream `MIC-DKFZ/nnUNet@master`,
`nnunetv2/training/nnUNetTrainer/variants/loss/` contains exactly `nnUNetTrainerCELoss.py`,
`nnUNetTrainerDiceLoss.py`, `nnUNetTrainerTopkLoss.py` — **no Skeleton Recall, no clDice, no focal,
no Tversky.** `MIC-DKFZ/Skeleton-Recall` (default branch `master`, `fork: false`, last push
2025-12-08) is a **full vendored copy of the nnunetv2 package**, containing its own
`nnunetv2/training/dataloading/data_loader_3d_skel.py`,
`nnunetv2/training/data_augmentation/custom_transforms/skeletonization.py`, and
`…/variants/loss/nnUNetTrainerSkeletonRecall.py`. That trainer overrides the dataloaders
(`nnUNetDataLoader3DSkel`), the train and validation transform pipelines
(`SkeletonTransform(do_tube=True)`), `train_step`, `validation_step`, and the
`DeepSupervisionWrapper` weights.

Consequences for this repo:
- `pyproject.toml` pins `nnunetv2>=2.5,<3`. Running Skeleton Recall means **replacing that install
  with the fork**, not passing `-tr`. The README still says *"Integration into the official nnUNet
  repo is currently discussed"* — the vault's "patched fork, pin the commit"
  (`Topology-aware losses…:270-273`) is right; proposals §2.3 / folder §1 "`-tr
  nnUNetTrainerSkeletonRecall`, pinned commit" reads like a flag and is not.
- `src/segtrain/nnunet_ext/nnUNetTrainer_segtrain.py` subclasses `nnUNetTrainer` and hooks the same
  methods to implement the 24-hour walltime checkpoint (`SEGTRAIN_MAX_SECONDS`) and the event
  stream. It must be composed by MRO against a *different* nnU-Net tree. Budget that, and re-run
  the chain-resume smoke test — the job-chain resume is the one thing in this plan that cannot
  quietly break.
- Good news the vault does not state: skeletonisation happens in the augmentation pipeline, not in
  preprocessing. **No re-preprocessing of the ~250 GB dataset is required.**

### W4 — The "8 % time / 2 % VRAM" figure does not transfer unexamined
Those figures were measured at nnU-Net's default patch sizes. This plan's patch is ~17–20 M voxels
(`Training plan.md:51`), roughly 8–10× a default 128³, and multiclass skeletonisation runs per
class on CPU dataloader workers. VRAM stays cheap; the risk moves to **dataloader starvation of
the H100**. That is one short run to measure and belongs in the §3.1 pre-submission gate list, not
in an assumption.

### W5 — The noise floor makes most of the planned comparisons unreadable
BCS reports 3-seed SDs ≤ 0.018 Dice on ImageCAS's 250-case test — **up to ~1.8 Dice points**. A
single-run paired comparison therefore cannot resolve anything below roughly 2.5 points, and
*every* coronary loss effect in this literature is smaller than that. Two consequences:
- The vault's instinct to make the acceptance criterion **per-class branch detection and
  centerline overlap for the smallest classes, not mean Dice**
  (`Proposed changes…:227-229`, folder §2) is correct and should be hardened: state that mean Dice
  is *not* an acceptance input for the loss experiment at all.
- Proposals §3.4's ResEnc rule — "a paired difference under ~0.5 Dice is inside the noise" — is
  too generous by about 4×. On this dataset the published noise floor is ~1.8.

### W6 — Architecture beats loss on the one coronary topology benchmark, and the plan never says so
ImageCAS-X Table 2 (confirmed): nnU-Net 89.8 DSC / Betti 5.6; CAS-Net 91.2 / **1.9**; ADE-HTL 87.7
/ **1.5**; inter-observer 92.8 / 0.4. The plan's chosen architecture is the **topological worst of
the trained methods on this exact cohort**, and the only loss tried on it moved Betti the wrong way
(5.6 → 8.0). If Betti-0 is going to be an acceptance gate (proposals §2.4 proposes exactly that),
then the measured lever on the method axis is 3–4× anything a loss has been shown to do here.

This does not mean abandon nnU-Net. It means: (a) say explicitly that the plan optimises DSC and
operational simplicity and accepts a topology penalty; (b) if Betti is a gate, the architecture
paired run cannot sit below the loss experiment in priority; (c) ImageCAS-X's Zenodo record ships
**six pretrained baselines** (proposals §0) — CAS-Net and ADE-HTL arrive as comparators for free,
with no training cost.

### W7 — Fragment misassignment: correct diagnosis, and no candidate loss can touch it
The vault's separation of the two failure modes
(`Enforcing per-branch connectivity…:66-86`) is the best reasoning in the slice, and the conclusion
— that this is a graph/post-processing problem — is right. Worth making the mechanism explicit,
because it is structural and it rules out the whole loss family at once:
- **Skeleton Recall** is a recall term on the *label* skeleton. It never skeletonises the
  prediction, so it cannot see the prediction's connectivity at all, and nothing in it penalises
  one connected run of voxels carrying two labels.
- **clDice / cbDice** do skeletonise the prediction, but are computed one-vs-rest per class, so an
  LAD/LCx swap is scored as two independent per-class errors, never as one systematic swap.
- None of the four can express "voxels connected along a single vessel share a label".

Two gaps in the vault's treatment:
- The detection metric (per-component class purity, §3 of the folder proposals) is proposed without
  a gating threshold. Without one it is a number nobody acts on.
- VTG-Net's evidence is **2D retinal, 2 classes** (confirmed: AV-DRIVE 94.60 ± 0.70 → 98.11 ± 0.03;
  Tongren 93.81 ± 0.32 → 97.98 ± 0.03; *"multiple class assignment of a single vessel segment"*
  confirmed). +3.5 points on a globally-separable two-class problem is an **upper bound** on a
  14-class problem whose confusions are between anatomically adjacent siblings. **Hampe is the
  better anchor**, and it is verified: labelling F1 **0.95 on reference trees vs 0.74 on extracted
  trees**, tree extraction alone F1 0.85, 104 patients, 10 AHA classes (J Med Imaging 11(3):034001,
  PMC11095121). The paper attributes the gap as the vault says: *"septal branches (class S) were
  frequently missed … typically short and thin"* and *"the moderate performance for the LM segments
  may have been associated with tracking beyond the ostium into the aorta, causing the ensemble for
  tree refinement to discard the entire branch in some cases."* Proposals §3.6 uses this correctly.
  One caveat to record: Hampe's upstream extractor is a seed-and-track pipeline, not a voxel CNN, so
  the 21-point gap is the cost of *that* extraction failure mode; a voxel model's failure profile is
  over-fragmentation rather than missed tracking. **0.95 is the more transferable number: even given
  a perfect tree, a graph labeller gets 5 % of segments wrong at 10 classes.**

### W8 — The clDice-as-metric vs clDice-as-loss tension is coherent, but a real conflict hides inside it
Keeping clDice as a metric while rejecting it as a loss is not inconsistent — the ImageCAS-X and
Acebes results are precisely the argument for it (as an objective it failed to improve its own
metric on coronaries). Say that in one sentence in the plan so no reader reads it as a
contradiction.

But there is a genuine conflict the vault records in fragments and never joins up: in BCS,
**Skeleton Recall *lowers* the clDice metric** on all three backbones (0.875→0.861, 0.890→0.874,
0.874→0.850) while raising BCS and FFR agreement, and roughly doubles β₀. If clDice and Betti-0 are
acceptance metrics (`Training plan.md:136-139`, proposals §2.4), **the scheduled experiment will
fail its own acceptance test while being the right thing to adopt.** The acceptance criterion has
to be written to anticipate this — branch detection up, connectedness up, β₀ allowed to rise,
clDice-metric allowed to fall — or it will be read as a null result.

### W9 — "No controlled focal/Tversky/class-weighting ablation exists for vascular multiclass data"
(`Proposed changes…:438`; `Class imbalance…:108-113`.) Strictly true as written, because of the
word *multiclass*. Materially misleading, because the closest analogue exists, is open access, is
heavily cited, and the slice never opens it:

**Zheng, Zhao, Gu et al., *Alleviating Class-Wise Gradient Imbalance for Pulmonary Airway
Segmentation*, IEEE TMI 2021 (arXiv:2011.11952).** Read in full this session. It runs exactly this
ablation on a branching tubular tree: **five loss functions — General Union, Root Tversky, Prior
Tversky, Tversky, Dice+wBCE — on one backbone**, with DSC, branch-detected and length-detected
reported **stratified by branch diameter** ([0,2], [2,4], [4,6], [6,8], [8,20] mm), which is the
proximal/distal imbalance in the form that matters here. Table III isolates the loss term
(GS+HSS 90.8 length / 87.1 branch → GS+GUL+HSS 92.5 / 88.7). The paper states 76 % of branches are
below 4 mm.

Crucially, it reports what goes wrong with the naive fix the vault proposes:
- *"Compared with General Union loss, Root Tversky loss does not explicitly decrease the weights of
  large airways, leading to a dilated segmentation and a decreased DSC for the branches with a
  diameter between 2 mm and 8 mm."*
- *"Prior Tversky loss shows lower DSC and sensitivity in terms of the distal small airways."*
- *"The combination of Dice loss and wBCE loss can achieve a comparable performance for the
  peripheral bronchi. But meanwhile, the DSC is decreased for the other branches due to the
  dilation problem."*

That is direct evidence against the proposals' conditional experiment **as specified** — global
per-class inverse-frequency weights `w_c = 1/(N_c/N_max)` (§2.3, folder §7) — and in favour of a
*distance-based per-voxel* weight with a tunable gradient ratio. The vault's own BraTS-METS
citation (Kundu et al., arXiv:2604.24276 — **confirmed to exist**, authors and the 0.59 → 0.64
foreground Dice confirmed from the abstract) says the same thing from the other direction: global
inverse-size weighting destabilises training and must be confined locally.

Also absent from the slice entirely: **ATM'22** (Zhang et al., *Multi-site, Multi-domain Airway
Tree Modeling*, MedIA 2023, arXiv:2303.05745 — 500 CTs, 300/50/150, 22 teams), the largest public
benchmark for exactly this failure. The airway note claims to survey the airway literature and
never mentions it.

---

## 4. What's missing — extensions that would change a decision

Ranked by decision impact.

**M1. The right answer may be "topology-aware metric + reconnection, and no topology loss."**
The evidence now supports this reading: (a) no loss has moved a coronary topology metric in the
right direction in any of the three coronary measurements; (b) the only measured coronary topology
gain comes from a post-hoc reconnection stage (+1.40 Dice, HD95 5.06→1.07 mm) and from architecture
(Betti 5.6 → 1.5–1.9); (c) Skeleton Recall's one measured coronary effect is to roughly **double
β₀** while improving BCS and FFR agreement — i.e. it buys branch recovery by producing more
fragments, which then needs a reconnection stage anyway. The honest ordering is therefore:
1. **Metrics first** — β₀, Betti-matching, per-component class purity, a connectedness score. No
   GPU, and without them neither of the other two arms is interpretable. Proposals §4 lists these
   as code gaps M1–M4; they currently **block** the loss experiment's acceptance criterion.
2. **Reconnection** as a separate, separately-scored artefact.
3. **The loss last**, and framed as the arm that feeds reconnection more material.
Proposals §3.4 has Skeleton Recall at priority 3 and reconnection unscheduled. Consider inverting.

**M2. clCE (Acebes et al., MICCAI 2024) — a third coronary clDice datapoint *and* a candidate.**
Open access, code at `github.com/cesaracebes/centerline_CE`, ~8 lines. On ASOCA with nnU-Net 3D
full-res, 5-fold CV: L_Dice+clCE **84.80 DSC (+0.21) / 84.95 cl-DSC (+0.14)** — the only loss I
found measured on coronary CCTA that improves *both* overlap and the centerline metric. It is
small, and one caveat matters for this plan: **clCE still computes `soft_skel` on the prediction**,
so it inherits clDice's memory profile and would need a 14-class feasibility check before it could
be scheduled. Worth one line in §2.3 either way, because it is the third independent coronary
refutation of clDice-as-loss.

**M3. WingsNet / General Union loss is the cheapest closure of the class-imbalance gap** (W9). If
an imbalance arm is ever run, run the distance-weighted per-voxel variant with one tunable α, not
global inverse-frequency class weights — the ablation that exists says the latter dilates the large
structures.

**M4. The cheapest experiment that closes the imbalance gap costs no GPU time at all.** Run the
multiclass baseline once, then take *that same checkpoint* and report per-class Dice and detection
rate stratified by (a) prevalence across cases and (b) branch diameter, exactly as WingsNet Fig. 9
does. That distinguishes the TopCoW zero-collapse failure from an ordinary long tail, and it costs
one evaluation pass. Only if collapse appears does an arm get scheduled — and then one arm, judged
on diameter-stratified branch detection. Two runs total, not four.

**M5. Deep supervision and the topology loss are confounded in the proposed experiment.** Verified
in the Skeleton-Recall trainer source: it replaces the `DeepSupervisionWrapper` weights (1/2^i,
lowest scale zeroed, renormalised). So the Skeleton Recall arm is **not** a clean loss-only swap —
it also changes deep-supervision weighting relative to nnU-Net's default. Proposals §3.4 lists
"deep supervision" as a *separate* conditional experiment (priority 6). Either match the DS weights
in the baseline arm or state the confound; right now it is invisible unless someone reads the fork.

**M6. Boundary/Hausdorff-family and warping/homotopy losses are not considered anywhere in the
slice.** They should each get one line in "explicitly ruled out", with the reason, so the omission
is a decision rather than a hole: boundary/HD losses optimise surface distance, which on a
3–4-voxel tube is dominated by the same partial-volume jitter that makes Dice unsuitable, and they
carry no connectivity term; warping/homotopy and persistent-homology losses are per-patch CPU
topology computations that inherit precisely the scaling failure that put clDice out of memory,
and have no established multiclass formulation. The vault covers PH/Betti losses
(`Topology-aware losses…:224-229`) but not these.

**M7. Post-processing: two cheap hardenings.**
- The vault's "thresholds in mm³, never voxels" rule (`Largest-component…:97-101`) is right;
  strengthen it to **centerline length**, and require every deleted component to be logged with its
  length, max radius and distance to the nearest kept component. Deletion is the one irreversible
  operation in the pipeline and should leave an audit trail.
- **Comparability consequence the vault misses:** ImageCAS-X applies "threshold 0.5 + remove
  components < 100 voxels" to *every* method in its table, including its nnU-Net row. If this
  project compares its binary numbers to that table (proposals §1.4 makes 89.8 the new calibration
  target), it must apply the same rule for that comparison, or the comparison is not like-for-like.
  That is separate from the policy of scoring raw predictions, and both can be true.

---

## 5. Confidence, and what I could not check

**High confidence (primary source opened and read by me this session):** Skeleton Recall
(arXiv:2404.03010v2 — all five datasets, the full results table, the OOM sentence, both cost
figures); cbDice (arXiv:2407.01517v1 — the full PARSE and TopCoW tables); CorSegRec
(arXiv:2504.01597 — Tables 1, 6, 9 and the ASOCA split); ImageCAS-X (arXiv:2608.30404 — Table 2,
postprocessing, spacing, test count); BCS (arXiv:2607.28327 — Table 2 in full, splits, spacing, HU
clip, seeds, loss weights); nnU-Net `determine_postprocessing` (master source — conditional,
foreground-then-per-label, Dice-decided, "if a single class got worse as a result we won't do
this"); upstream nnU-Net loss-variant directory listing; the `MIC-DKFZ/Skeleton-Recall` repo tree
and trainer source; Hampe et al. (PMC11095121); VTG-Net (Front Med 8:750396); clCE (MICCAI 2024
open-access PDF); WingsNet (arXiv:2011.11952, pages 7–11).

**Confirmed to exist, content not fully read:** Kundu et al. arXiv:2604.24276 (title, authors and
0.59 → 0.64 confirmed from abstract; the vault's "rare-class Dice 0.44 ± 0.36" is **not** in the
abstract and I did not confirm it). ATM'22 arXiv:2303.05745 (challenge, 500 CTs, 22 teams and
architectures confirmed; I did not open the per-team loss column).

**Could not reach:**
- **Pan et al.**, Sci Rep 11:14493 — nature.com returns a 303 to an auth endpoint and PMC did not
  resolve. Existence, cohort (474 CCTA, Wanfang Hospital), architecture (3D Dense-U-Net) and the
  use of focal loss are confirmed secondhand. **The DSC 0.9691 vs 0.9603 figures and the Fig. 6
  radiologist branch ratings remain unverified** — the vault already flags the 0.97 as
  implausible, which is the right call.
- **"A Clinically-Informed Benchmark for Topology-Aware Coronary Artery Segmentation"**
  (doi:10.1007/978-3-032-17734-6_2) — still Springer login-walled. The vault's "do not cite until
  someone opens it" remains the correct handling, and it is the single highest-value fetch left in
  this slice: its reported finding (topology methods similar on primary segments, differences
  dominated by annotation inconsistency) would, if true, argue against scheduling *any* topology
  loss.
- **SN Computer Science Tversky/CCTA paper** (doi:10.1007/s42979-025-04619-5) — not attempted
  (Springer wall). WingsNet substantially substitutes for it and is open access.
- **ImageCAS-X's clDice-metric column** (the 92.3 → 91.7 pair). I confirmed the DSC, HD95 and Betti
  columns row by row; I did not read the centerline columns individually.
- **TubeLoss / vesselFM-CT** (Huang et al. 2026) — not attempted. The vault already marks it
  unverified and declines to schedule it, which is the right call.

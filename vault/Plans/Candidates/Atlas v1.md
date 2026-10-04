---
tags: [plans, candidate, nnunet, multiclass]
author: Atlas
round: 1
version: 1
updated: 2026-10-04
---

# Atlas v1 — one direct 4-class nnU-Net, trained from day 0, sized from measurements

## 1. Thesis

Train **one** nnU-Net v2 ResEnc model end-to-end on 4-class labels (LM, LAD, LCx, RCA), and start **now**,
not when the team's labels arrive: 800 of our 1000 cases already carry expert per-segment names (ImageCAS-X,
CC BY 4.0, case `c{id-1}`), and projecting those names onto our own binary masks gives 4-class labels **in the
convention the team will produce** (SegQueue confines annotator edits to our binary mask). The team's labels then
replace the projected ones case by case; the recipe never changes, only the labels get better. The recipe's key
choices are measured on this data, not assumed: train at **0.5 mm isotropic** (z is already 0.5 mm in all 1000
cases; the CT has no signal above 1 cycle/mm, so in-plane 0.35 → 0.5 mm loses nothing measurable) which lets a
**256³ = 128 mm patch** hold the whole coronary tree in ~98 % of cases and put the LM in view of ~97 % of
LAD-centred training patches; **override nnU-Net's CT window**, which on lumen labels clips calcium to the
intensity of contrast; **no mirroring**; default Dice+CE, default sampling (measured to need no class balancing).
Binary masks are not a training stage in this plan: they are the lumen extent that the labels partition.
Multi-stage schemes (binary → naming, cascade, pretrain → fine-tune) add a stage whose errors the next stage
cannot see; with hundreds of labelled cases available on day 0 they have nothing left to buy that the direct
model cannot learn. On the closest analogue (13-class Circle of Willis, TopCoW 2023) every winning team used
nnU-Net and the team listed first on both multiclass tracks trained a single-stage multiclass nnU-Net; other winners
were two-stage, so the challenge shows direct training is sufficient, not that staging always loses.

## 2. Recipe

### 2.1 Data and labels

| Set | Cases | Labels used | Role |
|---|---|---|---|
| ImageCAS-X train + val | 560 + 80 (`filelist/`) | **Proxy 4-class** (below) until the team label for that case exists, then the team label | Training (val 80 = monitoring fold) |
| ImageCAS-X test | 160 | Proxy now (interim test only); team labels when they arrive | 80 of them form the **sealed** test with 20 quality-0 cases; the other 80 are never proxy-trained and join training only once team-labelled |
| ImageCAS-X excluded (image quality 0: motion 114, step 76, other 10) | 200 | none until team-labelled | 20 of them join the sealed test once labelled; rest join training as labelled |

**Proxy label factory (CPU, no GPU, ~2 h on one cluster node).** For each of the 800 cases: every voxel of our
binary mask takes the ImageCAS-X class of the nearest ImageCAS-X voxel if one is within 2 mm (true for 86 % of our
voxels: [[Bridge - ImageCAS-X names transfer onto our binary masks, which are three times fatter]]); remaining mask
voxels inherit a name by geodesic growth inside the mask from named voxels; disconnected specks stay background.
The 14 ImageCAS-X classes then collapse to 4 in two variants, both produced:

- **trunk**: LM ← 1, LAD ← 2, LCx ← 3, RCA ← 9; side-branch-named voxels → background (reading the protocol's
  "LAD along the anterior interventricular groove; LCx along the left AV groove" literally);
- **territory**: side branches take their parent's class (D → LAD; OM, L-PDA, L-PLA → LCx; R-PDA, R-PLA → RCA;
  IM and "Other" → parent by geodesic proximity).

ImageCAS-X's own LAD/LCx continuation rule is "by course, not size" — the same as ours
([[Crucible - ImageCAS-X is real and its 800 cases are our cases c(id-1)]]). **Pre-registered convention check:**
when the first 20 team labels on ImageCAS-X cases arrive, compute per-class Dice of each variant against them;
the variant with the higher macro Dice becomes the proxy for all further training. If neither reaches 0.80 macro
Dice, the team's convention differs from both and proxies are dropped from the next wave onward (team labels
only) — see risks.

### 2.2 Preprocessing

- nnU-Net v2 (pin the version used for the planner sweep: 2.8.1), `3d_fullres` only. **Never train `3d_lowres`**
  (no cascade). [[Atlas - Every case has 0.5 mm slices and nnU-Net's own planner fixes the patch menu]]
- **Target spacing 0.5 × 0.5 × 0.5 mm** (`-overwrite_target_spacing 0.5 0.5 0.5`). z is native; only in-plane is
  resampled (0.29–0.47 → 0.5 mm). Evidence:
  [[Atlas - Resampling to 0.5 mm isotropic loses nothing measurable, 0.7-0.8 mm does]] — power above the 0.5 mm
  Nyquist is at the noise floor in 12/12 CTs; centreline contrast retained 1.000–1.005; label round-trip Dice
  ≥ 0.985 per class (mean 0.994–0.997), versus 0.83–0.94 at 0.8 mm. Median preprocessed case 275 × 358 × 358.
- **Fixed CT window**: after planning, set `foreground_intensity_properties_per_channel` in the plans file to clip
  **[−300, 1300] HU** (mean 100, sd 400). Default `CTNormalization` would clip at the 0.5/99.5 percentiles of
  labelled voxels: [65, 688] HU on a lumen protocol (38 % of the heart box flattened, calcium = bright lumen), or
  ≈ [−164, 640] HU on our masks' convention (calcium still saturated).
  [[Atlas - nnU-Net's automatic CT window on lumen labels flattens 38 percent of the heart box]]
- No heart crop: the 128 mm patch already holds the tree, and inference needs only ~8 windows per case at 0.5 mm.

### 2.3 Model

- **ResEnc U-Net** (`ResEncUNetPlanner`, `-gpu_memory_target 60`, plans `nnUNetResEncUNetPlans_60G_iso05`).
  Planner output on the real 1000-case fingerprint: **patch 256 × 256 × 256 (128 mm cube), batch 2, 7 stages**.
  Rationale for ResEnc over plain: nnU-Net Revisited (Isensee et al., MICCAI 2024, arXiv:2404.09556, Table 2)
  — ResEnc L/XL over the original nnU-Net +2.1/+2.6 Dice on KiTS and +0.8/+1.0 on AMOS, the two large
  fine-structure CT datasets in the benchmark; it is the only architecture change their benchmark supports.
- Why the VRAM target is set explicitly: the shipped presets give patches of 48–80 mm through-plane at native
  spacing and do not contain one coronary tree (ResEnc L native: whole left tree in one patch in 7 % of cases; LM visible to 61 % of LAD-centred patches).
  [[Atlas - A 128 mm patch at 0.5 mm holds the whole tree and the LM in almost every training patch]]
- Deep supervision on (default). Output 5 channels (bg + 4).

### 2.4 Loss, sampling, augmentation

- **Loss: Dice + CE (nnU-Net default).** Skeleton Recall (Kirchhoff et al., ECCV 2024, arXiv:2404.03010; +1.2 Dice
  on 13-class TopCoW with nnU-Net) is ablation A4, not default: on ImageCAS it recovered branches but roughly doubled
  connected components ([[Delta - Topology losses on coronaries are verified, and they recover branches but do not connect them]]).
- **Sampling: nnU-Net default** (33 % foreground-forced patches, class picked uniformly among present classes).
  With a 128 mm patch a random patch contains each of the four classes in ≥ 0.985 of positions and the whole
  tree fits in 98 % of cases, so the class-balanced sampler proposed in [[Training plan]] §5 has nothing to fix.
- **Augmentation:** nnU-Net defaults (rotation ±30°, scaling 0.7–1.4, noise, blur, brightness, contrast, gamma,
  low-res simulation) **with mirroring off on every axis** (`nnUNetTrainerNoMirroring`; also disables mirror TTA).
  Mirroring swaps left and right trees; TopCoW's organisers make the same rule for multiclass vessels
  (Yang et al., arXiv:2312.17670, §5.1: "important to turn off the mirror augmentation in nnUNet for multiclass
  segmentation"). Rotation is ablation A3 (ImageCAS measured rotation+flip −2.7 %, never rotation alone).

### 2.5 Schedule on Trillium (1 × H100 80 GB, 24 h, chain resume)

- nnU-Net trains a fixed 1000 epochs × 250 iterations; there is **no early stopping** in v2 (checked in source;
  the vault's schedule note says otherwise). Chain links resume with `nnUNetv2_train … --c`; checkpoint every 50
  epochs, so a link loses ≤ 50 epochs if killed — set the walltime-aware stop at 23 h.
- **Estimated 40–60 H100-h per 1000-epoch run (2–3 links).** Basis: nnU-Net Revisited measured 35 / 66 A100-40GB
  GPU-hours for ResEnc L / XL (22.7 / 36.6 GB); scaling to a ~60 GB config ≈ 110 A100-h; H100 SXM assumed ≈ 2×
  A100 PCIe. This is an extrapolation; run **R0** measures it.

| Run | What | Epochs | Est. H100-h |
|---|---|---|---|
| R0 | `nnUNetTrainerBenchmark_5epochs` + 1 real epoch: peak VRAM, s/epoch, data-loader saturation (≥ 8 CPU workers) | 5 | 1 |
| R1 | **Baseline**: proxy labels (variant: territory until the convention check decides), train 560 / monitor on val 80 | 1000 | ~50 |
| A0 | Baseline at 250 epochs (shared control arm for ablations) | 250 | ~13 |
| A1 | Spacing: native (0.5 × 0.35 × 0.35) with ResEnc 60 GB → patch 160 × 320 × 320 (80 × 112 × 112 mm) | 250 | ~15 |
| A2 | Window: nnU-Net default `CTNormalization` | 250 | ~13 |
| A3 | Rotation off | 250 | ~13 |
| A4 | + Skeleton Recall (MIC-DKFZ/Skeleton-Recall trainer), weight as published | 250 | ~14 |
| A5 (optional) | Init from a binary model trained 250 epochs on all 1000 binary masks (13 h) vs A0 | 250 | ~26 |

Ablation rule: adopt a variant only if the paired per-case difference in the decisive metric on the val fold has a
bootstrap 95 % CI excluding 0 in its favour; otherwise keep the simpler baseline. A0–A4 can run as parallel jobs.

### 2.6 Post-processing

None of nnU-Net's largest-component logic. Per class, remove connected components < 100 voxels at 0.5 mm
(ImageCAS-X's rule; on our masks it deletes no component ≥ 1000 voxels:
[[Delta - The binary masks are two clean trees, and a tight tree ROI is only 2-3x smaller than the volume]]).
Never delete a large component; never force left and right apart. A fragment-relabel step (reassign a small
component of class k that touches only class j) is added only if the val fold shows branch-swap fragments.

### 2.7 How labels arriving over time are used

| Team labels in hand | Action | Cost |
|---|---|---|
| 0 | Proxy factory; R0; R1; ablations. R1 predictions (4-class) offered to the labelling lead as optional seeds | ~120 H100-h |
| first 20 (on ImageCAS-X cases) | Convention check (§2.1) → fix proxy variant; measure team-vs-proxy agreement | 2 analyst-hours |
| 100 sealed test (asked for **first**: 80 ImageCAS-X test + 20 quality-0) | Becomes the decisive test set; interim proxy test retired | — |
| +150, +300, +600 training labels | **Fine-tune** latest model 250 epochs on {team ∪ proxy} (team overrides proxy per case; quality-0 cases enter only via team labels) | 3 × ~13 h |
| ≥ 600 | One paired run: team-only vs team + proxy; keep the better for the final | ~26 h |
| all 900 non-test | **Final**: from scratch, 1000 epochs, 5-fold CV ensemble (or `all` single model if the CV ensemble gain is within CI) | 50–250 h |

## 3. Evaluation

- **Sealed test**: 100 team-labelled cases (80 ImageCAS-X test + 20 image-quality-0), never used for training or
  model selection; ImageCAS-X's descriptors stratify it (dominance 729 R / 41 L / 30 co; disease 48.5 %).
  Until it exists, the interim test is the 160 ImageCAS-X test cases with proxy labels.
- **Decisive metric: macro-mean over LM, LAD, LCx, RCA of per-class clDice** (centreline Dice of each class,
  skeleton of reference and prediction computed per class at 0.5 mm), averaged over cases. Why clDice and not
  Dice: our labels are ~3× thicker than the expert lumen, so voxel Dice mostly scores boundary convention; clDice
  scores length found and named correctly, which is what the 4-class task is. Absent class (e.g. RCA in a
  left-dominant case) absent in both → dropped from that case's mean; present in only one → 0.
- Reported with it, per class: Dice, HD95, **branch-swap rate** (fraction of reference class-k centreline predicted
  as another named class), detection (class found with ≥ 5 mm centreline), β₀ (components) vs the reference's own
  count, LM length error. Stratified by dominance, disease, image quality.
- Paired comparisons: per-case differences, bootstrap 95 % CI, Wilcoxon signed-rank.
- **Ceiling**: 30 test cases double-labelled by two team annotators → per-class inter-rater clDice and Dice.
  ImageCAS-X's per-class inter-observer Dice on the expert lumen (LM 91.9, LAD 92.3, LCx 84.8, RCA 95.3;
  arXiv:2608.30404, Table 1) is context, not our ceiling (different lumen convention).
- **Acceptance**: model within 5 clDice points of team inter-rater agreement on every class, branch-swap rate < 5 %.

## 4. Evidence

| Claim | Evidence |
|---|---|
| z = 0.5 mm in all 1000; planner's patch/batch menu for every preset and VRAM target | [[Atlas - Every case has 0.5 mm slices and nnU-Net's own planner fixes the patch menu]] |
| 0.5 mm iso is lossless for image and labels; 0.7–0.8 mm is not | [[Atlas - Resampling to 0.5 mm isotropic loses nothing measurable, 0.7-0.8 mm does]] |
| A 128 mm patch holds the tree (98 %) and puts LM in view of 97 % of LAD-centred patches; presets do not (7 % / 61 %) | [[Atlas - A 128 mm patch at 0.5 mm holds the whole tree and the LM in almost every training patch]] |
| Default CT window erases fat and saturates calcium on lumen labels | [[Atlas - nnU-Net's automatic CT window on lumen labels flattens 38 percent of the heart box]] |
| ImageCAS-X exists, CC BY 4.0, ids map to `c{id-1}`, LAD/LCx rule by course | [[Crucible - ImageCAS-X is real and its 800 cases are our cases c(id-1)]] |
| Team labels will be partitions of our ~3× fatter binary masks; ICX names project onto 86 % of our voxels within 2 mm | `docs/SEGQUEUE.md`; [[Bridge - ImageCAS-X names transfer onto our binary masks, which are three times fatter]] |
| Direct multiclass nnU-Net is sufficient to win the closest multiclass-vessel benchmark; mirroring must be off | TopCoW, Yang et al. arXiv:2312.17670, §5.1 and App. A ("All winning teams used nnUNet"; WilliWillsWissen, listed first on both multiclass tracks: patch-based 3D nnU-Net + clDice/SkelRecall, 5-fold ensembles; NexToU and NIC-VICOROB used two stages) |
| Skeleton Recall: +1.2 Dice multi-class TopCoW (85.36 → 86.59), clDice OOM there | Kirchhoff et al. arXiv:2404.03010, Table 2 |
| ResEnc is the architecture upgrade worth paying for; GPU-hours by preset | Isensee et al. arXiv:2404.09556, Table 2 (KiTS 86.04 → 88.17 L / 88.67 XL; 9 / 35 / 66 A100-h) |
| ImageCAS-X trained nnU-Net at 0.5 mm iso, 89.8 binary Dice vs 92.8 inter-observer | arXiv:2608.30404, Table 2, App. E |
| Anatomical CT structures plateau at tens to ~100 training cases; tumours need hundreds | Gottlich et al., J Digit Imaging 2023, doi:10.1007/s10278-023-00804-1 (kidney CT plateau at 54 cases, KiTS21 3D nnU-Net at 440) |

## 5. Risks and early detection

| Risk | Early signal | Response |
|---|---|---|
| Team convention matches neither proxy variant | Convention check on first 20 team labels (< 0.80 macro Dice) | Drop proxies from next wave; team labels only; R1 weights kept as init |
| Proxy names wrong near bifurcations (projection) | Team-vs-proxy branch-swap rate on the first 20 | Use Bridge's tree labeller as a second proxy and take agreement-only voxels, others `ignore` |
| H100 time per epoch > estimate | R0 (5-epoch benchmark) | Drop to ResEnc 40 GB at 0.5 mm (192 × 256 × 256) — still holds left trees; recheck A1 |
| 0.5 mm resampling hurts thin distal LAD/LCx | A1 paired run, per-class clDice and detection | Switch to native spacing (A1 arm) |
| Class swaps along long vessels | Branch-swap rate on val fold every 50 epochs | Fragment relabel post-processing; larger patch |
| Calcium / stents labelled as lumen | Stratified test by disease; A2 | Window already fixed; add calcium-aware augmentation later |
| Quality-0 cases (20 % of cohort, motion/step) unseen until team labels | Sealed test includes 20; per-stratum metrics | Prioritise their labelling in later waves |
| Over-fitting ablations to the val fold | Decisions only on val; test touched once per milestone | — |

## 6. Comparison

**Against the current plan of record ([[Training plan]]; no master yet).** Kept: one-stage nnU-Net 3d_fullres, no
cascade, no largest-component post-processing, no mirroring, ResEnc evaluated. Changed, each on measured evidence:
(1) the multiclass model starts on day 0 on 640 proxy-labelled cases instead of a binary model first — the binary
model would learn the masks' convention well but its only downstream use (seeding annotators) is better served by
4-class predictions; (2) **0.5 mm isotropic, not native 0.35 mm**: lossless here, and it turns the planner's
19.7 Mvox native patch (96 × 112 × 112 mm, whole tree in 60 % of cases) into a 128 mm cube (whole tree 98 %) at
lower VRAM; (3) ResEnc from the start, VRAM target set explicitly; (4) fixed CT window — a default-pipeline defect
the plan does not mention; (5) the class-balanced sampler is unnecessary at this patch size; (6) schedule: there
is no early stopping in nnU-Net v2 and the 1000-epoch run is ~2–3 links, not "two blocks until early stopping";
(7) a decisive metric is named.

**Against a binary-then-naming plan (Bridge's thesis).** The binary stage's strength — learning our masks'
convention from all 1000 cases — is matched by training on labels that *are* partitions of those masks. The naming
stage's claimed advantage, seeing the whole tree, is available to a 128 mm patch: 97 % of LAD-centred training
patches contain the LM, and at inference every 256-slice window spans ≥ 92 % of the volume's height. Naming rules fitted on
tens of cases and applied after a binary model compound two error sources the second stage cannot correct (a vessel
the binary model breaks becomes a separately-named fragment). The direct model also gives per-voxel class
probabilities for review. Bridge's rule-labeller is still useful in this plan — as a second proxy and a QC
cross-check.

**Against a pseudo-label pretrain → fine-tune plan (Crucible's thesis).** Same data source; this plan has no
separate pretraining stage, so there is nothing to tune about when to switch and how to weight the two label
sources beyond the one pre-registered team-only-vs-mixed comparison at 600 labels.

**Against a topology-first plan (Delta's thesis).** This plan adopts Delta's measured post-processing rules and
treats topology losses as an ablation, because the coronary evidence (Delta's own note) does not show they reduce
fragmentation. Its decisive metric (per-class clDice) and branch-swap rate already score topology-relevant failure.

## 7. Cost

- **GPU:** R0 1 h; R1 ~50 h; ablations A0–A4 ~68 h (+26 h if A5); wave fine-tunes ~39 h; team-vs-mixed ~26 h;
  final 50 h (single) – 250 h (5-fold); inference on 1000 cases ~3 h. **Total ≈ 240–460 H100-h** (≈ 10–19 chained
  24 h jobs); ~120 H100-h are spent before any team label exists.
- **CPU:** proxy factory ~2 node-hours; preprocessed data at 0.5 mm ≈ 180 GB vs ≈ 360 GB at native (half the voxels).
- **Human:** convention check 2 analyst-hours; 30 cases double-labelled for the ceiling (~30 extra annotation
  sessions); labelling order request (sealed test first); optional review of R1 4-class seeds.

## 8. Changes since previous version

First version.

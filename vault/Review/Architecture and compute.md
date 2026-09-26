---
tags: [review, verification, decision-record]
status: complete
updated: 2026-09-26
slice: Research/Architectures and training, plan §1-§3, proposals §1.2, §1.3, §3.1, §3.4
---

# Review 03 — Architecture and compute: the plan's central technical bet

Reviewer 3 of 10. Slice: `vault/Research/Architectures and training/` (9 notes), cross-referenced
against `vault/Training method/Training plan.md` §1–§3 and `vault/Proposed changes to the training
plan.md` §1.2, §1.3, §3.1, §3.4.

nnU-Net is **not installed and not vendored** in this repo (`python -c "import nnunetv2"` →
ModuleNotFoundError; `pip show nnunetv2` → not found; no vendored planner/dataloader files). Every
source claim below was checked against files fetched from `MIC-DKFZ/nnUNet` at tag **v2.5.1** (and
v2.6.2 / master where stated), plus `MIC-DKFZ/dynamic-network-architectures` and
`MIC-DKFZ/batchgenerators`. Working copies and my re-derivation scripts are in
`.../scratchpad/nn/` (`sim.py`, `flops.py`, `flops2.py`).

---

## 1. Verdict in five lines

1. **The 70 GB number is wrong, and wrong in a way that matters.** nnU-Net's planner caps the patch
   at the volume of a 256³ patch and only ever shrinks it; above ~52–64 GB every extra GB is spent
   on **batch size**, not patch size. At `--gpu-mem 70` on an isotropic cohort the planner returns
   batch **3**, not 2 — the plan's own gate (c) fails — and batch 3 at 256³ costs **77.3 GB** by the
   planner's own model on an 80 GB card. `--gpu-mem 52–64` is the correct ask.
2. **Patch fraction cannot be bought with VRAM.** It is pinned at ≈16.8M voxels / median volume =
   **23–31 %** depending on the median z-extent and the target spacing, for *any* budget above
   ~52 GB. Against the real 25 % cascade trigger (proposals §1.2 is correct) the margin is
   sometimes negative, and the plan's implicit remedy ("raise the budget") does not exist.
3. **Proposals §1.2, §3.4 and the substance of §1.3 all check out** against real source and against
   arXiv:2404.09556v2 Table 1 (I reproduced every cited number). §1.3's *citation* is fabricated in
   file, class and API name even though its conclusion is right.
4. **The 24 h schedule note is built on a mechanism that does not exist**: nnU-Net v2 has **no early
   stopping**, no `(1-ep/1000)²` LR, and does not validate every 50 iterations. Cost per fold is
   *fixed* at 250 000 iterations. One fold is **33–72 h**, so `chain_max: 3` (~71 h) is at the very
   edge at 70 GB and comfortable only at 52 GB.
5. **The programme is affordable in GPU-hours (~800–1100, ≈0.1 GPU-year) but the plan never
   considers the one lever that removes the walltime problem entirely**: Trillium GPU nodes are
   4 × H100 and `nnUNetv2_train -num_gpus 4` appears nowhere in 84 notes. That, plus bf16 and
   gradient checkpointing, are the unexamined options.

---

## 2. Errors found, ranked by what they change

### E1. The patch size is hard-capped by construction; `--gpu-mem 70` buys batch size, not patch size — and probably OOMs

**What the vault says.** Plan §2 L50-53: *"The default 8 GB budget sizes patches around 128³ (~2 M
voxels); ~70 GB buys roughly 256³–288×288×224 (~17–20 M voxels) at batch 2, which is ~27–30 % of a
full volume."* Plan L73-77 makes gates (a) ≥12.5 % fraction, (b) native spacing, (c) batch size 2.
Patch-size note L105-113 calls it "scaling arithmetic". The ResEnc note L114-119 advises *"the extra
VRAM should be spent on patch size at ResEnc-L-like depth rather than on more channels."*

**What is actually true.** `nnunetv2/experiment_planning/experiment_planners/default_experiment_planner.py`
@ **v2.5.1**, inside `get_plans_for_configuration`, L259-272:

```python
# we then upscale it so that it initially is certainly larger than what we need (rescale to have the same
# volume as a patch of size 256 ** 3)
# this may need to be adapted when using absurdly large GPU memory targets. ...
if len(spacing) == 3:
    initial_patch_size = [round(i) for i in tmp * (256 ** 3 / np.prod(tmp)) ** (1 / 3)]
...
initial_patch_size = np.array([min(i, j) for i, j in zip(initial_patch_size, median_shape[:len(spacing)])])
```

and the sizing loop at L321 (`while (estimate / ref_bs * 2) > reference:`) only ever **subtracts**
from `patch_size`. There is no growth path. The leftover budget goes to batch size at L377:
`batch_size = round((reference / estimate) * ref_bs)`.

So the patch is bounded above by a 256³-*volume* initial guess (16 777 216 voxels), modulo the
divisibility padding in `get_pool_and_conv_props`, which can push it ~20 % higher on anisotropic
aspect ratios. The relevant constants are L54-69: `UNet_reference_val_3d = 560000000`,
`UNet_reference_val_corresp_GB = 8`, `UNet_reference_val_corresp_bs_3d = 2`,
`UNet_min_batch_size = 2`, `max_dataset_covered = 0.05`.

**My arithmetic, and how it was derived.** I re-implemented `compute_conv_feature_map_size` for
`PlainConvUNet` from `dynamic_network_architectures` (`architectures/unet.py` L96-104 =
encoder + decoder; `building_blocks/plain_conv_encoder.py` L93-103;
`building_blocks/unet_decoder.py` L127-154; `building_blocks/simple_conv_blocks.py` L73-78 and
L139-147) and drove it with the **real** `network_topology.get_pool_and_conv_props`.
Note `deep_supervision` defaults to `False` in the estimate (`static_estimate_VRAM_usage` calls
`get_network_from_plans(..., allow_init=False)` with `deep_supervision=None`, and
`PlainConvUNet.__init__` defaults it to False — `unet.py` L40), so only the final seg head counts.

Validation: my function returns **450 699 264** for the canonical 128³ / 6-stage / 2-class config.
The planner's own source comment on the same line as the constant reads
`self.UNet_reference_val_3d = 560000000  # 455600128  550000000` — my value is within **1.1 %** of
its historical measured reference. I treat the implementation as verified.

`reference(G) = 560e6 · G/8`. Because `ref_bs = 2`, the shrink test reduces to `estimate > reference`.
Solving the model for the memory a config needs: **G_required = estimate · batch / 1.4e8**.

| patch | estimate (feature-map elements) | G_req @bs 1 | @bs 2 | @bs 3 |
|---|---|---|---|---|
| 256³, 7 stages, 2 classes | 3 606 126 592 | 25.8 GB | **51.5 GB** | **77.3 GB** |

Sweeping `--gpu-mem` for an isotropic 0.35 mm cohort, median transposed shape (240, 512, 512):

| `--gpu-mem` | patch | voxels | batch | patch fraction |
|---|---|---|---|---|
| 8 | 80×192×160 | 2.46 M | 2 | 3.9 % |
| 24 | 112×256×256 | 7.34 M | 2 | 11.7 % |
| 40 | 192×256×256 | 12.58 M | 2 | 20.0 % |
| 51 | 224×256×256 | 14.68 M | 2 | 23.3 % |
| **52–64** | **256×256×256** | **16.78 M** | **2** | **26.7 %** |
| 65–90 | 256×256×256 | 16.78 M | **3** | 26.7 % |

Three consequences the plan does not know about:

- **Gate (c) fails at 70 GB.** `round((4.9e9/3.606e9)·2) = round(2.718) = 3`. The plan's third
  pre-submission gate is "batch size 2"; the planner will hand back 3. Nothing in `src/segtrain`
  enforces the gate — `plans.py:describe_plans()` only *prints* `batch_size` (L235), and the only
  hard check is `spacing_warnings()` (L253-283).
- **OOM risk is real and is caused by `round()`.** The planner's own model says batch 3 at 256³
  needs 77.3 GB; asking for 70 overshoots the request by 10 % and lands at 97 % of the card — before
  the things the estimate ignores (deep-supervision seg maps at 5 resolutions, the fp32 one-hot
  target and softmax in `DC_and_CE_loss`, cuDNN workspace, allocator fragmentation). At 15 classes
  the estimate rises to 3.824e9 → 82 GB modelled at batch 3. **`--gpu-mem 70` is not safe; it is the
  worst value in the range.** `--gpu-mem 52–64` gives the same patch at batch 2 for a modelled
  51.5 GB, i.e. 28 GB of genuine headroom.
- **The 17–20 M / 27–30 % / batch-2 triple is only self-consistent in the anisotropic regime.**
  Isotropic 0.35 mm → 16.78 M, 26.7 %, batch 3. With a coarser z (0.5, 0.35, 0.35) the aspect-ratio
  rule gives `initial_patch_size = [202, 288, 288]`, padding pushes it up, and the loop lands at
  **192×320×320 = 19.66 M voxels, batch 2, fraction 31.25 %** at 64–70 GB. Both of the plan's quoted
  shapes exist — in *different* spacing regimes, with different batch sizes — and nobody has
  measured which regime ImageCAS is in. The plan reads as if one arithmetic covers both.

**Fix.** (i) Change `--gpu-mem 70` to `--gpu-mem 56` (mid-window, robust to the median shape) in
plan §2 L50 and in `configs/tasks/Dataset710_CoronaryLumen.yaml` / `Dataset711_CoronaryLumenX.yaml`.
(ii) Replace the sentence "~70 GB buys roughly …" with the mechanism: *the planner caps the patch at
a 256³-volume initial guess and spends surplus VRAM on batch size; the budget only needs to be large
enough to stop the shrink loop firing, which is ~52 GB on this cohort.* (iii) Make gates (a) and (c)
machine-checked in `describe_plans`, not eyeballed. (iv) Delete the ResEnc note's advice to buy patch
size with the extra VRAM — `residual_encoder_unet_planners.py` contains the byte-identical
`256 ** 3` initial-patch block, so that is not purchasable with the stock planner.

### E2. The schedule note's convergence mechanism does not exist in nnU-Net v2

**What the vault says.** `Training schedule length and early stopping…md` L14-18, presented as
*"Verified in nnU-Net source (nnUNetv2, master branch, 2026)"*: **early stopping if validation loss
does not improve by ≥5×10⁻³ within the last 60 epochs, but not before LR < 10⁻⁶**; LR
`0.01 × (1 − epoch/1000)²`; **validation every 50 training iterations**. L58 adds that the trainer
saves "latest" *"at every validation (every 50 iterations)"*. The note's operating advice (L83-85)
is "continue into the second block until early-stopping fires".

**What is actually true**, `nnunetv2/training/nnUNetTrainer/nnUNetTrainer.py` @v2.5.1:

- L147-152: `initial_lr = 1e-2`, `weight_decay = 3e-5`, `oversample_foreground_percent = 0.33`,
  `num_iterations_per_epoch = 250`, `num_val_iterations_per_epoch = 50`, `num_epochs = 1000`.
  → 250 000 iterations is right; "validation every 50 iterations" is a misreading of *50 validation
  iterations per epoch*.
- L1364: `for epoch in range(self.current_epoch, self.num_epochs):` — a fixed loop. Grepping the
  whole trainer for `early`, `patience` returns **nothing**. There is **no early stopping in
  nnU-Net v2**; the ≥5×10⁻³/60-epoch rule is nnU-Net **v1** behaviour.
- `nnunetv2/training/lr_scheduler/polylr.py`: `PolyLRScheduler(..., exponent: float = 0.9)`,
  `new_lr = initial_lr * (1 - step/max_steps) ** exponent`, instantiated at trainer L508 with no
  override. Exponent **0.9**, not 2.
- L188: `self.save_every = 50` and L1140: checkpoint written every 50 **epochs**, not every 50
  iterations.

**Why it matters.** The note's whole cost model is "train until the plateau", so it treats the run
length as data-dependent and argues for "two blocks, maybe three". The truth is that the cost is
**fixed and known in advance**: 1000 epochs × 250 iterations, always. You cannot save walltime by
converging; you can only cut `num_epochs` deliberately. Every downstream budget in the vault
inherits this error.

**Fix.** Rewrite L14-20 of that note from source. Replace the "continue until early stopping fires"
advice with an explicit decision: either budget the full 250 k iterations per arm, or set
`-tr nnUNetTrainer_Xepochs` / a reduced `epochs:` for ablation arms and say so. The repo is already
ahead of the vault here — `configs/dataset.yaml` L150 sets `save_every: 25` and L138 a
`pause_margin_seconds: 1800` clean-pause budget — but the vault still documents the v1 mechanism.

### E3. §1.3's conclusion is right; its citation is invented

**What the vault says.** Proposals §1.3 L122: *"Verified in `DataLoader3D.get_bbox`."* The source note
(`Class-balanced and vessel-anchored patch sampling…md` L26-33) is more specific: *"nnU-Net's v2
`DataLoader3D.get_bbox` (`nnunetv2/training/dataloading/data_loader.py`, verified against current
source) calls `fg_locations.eligible_classes(identifier)` …"*

**What is actually true.** There is no `data_loader.py` and no `DataLoader3D` in
`nnunetv2/training/dataloading/` at v2.5.1 (directory listing: `base_data_loader.py`,
`data_loader_2d.py`, `data_loader_3d.py`, `nnunet_dataset.py`, `utils.py`). `get_bbox` lives on
`nnUNetDataLoaderBase` in **`base_data_loader.py` L65**. There is no
`fg_locations.eligible_classes()` API anywhere; the real line is **L103**:

```python
eligible_classes_or_regions = [i for i in class_locations.keys() if len(class_locations[i]) > 0]
```

and the choice at **L121**:

```python
selected_class = eligible_classes_or_regions[np.random.choice(len(eligible_classes_or_regions))] if \
    (overwrite_class is None or (overwrite_class not in eligible_classes_or_regions)) else overwrite_class
```

**So the conclusion stands** — the per-case class choice *is* uniform over classes present in that
case, and within the class, `selected_voxel = voxels_of_that_class[np.random.choice(...)]` (L129) is
uniform over stored locations, which `DefaultPreprocessor._sample_foreground_locations`
(`default_preprocessor.py` L152-177) has already subsampled to ≤10 000 per class with a 1 %-coverage
floor, so within-case volume differences are already normalised too. Starvation is therefore at
case-selection frequency, exactly as §1.3 says.

**But §5 of the plan is wrong in a second way nobody caught.** Plan L123 says nnU-Net *"picks one
random foreground class for a third of patches"*. `_oversample_last_XX_percent`
(`base_data_loader.py` L46-50) is `not sample_idx < round(batch_size * (1 - 0.333))`. At **batch 2**
that is `round(1.334) = 1`, so sample 0 is random and sample 1 is forced-foreground — **50 %, not
33 %**. nnU-Net's own source comments on this at trainer L367-369. At batch 3 it is 33 %. So the
oversampling rate silently depends on the batch size the planner happened to return — another reason
E1's batch-2-vs-3 ambiguity is not cosmetic.

**Fix, and how to implement it.** The dataloader already has the hook. `nnUNetDataLoaderBase.__init__`
L22 forwards `sampling_probabilities` to batchgenerators' `DataLoader`, whose docstring (L153-156)
says *"only applies if infinite=True. If sampling_probabilities is not None, the probabilities will be
used by np.random.choice to sample the indexes for each batch"* — and nnU-Net passes `infinite=True`.
`nnUNetTrainer.get_dataloaders` passes `sampling_probabilities=None` at **L660, L666, L673, L679**.
The fix is therefore ~5 lines in `nnUNetTrainer_segtrain`: override `get_dataloaders`, compute a
per-case weight from `dataset_fingerprint`/`class_locations` presence, and pass it in.

Concretely, and this is the part the vault has not thought through: **pure inverse-frequency case
weighting does wreck everything else.** If L-PDA is present in 30/1000 cases and you weight those
cases up by 1000/30 ≈ 33×, those 30 cases dominate the epoch, and because the per-case class choice
is uniform over *all* classes present in them, you also 33× the LAD/RCA/LM voxels in those same 30
patients — you have not rebalanced classes, you have rebalanced *patients*, and you have introduced a
30-case overfit. Two safer forms:
- **Capped square-root weighting on case selection**: `w_case ∝ max over classes present of
  (1/freq_c)^0.5`, normalised, clipped to ≤5× uniform. Keeps the tail visible without collapsing the
  epoch onto it.
- **Per-case slot allocation, which is the cleaner lever and needs no case reweighting at all**:
  `get_bbox` already accepts `overwrite_class` (L66, L98-100, L122). Override
  `nnUNetDataLoader3D.generate_train_batch` to pass `overwrite_class = the rarest class present in
  this case` for the forced-foreground slot. That changes *which* class the patch centres on when a
  rare-class case is drawn, leaves case frequency alone, and cannot distort the common classes'
  exposure because the common classes are present in almost every case anyway.

The second is what "class-balanced, vessel-anchored" should mean, and it is a 15-line override. Note
`max_dataset_covered = 0.05` (planner L66) is irrelevant here — it caps batch size, not sampling.

### E4. The disk and inference costs of dropping the heart crop are mis-stated in both directions

**What the vault says.** Plan §2 L65-68: *"preprocessed data ~3× larger on disk (order 250 GB +
transient doubling from the `.npz`→`.npy` unpack — measure, and provision `$SCRATCH` accordingly),
and ~3–4× more sliding windows at inference. Neither affects training accuracy."*

**Disk, computed.** `default_preprocessor.py` @v2.5.1: data → `np.float32` (L44), seg → `np.int8`
(L112) or int16 if >127 labels, written with `np.savez_compressed` (L148). CT in HU has air at −1000,
so `create_nonzero_mask` cropping is a no-op on full-FOV CCTA; at native median spacing, resampling
barely changes shape. For median 512×512×240 = 62.9 M voxels:

- `.npz`: ~0.6 × 251.7 MB (float32 deflates poorly) + ~0.02 × 62.9 MB ≈ **150 MB/case → ~150 GB**
- unpacked `.npy` + `_seg.npy`: 251.7 + 62.9 = **314.6 MB/case → ~315 GB**
- both resident during and after training: **~465 GB**, plus ~65 GB of `nnUNet_raw` NIfTI.

So the plan's order of magnitude is defensible but the word **"transient" is backwards**: the `.npy`
is the *resident* training format and persists for the whole run and every subsequent fold; the
`.npz` is the deletable one.

**And it is version-dependent, which the vault never says.** The repo pins `nnunetv2>=2.5,<3`.
At **v2.6.2** the preprocessor switched to **blosc2** (`default_preprocessor.py` L154-166,
`nnUNetDatasetBlosc2.save_case`) — chunked compressed arrays read directly, with **no unpack step**,
so the ~315 GB `.npy` tier disappears entirely; but seg is forced to `np.int16` (L155) rather than
int8. Net: ~150–170 GB instead of ~465 GB. **Pin `nnunetv2>=2.6` and the disk problem is a third of
what the plan budgets.**

**$SCRATCH fit.** I could not reach a Trillium quota table (`docs.scinet.utoronto.ca/index.php/Trillium`
→ 404; `docs.alliancecan.ca/wiki/Trillium` → BotStopper 403; the Trillium Quickstart page does not
carry one). **Unreachable, not confirmed.** What I can say: Alliance/SciNet scratch quotas are in the
tens of TB (Niagara's was 25 TB / 1 M files), and 465 GB / ~4000 files is far inside any plausible
figure, so the accepted cost **is** affordable. The real hazard is not the quota: SciNet
*"automatically deletes files in /scratch that have not been accessed or modified for more than
2 months"*. The plan's sequencing puts months between preprocessing the binary task and the
multiclass work; the ~465 GB will be silently purged in between. Nothing in the vault or in
`configs/dataset.yaml` mentions this.

**Inference, computed.** nnU-Net's `nnUNetPredictor.__init__` (`predict_from_raw_data.py` L38-56)
defaults `tile_step_size = 0.5` and `use_mirroring = True` (so proposals §3.1's third gate is
confirmed at 50 % before you even look). With patch 256³ over a 512×512×240 volume: 3 steps in x,
3 in y, **1** in z (the patch exceeds the z extent) = **9 windows**, × 8 mirror passes = 72 forward
passes × 8.53 TFLOP = **614 TFLOP/case**, i.e. a few seconds per case and well under an hour for a
250-case test set. For comparison, a 128³ patch needs **147** windows. **The big patch makes
inference roughly 2× cheaper, not more expensive.** The "3–4× more sliding windows" is only true
against a hypothetical heart crop, and in absolute terms it is negligible either way. The plan
accepts a cost that is not the binding one and says nothing about the one that is (the 8-fold
mirroring TTA, which §4 rules out for multiclass on correctness grounds and which therefore *also*
divides the inference cost by 8 for the multiclass model — an interaction the plan misses).

**Preprocessing fit in walltime.** `plans.py:preprocess()` L200 caps at
`max(1, min(8, cfg.n_workers() // 2))` processes, and `extract_fingerprint` L72 at `min(8, ...)`.
Eight processes on a 96-core Trillium node for 1000 order-3 spline resamplings of 62.9 M-voxel
volumes plus 1000 × 250 MB deflate writes is roughly 2–4 min/case ÷ 8 ≈ **4–8 h**, against
`prepare_walltime: "12:00:00"`. It fits, but with no margin — and **the prepare job is not chained**
(`submit_chain` only wraps the training script; `prepare_walltime` is a single job), so an overrun
means starting over. The 8-process cap is the thing to raise, not the walltime.

### E5. The 25 % trigger correction is right, and the "what if it comes back at 22 %" question has no answer in the plan

**Verified.** `lowres_creation_threshold = 0.25` at `default_experiment_planner.py` **L71**, tag
**v2.5.1**; the v2.6.2 file is **md5-identical** (`6c50fd98…`), so the same line and number; on
**master** the same constant is at L71. The gate is applied at **L459**
(`while num_voxels_in_patch / median_num_voxels < self.lowres_creation_threshold:`) and the second,
independent trigger the cascade note flags is real: **L471-475** drops the lowres config if
`np.prod(new_median_shape_transposed) / median_num_voxels < 2`. Proposals §1.2 is **correct**, down
to the tag list. `configs/tasks/Dataset710_CoronaryLumen.yaml` already carries the corrected 25 %.

**Now the consequence, which is worse than the vault says.** My sweep gives, at any budget ≥52 GB
and isotropic 0.35 mm spacing:

| median z | median volume | patch fraction |
|---|---|---|
| 206 | 54.0 M | 27.2 % (patch 224×256×256 at 52 GB) |
| 230 | 60.3 M | 27.8 % |
| 240 | 62.9 M | 26.7 % |
| 256 | 67.1 M | **25.0 %** — exactly on the trigger |
| 275 | 72.1 M | **23.3 %** — below |

ImageCAS is 512×512×**206–275**. The patch fraction therefore straddles the threshold as a function
of a number nobody in the vault has measured, and — this is the single point of failure — **it cannot
be fixed by raising `--gpu-mem`, because the patch is capped.** The plan's gate (a) is written as a
pass/fail with an implied remedy ("spend more VRAM"), and that remedy does not exist. The cascade
note (L86-93) gets the right answer for the wrong reason: it says a lowres entry "is not a failure"
because `configuration: 3d_fullres` decides what trains, which is true (`plans.py:preprocess()`
L201-207 preprocesses only `task.configuration`, and the repo already passes a single-element
`configurations=[...]`). But it frames the 25 % number as "an indicator that the patch is large
enough", and if the indicator reads 22 % there is nothing to do about it. The honest statements are:
(a) patch fraction on this cohort is ~23–31 %, structurally, and is not a tunable; (b) the only
levers that move it are coarsening the target spacing (refused by §1) or cropping (refused by §2);
(c) so gate (a) should be demoted from a gate to a recorded fact, and the plan should say in advance
that a fraction of 22 % is an accepted outcome, not a blocker.

### E6. ResEnc numbers are correct; the "VRAM scaling went negative" claim is true

Proposals §3.4 L354-359 and the ResEnc note's table (L26-43) are marked **[reported]**. I fetched
arXiv **2404.09556v2** (Isensee, Wald, Ulrich, Baumgartner, Roy, Maier-Hein, Jaeger, *nnU-Net
Revisited*, MICCAI 2024, DOI 10.1007/978-3-031-72114-4_47) and compared Table 1 row by row. **Every
number in the vault's table matches the paper**, including VRAM and runtime columns. Therefore:

- ResEnc L − nnU-Net (org.): KiTS 88.17 − 86.04 = **+2.13**; AMOS 89.41 − 88.64 = **+0.77**. ✓
- Training time 35 h vs 9 h = **3.89×**. ✓ ("3.9×")
- ResEnc **XL vs L**: BTCV 83.28 − 83.35 = **−0.07**; ACDC 91.48 − 91.69 = **−0.21**; LiTS 81.19 −
  81.60 = **−0.41**; positive only on KiTS (+0.50), AMOS (+0.27), BraTS (+0.05). **Negative on 3 of
  6 — confirmed**, at 36.6 GB vs 22.7 GB and 66 h vs 35 h.
- The "+0.37 isolated ablation" in the patch-size note L69-79 is from a *different* paper
  (arXiv:2208.10791, *Extending nnU-Net is all you need*, AMOS Task 1: 89.08 → 89.45). I did not
  re-fetch that one; it remains **[reported]**. The vault is right to keep the two separate.

**Where the vault over-reads it.** Marking XL-vs-L as "the strongest argument against the entire
70 GB bet" is not quite the right reading, because the XL→L difference is *architecture scaling at
roughly fixed patch*, whereas the plan's bet is *patch scaling at fixed architecture*. The paper does
not isolate the latter. The honest statement: the paper shows **compute scaling has a ceiling and
crosses zero on 3 of 6 datasets**, which makes an unmeasured 2× extrapolation past their largest
preset a real risk — but not a measurement of it.

**What does bear directly on §3.** `residual_encoder_unet_planners.py` @v2.5.1:
`nnUNetPlannerResEncL.__init__` warns loudly if `gpu_memory_target_in_gb != 24`
(`UNet_reference_val_3d = 2100000000`, `corresp_GB = 24`, `max_dataset_covered = 1`);
`ResEncXL` likewise at 40. And its `get_plans_for_configuration` contains the **identical**
`256 ** 3` initial-patch block. So the "paired ResEnc run, sized for this much VRAM" of plan §3.3 has
no supported configuration: the presets are pinned at 24/40 GB, and forcing them to 70 triggers the
warning and buys batch size, not depth or patch.

Cost of the paired run, computed the same way as E1 (FLOPs, `flops2.py`): at a fixed 256³ patch, a
ResEnc encoder with `n_blocks_per_stage = (1,3,4,6,6,6,6)` and a 1-conv decoder is **1.34×** the
plain U-Net's forward FLOPs — not 3.9×. The paper's 3.9× is L-vs-original at *different* patch sizes
and VRAM. So the ResEnc arm costs ~1.34 folds, not ~4, which makes it **cheaper than the vault
thinks** and weakens the "3.9× is the binding constraint against a 24 h walltime" argument in §3.4
L358-359.

### E7. The anisotropy gate cannot fire; it is a formality

Proposals §3.1 L300 adds a gate: *"Confirm the anisotropy branch does not fire."* `ANISO_THRESHOLD = 3`
(`nnunetv2/configuration.py`), and the branch needs *both*
`target[worst] > 3 · max(others)` **and** `target_size[worst] · 3 < min(others)`
(`default_experiment_planner.py` L186-187). ImageCAS spacing is 0.25–0.45 mm in-plane / through-plane,
so the worst achievable ratio is ~0.45/0.29 ≈ **1.55** (≈1.72 if you take 0.5/0.29) — less than half
the threshold, and the size condition also fails (512 vs ~240). **The branch is unreachable on this
cohort.** Keep the gate as a one-line recorded fact; do not present it as a risk. The risk the repo's
`max_spacing_mm: 0.5` guard (`plans.py:spacing_warnings()` L253-283) protects against — the *median*
being dragged coarse — is the real one, and it is already handled in code.

---

## 3. Weak reasoning and unsupported leaps

**L1. "The big patch plus a smarter sampler buys what the crop bought" (plan L57-59) is asserted, not
argued.** The crop bought three distinct things and the plan conflates them: patch *fraction*
(genuinely replaced — 27 % without a crop), sampling *efficiency* (partly replaced, and only by the
sampler experiment in §5, which is unimplemented, unvalidated and, per E3, misspecified), and
*background suppression* (not replaced at all — a 256³ patch centred on the aorta at 0.35 mm spans
90 mm and still contains lung, spine and pulmonary vasculature). The third is then re-labelled a
*benefit* at L60-63: *"Keeping whole volumes also lets the model learn to reject coronary look-alikes
(pulmonary vessels, bone edges) that live outside any heart crop — ImageCAS's documented mis-crop
failure."* **That benefit has no evidence anywhere in the 9 notes of this folder.** I searched the
slice: the sampling note L107-110 asserts the same thing ("Keep some genuinely random background
patches … for look-alike rejection") and explicitly says none of its cited imbalance evidence
supports it. The only related measured fact in the vault cuts the *other* way — proposals §1.5 L147
says the original ImageCAS masks *include* pulmonary vessels and coronary veins, i.e. the binary
model's labels **teach it to accept the look-alikes**, not reject them. The look-alike-rejection
argument should be marked [unverified] and dropped from the justification for the no-crop decision;
the decision survives on the patch-fraction and silent-truncation arguments alone, which are sound.

**L2. The patch-size evidence is 64³ and the operating point is 16.8 M voxels — a 65× extrapolation,
and the vault says so and then proceeds anyway.** The patch-size note is the most honest document in
the folder (L51-56: *"the honest claim the plan can make is 'small patches are demonstrably harmful
on this data', not '256³ is demonstrably optimal'"*), and it correctly notes at L44-49 that
ImageCAS's own 32³→64³ gain went non-significant once context was supplied another way. Nothing in
the plan carries that caveat forward. Plan §2 reads as settled. Given E1 — that the patch is capped
at 16.8 M *whatever* you ask for — the extrapolation is also **unfalsifiable by tuning**: there is no
"bigger patch" arm available without patching the planner. That strengthens the case for making the
patch-budget comparison an early measurement (see M1).

**L3. "Neither affects training accuracy" (plan L68) is asserted about disk and inference cost and is
true, but it is used to close a question that is really about *feasibility*, not accuracy.** Disk
plus purge policy plus a non-chained 12 h prepare job is where this plan is most likely to lose a
week, and none of it is scheduled or measured.

**L4. The schedule note reasons from an ImageCAS number it simultaneously discredits.** L43:
*"ImageCAS's 21 k iterations is 8.4 % of nnU-Net's nominal 250 k schedule. The published Dice is at or
near the inter-observer ceiling (0.8296 vs ~0.856 agreement), suggesting either (a) that dataset has
early saturation, or (b) stopping at 21 k was arbitrary."* Proposals §1.1 and §1.4 have already
established that 0.856 is the wrong ceiling (binary ASOCA, not this cohort) and that 82.96 % is an
under-trained baseline against labels a re-annotation disagrees with at 41.8 % Dice. The "early
saturation" hypothesis therefore rests on a comparison the same document set has retracted. Delete
branch (a); the honest read is that 21 k was arbitrary, and the note's own L71 conclusion — *"the
binary model (21 k iterations) could complete in a single 24-hour block"* — is a category error:
**we** will train 250 k iterations, not 21 k, because v2 has no early stopping (E2).

**L5. §3's ordering argument ("not first, because it adds a variable before a baseline exists",
L92) is sound, but it is applied inconsistently.** The same logic would make the patch-budget sanity
run *first*, since `--gpu-mem` is the largest single unvalidated variable in the plan and it is
baked into every subsequent checkpoint (`plans.py` L89-92 notes plans made for one budget are not
interchangeable with checkpoints from another). §3.4 ranks it **2nd**, behind binary-init
fine-tuning — which is an experiment about the *multiclass* model, requires per-branch labels, and is
subject to the §2.2 leakage constraint. Ranking an experiment that cannot start yet above one that
gates everything is the wrong order.

---

## 4. What's missing — extensions that would change a decision

**M1. The patch-budget sanity run should be experiment #1, and its design should change.** §3.4 ranks
it 2nd and specifies `--gpu-mem 24` vs `--gpu-mem 70`, one fold each. Given E1, promote it to #1 and
respecify: **`--gpu-mem 24` (7.34 M voxels, bs 2) vs `--gpu-mem 56` (16.78 M voxels, bs 2)** — the
56 GB arm is the only one that isolates patch size, because the 70 GB arm changes *both* patch and
batch and so confounds the comparison with the +0.12-Dice batch effect the patch-size note L73-77
already measured. Cost: 14–21 h + 33–48 h ≈ **2–3 blocks total**, on labels that already exist. It
gates the `--gpu-mem` value in both task configs and every checkpoint downstream. Rank: **1**.

**M2. Multi-GPU is never considered, and it dissolves the walltime constraint.** Trillium's GPU
subcluster is 63 nodes × 4 × H100-80GB, and *"Jobs are allocated either per-node, or single-GPU
(1/4 node)"* — so the repo's `configs/dataset.yaml` L116-118 comment is right and a 1-GPU job is
**not** billed as a whole node (I checked this specifically because it would have been a 4× budget
error; it is not one). But `nnUNetv2_train -num_gpus N` appears **nowhere** in 84 notes. Four GPUs
would cut a 48 h fold to ~13 h — **one 23:50 block, no chain, no resume risk** — at the same
GPU-hour cost. The catch, which is exactly E1 again: `nnUNetTrainer._set_batch_size_and_oversample`
asserts `global_batch_size >= world_size` (trainer L355). At `--gpu-mem 56` the planner gives batch
2 → **2 GPUs max**; at 70 it gives 3 → and the scheduler accepts only 1 or 4. To use 4 GPUs you must
force `batch_size: 4` in the plans file, which puts 1 sample/GPU at 256³ ≈ 26 GB modelled — very
comfortable. **Recommendation: measure a 2-GPU run in the first sanity job. If it scales, the
job-chain machinery (`slurm.py`, 25 kB, `chain_mode`, `chain_max`, `pause_margin_seconds`) becomes
optional rather than load-bearing.** That is the single largest de-risking available.

**M3. `chain_max: 3` is probably too small at 70 GB and exactly right at 56.** Anchoring on
arXiv:2404.09556 Table 1 (nnU-Net org., 1000 epochs, **9 h**) and scaling by the FLOP ratio I
computed, with an H100-vs-A100 factor of 1.5–2.2×:

| config | FLOP ratio vs typical | h / fold | × 23:50 blocks |
|---|---|---|---|
| 112×256×256, bs 2 (`--gpu-mem 24`) | 3.50× | 14–21 | 0.6–0.9 |
| **256³, bs 2 (`--gpu-mem 56`)** | **8.01×** | **33–48** | **1.4–2.0** |
| 256³, bs 3 (`--gpu-mem 70`) | 12.0× | 49–72 | 2.1–3.0 |
| ResEnc, 256³, bs 2 | 10.8× | 44–65 | 1.8–2.7 |

So `chain_max: 3` (~71 h) is **at the ceiling** at 70 GB — and the ceiling is the pessimistic end of
my range, with another reviewer estimating 100–200 GPU-h/fold, which would blow it outright. At
56 GB it is a 1.5× margin. **Recommendation: raise `chain_max` to 5 (`configs/dataset.yaml` L148,
`config.py` L115) and, more importantly, add a hard check — the trainer should compare
`epoch_time × remaining_epochs` against `chain_max × walltime` at the end of block 1 and fail loudly
if the run cannot finish.** Right now a chain that runs out produces a half-trained checkpoint with
no signal, and since nnU-Net's LR schedule is `(1 − epoch/1000)^0.9`, a run stopped at epoch 600 is
at LR 0.0045 — visibly unconverged, but only if someone looks.

**M4. Total programme cost, and whether it fits.** Assuming `--gpu-mem 56` (40 h/fold; +10 % for
15-class multiclass):

| item | folds | h |
|---|---|---|
| Binary run A (Dataset710, fold 0) | 1 | 40 |
| Binary run B (Dataset711, fold 0) | 1 | 40 |
| Patch-budget sanity (24 GB arm) | 1 | 18 |
| Multiclass baseline, 5-fold | 5 | 220 |
| Fold-0 ablations: binary-init FT, Skeleton Recall, class-balanced sampling, rotation, heart-crop paired, deep supervision | 6 | 264 |
| ResEnc paired run (1.34×, fold 0) | 1 | 59 |
| TTA / overlap tuning (inference only) | — | ~2 |
| **total** | | **≈640 GPU-h** |

At 70 GB with batch 3 that becomes ≈**960 GPU-h**; at the pessimistic end of the hardware range,
≈1400. One Alliance GPU-year is 8766 GPU-h, so the programme is **0.07–0.16 GPU-years** — well
inside even a modest RAC, and **not compute-infeasible**. The binding constraint is not GPU-hours,
it is **serialisation**: ~30–45 chained 23:50 blocks, each with a queue wait, on a 63-node
subcluster, with `chain_mode: array` (`--array=1-3%1`) running one block at a time *within* a run.
The programme is calendar-feasible **only if the independent arms are submitted as concurrent
chains** (SciNet allows 50 running / 1000 queued jobs for users with an allocation, so this is
possible) — and only if every arm is not silently a full 1000-epoch run. Nothing in the plan says
ablation arms may be shortened, and since v2 has no early stopping (E2) they will not shorten
themselves. **Recommendation: state a reduced epoch budget for fold-0 ablation arms explicitly
(`epochs:` is already a task-config field), and say the 5-fold final config is the only full-schedule
5-fold run.** That is the difference between ~640 h and ~1400 h.

**M5. bf16 instead of fp16, on a card that supports it natively.** `nnUNetTrainer` uses
`autocast(self.device.type, enabled=True)` with a `GradScaler` (L164, L993, L998-1003) — i.e. **fp16
AMP**. On an H100, bf16 has the same throughput, needs no loss scaler, and removes an entire class of
failure (scaler skipping steps, inf/NaN on the Dice denominator). This is not mentioned anywhere in
the vault. It is a ~3-line trainer override and it interacts with M2: DDP + fp16 GradScaler across 4
ranks is a known source of rank-divergent step skipping. **Recommendation: add to the pre-submission
gates — record which autocast dtype the run used, and default to bf16.**

**M6. Gradient checkpointing is the only mechanism that would actually buy patch size, and it is not
considered.** Given E1, the planner will not give you more than ~16.8 M voxels. If the patch-budget
experiment (M1) shows the gain is still rising at 16.8 M, the *only* ways forward are (a)
`torch.utils.checkpoint` on the encoder stages, which trades ~30 % compute for ~40-60 % activation
memory and would let a hand-edited plans file carry a 320³ patch at batch 2, or (b) patching
`initial_patch_size` in a planner subclass — a 2-line override of `get_plans_for_configuration`.
Both are cheap; neither appears in the vault. **This is the missing contingency for "what if bigger
is better and nnU-Net won't give it to me".**

**M7. `tile_step_size` is a free accuracy/cost dial nobody has costed.** Verified default 0.5
(`predict_from_raw_data.py` L39). At 256³ over 512×512×240 the window count is only 9, so dropping to
`tile_step_size = 0.25` costs ~5×5×1 = 25 windows — still trivially cheap in absolute terms, and it
is the cheapest available lever on the exact failure mode this project cares about (fragmentation at
patch seams, where a 3-voxel vessel crosses a boundary). The proposals list "TTA / overlap tuning" as
priority 6, conditional. Given the absolute numbers, it should be **unconditional and free**: it
needs no training, only re-inference of an existing checkpoint. Promote it.

**M8. A two-stage patch pipeline at native resolution is refused by name but never by argument.**
§1 rules out `3d_cascade_fullres` because the *first* stage downsamples. That reasoning does not
cover a *native-resolution* two-stage design (binary lumen at full res → dilate → multiclass only
inside the dilated mask), which is precisely what ImageCAS's own best result did — and the cascade
note L44-49 records that ImageCAS's 32³→64³ patch gain *vanished* once the dilated pre-segmentation
supplied context. That is direct evidence on this cohort that a native-res prior substitutes for
patch size, and the plan's §2 argument ("context can be bought either by a bigger patch or by handing
the network a prior; we are buying it with the patch", patch-size note L47-49) picks the expensive
half without a measurement. Since plan §3 produces a binary model *anyway*, the prior is free. Worth
recording as a paired experiment rather than leaving it covered by a refusal aimed at something else.

---

## 5. Confidence, and what I could not check

**High confidence (read the source, quoted file + line + tag):** the 256³ initial-patch cap and the
shrink-only loop; `lowres_creation_threshold = 0.25` at v2.5.1 / v2.6.2 / master; the second lowres
drop trigger; `ANISO_THRESHOLD = 3`; `num_epochs = 1000` / `num_iterations_per_epoch = 250`; the
**absence** of early stopping; `PolyLRScheduler` exponent 0.9; `save_every = 50` epochs;
`get_bbox`'s uniform class choice and its real file/class/line; the 50 %-not-33 % oversample at
batch 2; `sampling_probabilities` as an existing hook; `overwrite_class` as an existing hook; the DDP
`global_batch_size >= world_size` assert; `tile_step_size = 0.5` and `use_mirroring = True`;
preprocessor dtypes and the v2.6 blosc2 switch; the ResEnc planners' pinned 24/40 GB targets and
their identical 256³ cap.

**High confidence (independently reproduced):** every number in the vault's nnU-Net Revisited table,
against arXiv:2404.09556v2 Table 1 — including +2.13 KiTS, +0.77 AMOS, 3.89× runtime, and XL-vs-L
negative on 3 of 6.

**Medium confidence — my own arithmetic, validated but not measured.** My
`compute_conv_feature_map_size` reproduction agrees with the planner's own historical reference
(450 699 264 vs the commented 455 600 128, 1.1 %), so the patch/batch table is as good as the
planner's model. But **the planner's model is itself a heuristic**, and the mapping from
feature-map elements to real bytes is calibrated, not derived. So "batch 3 needs 77.3 GB" is
nnU-Net's own claim restated, not a measurement. **`--gpu-mem 70` is very likely to OOM or to sit at
97 % of the card; I could not run it.** The one cheap way to settle it is `segtrain plan` on the real
fingerprint, which needs no GPU — and which is exactly what the plan's own L77 says ("the planner's
number is the real one"). It should be run before anything else in this review is acted on.

**Medium confidence — wall-clock.** My 33–72 h/fold rests on FLOP ratios against a single anchor
(9 h for nnU-Net original in Table 1) and an assumed 1.5–2.2× H100/A100 factor. The paper does not
state per-dataset patch sizes for that row, so the 8.01× ratio has real slack. A pure-FLOPs
efficiency check suggests the anchor implies only ~50 TFLOPS effective, which is plausible for 3D
convs + InstanceNorm but means the run may be partly dataloader- or memory-bandwidth-bound, in which
case my numbers are optimistic. **Treat 33–72 h as a bracket, and measure epoch time in block 1.**

**Could not check (unreachable, not confirmed):**
- **Trillium's $SCRATCH quota and inode limit.** `docs.scinet.utoronto.ca/index.php/Trillium` → 404;
  `docs.alliancecan.ca/wiki/Trillium` → 403 (BotStopper); the Quickstart page carries no quota table.
  I verified the 4×H100/node configuration, the 24 h cap, per-node-or-single-GPU allocation, and the
  2-month scratch purge via search, but the quota number itself is unverified. The conclusion
  ("~465 GB fits") rests on Alliance norms, not on a read quota.
- **The actual ImageCAS median shape and median spacing after transposition.** Everything in E1 and
  E5 that depends on "median z" and "isotropic vs 0.5 mm z" is conditional on a fingerprint nobody
  has extracted. This is the cheapest missing measurement in the whole plan and it decides whether
  gate (a) reads 23 % or 31 % and whether gate (c) reads 2 or 3.
- **The +0.37 isolated residual-encoder ablation** (arXiv:2208.10791) — I did not re-fetch it; it
  stays [reported].
- **The Hung et al. per-configuration numbers** (DOI 10.1007/s10439-026-03974-5) — still paywalled,
  as the cascade note L52-54 says. The cascade refusal therefore still rests on "no evidence a
  cascade helps" rather than "a cascade has been shown to lose", which is how the note already
  words it. Correctly.
- **Whether the repo's `nnUNetTrainer_segtrain`** (`src/segtrain/nnunet_ext/`) overrides any of the
  trainer defaults I quoted. I read `plans.py`, `config.py` and the task configs but not the custom
  trainer; `configs/dataset.yaml` L150 (`save_every: 25`) and L138 (`pause_margin_seconds`) imply it
  does override at least those two, so the repo is ahead of the vault on E2's operational half.

---

## Appendix — the four plan changes this review asks for, in order

1. **`--gpu-mem 70` → `--gpu-mem 56`** in plan §2 L50 and both task configs, with the mechanism
   (planner caps patch at 256³-volume; surplus buys batch size) written down in place of the
   scaling arithmetic. Fixes gate (c), removes the 77/80 GB OOM risk, costs nothing in patch size.
2. **Re-frame gate (a)** from a pass/fail with an implied VRAM remedy to a recorded fact: patch
   fraction on this cohort is structurally 23–31 % and is not tunable; 22 % is an accepted outcome
   and `3d_lowres` appearing in the plans file is cosmetic. Correct the threshold to 25 % (already
   done in the configs, not in the plan).
3. **Promote the patch-budget sanity run to experiment #1**, respecified as 24 GB vs 56 GB (both
   batch 2) so it isolates patch size, and add a 2-GPU throughput measurement to the same job.
4. **Rewrite the schedule note from source**: no early stopping, exponent 0.9, 50 validation
   iterations per epoch, checkpoint every N *epochs*. Then raise `chain_max` to 5, add an
   end-of-block-1 feasibility check, and state a reduced epoch budget for fold-0 ablation arms.

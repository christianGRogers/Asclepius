---
tags: [plans, experiment, audit, segtrain, implementation, sealed-test, reads, convert]
author: Echo
round: 6
updated: 2026-10-10
---

# Audit of the segtrain implementation against the master plan

## Question

Does `src/segtrain/` (with `configs/` and `docs/TRAINING-R1.md`) do what
[[Master plan]] (Atlas v5 + A1–A16), [[Human decisions]] (D0–D5) and [[Sealed test]]
say, end to end: from the proxy labels and the SegQueue export, through convert,
splits, plans and the trainer, to scoring and the double-read report? (Round 6, Q4.)

## Method

- I read every module on the R1 path: `cli`, `config`, `index`, `splits`,
  `convert`, `plans`, `proxy`, `namer` (decision layer), `reads`, `tf1`,
  `evaluate`, `slurm`, `nnunet_ext/*`. I also read the three task YAMLs,
  the two label sets, the runbook, the SegQueue segment defaults
  (`server/girder_segqueue/settings.py`) and the exporter
  (`server/girder_segqueue/export.py`). Each finding was checked against
  the full amendment wording in [[Round 2]], [[Round 3]] and [[Round 5]] §1,
  not only against the master's summary.
- `src/segtrain/tf1.py` sha256 is `3c737cbc…9253`, equal to the A1c hash.
  I did not edit `src/`.
- Real data, all of it non-sealed:
  - The ImageCAS-X filelists (`work/Bridge/icx/*.txt`) gave the R1 case
    counts.
  - c0001's cached mask header and the real SegQueue submission
    `imagecas_0002_attempt1.seg.nrrd` gave the orientation check (header
    only).
  - `experiments/Echo/proxy_qa_probe.py` ran the proxy projection and the A4
    namer QA on ImageCAS-X train cases c0003, c0016, c0032, c0050, c0059,
    c0071, c0090 and c0116.
- Every runbook command was parsed by `segtrain`'s own argparse. All 11 parse.
- Each confirmed defect has a test, marked `xfail(strict=True)`, in
  `tests/test_audit_pipeline.py`, `tests/test_audit_reads.py` or
  `tests/test_audit_inference.py`. All 17 fail for the stated reason under
  `--runxfail`, and the suite stays green (639 passed, 46 skipped,
  17 xfailed). When a fix lands, its test turns red (XPASS strict), and the
  owner removes the marker.

## Result: confirmed defects

| ID | Severity | Defect | Contradicts | Owner | Test |
|---|---|---|---|---|---|
| D2 | **critical** | The sealed refusal is keyed on exact `cNNNN` ids, so team reads of sealed cases enter `imagesTr` | A14 | Atlas (convert) + project lead (SegQueue export) | `test_audit_pipeline::test_sealed_case_under_its_segqueue_name_is_refused`, `::test_second_read_of_a_sealed_case_is_refused` |
| D3 | high | convert drops physically correct labels stored z-reversed, and trains any case whose labels it dropped as all-background | D0/D2 (team labels reach training) | Atlas (convert) | `::test_physically_identical_z_reversed_label_is_kept`, `::test_case_with_dropped_labels_does_not_enter_training` |
| D1 | high | The runbook's index → convert → explicit split silently loses 86 of the 640 R1 cases | Master recipe (560/80 ImageCAS-X train/val) | Atlas (index/convert/plans, runbook) | `::test_runbook_index_convert_split_keeps_every_icx_train_case` |
| D5 | medium | `reads.a11_targets` still writes the name-conflict `ignore` that A11′ removed | A11′ | Crucible (reads) | `test_audit_reads::test_two_read_targets_keep_each_reads_own_names` |
| D6 | medium | The wave report never runs A3's calibre trigger | A3 | Crucible (reads) | `::test_wave_report_runs_the_calibre_trigger` |
| D7 | medium | The wave report's third-read rule ignores the ramus-only exemption | A11′ / Round 3 A4 / D1b | Crucible (reads) | `::test_ramus_only_disagreement_does_not_trigger_a_third_read` |
| D4 | medium | The reads scorer drops `provisional` and `flagged`, so A10 aggregates cannot obey A1a/A1b | A1a, A1b, A10 | Crucible (reads); Delta to advise on the interface | `::test_score_vs_reads_carries_the_provisional_flag` |
| D10 | medium | `load_read_folder` ignores affines, and it reads the SegQueue export's `ct.nii.gz` as an annotator | A3, A12, runbook step 9 | Crucible (reads) | `::test_read_folder_aligns_reads_with_the_mask`, `::test_read_folder_does_not_take_the_ct_for_a_read` |
| D12 | medium | `segtrain tf1` never checks that the prediction (or aorta) affine matches the reference | A9 | Atlas (cli); Delta to review | `test_audit_inference::test_tf1_cli_refuses_or_aligns_a_reoriented_prediction` |
| D13 | medium | `segtrain plan` and `scinet prepare` overwrite the ImageCAS-X split with the hash split | Master recipe | Atlas (plans/slurm) | `test_audit_pipeline::test_prepare_job_for_712_keeps_the_icx_split` |
| D11 | low | Test-set inference does not save softmax | A7 (Round 2 wording) | Atlas (evaluate) | `test_audit_inference::test_test_set_inference_saves_softmax` |
| D8 | low | `segtrain proxy` reports success when no case was written, and drops missing cases silently | "inputs silently dropped" | Atlas (proxy/cli) | `test_audit_pipeline::test_proxy_cli_fails_when_no_case_was_written` |
| D9 | low | Two runbook steps do not work as written | docs | Atlas (runbook, plans) | `::test_plan_printout_shows_the_ct_window`, `::test_runbook_convert_points_at_the_proxy_tree` |

**Totals:** 13 confirmed defects. By severity: 1 critical, 2 high, 7 medium,
3 low.

### D2 — sealed cases reach training through the team-label path (critical)

The trigger is `convert_dataset`, which excludes `load_sealed()` ids by exact
string match. Two real names fail that match.

- **The SegQueue case name.** SegQueue names a case `imagecas_NNNN`, using the
  1-based ImageCAS id. Both real submissions are named this way
  (`imagecas_0002`, `imagecas_0005`). `imagecas_0002` is voxel-identical to
  `c0001` ([[Crucible - ImageCAS-X is real and its 800 cases are our cases c(id-1)]]).
  `segqueue-export` writes `<out>/<case['name']>/…`, and nothing in
  `src/segtrain` maps `imagecas_NNNN` to `c{NNNN-1}`. So
  `imagecas_0003` (= c0002, sealed) indexes, converts and lands in
  `imagesTr`. The test shows `{'imagecas_0003_0000.nii.gz', …}`.
- **The replica suffix.** D2 means every case is read twice. Getting both reads
  out needs `segqueue-export --replicas all`, which names the second read
  `<case>__r2`. `c0002__r2` is not in the sealed set and is converted.
  The test shows `{'c0002__r2_0000.nii.gz'}`.

The same names also break the other sealed-test and ImageCAS-X lookups:

- `write_explicit_splits` drops `__r2` and `imagecas_*` ids without a
  message. A11′ wants the second read as its own training sample, so it never
  trains.
- `load_read_folder` finds no ImageCAS-X anchor for `imagecas_*`
  (`case[1:].isdigit()` fails).
- Hash splits put the two reads of one case in different splits, which leaks
  val into train.

Severity: the proxy path is safe, because it only proxies ImageCAS-X
train/val and refuses sealed cases. Once team reads exist, the documented
route (export → index → convert) breaks A14 without any message, and A14 is
the plan's one guarantee of an unbiased final test.

Fix: map export names to case ids (`imagecas_NNNN` → `c{NNNN-1:04d}`, strip
`__rK`) at one place (index or convert). Apply the sealed refusal to the
mapped id, refuse any unmapped id for task 712, and keep both reads of a case
in the same split.

### D3 — convert discards real team labels, then trains the case anyway (high)

The real SegQueue submission header, set against c0001's mask:

- **Submission:** `space: left-posterior-superior`,
  `space directions (0.371,0,0) (0,-0.371,0) (0,0,-0.5)`,
  origin `(-43.81,-75.19,-186.55)`.
- **Mask:** RAS affine with z column `+0.5`, origin z `-323.55`.

Converted to RAS, the two grids cover exactly the same voxel centres (same
bounding box), but k runs the other way. The exporter keeps the submission's
voxel order and direction (`CopyInformation`). `geometry_offset_mm` compares
the two affines at the same voxel-index corners, so it reports **137.0 mm**:
a z-reversed but physically identical label is "geometry mismatch", and its
labels are "DROPPED".

Separately, any case whose labels are dropped is still written to
`labelsTr` as all zeros, and its CT is linked into `imagesTr`. It is counted
as converted, and `report.ok` stays True. This applies to both
`merge_masks` (the export's per-structure layout) and `remap_multilabel`.
The run prints one WARNING line and then trains that case's vessels as
background.

The first half (reversed-axis drop) is confirmed on the real header geometry.
I have not seen a real export of an approved submission. The second half
(dropped labels still trained) is confirmed by code and test, whatever the
cause of the drop.

Fix: compare physical voxel centres after canonical reordering (nibabel
`as_closest_canonical`), or reorient the label onto the CT grid. Fail the
case (keep it out of `imagesTr`) whenever any structure is dropped.

### D1 — the runbook loses 13 % of R1's training set (high)

- `segtrain index` (runbook step 4, defaults `--val-fraction 0.15
  --test-fraction 0.15`) hashes every proxy case into
  train/val/**test**.
- `convert` sends the "test" ones to `imagesTs`.
- `segtrain splits --explicit-icx` then intersects ImageCAS-X's lists with
  `imagesTr`. `write_explicit_splits` does this with no message, unlike
  `write_splits`, which prints a note.

On the real filelists this loses **75 of 560** ImageCAS-X train cases and
**11 of 80** val cases. The test reproduces it: train
`['c0105','c0107']` instead of 4 cases. Run 1 is not affected, because it
used its own `trillium/atlas/lib/prepare.py`. The full R1 and every
fine-tune that follows the runbook are affected.

A side effect is that `segtrain evaluate --task 712` then predicts and scores
`imagesTs`, which holds those 86 proxy-labelled ImageCAS-X **train/val**
cases. That is neither the sealed test nor the 36 open test cases, and the
score is Dice/NSD rather than tF1.

Fix: for task 712, index with `--val-fraction 0 --test-fraction 0`
(or pin every case to train via `--overrides`), and make
`write_explicit_splits` refuse, or at least report, listed cases that are
absent.

### D5 — the retired A11 `ignore` is the only two-read target builder (medium)

Round 5 replaced the A11 voxel rule with A11′: "each read is a separate
training sample with **no name-conflict `ignore`**". `reads.a11_targets` (and
the `reads` module docstring) still set `ignore=5` wherever the reads name a
voxel differently. The A12 report uses it to compute "ignore fraction". The
task YAML (`configs/tasks/Dataset712_CoronaryBranches.yaml`) still points to
`segtrain.reads` and A11 for team-read targets. So the one documented target
builder implements the rule the judge retired, and no A11′ builder exists.

### D6 — the A3 calibre trigger never runs (medium)

A3 (Round 3) flags a read as thin on either of two triggers: union Dice
< 0.9, or calibre nearer ImageCAS-X than the mask. `convention_check`
implements both. `first_reads_report`, the code behind
`segtrain reads-report`, calls it without `icx_lumen`, even when it has
loaded `cr.icx4`. In the wave report, the monitor that decides a wave halt
is therefore Dice-only.

### D7 — ramus-only disagreements still go to a third reader (medium)

`third_read_triggers` supports a `ramus_mask` exemption.
`first_reads_report` never passes one. `naming_attribution` computes the
namer's ramus candidates, but it does not return them. In the test, the
namer reports `ramus_only` for a 25.5 % LAD/LCx swap confined to the ramus
candidate, yet the case still needs a third read ("LAD/LCx swap 25.5 % >
5 %"). This contradicts the exemption kept in A11′ and D1b. The cost is
reviewer time on every early-diagonal-or-ramus case, which the namer cannot
tell apart by geometry ([[Round 3]] A4).

### D4 — A1a/A1b cannot be enforced in the A10 aggregates (medium)

`reads.default_scorer` returns `TreeF1.per_class` only. Both
`TreeF1.provisional` (no aorta mask, A1a) and `TreeF1.flagged` (A1b) are
discarded. Every caller then averages without them: `score_vs_reads`,
`inter_read_tf1`, `acceptance`, the third-read trigger
`inter-read tF1 < 0.80`, and the report's "acceptance ceiling".

`segtrain reads-report` always scores without aortas. Its REPORT.md does
not say "provisional", although step 9 of the runbook admits it. Under A1a
such a number "decides nothing", and yet the third-read trigger acts on it.
A1b requires flagged trees to be "excluded from decisive aggregates until a
human has reviewed them", and `acceptance()` has no way to do that.

### D10 — the reads loader is blind to geometry and to the export layout (medium)

- **Affines.** `load_read_folder` keeps the last read's affine and never
  compares it with the mask's or the ImageCAS-X grid. With a z-reversed read
  (the real submission storage, see D3), A3 sees union Dice 0.000 and flags
  a perfect split as thin. The carina anchor is computed on misaligned
  arrays.
- **Export layout.** Pointed at the SegQueue export
  (`<case>/ct.nii.gz + segmentations/*.nii.gz`), the loader takes
  `ct.nii.gz`, cast to uint8, as an annotator called "ct" and ignores the
  segmentations.

No code converts the export into the `<case>/<annotator>.nii.gz` layout
that runbook step 9 asks for.

### D12 — the deciding-metric command trusts array order (medium)

`segtrain tf1` loads the reference, the prediction and `--aorta`, takes
spacing from the reference header, and compares arrays voxel by voxel. It
never checks that the shapes and affines agree. A prediction on the same
physical grid, stored z-reversed, scores tF1 0.0 instead of 1.0 and no
warning is raised. nnU-Net's `NibabelIOWithReorient` writes predictions
back in the input orientation, so the main R1 path is fine. Aorta masks from
TotalSegmentator, team reads (D3) and any external prediction are exactly
where this bites, and A1 makes the aorta decisive.

### D13 — re-planning silently discards the ImageCAS-X split (medium)

`cmd_plan` always ends with `write_splits(scheme=official)`, which writes the
meta.csv hash split. The runbook order (plan, then
`splits --explicit-icx`) works only once. A re-plan, for instance for run
2's winning window, overwrites the ImageCAS-X split without a message.
`segtrain scinet prepare --task 712` runs convert, plan and preprocess with
no explicit-split step at all, so a prepared task 712 trains on the hash
split.

### D11 — no softmax at test inference (low)

Round 2 A7: "val and test inference **save softmax**". The coronary trainer
saves the val softmax (correct). `evaluate.predict_test_set` passes
`save_probabilities=False`. Low severity, because R and H are retired
(Round 5 A7) and A13's inference-only reuse relies on the val softmax. The
binding sentence still covers test, though.

### D8 — `segtrain proxy` reports success on total failure (low)

`cmd_proxy` prints `len(records)` as "proxy cases written". That count
includes records with `ok=False` and A4-excluded cases. It returns 0 even
when nothing was written. The test case points `--icx` at a
`segmentations/` subfolder (the layout of the agents' own ImageCAS-X
caches) and gets "1 proxy cases written" with nothing written.
`build_proxy_tree` also drops requested cases missing from `--cases`, and
only `proxy_report.json` (`n_requested` vs `n_present`) records it.

This is the class of silent drop that hit a Trillium launcher once before.

### D9 — two runbook steps do not work as written (low)

- **Step 4.** `segtrain index --root $SCRATCH/asclepius/proxy` writes
  `proxy/meta.csv`. The following `segtrain convert --task 712` reads
  `<zenodo_root>/meta.csv` (default `/data/coronary`). It fails loudly
  unless `--zenodo-root` (or `dataset.local.yaml`) points at the proxy tree.
- **Step 5.** It says to "check the plan printout: … window [−300, 1300]",
  but `describe_plans` never prints the window.

## Checked and found consistent

- **Labels.** `coronary_branches.yaml` 1 LM, 2 LAD, 3 LCx, 4 RCA, which is
  what SegQueue `DEFAULT_SEGMENTS` uses (names and values), and what the
  proxy writes. `ignore` = 5 = n_classes + 1 in `dataset.json` and convert.
- **Territory and ramus.** `ICX_TO_4` is identical in `proxy`, `namer`,
  `reads` and the ported `trillium/atlas/lib/proxy.py` (D1, ramus 8 → LCx,
  D1b). "Other" (14) is left to inheritance. The namer default is
  `ramus="LCx"` everywhere (cli, `disagreement`, `naming_attribution`).
- **The A4 absent-LM guard.** It skips only the `lm`/`ostium` triggers and
  marks the case for review, which is the Round 5 wording. Ramus-only
  disagreements never exclude a proxy.
- **Case mapping.** `imagecas_id_to_case(n) = c{n-1:04d}`, used by
  `icx_split`, `build_proxy_tree`, `load_read_folder` and `_discover_cases`
  (`43.img` → c0042). On the real lists, all 80 sealed ImageCAS-X ids are in
  ImageCAS-X test, and the 20 sealed quality-0 cases are all in
  `exclude.txt`. None of the 640 train/val cases is sealed.
- **CT window.** `finalize_plans` writes [−300, 1300] / (100, 400) into
  `foreground_intensity_properties_per_channel`, which is where nnU-Net
  2.8.1's `CTNormalization` reads it. The coronary trainer refuses other
  windows at `on_train_start`. `channel_names` is `CT`.
- **Mirroring off.** The coronary trainer returns `mirror_axes=None` and
  sets `inference_allowed_mirroring_axes=None`. nnU-Net 2.8.1's predictor
  mirrors only over the checkpoint's allowed axes, so
  `predict_test_set(use_mirroring=True)` does not mirror. Its comment
  ("Mirroring IS enabled here") is misleading but harmless.
- **Softmax at val.** The coronary trainer saves it, on by default.
- **tF1.** The tF1 hash equals A1c. The ostium is the nearest centreline
  voxel to the aorta within 5 mm, per component and per side, flagged on
  > 5 mm disagreement or no aorta contact, and `provisional` without an
  aorta (A1). The FP gate is read on the raw prediction after < 100-voxel
  removal (A2/A15). The tolerance is 1.5 mm (D3).
- **A3 direction.** The monitor flags *thin* reads (Dice < 0.9; calibre
  nearer ImageCAS-X), and a wave halts above 10 %, as D0 requires. The only
  problem is D6.
- **A10.** Per-class paired bootstrap, lower bound > −0.02, scored against
  each read with no fused reference.
- **Proxy orientation.** On c0003 and c0016 the RCA-named voxels lie at
  more positive world x than the left tree (−2.8 vs −53.4 mm; −10.4 vs
  −57.5 mm). That is correct for RAS+, where the patient's left is
  negative x.
- **Runbook commands.** All 11 parse.

## Suspicions (not confirmed; no test)

- **A4 "ignore only near the carina".** `namer.compare` sets `ignore` on
  every voxel where proxy and namer both see vessel but name it
  differently, anywhere in the tree. Round 2's A4 says the ignore "applies
  only to near voxels … all within 10 mm of the carina". On the real
  probe, every unflagged case had 100 % of its ignore voxels within 10 mm of
  the carina (table below); the two flagged cases are exempt or excluded, so the wording gap has no measured effect.
  Not a defect on current evidence.
- **"LM present in one read only"** is a third-read trigger. The Round 5 A4
  guard ("the same guard applies to the A11 third-read triggers") arguably
  exempts a read with no LM from LM-based triggers. Whether one-sided
  absence of the LM is a decision disagreement (likely yes) is for Crucible
  and the judge to settle.
- **No sealed guard in `reads-report`, `tf1` or `name`.** A3 says every
  sealed case must pass the monitor before it is frozen, so the report may
  legitimately see sealed reads, but nothing stops inter-read tF1 on sealed
  cases being read before a milestone. A `--sealed` filter, on by default,
  would make the rule mechanical.
- **No aorta producer.** No batch evaluator in `src/` produces TotalSegmentator
  aortas, computes macro tF1 with A1a/A1b separation, or reports the FP
  gate. `segtrain evaluate` reports Dice/NSD only, and the runbook gives
  only the per-case `segtrain tf1` command and does not say how to get
  aorta masks.
- **Patch pinning.** `enforce_patch` pins 256³ after planning without
  re-deriving the architecture (pooling and strides). It is safe only while
  the planner itself returns 256³, which Atlas measured it does.
- **Silent loss of a class in tF1.** On synthetic boxes of even
  cross-section, skimage 0.26 `skeletonize` returns an empty skeleton, and
  `tree_f1` then silently drops that class from `per_class`. Real lumens
  are not boxes, so this probably never fires, but a class that is present
  in the reference with no centreline is dropped without a flag.
- **A4 QA skipped silently.** `proxy.qa_with_namer` writes the proxy
  without A4 QA, marking only `qa.applied=False` in the report, if
  `segtrain.namer` fails to import (for instance, a missing scipy or
  skimage in a Trillium venv).

## A4 probe on real cases

`experiments/Echo/proxy_qa_probe.py`. Projection plus
`namer.disagreement(label, mask, affine)` with ramus → LCx. Beyond 10 mm is
the share of the ignore voxels lying more than 10 mm from the carina.

| Case | Flags | Excluded | Ramus-only | Ignore voxels (namer vs proxy) | % of proxy vessel | Share beyond 10 mm | World x: left tree / RCA (mm) |
|---|---|---|---|---|---|---|---|
| c0003 | — | no | — | 476 | 0.27 % | 0.00 | −53.4 / −2.8 |
| c0016 | — | no | — | 215 | 0.26 % | 0.00 | −57.5 / −10.4 |
| c0032 | — | no | — | 518 | 0.41 % | 0.00 | −50.3 / −13.2 |
| c0050 | swap | no | **yes** (exempt; the proxy writes no ignore) | 13 610 | 13.7 % | 0.84 | −52.5 / +1.0 |
| c0059 | — | no | — | 323 | 0.22 % | 0.00 | −48.4 / +7.1 |
| c0071 | — | no | — | 413 | 0.32 % | 0.00 | −62.3 / −12.9 |
| c0090 | — | no | — | 443 | 0.33 % | 0.00 | −43.3 / +14.7 |
| c0116 | swap, tree | **yes** | no | 98 684 | 54 % | 0.99 | −69.9 / −23.8 |

Six of the eight cases are unflagged. In those, 0.22–0.41 % of the proxy
voxels become `ignore`, all of them within 10 mm of the carina, which matches
Round 2's 0.26 % median. The far disagreements occur only in flagged cases,
and those are either exempt (c0050: ramus-only, so the proxy writes no
ignore) or excluded (c0116). That is why the A4 "near carina" wording gap is
a suspicion, not a defect.

In every case the RCA lies at more positive world x than the left tree, so
orientation is consistent. Each case took about 150–205 s on one core.

## What it implies

- **Before team reads.** Fix D1 and D13 before the full-length R1, which A16
  defers until after run 2, or train from a hand-checked
  `splits_final.json`. Otherwise R1 trains on about 474 + 69 cases instead
  of 560 + 80, and nobody is told.
- **Before wave 1.** D2, D3, D10 and D5 together mean the team-label route
  does not work yet. Reads would be named `imagecas_*`, stored z-reversed,
  in a layout neither convert nor reads-report handles correctly. Sealed
  reads would leak into training, and labels would be dropped and trained
  as background. This is the next implementation job for Atlas (convert,
  index) and Crucible (reads), with the SegQueue exporter's naming as the
  integration point. A dry run of one real approved export through index,
  convert and reads-report would have caught all four.
- **Before any A10 decision.** D4, D6 and D7 change what the wave-1 report
  says (halt, third reads, ceiling), and they should be fixed before the
  first 50 double reads arrive (A12).

## Limits

- D3's reversed-axis half rests on the header of the one real submission
  plus the exporter's code. I did not have an approved export to run
  through convert.
- The SegQueue case naming rests on the submission file names and the
  Crucible note. I did not query Girder.
- Nothing was run on a GPU or with nnU-Net training. The trainer was
  audited by reading it against nnU-Net 2.8.1's source.
- The A4 probe covers only the 8 cases listed.

---
tags: [review, verification, decision-record]
status: complete
updated: 2026-09-26
slice: src/segtrain, src/segqueue, configs/, docs/, proposals §4
---

# Review 08 — implementation truth: code vs plan

Slice: does the code do what the vault says, does the vault describe the code, is the
implementation correct. All claims below were checked by reading the cited lines and, where
marked *probe*, by executing the code.

---

## 1. Verdict in five lines

1. **Phase 1 cannot be run as written.** `segtrain convert` still assumes one directory per
   case, so every case of a flat ImageCAS dataset fails — 3/3 in a probe — and the new flat
   scanner in `index.py` feeds a `convert` that cannot read the layout it detected.
2. Of the plan's seven configuration decisions, **three are enforced** (`3d_fullres`, no
   cascade, native spacing), **one is warned-about but documented as enforced**
   (`max_spacing_mm`), and **three are prose only** (`--gpu-mem 70`, batch 2, no mirroring).
3. **M5 and M8 both exist**, at the lines claimed; M8's severity is right, M5's stated
   mechanism ("vanish from the means") is wrong — no HD95 mean exists anywhere.
4. **Four correctness bugs the vault did not find**, one of them capable of poisoning an
   annotator's entire quality statistic with a bare `NaN` in JSON.
5. The vault's own cross-references are **stale in 10 places**, including the one §1.2 leans
   on; and `configs/dataset.yaml` plus `README.md` still describe the retired plan.

Test suite: **486 passed, 1 failed, 41 skipped** (details in §6).

---

## 2. Errors found — vault says X, code does Y

### E1. `max_spacing_mm: 0.5` warns; two documents say it refuses
- **Vault/docs say:** `docs/TRAINING-PHASE1.md:155` — "`max_spacing_mm: 0.5` in the task
  config **refuses that outright**." `configs/tasks/Dataset710_CoronaryLumen.yaml:46` —
  "**Refuse** a planned target coarser than this." `config.py:454` — "**Refuse** a planned
  target spacing coarser than this."
- **Code does:** `plans.py:253-283 spacing_warnings()` returns a list of strings.
  `plans.py:248-249` appends them as `"  WARNING  ..."` lines inside
  `describe_plans()`. `cli.py:218-235 cmd_plan` prints that and **returns 0**. Nothing
  raises, and no exit code changes. Worse, in the scripted path
  (`slurm.py:468-471`) the `plan` step is immediately followed by `preprocess` in the same
  `set -euo pipefail` job, so the warning scrolls into a SLURM log and the dataset is
  preprocessed at the coarse spacing anyway.
- **Fix:** `plans.py` — have `plan_experiment` (or `cmd_plan`) raise when
  `spacing_warnings()` is non-empty, with an explicit `--allow-coarse-spacing` escape.
  The guard is worth nothing if it only prints. The `max(...)` over axes at `plans.py:270`
  is correct, so only the escalation is missing.

### E2. `--gpu-mem 70` is unreachable from the job that actually plans
- **Plan says:** Training plan §2 — "Plan with `segtrain plan --task 710 --gpu-mem 70`";
  README.md:41-43 calls the 70 GB budget the thing that replaces the heart crop;
  `Proposed changes` §3.4 experiment 2 depends on it.
- **Code does:** `slurm.py:468` emits exactly
  `segtrain plan --task <id> --scheme official <roots>` — **no `--gpu-mem`**. And
  `cli.py:1092-1099` (`scinet prepare` subparser) has **no `--gpu-mem` argument at all**,
  so it cannot be passed even by hand. `cli.py:1028` defines `--gpu-mem` only on the
  standalone `plan` command, with no default, and `plans.py:107-108` omits
  `gpu_memory_target_in_gb` when it is `None` — so nnU-Net's **8 GB default** applies
  (verified upstream: `default_experiment_planner.py`, `gpu_memory_target_in_gb=8`).
  The documented runbook (`docs/TRAINING-PHASE1.md:144`, `segtrain scinet prepare --task 710
  --convert`) therefore plans a ~128³ patch, not ~256³ — and then §5 of the same document
  tells the operator to read the output of a *different*, 70 GB invocation.
- **Fix:** add `gpu_mem: 70` to the task YAML (it belongs with `configuration` and
  `max_spacing_mm`, not on a command line), thread it through `TaskConfig` and
  `plan_experiment`, and let `--gpu-mem` override. That removes the possibility of
  training a checkpoint against a plan nobody intended — which matters because, as
  `plans.py:89-91` itself notes, plans are not interchangeable across budgets.

### E3. Mirroring is disabled nowhere — not at training, not at inference
- **Plan says:** Training plan §4 rules out mirroring for multiclass.
  `Proposed changes` §1.6 says it must be disabled in **two** places.
  `vault/Research/Augmentation and preprocessing/Mirroring is ruled out...:105-108` already
  records that nothing in the trainer or the task config encodes it.
- **Code does:** `nnunet_ext/nnUNetTrainer_segtrain.py` overrides `__init__`,
  `on_train_start`, `on_epoch_end`, `save_checkpoint`, `on_train_end`, `run_training` —
  and nothing touching augmentation. Its docstring (line 4-6) states "the loss, optimizer,
  schedule and **augmentation** are untouched nnU-Net defaults". `evaluate.py:53-56` sets
  `use_mirroring=True` with a comment endorsing it.
- **Upstream mechanism (verified):** mirror axes come from
  `configure_rotation_dummyDA_mirroring_and_inital_patch_size()`, are derived from patch
  size (not from any `plans.json` field), and `inference_allowed_mirroring_axes` is written
  into the checkpoint. So the *only* place this can be fixed is a trainer subclass;
  `evaluate.py`'s `use_mirroring=True` becomes a harmless no-op once the checkpoint
  allows no axes.
- **Fix:** add `nnUNetTrainer_segtrain_nomirror` in `nnunet_ext/` that overrides
  `configure_rotation_dummyDA_mirroring_and_inital_patch_size` to return empty mirror axes
  and sets `self.inference_allowed_mirroring_axes = None`; name it in the multiclass task's
  `trainer:` field. Then add a check in `config.py::load_task` that any task with
  `label_set.n_classes > 1` uses a no-mirror trainer — the decision is class-count
  dependent, which is exactly the kind of thing a config validator can hold.
- **Note for the vault:** §1.6 is marked **[reported]**; it is now **[source]**-grade,
  and the "two places" framing is slightly off — there is one decision point (the trainer)
  whose value is persisted into the checkpoint and read back at inference.

### E4. M5 exists, but not by the stated mechanism
- **Vault says (§4, M5):** "`hausdorff95` returns `inf` for one-sided absence and
  `agreement()` serialises it to `None`" → "**The worst cases vanish from the means.**"
- **Code does:** `metrics.py:158-159` returns `float("inf")` when present in exactly one.
  `metrics.py:200` — `"hd95": None if (h != h or h == float("inf")) else round(h, 3)` —
  collapses `inf` and `NaN` to the same `None`.
  *Probe:* a structure present only in A yields `{'dice': 0.0, 'hd95': None, 'voxels_a': 27,
  'voxels_b': 0}`; a structure absent from both yields `{'dice': None, 'hd95': None, ...}`.
  The two are indistinguishable in the `hd95` field.
- **But:** `agreement()` returns only `mean_dice` (`metrics.py:207`), computed from
  `dices` — and a one-sided absence gives `dice = 0.0` (not NaN), which **is** included.
  The only aggregator of any of this in the whole repo is
  `server/girder_segqueue/rest/admin.py:120 meanAgreementDice`, which averages `mean_dice`.
  **No mean HD95 is computed anywhere**, so nothing can vanish from one.
- **The real failure, stated correctly:** the *record* loses the distinction between
  "nothing to score" and "an entire vessel is in one annotation and not the other", so any
  future HD95 aggregation — and any reviewer reading the JSON — cannot see the worst case.
  It is a latent, not an active, corruption. Severity: the gap is real and worth fixing,
  but "the worst cases vanish from the means" overstates today's damage.
- **Fix:** return a stated finite bound (TopCoW uses 90 mm) *or* keep `inf` and serialise it
  as a distinct sentinel plus a `one_sided: true` flag. Either way the per-structure record
  must distinguish the three cases. There is **no test for `hausdorff95` or `agreement()`
  anywhere in `tests/`** — that is why this survived.

### E5. M8 exists and the severity claim is right
- **Vault says (§4, M8):** "`summarize()` pools all (case, structure) pairs into one mean
  Dice"; the Metrics Reloaded aggregation pitfall.
- **Code does:** `evaluate.py:162-163` builds `all_dice = [s.dice for scores in
  per_case.values() for s in scores]`, printed at `:168` as the headline `mean Dice`.
  This is neither macro-over-classes nor micro-over-voxels: it is a mean over (case,
  structure) pairs, which weights each class by **how many cases it appears in** — exactly
  backwards for rare branches.
  *Probe*, 2 classes, 4 cases (`big` present 4/4 at 0.947; `rare` present 1/4 at 0.0):
  pooled headline **0.7579** vs macro-over-classes **0.4737** — 28 points apart. The vault's
  "2-5 points" (§3.2) is the conservative end.
  `metrics.py:286-308 aggregate()` already computes the correct per-structure means, and
  `write_reports` already writes them (`evaluate.py:144-152`), so the fix is small.
- **Note:** for phase 1 (one class) macro and pooled coincide, so M8 cannot bite until the
  multiclass task exists. Severity is right; urgency is lower than its table position.
- **Fix:** `evaluate.py:157` — print macro-over-classes as the headline, label it
  "macro over N classes", and print the pooled number beside it labelled as such.

### E6. Stale repo cross-references in the vault
`configs/tasks/Dataset710_Coronary.yaml` was deleted by HEAD (renamed to
`Dataset710_CoronaryLumen.yaml`). It is still cited in:
- `vault/Proposed changes to the training plan.md:112` — **this is §1.2's own evidence
  line**, the correction the vault is most insistent about. The 0.25 figure *is* now in
  `configs/tasks/Dataset710_CoronaryLumen.yaml:32-34` and
  `docs/TRAINING-PHASE1.md:154`, so the claim survives; only the path is dead.
- `vault/README.md:39` — used as the *example* of how to link out to code.
- `vault/Training method/Plan status.md:24`
- `vault/Research/Architectures and training/Cascade and low-resolution stages...:66,103`
- `vault/Research/Architectures and training/Proposed changes.md:17`
- `vault/Research/Augmentation and preprocessing/CT normalisation...:57`
- `vault/Research/Augmentation and preprocessing/Mirroring is ruled out...:106,108`
- `vault/Research/Augmentation and preprocessing/Proposed changes.md:18`

Two more dead paths in the vault:
- `src/segtrain/preview.py` (`Mirroring is ruled out...:94`, cited as evidence that
  `use_mirroring=False` is already done somewhere) — **the file does not exist**; it was
  removed with the Slicer monitor in `27b2b13`. That citation's evidentiary value is gone.
- `src/segqueue/scoring.py` (`Quality control rules that do not need duplicate
  assignment.md:114`, the target of an "implement immediately" recommendation) — the file
  is `server/girder_segqueue/scoring.py`. The ticket points at nothing.
- `src/segtrain/convert.py:395` (`CT normalisation...:19`) — `"channel_names"` is now at
  `convert.py:396`. One-line drift, harmless.

Also stale **inside the repo**, introduced or left by HEAD:
- `README.md:44` still says "above the **12.5 %** threshold at which nnU-Net would plan a
  cascade" — the correction the commit applied to the task YAML and the runbook was not
  applied to the README.
- `README.md:49-51` still says the binary model "**seeds the annotators' presegmentations**"
  as one undivided step — precisely the conflation HEAD split apart. Run A explicitly does
  not produce seeds (`Dataset710_CoronaryLumen.yaml:20-25`).
- `configs/dataset.yaml:20` points at `configs/labels/coronary.yaml`; only
  `coronary_lumen.yaml` exists. `dataset.yaml:11-23` documents only the nested layout — no
  mention of the flat form the real data arrives in — and `:27-29` still describes
  "phase 2 (tasks 702-706)" and the TotalSegmentator tree, both retired.
- `nnunet_ext/nnUNetTrainer_segtrain.py:12` cites `segtrain.logparse` as an existing
  fallback; that module does not exist.
- `evaluate.py:1,3` ("the **89** test cases"), `plans.py:137` ("The 89 test cases"),
  `splits.py:3,5,6,16` and `splits.py:38 EXPECTED_COUNTS = {train: 1082, val: 57, test: 89}`
  are all TotalSegmentator leftovers in the module that now governs ImageCAS splits.
  `EXPECTED_COUNTS` is load-bearing twice: its **keys** gate `read_meta`'s
  "unexpected split values" check (`splits.py:98-100`), and its **values** are asserted by
  `check_expected_counts(strict=True)` (`splits.py:115-116`). Nothing in the phase-1 path
  calls it strict, so it is inert today — but it is a trap for anyone who does.

---

## 3. Bugs the vault did not find

### B1 (blocking). `convert` cannot read the flat layout that `index` now detects
`convert.py:335-346` builds `subject = Path(zenodo_root) / case_id` and calls
`find_image(subject)` / `find_labels(subject)` — the **nested** helpers. Nothing in
`convert.py` calls `scan`, `scan_flat` or `looks_flat`, and `meta.csv` records only
`image_id` (`index.py:306`), so the layout information discovered at index time is thrown
away and cannot be recovered downstream.

*Probe* on a synthetic ImageCAS tree (`1/2/10 . {img,label} .nii.gz`):
`segtrain index` succeeds, reports "3 case(s) with an image / 3 multilabel", and prints
`next: segtrain convert --task 710`. `segtrain convert --task 710` then reports
`0 training, 0 test cases converted / FAILED: 3 case(s)` with
`no image found in ...\imagecas\1 (looked for ct.nii.gz, image.nii.gz, 1.nii.gz)` for
every case. Exit code 1, so the `set -euo pipefail` prepare job does abort — the failure is
loud, not silent. But it means **phase 1 is not runnable end to end**, after a CPU queue
wait, and the commit's verification ("driving the CLI against a synthetic ImageCAS tree")
covered `index` only. A `dataset.json` with `numTraining: 0` is written regardless
(`convert.py:554-560` runs after the pool, unconditionally).

**Fix:** teach `convert_case` the layout. Cleanest: have `cmd_convert` call
`scan(root, layout=...)` once, build a `{case_id: ScannedCase}` map, and pass each case's
resolved image/label paths into the worker instead of re-deriving them from `case_id`.
That also removes the duplicated discovery logic. Failing that, add `image_path` and
`label_path` columns to `meta.csv` — but then `write_meta`'s "one index format" claim
(`index.py:298-300`) needs revisiting. Add an integration test that runs
index → convert on a flat tree; the existing `tests/test_index_flat.py` stops at the
scanner boundary, which is exactly where the bug lives.

### B2 (serious, silent). `agreement()`'s `mean_dice` is not NaN-sanitised, and it poisons the annotator QA statistic
`metrics.py:207` returns `"mean_dice": nanmean(dices)`. `nanmean` (`metrics.py:261-264`)
returns `float("nan")` when every value was NaN — which happens whenever no structure in the
project's segment list is present in either volume.

The docstring at `metrics.py:184` promises "``inf`` is serialised as ``None`` so the result
drops straight into JSON", and the per-structure entries honour that (`:199-200`). The
top-level `mean_dice` does not.

*Probe:* `json.dumps(agreement(zeros, zeros, ['s1'], (1,1,1)))` →
`{"mean_dice": NaN, ...}`. Bare `NaN` is not valid JSON (RFC 8259); `JSON.parse` throws in
a browser, and it round-trips through Mongo as a float NaN.

Then `server/girder_segqueue/rest/admin.py:133-140 _agreementScores` filters only
`if mean is not None` — NaN passes — and `:120` computes `sum(agreements) / len(agreements)`.
**One degenerate submission makes an annotator's entire `meanAgreementDice` NaN**, and the
admin dashboard shows a broken number with no indication which case caused it. This is a
sharper version of what M5 is gesturing at, in the code path that is actually live today.

**Fix:** sanitise at the boundary, in `agreement()`: `"mean_dice": None if m != m else
round(m, 4)`, and make `_agreementScores` reject non-finite values explicitly
(`math.isfinite`), not just `None`.

### B3. `agreement()` maps label integers to names positionally, with no validation
`metrics.py:193` — `for idx, name in enumerate(names, start=1)` — and `names` comes from
`server/girder_segqueue/scoring.py:75-78 _structureNames()`, i.e.
`[s.name for s in getProject().segments]`, a list held in mutable Girder project settings.
If that list is ever reordered or an entry inserted, every structure in every QA score is
compared under the wrong name, and nothing raises.

This is the exact hazard `config.py:319-346 LabelSet.source_values` was built to prevent —
`configs/labels/coronary_lumen.yaml:13-16` even explains why reading positionally
"would mislabel every voxel while appearing to succeed". `agreement()` has no equivalent
guard because it takes a bare `Sequence[str]`.

**Fix:** have `agreement()` accept a `LabelSet` (or a `{name: index}` mapping) rather than an
ordered list, and have `scoring.py` build it from the project's segments *with* their stored
indices. Cheap, and it closes a mislabelling path in the one module whose numbers go into a
paper's inter-rater table.

### B4. `aggregate()` averages Dice over more cases than the count it prints beside it
`metrics.py:302-307`: `"dice": nanmean(s.dice for s in scores)` runs over **all** scores,
while `"n_cases_present": len(present)` counts only `ref_voxels > 0`. A case where the class
is **absent from the reference but predicted anyway** yields `dice = 0.0` (not NaN, per
`metrics.py:70-73`), so it enters the mean but not the count.

*Probe:* one perfect case + one false-positive-only case →
`{'x': {'dice': 0.5, 'nsd': nan, 'n_cases_present': 1, 'n_cases': 2}}`. The reported Dice of
0.50 is an average of two values against a printed denominator of one.

This lands directly in `test_per_structure.csv` (`evaluate.py:144-152`), the table intended
to be the headline. For coronaries it will bite hardest exactly where it matters: a model
that hallucinates L-PDA in cases without one gets a rare class's Dice dragged down against a
case count that says the score rests on a handful of cases. The vault's E21 ("absent-absent
predictions are excluded from aggregation") describes what a reader will assume; the code
excludes absent-**absent** but includes absent-**predicted**, and never says so.

**Fix:** report both denominators, or add a third field (`n_cases_scored`) so Dice and its
count agree. State the policy in the CSV header comment or the docstring — the vault's E21
is asking for exactly that.

### B5 (minor, real). `DEFAULT_NSD_TOLERANCE_MM` is duplicated in the CLI
`metrics.py:39` sets 1.5; `cli.py:1146` independently hardcodes
`--nsd-tolerance ... default=1.5`. Fixing M6 in `metrics.py` alone will not change the
default anyone actually gets. Worth folding into the M6 ticket: import the constant, or
better, move the tolerance into the task YAML as E15/M12 propose.

### B6 (minor). Unmapped source label values are reported under `geometry_mismatch`
`convert.py:296-303` appends "unmapped label value N (… voxels) dropped" to `problems`;
`convert.py:356` binds that return value to `mismatch` and `:379` reports it as
`geometry_mismatch=`. The message still surfaces, so nothing is lost — but it is filed under
the wrong heading, which matters for §4c below: if ImageCAS-X's "lumen" file turns out to
carry segment values 1..14, the operator gets 800 × 13 messages labelled as geometry
problems. Rename the field, or split the two channels.

### B7 (cosmetic). NaN in a sort key
`evaluate.py:151` sorts `agg.items()` by `kv[1]["dice"]` with no NaN guard, while
`evaluate.py:174` does guard. Inconsistent ordering in the CSV, not wrong numbers.
`cli.py:155-157`'s "no cases found" message still says "Expected one directory per case",
which is no longer the only supported layout.

---

## 4. Decided but unenforced

| Plan decision | Enforced? | Where |
|---|---|---|
| `3d_fullres` | **Yes** | `Dataset710_CoronaryLumen.yaml:55`, `Dataset711:44`; used by `plans.py:204` (preprocess) and `evaluate.py:49` (model folder) |
| No cascade | **Yes, indirectly** | `preprocess` builds only `[task.configuration]` (`plans.py:204`), so no `3d_lowres` data is ever produced; a `3d_lowres` entry in the plans file is inert. Nothing *asserts* patch fraction ≥ 0.25 though — it is an eyeball gate (`docs/TRAINING-PHASE1.md:154`) |
| Native spacing | **Yes** | `config.py:528-538` requires the key explicitly; `plans.py:105-106` omits the override when `None` |
| `max_spacing_mm: 0.5` | **No — warns only** | E1 above |
| `--gpu-mem 70` | **No — unreachable from `scinet prepare`** | E2 above |
| Batch size 2 | **No** | Prose gate only (`docs/TRAINING-PHASE1.md:156` — an empty "Why" cell). `describe_plans` prints it (`plans.py:236`); nothing checks it |
| No mirroring, train **and** test | **No — not in either place** | E3 above |
| Dice+CE baseline | **Yes, by omission** | Trainer overrides nothing loss-related; `plans.py:18-20` records the intent |
| No largest-component post-processing | **Yes, by omission** | `evaluate.py` never calls `nnUNetv2_determine_postprocessing`; `docs/TRAINING-PHASE1.md:208-212` |
| Leakage constraint (§2.2 / `docs/TRAINING-PHASE1.md:43-46`) | **No — prose only** | See below |

### The leakage constraint has no enforcement, and no mechanism to enforce yet
`grep -rn "pretrained\|init_from\|finetune" src/segtrain/` returns **nothing**: there is no
`--pretrained-weights` plumbing, so binary-init fine-tuning cannot be run at all today.
`splits.py:192-206 validate_splits` checks only leakage *within* one task's own
`test` column. Nothing computes the ID intersection between 710's or 711's training pool and
ImageCAS-X's 160 test ids — which is precisely what §2.2 asks for ("Compute and record the ID
intersection so this is a documented fact rather than a trap somebody rediscovers").

The constraint therefore lives in three prose locations
(`docs/TRAINING-PHASE1.md:43-46`, `Dataset711_CoronaryLumenX.yaml:26-30`,
`Proposed changes` §2.2) and nowhere in code. That is a finding, and it is the cheap kind
to fix *before* the init path exists: add `segtrain splits --check-disjoint <other-task>`
that intersects two tasks' `meta.csv` test/train columns and writes the result into the run
directory. Then, when a `--init-from` flag is added, make it refuse unless that check has
been recorded.

### Stratification on dominance and disease status cannot be expressed
`splits.py:130-156 _stratified_folds` stratifies on `CaseMeta.study_type` and nothing else.
`CaseMeta` (`splits.py:45-57`) has five fields — `case_id, split, study_type, institute,
manufacturer` — none of which is dominance or disease status, and `write_meta`
(`index.py:304-309`) writes exactly that fixed header. `build_rows` (`index.py:240,258`)
hardcodes `study_type="ccta"` for **every** case. So on this dataset every case is in one
stratum and `_stratified_folds` degenerates to a seeded round-robin over a shuffled list —
stratification is present in form and a no-op in fact. §2.2's warning that "unstratified
folds can starve L-PDA and L-PLA entirely" applies to the code as it stands.

**What §2.2 *can* already be expressed:** sealing a fixed test set works — pin the 160 ids as
`test` via `index --overrides` (`index.py:262-292`, `build_rows:255`), then
`plan --scheme cv5 --folds 5`; `training_pool` (`splits.py:125-127`) excludes them and
`validate_splits` proves it. ImageCAS Split-1 works the same way via `--scheme official`.

**One trap in the documented run-A recipe:** `docs/TRAINING-PHASE1.md:116-121` shows an
overrides CSV containing only `train` and `test` rows. If all 1000 cases are pinned that way,
`build_splits(scheme="official")` raises — *probe:*
`SplitError: meta.csv contains no 'val' cases; use --scheme cv5 to generate folds instead`
(`splits.py:172-175`). Split-1 is 700/50/250, so the 50 val cases must be pinned too; the
runbook never says so.

### Dataset711 coherence (nobody has downloaded ImageCAS-X)
Structurally `Dataset711_CoronaryLumenX.yaml` is coherent — it reuses `coronary_lumen`,
`spacing: native`, `max_spacing_mm: 0.5`, `3d_fullres`, and `load_task` accepts it
(`tests/test_config.py` passes). Three assumptions are unverified and one is load-bearing:
1. **Layout.** `docs/TRAINING-PHASE1.md:89-91` and `Dataset711:22` both assume
   `--layout flat` with recognised markers. ImageCAS-X's Zenodo archive ships centerlines,
   meshes and descriptors alongside the lumen. If the lumen file's suffix is not in
   `LABEL_MARKERS` (`index.py:72-73` — e.g. `_ann`, `.annotation`, `.lumen`), `scan_flat`
   classifies it as an **image** (`index.py:109-110` takes any unmarked file as the image),
   producing phantom unlabelled "cases" that `summarize` reports as a WARNING
   (`index.py:355-359`) but that still land in `meta.csv`. And if the archive is
   per-case directories containing extra non-image files, `looks_flat`
   (`index.py:118-128`) will call it nested and `find_image` will return `None` for cases
   whose image is not one of `IMAGE_NAMES`, silently dropping them (`index.py:202-203`
   — `continue`, no report).
2. **Label values.** If ImageCAS-X's lumen annotation is actually the 14-class segment
   volume, `remap_multilabel` keeps only value 1 and reports 2..14 as dropped (see B6).
   A `coronary_lumen` model trained on that would learn the left main only. It is reported,
   not silent — but reported under the wrong field name and 800 × 13 times.
3. **No test set until someone writes one.** `Dataset711:50-53` says folds `[0]` and calls
   the 160-case seal "a proposal, not yet a decision", so the sealed test set exists only in
   prose. Until it is pinned in an overrides file, `assign_split`'s hash
   (`index.py:224-232`) will place 15 % of the 800 in `test` — **not** ImageCAS-X's 160 —
   and the comparison to their table (`Dataset711:15-18`) will be against a different test
   set while looking entirely successful.

### The flat-pairing test does not prove what the commit says it proves
`tests/test_index_flat.py:42-53 test_every_image_is_paired_with_its_own_label` asserts that
each returned case's label stem equals its case id. It never constructs the positional
alternative, so it cannot demonstrate the failure it names. And the named failure is
**not real for ImageCAS's uniform naming**: with every image `<id>.img.nii.gz` and every
label `<id>.label.nii.gz`, both sorted lists order identically by id, so `zip`-pairing would
also be correct. Non-zero-padded ids alone are not sufficient.

Positional pairing genuinely breaks in two cases, neither of which this test covers:
- **Mixed marker spellings.** `1_img.nii.gz` sorts *after* `10.img.nii.gz`
  (`_` = 0x5F > `0` = 0x30) while `1.label.nii.gz` sorts *before* `10.label.nii.gz`, so
  case 10's image pairs with case 1's label.
- **Unequal membership** — a missing label shifts every subsequent pair by one. This *is*
  covered, by `test_an_image_with_no_label_still_indexes:93` and
  `test_a_label_with_no_image_is_not_a_case:105`.

The implementation (`index.py:98-115`) is correct; the justification in the commit message
and in the test docstring is not. One real robustness gap remains: both `images` and
`labels` are plain dicts, so two files resolving to the same case id (e.g.
`1.nii.gz` beside `1.img.nii.gz`) **silently overwrite** each other with no report.

---

## 5. Ranked next actions

Each is a ticket with a file and an approach.

1. **Make `convert` read the flat layout.** `src/segtrain/convert.py` +
   `src/segtrain/cli.py::cmd_convert`. Have `cmd_convert` call
   `index.scan(cfg.zenodo_root, layout=...)`, build `{case_id: ScannedCase}`, and pass
   resolved paths into `convert_case` instead of `zenodo_root / case_id`. Add
   `--layout` to the `convert` and `scinet prepare` subparsers, and an integration test
   `index → convert` on a flat tree. **Nothing else on this list matters until this works** —
   phase 1 is currently un-runnable (B1).
2. **Put the patch budget in the task config.** `configs/tasks/*.yaml` gains `gpu_mem: 70`;
   `config.py::TaskConfig` gains the field; `plans.py::plan_experiment` reads it;
   `cli.py --gpu-mem` overrides it. Without this the scripted path trains against an 8 GB
   plan (E2), which invalidates the whole no-heart-crop argument.
3. **Make `max_spacing_mm` refuse.** `plans.py::plan_experiment` — raise on non-empty
   `spacing_warnings()`, with `--allow-coarse-spacing` to override (E1). Two documents
   already claim this behaviour.
4. **Fix the two live metric bugs before any evaluation is run.** `metrics.py:207`
   (sanitise `mean_dice`; B2) and `admin.py:137` (`math.isfinite`). Then `metrics.py:302`
   (B4 — make Dice's denominator and `n_cases_present` agree). These are the items that
   **will silently produce wrong numbers if someone runs an evaluation tomorrow**:
   - B4 produces a wrong per-structure Dice in `test_per_structure.csv` the moment any
     class is predicted where the reference has none. On coronaries that is the normal case.
   - E5/M8 produces a headline mean weighted by class prevalence, which on the 14-class
     schema will read 20-30 points above the macro mean (probe: 28).
   - B2 makes an annotator's dashboard statistic NaN and emits invalid JSON.
   - E1/E2 mean the numbers could come from a model planned at the wrong spacing or the
     wrong patch size, with only a log line to say so.
5. **Add the no-mirror trainer.** New `nnunet_ext/nnUNetTrainer_segtrain_nomirror.py`
   overriding `configure_rotation_dummyDA_mirroring_and_inital_patch_size` and setting
   `inference_allowed_mirroring_axes = None`; validate in `config.py::load_task` that any
   `n_classes > 1` task names it (E3). Do it now, while there is no multiclass checkpoint to
   invalidate — after one exists, this is a retrain.
6. **Headline macro Dice.** `evaluate.py:157-179` — print macro-over-classes labelled as
   such, pooled beside it, and state the NaN policy (E5, and the vault's E19-E21).
7. **`segtrain splits --check-disjoint <other-task>`.** `cli.py` + `splits.py` — intersect
   two tasks' `meta.csv` id sets and write the result into the run directory. Turns the
   leakage constraint from prose into a recorded fact, and is the precondition for any
   `--init-from` flag.
8. **Extend `CaseMeta` and `meta.csv` with stratification columns.** `splits.py:45-57`,
   `index.py:304-309`, `_stratified_folds:130`. Add free-form `strata` (or explicit
   `dominance`, `disease`) fields and stratify on a tuple of them. ImageCAS-X ships the
   scan-level descriptors that populate this (§0), so the data will exist.
9. **Test `hausdorff95` and `agreement()`.** `tests/test_metrics.py` has none. Cover:
   one-sided absence, absent-from-both, the JSON round-trip, and the name→index mapping
   (B3). Then fix M5 with a stated finite bound.
10. **Fix the stale references.** Vault: the nine `Dataset710_Coronary.yaml` citations, the
    dead `src/segtrain/preview.py` evidence line, and `src/segqueue/scoring.py`. Repo:
    `README.md:44` (12.5 % → 25 %), `README.md:49-51` (the run A / run B conflation),
    `configs/dataset.yaml:11-29`, `nnUNetTrainer_segtrain.py:12`, and the TotalSegmentator
    docstrings in `splits.py` / `plans.py` / `evaluate.py` — including
    `splits.py:38 EXPECTED_COUNTS`, which is a live trap.
11. **M1-M4, M7, M9-M14** stand as described; none is contradicted by the code. Sequence
    them after 1-6. M2 (detection outcome / per-class IoU) and M3 (component count) are the
    two the plan's own Evaluation section already promises and cannot currently deliver.

---

## 6. Test-suite result, and what I could not check

**Command:** `PYTHONPATH=src python -m pytest -q` (from the repo root).
**Result:** `1 failed, 486 passed, 41 skipped in 4.83s`.

The single failure is `tests/test_slurm.py:372::test_write_script_is_executable` —
`assert path.stat().st_mode & stat.S_IXUSR` fails on Windows (NTFS has no POSIX exec bit).
Environment-specific, matches the commit message's own account.

Note that a bare `python -m pytest -q` **fails before collection**:
`ImportError while loading conftest ... No module named 'segtrain'`. The package is not
installed in this interpreter and `pyproject.toml` sets no `pythonpath`. Worth a line in
`CONTRIBUTING.md`, or `pythonpath = ["src"]` under `[tool.pytest.ini_options]`.

`mcp__ide__getDiagnostics` returned no diagnostics for any file.

**Could not check:**
- `nnunetv2` is **not installed** in this environment (`ModuleNotFoundError`). Everything
  touching nnU-Net's own behaviour — `plan_experiments`, `preprocess_dataset`,
  `nnUNetPredictor`, the trainer base class — was verified by reading upstream source on
  GitHub `master` rather than by execution. Confirmed that way:
  `lowres_creation_threshold = 0.25`; `gpu_memory_target_in_gb` default `8`;
  mirror axes set in `configure_rotation_dummyDA_mirroring_and_inital_patch_size()` from
  patch size, not from `plans.json`; `inference_allowed_mirroring_axes` persisted in the
  checkpoint. I did **not** verify against the exact pinned tags (`v2.5.1`, `v2.6.2`) the
  vault cites, only `master`.
- Whether `nnUNetTrainer_segtrain.run_training`'s hand-rolled loop still matches the base
  class in the installed nnU-Net version. It is a copy of `run_training`'s body with a
  deadline check; if upstream adds a step, the override silently skips it. Worth a test that
  compares the two, but it needs nnU-Net installed.
- Anything requiring real data: fingerprint output, actual patch fraction, whether the
  anisotropy branch fires, whether ImageCAS-X's files match the assumed markers. The 41
  skipped tests are mostly `needs_data` / `needs_mongo`.
- `scinet check` / `submit` against a real SLURM.
- Vault content outside the files I was asked to read plus every note that cites a repo
  path (found by grep); I did not audit the research notes' scientific claims.

# atlas3: Atlas run 3, the FP-aware loss pilot (Round 8, A24)

> **Finished; kept as the record.** Results: `trillium-results/round7/atlas3/`. The vendored copy of `segtrain`
> this job ran from (`lib/vendor/segtrain`, byte-identical to `src/segtrain` at the time) was removed in #51; to
> re-run, restore it from commit `743fe90`
> (`git checkout 743fe90 -- trillium/atlas3/lib/vendor`). The launcher refuses to start without it.

This is the third Atlas experiment. It follows the contract in `trillium/README.md`: one command, no arguments,
one 1×H100 job of at most 23:50, account `def-aso22`. It never writes to Girder, never needs a password and never
touches a sealed case.

It **reuses run 2** (`./atlas2`, `$SCRATCH/atlas2`) and **run 1** (`./atlas`, `$SCRATCH/atlas`). Nothing is
recomputed that already exists:
- arm B's `checkpoint_final.pth` (the default window, the window R1 will use) is the warm source of both arms;
- dataset 714's preprocessed data is read in place;
- run 1's 80 val reference labels are reused;
- the **80 TotalSegmentator aortas from run 2 are reused, never recomputed** (they took 3.7 h there);
- ImageCAS-X labels come from run 1, centrelines from run 2.

```sh
cd <root>/experiments/atlas3 && ./atlas3     # login node: set up, then submit one job
./atlas3 status
./atlas3 collect                             # results/ back (SUMMARY.md, results.json, small tables)
```

## What runs

**Two arms**, both the A17a warm fine-tune (`src/segtrain/nnunet_ext`, vendored in `lib/vendor/segtrain` for the run, identical
to the repo copy; removed since, see above). Each loads B's checkpoint in full, heads included, and refuses any other plans or normalisation.
LR warms up over 2,500 iterations to a 1e-2 peak, then poly; the coronary invariants hold (window check against B's
[−169, 719], no mirroring, val softmax, A14 refusal).

| Arm | Trainer | Loss |
|---|---|---|
| F0 | `nnUNetTrainer_segtrain_fppilot_F0` | nnU-Net DiceCE (deep supervision) |
| F1 | `nnUNetTrainer_segtrain_fppilot_F1` | the same **plus** λ · mean over voxels > 1.5 mm from any label of −p_fg^γ · log p_bg (λ = 1, γ = 2; full resolution) |

**Pairing (A24.1).** The loss is the only difference between the arms.
- **Same source and same seed** (`SEGTRAIN_SEED`, default 12345).
- **Same data and augmentation stream.** The augmenters are batchgenerators' deterministic
  `MultiThreadedAugmenter` with fixed per-worker seeds, and the case sampler is seeded too. A CPU test shows that F0,
  a second F0 and F1 see bit-identical batches.
- **Equal epochs.** The epoch count is set **once, from the time actually left before training**, for both arms, so
  each poly schedule completes (A22). The budget allows for F1's extra cost (×1.1), two final validations, scoring
  and the report. It is capped at 200. With run 2's measured 175.85 s/epoch, both arms get 200 epochs, about 20.5 h.
- A safety stop per arm leaves time for validation. If an arm pauses, the report says "reported, not decided".

**Scoring.** `segtrain.tf1` at the **pinned A1c hash `24441cf8…5254`**, with the fallback centreline as default
(Round 8). The entry point and the job refuse any other hash. Ostium: A1, from run 2's aortas. Flagged trees are
reported apart (A1b).
- **The FP gate and census** use the same categories as run 2.
- **Per class (A24.3):**
  - recall on ImageCAS-X-traced centreline (within 1 mm of an ImageCAS-X vessel);
  - recall on mask-only low-HU centreline (> 1 mm from ImageCAS-X, smoothed HU < 0.3 × median aortic HU);
  - the A23 contrast-supported tF1.
  - All three use the frozen module's own recall rule (`_recall_keep`, `contrast_supported_tf1`).
- **The schedule:** F0 is scored on the CPU while F1 trains, and F1 afterwards.

## Decision table (A24.2, fixed before the run; `lib/score.py: decide_fp_term`)

Paired F1 − F0 on the 80 val cases.

| FP components per case (case CI) | Decisive tF1 (CI with seed term, SE = √(SE²_case + 0.013²)) | Verdict |
|---|---|---|
| CI does not exclude 0 | — | **not adopted**: no FP reduction detected; R1 runs plain |
| falls, CI < 0 | lower bound > −0.01 | **ADOPT** the FP term for R1 and the waves |
| falls, CI < 0 | upper bound < −0.01 | **not adopted**: tF1 inferior; the trade-off goes to the humans |
| falls, CI < 0 | interval straddles −0.01 | **second seed needed**: both arms again (≈ 20 h) before R1; this also measures σ_seed |
| unequal epochs or a paused arm | — | reported, not decided (A22) |

A single-seed tF1 difference inside ±0.02 is labelled "no difference detected" (A22). MDEs (A19): FP about 0.41
per case; tF1 0.010–0.022 on the case term alone.

## Results (`results/`, < 1 MB, no volumes)

- `SUMMARY.md`, `results.json` (the decision, paired CIs, per-class split).
- `per_case_F0.json`, `per_case_F1.json`; `census_F0.json`, `census_F1.json`.
- Training logs per arm, timings, schedule, the metric hash.

## Tested on CPU here

- **Dry run.** `ATLAS_DRYRUN=1` passed in both case layouts against fake run-1 and run-2 trees.
- **Refusals.** A tampered `tf1.py` is refused, and so is a missing run 2.
- **Job body.** `lib/job_body.sh` ran end to end (`ATLAS3_LOCAL_TEST=1`) with a stub `nnUNetv2_train`:
  - the hash check passed, and both arms got 200 equal epochs from the budget;
  - both arms were scored with the pinned metric, including the recall split and A23 on a real case with CT, aorta
    and ImageCAS-X;
  - the report was written, and the decision table was exercised.
- **The arms themselves** (`tests/test_fppilot.py`, real nnU-Net on CPU, a tiny network and a dataset preprocessed by
  nnU-Net):
  - the FP term acts only on confident voxels beyond the 1.5 mm band, and its gradients stay off the band and the
    tree;
  - F0, F0 again and F1 see identical batches;
  - F1's loss is the FP-aware wrapper and F0's is not.
- **The A17a load** (`tests/test_finetune.py`): heads are kept bitwise.
- **Lint.** `shellcheck` is clean, and so are ruff and pyflakes.

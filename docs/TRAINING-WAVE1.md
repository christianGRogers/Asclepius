# Wave 1: fine-tune icx4 on SegQueue14 reads (task 716)

Round 9 A32 (#85). Wave 1 warm-starts from icx4's checkpoint (Dataset 715, [`trillium/icx4`](../trillium/icx4/README.md))
and fine-tunes it on the team's approved SegQueue14 reads, with the A17 fine-tune trainer. The task is
[`configs/tasks/Dataset716_CoronaryICX4Wave1.yaml`](../configs/tasks/Dataset716_CoronaryICX4Wave1.yaml); its
comments give the reasons, and `tests/test_task_icx4_wave1.py` checks it against icx4's recipe.

> **Status.** These are commands only. Nothing here has been run, and icx4 is still training on Fir.

## What is fixed

| | Value | Enforced by |
|---|---|---|
| Classes | LM 1, LAD 2, LCx 3, RCA 4 (`coronary_icx4`, D25) | the tests, against `src/segqueue14/labels.py` |
| Samples | Each read is its own sample (A11′): `<case>`, `<case>__r2` | `segtrain index` keys the split on the case, so both reads of a case land in the same split |
| Plans | icx4's own plans file, adopted rather than re-planned: 0.5 mm iso, ResEnc 60 GB, 256³ / batch 2, icx4's CT window | `segtrain plan --plans-from` refuses any other plans; the trainer's loader refuses a checkpoint whose plans differ |
| Trainer | `nnUNetTrainer_segtrain_finetune`: full load including the output heads, 2500-iteration warm-up then poly, 250 epochs, mirroring off | the trainer refuses to start from random weights |
| LR arms | `primary` peak 1e-2 (A17a/b); `lr1e3` peak 1e-3 (the pre-registered fallback) | `--arm` |
| ImageCAS seal (A14) | `trillium/sealed_test.json`; an ImageCAS name it can't map (`ImageCAS__0003`) or any other unmappable non-pool name is refused | `convert`, the trainer's sealed check |
| Pool seal (D27) | `configs/segqueue14/sealed-pool-2026-10.json` (150 pool patients + 20 ImageCHD report-only, D32/D33), sha256-pinned | `segtrain.pool_seal`, in `convert` and the trainer |

**Pool reads.** SegQueue14 pool reads (`<Source>__<Case>`, `__r2` for the second read) are training samples
(`pool_reads: true`). They are not ImageCAS cases, so A14 doesn't judge them. The D27 seal does, **by patient**
(`pool_seal.ingest_patient`): a read of any volume of a sealed patient is refused, including a volume added to the
pool after the seal was built. `convert` refuses outright if any read is sealed. `--exclude-sealed-pool` drops them
instead and reports the count. The trainer refuses again, with no exclude mode. `segtrain index` keys a pool read's
split on its patient, so one patient's volumes never straddle train and val. `train` and `scinet submit` load the
seal (checking its hash) before anything is queued, and pass `SEGTRAIN_POOL_SEAL` and `SEGTRAIN_POOL_READS=1` to the
trainer. Running `nnUNetv2_train` directly without them refuses every pool read.

## Commands

On the Girder host, export approved reads, with second reads as `<case>__r2`:

```sh
segqueue14-export --out /srv/segqueue14/export-wave1 --replicas all    # leaves out sealed pool reads, says how many
```

On the cluster (`$SCRATCH/wave1` here), after moving the export there (`segtrain scinet fetch`, or rsync):

```sh
segtrain index   --root $SCRATCH/wave1 --layout nested
segtrain convert --task 716 --zenodo-root $SCRATCH/wave1      # refuses on any A14- or D27-sealed read
segtrain plan    --task 716 --zenodo-root $SCRATCH/wave1 \
                 --plans-from $SCRATCH/icx4/nnunet_preprocessed/Dataset715_ICX4/nnUNetResEncUNetPlans_60G_iso05.json
segtrain preprocess --task 716
```

`plan` copies icx4's plans with only the dataset name changed. It records the source and its sha256 in
`nnUNetResEncUNetPlans_60G_iso05.adopted_from.json`, then writes `splits_final.json` from `meta.csv` (default scheme:
`official`, not `cv5`). It never runs the planner.

Train the primary arm from icx4's final checkpoint:

```sh
ICX4=$SCRATCH/icx4/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0/checkpoint_final.pth
segtrain scinet submit --task 716 --fold 0 --finetune-from $ICX4 --dry-run   # read the script first
segtrain scinet submit --task 716 --fold 0 --finetune-from $ICX4
```

The fallback arm, in its own runs root so the two event streams stay separate:

```sh
segtrain scinet submit --task 716 --fold 0 --arm lr1e3 --finetune-from $ICX4 --runs-root $SCRATCH/runs-lr1e3
```

`segtrain train` takes the same `--arm` and `--finetune-from` flags for a single local or SLURM run. Both set
`SEGTRAIN_FINETUNE_FROM`. They also set `SEGTRAIN_CT_WINDOW` to the adopted plans' window, so the trainer checks icx4's
window rather than the fixed [−300, 1300] HU of task 712. A fresh fine-tune with no `--finetune-from` is refused.
A resumed block (`--continue-training`) restarts from its own checkpoint.

Notes:

- `segtrain status` reads events from the runs root (pass the same `--runs-root` for `lr1e3`). `segtrain evaluate`
  looks only in the primary arm's model folder (`nnUNetTrainer_segtrain_finetune__…`). Score the `lr1e3` model
  from its own folder (`nnUNetTrainer_segtrain_finetune_lr1e3__…`) with `nnUNetv2_predict -tr`.
- Don't also pass nnU-Net's `-pretrained_weights`. It would overwrite the network body after the full load.

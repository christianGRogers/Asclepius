# Bridge — one H100, ≤ 24 h: does structure-aware naming beat the direct model's own names?

```sh
cd <root>/experiments/bridge && ./bridge          # prepare + submit (run from any Trillium login node)
./bridge status                                    # queue, budget used, log tails
./bridge collect                                   # copy results/ back from $SCRATCH when done
```

## What it does

1. **Login node** (internet):
   - builds `$HOME/venvs/bridge_r3`: Alliance torch wheel, nnunetv2 2.8.1, kimimaro, cc3d;
   - finds `cases/` by walking up and prints the layout (`imagecas` or `girder`);
   - fetches the ImageCAS-X label maps (≈ 14 MB range read from Zenodo) into `$SCRATCH/bridge_r3/icx`;
   - submits **one** job: 1 × H100, `--account=def-aso22` (override `ACCOUNT=`), ≤ 24 h, from
     `trig-login01`. The launcher hops there by ssh if started on a CPU login node.
2. **The job** (`job.sh`, all resumable; `$SCRATCH` only):
   - **Proxy labels.** The master plan's territory proxy (Atlas v3 §2.1): ImageCAS-X names on the
     **original ImageCAS mask** (D0), D1 territory, ramus → LCx (D1b). Built for the ImageCAS-X train (560)
     and val (80) lists.
   - **Plan and preprocess.** nnU-Net `3d_fullres` with the **master recipe**: `ResEncUNetPlanner`,
     60 GB target, 0.5 mm isotropic, fixed window [−300, 1300] HU, no mirroring. If the 60 GB plan runs
     out of memory before the first checkpoint, the job re-plans at 40 GB, and the results say so.
   - **Train** on the 560 cases (fold 0 = ImageCAS-X train/val split) until a deadline that leaves 4.5 h,
     about 19.5 h of training. This is a shortened R1 that stops wherever the deadline falls; the epoch
     count is reported.
   - **Predict** the 80 val cases with softmax (`--npz`, nnU-Net's own validation; tile step 0.5, no TTA).
   - **Score four namings of the same predicted lumen** against the proxy reference, by tree-F1 @ 1.5 mm
     (D3), swaps and macro Dice:
     - **D**: the model's own names;
     - **R**: Bridge's rule namer on D's foreground (A7);
     - **H**: grammar decoding of D's softmax (A7 candidate P3b);
     - **O**: oracle names, the headroom bound.
   - Applies the **A7 adoption rule**: paired bootstrap CI of R−D (H−D) above 0, and swap rate no higher.
3. **Results** (`$SCRATCH/bridge_r3/results` → `./bridge collect` → `results/`, < 50 MB):
   - `SUMMARY.md`, `results.json` (per case and per arm);
   - `meta.json` (plan, patch, epochs, hours);
   - nnU-Net training log and progress plot, `plan.txt`, SLURM logs.

## Budget

One job of ≤ 24 h on one H100. A resubmission (after a node failure) only gets what is left of the
24 h; `$SCRATCH/bridge_r3/gpu_seconds` is the ledger. The scoring step runs on the job's 24 cores.

## Tested on CPU (no GPU, no SLURM)

```sh
BRIDGE_DRYRUN=1 BRIDGE_W=/tmp/w BRIDGE_VENV=/path/to/venv BRIDGE_MIN_TRAIN=5 BRIDGE_MIN_VAL=2 \
BRIDGE_EPOCHS=1 BRIDGE_ITERATIONS=2 BRIDGE_TRAIN_HOURS=1 BRIDGE_NCPU=3 ./bridge
```

This runs the identical `job.sh` on a 13-case fake `cases/` tree (Girder layout), with nnU-Net's default
planner at 2 mm on the CPU. Layout detection for the ImageCAS release layout was tested separately
(`python py/cases.py DIR`). `shellcheck bridge job.sh` is clean.

## Limits, stated up front

- **The reference is the proxy, not team labels** (none exist yet; D5). The model is trained on the same
  proxy. All four arms share the lumen, so the comparison is about naming only.
- **The ostium is derived from the reference, not the A1 aorta contact,** so per A9 these numbers are
  provisional. They inform R1's pre-registered D/R/H comparison; they do not replace it.
- **Training is shortened** (~19.5 h vs the master's ~45 h forecast). The model's names may improve with
  more training; the run reports its epoch count, and SUMMARY.md says how to read a positive or a null
  result.

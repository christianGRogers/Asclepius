# atlas — R0 benchmark + short R1 of the master recipe (1 × H100, one 23:50 job)

```sh
cd <root>/experiments/atlas && ./atlas      # login node (trillium-gpu): venv, cases, ImageCAS-X labels, sbatch
./atlas status                              # stages done, job state, log tail
./atlas collect                             # copy $SCRATCH/atlas/results -> ./results (also done by ./atlas when finished)
```

- Account `def-aso22` (override `ACCOUNT=`). `--nodes=1 --gpus-per-node=1 --time=23:50:00`, no partition, no `--mem`,
  submitted from `$SCRATCH/atlas`, all writes under `$SCRATCH/atlas`. Venv `$HOME/atlas-venv` (Alliance torch wheel +
  `nnunetv2==2.8.1`).
- Cases: walks up to `<root>/cases`; ImageCAS (`<n>.img.nii.gz`/`<n>.label.nii.gz`) or Girder
  (`<case>/ct.nii.gz`/`<case>/coronary_arteries.nii.gz`) layout; ImageCAS id n → `c{n-1:04d}`.
- Job stages (idempotent): A proxy labels (ImageCAS mask split, territory, ramus → LCx) + nnU-Net plan/preprocess
  (0.5 mm, 256³, fixed window) → B benchmark at 12/22 loader workers (VRAM, s/epoch, loader wait) → C training for as
  many epochs as fit → D tree-F1 scoring of the 80 val cases → `results/SUMMARY.md`, `results.json`, logs (< 1 MB).
- Re-running never submits a second long job (budget guard via `sacct`).
- Tested on CPU: `ATLAS_DRYRUN=1 SCRATCH=... ATLAS_DRY_ICX=<local icx> ./atlas` and `./atlas selftest`.
Vault note: `vault/Plans/Experiments/Atlas - Pending Trillium run, R0 benchmark and a short R1 scored by tree-F1.md`.

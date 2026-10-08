# Delta — does gap-centred re-inference beat nnU-Net's default inference? (Trillium, 1 × H100, ≤ 24 h)

Run: `cd <root>/experiments/delta && ./delta`. The command takes no arguments. Results land in
`./results/`. To copy them back, run `./delta` again after the job finishes, or run `./delta collect`.

What it does, all inside one job:
1. Builds thick-convention 4-class labels: the ImageCAS mask split by ImageCAS-X names, using the
   territory rule and ramus → LCx. ImageCAS-X is fetched from Zenodo on the login node, 18 MB.
2. Trains one nnU-Net v2.8.1 model on the 640 ImageCAS-X train+val cases. Settings: ResEnc-L planner,
   0.5 mm isotropic, the master's fixed CT window, no mirroring, 250 epochs. The epoch budget is
   deadline-aware and reserves 8 h for evaluation.
3. Predicts the 160 ImageCAS-X test cases at tile step 0.5 (nnU-Net's default) and at 0.75.
   It then adds gap-centred re-inference (P1′), ≤ 3 mm bridging (with and without the support rule),
   and label repair.
4. Scores every variant by tree-F1 @ 1.5 mm against the thick reference. Alongside it records the raw
   FP gate (full volume, before repair) and the bridge audit. Each paired comparison C1–C7 gets a
   bootstrap CI.

Other commands:
- `./delta status` shows progress.
- `./delta dryrun` prints the job script.
- `./delta smoke` is the CPU end-to-end test (5 cases, 1 epoch, 64³ patch, a synthetic cut prediction).

| File | Purpose |
|---|---|
| `delta` | Entry point. It finds `cases/` by walking up from its own directory. On a CPU login node it ssh-es to `trig-login01`. It builds the venv in `$HOME/venvs/delta` once, works under `$SCRATCH/delta_exp`, charges `--account=def-aso22` (`ACCOUNT=` overrides), keeps a walltime ledger, and never resubmits while a `delta_p1` job is queued. |
| `layout.py` | Detects the ImageCAS release layout and the Girder export layout. ImageCAS id n maps to case c{n-1}. |
| `fetch_icx.py` | Fetches ImageCAS-X segmentations and file lists by HTTP range read. |
| `pipeline.py` | The job's steps: prepare, plan, train, evaluate, summarize. Each step is idempotent and resumable. |
| `deltalib.py` | Tree-F1, the ostium rules, blood pool, bridging and its audit, label repair. These are copied from `experiments/Delta/`. |
| `nnUNetTrainerDelta.py` | The trainer: no mirroring, 250 epochs, deadline-aware, and it skips nnU-Net's own final validation. |

Vault note: `vault/Plans/Experiments/Delta - PENDING Trillium run - does gap-centred re-inference beat nnU-Net's default inference on a thick-convention 4-class model.md`.

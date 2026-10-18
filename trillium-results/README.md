# Trillium results

Results returned from the project lead's Trillium runs, exactly as the experiments wrote them
(`./<name> collect`). Each run's `results/SUMMARY.md` is the place to start; the vault notes in
`vault/Plans/Experiments/` interpret them.

| Folder | Returned | Contents |
|---|---|---|
| `round5/` | 2026-10-09, Delta 2026-10-10 | Atlas (R0 + short R1), Bridge (D/R/H/O naming on Atlas's model), Crucible (two-read fusion arms), Delta (P1′, bridging and repair on Atlas's model, open test cases). |
| `round6/` | 2026-10-11 | Atlas run 2 (A1 re-score and FP census of run 1; default-window ablation B; open-36 predictions, volumes on $SCRATCH), Crucible seed 2 (two-read arms, second network seed). |
| `round7/` | 2026-10-12 | Atlas run 3 (FP-aware loss pilot, arms F0/F1); not adopted. |
| `icx14/` | 2026-10-13, job 2 2026-10-15 | The 14-class run: `results/` is the interim check after job 1, `job2/results/` the restart after the resume fix. Cancelled by D25 (four classes again, `trillium/icx4`). |

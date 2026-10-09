# Crucible GPU experiment: training on two reads per case

nnU-Net v2 3d_fullres, no mirroring, 300 epochs x 250 iterations per arm (23.0 s/epoch), patch [96, 160, 160], spacing [0.5, 0.3515625, 0.3515625]. 200 training cases (ImageCAS-X train list), 50 test cases (ImageCAS-X val list). Reads simulated (read model annot_bias; base parameters {'SIG': 2.0, 'R_LO': 0.6, 'R_HI': 1.05, 'P_RAMUS': 0.3, 'P_SIDE': 0.15}). Unfinished arms: none.

| arm | tF1 vs truth | tF1 vs reads (mean of A, B) | Dice vs truth | rooted recall vs truth | precision vs truth | fg volume / truth |
|---|---|---|---|---|---|---|
| single | 0.800 | 0.771 | 0.788 | 0.828 | 0.828 | 1.017 |
| both | 0.830 | 0.789 | 0.805 | 0.856 | 0.846 | 1.014 |
| a11 | 0.822 | 0.754 | 0.805 | 0.850 | 0.835 | 0.999 |
| agree | 0.833 | 0.791 | 0.805 | 0.845 | 0.860 | 0.991 |
| union | 0.815 | 0.746 | 0.805 | 0.846 | 0.835 | 0.996 |
| oracle | 0.825 | 0.778 | 0.810 | 0.856 | 0.849 | 1.024 |

Inter-read ceiling (read B scored against read A): tF1 0.877, Dice 0.909.

Paired differences (per test case, bootstrap 95 % CI); a11-both_vs_T is the decisive comparison:

- both-single_vs_T: +0.030 [+0.010, +0.050], better in 31/50
- both-single_vs_reads: +0.017 [+0.001, +0.036], better in 27/50
- a11-single_vs_T: +0.022 [+0.003, +0.042], better in 32/50
- a11-single_vs_reads: -0.018 [-0.037, +0.005], better in 11/50
- agree-single_vs_T: +0.033 [+0.016, +0.053], better in 39/50
- agree-single_vs_reads: +0.019 [+0.003, +0.039], better in 27/50
- union-single_vs_T: +0.014 [-0.001, +0.031], better in 29/50
- union-single_vs_reads: -0.025 [-0.043, -0.005], better in 8/50
- oracle-single_vs_T: +0.025 [+0.002, +0.048], better in 34/50
- oracle-single_vs_reads: +0.006 [-0.014, +0.028], better in 24/50
- a11-both_vs_T: -0.008 [-0.018, +0.003], better in 14/50
- a11-both_vs_reads: -0.035 [-0.046, -0.023], better in 10/50
- agree-both_vs_T: +0.003 [-0.005, +0.012], better in 26/50
- agree-both_vs_reads: +0.002 [-0.006, +0.011], better in 23/50
- union-both_vs_T: -0.015 [-0.029, -0.004], better in 13/50
- union-both_vs_reads: -0.042 [-0.057, -0.029], better in 7/50

Reading guide: decisive is a11-both_vs_T (does the network fill the ignored carina band under opposite annotator habits?). a11 >= both: A11 stands; a11 < both with CI excluding 0: narrow A11's ignore to cases without habits. "vs reads" differences are expected to be ~0 whatever the truth says (A10 scoring cannot choose a fusion). See vault/Plans/Experiments/Crucible - GPU experiment on training with two reads per case (pending).md for the decision rule.

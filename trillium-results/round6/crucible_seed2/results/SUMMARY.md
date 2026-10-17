# Crucible GPU experiment: training on two reads per case

nnU-Net v2 3d_fullres, no mirroring, 300 epochs x 250 iterations per arm (22.96666666666667 s/epoch), patch [96, 160, 160], spacing [0.5, 0.3515625, 0.3515625]. 200 training cases (ImageCAS-X train list), 50 test cases (ImageCAS-X val list). Reads simulated (read model annot_bias; base parameters {'SIG': 2.0, 'R_LO': 0.6, 'R_HI': 1.05, 'P_RAMUS': 0.3, 'P_SIDE': 0.15}). Unfinished arms: none.

| arm | tF1 vs truth | tF1 vs reads (mean of A, B) | Dice vs truth | rooted recall vs truth | precision vs truth | fg volume / truth |
|---|---|---|---|---|---|---|
| single | 0.805 | 0.779 | 0.792 | 0.828 | 0.841 | 0.996 |
| both | 0.821 | 0.778 | 0.802 | 0.851 | 0.841 | 1.008 |
| a11 | 0.833 | 0.789 | 0.803 | 0.851 | 0.855 | 1.006 |
| agree | 0.827 | 0.785 | 0.801 | 0.849 | 0.846 | 1.003 |
| union | 0.820 | 0.755 | 0.804 | 0.851 | 0.833 | 1.004 |
| oracle | 0.826 | 0.778 | 0.808 | 0.853 | 0.846 | 1.025 |

Inter-read ceiling (read B scored against read A): tF1 0.877, Dice 0.909.

Paired differences (per test case, bootstrap 95 % CI); a11-both_vs_T is the decisive comparison:

- both-single_vs_T: +0.016 [+0.000, +0.033], better in 32/50
- both-single_vs_reads: -0.001 [-0.015, +0.015], better in 26/50
- a11-single_vs_T: +0.028 [+0.012, +0.047], better in 38/50
- a11-single_vs_reads: +0.010 [-0.004, +0.027], better in 25/50
- agree-single_vs_T: +0.022 [+0.007, +0.041], better in 31/50
- agree-single_vs_reads: +0.007 [-0.008, +0.024], better in 26/50
- union-single_vs_T: +0.015 [-0.001, +0.033], better in 26/50
- union-single_vs_reads: -0.023 [-0.038, -0.006], better in 12/50
- oracle-single_vs_T: +0.021 [+0.005, +0.039], better in 33/50
- oracle-single_vs_reads: -0.000 [-0.015, +0.015], better in 19/50
- a11-both_vs_T: +0.012 [+0.000, +0.026], better in 26/50
- a11-both_vs_reads: +0.011 [-0.001, +0.025], better in 28/50
- agree-both_vs_T: +0.007 [-0.005, +0.020], better in 24/50
- agree-both_vs_reads: +0.008 [-0.004, +0.021], better in 24/50
- union-both_vs_T: -0.001 [-0.012, +0.010], better in 21/50
- union-both_vs_reads: -0.022 [-0.034, -0.011], better in 16/50

Reading guide: decisive is a11-both_vs_T (does the network fill the ignored carina band under opposite annotator habits?). a11 >= both: A11 stands; a11 < both with CI excluding 0: narrow A11's ignore to cases without habits. "vs reads" differences are expected to be ~0 whatever the truth says (A10 scoring cannot choose a fusion). See vault/Plans/Experiments/Crucible - GPU experiment on training with two reads per case (pending).md for the decision rule.

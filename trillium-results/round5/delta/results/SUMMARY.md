# Delta Trillium experiment — results

Model: Atlas's master-configuration checkpoint (ResEnc 60 GB plan, 256^3 patch, 0.5 mm iso), inference only. Reference: thick convention (ImageCAS mask split by ImageCAS-X names, territory,
ramus->LCx). Tested on 27 *open* ImageCAS-X test cases; the 100
sealed cases (/scratch/croger/asclepius/experiments/atlas/sealed_test.json) were never predicted. Deciding metric: macro tree-F1 @ 1.5 mm.

## Variants (mean over test cases)

| variant | tF1@1.5 | tF1@0 | rooted@1.5 | macro Dice | FP comps after | bridges (FP joins, cross-tree) |
|---|---|---|---|---|---|---|
| s05:raw | 0.835 | 0.807 | 0.819 | 0.823 | 1.19 |  (, ) |
| s05:raw+bridge3 | 0.835 | 0.826 | 0.822 | 0.823 | 0.74 | 25 (12, 0) |
| s05:raw+repair | 0.835 | 0.807 | 0.819 | 0.822 | 1.19 |  (, ) |
| s05:regap | 0.835 | 0.816 | 0.833 | 0.824 | 1.37 |  (, ) |
| s05:regap+bridge3 | 0.835 | 0.835 | 0.836 | 0.824 | 0.96 | 24 (11, 0) |
| s05:regap+bridge3sup | 0.835 | 0.835 | 0.836 | 0.824 | 1.00 | 22 (10, 0) |
| s05:regap+bridge3sup+repair | 0.835 | 0.835 | 0.836 | 0.823 | 1.00 | 22 (10, 0) |
| s05:regap+repair | 0.835 | 0.816 | 0.833 | 0.823 | 1.37 |  (, ) |
| s075:raw | 0.841 | 0.814 | 0.819 | 0.822 | 1.26 |  (, ) |
| s075:raw+bridge3 | 0.841 | 0.832 | 0.822 | 0.822 | 0.78 | 27 (13, 0) |
| s075:raw+repair | 0.841 | 0.814 | 0.819 | 0.821 | 1.26 |  (, ) |
| s075:regap | 0.842 | 0.823 | 0.833 | 0.823 | 1.52 |  (, ) |
| s075:regap+bridge3 | 0.842 | 0.842 | 0.836 | 0.823 | 1.07 | 24 (12, 0) |
| s075:regap+bridge3sup | 0.842 | 0.842 | 0.836 | 0.823 | 1.11 | 22 (11, 0) |
| s075:regap+bridge3sup+repair | 0.842 | 0.842 | 0.836 | 0.823 | 1.11 | 22 (11, 0) |
| s075:regap+repair | 0.842 | 0.823 | 0.833 | 0.823 | 1.52 |  (, ) |

Decisions use the **27 clean open cases** only (never used in any advocate's development, A14). The 36 declared development cases are reported below for transparency and never decide anything.

## Paired comparisons on the clean open cases (tF1@1.5, per-case difference, bootstrap 95 % CI)

- **C1 tile 0.5 vs 0.75 (raw)**: -0.0064 [-0.0217, +0.0022], n=27, better 2, worse 1
- **C2 P1' on default overlap: s05 regap+bridge3sup vs s05 raw**: +0.0007 [-0.0061, +0.0059], n=27, better 15, worse 9
- **C3 P1' on 0.75 vs default 0.5 raw**: +0.0075 [-0.0050, +0.0253], n=27, better 15, worse 9
- **C4 bridging alone (s05)**: +0.0002 [-0.0012, +0.0019], n=27, better 5, worse 7
- **C5 support rule: s05 regap+bridge3sup vs regap+bridge3**: +0.0001 [-0.0000, +0.0002], n=27, better 1, worse 0
- **C6 label repair (s05 raw)**: +0.0000 [+0.0000, +0.0000], n=27, better 0, worse 0
- **C7 full stage (s05 regap+bridge3sup+repair) vs raw**: +0.0005 [-0.0064, +0.0057], n=27, better 15, worse 9

## Same comparisons, dev (reported only) (n=36)

- C1 tile 0.5 vs 0.75 (raw): +0.0002 [-0.0008, +0.0013], n=36, worse 4
- C2 P1' on default overlap: s05 regap+bridge3sup vs s05 raw: +0.0067 [-0.0039, +0.0225], n=36, worse 18
- C3 P1' on 0.75 vs default 0.5 raw: +0.0073 [-0.0033, +0.0230], n=36, worse 18
- C4 bridging alone (s05): +0.0016 [-0.0006, +0.0048], n=36, worse 7
- C5 support rule: s05 regap+bridge3sup vs regap+bridge3: -0.0001 [-0.0002, +0.0000], n=36, worse 1
- C6 label repair (s05 raw): -0.0000 [-0.0001, +0.0000], n=36, worse 0
- C7 full stage (s05 regap+bridge3sup+repair) vs raw: +0.0067 [-0.0039, +0.0224], n=36, worse 18

## Same comparisons, all open (n=63)

- C1 tile 0.5 vs 0.75 (raw): -0.0026 [-0.0094, +0.0012], n=63, worse 5
- C2 P1' on default overlap: s05 regap+bridge3sup vs s05 raw: +0.0041 [-0.0027, +0.0138], n=63, worse 27
- C3 P1' on 0.75 vs default 0.5 raw: +0.0074 [-0.0016, +0.0189], n=63, worse 27
- C4 bridging alone (s05): +0.0010 [-0.0004, +0.0029], n=63, worse 14
- C5 support rule: s05 regap+bridge3sup vs regap+bridge3: -0.0000 [-0.0001, +0.0001], n=63, worse 1
- C6 label repair (s05 raw): -0.0000 [-0.0000, +0.0000], n=63, worse 0
- C7 full stage (s05 regap+bridge3sup+repair) vs raw: +0.0040 [-0.0028, +0.0137], n=63, worse 27

## Facts (clean open cases)

```
{
 "n_test_cases": 27,
 "n_errors": 0,
 "n_degenerate": 0,
 "cut_cases_rooted15_lt_0_9": 17,
 "fp_gate_raw_mean": 1.1851851851851851,
 "ostium_flagged_trees": 11,
 "reference_trees": 53,
 "mean_gap_sites_s05": 2.185185185185185,
 "per_class_tf1_s05_raw": {
  "1": 0.9287007077512054,
  "2": 0.8660853025477008,
  "3": 0.7740187546386008,
  "4": 0.8021167756688411
 }
}
```

## How to read it

- C1 ~ 0 and C3 <= C2: tile overlap is not the issue; P1' stands or falls on C2.
- C2 CI excluding 0 in favour: adopt P1' (gap-centred re-inference + support-gated bridging).
- C2 CI including 0, or 'worse' > 0 cases: drop P1' (keep nnU-Net default inference).
- C5: the support rule should block FP joins (see bridges column) without losing tF1.
- cut_cases: how often the master-class model cuts trees on the decided thick convention.

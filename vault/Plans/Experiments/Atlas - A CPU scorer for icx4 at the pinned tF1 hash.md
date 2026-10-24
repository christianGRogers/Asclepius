---
aliases: [Atlas R9 scorer]
tags: [plans, experiment, round9, implementation, tf1, icx4, sealed-test]
author: Atlas
round: 9
status: done (self-tested; awaits icx4 predictions)
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
---

# A CPU scorer for icx4 at the pinned tF1 hash, and a zero-code seal of the sealed test

**Why.**

- icx4 reports Dice only (`trillium/icx4/lib/score.py`). The master decides by tF1 at 1.5 mm with the A1 aorta
  ostium, at the frozen A1c hash.
- As written, icx4 also scores all 160 ImageCAS-X test cases, including the 80 sealed under A14 (Echo, #49).

[[Atlas v11]] needs both fixed for the first Fir run, without editing icx4: the lead's code, built for D25, already
tested on Trillium.

## 1. `experiments/Atlas/r9_seal_icx_test.py`: the sealed 80 never reach icx4's scorer

**Status: fallback only.** PR #66 (`role:swe`, for #55/#54, opened while this was written) puts a sealed filter into
icx4 itself, adds the in-job tF1 on the 80 open cases, and adds `ICX4_WORK`. Use this script **only if #66 has not
merged** when the lead starts. #66's launcher refuses a test split that is not exactly 80 + 36 + 44, so the two must
never be combined (restore with `mv test.full.txt test.txt`). §2's scorer is still needed with #66: #66 scores the
open test cases, while decisions and the seed pairing use the **val 80**.

`prepare.py` builds `splits.json`'s "test" list from ImageCAS-X's `test.txt`, and `score.py` scores that list. The
script rewrites `test.txt` without the 80 sealed IDs, keeping `test.full.txt` as a backup. It runs **before**
`./icx4`; `fetch_icx.py` skips files that exist, so the edit survives.

It refuses (exit 2) if:
- a sealed case is in train or val;
- the sealed list does not have 80 cases;
- the result is not exactly the 80 open test cases of `trillium/sealed_test.json` (36 clean + 44 development).

`--fetch` downloads only the four filelists from the Zenodo zip by HTTP range requests, using the standard library
only, so it runs on a bare login node.

**Tested.**
- Self-test: 160 → 80; running it twice gives the same result; a planted leak in val is refused.
- On the real Zenodo filelists (fetched with `--fetch` in this sandbox, 2026-10-18): 160 → 80, train 560 and val 80
  unchanged, and the backup is identical to the `test.txt` icx4's own fetcher downloads.

Training is untouched. icx4 still **predicts** all 1000 cases (the hand-off needs them) but never scores a sealed one.

## 2. `experiments/Atlas/r9_score_icx4.py`: the decisive score

For each case in the 80 val (`splits.json`) and/or the 36 clean open test cases (`sealed_test.json`):

- **Prediction:** `predictions/<case>.nii.gz`, uint8 on the CT grid.
- **Reference:** ImageCAS-X collapsed by `trillium/icx4/lib/territory.py`, the same code icx4 trains on (D8, D25).
- **Metric:** `segtrain.tf1.tree_f1` with the A1 aorta (run 2's `<case>_aorta.nii.gz`). The case is provisional
  without an aorta (A1a); flagged trees are reported apart (A1b).
- **Also reported:** `fp_components` (the A2 gate, raw) and per-class Dice.
- **Summary:** decisive macro tF1 with a case-bootstrap CI, per-class tF1, FP/case and Dice.
- **`--pair DIR2` (Job B):** the paired difference with a case CI and a seed-inclusive CI (A22, prior σ 0.013),
  and the one-pair estimate σ̂_seed = √(max(d² − SE²_case, 0)/2).

**Guards.**
- It refuses unless `src/segtrain/tf1.py` has sha256 `24441cf8…5254` (A1c, Round 8).
- It refuses any sealed case (ImageCAS-X or quality-0).

**Self-test** (`--selftest`, on the `tests/test_tf1.py` fixture geometry: LM → LAD + LCx, a tapering RCA, an aorta
box):

| Check | Result |
|---|---|
| Perfect prediction | tF1 1.0, 0 FP, not provisional |
| 3 mm cut across the LAD | LAD tF1 0.40, RCA 1.0 |
| LCx named LAD | LCx tF1 0.0 |
| One off-tree blob | 1 FP component |
| No aorta | provisional |
| End to end | NIfTI files through `territory.py` (ImageCAS-X value 9 → RCA), pairing (run 2 worse) and the sealed refusal all as expected |

**Cost.** tF1 on one real case was about 20–60 s per core in rounds 5–8, so 116 cases × 2 runs is about 2 core-h on
a login node, or about 15 min with 10 workers.

**Not included.** The A23 contrast-supported extent diagnostic (it needs CT HU and is report-only) and the A1b
review lists. Both are added when pool reads arrive.

## Round 10 update (#86): one implementation, so A26 holds by construction

Round 9's A26 requires the val-80 scorer to reproduce the in-job `tf1_per_case.json` on open-36, per case and per
class. The Round 9 version of `r9_score_icx4.py` could not:

- it gave `find_ostia` no CT, so the `pool_thick` cross-check rule (and therefore the A1b flags) differed from the
  job's;
- it flagged whole cases rather than classes;
- it did not crop as the job does.

Since #86, `r9_score_icx4.py` **calls icx4's own `lib/tf1_score.score_case`**, which uses the same crop, ostium
rules, flag rule and frozen `lib/segtrain_tf1.py`, with the CT from icx4's `layout.json`. It summarises with icx4's
own `report.tf1_summary`, so the decisive macro has the same definition. It still chooses only non-sealed cases and
adds Dice (report only). Its command line is unchanged; `--layout` defaults to the `layout.json` beside
`--splits`.

- **Self-test:** its rows equal the in-job function's on identical inputs, through a JSON round trip.
- **The reading of its output** (A26, A27, A29, A15) is
  `experiments/Atlas/r10_read_icx4.py` (template `experiments/Atlas/r10_icx4_results_template.md`); the result is [[icx4 - Results]].

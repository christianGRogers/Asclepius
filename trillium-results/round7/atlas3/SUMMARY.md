# Atlas run 3: the FP-aware loss pilot (Round 8, A24)

Generated 2026-10-12 09:16:53. Machine-readable: `results.json`; per case: `per_case_F0.json`, `per_case_F1.json`; FP components: `census_F0.json`, `census_F1.json`.

Metric: `segtrain.tf1` sha256 `24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254` (pinned: True); fallback centreline default; A1 ostium from atlas2's TotalSegmentator aortas. Both arms: warm from run 2's B (default window), A17a trainer, seed 12345, same data stream, 200 epochs each.

| arm | epochs | decisive macro tF1 | LM / LAD / LCx / RCA (unflagged) | FP comps / case (≤ 1) | confident_other | FP term first → last |
|---|---|---|---|---|---|---|
| F0 | 200 | 0.891 | 0.948 / 0.896 / 0.841 / 0.875 | 1.31 (53/80) | 83 | n/a → n/a |
| F1 | 200 | 0.895 | 0.959 / 0.901 / 0.846 / 0.882 | 1.27 (49/80) | 84 | 0.0001 → 0.0001 |

## Decision (A24.2, fixed before the run)

Paired F1 − F0 on 80 cases: decisive tF1 0.0047, case CI -0.0032..0.0136, **seed-inclusive CI -0.0222..0.0315** (σ_seed 0.013); FP -0.037 per case, CI -0.350..0.263. Single-seed label: no difference detected.

**Verdict: not adopted: no FP reduction detected** — FP CI does not exclude 0; R1 runs plain.

## Per class, alongside (A24.3; report only)

| class | recall, ImageCAS-X-traced F0 → F1 (Δ, CI) | recall, mask-only low-HU F0 → F1 (Δ, CI) | A23 contrast-supported tF1 F0 → F1 (Δ, CI) |
|---|---|---|---|
| LM | 0.952 → 0.980 (0.027, 0.001..0.067) | 0.341 → 0.205 (-0.136, -0.136..-0.136) | 0.923 → 0.959 (0.036, -0.002..0.083) |
| LAD | 0.932 → 0.957 (0.025, -0.005..0.064) | 0.374 → 0.381 (0.007, -0.057..0.072) | 0.914 → 0.944 (0.030, 0.002..0.068) |
| LCx | 0.898 → 0.929 (0.031, -0.001..0.071) | 0.280 → 0.306 (0.025, -0.011..0.063) | 0.870 → 0.887 (0.017, -0.009..0.050) |
| RCA | 0.909 → 0.920 (0.011, -0.002..0.027) | 0.615 → 0.621 (0.006, -0.027..0.040) | 0.887 → 0.895 (0.008, -0.001..0.017) |

Reading: `vault/Plans/Experiments/Atlas - Pending Trillium run 3, the FP-aware loss pilot.md`.

---
tags: [plans, implementation, branch-labelling, A4, A7, A8, D1, D1b]
author: Bridge
round: implementation
updated: 2026-10-09
---

# Implementation of namer: the frozen rule namer as `segtrain.namer` (A4, A7, A8)

`src/segtrain/namer.py` is the frozen rule-based branch namer from the experiment, packaged as a library.

- The source is `experiments/Bridge/label.py` (md5 06f53291…) plus the skeleton step from `extract.py`.
- It needs only numpy and scipy.
- Its tests are `tests/test_namer.py`: 18 tests on synthetic tubes, about 9 s, with no case data.
- On all 163 unsealed ImageCAS-X cases it reproduces the experiment's run, case for case (see Validation below).

## Public API

| Function | Returns | Used by |
|---|---|---|
| `name_tree(mask, affine, *, ramus="LCx", bridge_mm=4.0)` | `NamingResult`: uint8 labels 0..4, `Decisions`, `ramus_candidates` mask, `info` (components, tree lengths, bridge joins for the audit) | A4 QA, A7 renaming |
| `rename(labels4, affine, **kw)` | `NamingResult` naming the foreground of a 4-class prediction; its own names are discarded | A7 "R" |
| `extract_decisions(labels4, affine)` | `Decisions` read from any 4-class labelling: ostium, LM end, left and right components, fused flag | A11/A12 decision comparison |
| `compare(reference, named, affine, *, ostium_mm=5, lm_dice_min=0.5, swap_max=0.05, ramus_candidates=None, ramus_share=0.8)` | `Disagreement` (see below) | A4, A11 |
| `disagreement(label, mask, spacing_or_affine)` | A dict with `ignore`, `exclude`, `ramus_only`, `flags`, `reason`, `report`, `decisions` | The contract `segtrain.proxy.qa_with_namer` calls |
| `as_affine(x)` | A 4×4 affine; a bare 3-vector of spacings is read as LAS | |
| `icx_to_four(icx)` | The ImageCAS-X 14 classes mapped to 4 (territory; IM → LCx; Other → 0) | |

`Decisions` holds:

- `ostium_vox`, `lm_end_vox`, `lm_length_mm`;
- `left_component`, `right_component`;
- `n_ramus`, `fused_trees`;
- `failure`: one of `empty`, `no_tree`, `single_tree`, `no_bifurcation`.

`Disagreement` holds:

- `ignore`: voxels that both labellings call vessel but name differently;
- `ignore_fraction`;
- `ignore_within_10mm_of_carina`;
- `ostium_distance_mm`, `lm_dice`, `lad_lcx_swap`, `tree_swap`;
- `flags`: from `ostium`, `lm`, `swap`, `tree`;
- `ramus_only`, `wholesale`.

## What was ported, and how faithfully

- **The naming rules are unchanged.** The port keeps:
  - left/right separation by RAS x centroid;
  - the learned ostium score (weights from `ostium_w_dev2.json`) with the top-5 plausibility re-rank;
  - the `apsplit` LM-bifurcation search within 40 mm;
  - LAD as the anterior child;
  - subtree inheritance (D1 territory);
  - the A8 ramus switch, defaulting to LCx (D1b);
  - 4 mm naming bridges, graph only;
  - voxels taking the class of their nearest skeleton vertex in the same component.
  - All constants are the frozen ones.
- **The skeleton is TEASAR re-implemented in scipy** (`_teasar`). kimimaro is not a pipeline dependency, so it could not be imported. The port follows kimimaro's `trace` as the experiment called it:
  - parameters: scale 1.5, const 2 mm, pdrf_scale 1e5, exponent 4, `fix_branching`, dust 100, `fix_borders`;
  - root: the geodesically farthest voxel from the first voxel in Fortran order, or a border target;
  - PDRF = 1e5·(1 − DBF/max^1.01)^4 + DAF/max(DAF);
  - each path is a Dijkstra "railroad" from the valid voxel with the largest DAF to the skeleton so far (rails cost nothing);
  - invalidation is a flood inside a ball of 1.5·r + 2 mm around each path voxel. The flood passes only through voxels that were valid before the path, and only from path voxels that were still valid. I checked these semantics against `skeletontricks.roll_invalidation_ball_inside_component` on probe volumes.
- **Agreement with kimimaro** on real masks:
  - c0000: identical vertex, endpoint and junction counts; the median distance between vertices is 0, and the 95th percentile is 0.38 mm.
  - c0128 and c0329: within 1–6 extra 0.6–3 mm surface spurs (tie-breaking order).
  - `test_skeleton_matches_kimimaro_teasar` checks this wherever kimimaro is installed, and is skipped elsewhere.
- **Cost:** about 18 s per case (39 s at most) and about 0.8 GB RSS. The tests' 80³ volumes take under 1 s.

### A first attempt that failed (kept as a record)

The first port used scikit-image `skeletonize` with an MST, spur pruning, ring contraction and endpoint extension. It lost 5–7 cases out of 67–72 against the frozen run. The causes were:

- the left main pruned as a spur, because skimage endpoints stop ~5 mm inside a fat ostium;
- rings at fat bifurcations;
- junctions split a few mm apart;
- a 4 mm bridge fusing the left and right trees.

Each workaround fixed one case and moved others. Re-implementing TEASAR removed the whole class of problem.

## Validation against the experiment's run

Same 163 unsealed cases, the same projection (nearest ImageCAS-X voxel within 2 mm, territory, IM → LCx) and the same scoring as `summ_d1b.py`. The frozen numbers are the per-case results in `ev_r3_LCx.jsonl`. The 9 sealed cases are skipped (A14).

| Set | n | Fully right (all four Dice ≥ 0.8), port / frozen | Swap (any class < 0.5), port / frozen | Mean Dice LM / LAD / LCx / RCA (port) |
|---|---|---|---|---|
| dev (devset3) | 96 | 0.917 / 0.917 | 0.062 / 0.062 | 0.928 / 0.980 / 0.945 / 0.989 |
| held-out, unsealed | 67 | 0.866 / 0.866 | 0.090 / 0.090 | 0.908 / 0.974 / 0.936 / 0.985 |
| all | 163 | 0.896 / 0.896 | 0.074 / 0.074 | 0.920 / 0.977 / 0.941 / 0.988 |

- The two runs fail on exactly the same cases.
- The ostium is identical (< 0.5 mm) in 97.5 % of cases. It differs by more than 5 mm in one case (c0479), whose outcome is unchanged.
- The per-class Dice difference has a median of 0.000 and a 95th percentile of 0.0035.
- The 88.2 % held-out figure in [[Bridge - Under the binding ramus rule the namer gets 88 percent of unseen thick-mask cases fully right]] used 76 cases. Nine of them are now sealed, so the comparable unsealed figure is 0.866 (n = 67).
- The end-to-end A7 result ([[Bridge - On real stage-1 output, the two-stage namer is within 0.01-0.03 tree-F1 of perfect naming]]) was **not re-run**. Those are ImageCAS-X test cases, and most of them are now sealed. Skeleton equivalence is the evidence that it carries over.
- Scripts are in my scratch: `nt/validate.py`, `nt/summ.py`, `nt/cmpk.py` (the comparison with kimimaro).

## Deviations and how the spec's gaps were resolved

1. **Orientation.** Atlas's first contract passed the spacing only. Every ImageCAS mask is stored LAS (all 1000 checked), so `as_affine` reads a bare spacing as diag(−sx, sy, sz). A RAS assumption would swap the left and right trees. Atlas's `proxy.py` now passes the NIfTI affine.
2. **The `ignore` mask** covers naming differences only (both labellings call the voxel vessel). Extent differences are kept, as A11 says.
   - `exclude` (A4) is `wholesale`: any of `ostium` > 5 mm, LM Dice < 0.5, LAD↔LCx swap > 5 %, or a tree exchange.
   - The ramus exemption applies when ≥ 80 % of the swapped voxels lie in the namer's ramus-candidate region: side branches ≥ 10 mm leaving the LAD or LCx within 10 mm of the carina, plus the switched ramus.
   - Under the exemption a swap is not wholesale. `disagreement()['ramus_only']` is set only when the swap was the *only* trigger, so a case with a ramus swap *and* an ostium error is still excluded.
3. **The A12 "decision vs diffuse" split** is approximated by `ignore_within_10mm_of_carina`, together with the per-decision flags. A finer attribution, along the lines of the five-decision note, is not built.
4. **A kept quirk.** In the frozen ostium score, the 'beyond' feature is about 1.0 for every endpoint except the tree's vertex 0, the lexicographically smallest skeleton vertex. That endpoint gets a sizeable bonus whenever it is an endpoint. The port keeps the same vertex order and the quirk, because the weights were fit with it. The test fixtures keep their smallest-x vertex mid-vessel so the quirk is not what they test.
5. **The bridge guard and feature clipping** that the skimage attempt needed were removed. The bridges are exactly the frozen rule: an endpoint within 4 mm of any vertex of another component.

## Suggested CLI (for the orchestrator)

- `segtrain name MASK OUT [--ramus LCx|LAD|inherit] [--bridge-mm 4] [--json decisions.json]` would wrap `name_tree`: it writes labels with the mask's affine, plus the decisions and bridge joins as JSON.
- `segtrain name-qa LABEL MASK [--json]` would wrap `disagreement`.

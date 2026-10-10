---
tags: [plans, implementation, metrics, tree-f1, ostium]
author: Delta
round: implementation
updated: 2026-10-10
---

# Implementation of tf1: one tree-F1 for the whole project (A9, A1, A2)

`src/segtrain/tf1.py` holds the deciding metric. Its tests are in `tests/test_tf1.py`: 23 tests that take about 10 s on synthetic tubes, with no case data. Before this module, four copies existed: `experiments/Delta/perturb_metrics.py`, `trillium/delta/deltalib.py`, `trillium/atlas/lib/tf1.py` and `trillium/bridge/py/tf1.py`. They now count as experiment code only.

## Public API (stable; Crucible and Atlas import it)

| Function | Returns | What it is |
|---|---|---|
| `tree_f1(reference, prediction, spacing, *, tol_mm=1.5, ostia=None, aorta=None, ct=None, min_component_voxels=100)` | `TreeF1` | `.tf1` (macro), `.per_class`, `.recall`, `.precision`, `.rooted_fraction`, `.ostia`, `.provisional`, `.flagged`, `.as_row()` |
| `find_ostia(reference, spacing, *, aorta=None, ct=None)` | `OstiumReport` | One `Ostium` per reference tree component, with the rule of record, every rule's candidate, `disagreement_mm` and `flagged` |
| `fp_components(reference, prediction, *, threshold=0.5, min_voxels=100)` | int | The A2 gate, read on the raw prediction |
| `raw_prediction(prediction, threshold=0.5, min_voxels=100)` | label map | A probability map is thresholded; components under 100 voxels are dropped; no other change |
| `audit_bridges(reference, before, after, bridges, spacing)` | `BridgeAudit` | One row per join: orphan size, `touches_reference` (no means an FP join), `cross_tree`, and off-reference voxels added. The FP count is given both before and after bridging |
| `components`, `remove_small_components`, `blood_pool` | | Helpers (26-connectivity; small components dropped, never keep-largest) |

Constants: `TOLERANCE_MM=1.5` (D3), `AORTA_CONTACT_MM=5`, `DISAGREEMENT_MM=5`, `MIN_COMPONENT_VOXELS=100`, `MIN_TREE_VOXELS=1000`.

## What was ported

- **Tree-F1.** The definition is the one in deltalib, perturb_metrics and Atlas's copy:
  - Grow the prediction by a tol/2 ball and take 26-connected components.
  - Recall for class c is the reference class-c centreline that is predicted as c and lies in a component that reaches an ostium.
  - Precision for class c is the predicted class-c centreline that lies inside reference class c.
  - tF1 is the macro mean over the classes present in the reference.
- **Ostium rules.** `thick` and `pool_thick` come from *Delta - Two cheap ostium rules find 116 of 116 true ostia*, applied per component (`RefTree`). The aorta-contact rule comes from `ostium_eval_cc.py`.
- **Gate and audit.** These come from deltalib `fp_components` / `audit`, which follow *Delta - Real bridging on 17 nnU-Net predictions…*.

## Deviations from the experiment code

1. **Libraries.** scipy `ndimage.label` replaces cc3d, and a small CSR graph with BFS replaces networkx. The results are identical on the fixtures. No new dependencies were added.
2. **Ostium matching.** A component is rooted when any of its predicted voxels lies within max(tol, largest voxel side) of the ostium. This is Atlas's rule. deltalib and Bridge's copy required the ostium voxel itself to lie inside the grown prediction, which penalises a prediction that stops a voxel short of the ostium tip. The two rules agree whenever the prediction covers the ostium (regression tests). A test pins the tip case.
3. **The aorta rule is the rule of record.** It picks the centreline voxel nearest the aorta, of any degree, if that voxel is within 5 mm. With an aorta mask, a component that holds both trees gets one ostium per side (`Ostium.side`). If a tree does not touch the aorta, it falls back to `thick` and is **flagged**, never scored silently.
   - *Revised in Round 5.* The first version took the thickest endpoint within 5 mm. On the thick reference the ostium is often not an endpoint, so that version scored c0038 and c0560 wrong without flagging them. See [[Delta - On the thick reference the cheap ostium rules miss 1 in 8 ostia silently, which made 13 of the 17 cut trees]].
   - Two tests pin the new behaviour: a pass-through ostium, and joined left and right trees.
4. **Rule disagreement.** Every pair of rules is compared. Before, only thick and pool were compared.
5. **No ostium given.** Without an aorta mask, the result is `provisional=True`. With neither an aorta mask nor a CT, there is no cross-check at all.
6. **Small components.** `tree_f1` always drops predicted components under 100 voxels, as Atlas's copy does. deltalib left this to the caller.
7. **Empty reference.** The score is NaN, where earlier copies gave a dict or 0. An empty prediction scores 0.

## Regression

The regression tests compare six predictions at tol 0 and 1.5: identity, a 4 mm cut, a 1 mm gap, a cut LM, a swapped LAD/LCx and a lost LCx. The new module's tF1, per-class values and FP count match Atlas's copy to within 1e-9. Its tF1 and FP count match deltalib and Bridge's `score`, and its ostia match deltalib's `RefTree.roots`. The tF1 values are 1.0, 0.9, 0.996 (0.9 at tol 0), 0.35, 0.5 and 0.75. The deltalib and Bridge comparisons are skipped if cc3d or networkx is absent.

perturb_metrics was not loaded directly, because it hard-codes a path to `treelib`. deltalib is its Trillium port and shares its definition.

## Ambiguities resolved

- **The "connected to the ostium" tolerance.** The spec does not say how close a component must come to the ostium. The rule is max(tol, voxel), which is Atlas's choice.
- **A left tree split into components** (no LM). Each component gets its own ostium. Atlas's copy gave a single left root, chosen per class set.
- **Bridge-audit format.** The audit takes the dict format that deltalib `bridge()` already emits (`p`, `q`, `gap_mm`).

## Open questions

- scikit-image (`skeletonize`) is not in `pyproject` `dependencies`. It is imported lazily and arrives with nnunetv2, but `segtrain evaluate` on a laptop would need it, so it should be added to the core dependencies.
- CLI wiring is left to the orchestrator (`cli.py` is not owned here).

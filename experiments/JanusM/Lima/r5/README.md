# Lima, Round 5 (path `jm/rest-ccta`, #223)

**Candidate:** `vault/JanusM/Candidates/Lima v4.md`.

CPU only: analytic phantoms, with no case and no image. Each script still calls `janusm.guard.refuse(...)` first, on
an empty list, so that it fails closed if the guard's pins are broken. Run the scripts from the repository root; they
add `src/` themselves. Shipped code is not changed: the band variants are defined here and passed in as `roi=`, and
`validate_bias_estimator` is called with `H.ja37_band` patched for that one call and then restored.

| File | #223 item | What |
|---|---|---|
| `e1_open_base_remedy.py` → `e1_open_base_remedy.json` | 2 | Four bands — shipped, the #219 remedy as worded ("literal"), a cut-cap-only reading ("cap_plane") and a base slab ("slab") — on India's open E6 phantom and on `validate_bias_estimator(open_base=True)` at its defaults. It also runs the E4 closed shells (both borders) and records how much band each variant keeps on `H.phantom()`. Takes ≈ 35 min. |
| `e2_la_capped_heart.py` → `e2_la_capped_heart.json` | 2 (control) | The same four bands on `H.phantom()`, whose base opens into the LA: two grids × three walls × two offsets × both borders × ±0.3 / ±0.5 mm, against the exact shift. Takes ≈ 5 min. |

India's phantom and its truth come from `tests/test_janusm_harness.py` (`_e6_phantom`, `_e6_labels`, `_e6_truth`).
They are imported unchanged.

**Note:** `vault/JanusM/Experiments/Lima - The open-base remedy as worded empties the epicardial band, while a
cut-cap-only band passes and the shipped band already passes where the base meets the LA.md`.

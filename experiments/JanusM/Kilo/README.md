# Kilo (Janus-M Round 1): experiment code

Plan: `vault/JanusM/Candidates/Kilo v1.md`. Notes: `vault/JanusM/Experiments/Kilo - E0 …`, `Kilo - E1-E3 …`.

| File | What |
|---|---|
| `heldout.py` | Every TotalSegmentator id in a held-out list (pool seal, pool list, reserve, every r10 D35 draw, ImageCAS-X seal); refuses them in code |
| `fetch_ts_cardiac.py` | Public TotalSegmentator v1 cardiac cases by HTTP range (Zenodo 6802614, CC BY 4.0), held-out ids refused first |
| `layers.py` | The computed layers: Laplace transmural depth, thirds, thickness, AHA 17 segments |
| `exp_layers.py`, `summarise.py` | E1–E3; `results_e123_grid05.json`, `summary_e123_grid05.json` |
| `allowed_volumes.py` → `allowed_volumes.json` | E0: the Girder volumes Janus-M may use (by patient, via `segtrain.pool_seal`) |
| `make_seal.py` → `janusm_seal_proposal.json` | The proposed 20-patient Janus-M seal |
| `fir/m0_inputs.py`, `fir/m0_geometry.py` | Job M0 for the lead (Kilo v1 §8) |
| `citations.md` | The citation check |

Reproduce E1–E3 (CPU, ~100 min on 4 cores, ~2 GB download):
`python fetch_ts_cardiac.py DATA 40 && python exp_layers.py DATA/Totalsegmentator_dataset out.json --reps 2 --jobs 4 && python summarise.py out.json`

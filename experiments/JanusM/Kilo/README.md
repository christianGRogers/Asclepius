# Kilo (Janus-M): experiment code

Round 1 plan: `vault/JanusM/Candidates/Kilo v1.md`. Notes: `vault/JanusM/Experiments/Kilo - E0 …`, `Kilo - E1-E3 …`.
Round 2 (path `jm/paired-scar`): `vault/JanusM/Candidates/Kilo v2.md`. Notes: `Kilo - E4 …`, `Kilo - E5 …`, `Kilo - E6 …`.

| File | What |
|---|---|
| `heldout.py` | Every TotalSegmentator id in a held-out list (pool seal, pool list, reserve, every r10 D35 draw, ImageCAS-X seal); refuses them in code. Round 2: `refused_with_twins` / `check_public` add the JA12 twin rule (same sex and institute, age ±5 y, any study type) |
| `fetch_ts_cardiac.py` | Public TotalSegmentator v1 cardiac cases by HTTP range (Zenodo 6802614, CC BY 4.0), held-out ids and JA12 twins refused first |
| `layers.py` | The computed layers: Laplace transmural depth, thirds, thickness, AHA 17 segments |
| `exp_layers.py`, `summarise.py` | E1–E3; `results_e123_grid05.json`, `summary_e123_grid05.json` |
| `allowed_volumes.py` → `allowed_volumes.json` | E0: the Girder volumes Janus-M may use (by patient, via `segtrain.pool_seal`) |
| `make_seal.py` → `janusm_seal_proposal.json` | The proposed 20-patient Janus-M seal |
| `fir/m0_inputs.py`, `fir/m0_geometry.py` | Job M0 for the lead (Kilo v1 §8) |
| `citations.md` | The citation check |

Reproduce E1–E3 (CPU, ~100 min on 4 cores, ~2 GB download):
`python fetch_ts_cardiac.py DATA 40 && python exp_layers.py DATA/Totalsegmentator_dataset out.json --reps 2 --jobs 4 && python summarise.py out.json`

## Round 2 (path `jm/paired-scar`)

| File | What |
|---|---|
| `e4_twins.py` → `results_e4_twins.json` | E4: the JA12 twin rule on TotalSegmentator v1 `meta.csv` (16 held out, 624 twins, 18 open cardiac) |
| `e5_lie_registration.py` → `results_e5_lie_registration.json` | E5: first-pass → synthetic LIE registration (none / rigid / affine / heart-masked rigid / + B-spline) and scar grading inside the registered wall |
| `e6_power.py` → `results_e6_power.json` | E6: paired CT–LGE cohort size for segment-level scar presence and transmurality agreement (simulation, no image) |

Reproduce (CPU; E5 about 40 min on 4 cores, 225 MB download):
```sh
python fetch_ts_cardiac.py DATA 100          # refuses held-out and twins; fetches the 18 open cardiac cases
python e4_twins.py DATA/Totalsegmentator_dataset/../meta.csv results_e4_twins.json   # or any copy of meta.csv
python e5_lie_registration.py DATA/Totalsegmentator_dataset results_e5_lie_registration.json --jobs 4 --reps 3 --meta META_CSV
python e6_power.py results_e6_power.json --sims 200 --boot 200
```
`meta.csv` is `Totalsegmentator_dataset/meta.csv` inside the Zenodo zip (read by `fetch_ts_cardiac.py`; save a copy with
`remotezip` to pass as `--meta`).

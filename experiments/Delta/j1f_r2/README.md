# Delta, track 1-F round 2 (#303)

CPU only, labels only. The 720 non-sealed ImageCAS-X label files were fetched with `../j1f_r1/fetch_allowed.py`
(skips every sealed case before any byte is read). No CT, no model output, no sealed case.

| File | What |
|---|---|
| `gate_sim.py <j1f_r1> <out.json> [min_mm]` | False-fail rate of the B gates for a human-level reader (ImageCAS-X Table 1), and power against bad models, on the locked 100's reference branches. `gate_sim.log` (5 mm), `gate_sim_3mm.log` |
| `branch_score.py` | The branch scorer of record (presence, detection, naming, branch tF1, SegQueue's contact collapse) |
| `test_branch_score.py <icx>` | Its self-test on 6 hash-chosen training cases (`test_branch_score.log`: 31/31 PASS) |
| `label_checks.py <icx> <census.json> <out.json> [n]` | (1) SegQueue 0.20.0's `collapse_to_four` vs ImageCAS-X's L-/R- origin labels on all 720; (2) the stage-2 band on n training cases |
| `summarise_checks.py <label_checks.json> <out.md>` | `label_checks_summary.md` |
| `d35_yield.py` | Binomial yield of a held-out extended-read set (`d35_yield.txt`) |

Plan: `vault/Plans/Candidates/Janus 1-F/Delta v2.md`.

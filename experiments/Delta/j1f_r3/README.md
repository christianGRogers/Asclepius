# Delta, track 1-F round 3 (#303)

CPU only. Labels of the D45 620 training cases only (fetched with `experiments/Atlas/j1f_r2/fetch_620.py`, which checks
every member name against the 620 before reading it). No locked-100 label, no sealed or quality-0 case, no CT, no model
output. Plan: `vault/Plans/Candidates/Janus 1-F/Delta v3.md`.

| File | What | Run |
|---|---|---|
| `j1f_scorer.py` | Scorer of record (F-A16): Atlas's r2 scorer with SegQueue's collapse imported and pinned | `python j1f_scorer.py selftest` |
| `j1f_labels.py` | Converter of record (F-A18): D47 (A) hard-wired, F-A3's ignore rule | `python j1f_labels.py selftest` |
| `j1f_gates.json` | F-A15's lines, pinned to the scorer's sha256 | — |
| `j1f_gate.py` | Applies the gate file; the OM2 0.59 / 0.61 test | `python j1f_gate.py selftest` |
| `test_j1f_scorer.py` | Delta r2's checks ported + additions, on six training cases | `python test_j1f_scorer.py <icx620> <split_j1l.json>` → `test_j1f_scorer.log` |
| `j1f_decode.py` | Decode F / T (F-A19), within-group maps (T_L), parent copy, `splits_final` (F-A20), chunk loop | `python j1f_decode.py selftest` |
| `plans_check.py` | L-A21's plans check pinned to Step T's hashes, `batch_dice` False | `python plans_check.py selftest` |
| `splits_final_j1f.json` | train 620, val = the 20 fit-check cases | — |
| `npz_size.py` | One case's `--save_probabilities` npz, estimated | `python npz_size.py <icx620> <split_j1l.json>` → `npz_size.json` |
| `census620.py` | One pass over the 620: converter counts, collapse check, scorer pieces, stage-2 stand-ins | `python census620.py <icx620> <split_j1l.json> <out.jsonl> 4` |
| `summarise_census.py` | → `census620_summary.json` (§1.3, §1.4, §5 of the candidate) | `python summarise_census.py <out.jsonl (sorted)> ../../Atlas/j1f_r2/census_r2.jsonl census620_summary.json` |
| `census620.jsonl.gz` | The per-case census (labels-derived counts and lengths only) | — |
| `gate_sim_on_census620.json`, `.out` | Atlas's `gate_sim.py` re-run on this census (sorted by case): byte-identical to `../../Atlas/j1f_r2/gate_sim.json` and `.out` | `python ../../Atlas/j1f_r2/gate_sim.py <census620.jsonl> gate_sim_on_census620.json` |

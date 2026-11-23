# Bridge, Janus 1-F Round 3 (#303)

These are the CPU experiments behind
[`Bridge v3`](../../../vault/Plans/Candidates/Janus%201-F/Bridge%20v3.md).

- Only the 620 Janus 1 training cases of D45 are read (fetched by `../j1f_r2/fetch_seg620.py`, Zenodo
  10.5281/zenodo.21887809, CC BY 4.0). Every script re-checks a case is in `train620`.
- No locked-100, sealed, quality-0 or D60 label or CT is opened, and no model output exists here.
- Nothing ran on Fir, SciNet or Trillium.

| File | What | Run |
|---|---|---|
| `j1f_scorer.py` | The scorer of record (F-A16, F-A17): Atlas's round-2 file with SegQueue's `collapse_to_four`, the converter removed, and `load_gates` / `aggregate` / `verdict` added. sha256 `7e6875a3…ff78` | `python3 j1f_scorer.py selftest` |
| `configs/j1f_gates.json` | F-A15's lines, `k_of_6`, `presence_mm`, `tol_mm`. sha256 `16ce8954…1b6b` | — |
| `test_gates.py` | OM2 recall 0.59 fails, 0.60/0.61 pass; each of 18 lines bites 0.01 below; refusals | `python3 test_gates.py` |
| `test_scorer_cases.py` → `test_scorer_cases.out` | Delta's 31 checks + Atlas's perturbations on Delta's six training cases | `python3 test_scorer_cases.py $W` (~20 min) |
| `run620.py`, `summarise620.py` → `run620_summary.json` | The scorer on all 620 references vs Atlas's `census_r2.jsonl` | `python3 run620.py $W $W/run620.jsonl 3` (~90 min on 3 cores), then `python3 summarise620.py $W/run620.jsonl > run620_summary.json` |
| `decode_ref.py` → `decode_ref.out` | Reference decode F / T (F-A19) and `splits_final.json` (F-A20), with self-tests; the fit-check 20 | `python3 decode_ref.py selftest $W` |
| `npz_size.py` → `npz_size.out` | Disk per locked case for `--save_probabilities` (13 channels, float32) | `python3 npz_size.py $W c0519 32` |
| `stage2_sim.py`, `summarise_stage2.py` → `stage2_summary.json` | F-A22's L1, L2, K1 on a simulated correct stage-2 model over 120 training cases | `python3 stage2_sim.py $W $W/stage2_sim.jsonl 120 1` (~70 min), then `python3 summarise_stage2.py $W/stage2_sim.jsonl > stage2_summary.json` |

`$W` is the folder `fetch_seg620.py` wrote (it holds `split.json` and `segmentations/`). The scripts import Atlas's
round-2 `stage1_labels` for references (the converter the gate census used); the scorer itself has no converter.

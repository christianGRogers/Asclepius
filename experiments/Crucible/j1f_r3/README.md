# Crucible, Janus 1-F round 3

Evidence for [[Crucible v3]] (vault/Plans/Candidates/Janus 1-F/Crucible v3.md). Training labels only (the 620,
fetched by `../j1f_r2/fetch620.py`); no CT, no locked/sealed/quality-0 label, no model output, nothing on a cluster.

| File | Run | What |
|---|---|---|
| `j1f_scorer.py` | `python j1f_scorer.py selftest` | the scorer of record: Atlas r2 + SegQueue's collapse + aggregate/verdict |
| `j1f_gates.json` | — | F-A15's lines; copy byte-identically to `configs/janus1/j1f_gates.json` |
| `test_gates.py` | `python test_gates.py` | OM2 0.59 fails / 0.61 passes, tamper refusal (`test_gates.log`) |
| `test_scorer.py` | `python test_scorer.py <icx620>` | Delta's checks on his six training cases (`test_scorer.log`) |
| `decode_ref.py` | `python decode_ref.py selftest` | F, name maps, T, T_L, splits_final (`decode_ref.log`) |
| `pass620.py` | `python pass620.py <icx620> <out.jsonl> 4` | one pass over the 620 (≈ 25 s/case/core) |
| `summarise.py` | `python summarise.py <out.jsonl> summary620.json` | §1.3 and §5 of the candidate |
| `npz_size.py` | `python npz_size.py <icx620>` | one 13-class npz's size (`npz_size.out`) |

`<icx620>` is the folder `fetch620.py` fills (it also writes `split.json` there).

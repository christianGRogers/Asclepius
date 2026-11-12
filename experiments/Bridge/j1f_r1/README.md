# Bridge, Janus 1-F Round 1 (#303)

CPU experiments for [`Bridge v1`](../../../vault/Plans/Candidates/Janus%201-F/Bridge%20v1.md). Only the 620 Janus 1
training cases of D45 are read; no locked-100, sealed or quality-0 label is fetched.

| File | What |
|---|---|
| `split620.py`, `split_d45.json` | D45's 620/100 split rebuilt from `trillium/sealed_test.json` and ImageCAS-X's file lists |
| `fetch620.py` | Downloads ImageCAS-X labels (Zenodo 10.5281/zenodo.21887809) for the 620 only |
| `census.py` → `census_620.jsonl` | Per case: class volume, length, diameter; branch parent and origin along the parent |
| `analyse.py` → `census_summary.json` | Census, "Other" sides, ordinal order and re-derivation, dominance, Wilson widths |
| `icx14_emergence.py` → `icx14_emergence.json` | When each class first appeared in the cancelled 14-class run |
| `test_j1f_r1.py` | Synthetic self-tests (`python3 test_j1f_r1.py`) |

```sh
python3 fetch620.py $W ../../../trillium/sealed_test.json      # ~40 MB
python3 census.py $W $W/census.jsonl 4                          # ~25 min on 4 cores
python3 analyse.py $W/census.jsonl census_summary.json
python3 icx14_emergence.py ../../.. icx14_emergence.json
```

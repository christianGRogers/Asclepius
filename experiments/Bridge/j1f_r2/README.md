# Bridge, Janus 1-F Round 2 (#303)

These are the CPU experiments behind
[`Bridge v2`](../../../vault/Plans/Candidates/Janus%201-F/Bridge%20v2.md).

- Only the 620 Janus 1 training cases of D45 are read.
- No locked-100, sealed or quality-0 label is fetched.
- `gate_sim.py` reads no data at all: it uses ImageCAS-X's published Table 1 and the locked-100 label counts (F-A7).

| File | What |
|---|---|
| `gate_sim.py` → `gate_sim.json` | Item 1: how often B's gate lines fail a human-level reader, ruled vs proposed lines |
| `untraced_yield.py` → `untraced_yield.json` | Item 6: expected yield of each untraced class on D35's 35 patients |
| `fetch_seg620.py` | Fetches ImageCAS-X labels for the 620 (Zenodo 10.5281/zenodo.21887809) by range requests, plus `Descriptors.xlsx` |
| `census_r2.py` → `census_r2.jsonl` | Per case: SegQueue's D47 contact rule vs ImageCAS-X's side; the background released by stage-2 bands at 4/8/15 mm; unnamed trunk twigs |
| `summarise_r2.py` → `census_r2_summary.json` | Medians and counts over the 620 |
| `test_j1f_r2.py` | Synthetic self-tests (`python3 test_j1f_r2.py`) |

```sh
python3 gate_sim.py > gate_sim.json                                   # seconds
python3 untraced_yield.py > untraced_yield.json
python3 fetch_seg620.py $W ../../../trillium/sealed_test.json 3       # range requests, ~45 MB
python3 census_r2.py $W $W/census_r2.jsonl 2                          # ~30 s per case per core
python3 summarise_r2.py $W/census_r2.jsonl census_r2_summary.json
```

**Note on `census_r2.py`:** a few large cases need about 1 GB each for the 15 mm band.
- With 4 processes, a worker killed for lack of memory hangs `Pool.imap`.
- The script resumes from finished cases, so re-run it with 2 processes if that happens.

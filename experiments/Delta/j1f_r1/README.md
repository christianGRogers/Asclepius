# Delta, track 1-F round 1 (#303)

CPU only, labels only. No sealed case is downloaded (`fetch_allowed.py` skips them before fetching) or opened.

| File | What |
|---|---|
| `fetch_allowed.py <dir>` | ImageCAS-X filelists + the 720 non-sealed segmentations from Zenodo (HTTP range requests) |
| `split_d45.py <dir> split_d45.json` | D45's 620 / 100 recomputed from ids; matches the 1-L L-A1 list pins |
| `census.py <dir> census.json` | per-class presence, volume, pieces, centreline length, radius; "Other" sides; unnamed side branches in LAD/LCx/RCA |
| `ordinal.py <dir> census.json ordinal.json` | geodesic attachment order of D1/D2, OM1/OM2 and "Other" pieces |
| `j1f_labels.py <dir> census.json j1f_labels.json [--left-pda lcx\|name]` | ImageCAS-X -> 1-F stage-1 labels (13 values) and the check against `trillium/icx4/lib/territory.py` |
| `parent_copy.py` | parent-copy head initialisation + self-test (`parent_copy_selftest.log`) |
| `summary.py census.json ordinal.json > summary.md` | the tables in the vault note |

Note: `vault/Plans/Experiments/Delta - Janus 1-F, ImageCAS-X traced 12 of 1-F's 18 classes, numbers its branches in strict order, and leaves the other six as background.md`.
Plan: `vault/Plans/Candidates/Janus 1-F/Delta v1.md`.

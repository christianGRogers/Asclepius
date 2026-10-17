# CCTA-Pool tooling

One-off data collection for the 2026-10 CCTA sourcing (D17-D23): fetch public cardiac
CT datasets, convert them, and upload them to the Girder collection `CCTA-Pool`; then
reorganise Girder (D22), quality-check every volume, and make the TotalSegmentator seed
masks that SegQueue14 serves (D23). Results and decisions are in
`vault/Research/Datasets and benchmarks/CCTA sourcing 2026-10/`.

| File | What it does |
|---|---|
| `ccta_ingest.py` | Shared Girder client: convert, light QC, dedupe, upload into `CCTA-Pool/<dataset>/<case>/` (1 MB chunks) |
| `ingest_open.py`, `ingest_idc.py`, `ingest_totalseg.py`, `ingest_aicup.py`, `round3/` | Per-source download and ingest |
| `approx_hu.py` | Approximate HU for the two sets released without it (HOCM, Figshare) |
| `reorganise_girder.py` | D22: ImageCAS-X collection, CT-only `SegQueue/cases`, human-readable names |
| `qc_render.py` | Six-panel QC picture and measurements for one volume |
| `totalseg_cpu.py` | D23: TotalSegmentator `coronary_arteries` seed masks into `SegQueue/seeds-totalseg` |

Run against Girder with `GIRDER_TOKEN_FILE=<file holding a token>`; never commit a token.
Not linted (`pyproject.toml`): one-off code, judged by what it produced.

# Lima (Janus-M Round 2, path `jm/rest-ccta`)

Candidate: `vault/JanusM/Candidates/Lima v1.md`. Notes: `vault/JanusM/Experiments/Lima - *.md`.

| File | What |
|---|---|
| `heldout.py` | Guard: refuses the 16 held-out TotalSegmentator patients and every JA12 twin, before any file of a subject is requested |
| `twins.py` → `twins.json` | E1: the JA12 twin rule on the public `meta.csv` files (metadata only; held-out ids stored as a hash) |
| `fetch_ts.py` | Fetches the 23 allowed public cardiac subjects (CT + 5 heart masks) by range reads, after the guard |
| `harness.py` → `e2_summary.json` (`summarise_e2.py`) | E2: the shared border-error harness; Round 1's four models plus Lima's, against realised ASSD |
| `calibrate_sim.py` → `calibrate_sim.json` | E3: calibrating Stage A thinning without a scar reference (simulation) |
| `lima_geom.py` | The read-out: thickness, halves, AHA frame (fixed and arc sectors), ET / Laplace / Yezzi-Prince depth, half-maximum offsets, guarded TPR, fat clusters, Euclidean and geodesic territories |
| `local_check.py` → `local_check_summary.json` (`summarise.py`) | Self-test of `lima_geom` on the 23 allowed public hearts (1.5 mm labels; synthetic coronaries) |
| `fir/jm0b_readout.py` | Job JM-0b for the lead: the same read-out on Job JM-0's 40 ImageCAS-X cases; guard refuses sealed, test, non-train and Janus-M seal/decision cases |

Images and `meta.csv` stay in a scratch folder and are never committed. Uses Kilo's `layers.aha17` (in `harness.py`
only, to place STA's virtual scars).

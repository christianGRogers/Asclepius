# Hotel, Janus-M Round 2 (path `jm/rest-ccta`)

Candidate: `vault/JanusM/Candidates/Hotel v2.md`. Notes: `vault/JanusM/Experiments/Hotel - *.md` (round 2).

| Script | What | Output | Opens images? |
|---|---|---|---|
| `../guard_r2.py` | Held-out guard (all JA12 categories + TotalSegmentator twin rule); every script below calls it first | stdout | no |
| `e1_twins.py V1_META V2_META OUT` | E1: twin rule on both public TotalSegmentator `meta.csv` files; Round 1 overlap | `e1_twins.json` | no (metadata only) |
| `e1_chance.py V1_META OUT` | E1b: are exact matches more than chance? | `e1_chance.json` | no |
| `e2_harness.py OUT` | E2: Round 1 error models replayed (Part A) + shared harness at 0.5 mm (Part B) | `e2_harness.json` | no (phantom) |
| `e3_tpr.py OUT` | E3: rest TPR vs edge width, guard band, wall, border error | `e3_tpr.json` | no (1-D model) |
| `e5_depth.py OUT` | E5: equal thickness vs Yezzi-Prince vs raw Laplace | `e5_depth.json` | no (phantom) |
| `summarise_r2.py OUT` | Tables for the notes, and E4 (repeatability floor) | `summary.json` | no |
| `fir/halfmax_tpr_m0.py` | Job JM-0 CPU add-on for the lead (Hotel v2 §7) | aggregate JSON | ImageCAS-X train JM-0 cases only, after the guard |

The `meta.csv` files come from Zenodo 6802614 (v1) and 10047292 (v2.0.1) by HTTP range request
(`remotezip`), e.g. `RemoteZip(url).extract('Totalsegmentator_dataset/meta.csv')`; they are not committed.

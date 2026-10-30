# Hotel, Janus-M Round 4 (path `jm/rest-ccta`, #205)

Candidate: `vault/JanusM/Candidates/Hotel v4.md`. Note: `vault/JanusM/Experiments/Hotel - Lima's 45 percent and
Hotel's 35 percent differ by the wall the F1 floor is measured against, and R9 never passes the measured wall.md`.
No case is opened: each script simulates, and calls `janusm.guard.refuse([])` first by rule.

| Script | What | Output |
|---|---|---|
| `e8_e5_vs_e7.py OUT [--seeds N]` | E8: Lima E5's 45 % vs Hotel E7's 35 % decomposed on S3 (`janusm.calibrate`), one seed, every F1 on the same hearts; a wall sweep; Lima's own design at 5 seeds | `e8_e5_vs_e7.json` (run with `--seeds 3`) |
| `e9_r9_median.py OUT` | E9: what `jm0r_decide.py` R9 prints for a JM-0R wall median, as shipped and with the median passed through | `e9_r9_median.json` |

Run from the repository root with the package installed (`pip install -e .`). E8 takes about 15 minutes on one CPU,
E9 about 5.

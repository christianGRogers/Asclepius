# Hotel, Janus-M Round 3 (path `jm/rest-ccta`)

Candidate: `vault/JanusM/Candidates/Hotel v3.md`. Notes: `vault/JanusM/Experiments/Hotel - *` (round 3).
Nothing here opens a case; every script is an analytic phantom, a simulation, or reads aggregate JSON only.

| Script | What | Output |
|---|---|---|
| `e6_estimators.py OUT [--quick]` | E6: ASSD / signed-bias / thickness estimators vs a known truth (India's and Lima's functions imported unchanged) | `e6_estimators.json` |
| `summarise_e6.py OUT` | E6 pass rule (fixed before the run) and tables | `e6_summary.json` |
| `e7_detectable.py OUT [--inputs JSON]` | E7: Lima's rule C (imported unchanged) with measured cv_n and shape; detectable depth; F1 floor | `e7_detectable.json` |
| `jm0r_decide.py --jm0r F` (or `--juliet/--lima/--india/--hotel`) | The pre-registered decision procedure for JM-0 / JM-0R outputs (Hotel v3 §6); runs when the lead posts them | stdout, `--out` |

E7's default inputs are Lima's guarded self-test summary (`experiments/JanusM/Lima/local_check_summary.json`);
when the lead posts JM-0R, rerun with `--inputs <JM-0R aggregate>`.

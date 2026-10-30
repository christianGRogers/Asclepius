# Lima, Round 4 (path `jm/rest-ccta`, #205)

Candidate: `vault/JanusM/Candidates/Lima v3.md`. CPU only: simulations and analytic phantoms, no case and no image.
Each script still calls `janusm.guard.refuse(...)` first, on an empty list, so that it fails closed if the
guard's pins are broken. Run from the repository root; the scripts add `src/` themselves.

| File | #205 item | What |
|---|---|---|
| `e6_depth_decomposition.py` → `e6_depth_decomposition.json` | 2 | E5's 45 % against E7's 35 % on one seed with the shipped `janusm.calibrate`: a 2 × 2 × 2 × 2 factorial (median, σ_m, F1 floor, F1 deviation), E5's own function on 20 seeds, and JA40's function at four medians on five seeds (≈ 1 min) |
| `e7_pp_tolerance.py` → `e7_pp_tolerance.json` | 6 | The raw pp ASSD / bias errors on the 72 conditions of `test_e6_pp_within_ja39_tolerances` (≈ 2 min) |
| `dryrun_selftest_decisions.json` | 7 | `jm0r_decide.py --lima ../local_check_summary.json`: a **dry run** on Lima's R2 self-test aggregate (23 public hearts), not JM-0R. Shows R3 rejecting the 9.668 mm median that R9 uses by default |

Notes: `vault/JanusM/Experiments/Lima - E5's 45 percent and E7's 35 percent differ because F1's 1 mm floor is read
against a 9.7 mm wall in one and a 5.7 mm wall in the other.md` and `… The shipped point-to-plane ASSD meets JA39 at
0.035 mm, not 0.03, and a strict 0.03 fails two conditions.md`.

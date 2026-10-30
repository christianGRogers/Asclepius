# Hotel, Janus-M Round 5 (path `jm/rest-ccta`, #223)

Candidate: `vault/JanusM/Candidates/Hotel v5.md`. No case is opened. The script builds synthetic phantoms only, and it
calls `janusm.guard.refuse([])` first by rule. Shipped code is only called, never changed. Every band variant is built
inside the script.

| Script | What | Output |
|---|---|---|
| `e11_open_base_remedy.py OUT [--quick]` | E11: R4-S4's open-base check repeated with the #219 engineer's remedy (`literal`) and two label-only narrowings (`rim15`, `plane`), on three phantoms: India's open-base E6 phantom (A), the cut capsule of `validate_bias_estimator(open_base=True)` (B), and a read-like `harness.phantom()` with a 60° outflow opening (C) | `e11_open_base_remedy.json` (full run: two grids, three offsets) |

Run it from the repository root, with the package installed (`pip install -e .`). The full run takes about 9 minutes
on one CPU; `--quick` takes about 3 minutes.

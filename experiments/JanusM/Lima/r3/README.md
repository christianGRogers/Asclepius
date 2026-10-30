# Lima, Round 3 (path `jm/rest-ccta`, #167)

Candidate: `vault/JanusM/Candidates/Lima v2.md`. Every script calls `janusm.guard.refuse(...)` before it opens a
case (JA22). Run with `PYTHONPATH=src` from the repository root, or from here (the scripts add `src/` themselves).

| File | Ruling §7 item | What |
|---|---|---|
| `apply_r2_rules.py` | 1 | The pre-registered JM-0 / JM-0R decisions, applied to an aggregate JSON; `QUANTITIES` is the JM-0R output schema for #169 |
| `e4_estimators.py` → `e4.json`, `e4_sdf_rule.json` | 2 | ASSD, signed-bias and thickness checked against exact spheres and the 23 guard-allowed real walls; what the harness shift rule realises |
| `e5_ja18.py` → `e5_ja18.json` | 3 | Lima E3 under the full JA18 rule (rule C + F1 + gate), with the measured `cv_n` and shape; κ vs ICC vs detectable-depth gates; composite null; the page line |

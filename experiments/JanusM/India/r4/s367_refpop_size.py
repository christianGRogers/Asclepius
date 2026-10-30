"""India R4 (#205 item 3): what 60 more reference cases (420 vs 360) would buy, on simulation.

Part 1 (ids only, counts printed): the derived population is 360, and janusm.guard refuses each
of the 60 seal-extension cases under purpose "any" (no file but the committed lists is read).
Part 2 (synthetic): rule C fitted by janusm.reference.rule_c_fit on Lima's population (JA40
settings, cv_n 0.088, 9.668 mm) of n = 360 and n = 420, 40 seeds each; the spread of the cut's k
and the false-flag rate it realises on a fresh null population of 20 000.

    python experiments/JanusM/India/r4/s367_refpop_size.py   # writes s367_refpop_size.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))
from janusm import calibrate as C  # noqa: E402
from janusm import guard, sealed_r1  # noqa: E402
from janusm import reference as R  # noqa: E402

OUT = Path(__file__).with_suffix(".json")


def ids_part():
    cases = R.derive_cases()
    R.refuse_cases(cases)  # the shipped S6 guard: passes on the derived 360
    ext = sorted(sealed_r1.load().seal_extension)
    refused = 0
    for c in ext:
        try:
            guard.refuse([c], what="India r4 count check", source=guard.ICX_SOURCE,
                         purpose=guard.ANY)
        except guard.HeldOutError:
            refused += 1
    seal_ok = 0
    for c in ext:
        try:
            guard.refuse([c], what="India r4 count check", source=guard.ICX_SOURCE,
                         purpose=guard.SEAL_SCORING)
            seal_ok += 1
        except guard.HeldOutError:
            pass
    return {"derived_reference_population": len(cases), "seal_extension": len(ext),
            "extension_refused_purpose_any": refused,
            "extension_allowed_purpose_seal_scoring": seal_ok}


def fit_once(n, seed):
    rng = np.random.default_rng(seed)
    meas, *_ = C.population(n, 0.1, 0.3, 0.088, 0.0, C.PHASE_MIX, rng, median_mm=9.668)
    fit = R.rule_c_fit(meas, seed + 1)
    # realised false-flag rate on fresh healthy hearts, scored with the fitted shape/scale/cut
    r2 = np.random.default_rng(seed + 2)
    null, *_ = C.population(20000, 0.0, 0.0, 0.088, 0.0, C.PHASE_MIX, r2, median_mm=9.668)
    rel = null / np.median(null, 1, keepdims=True)
    z = (rel - np.asarray(fit["shape"])) / np.asarray(fit["scale"])
    ff = float(C.territory_flags(z < fit["cut"]).any(1).mean())
    return fit["k"], ff, fit["cv_n"]


def main():
    out = {"ids": ids_part(), "sim": {}}
    for n in (360, 420):
        ks, ffs, cvs = zip(*[fit_once(n, 1000 + 10 * s) for s in range(40)])
        out["sim"][str(n)] = {
            "k_mean": round(float(np.mean(ks)), 3), "k_sd": round(float(np.std(ks, ddof=1)), 3),
            "false_flag_mean": round(float(np.mean(ffs)), 4),
            "false_flag_sd": round(float(np.std(ffs, ddof=1)), 4),
            "false_flag_p95": round(float(np.percentile(ffs, 95)), 4),
            "cv_n_sd": round(float(np.std(cvs, ddof=1)), 4)}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

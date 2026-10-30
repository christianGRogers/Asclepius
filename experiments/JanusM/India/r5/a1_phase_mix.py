"""India R5, item 3 of #223: does S3 take JA60's hypoattenuation mix, ``{"ED": 1.0}``?

#217's engineer recorded that ``calibrate.population`` raises on a phase_mix that omits phases.
JA60 rules that hypoattenuation is simulated with ``phase_mix = {"ED": 1.0}``, and calibrate's
own docstring says the same. This calls S3 with that mix and with the three-key mix that
``reference.HYPO_PHASE_MIX`` passes. Simulation only; no case is opened.

Run from the repo root:  python experiments/JanusM/India/r5/a1_phase_mix.py
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))

from janusm import calibrate as C  # noqa: E402
from janusm import guard  # noqa: E402


def attempt(fn, *a, **k):
    try:
        return {"ok": True, "value": fn(*a, **k)}
    except Exception as e:  # recorded, not raised
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def main():
    guard.refuse([], what="India R5 a1 phase mix (simulation; no case opened)")
    kw = dict(seed=31000, measured_median_mm=6.3)
    out = {
        "calibrate_version": C.CALIBRATE_VERSION,
        "population_factor_ED_only": attempt(C.population_factor, {"ED": 1.0}, C.LIMA_SHAPE,
                                             0.088),
        "detectable_depth_ED_only": attempt(C.detectable_depth, 0.088, C.LIMA_SHAPE, 1.0,
                                            phase_mix={"ED": 1.0}, **kw),
        "detectable_depth_ED_full_keys": attempt(C.detectable_depth, 0.088, C.LIMA_SHAPE, 1.0,
                                                 phase_mix={"ED": 1.0, "MD": 0.0, "SYS": 0.0},
                                                 **kw),
    }
    for k in ("detectable_depth_ED_only", "detectable_depth_ED_full_keys"):
        v = out[k].get("value")
        if isinstance(v, dict):
            out[k]["value"] = {kk: v[kk] for kk in ("depth",) if kk in v} or str(v)[:200]
    out = json.loads(json.dumps(out, default=str))
    pathlib.Path(__file__).with_suffix(".json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

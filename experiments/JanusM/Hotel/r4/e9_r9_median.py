"""E9 (Round 4, #205 items 1-2, 7): what R9 prints for a given JM-0R wall median, as shipped and
with the median passed through.

Simulation and aggregate inputs only: no case is opened. ``janusm.guard.refuse([])`` is called first
by rule; it names nothing.

As shipped, ``jm0r_decide.decide`` calls ``detectable_depth(cv_n, shape, rc, sig_m=, seed=)`` and never
passes ``thickness_median_mm``, so every JM-0R result is simulated on S3's default wall
(``median_mm`` = 9.668 mm). And ``population`` multiplies ``median_mm`` by the phase factor (1.00 /
1.14 / 1.40, mix 40 / 40 / 20) and the segment shape, so the simulated hearts' median wall is
``K`` x ``median_mm`` (``K`` measured here). A measured JM-0R median M therefore enters as
``median_mm = M / K``.

    python experiments/JanusM/Hotel/r4/e9_r9_median.py OUT_JSON
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments" / "JanusM" / "fir"))

import jm0r_decide as D  # noqa: E402

from janusm import calibrate as C  # noqa: E402
from janusm.guard import refuse  # noqa: E402


def inflation(median_mm=5.7, n=20000, seed=0):
    """K: the simulated hearts' median wall over ``median_mm`` (no thinning)."""
    meas, *_ = C.population(n, 0.0, 0.0, C.LIMA_CV_N, 0.0, C.PHASE_MIX,
                            np.random.default_rng(seed), median_mm=median_mm)
    return float(np.median(np.median(meas, 1)) / median_mm)


def main():
    out_path = Path(sys.argv[1])
    refuse([], what="E9 (simulation; no case)")
    k = inflation()
    rows = []
    for m in (4.2, 5.0, 6.0, 7.0, 8.0, 9.668):
        x = {"cv_n": C.LIMA_CV_N, "segment_shape": list(C.LIMA_SHAPE), "thickness_median_mm": m}
        shipped = {r["rule"]: r for r in D.decide(x)}["R9"]["depth"]
        passed = C.detectable_depth(C.LIMA_CV_N, C.LIMA_SHAPE, D.F1_FLOOR_MM,
                                    seed=D.DEPTH_SEED, median_mm=m / k)["depth"]
        rows.append({"jm0r_thickness_median_mm": m, "r9_as_shipped": shipped,
                     "r9_median_passed": passed, "r3_window_holds":
                     D.THICK_WINDOW[0] <= m <= D.THICK_WINDOW[1]})
        print(rows[-1], flush=True)
    doc = {"K_sim_median_over_median_mm": round(k, 4), "cv_n": C.LIMA_CV_N,
           "rc_terr_mm": D.F1_FLOOR_MM, "seed": D.DEPTH_SEED, "rows": rows,
           "calibrate_version": C.CALIBRATE_VERSION, "decide_version": D.DECIDE_VERSION}
    out_path.write_text(json.dumps(doc, indent=1) + "\n")
    print("K =", round(k, 4))


if __name__ == "__main__":
    main()

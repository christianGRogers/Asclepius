"""India R4 check (S2/S4, JA44 acceptance): JM-0R's synthetic summary through jm0r_decide.py with
the merged S3, and what R9 does. Synthetic phantom only (the tests' phantom); no case is opened, so
no guard call is needed.

    python experiments/JanusM/India/r4/s24_acceptance.py > .../r4/s24_acceptance.json

1. 40 identical synthetic rows (as the shipped acceptance test builds them): cv_n is 0, S3 refuses,
   and R9 prints the provisional 35 % with no NOT DECIDABLE line.
2. The same rows with seeded per-segment jitter (log-SD 0.088) on relative thickness, so cv_n > 0:
   R9 computes a depth, at S3's default median (9.668 mm), not JM-0R's ``thickness_median_mm``.
3. Lima's E7 inputs at median 9.668 vs 5.7 mm (issue #205 item 2).
"""
import copy
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(REPO / "src"), str(REPO / "tests")]

from janusm import calibrate as C  # noqa: E402


def _mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def _run(dec, summary):
    x = dec.from_jm0r(json.loads(json.dumps(summary)))
    res = {d["rule"]: d for d in dec.decide(x)}
    return x, {
        "cv_n": x["cv_n"], "thickness_median_mm": x["thickness_median_mm"],
        "R9_outcome": res["R9"]["outcome"], "R9_missing": res["R9"]["missing"],
        "R9_depth": res["R9"]["depth"],
        "not_decidable_lines": [ln for ln in dec.lines(res.values()) if "NOT DECIDABLE" in ln],
    }


def main():
    jm0r = _mod("jm0r_readout", REPO / "experiments/JanusM/fir/jm0r_readout.py")
    dec = _mod("jm0r_decide", REPO / "experiments/JanusM/fir/jm0r_decide.py")
    T = _mod("t_readout", REPO / "tests/test_janusm_jm0r_readout.py")
    lab, aff, w = T.phantom()
    r = jm0r.measure(lab, T.ct_from(lab, w["sp"]), aff, T.coronary(lab, w))

    out = {}
    _, out["identical_rows"] = _run(dec, jm0r.aggregate([dict(r) for _ in range(40)]))

    rng = np.random.default_rng(205)
    rows = []
    for _ in range(40):
        q = copy.deepcopy(r)
        q["rel_thickness"] = {k: v * float(rng.lognormal(0, 0.088))
                              for k, v in q["rel_thickness"].items()}
        rows.append(q)
    x2, out["jittered_rows"] = _run(dec, jm0r.aggregate(rows))
    out["jittered_rows"]["depth_if_median_mm_passed"] = C.detectable_depth(
        x2["cv_n"], x2["segment_shape"], 1.0, seed=dec.DEPTH_SEED,
        median_mm=x2["thickness_median_mm"])["depth"]

    for med in (C.LIMA_MEDIAN_MM, C.ED_MEDIAN_MM):
        out[f"lima_e7_inputs_cv0.088_rc1.0_median{med}"] = C.detectable_depth(
            C.LIMA_CV_N, list(C.LIMA_SHAPE), 1.0, seed=dec.DEPTH_SEED, median_mm=med)["depth"]
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

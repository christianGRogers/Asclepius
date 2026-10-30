"""Pool E9 into results/e9_estimators.json: error = estimate - truth, per estimator, border, shift and noise.

JA16's test: recover a known 0.5 mm shift, in each direction, to within +-0.05 mm. Reported per estimator: median
error, p10/p90, and the share of cases within +-0.05 mm, for |b| = 0.5 and 0.3 separately.

    python summarise_e9.py E9_DIR
"""
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BIAS = ("bias_centres", "bias_symmetric", "bias_volume")
ASSD = ("assd_band", "assd_segtrain")
THICK = ("thick_t1", "thick_mid", "thick_mean")


def stats(e):
    e = np.array([x for x in e if x is not None], float)
    if not e.size:
        return None
    return dict(median=round(float(np.median(e)), 3), p10=round(float(np.percentile(e, 10)), 3),
                p90=round(float(np.percentile(e, 90)), 3), within_0p05=round(float(np.mean(np.abs(e) <= 0.05)), 3),
                n=int(e.size))


def collect(rows, kind):
    out = {}
    groups = {}
    for r in rows:
        for x in r["rows"]:
            key = (x["border"], "out" if x["b"] > 0 else "in", abs(x["b"]), x["noise"])
            groups.setdefault(key, []).append(x)
    for (border, d, mag, noise), xs in sorted(groups.items()):
        g = {}
        for k in BIAS:
            g[k] = stats([x["est"][k] - x["truth"]["bias"] for x in xs])
        for k in ASSD:
            tr = (lambda x: abs(x["truth"]["bias"])) if kind == "real" else (lambda x: x["truth"]["assd"])
            g[k] = stats([x["est"][k] - tr(x) for x in xs]) if noise == 0 else None
        for k in THICK:
            g[k] = stats([None if x["est"].get(k) is None else x["est"][k] - x["truth"]["thick"] for x in xs])
        if kind == "real":
            g["realised_over_nominal"] = round(float(np.median([x["truth"]["bias"] / x["b"] for x in xs])), 3)
        out[f"{border} {d} {mag} noise{noise}"] = g
    return out


def verdict(table, est, mags=(0.5,), noise=(0.0,)):
    rows = [v[est] for k, v in table.items() if v.get(est) and float(k.split()[2]) in mags
            and float(k.split()[3][5:]) in noise]
    return dict(worst_abs_median=max(abs(r["median"]) for r in rows), min_within_0p05=min(r["within_0p05"] for r in rows))


def main(d):
    sph = json.load(open(os.path.join(d, "spheres.json")))
    real = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, "s*.json")))]
    real = [r for r in real if r.get("ok")]
    res = dict(n_spheres=len(sph), n_real=len(real), spheres=collect(sph, "sphere"), real=collect(real, "real"))
    res["verdicts"] = {}
    for est in BIAS + THICK + ASSD:
        res["verdicts"][est] = {
            "spheres_0.5": verdict(res["spheres"], est), "spheres_0.3": verdict(res["spheres"], est, (0.3,)),
            "real_0.5": verdict(res["real"], est), "real_0.3": verdict(res["real"], est, (0.3,)),
            "real_0.5_noise0.25": verdict(res["real"], est, (0.5,), (0.25,)) if est not in ASSD else None}
    json.dump(res, open(os.path.join(HERE, "results", "e9_estimators.json"), "w"), indent=1)
    print(json.dumps(res["verdicts"], indent=1))


if __name__ == "__main__":
    main(sys.argv[1])

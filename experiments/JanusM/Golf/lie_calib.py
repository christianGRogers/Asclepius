"""Golf R2 E5b: calibrate Scar-0's presence threshold on half the E5 hearts, test it on the other half.

Reads lie_reg.json (or lie_reg_partial.json). For each (misalignment, CNR, registration) and each presence threshold
tau in 0..0.30, a segment is scar-present if its thresholded fraction T >= tau; its Kim bin comes from T. tau is
chosen on the "development" hearts (even index in sorted order) by linear-weighted kappa, then scored once on the
"test" hearts (odd index), as the paired development / seal split will do (Golf v2 section 6.3).
Writes lie_calib.json.
"""
import json, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lie_reg import kim, wkappa  # noqa: E402

TAUS = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]


def load():
    p = HERE / "lie_reg.json"
    if p.exists():
        return json.loads(p.read_text())["cases"]
    return json.loads((HERE / "lie_reg_partial.json").read_text())


def score(tb, frac, tau):
    g = kim(np.where(frac >= tau, frac, 0.0))
    pos = tb > 0
    return {"kim_acc": float((g == tb).mean()), "wkappa": wkappa(tb, g),
            "sens": float((g[pos] > 0).mean()), "spec": float((g[~pos] == 0).mean())}


def main():
    res = {k: v for k, v in load().items() if "runs" in v}
    ids = sorted(res)
    dev, test = ids[0::2], ids[1::2]
    keys = sorted({(r["mis"], r["cnr"], r["reg"]) for c in res.values() for r in c["runs"]},
                  key=lambda k: (["none", "typical", "large"].index(k[0]), k[1],
                                 ["identity", "rigid", "affine", "bspline"].index(k[2])))
    out = []
    for key in keys:
        def gather(group):
            tb, fr = [], []
            for c in group:
                for r in res[c]["runs"]:
                    if (r["mis"], r["cnr"], r["reg"]) == key:
                        tb += res[c]["truth_bins"]; fr += r["T"]["frac"]
            return np.array(tb), np.array(fr)
        tbd, frd = gather(dev)
        tbt, frt = gather(test)
        grid = {t: score(tbd, frd, t) for t in TAUS}
        best = max(TAUS, key=lambda t: (grid[t]["wkappa"], -t))
        row = {"mis": key[0], "cnr": key[1], "reg": key[2], "tau_dev": best, "dev": grid[best],
               "test": score(tbt, frt, best), "test_tau0": score(tbt, frt, 0.0),
               "n_dev_segments": int(tbd.size), "n_test_segments": int(tbt.size)}
        out.append(row)
        print(key, "tau", best, "test", {k: round(v, 2) for k, v in row["test"].items()},
              "tau0", {k: round(v, 2) for k, v in row["test_tau0"].items()})
    (HERE / "lie_calib.json").write_text(json.dumps({"dev": dev, "test": test, "rows": out}, indent=1) + "\n")


if __name__ == "__main__":
    main()

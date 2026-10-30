"""Golf E2b: which RV-insertion end is "anterior"?  Two rules for the AHA angle origin, checked on the E2 cases.

Rule A (E2 as run): the arc end whose direction points more anterior (RAS +y).
Rule B: the arc end whose direction points more anterior-superior (RAS +y +z). The inferior insertion sits on the
diaphragmatic surface, so it is both posterior and inferior; the anterior insertion is anterior and superior.
Check (the same for both rules): segment 1 (anterior) lies both anterior AND superior of segment 4 (inferior),
the septum faces the RV and the lateral wall faces away.  1.5 mm grid, ~5 s per case.

Usage: python aha_check.py <ts_dir>   (writes aha_check.json)
"""
import json, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import layers_ts as L  # noqa: E402


def checks(seg, myo, rv, Rw):
    cen = lambda m: np.argwhere(m).mean(0) @ Rw.T
    c0, rvdir = cen(myo), cen(rv) - cen(myo)
    d14 = cen(seg == 1) - cen(seg == 4)            # world mm, RAS
    a1, a4 = float(d14[1]), float(d14[2])          # segment 1 minus segment 4: anterior (+y) and superior (+z)
    sept = bool(np.dot(cen(np.isin(seg, (2, 3, 8, 9))) - c0, rvdir) > 0)
    lat = bool(np.dot(cen(np.isin(seg, (5, 6, 11, 12))) - c0, rvdir) < 0)
    return {"seg1_minus_seg4_anterior_mm": a1, "seg1_minus_seg4_superior_mm": a4, "septum_towards_rv": sept,
            "lateral_away": lat, "ok": bool(a1 > 0 and a4 > 0 and sept and lat)}


def main():
    ts = Path(sys.argv[1])
    ids = list(json.loads((Path(__file__).parent / "ts_cases.json").read_text()))
    out = {}
    for i in ids:
        ct, Lb, sp, aff = L.load(ts / i)
        if not (Lb[L.MYO].any() and Lb[L.LV].any()):
            out[i] = {"fail": "no LV myocardium / blood-pool label"}
            print(i, out[i], flush=True)
            continue
        la, myo, cav, rv = L.crop(Lb[L.LA], Lb[L.MYO], Lb[L.LV], Lb[L.RV], mask=Lb[L.MYO] | Lb[L.LV])
        R = aff[:3, :3] / np.linalg.norm(aff[:3, :3], axis=0)
        geom, _ = L.aha(myo, cav, rv, la, sp)
        if geom is None:
            out[i] = {"fail": "AHA derivation failed"}
            continue
        r = {}
        for name, d in (("A_anterior", [0.0, 1.0, 0.0]), ("B_anterior_superior", [0.0, 1.0, 1.0])):
            seg = L.aha_labels(myo, geom, R.T @ (np.array(d) / np.linalg.norm(d)))
            r[name] = checks(seg, myo, rv, R * sp)
        out[i] = r
        print(i, {k: v["ok"] for k, v in r.items()}, flush=True)
    ok = {k: sum(v[k]["ok"] for v in out.values() if "fail" not in v) for k in ("A_anterior", "B_anterior_superior")}
    print("orientation ok:", ok, "of", sum("fail" not in v for v in out.values()))
    (Path(__file__).parent / "aha_check.json").write_text(json.dumps({"ok": ok, "cases": out}, indent=1))


if __name__ == "__main__":
    main()

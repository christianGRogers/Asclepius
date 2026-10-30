"""India Round 3, E10: Lima's E3 re-run with a measured segment shape and cv_n (ruling R2 §7 item 3, JA18).

JA18 prints on the page, instead of a sensitivity, the relative thinning depth that rule C (Lima: patient-relative,
shape-corrected, per territory, <= 5 % null patients flagged) finds 80 % of the time. Lima's E3 assumed a segment shape
from 23 public 1.5 mm hearts and swept cv_n (normal segment-to-segment variation) over 0.06 / 0.10 / 0.15.

E10 does three things:
1. **Measures** on public hearts (after `janusm.guard.refuse`), on JA15's 0.5 mm walls:
   - the segment shape (median over hearts of segment thickness / the heart's median), segments 1-16;
   - cv_n_raw: the pooled robust SD of log(relative thickness / shape). Model-made labels carry their own error, so
     this is an upper bound on the true normal variation;
   - sig_m(ASSD): the per-segment thickness error SD that JA15's model U produces at a realised border ASSD, i.e.
     the measurement error of a model at JA8's acceptance edge.
2. **Re-runs Lima's E3** (`experiments/JanusM/Lima/calibrate_sim.py`, imported unchanged) with that shape and cv_n,
   and with sig_m at the realised ASSDs U gives, reporting the depth for 80 % territory sensitivity and the
   patient-level false-flag rate by phase mix.
3. Provides `detectable_depth(shape, cv_n, sig_m)` for the pre-registered JM-0R step (`jm0r_rules.py`), which re-runs
   it with JM-0R's measured `cv_n` and shape.

    python e10_detectable_depth.py TS_DIR OUT_DIR [--cases N] [--workers 3]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.join(REPO, "experiments", "JanusM", "Lima"))
import calibrate_sim as L3  # noqa: E402  (Lima's E3, unchanged)
import lvgeom as G  # noqa: E402
from harness_r2 import MASKS, field, load_masks, model_walls, walls_from  # noqa: E402
from janusm.guard import refuse_one  # noqa: E402

SIGMAS = (0.25, 0.5)


def seg_thickness(myo, cav, seg, sp):
    _, th = G.depth_distance(myo, cav, sp)
    out = np.full(16, np.nan)
    for s in range(1, 17):
        m = myo & (seg == s)
        if m.sum() > 30:
            out[s - 1] = float(np.median(th[m]))
    return out


def case(args):
    d, outdir = args
    sid = os.path.basename(os.path.normpath(d))
    path = os.path.join(outdir, f"{sid}.json")
    if os.path.exists(path):
        return sid, "cached"
    try:
        refuse_one(sid, source="TotalSegmentator")
        sub, why = load_masks(d)
        if sub is None:
            json.dump(dict(sid=sid, ok=False, why=why), open(path, "w"))
            return sid, why
        rng = np.random.default_rng(int(sid[1:]) + 23)
        g, se, ss, rv, la, ao, aff = model_walls(sub, "U")
        sp = np.full(3, g)
        cav, myo, sol = walls_from(se, ss)
        geo = dict(myo=myo, lv=cav, rv=rv & ~sol, la=la & ~sol, affine=aff)
        fr = G.lv_frame(geo)
        if fr is None:
            json.dump(dict(sid=sid, ok=False, why="no frame"), open(path, "w"))
            return sid, "no frame"
        seg = G.aha17(geo, fr)
        ref = seg_thickness(myo, cav, seg, sp)
        res = dict(sid=sid, ok=True, thick=ref.tolist(), err={})
        for sig in SIGMAS:
            n1, n2 = field(se.shape, g, sig, 8.0, rng), field(se.shape, g, sig, 8.0, rng)
            cp, mp, solp = walls_from(se + n1, ss + n2)
            gp = dict(myo=mp, lv=cp, rv=rv & ~solp, la=la & ~solp, affine=aff)
            fp = G.lv_frame(gp)
            segp = G.aha17(gp, fp) if fp is not None else seg * mp
            res["err"][str(sig)] = (seg_thickness(mp, cp, segp, sp) - ref).tolist()
        json.dump(res, open(path, "w"))
        return sid, "ok"
    except Exception:
        json.dump(dict(sid=sid, ok=False, why=traceback.format_exc()[-800:]), open(path, "w"))
        return sid, "error"


def measure(rows):
    T = np.array([r["thick"] for r in rows], float)
    rel = T / np.nanmedian(T, 1, keepdims=True)
    shape = np.nanmedian(rel, 0)
    lr = np.log(rel / shape)
    lr = lr[np.isfinite(lr)]
    cv_raw = float(1.4826 * np.median(np.abs(lr - np.median(lr))))
    sig = {}
    for s in SIGMAS:
        e = np.array([v for r in rows for v in r["err"][str(s)] if v is not None and np.isfinite(v)])
        sig[s] = float(1.4826 * np.median(np.abs(e - np.median(e))))
    return shape, cv_raw, sig, float(np.nanmedian(T))


def detectable_depth(shape, cv_n, sig_m, n=2000, prev=0.1, mix=None, seed=20261031):
    """Depth (relative) at which rule C finds >= 80 % of infarct territories, and its false-flag rate. Lima's E3
    population and rule, with this shape, cv_n and sig_m. Depths 0.15-0.60 in steps of 0.05."""
    mix = mix or {"ED": 0.4, "MD": 0.4, "SYS": 0.2}
    old = L3.SHAPE
    L3.SHAPE = np.asarray(shape, float)
    rng = np.random.default_rng(seed)
    try:
        rows = []
        for depth in np.arange(0.15, 0.601, 0.05):
            meas, lesion, sick, terr, ph = L3.population(n, prev, depth, cv_n, sig_m, mix, rng)
            cut, k = L3.calibrate_c(L3.rule_c_scores(meas))
            r = L3.evaluate(meas, lesion, sick, terr, ph, cut)["C_relative_territory"]
            rows.append(dict(depth=round(float(depth), 2), k=k, **r))
        ok = [r["depth"] for r in rows if r["territory_sensitivity"] >= 0.8]
        return dict(depth_80=ok[0] if ok else None, rows=rows)
    finally:
        L3.SHAPE = old


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ts_dir"); ap.add_argument("out_dir")
    ap.add_argument("--cases", type=int, default=30); ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    dirs = sorted(glob.glob(os.path.join(a.ts_dir, "Totalsegmentator_dataset", "s*")))
    dirs = [d for d in dirs if all(os.path.exists(f"{d}/segmentations/{v}.nii.gz") for v in MASKS.values())]
    for d in dirs:
        refuse_one(os.path.basename(d), source="TotalSegmentator")
    ok = 0
    with ProcessPoolExecutor(a.workers) as ex:
        for sid, st in ex.map(case, [(d, a.out_dir) for d in dirs]):
            print(sid, st, flush=True)
            ok += st in ("ok", "cached")
            if ok >= a.cases:
                break
    rows = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(a.out_dir, "s*.json")))]
    rows = [r for r in rows if r.get("ok")]
    shape, cv_raw, sig, med = measure(rows)
    out = dict(n_cases=len(rows), shape=[round(float(x), 3) for x in shape], cv_n_raw=round(cv_raw, 4),
               lima_shape=L3.SHAPE.round(3).tolist(), median_thickness_mm_public_labels=round(med, 2),
               sig_m_by_U_sigma={str(k): round(v, 3) for k, v in sig.items()},
               note="U sigma 0.25 / 0.5 realise ASSD ~0.21 / ~0.36 mm (India R2 E5)", runs={})
    for cv in sorted({round(cv_raw, 3), 0.06, 0.10}):
        for s_name, s_val in list(sig.items()) + [("0.0", 0.0)]:
            for mix_name, mix in (("mixed", None), ("all_ED", {"ED": 1.0, "MD": 0.0, "SYS": 0.0})):
                for shp_name, shp in (("measured", shape), ("lima", L3.SHAPE)):
                    r = detectable_depth(shp, cv, s_val, mix=mix)
                    ff = [x["patient_false_flag"] for x in r["rows"]]
                    out["runs"][f"cv{cv} sigU{s_name} {mix_name} shape_{shp_name}"] = dict(
                        depth_80=r["depth_80"], false_flag_max=max(ff), false_flag_median=float(np.median(ff)))
    json.dump(out, open(os.path.join(HERE, "results", "e10_detectable_depth.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "runs"}, indent=1))
    for k, v in out["runs"].items():
        print(k, v)


if __name__ == "__main__":
    main()

"""India Round 2, E6: depth and sector rules on a 0.5 mm grid (ruling §6 item 3, first two parts).

On each public case (same loader and guard as E5), on the 0.5 mm slope-1 SDF grid:
1. Depth: JA2's equal-thickness depth (ET) vs the Yezzi-Prince depth (YP: lengths along the Laplace streamlines,
   Yezzi & Prince 2003, IEEE TMI 22:1332, doi:10.1109/TMI.2003.817775). Reports the share of wall voxels in the same
   third, and each depth's third Dice and STA under E5's error model U (sigma 0.5 mm, corr 8 mm): which depth is
   more stable under border error.
2. Sectors: fixed 60 deg (basal, mid) / 90 deg (apical) sectors from the anterior RV insertion (JA3) vs sectors
   proportional to the measured septal arc (the two septal segments share the arc; the other four share the rest).
   Reports the share of myocardium that changes segment and that changes AHA-default territory, and the mean
   segment Dice of each rule under U, i.e. its reproducibility.

    python e6_depth_sectors.py TS_DIR OUT_DIR [--cases N] [--workers 3]
"""
from __future__ import annotations

import argparse, glob, json, os, sys, traceback
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lvgeom as G  # noqa: E402
from guard_r2 import refuse  # noqa: E402
from harness_r2 import (MASKS, TAUS, kim, load_masks, model_walls, walls_from, field)  # noqa: E402


def yezzi_prince(myo, cav, sp, iters=400):
    """Yezzi-Prince depth L0/(L0+L1): L0 = path length from the endocardium along the Laplace streamlines,
    L1 = path length to the epicardium; upwind fixed-point iteration (isotropic grid)."""
    u = G.depth_laplace(myo, cav)
    endo, epi = G.boundaries(myo, cav)
    uu = u.copy()
    uu[endo] = 0.0
    uu[epi] = 1.0
    gx = np.stack(np.gradient(uu), 0)
    nrm = np.sqrt((gx ** 2).sum(0)) + 1e-9
    T = gx / nrm
    h = float(sp[0])

    def solve(direction, zero_shell):
        L = np.zeros(myo.shape, np.float32)
        Tm = T * direction                                 # march along +T for L0 (from endo), -T for L1
        A = np.abs(Tm)
        den = A.sum(0) + 1e-9
        for _ in range(iters):
            num = np.full(myo.shape, h, np.float32)
            for ax in range(3):
                s = np.sign(Tm[ax])
                fwd = np.roll(L, 1, axis=ax)                # value at x - e_ax
                bwd = np.roll(L, -1, axis=ax)               # value at x + e_ax
                fz = np.roll(zero_shell, 1, axis=ax)
                bz = np.roll(zero_shell, -1, axis=ax)
                fm = np.roll(myo, 1, axis=ax) | fz
                bm = np.roll(myo, -1, axis=ax) | bz
                nb = np.where(s > 0, fwd, bwd)
                nbz = np.where(s > 0, fz, bz)
                nbm = np.where(s > 0, fm, bm)
                nb = np.where(nbz, 0.0, nb)
                ok = nbm
                num += np.where(ok, A[ax] * nb, 0.0)
                # an upwind neighbour outside the wall (and not the zero shell) drops out of the stencil
            dd = np.zeros_like(den)
            for ax in range(3):
                s = np.sign(Tm[ax])
                fm = np.roll(myo, 1, axis=ax) | np.roll(zero_shell, 1, axis=ax)
                bm = np.roll(myo, -1, axis=ax) | np.roll(zero_shell, -1, axis=ax)
                dd += np.where(np.where(s > 0, fm, bm), A[ax], 0.0)
            Ln = np.where(myo, num / np.maximum(dd, 1e-3), 0.0).astype(np.float32)
            if np.abs(Ln - L).max() < 1e-3:
                L = Ln
                break
            L = Ln
        return L

    L0 = solve(+1.0, endo)
    L1 = solve(-1.0, epi)
    t = np.zeros(myo.shape, np.float32)
    t[myo] = L0[myo] / np.maximum(L0[myo] + L1[myo], 1e-6)
    return np.clip(t, 0, 1)


def aha_prop(g, fr):
    """AHA 17 with sectors proportional to the measured septal arc (basal, mid and apical rings)."""
    seg = G.aha17(g, fr)                    # rings, apex cap and the out-of-range voxels stay as in JA3
    myo, aff = g["myo"], g["affine"]
    P = np.argwhere(myo)
    w = G.world(P, aff) - fr["base"]
    ang = np.degrees(np.arctan2(w @ fr["e2"], w @ fr["e1"])) % 360
    phi = (fr["sign"] * (ang - fr["ref"])) % 360
    arc = float(np.clip(fr["septal_arc_deg"], 60, 240))
    rest = (360 - arc) / 4
    s0 = seg[tuple(P.T)]
    out = s0.copy()
    # basal / mid: [0, arc/2) anteroseptal, [arc/2, arc) inferoseptal, then inferior, inferolateral, anterolateral, anterior
    edges = [0, arc / 2, arc, arc + rest, arc + 2 * rest, arc + 3 * rest, 360.0001]
    six = [2, 3, 4, 5, 6, 1]
    k6 = np.clip(np.searchsorted(edges, phi, side="right") - 1, 0, 5)
    base_ring = np.isin(s0, (1, 2, 3, 4, 5, 6))
    mid_ring = np.isin(s0, (7, 8, 9, 10, 11, 12))
    out[base_ring] = np.array(six)[k6[base_ring]]
    out[mid_ring] = np.array(six)[k6[mid_ring]] + 6
    # apical: septal = the arc, the other three share the rest: inferior 15, lateral 16, anterior 13
    r3 = (360 - arc) / 3
    e4 = [0, arc, arc + r3, arc + 2 * r3, 360.0001]
    k4 = np.clip(np.searchsorted(e4, phi, side="right") - 1, 0, 3)
    ap = np.isin(s0, (13, 14, 15, 16))
    out[ap] = np.array([14, 15, 16, 13])[k4[ap]]
    res = np.zeros(myo.shape, np.uint8)
    res[tuple(P.T)] = out
    return res


TERR = {**{s: 1 for s in (1, 2, 7, 8, 13, 14, 17)}, **{s: 2 for s in (3, 4, 9, 10, 15)},
        **{s: 3 for s in (5, 6, 11, 12, 16)}}


def terr(seg):
    t = np.zeros(seg.shape, np.uint8)
    for s, v in TERR.items():
        t[seg == s] = v
    return t


def sta(myo_r, t_r, seg_r, myo_p, t_p, seg_p):
    def tx(scar, myo, seg, s):
        m = myo & (seg == s)
        return (scar & m).sum() / m.sum() if m.sum() > 50 else np.nan
    agree = []
    for s in range(1, 17):
        for tau in TAUS:
            scar = myo_r & (seg_r == s) & (t_r < tau)
            b = kim(tx(scar, myo_r, seg_r, s))
            if b >= 0:
                agree.append(b == kim(tx(scar, myo_p, seg_p, s)))
    return float(np.mean(agree)) if agree else None


def seg_dice(a, b, myo_a, myo_b):
    return float(np.nanmean([G.dice((a == k) & myo_a, (b == k) & myo_b) for k in range(1, 18)]))


def run_case(args):
    d, outdir = args
    sid = os.path.basename(os.path.normpath(d))
    path = os.path.join(outdir, f"{sid}.json")
    if os.path.exists(path):
        return sid, "cached"
    try:
        sub, why = load_masks(d)
        if sub is None:
            json.dump(dict(sid=sid, ok=False, why=why), open(path, "w")); return sid, why
        rng = np.random.default_rng(int(sid[1:]) + 11)
        g, se, ss, rv, la, ao, aff = model_walls(sub, "U")
        sp = np.full(3, g)
        cav_r, myo_r, sol_r = walls_from(se, ss)
        geo = dict(myo=myo_r, lv=cav_r, rv=rv & ~sol_r, la=la & ~sol_r, affine=aff)
        fr = G.lv_frame(geo)
        if fr is None:
            json.dump(dict(sid=sid, ok=False, why="no frame"), open(path, "w")); return sid, "no frame"
        et_r, _ = G.depth_distance(myo_r, cav_r, sp)
        yp_r = yezzi_prince(myo_r, cav_r, sp)
        fx_r, pr_r = G.aha17(geo, fr), aha_prop(geo, fr)
        L_et, L_yp = G.layers(et_r, myo_r), G.layers(yp_r, myo_r)
        res = dict(sid=sid, ok=True, septal_arc_deg=float(fr["septal_arc_deg"]),
                   third_agree_et_yp=float((L_et == L_yp)[myo_r].mean()),
                   median_abs_dt_et_yp=float(np.median(np.abs(et_r - yp_r)[myo_r])),
                   third_share_et=[float((L_et == k)[myo_r].mean()) for k in (1, 2, 3)],
                   third_share_yp=[float((L_yp == k)[myo_r].mean()) for k in (1, 2, 3)],
                   in17 = float((fx_r > 0)[myo_r].mean()),
                   seg_changed_fixed_vs_prop=float((fx_r != pr_r)[myo_r & (fx_r > 0)].mean()),
                   terr_changed_fixed_vs_prop=float((terr(fx_r) != terr(pr_r))[myo_r & (fx_r > 0)].mean()),
                   runs=[])
        for rep in range(2):
            n1, n2 = field(se.shape, g, 0.5, 8.0, rng), field(se.shape, g, 0.5, 8.0, rng)
            cav_p, myo_p, sol_p = walls_from(se + n1, ss + n2)
            geo_p = dict(myo=myo_p, lv=cav_p, rv=rv & ~sol_p, la=la & ~sol_p, affine=aff)
            fr_p = G.lv_frame(geo_p)
            if fr_p is None:
                continue
            et_p, _ = G.depth_distance(myo_p, cav_p, sp)
            yp_p = yezzi_prince(myo_p, cav_p, sp)
            fx_p, pr_p = G.aha17(geo_p, fr_p), aha_prop(geo_p, fr_p)
            dl = lambda tr, tp: [float(G.dice(G.layers(tr, myo_r) == k, G.layers(tp, myo_p) == k)) for k in (1, 2, 3)]
            res["runs"].append(dict(
                arc_p=float(fr_p["septal_arc_deg"]),
                dice_thirds_et=dl(et_r, et_p), dice_thirds_yp=dl(yp_r, yp_p),
                sta_et=sta(myo_r, et_r, fx_r, myo_p, et_p, fx_p), sta_yp=sta(myo_r, yp_r, fx_r, myo_p, yp_p, fx_p),
                seg_dice_fixed=seg_dice(fx_r, fx_p, myo_r, myo_p), seg_dice_prop=seg_dice(pr_r, pr_p, myo_r, myo_p)))
        json.dump(res, open(path, "w"))
        return sid, "ok"
    except Exception:
        json.dump(dict(sid=sid, ok=False, why=traceback.format_exc()[-800:]), open(path, "w"))
        return sid, "error"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ts_dir"); ap.add_argument("out_dir")
    ap.add_argument("--cases", type=int, default=30); ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    dirs = sorted(glob.glob(os.path.join(a.ts_dir, "Totalsegmentator_dataset", "s*")))
    dirs = [d for d in dirs if all(os.path.exists(f"{d}/segmentations/{v}.nii.gz") for v in MASKS.values())]
    for d in dirs:
        refuse("TotalSegmentator", os.path.basename(d))
    ok = 0
    with ProcessPoolExecutor(a.workers) as ex:
        for sid, st in ex.map(run_case, [(d, a.out_dir) for d in dirs]):
            print(sid, st, flush=True)
            ok += st in ("ok", "cached")
            if ok >= a.cases:
                break


if __name__ == "__main__":
    main()

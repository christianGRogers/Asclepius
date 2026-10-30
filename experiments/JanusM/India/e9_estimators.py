"""India Round 3, E9: validate the JA15 estimators (ruling R2 §7 item 2; JA16's +-0.05 mm test).

Does each candidate implementation of ASSD, signed border bias and segment-thickness change recover a known border
shift to within +-0.05 mm? The JA16 test: "the estimator must recover a known 0.5 mm shift, in each direction, to
within +-0.05 mm in the JA15 harness". Its answer decides the signed-bias guard (0.3 mm if it passes, else 0.5 mm).

Two kinds of truth:
- **Spheres** (exact): a pool of radius r_p in a shell to r_o, rasterised at 0.5 mm with a random sub-voxel centre;
  one radius moved by b. The true signed bias is b, the ASSD |b|, the thickness change -b (endo) or +b (epi).
- **Real shapes in JA15's model** (U = lima_c8): the 0.5 mm walls of public TotalSegmentator hearts (after
  `janusm.guard.refuse`), one border's SDF moved by a nominal b, alone or with independent random fields of RMS
  0.25 mm on both borders. The SDF is zoomed from the 1.5 mm labels, so its slope is not exactly 1 and a nominal b
  does not move the surface by exactly b. The truth is therefore measured on the continuous fields: the mean
  outward displacement Delta V / A of the zero level set (`continuum_bias`), independent of any rasterisation.

Shifts b in {-0.5, -0.3, +0.3, +0.5} mm per border (+ = outward: cavity grows for endo, wall grows for epi).

Estimators (each on binary masks only, as a read or a model gives them):
- bias_centres: India R2's: mean slope-1 SDF of the test object at the reference surface voxels (minus h/2).
- bias_symmetric: (bias_centres(ref -> test) - bias_centres(test -> ref)) / 2.
- bias_volume: (V_test - V_ref) in a band around the border / the reference border's area (marching cubes on the
  mask smoothed by 1 voxel), restricted to the part of the border that faces the myocardium.
- assd_band: symmetric surface-voxel ASSD restricted to the myocardium-facing border (India R2's harness).
- assd_segtrain: `segtrain.metrics.surface_distances` on the whole object (what `janusm_reads.anchoring` uses).
- thick_t1: median over voxels of d_endo + d_epi - h (India R2; per AHA segment on real shapes, then the median over
  segments 1-16, as JA8 defines the co-primary).
- thick_mid: the same, sampled only at mid-wall depth 0.4 <= u <= 0.6.
- thick_mean: the segment *mean* of d_endo + d_epi - h (a median over voxels is non-linear for a sub-voxel shift,
  since only some voxels move); the median over segments 1-16 is kept.

    python e9_estimators.py TS_DIR OUT_DIR [--cases N] [--workers 3] [--spheres 40]
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
from scipy import ndimage as ndi
from skimage.measure import marching_cubes

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "src"))
import lvgeom as G  # noqa: E402
from harness_r2 import MASKS, field, load_masks, model_walls, sdf_half, walls_from  # noqa: E402
from janusm.guard import refuse_one  # noqa: E402
from segtrain.metrics import surface_distances  # noqa: E402

SHIFTS = (-0.5, -0.3, 0.3, 0.5)
ST = G.STRUCT


def surf(m):
    return m & ~ndi.binary_erosion(m, ST, border_value=1)


def facing(obj, myo_r, border):
    """Reference-surface voxels of `obj` that face the myocardium (endo: cavity voxels next to myo; epi: myo voxels
    next to the outside)."""
    s = surf(obj)
    if border == "endo":
        return s & ndi.binary_dilation(myo_r, ST)
    return s & myo_r


def bias_centres(ref, test, mask, sp):
    h = float(sp[0]) / 2
    return float(-(np.mean(sdf_half(test, sp)[mask]) + h))


def bias_symmetric(ref, test, mref, mtest, sp):
    return 0.5 * (bias_centres(ref, test, mref, sp) - bias_centres(test, ref, mtest, sp))


def area_in_band(obj, band, sp):
    sm = ndi.gaussian_filter(obj.astype(np.float32), 1.0)
    v, f, _, _ = marching_cubes(sm, 0.5, spacing=tuple(sp))
    tri = v[f]
    a = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    c = np.clip(np.round(tri.mean(1) / sp).astype(int), 0, np.array(obj.shape) - 1)
    return float(a[band[tuple(c.T)]].sum())


def bias_volume(ref, test, band, sp):
    dv = (test & band).sum() - (ref & band).sum()
    A = 0.5 * (area_in_band(ref, band, sp) + area_in_band(test, band, sp))
    return float(dv * np.prod(sp) / max(A, 1e-6))


def assd_band(ref, test, mask_ref, mask_test, sp):
    da = ndi.distance_transform_edt(~surf(test), sampling=sp)[mask_ref]
    db = ndi.distance_transform_edt(~surf(ref), sampling=sp)[mask_test]
    return float((da.sum() + db.sum()) / (len(da) + len(db)))


def assd_seg(ref, test, sp):
    a, b = surface_distances(test, ref, sp)
    return float((a.sum() + b.sum()) / (a.size + b.size))


def thickness(myo, cav, sp, seg=None, mid=False, agg=np.median):
    t, th = G.depth_distance(myo, cav, sp)
    sel = myo & ((t >= 0.4) & (t <= 0.6) if mid else True)
    if seg is None:
        return float(agg(th[sel]))
    v = [agg(th[sel & (seg == s)]) for s in range(1, 17) if (sel & (seg == s)).sum() > 30]
    return np.array(v), [s for s in range(1, 17) if (sel & (seg == s)).sum() > 30]


def estimate(cav_r, myo_r, sol_r, cav_p, myo_p, sol_p, border, sp, seg_r=None, seg_p=None):
    ref, test = (cav_r, cav_p) if border == "endo" else (sol_r, sol_p)
    mr, mt = facing(ref, myo_r, border), facing(test, myo_p, border)
    band = ndi.binary_dilation(mr | mt, ST, iterations=4)
    out = dict(bias_centres=bias_centres(ref, test, mr, sp),
               bias_symmetric=bias_symmetric(ref, test, mr, mt, sp),
               bias_volume=bias_volume(ref, test, band, sp),
               assd_band=assd_band(ref, test, mr, mt, sp),
               assd_segtrain=assd_seg(ref, test, sp))
    if seg_r is None:
        out["thick_t1"] = thickness(myo_p, cav_p, sp) - thickness(myo_r, cav_r, sp)
        out["thick_mid"] = thickness(myo_p, cav_p, sp, mid=True) - thickness(myo_r, cav_r, sp, mid=True)
        out["thick_mean"] = thickness(myo_p, cav_p, sp, agg=np.mean) - thickness(myo_r, cav_r, sp, agg=np.mean)
    else:
        for key, mid, agg in (("thick_t1", False, np.median), ("thick_mid", True, np.median),
                              ("thick_mean", False, np.mean)):
            vr, sr = thickness(myo_r, cav_r, sp, seg_r, mid, agg)
            vp, spp = thickness(myo_p, cav_p, sp, seg_p, mid, agg)
            common = [s for s in sr if s in spp]
            d = [vp[spp.index(s)] - vr[sr.index(s)] for s in common]
            out[key] = float(np.median(d)) if d else None
    return out


# ------------------------------------------------------------------------------------------------ spheres

def sphere_case(i):
    rng = np.random.default_rng(1000 + i)
    g = 0.5
    sp = np.full(3, g)
    rp, ro = rng.uniform(15, 25), 0.0
    ro = rp + rng.uniform(6, 11)
    n = int(np.ceil((ro + 4) * 2 / g)) + 4
    c = (np.array([n, n, n]) * g) / 2 + rng.uniform(-g / 2, g / 2, 3)
    z, y, x = np.indices((n, n, n), dtype=np.float32) * g
    r = np.sqrt((z - c[0]) ** 2 + (y - c[1]) ** 2 + (x - c[2]) ** 2)

    def walls(rp_, ro_):
        cav = r <= rp_
        sol = r <= ro_
        return cav, sol & ~cav, sol

    W = walls(rp, ro)
    rows = []
    for border in ("endo", "epi"):
        for b in SHIFTS:
            P = walls(rp + b, ro) if border == "endo" else walls(rp, ro + b)
            est = estimate(*W, *P, border, sp)
            truth = dict(bias=b, assd=abs(b), thick=-b if border == "endo" else b)
            rows.append(dict(border=border, b=b, noise=0.0, truth=truth, est=est))
    return dict(kind="sphere", id=i, rp=rp, ro=ro, rows=rows)


# ------------------------------------------------------------------------------------------------ real shapes

def continuum_bias(f0, c, band, g):
    """The true mean outward displacement of the level set {f0 = 0} when the field becomes f0 + c, measured on the
    continuous fields, not on voxels: Delta V / A by the coarea formula, with a linear occupancy ramp of one voxel's
    width. Exact to first order for any |grad f0| (so it also corrects the zoomed staircase SDF's local slope)."""
    phi = lambda f: np.clip(0.5 - f / g, 0.0, 1.0)
    f0b = f0[band]
    f1b = (f0 + c)[band] if np.ndim(c) else f0b + c
    dv = (phi(f1b) - phi(f0b)).sum() * g ** 3
    gr = np.sqrt(sum(x ** 2 for x in np.gradient(f0, g)))[band]
    A = ((np.abs(f0b) < g / 2) * gr).sum() * g ** 2
    return float(dv / max(A, 1e-9))


def real_case(args):
    d, outdir = args
    sid = os.path.basename(os.path.normpath(d))
    path = os.path.join(outdir, f"{sid}.json")
    if os.path.exists(path):
        return sid, "cached"
    try:
        refuse_one(sid, source="TotalSegmentator")          # JA22: the shared guard, before any byte is read
        sub, why = load_masks(d)
        if sub is None:
            json.dump(dict(sid=sid, ok=False, why=why), open(path, "w"))
            return sid, why
        rng = np.random.default_rng(int(sid[1:]) + 17)
        g, se, ss, rv, la, ao, aff = model_walls(sub, "U")
        sp = np.full(3, g)
        cav_r, myo_r, sol_r = walls_from(se, ss)
        geo = dict(myo=myo_r, lv=cav_r, rv=rv & ~sol_r, la=la & ~sol_r, affine=aff)
        fr = G.lv_frame(geo)
        if fr is None:
            json.dump(dict(sid=sid, ok=False, why="no frame"), open(path, "w"))
            return sid, "no frame"
        seg_r = G.aha17(geo, fr)
        m_endo, m_epi = facing(cav_r, myo_r, "endo"), facing(sol_r, myo_r, "epi")
        b_endo = ndi.binary_dilation(m_endo, ST, iterations=4)
        b_epi = ndi.binary_dilation(m_epi, ST, iterations=4) & ~ndi.binary_erosion(cav_r, ST, iterations=2)
        rows = []
        for noise in (0.0, 0.25):
            for border in ("endo", "epi"):
                for b in SHIFTS:
                    n1 = field(se.shape, g, noise, 8.0, rng) if noise else np.float32(0)
                    n2 = field(se.shape, g, noise, 8.0, rng) if noise else np.float32(0)
                    c1 = n1 - (b if border == "endo" else 0.0)       # added to the SDF: + moves inward
                    c2 = n2 - (b if border == "epi" else 0.0)
                    cav_p, myo_p, sol_p = walls_from(se + c1, ss + c2)
                    geo_p = dict(myo=myo_p, lv=cav_p, rv=rv & ~sol_p, la=la & ~sol_p, affine=aff)
                    fr_p = G.lv_frame(geo_p)
                    seg_p = G.aha17(geo_p, fr_p) if fr_p is not None else seg_r * myo_p
                    est = estimate(cav_r, myo_r, sol_r, cav_p, myo_p, sol_p, border, sp, seg_r, seg_p)
                    # truth: the continuum mean outward displacement of each border (thickness: their difference,
                    # an approximation to the segment-median change; noted in the write-up)
                    t_endo = continuum_bias(se, c1, b_endo, g)
                    t_epi = continuum_bias(ss, c2, b_epi, g)
                    tb = t_endo if border == "endo" else t_epi
                    truth = dict(bias=tb, thick=t_epi - t_endo, nominal=b)
                    rows.append(dict(border=border, b=b, noise=noise, truth=truth, est=est))
        json.dump(dict(sid=sid, ok=True, rows=rows), open(path, "w"))
        return sid, "ok"
    except Exception:
        json.dump(dict(sid=sid, ok=False, why=traceback.format_exc()[-800:]), open(path, "w"))
        return sid, "error"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ts_dir"); ap.add_argument("out_dir")
    ap.add_argument("--cases", type=int, default=24); ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--spheres", type=int, default=40)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    sph = os.path.join(a.out_dir, "spheres.json")
    if not os.path.exists(sph):
        with ProcessPoolExecutor(a.workers) as ex:
            json.dump(list(ex.map(sphere_case, range(a.spheres))), open(sph, "w"))
        print("spheres done", flush=True)
    dirs = sorted(glob.glob(os.path.join(a.ts_dir, "Totalsegmentator_dataset", "s*")))
    dirs = [d for d in dirs if all(os.path.exists(f"{d}/segmentations/{v}.nii.gz") for v in MASKS.values())]
    for d in dirs:
        refuse_one(os.path.basename(d), source="TotalSegmentator")
    ok = 0
    with ProcessPoolExecutor(a.workers) as ex:
        for sid, st in ex.map(real_case, [(d, a.out_dir) for d in dirs]):
            print(sid, st, flush=True)
            ok += st in ("ok", "cached")
            if ok >= a.cases:
                break


if __name__ == "__main__":
    main()

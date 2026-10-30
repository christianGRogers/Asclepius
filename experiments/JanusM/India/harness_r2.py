"""India Round 2, E5: one perturbation harness for the four Round 1 border-error simulations (ruling §6 item 2).

Round 1 reported the subendocardial-third Dice at a "0.5 mm" smooth border error as 0.909 (Golf), 0.927 (India),
0.939 (Kilo) and 0.975 (Hotel). E5 re-implements each advocate's error model as committed, runs all four on the
same public cases, and measures what each one *actually* does to the border: the realised endocardial ASSD (mm)
between the unperturbed and the perturbed wall. The hypothesis is that the four differ in how their signed-distance
function (SDF) converts a field value into a surface shift, not in the physics.

The four models (from the committed code):
- golf  (Golf/layers_ts.py):   SDF with the surface half-way between voxel centres (slope 1), computed on the native
                               grid and zoomed to 0.5 mm; field correlation 8 mm.
- india (India/lvgeom.py):     masks resampled to 0.5 mm, SDF = +-h/2 at the boundary with h = half a voxel, i.e.
                               +-0.25 voxel: slope 1.5 across the boundary; field correlation 8 mm.
- kilo  (Kilo/exp_layers.py):  plain SDF (edt(~m) - edt(m), +-1 voxel at the boundary, slope 2) on the native grid,
                               zoomed to 0.5 mm; field correlation 10 mm.
- hotel (Hotel/layers_from_borders.py): masks upsampled x2 (0.75 mm), plain SDF on that grid (+-1 voxel,
                               slope 2, and a dead zone: a field value below one voxel moves no boundary voxel);
                               field correlation 6 mm.

Then one fixed error model (U): the slope-1 SDF on 0.5 mm, field correlation 8 mm (and 4 / 16 mm as a
sensitivity), sigma 0.25 / 0.5 / 1.0 mm, plus 0.5 mm endocardial and epicardial biases. In U it computes, per case:
subendocardial-third Dice, realised ASSD and signed bias per border, the per-segment thickness error, and STA (Kilo
v1 §6.2: a virtual subendocardial scar at depth tau in {0.15, 0.40, 0.65, 0.90} in each of segments 1-16, fixed
in the image; STA = share of the 64 scars whose Kim bin agrees between the reference wall and the perturbed wall).

Depth is the JA2 equal-thickness depth in every model, so only the error model differs.

    python harness_r2.py TS_DIR OUT_DIR [--cases N] [--workers 3]
"""
from __future__ import annotations

import argparse, glob, json, os, sys, traceback
from concurrent.futures import ProcessPoolExecutor

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lvgeom as G  # noqa: E402
from guard_r2 import refuse  # noqa: E402

MASKS = dict(myo="heart_myocardium", lv="heart_ventricle_left", rv="heart_ventricle_right",
             la="heart_atrium_left", ao="aorta")
TAUS = (0.15, 0.40, 0.65, 0.90)
KIM = np.array([0.0, 0.25, 0.50, 0.75, 1.0001])


# ------------------------------------------------------------------------------------------------ io

def load_masks(d, margin_mm=14.0):
    sid = os.path.basename(os.path.normpath(d))
    refuse("TotalSegmentator", sid)               # before a byte of the case is read
    im = nib.load(f"{d}/segmentations/{MASKS['myo']}.nii.gz")
    sp = np.array(im.header.get_zooms()[:3], float)
    m = {k: np.asanyarray(nib.load(f"{d}/segmentations/{v}.nii.gz").dataobj) > 0 for k, v in MASKS.items()}
    lvs = m["myo"] | m["lv"]
    if m["myo"].sum() < 2000 or m["lv"].sum() < 2000:
        return None, "no LV"
    idx = np.argwhere(lvs)
    mg = np.ceil(margin_mm / sp).astype(int)
    lo, hi = idx.min(0) - mg, idx.max(0) + mg + 1
    if (lo < 0).any() or (hi > np.array(lvs.shape)).any():
        return None, "LV touches the field-of-view edge"
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    aff = im.affine.copy()
    aff[:3, 3] = aff[:3, :3] @ lo + aff[:3, 3]
    out = {k: G.keep_largest(v[sl]) if k in ("myo", "lv") else v[sl] for k, v in m.items()}
    out["myo"] &= ~out["lv"]
    shell = ndi.binary_dilation(out["lv"], G.STRUCT) & ~out["lv"]
    enclosed = float((shell & (out["myo"] | out["la"] | out["ao"])).sum() / max(shell.sum(), 1))
    if enclosed < 0.85:
        return None, f"cavity not enclosed ({enclosed:.2f})"
    return dict(spacing=sp, affine=aff, **out), "ok"


# ------------------------------------------------------------------------------------------------ SDFs

def sdf_half(m, sp):
    """Slope-1 SDF: the surface half-way between voxel centres (+-sp/2 at the boundary voxels)."""
    h = float(np.mean(sp)) / 2
    return np.where(m, h - ndi.distance_transform_edt(m, sampling=sp),
                    ndi.distance_transform_edt(~m, sampling=sp) - h).astype(np.float32)


def sdf_plain(m, sp):
    """edt(~m) - edt(m): +-1 voxel at the boundary voxels (slope 2 across the boundary)."""
    return (ndi.distance_transform_edt(~m, sampling=sp) - ndi.distance_transform_edt(m, sampling=sp)).astype(np.float32)


def sdf_india(m, sp):
    h = 0.5 * float(np.mean(sp))
    return np.where(m, h / 2 - ndi.distance_transform_edt(m, sampling=sp),
                    ndi.distance_transform_edt(~m, sampling=sp) - h / 2).astype(np.float32)


def field(shape, grid, sigma, corr_mm, rng):
    if sigma == 0:
        return np.zeros(shape, np.float32)
    # drawn on a 4x coarser grid, smoothed, then upsampled (as India v1's lvgeom.smooth_noise): same correlation
    # length, about 50x faster; the Gaussian smoothing dominates the spectrum at corr >= 4 mm
    c = 4
    cs = tuple(int(np.ceil(s / c)) for s in shape)
    f = ndi.gaussian_filter(rng.standard_normal(cs).astype(np.float32), corr_mm / (grid * c))
    f = ndi.zoom(f, [s / q for s, q in zip(shape, cs)], order=1)[:shape[0], :shape[1], :shape[2]]
    return (f * (sigma / (f.std() + 1e-9))).astype(np.float32)


# ------------------------------------------------------------------------------------------------ geometry

def depth(myo, cav, sp):
    t, thick = G.depth_distance(myo, cav, sp)
    return t, thick


def surf(m):
    return m & ~ndi.binary_erosion(m, G.STRUCT, border_value=1)


def border_stats(cav_r, solid_r, cav_p, solid_p, myo_r, sp):
    """Realised endocardial / epicardial ASSD and signed bias (mm, + = outward) between two walls."""
    out = {}
    idx = np.argwhere(myo_r)
    lo, hi = np.maximum(idx.min(0) - 8, 0), np.minimum(idx.max(0) + 9, myo_r.shape)
    bb = tuple(slice(a, b) for a, b in zip(lo, hi))
    cav_r, solid_r, cav_p, solid_p, myo_r = cav_r[bb], solid_r[bb], cav_p[bb], solid_p[bb], myo_r[bb]
    near = ndi.binary_dilation(myo_r, G.STRUCT, iterations=4)
    for name, a, b in (("endo", cav_r, cav_p), ("epi", solid_r, solid_p)):
        sa, sb = surf(a) & near, surf(b) & near
        if not sa.any() or not sb.any():
            out[name] = None
            continue
        da = ndi.distance_transform_edt(~sb, sampling=sp)[sa]
        db = ndi.distance_transform_edt(~sa, sampling=sp)[sb]
        # signed: where on the reference surface does the perturbed solid lie outside (positive) or inside?
        S = sdf_half(b, sp)[sa]
        out[name] = dict(assd=float((da.sum() + db.sum()) / (len(da) + len(db))),
                         bias=float(-(np.mean(S) + float(np.mean(sp)) / 2)))
    return out


def third_dice(myo_r, t_r, myo_p, t_p):
    L_r, L_p = G.layers(t_r, myo_r), G.layers(t_p, myo_p)
    return [float(G.dice(L_r == k, L_p == k)) for k in (1, 2, 3)]


def kim(x):
    return int(np.searchsorted(KIM, x, side="right") - 1) if x > 0 else -1


# ------------------------------------------------------------------------------------------------ models

def model_walls(sub, name):
    """Return (grid, endo SDF, solid SDF, rv, la, affine) on that model's working grid, as its code builds them."""
    sp0, aff0 = sub["spacing"], sub["affine"]
    cav, solid = sub["lv"], sub["lv"] | sub["myo"]
    if name in ("golf", "U", "kilo"):
        g = 0.5
        f = sp0 / g
        fn = sdf_plain if name == "kilo" else sdf_half
        se, ss = ndi.zoom(fn(cav, sp0), f, order=1), ndi.zoom(fn(solid, sp0), f, order=1)
    elif name == "india":
        g = 0.5
        f = sp0 / g
        cv = ndi.zoom(cav.astype(np.float32), f, order=1) > 0.5
        so = ndi.zoom(solid.astype(np.float32), f, order=1) > 0.5
        se, ss = sdf_india(cv, np.full(3, g)), sdf_india(so | cv, np.full(3, g))
    elif name == "hotel":
        g = float(np.mean(sp0)) / 2
        f = np.full(3, 2.0)
        vox = lambda m: (ndi.distance_transform_edt(~m) - ndi.distance_transform_edt(m)).astype(np.float32)
        cv = ndi.zoom(vox(cav), f, order=1) < 0
        so = ndi.zoom(vox(solid), f, order=1) < 0
        se, ss = sdf_plain(cv, np.full(3, g)), sdf_plain(so | cv, np.full(3, g))
    else:
        raise ValueError(name)
    zm = lambda m: ndi.zoom(sdf_half(m, sp0), f, order=1) < 0
    aff = aff0.copy()
    aff[:3, :3] = aff0[:3, :3] / f
    return g, se, ss, zm(sub["rv"]), zm(sub["la"]), zm(sub["ao"]), aff


CORR = dict(golf=8.0, india=8.0, kilo=10.0, hotel=6.0)


def walls_from(se, ss):
    cav = se < 0
    solid = (ss < 0) | cav
    return cav, solid & ~cav, solid


def run_case(args):
    d, outdir = args
    sid = os.path.basename(os.path.normpath(d))
    path = os.path.join(outdir, f"{sid}.json")
    if os.path.exists(path):
        return sid, "cached"
    try:
        sub, why = load_masks(d)
        if sub is None:
            json.dump(dict(sid=sid, ok=False, why=why), open(path, "w"))
            return sid, why
        rng = np.random.default_rng(int(sid[1:]) + 7)
        res = dict(sid=sid, ok=True, spacing=sub["spacing"].tolist(), models={}, U=[])
        # ---- part 1: the four Round 1 models at their nominal 0.5 and 1.0 mm
        for name in ("golf", "india", "kilo", "hotel"):
            g, se, ss, rv, la, ao, aff = model_walls(sub, name)
            sp = np.full(3, g)
            cav_r, myo_r, sol_r = walls_from(se, ss)
            t_r, _ = depth(myo_r, cav_r, sp)
            rows = []
            for sig in (0.5, 1.0):
                n1, n2 = field(se.shape, g, sig, CORR[name], rng), field(se.shape, g, sig, CORR[name], rng)
                cav_p, myo_p, sol_p = walls_from(se + n1, ss + n2)
                t_p, _ = depth(myo_p, cav_p, sp)
                b = border_stats(cav_r, sol_r, cav_p, sol_p, myo_r, sp)
                rows.append(dict(sigma=sig, dice_myo=float(G.dice(myo_r, myo_p)),
                                 dice_thirds=third_dice(myo_r, t_r, myo_p, t_p), border=b))
            # the boundary gain: how far a uniform 0.5 mm field value moves the endocardium
            cav_p, myo_p, sol_p = walls_from(se - 0.5, ss)
            g05 = border_stats(cav_r, sol_r, cav_p, sol_p, myo_r, sp)["endo"]
            res["models"][name] = dict(grid=g, corr_mm=CORR[name], runs=rows, uniform_0p5_endo=g05)
        # ---- part 2: one error model U, with STA and segment thickness
        g, se, ss, rv, la, ao, aff = model_walls(sub, "U")
        sp = np.full(3, g)
        cav_r, myo_r, sol_r = walls_from(se, ss)
        t_r, th_r = depth(myo_r, cav_r, sp)
        geo = dict(myo=myo_r, lv=cav_r, rv=rv & ~sol_r, la=la & ~sol_r, affine=aff)
        fr = G.lv_frame(geo)
        if fr is None:
            res["U_skip"] = "no LV frame"
            json.dump(res, open(path, "w")); return sid, "no frame"
        seg_r = G.aha17(geo, fr)
        res["septal_arc_deg"] = float(fr["septal_arc_deg"])
        scars = {(s, tau): myo_r & (seg_r == s) & (t_r < tau) for s in range(1, 17) for tau in TAUS}

        def segtx(scar, myo, seg, s):
            m = myo & (seg == s)
            return (scar & m).sum() / m.sum() if m.sum() > 50 else np.nan

        ref_bin = {k: kim(segtx(v, myo_r, seg_r, k[0])) for k, v in scars.items()}
        th_seg_r = {s: float(np.median(th_r[myo_r & (seg_r == s)])) for s in range(1, 17) if (myo_r & (seg_r == s)).sum() > 50}
        conds = [("rand", s, c) for c in (8.0,) for s in (0.25, 0.5, 1.0)] + \
                [("rand", 0.5, c) for c in (4.0, 16.0)] + \
                [("endo_out", 0.5, 0), ("endo_in", 0.5, 0), ("epi_out", 0.5, 0)]
        for kind, sig, corr in conds:
            if kind == "rand":
                n1, n2 = field(se.shape, g, sig, corr, rng), field(se.shape, g, sig, corr, rng)
            else:
                n1 = np.float32(-sig if kind == "endo_out" else sig if kind == "endo_in" else 0)
                n2 = np.float32(-sig if kind == "epi_out" else 0)
            cav_p, myo_p, sol_p = walls_from(se + n1, ss + n2)
            t_p, th_p = depth(myo_p, cav_p, sp)
            geo_p = dict(myo=myo_p, lv=cav_p, rv=rv & ~sol_p, la=la & ~sol_p, affine=aff)
            fr_p = G.lv_frame(geo_p)
            seg_p = G.aha17(geo_p, fr_p) if fr_p is not None else seg_r * myo_p
            agree = [ref_bin[k] == kim(segtx(v, myo_p, seg_p, k[0])) for k, v in scars.items() if ref_bin[k] >= 0]
            th_err = [abs(float(np.median(th_p[myo_p & (seg_p == s)])) - th_seg_r[s])
                      for s in th_seg_r if (myo_p & (seg_p == s)).sum() > 50]
            th_sgn = [float(np.median(th_p[myo_p & (seg_p == s)])) - th_seg_r[s]
                      for s in th_seg_r if (myo_p & (seg_p == s)).sum() > 50]
            res["U"].append(dict(kind=kind, sigma=sig, corr=corr, dice_myo=float(G.dice(myo_r, myo_p)),
                                 dice_thirds=third_dice(myo_r, t_r, myo_p, t_p),
                                 border=border_stats(cav_r, sol_r, cav_p, sol_p, myo_r, sp),
                                 sta=float(np.mean(agree)) if agree else None, n_scars=len(agree),
                                 thick_err_median=float(np.median(th_err)) if th_err else None,
                                 thick_bias_median=float(np.median(th_sgn)) if th_sgn else None))
        json.dump(res, open(path, "w"))
        return sid, "ok"
    except Exception:
        json.dump(dict(sid=sid, ok=False, why=traceback.format_exc()[-800:]), open(path, "w"))
        return sid, "error"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ts_dir"); ap.add_argument("out_dir")
    ap.add_argument("--cases", type=int, default=40); ap.add_argument("--workers", type=int, default=3)
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

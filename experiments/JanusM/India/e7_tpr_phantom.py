"""India Round 2, E7: is rest TPR measurable at native 0.5 mm with a 1 mm guard band? (ruling §6 item 6, JA11)

A phantom built on real heart shapes (public TotalSegmentator v1 walls, E5's 0.5 mm slope-1 grid). Known truth:
- LV and RV blood 450 HU, LA and aorta 450 HU, myocardium with a known transmural ratio R (inner-third mean /
  outer-third mean): R = 1.00 (flat, 120 HU) or R = 1.08 (a normal endocardial gradient, Forte 2020 septal TPR
  1.06 and George 2009's normal > 0.99), epicardial fat -90 HU in a 3 mm shell outside the free wall, 40 HU
  elsewhere;
- the image is blurred by a Gaussian PSF (FWHM 0.6 mm for a 0.5 mm CCTA reconstruction; 1.5 mm as Round 1's
  grid) and gets correlated noise (SD 25 HU).

Per segment (AHA 1-16) it measures TPR = mean HU(inner third) / mean HU(outer third), with no guard band and with
a guard band (voxels within g mm of either border dropped; g = 0.5, 1.0, 1.5 mm), on the true borders and on borders
carrying E5's error model U (sigma 0.5 mm random, corr 8 mm; and 0.5 mm endocardial bias in / out). Reports the
median and IQR of (measured - true) over segments and cases, and the share of segments falsely < 0.99 when the
truth is 1.08 (a false "defect").

    python e7_tpr_phantom.py TS_DIR OUT_DIR [--cases N] [--workers 3]
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
from harness_r2 import MASKS, load_masks, model_walls, walls_from, field  # noqa: E402

BLOOD, MYO, FAT, OTHER = 450.0, 120.0, -90.0, 40.0
GUARDS = (0.0, 0.5, 1.0, 1.5)


def phantom(cav, myo, sol, rv, la, ao, t, R, sp, fwhm, rng, noise=25.0):
    img = np.full(cav.shape, OTHER, np.float32)
    d_out = ndi.distance_transform_edt(~sol, sampling=sp)
    img[(d_out <= 3.0) & ~sol & ~rv & ~la & ~ao] = FAT
    img[cav | rv | la | ao] = BLOOD
    # transmural profile: linear in depth t with inner-third mean / outer-third mean = R, mean MYO
    # mean over third k of a + b t: a + b * (k - 0.5) / 3 ; ratio (a + b/6) / (a + 5b/6) = R
    a = 1.0
    b = (1 - R) / (R * 5 / 6 - 1 / 6) if R != 1 else 0.0
    prof = a + b * t
    img[myo] = (MYO * prof[myo] / (a + b / 2)).astype(np.float32)
    if fwhm > 0:
        img = ndi.gaussian_filter(img, fwhm / 2.355 / sp[0])
    n = ndi.gaussian_filter(rng.standard_normal(img.shape).astype(np.float32), 0.5 / sp[0])
    img += n * (noise / (n.std() + 1e-9))
    return img


def tpr_segments(img, myo, cav, sol, t, seg, sp, guard):
    d_endo = ndi.distance_transform_edt(~cav, sampling=sp)
    d_epi = ndi.distance_transform_edt(sol, sampling=sp)
    core = myo & (d_endo > guard + sp[0] / 2) & (d_epi > guard)
    L = G.layers(t, myo)
    out = {}
    for s in range(1, 17):
        m = core & (seg == s)
        a, b = img[m & (L == 1)], img[m & (L == 3)]
        if len(a) >= 10 and len(b) >= 10 and b.mean() > 20:
            out[s] = float(a.mean() / b.mean())
    return out


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
        rng = np.random.default_rng(int(sid[1:]) + 13)
        g, se, ss, rv, la, ao, aff = model_walls(sub, "U")
        sp = np.full(3, g)
        cav, myo, sol = walls_from(se, ss)
        rv, la, ao = rv & ~sol, la & ~sol, ao & ~sol
        geo = dict(myo=myo, lv=cav, rv=rv, la=la, affine=aff)
        fr = G.lv_frame(geo)
        if fr is None:
            json.dump(dict(sid=sid, ok=False, why="no frame"), open(path, "w")); return sid, "no frame"
        t, _ = G.depth_distance(myo, cav, sp)
        seg = G.aha17(geo, fr)
        # measurement borders: true, random U, endo bias in / out
        n1, n2 = field(se.shape, g, 0.5, 8.0, rng), field(se.shape, g, 0.5, 8.0, rng)
        borders = {"true": (cav, myo, sol), "rand0.5": walls_from(se + n1, ss + n2),
                   "endo_in0.5": walls_from(se + 0.5, ss), "endo_out0.5": walls_from(se - 0.5, ss)}
        meas = {}
        for k, (c2, m2, s2) in borders.items():
            if k == "true":
                meas[k] = (c2, m2, s2, t, seg)
            else:
                g2 = dict(myo=m2, lv=c2, rv=rv & ~s2, la=la & ~s2, affine=aff)
                f2 = G.lv_frame(g2)
                t2, _ = G.depth_distance(m2, c2, sp)
                meas[k] = (c2, m2, s2, t2, G.aha17(g2, f2) if f2 is not None else seg * m2)
        res = dict(sid=sid, ok=True, rows=[])
        for R in (1.00, 1.08):
            clean = phantom(cav, myo, sol, rv, la, ao, t, R, sp, 0.0, rng, noise=0.0)
            res["rows"].append(dict(R=R, fwhm=0.0, borders="true", guard=0.0,
                                    tpr=tpr_segments(clean, myo, cav, sol, t, seg, sp, 0.0)))
            for fwhm in (0.6, 1.5):
                img = phantom(cav, myo, sol, rv, la, ao, t, R, sp, fwhm, rng)
                for k, (c2, m2, s2, t2, sg2) in meas.items():
                    for gd in GUARDS:
                        v = tpr_segments(img, m2, c2, s2, t2, sg2, sp, gd)
                        res["rows"].append(dict(R=R, fwhm=fwhm, borders=k, guard=gd, tpr=v))
        json.dump(res, open(path, "w"))
        return sid, "ok"
    except Exception:
        json.dump(dict(sid=sid, ok=False, why=traceback.format_exc()[-800:]), open(path, "w"))
        return sid, "error"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ts_dir"); ap.add_argument("out_dir")
    ap.add_argument("--cases", type=int, default=20); ap.add_argument("--workers", type=int, default=3)
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

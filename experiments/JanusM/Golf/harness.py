"""Golf R2 E7: one perturbation harness, and why the four Round 1 simulations disagree (ruling section 6 item 2).

At a nominal 0.5 mm border error the Round 1 subendocardial-third Dice was 0.909 (Golf), 0.927 (India), 0.939 (Kilo)
and 0.975 (Hotel). The four codes differ in three ways (read from the committed code):
  - signed distance: Golf and India put the surface half-way between voxel centres (slope 1 across the border);
    Hotel and Kilo use edt(~m) - edt(m), which jumps by two voxels across the border, so a displacement smaller than
    about one voxel moves nothing (a dead band);
  - grid: Golf 0.5 mm (interpolated); Kilo 0.5 mm; Hotel and India on the native 1.5 mm grid;
  - correlation length of the smooth field: Hotel 6, Golf 8, India 8, Kilo 10 mm.
This harness runs every combination on the same hearts, and reports the error each one actually *realises*
(ASSD between the perturbed and the reference border), next to the nominal RMS. It also reports the Kim-bin flip
rate of a fixed synthetic scar, which is the core of Kilo's STA.

Data: the public TotalSegmentator v2.0.1 gated-like cases that pass guard_r2 (fetch_ts_r2.py).
Usage: python harness.py <ts_dir> [--cases 10] [--np 3]      writes harness.json
"""
import argparse, json, sys
from multiprocessing import Pool
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from guard_r2 import refuse  # noqa: E402
from layers_ts import MYO, LV, depth, thirds, dice  # noqa: E402

SIGMAS = [0.25, 0.5, 1.0]
VARIANTS = [  # name, signed-distance kind, grid mm, correlation mm
    ("half-voxel sdf, 0.5 mm, corr 8 (Golf)", "half", 0.5, 8.0),
    ("half-voxel sdf, 0.5 mm, corr 6", "half", 0.5, 6.0),
    ("half-voxel sdf, 0.5 mm, corr 10", "half", 0.5, 10.0),
    ("half-voxel sdf, 1.5 mm, corr 8 (India)", "half", 1.5, 8.0),
    ("plain sdf, 0.5 mm, corr 10 (Kilo)", "plain", 0.5, 10.0),
    ("plain sdf, 1.5 mm, corr 6 (Hotel)", "plain", 1.5, 6.0),
]
KIM_MID = [0.15, 0.35, 0.60, 0.90]


def sdf(m, sp, kind):
    a, b = ndi.distance_transform_edt(~m, sampling=sp), ndi.distance_transform_edt(m, sampling=sp)
    if kind == "plain":
        return a - b
    h = float(np.mean(sp)) / 2
    return (a - h) * ~m - (b - h) * m


def field(shape, sp, corr, rms, rng):
    f = ndi.gaussian_filter(rng.standard_normal(shape).astype(np.float32), corr / np.asarray(sp))
    return f * (rms / (f.std() + 1e-9))


def surf(m):
    return m & ~ndi.binary_erosion(m)


def assd(a, b, sp):
    sa, sb = surf(a), surf(b)
    da, db = ndi.distance_transform_edt(~sa, sampling=sp), ndi.distance_transform_edt(~sb, sampling=sp)
    return float((db[sa].mean() + da[sb].mean()) / 2)


def sectors(myo, cav, n=16):
    """16 equal circumferential x longitudinal sectors (a stand-in for AHA segments, same on every variant)."""
    P = np.argwhere(myo | cav).astype(float)
    c = P.mean(0)
    _, _, vt = np.linalg.svd(P - c, full_matrices=False)
    X = np.argwhere(np.ones(myo.shape, bool)).astype(float) - c
    s = X @ vt[0]; a = np.arctan2(X @ vt[2], X @ vt[1])
    lo, hi = np.percentile(P @ vt[0] - c @ vt[0], [2, 98])
    lev = np.clip(((s - lo) / (hi - lo) * 3).astype(int), 0, 2)
    sec = ((a + np.pi) / (2 * np.pi) * 6).astype(int) % 6
    return (lev * 6 + sec + 1).reshape(myo.shape)          # 1..18


def kim(f):
    f = np.asarray(f) * 100
    return np.select([f <= 0.5, f <= 25, f <= 50, f <= 75], [0, 1, 2, 3], 4)


def run_case(args):
    case_dir, idx = args
    refuse("TotalSegmentator-cardiac", case_dir.name)
    rng = np.random.default_rng(7000 + idx)
    ct = nib.load(case_dir / "ct.nii.gz")
    sp0 = np.array(ct.header.get_zooms()[:3], float)
    L = np.asanyarray(nib.load(case_dir / "cardiac_label.nii.gz").dataobj) > 0.5
    myo0, cav0 = L[MYO], L[LV]
    nz = np.argwhere(myo0 | cav0); m = 6
    sl = tuple(slice(max(a - m, 0), b + m + 1) for a, b in zip(nz.min(0), nz.max(0)))
    myo0, cav0 = myo0[sl], cav0[sl] & ~myo0[sl]
    out = {"case": case_dir.name, "rows": []}
    for name, kind, g, corr in VARIANTS:
        z = sp0 / g
        sp = np.full(3, g)
        if g == 1.5 and np.allclose(sp0, 1.5):
            cav, solid = cav0, myo0 | cav0
        else:   # interpolate the reference surfaces to the grid (always with the half-voxel sdf, so the reference is fair)
            cav = ndi.zoom(sdf(cav0, sp0, "half").astype(np.float32), z, order=1) < 0
            solid = ndi.zoom(sdf(myo0 | cav0, sp0, "half").astype(np.float32), z, order=1) < 0
        myo = solid & ~cav
        th = thirds(depth(myo, cav, sp), myo)
        u = depth(myo, cav, sp)
        sec = sectors(myo, cav) * myo
        tgt = np.zeros(19); tgt[1:] = rng.choice(KIM_MID, 18)
        scar = myo & (u < tgt[sec])
        tb = kim([scar[sec == k].sum() / max((sec == k).sum(), 1) for k in range(1, 19)])
        s_c, s_s = sdf(cav, sp, kind), sdf(solid, sp, kind)
        for sg in SIGMAS:
            for rep in range(2):
                cav2 = (s_c + field(cav.shape, sp, corr, sg, rng)) < 0
                sol2 = (s_s + field(cav.shape, sp, corr, sg, rng)) < 0
                cav2 &= sol2
                myo2 = sol2 & ~cav2
                th2 = thirds(depth(myo2, cav2, sp), myo2)
                fb = kim([(scar & myo2 & (sec == k)).sum() / max((myo2 & (sec == k)).sum(), 1) for k in range(1, 19)])
                out["rows"].append({
                    "variant": name, "sigma": sg, "rep": rep,
                    "realised_endo_assd": assd(cav2, cav, sp), "realised_epi_assd": assd(sol2, solid, sp),
                    "voxels_changed_endo": float((cav2 != cav).sum() / max(surf(cav).sum(), 1)),
                    "dice_myo": dice(myo2, myo), "dice_subendo": dice(th2 == 1, th == 1),
                    "kim_flip": float((fb != tb).mean())})
        print(case_dir.name, name, flush=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("ts_dir", type=Path)
    ap.add_argument("--cases", type=int, default=10)
    ap.add_argument("--np", type=int, default=3)
    a = ap.parse_args()
    ids = sorted(json.loads((HERE / "ts_cases_r2.json").read_text()))[:a.cases]
    with Pool(a.np) as p:
        res = p.map(run_case, [(a.ts_dir / i, n) for n, i in enumerate(ids)], chunksize=1)
    rows = [r for c in res for r in c["rows"]]
    summ = []
    for name, *_ in VARIANTS:
        for sg in SIGMAS:
            R = [r for r in rows if r["variant"] == name and r["sigma"] == sg]
            summ.append({"variant": name, "sigma_nominal": sg, "n": len(R), **{
                k: float(np.median([r[k] for r in R])) for k in
                ("realised_endo_assd", "realised_epi_assd", "voxels_changed_endo", "dice_myo", "dice_subendo", "kim_flip")}})
    (HERE / "harness.json").write_text(json.dumps({"summary": summ, "cases": res}, indent=1) + "\n")
    for s in summ:
        print(json.dumps(s))

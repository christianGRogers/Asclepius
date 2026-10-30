"""E4 (Round 2 ruling §7 item 2): validate the JA15 harness's ASSD, signed-bias and thickness implementations, and
decide whether a signed-bias estimator meets JA16's +-0.05 mm (which sets the guard at 0.3 or 0.5 mm).

Two test beds:
A. **Analytic shells** (exact truth). Spheres and concentric shells on a 0.5 mm grid, centre jittered by a random
   sub-voxel offset; the perturbed border is the *exact* sphere of radius R + d. True ASSD = |d|, true signed bias
   = d, true thickness change = -d (endocardium out) or +d (epicardium out).
B. **Real walls, the JA15 way.** The 23 guard-allowed public walls (1.5 mm labels to a 0.5 mm grid through the
   half-voxel-corrected signed distance); each border shifted by the harness's own rule, S_ref - d < 0, for
   d in {-0.5, -0.3, +0.3, +0.5} mm.

Signed-bias estimators compared (+ = outward):
- B1 `inner_boundary`  Lima R2: mean reference signed distance at the perturbed mask's inner-boundary voxels + h/2;
- B2 `face_midpoint`   mean, over every face between an inside and an outside voxel of the perturbed mask, of the
                       reference signed distance at the face midpoint (the average of its two voxels' values);
- B3 `volume_area`     (V_perturbed - V_reference) / A_reference, A by marching cubes (Hotel's mean |d|, signed);
- B4 `two_way`         half the difference of the mean signed surface-to-surface distances in both directions;
- B5 `volume_midarea`  (V_perturbed - V_reference) / mean(A_reference, A_perturbed), each A by marching cubes on the
                       smooth zero level set of the corrected signed distance (Lima R3 proposal; the signed distance is smoothed by 0.5 mm first).

ASSD: `segtrain.metrics.surface_distances` (the read queue's, `janusm_reads.anchoring.assd`), which is the same
voxel-surface definition as `harness.py`. Thickness: `harness.et_depth` (JA2) median.

    python e4_estimators.py TS_DIR OUT_JSON [--jobs 4]
"""
import argparse
import json
import os
import sys
from multiprocessing import Pool

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi
from skimage.measure import marching_cubes, mesh_surface_area

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.dirname(HERE))
from janusm.guard import refuse  # noqa: E402  (JA22: before any case is opened)
from segtrain.metrics import surface_distances  # noqa: E402

GRID = 0.5
SP = np.full(3, GRID)
FACE = ndi.generate_binary_structure(3, 1)


def csdf(m):
    """Half-voxel-corrected signed distance (mm, negative inside): JA15's model."""
    h = GRID / 2
    return np.where(m, h - ndi.distance_transform_edt(m, sampling=SP),
                    ndi.distance_transform_edt(~m, sampling=SP) - h).astype(np.float32)


def assd(a, b):
    d1, d2 = surface_distances(a, b, SP)
    return float((d1.sum() + d2.sum()) / (d1.size + d2.size))


def area(m):
    v, f, _, _ = marching_cubes(np.pad(m, 1).astype(np.float32), 0.5, spacing=tuple(SP))
    return mesh_surface_area(v, f)


def area_sdf(m):
    """Area of the zero level set of the corrected signed distance of m, smoothed by a 0.5 mm Gaussian. Unsmoothed,
    marching cubes counts the voxel staircase: +8.8 % on exact spheres of radius 12-29 mm, against +0.3 % after
    smoothing (checked in this round)."""
    s = np.pad(ndi.gaussian_filter(csdf(m), 0.5 / GRID), 1, constant_values=GRID)
    v, f, _, _ = marching_cubes(s, 0.0, spacing=tuple(SP))
    return mesh_surface_area(v, f)


def estimators(pert, ref, S_ref):
    inner = pert & ~ndi.binary_erosion(pert, FACE)
    b1 = float(S_ref[inner].mean() + GRID / 2)
    vals = []
    for ax in range(3):
        a = np.moveaxis(pert, ax, 0)
        s = np.moveaxis(S_ref, ax, 0)
        edge = a[:-1] != a[1:]
        vals.append(((s[:-1] + s[1:]) / 2)[edge])
    b2 = float(np.concatenate(vals).mean())
    b3 = float((pert.sum() - ref.sum()) * GRID ** 3 / area(ref))
    # B5: volume change over the mean of the two borders' smooth areas (cancels the first curvature term)
    b5 = float((pert.sum() - ref.sum()) * GRID ** 3 / ((area_sdf(ref) + area_sdf(pert)) / 2))
    # two-way: signed distance of each surface to the other, signed by inside/outside of the other mask
    sp_, sr_ = pert & ~ndi.binary_erosion(pert, FACE), ref & ~ndi.binary_erosion(ref, FACE)
    d_pr = ndi.distance_transform_edt(~sr_, sampling=SP)[sp_] * np.where(ref[sp_], -1, 1)
    d_rp = ndi.distance_transform_edt(~sp_, sampling=SP)[sr_] * np.where(pert[sr_], -1, 1)
    b4 = float((d_pr.mean() - d_rp.mean()) / 2)
    return {"inner_boundary": b1, "face_midpoint": b2, "volume_area": b3, "two_way": b4, "volume_midarea": b5}


def et_thick(myo, cav):
    de = ndi.distance_transform_edt(~cav, sampling=SP)
    dp = ndi.distance_transform_edt(myo | cav, sampling=SP)
    return float(np.median((de + dp - GRID)[myo]))


# ------------------------------------------------------------------ A. analytic shells
def analytic(seed=0, n_offsets=6):
    rng = np.random.default_rng(seed)
    rows = []
    for r_endo, wall in ((20.0, 9.0), (12.0, 6.0)):
        r_epi = r_endo + wall
        n = int(2 * (r_epi + 4) / GRID)
        ax = (np.arange(n) - n / 2) * GRID
        X, Y, Z = np.meshgrid(ax, ax, ax, indexing="ij")
        for _ in range(n_offsets):
            c = rng.uniform(-GRID / 2, GRID / 2, 3)
            R = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2)
            cav, sol = R < r_endo, R < r_epi
            S_cav, S_sol = csdf(cav), csdf(sol)
            th0 = et_thick(sol & ~cav, cav)
            for border in ("endo", "epi"):
                for d in (-1.0, -0.5, -0.3, -0.1, 0.1, 0.3, 0.5, 1.0):
                    if border == "endo":
                        cav2, sol2, ref, pert, S = R < r_endo + d, sol, cav, R < r_endo + d, S_cav
                        dth_true = -d
                    else:
                        cav2, sol2, ref, pert, S = cav, R < r_epi + d, sol, R < r_epi + d, S_sol
                        dth_true = d
                    e = estimators(pert, ref, S)
                    rows.append({"bed": "analytic", "r_endo": r_endo, "border": border, "shift": d,
                                 "assd": assd(pert, ref), "thick_change": et_thick(sol2 & ~cav2, cav2) - th0,
                                 "thick_change_true": dth_true, **e})
    return rows


def sdf_rule_on_spheres(seed=1, n_offsets=3):
    """What the JA15 harness's shift rule (S_ref - d < 0) actually realises, on exact spheres: the realised shift by
    the exact estimator (volume_midarea) and the voxel ASSD, against the nominal d."""
    rng = np.random.default_rng(seed)
    rows = []
    for R in (20.0, 12.0):
        n = int(2 * (R + 4) / GRID)
        ax = (np.arange(n) - n / 2) * GRID
        X, Y, Z = np.meshgrid(ax, ax, ax, indexing="ij")
        for _ in range(n_offsets):
            c = rng.uniform(-GRID / 2, GRID / 2, 3)
            Rr = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2)
            ref = Rr < R
            S = csdf(ref)
            for d in (-0.5, -0.3, 0.3, 0.5):
                pert = (S - d) < 0
                rows.append({"r": R, "nominal": d, "realised": estimators(pert, ref, S)["volume_midarea"],
                             "assd": assd(pert, ref)})
    return rows


# ------------------------------------------------------------------ B. real walls, JA15 shifts
def real(case_dir):
    sid = os.path.basename(case_dir)
    refuse([sid], what=f"Lima R3 E4 {sid}", source="TotalSegmentator")
    d = os.path.join(case_dir, "segmentations")
    img = nib.load(os.path.join(d, "heart_myocardium.nii.gz"))
    sp0 = np.array(img.header.get_zooms()[:3], float)
    myo = np.asanyarray(img.dataobj) > 0
    lv = np.asanyarray(nib.load(os.path.join(d, "heart_ventricle_left.nii.gz")).dataobj) > 0
    if myo.sum() * sp0.prod() < 50e3 or lv.sum() * sp0.prod() < 20e3:
        return []
    box = myo | lv
    lo = np.maximum(np.argwhere(box).min(0) - 8, 0)
    hi = np.minimum(np.argwhere(box).max(0) + 9, box.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    f = sp0 / GRID

    def up(m):
        h = float(np.mean(sp0)) / 2
        s = np.where(m, h - ndi.distance_transform_edt(m, sampling=sp0),
                     ndi.distance_transform_edt(~m, sampling=sp0) - h).astype(np.float32)
        return ndi.zoom(s, f, order=1) < 0

    cav = up(lv[sl])
    sol = up((myo | lv)[sl]) | cav
    S_cav, S_sol = csdf(cav), csdf(sol)
    th0 = et_thick(sol & ~cav, cav)
    rows = []
    for border in ("endo", "epi"):
        for dd in (-0.5, -0.3, 0.3, 0.5):
            if border == "endo":
                pert = (S_cav - dd) < 0
                cav2, sol2, ref, S = pert & sol, sol, cav, S_cav
                dth_true = -dd
            else:
                pert = (S_sol - dd) < 0
                cav2, sol2, ref, S = cav, pert | cav, sol, S_sol
                dth_true = dd
            e = estimators(pert, ref, S)
            rows.append({"bed": "real", "case": sid, "border": border, "shift": dd, "assd": assd(pert, ref),
                         "thick_change": et_thick(sol2 & ~cav2, cav2) - th0, "thick_change_true": dth_true, **e})
    return rows


def summarise(rows):
    est = ("inner_boundary", "face_midpoint", "volume_area", "two_way", "volume_midarea")
    out = {}
    for bed in ("analytic", "real"):
        R = [r for r in rows if r["bed"] == bed]
        tab = []
        for border in ("endo", "epi"):
            for d in sorted({r["shift"] for r in R}):
                s = [r for r in R if r["border"] == border and r["shift"] == d]
                if not s:
                    continue
                row = {"border": border, "shift": d, "n": len(s),
                       "assd_median": round(float(np.median([r["assd"] for r in s])), 3),
                       "thick_change_median": round(float(np.median([r["thick_change"] for r in s])), 3),
                       "thick_change_true": s[0]["thick_change_true"]}
                for e in est:
                    err = np.array([r[e] - d for r in s])
                    row[e + "_err_median"] = round(float(np.median(err)), 3)
                    row[e + "_err_maxabs"] = round(float(np.abs(err).max()), 3)
                tab.append(row)
        out[bed] = tab
        # JA16 test: a known 0.5 mm shift, each direction, each border, within +-0.05 mm (median over cases;
        # and the worst case, reported)
        verdict = {}
        for e in est:
            ok_med, ok_all = True, True
            for t in tab:
                if abs(t["shift"]) == 0.5:
                    ok_med &= abs(t[e + "_err_median"]) <= 0.05
                    ok_all &= t[e + "_err_maxabs"] <= 0.05
            verdict[e] = {"median_within_0p05": bool(ok_med), "every_case_within_0p05": bool(ok_all)}
        out[bed + "_ja16"] = verdict
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ts_dir"); ap.add_argument("out"); ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--sdf-rule-only", help="write only the sphere test of the harness shift rule to this JSON")
    a = ap.parse_args()
    if a.sdf_rule_only:
        r = sdf_rule_on_spheres()
        summ = {str(d): {"realised": [round(min(x["realised"] for x in r if x["nominal"] == d), 3),
                                      round(max(x["realised"] for x in r if x["nominal"] == d), 3)],
                         "assd_median": round(float(np.median([x["assd"] for x in r if x["nominal"] == d])), 3)}
                for d in (-0.5, -0.3, 0.3, 0.5)}
        json.dump({"summary": summ, "rows": r}, open(a.sdf_rule_only, "w"), indent=1)
        print(json.dumps(summ, indent=1))
        return
    base = os.path.join(a.ts_dir, "Totalsegmentator_dataset")
    subj = sorted(s for s in os.listdir(base) if s.startswith("s"))
    refuse(subj, what="Lima R3 E4 case list", source="TotalSegmentator")  # the whole list first, then each case
    rows = analytic()
    print("analytic", len(rows), flush=True)
    with Pool(a.jobs) as p:
        for r in p.imap_unordered(real, [os.path.join(base, s) for s in subj]):
            rows += r
            print(r[0]["case"] if r else "skip", flush=True)
    s = summarise(rows)
    json.dump({"summary": s, "rows": [{k: v for k, v in r.items() if k != "case"} for r in rows]},
              open(a.out, "w"), indent=1)
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    main()

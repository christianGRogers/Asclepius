"""Kilo experiments E1-E3 on public TotalSegmentator v1 cardiac cases (CPU).

E1  Geometry: wall thickness, voxels across the wall, AHA 17 segments, Laplace vs distance
    depth agreement, on the reference masks.
E2  Boundary-error sensitivity of derived layers: perturb the endo- and epicardial surfaces
    with smooth random displacement (RMS sigma mm, 10 mm correlation length) or a fixed 1 mm
    endocardial bias, on a 0.5 mm grid (CCTA-like) and on the native 1.5 mm grid. Report
    myocardium Dice, per-third Dice, the fraction of voxels that change third, per-segment
    thickness error and the error in a synthetic subendocardial scar's segmental
    transmurality (and how often it changes Kim et al. 2000 bin).
E3  Rest transmural attenuation ratio (inner third / outer third mean HU) per segment, with
    and without a 1-voxel guard band, and its shift under boundary error.

Usage: python exp_layers.py DATA_DIR OUT_JSON [--grid 0.5] [--reps 2] [--jobs 4]
"""
from __future__ import annotations

import argparse, json, pathlib, sys
from concurrent.futures import ProcessPoolExecutor

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from layers import laplace_depth, distance_depth, thirds, aha17  # noqa: E402

KEYS = ("heart_myocardium", "heart_ventricle_left", "heart_ventricle_right",
        "heart_atrium_left", "aorta")
SIGMAS = (0.0, 0.5, 1.0, 1.5)
TAUS = (0.15, 0.40, 0.65, 0.90)  # centred in Kim bins 1-25, 26-50, 51-75, 76-100 %
KIM = np.array([0.0, 0.25, 0.50, 0.75, 1.0001])


def sdf(m, sp):
    m = m.astype(bool)
    return (ndi.distance_transform_edt(~m, sampling=sp) - ndi.distance_transform_edt(m, sampling=sp)).astype(np.float32)


def load(case):
    L = {k: np.asanyarray(nib.load(case / f"segmentations/{k}.nii.gz").dataobj) > 0 for k in KEYS}
    ct = nib.load(case / "ct.nii.gz")
    return L, np.asanyarray(ct.dataobj).astype(np.float32), ct.affine, np.array(ct.header.get_zooms()[:3], float)


def crop(L, img, margin=12):
    box = L["heart_myocardium"] | L["heart_ventricle_left"]
    lo = np.maximum(np.argwhere(box).min(0) - margin, 0)
    hi = np.minimum(np.argwhere(box).max(0) + margin + 1, box.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    return {k: v[sl] for k, v in L.items()}, img[sl], lo


def field(shape, sp, sigma, corr_mm, rng):
    if sigma == 0: return np.zeros(shape, np.float32)
    f = ndi.gaussian_filter(rng.standard_normal(shape).astype(np.float32), corr_mm / sp)
    return (f / f.std() * sigma).astype(np.float32)


def derive(myo, cav, rv, la, nf, aff, sp):
    t, info = laplace_depth(myo, cav, nf)
    _, th = distance_depth(myo, cav, nf, sp)
    seg, _ = aha17(myo, cav, rv, la, aff)
    return t, th, thirds(t), seg


def dice(a, b):
    s = a.sum() + b.sum()
    return float(2 * (a & b).sum() / s) if s else float("nan")


def transmurality(scar, myo, seg, s):
    m = myo & (seg == s)
    return (scar & m).sum() / m.sum() if m.sum() > 50 else np.nan


def run_case(args):
    case, grid, reps = args
    from heldout import check
    check(pathlib.Path(case).name)  # refuses any held-out pool patient before a file is opened
    case = pathlib.Path(case); rng = np.random.default_rng(int(case.name[1:]))
    L, img, aff, sp0 = load(case)
    out = {"case": case.name}
    if L["heart_myocardium"].sum() < 1000 or L["heart_ventricle_left"].sum() < 1000:
        out["skip"] = "no LV myocardium / cavity in mask"; return out
    L, img, lo = crop(L, img)
    aff = aff.copy(); aff[:3, 3] = aff[:3, :3] @ lo + aff[:3, 3]
    # E1 / E3 on native grid
    myo, cav, rv, la, ao = (L[k] for k in KEYS); nf = la | ao
    t, th, tr, seg = derive(myo, cav, rv, la, nf, aff, sp0)
    td, _ = distance_depth(myo, cav, nf, sp0)
    out["native_spacing"] = sp0.tolist()
    out["lv_cavity_HU_median"] = float(np.median(img[cav]))
    out["myo_HU_median"] = float(np.median(img[myo]))
    out["myo_ml"] = float(myo.sum() * np.prod(sp0) / 1000)
    out["thick_mm_p10_50_90"] = np.nanpercentile(th[myo], [10, 50, 90]).tolist()
    out["vox_across_wall_native_median"] = float(np.nanmedian(th[myo]) / sp0.mean())
    out["laplace_vs_distance_same_third"] = float((tr[myo] == thirds(td)[myo]).mean())
    out["seg_thick_mm"] = {int(s): float(np.nanmedian(th[myo & (seg == s)])) for s in range(1, 18) if (myo & (seg == s)).sum() > 20}
    # E3: rest transmural attenuation ratio per segment (segments 1-16)
    d_endo = ndi.distance_transform_edt(~cav, sampling=sp0); d_epi = ndi.distance_transform_edt(myo, sampling=sp0)
    guard = (d_endo > 1.5 * sp0.mean()) & (d_epi > 1.0 * sp0.mean())
    def tpr(tr_, myo_, seg_, g=None):
        r = {}
        for s in range(1, 17):
            m = myo_ & (seg_ == s) if g is None else myo_ & (seg_ == s) & g
            a, b = img[m & (tr_ == 1)], img[m & (tr_ == 3)]
            if len(a) > 10 and len(b) > 10: r[s] = float(np.mean(a) / np.mean(b))
        return r
    out["contrast"] = bool(out["lv_cavity_HU_median"] > 150)  # E3 needs contrast-enhanced blood pool
    if not out["contrast"]:
        out["E3_tpr"] = out["E3_tpr_guard"] = None; out["E3_tpr_sigma1"] = []
        S_cav, S_full = sdf(cav, sp0), sdf(myo | cav, sp0)
        return e2(out, L, cav, myo, aff, sp0, S_cav, S_full, grid, reps, rng)
    out["E3_tpr"] = tpr(tr, myo, seg); out["E3_tpr_guard"] = tpr(tr, myo, seg, guard)
    # E3 under boundary error, native grid
    S_cav, S_full = sdf(cav, sp0), sdf(myo | cav, sp0)
    e3 = []
    for r in range(reps):
        n1, n2 = field(cav.shape, sp0.mean(), 1.0, 10, rng), field(cav.shape, sp0.mean(), 1.0, 10, rng)
        cp = (S_cav < n1); mp = (S_full < n2) & ~cp
        _, _, trp, segp = derive(mp, cp, rv & ~mp & ~cp, la, nf & ~mp & ~cp, aff, sp0)
        e3.append(tpr(trp, mp, segp))
    out["E3_tpr_sigma1"] = e3
    return e2(out, L, cav, myo, aff, sp0, S_cav, S_full, grid, reps, rng)


def e2(out, L, cav, myo, aff, sp0, S_cav, S_full, grid, reps, rng):
    """E2 on the chosen grid."""
    f = sp0.mean() / grid
    up = lambda S: ndi.zoom(S, f, order=1) < 0
    Sx = {k: sdf(L[k], sp0) for k in ("heart_ventricle_right", "heart_atrium_left", "aorta")}
    S_cav_u, S_full_u = ndi.zoom(S_cav, f, order=1), ndi.zoom(S_full, f, order=1)
    rv_u, la_u, ao_u = (up(Sx[k]) for k in ("heart_ventricle_right", "heart_atrium_left", "aorta"))
    sp = np.full(3, grid); affu = aff.copy(); affu[:3, :3] = aff[:3, :3] / f
    cav_r = S_cav_u < 0; myo_r = (S_full_u < 0) & ~cav_r
    rv_u &= ~myo_r & ~cav_r; nf_u = (la_u | ao_u) & ~myo_r & ~cav_r
    t_r, th_r, tr_r, seg_r = derive(myo_r, cav_r, rv_u, la_u, nf_u, affu, sp)
    out["grid"] = grid
    out["vox_across_wall_grid_median"] = float(np.nanmedian(th_r[myo_r]) / grid)
    scars = {(s, tau): myo_r & (seg_r == s) & (t_r < tau) for s in range(1, 17) for tau in TAUS}
    est_r = {k: transmurality(v, myo_r, seg_r, k[0]) for k, v in scars.items()}
    seg_th_r = {s: np.nanmedian(th_r[myo_r & (seg_r == s)]) for s in range(1, 17)}
    rows = []
    conds = [("random", s) for s in SIGMAS[1:]] + [("endo_bias_in", 1.0), ("endo_bias_out", 1.0)]
    for kind, sig in conds:
        for r in range(reps if kind == "random" else 1):
            if kind == "random":
                n1 = field(cav_r.shape, grid, sig, 10, rng); n2 = field(cav_r.shape, grid, sig, 10, rng)
            else:
                n1 = np.full(cav_r.shape, -sig if kind == "endo_bias_in" else sig, np.float32); n2 = 0
            cp = S_cav_u < n1; mp = (S_full_u < n2) & ~cp
            rvp = rv_u & ~mp & ~cp; nfp = nf_u & ~mp & ~cp
            tp, thp, trp, segp = derive(mp, cp, rvp, la_u, nfp, affu, sp)
            both = myo_r & mp
            row = {"kind": kind, "sigma_mm": sig, "rep": r,
                   "dice_myo": dice(myo_r, mp),
                   "dice_third": [dice((tr_r == k) & myo_r, (trp == k) & mp) for k in (1, 2, 3)],
                   "frac_third_changed": float((tr_r[both] != trp[both]).mean()),
                   "dice_seg_mean": float(np.nanmean([dice(seg_r == s, segp == s) for s in range(1, 18)])),
                   "seg_thick_abs_err_mm": float(np.nanmean([abs(np.nanmedian(thp[mp & (segp == s)]) - seg_th_r[s])
                                                             for s in range(1, 17) if (mp & (segp == s)).sum() > 50])),
                   }
            err, binchg = {tau: [] for tau in TAUS}, {tau: [] for tau in TAUS}
            for (s, tau), sc in scars.items():
                e = transmurality(sc, mp, segp, s)
                if np.isnan(e) or np.isnan(est_r[(s, tau)]): continue
                err[tau].append(e - est_r[(s, tau)])
                binchg[tau].append(int(np.digitize(e, KIM) != np.digitize(est_r[(s, tau)], KIM)))
            row["transm_err_pp_mean"] = {str(t): float(100 * np.mean(v)) for t, v in err.items()}
            row["transm_err_pp_mae"] = {str(t): float(100 * np.mean(np.abs(v))) for t, v in err.items()}
            row["kim_bin_changed"] = {str(t): float(np.mean(v)) for t, v in binchg.items()}
            rows.append(row)
    out["est_ref_transm_mean"] = {str(t): float(np.nanmean([est_r[(s, t)] for s in range(1, 17)])) for t in TAUS}
    out["E2"] = rows
    print(out["case"], "done", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("out")
    ap.add_argument("--grid", type=float, default=0.5); ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--jobs", type=int, default=4); ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    cases = sorted(p for p in pathlib.Path(a.data).glob("s[0-9]*") if (p / "segmentations/aorta.nii.gz").exists())
    if a.only: cases = [c for c in cases if c.name in a.only]
    with ProcessPoolExecutor(a.jobs) as ex:
        res = list(ex.map(run_case, [(str(c), a.grid, a.reps) for c in cases]))
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()

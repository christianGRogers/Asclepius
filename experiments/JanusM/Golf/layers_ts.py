"""Golf E2: transmural layers and AHA segments derived from a myocardium mask, on real cardiac CT.

Question: should Janus-M *learn* myocardial layers (transmural thirds, AHA segments) as classes, or learn only the
myocardium (endocardial + epicardial borders) and *derive* the layers geometrically?  And what metric decides?

Data: TotalSegmentator v2.0.1 contrast cardiac CTs (CC BY 4.0) that are not in the SegQueue14 pool (fetch_ts.py),
with their released labels: channel 1 left atrium, 3 LV myocardium, 4 LV blood pool, 5 RV blood pool (1.5 mm iso).

Per case:
  A. Attenuation: median HU of LV blood pool and of the eroded myocardium; myocardial noise (MAD-SD).
  B. Wall thickness: median of d_endo + d_epi over myocardial voxels more than 5 mm from the left atrium.
  C. Transmural depth u = d_endo/(d_endo+d_epi) (equal-thickness thirds [0,1/3), [1/3,2/3), [2/3,1]); the
     Laplace-potential thirds (0 endocardium, 1 epicardium) are reported beside them for comparison.
  D. AHA 17 segments: long axis by PCA of the LV, base = mitral plane (LV voxels touching the LA), apex cap = myocardium
     beyond the cavity tip, angle zero = anterior RV insertion (ends of the RV-contact arc).
  E. Boundary-error sensitivity, on a 0.5 mm grid (signed distances interpolated from 1.5 mm): the endocardial and
     epicardial signed distances get a smooth random displacement field of RMS sigma; the layers are re-derived
     and compared with the reference: Dice of the myocardium, Dice of each third, Dice of the 17 segments, and the
     error in median wall thickness.  This is the error a model with a given border accuracy makes in each layer.

Usage: python layers_ts.py <ts_dir> [--cases N] [--sigmas 0.25,0.5,1.0] [--reps 2]
Writes layers_ts.json next to this file.  CPU only; ~1-3 min per case.
"""
import argparse, json, time
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import cg

LA, MYO, LV, RV = 1, 3, 4, 5
RNG = np.random.default_rng(20261030)


# ---------------------------------------------------------------------------------------------- geometry helpers
def laplace(myo, inner, spacing=None):
    """Solve Laplace in `myo` with phi=0 on `inner` and phi=1 elsewhere outside `myo` (6-neighbour, CG)."""
    idx = -np.ones(myo.shape, np.int64)
    pts = np.argwhere(myo)
    n = len(pts)
    idx[tuple(pts.T)] = np.arange(n)
    rows, cols, vals = [], [], []
    b = np.zeros(n)
    diag = np.zeros(n)
    for ax in range(3):
        for d in (-1, 1):
            nb = pts.copy()
            nb[:, ax] += d
            ok = np.all((nb >= 0) & (nb < np.array(myo.shape)), axis=1)
            j = np.full(n, -2, np.int64)
            j[ok] = idx[tuple(nb[ok].T)]
            diag += 1
            inmyo = j >= 0
            rows.append(np.nonzero(inmyo)[0]); cols.append(j[inmyo]); vals.append(-np.ones(inmyo.sum()))
            # Dirichlet neighbours: inner -> 0 (adds nothing), other -> 1
            out = ~inmyo
            isinner = np.zeros(n, bool)
            isinner[out & ok] = inner[tuple(nb[out & ok].T)]
            b += (out & ~isinner).astype(float)
    A = coo_matrix((np.concatenate(vals + [diag]),
                    (np.concatenate(rows + [np.arange(n)]), np.concatenate(cols + [np.arange(n)]))),
                   shape=(n, n)).tocsr()
    x0 = np.full(n, 0.5)
    x, _ = cg(A, b, x0=x0, rtol=1e-6, maxiter=3000)
    phi = np.full(myo.shape, np.nan, np.float32)
    phi[tuple(pts.T)] = x
    return phi


def depth(myo, cav, sp):
    """Equal-thickness transmural depth u = d_endo / (d_endo + d_epi) in [0, 1] (0 endocardium)."""
    de = ndi.distance_transform_edt(~cav, sampling=sp)
    dp = ndi.distance_transform_edt(myo | cav, sampling=sp)
    u = np.full(myo.shape, np.nan, np.float32)
    u[myo] = (de / np.maximum(de + dp, 1e-6))[myo]
    return u


def thirds(phi, myo):
    lab = np.zeros(myo.shape, np.uint8)
    p = np.nan_to_num(phi, nan=-1)
    lab[myo & (p < 1 / 3)] = 1      # subendocardial
    lab[myo & (p >= 1 / 3) & (p < 2 / 3)] = 2   # mid-wall
    lab[myo & (p >= 2 / 3)] = 3     # subepicardial
    return lab


def dice(a, b):
    s = a.sum() + b.sum()
    return float(2 * (a & b).sum() / s) if s else float("nan")


def aha(myo, cav, rv, la, spacing):
    """AHA 17-segment labels (1..17) on `myo`; returns labels and a dict of diagnostics."""
    sp = np.asarray(spacing)
    lvpts = np.argwhere(myo | cav) * sp
    c = lvpts.mean(0)
    _, _, vt = np.linalg.svd(lvpts - c, full_matrices=False)
    axis = vt[0]
    # mitral plane: cavity voxels within 3 mm of the LA
    near_la = cav & (ndi.distance_transform_edt(~la, sampling=sp) <= 3.0)
    if near_la.sum() < 10:
        return None, {"fail": "no LV-LA contact"}
    base_c = np.argwhere(near_la).mean(0) * sp
    if np.dot(base_c - c, axis) > 0:
        axis = -axis                       # axis points base -> apex
    proj = lambda m: (np.argwhere(m) * sp - base_c) @ axis
    cav_tip = np.percentile(proj(cav), 99.5)
    allpts = np.argwhere(myo)
    P = allpts * sp
    s = (P - base_c) @ axis
    # circumferential frame
    rel = P - base_c - np.outer(s, axis)
    near_rv = myo & (ndi.distance_transform_edt(~rv, sampling=sp) <= 3.0)
    if near_rv.sum() < 10:
        return None, {"fail": "no myocardium-RV contact"}
    u = np.cross(axis, [0.0, 0.0, 1.0]); u /= np.linalg.norm(u)
    v = np.cross(axis, u)
    ang = np.degrees(np.arctan2(rel @ v, rel @ u)) % 360
    rvp = np.argwhere(near_rv) * sp
    rvrel = rvp - base_c - np.outer((rvp - base_c) @ axis, axis)
    rva = np.degrees(np.arctan2(rvrel @ v, rvrel @ u)) % 360
    # contact arc: largest gap in the circular histogram of RV-contact angles gives the arc's two ends
    h = np.sort(rva)
    gaps = np.diff(np.concatenate([h, [h[0] + 360]]))
    g = int(np.argmax(gaps))
    end1, end2 = h[(g + 1) % len(h)], h[g]          # arc runs from end1 counter-clockwise to end2
    arc = (end2 - end1) % 360
    # which end is anterior (RAS: +y anterior in voxel space only if the affine is near-diagonal; use world later)
    def world_dir(a):
        a = np.radians(a)
        return np.cos(a) * u + np.sin(a) * v
    return (s, ang, cav_tip, end1, end2, arc, world_dir, allpts), {"septal_arc_deg": float(arc)}


def aha_labels(myo, geom, anterior_vox):
    s, ang, cav_tip, end1, end2, arc, world_dir, allpts = geom
    # anterior insertion = arc end whose direction points more anterior
    a1 = np.dot(world_dir(end1), anterior_vox)
    a2 = np.dot(world_dir(end2), anterior_vox)
    if a1 >= a2:
        ant, sign = end1, 1.0      # septum lies counter-clockwise from the anterior insertion
    else:
        ant, sign = end2, -1.0
    theta = (sign * (ang - ant)) % 360    # 0 at anterior insertion, increasing through the septum
    lab = np.zeros(myo.shape, np.uint8)
    lev = np.where(s > cav_tip, 3, np.minimum((s / max(cav_tip, 1e-6) * 3).astype(int), 2))
    lev[s < 0] = 0
    seg = np.zeros(len(s), np.uint8)
    # basal / mid: 1 anterior, 2 anteroseptal, 3 inferoseptal, 4 inferior, 5 inferolateral, 6 anterolateral.
    # The septum (2, 3) spans the measured RV-contact arc; the free wall (4, 5, 6, 1) splits the rest in four.
    def six(t):
        out = np.empty(len(t), np.uint8)
        sept = t < arc
        out[sept] = np.where(t[sept] < arc / 2, 2, 3)
        r = (t[~sept] - arc) / (360 - arc) * 4          # 0..4 over the free wall: inferior..anterior
        out[~sept] = np.array([4, 5, 6, 1], np.uint8)[np.clip(r.astype(int), 0, 3)]
        return out
    for L, off in ((0, 0), (1, 6)):
        m = lev == L
        seg[m] = six(theta[m]) + off
    m = lev == 2       # apical: 13 anterior, 14 septal, 15 inferior, 16 lateral (septum centred on the arc)
    t = (theta[m] - arc / 2 + 45) % 360
    seg[m] = np.array([14, 15, 16, 13], np.uint8)[(t // 90).astype(int) % 4]
    seg[lev == 3] = 17
    lab[tuple(allpts.T)] = seg
    return lab


# ---------------------------------------------------------------------------------------------- per case
def load(case_dir):
    from heldout import refuse
    refuse("TotalSegmentator-cardiac", Path(case_dir).name)   # never opens a held-out case
    ct = nib.load(case_dir / "ct.nii.gz")
    lab = nib.load(case_dir / "cardiac_label.nii.gz")
    L = np.asanyarray(lab.dataobj) > 0.5           # (13, X, Y, Z)
    return np.asanyarray(ct.dataobj).astype(np.float32), L, np.array(ct.header.get_zooms()[:3], float), ct.affine


def crop(*arrs, mask, margin=8):
    nz = np.argwhere(mask)
    lo = np.maximum(nz.min(0) - margin, 0)
    hi = np.minimum(nz.max(0) + margin + 1, mask.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    return [a[sl] for a in arrs]


def smooth_field(shape, spacing, corr_mm, rms):
    f = ndi.gaussian_filter(RNG.standard_normal(shape).astype(np.float32), sigma=corr_mm / np.asarray(spacing))
    return f * (rms / (f.std() + 1e-9))


def sdf(m, sp):
    """Signed distance (mm, negative inside) with the surface half-way between voxel centres, so its slope is 1
    across the border (a plain edt(~m) - edt(m) jumps by one voxel there and halves every shift)."""
    h = float(np.mean(sp)) / 2
    return (ndi.distance_transform_edt(~m, sampling=sp) - h) * ~m - (ndi.distance_transform_edt(m, sampling=sp) - h) * m


def wall_thickness(myo, cav, phi, sp, exclude):
    de = ndi.distance_transform_edt(~cav, sampling=sp)
    dp = ndi.distance_transform_edt(myo | cav, sampling=sp)
    t = (de + dp)[myo & ~exclude]          # local thickness at every myocardial voxel away from the base
    return float(np.median(t)) if t.size else float("nan"), t


def run_case(case_dir, sigmas, reps, fine=0.5):
    t0 = time.time()
    ct, L, sp, aff = load(case_dir)
    la, myo, cav, rv = L[LA], L[MYO], L[LV], L[RV]
    ct, la, myo, cav, rv = crop(ct, la, myo, cav, rv, mask=myo | cav)
    out = {"spacing_mm": sp.tolist(), "myo_ml": float(myo.sum() * sp.prod() / 1000)}
    # A. attenuation
    core = ndi.binary_erosion(myo, iterations=1)
    out["hu_lv_blood"] = float(np.median(ct[ndi.binary_erosion(cav, iterations=2)]))
    out["hu_myo"] = float(np.median(ct[core])) if core.any() else float("nan")
    out["sd_myo"] = float(1.4826 * np.median(np.abs(ct[core] - out["hu_myo"]))) if core.any() else float("nan")
    # B/C. Laplace and thickness at 1.5 mm
    base_excl = ndi.distance_transform_edt(~la, sampling=sp) <= 5.0
    phi = laplace(myo, cav)
    out["wall_mm_median"], tvals = wall_thickness(myo, cav, phi, sp, base_excl)
    out["wall_mm_p10_p90"] = [float(np.percentile(tvals, 10)), float(np.percentile(tvals, 90))] if tvals.size else None
    th_lap = thirds(phi, myo)
    th = thirds(depth(myo, cav, sp), myo)
    out["third_share_equal_thickness"] = [float((th == k).sum() / myo.sum()) for k in (1, 2, 3)]
    out["third_share_laplace_potential"] = [float((th_lap == k).sum() / myo.sum()) for k in (1, 2, 3)]
    out["agree_laplace_vs_thickness_thirds"] = float((th == th_lap)[myo].mean())
    out["voxels_per_third_at_1p5mm"] = out["wall_mm_median"] / 3 / sp.mean()
    # D. AHA
    anterior_world = np.array([0.0, 1.0, 0.0])             # RAS +y
    R = aff[:3, :3] / np.linalg.norm(aff[:3, :3], axis=0)  # voxel axes in world
    anterior_vox = R.T @ anterior_world
    geom, diag = aha(myo, cav, rv, la, sp)
    out.update(diag)
    if geom is not None:
        seg = aha_labels(myo, geom, anterior_vox)
        vols = np.array([(seg == k).sum() for k in range(1, 18)], float)
        out["aha_share"] = (vols / vols.sum()).round(4).tolist()
        out["aha_empty_segments"] = int((vols == 0).sum())
        out["aha_cv_1_16"] = float(vols[:16].std() / vols[:16].mean())
        Rw = R * sp                                         # voxel index -> world offset (mm)
        cen = lambda m: np.argwhere(m).mean(0) @ Rw.T
        c0 = cen(myo)
        rvdir = cen(rv) - c0
        ant = lambda k: float(np.dot(cen(seg == k) - c0, anterior_world))
        out["aha_checks"] = {
            "seg1_anterior_mm": ant(1), "seg4_anterior_mm": ant(4),
            "septum_towards_rv": bool(np.dot(cen((seg == 2) | (seg == 3) | (seg == 8) | (seg == 9)) - c0, rvdir) > 0),
            "lateral_away_from_rv": bool(np.dot(cen((seg == 5) | (seg == 6) | (seg == 11) | (seg == 12)) - c0, rvdir) < 0)}
        out["aha_checks"]["ok"] = bool(out["aha_checks"]["seg1_anterior_mm"] > out["aha_checks"]["seg4_anterior_mm"]
                                       and out["aha_checks"]["septum_towards_rv"] and out["aha_checks"]["lateral_away_from_rv"])
    # E. sensitivity on a fine grid
    z = sp / fine
    s_epi = ndi.zoom(sdf(myo | cav, sp).astype(np.float32), z, order=1)
    s_endo = ndi.zoom(sdf(cav, sp).astype(np.float32), z, order=1)
    la_f = ndi.zoom(sdf(la, sp).astype(np.float32), z, order=1) < 0
    rv_f = ndi.zoom(sdf(rv, sp).astype(np.float32), z, order=1) < 0
    fsp = np.full(3, fine)

    def derive(se, sn):
        cv = sn < 0
        m = (se < 0) & ~cv
        return m, cv, None, thirds(depth(m, cv, fsp), m)   # the Laplace potential is not needed here

    myo_r, cav_r, phi_r, th_r = derive(s_epi, s_endo)
    excl_f = ndi.distance_transform_edt(~la_f, sampling=fsp) <= 5.0
    w_ref, _ = wall_thickness(myo_r, cav_r, phi_r, fsp, excl_f)
    geom_r, _ = aha(myo_r, cav_r, rv_f, la_f, fsp)
    seg_r = aha_labels(myo_r, geom_r, anterior_vox) if geom_r is not None else None
    out["fine"] = {"wall_mm_ref": w_ref, "runs": []}
    for sg in sigmas:
        for r in range(reps):
            se = s_epi + smooth_field(s_epi.shape, fsp, 8.0, sg)
            sn = s_endo + smooth_field(s_endo.shape, fsp, 8.0, sg)
            m, cv, ph, th = derive(se, sn)
            w, _ = wall_thickness(m, cv, ph, fsp, excl_f)
            run = {"sigma_mm": sg, "rep": r, "dice_myo": dice(m, myo_r),
                   "dice_thirds": [dice(th == k, th_r == k) for k in (1, 2, 3)],
                   "wall_err_mm": w - w_ref}
            if seg_r is not None:
                g2, _ = aha(m, cv, rv_f, la_f, fsp)
                if g2 is not None:
                    s2 = aha_labels(m, g2, anterior_vox)
                    run["dice_aha_mean"] = float(np.nanmean([dice(s2 == k, seg_r == k) for k in range(1, 18)]))
            out["fine"]["runs"].append(run)
    for name, de, dn in (("epi_out_0.5mm", -0.5, 0.0), ("endo_in_0.5mm", 0.0, 0.5), ("both_0.5mm_thicker", -0.5, 0.5)):
        m, cv, ph, th = derive(s_epi + de, s_endo + dn)
        w, _ = wall_thickness(m, cv, ph, fsp, excl_f)
        out["fine"]["runs"].append({"bias": name, "dice_myo": dice(m, myo_r),
                                    "dice_thirds": [dice(th == k, th_r == k) for k in (1, 2, 3)],
                                    "wall_err_mm": w - w_ref})
    out["seconds"] = round(time.time() - t0, 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ts_dir")
    ap.add_argument("--cases", type=int, default=24)
    ap.add_argument("--sigmas", default="0.25,0.5,1.0")
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--part", default="0/1", help="i/n: run every n-th case from i (parallel runs), merged by --merge")
    ap.add_argument("--merge", action="store_true", help="merge layers_ts.part*.json into layers_ts.json and stop")
    a = ap.parse_args()
    here = Path(__file__).parent
    ids = list(json.loads((here / "ts_cases.json").read_text()))[: a.cases]
    sig = [float(x) for x in a.sigmas.split(",")]
    res = {}
    outp = here / "layers_ts.json"
    if a.merge:
        for f in sorted(here.glob("layers_ts.part*.json")):
            res.update(json.loads(f.read_text())["cases"])
        if outp.exists():
            res = {**json.loads(outp.read_text()).get("cases", {}), **res}
        res = {i: res[i] for i in ids if i in res}
        outp.write_text(json.dumps({"sigmas": sig, "reps": a.reps, "cases": res}, indent=1))
        print("merged", len(res), "cases")
        return
    done = json.loads(outp.read_text()).get("cases", {}) if outp.exists() else {}
    k, n = map(int, a.part.split("/"))
    if n > 1:
        ids = [i for j, i in enumerate(ids) if j % n == k and i not in done]
        outp = here / f"layers_ts.part{k}.json"
    if outp.exists():
        res = json.loads(outp.read_text()).get("cases", {})
    for i in ids:
        if i in res:
            continue
        try:
            res[i] = run_case(Path(a.ts_dir) / i, sig, a.reps)
        except Exception as e:  # report, never hide
            res[i] = {"error": repr(e)}
        r = res[i]
        print(i, {k: r.get(k) for k in ("hu_lv_blood", "hu_myo", "wall_mm_median", "septal_arc_deg",
                                         "aha_cv_1_16", "seconds", "error")}, flush=True)
        outp.write_text(json.dumps({"sigmas": sig, "reps": a.reps, "cases": res}, indent=1))


if __name__ == "__main__":
    main()
